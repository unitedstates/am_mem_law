#!/usr/bin/env python

# Convert the American Memory Century of Lawmaking metadata files for
# House and Senate bills and resolutions (llhb, llsb, llsr) into JSON
# files for bills in the format used by the unitedstates/congress
# project.
#
# This script was written originally by Gordon Hemsley. Modified by
# Joshua Tauberer.
#
# You'll need the Congress project's environment activated and its
# files on the path:
#   source ../../congress/.env/bin/activate
#   export PYTHONPATH=../../congress/tasks
#   python bills.py

import sys, os, os.path, glob
import datetime, time
import re
import json
import bill_info, utils

# Options to pass to bill_info.output_bill.

write_options = { }
if "--govtrack" in sys.argv: write_options["govtrack"] = True

###

collections = [ "llhb", "llsb" ]
image_path_template = "http://memory.loc.gov/ll/%s/%s/%s/%s.%s"

chambers = { "llhb": "h", "llsb": "s" }

bills = {}
congress_committees = {}
calendar = {}

print "Parsing bill collection files..."

for collection in collections:
	large_volumes = set()
	for volume_fn in glob.glob("json/" + collection + "*.json"):
		
			with open(volume_fn) as json_file:
				print volume_fn, "..."

				metadata = json.load(json_file)
				for document in metadata:
					if document['chamber'] != chambers[collection]:
						raise ValueError( "Unexpected chamber" )
						
					if 'bill_stable_number' not in document:
						# not a recognized bill
						continue
						
					bill_id = document['bill_type'] + str(document['bill_stable_number']) + "-" + str(document['congress'])

					# A bill can appear multiple times because it may have been reprinted after
					# major activity. Turn each print into action information.
					bill = bills\
						.setdefault(document['congress'], {})\
						.setdefault(document['bill_type'], {})\
						.setdefault(bill_id, {
							"bill_id": bill_id,
							"bill_type": document['bill_type'],
							"number": str(document['bill_stable_number']),
							"congress": str(document['congress']),
							
							"updated_at": utils.format_datetime(datetime.datetime.fromtimestamp(time.time())),
	
							"original_bill_number": "/".join(document['bill_numbers']),
							"session": document['session'],
							"chamber": document['chamber'],
	
							"introduced_at": utils.format_datetime(document['dates'][0]),
							
							# filled in below
							"titles": [],
							"official_title": None,
							"committees": [],
							"actions": [],

							# not yet scraped
							"sponsor": None,
							
							# not known
							"cosponsors": [],
							"related_bills": [],
							"subjects_top_term": None,
							"subjects": [],
							"amendments": [],
						})
	
					# Take some metadata like the title and status from the most recent print. Assumes the records in
					# each JSON file are in chronological order.\

					# The original description field.
					bill["description"] = document["description"]

					# Scrape the title out of the description field.
					bill_heading = None
					bill_title_match = re.search( "(An Act|A Bill),? (.+?)(: Therefore,)?$", bill["description"] )
					if bill_title_match:
						bill_heading = bill_title_match.group(1)
						bill_title = bill_title_match.group(2)
						bill["titles"] = [ { "type": "official", "as": "introduced", "title": bill_title, "is_for_portion": False } ]
						bill["official_title"] = bill_title
					else:
						pass # print "Invalid bill title:", bill["description"]

					# Committees.
					for committee in document["committees"]:
						# We may have seen this committee in a previous print.
						if committee in [c["committee"] for c in bill["committees"]]: continue
						
						# Create a committee record.
						bill["committees"].append({
							"committee": committee,
							"activity": [ "referral" ], # XXX
							"committee_id": None, # XXX
						})

						# Mark off the committee names we've seen.
						congress_committees.setdefault(document['chamber'], {}).setdefault(committee, set()).add(document['congress'])

					# Current status.
					bill_status = "INTRODUCED"
					if bill_heading == "An Act": bill_status = "ENACTED:SIGNED" # best guess
					bill["status"] = bill_status
					bill["status_at"] = utils.format_datetime(document['dates'][-1])
					
					# Source links.
					source_info = {
						"source": "ammem",
						"collection": document['collection'],
						"volume": document['volume'],
						"source_url": document['pages'][0]['link'],
					}
					bill["sources"] = [source_info] # just use the most recent
						
					# Action.
					action = {
						"acted_at": document["dates"][0], #Sometimes the bill has multiple dates associated with it
						"text": bill["description"],
						"references": [],
						"source": source_info,
					}
					if len(document["committees"]) > 0:
						# If there are committees associated with the resource, it's probably a referral action.
						action["type"] = "referral"
						action["committee"] = document["committees"]
					else:
						action["type"] = "action"
					bill["actions"].append( action )
					if ( action["text"] != "" ) or ( "committee" in action ):
						calendar.setdefault(document['congress'], {}).setdefault(action["acted_at"], []).append({
							"source": "%s%s" % ( collection, document['volume'] ),
							"session": document['session'],
							"chamber": document['chamber'],
							"bill_id": bill_id,
							"action": action,
						})

					# Set 'urls' to the most recent version.
					bill["urls"] = {
						"web": document['pages'][0]['link'],
						"tiff": document['pages'][0]['large_image_url'],
						"gif": document['pages'][0]['small_image_url'],
					}
					

# Move to the congress project directory so the output done by bill_info.output_bill
# gets to the right place.
os.chdir(os.path.join(os.path.dirname(utils.__file__), ".."))

print "Writing committees file..."

with open("historical-committees.json", "w") as commitees_file:
	json.dump( congress_committees, commitees_file, indent=2, separators=(',', ': '), sort_keys=True, default=(lambda obj: sorted(list(obj)) if isinstance(obj, set) else json.JSONEncoder.default(obj)) )

print "Writing bill data files..."

for congress in bills:
	for bill_type in bills[congress]:
		for bill_id in bills[congress][bill_type]:
			bill = bills[congress][bill_type][bill_id]
			try:
				bill_info.output_bill(bill, write_options)
			except:
				print bill["bill_id"]
				raise

print "Writing calendar files..."

for congress in calendar:
	with open("%s/%s/calendar.json" % ( utils.data_dir(), congress ), "w") as calendar_file:
		json.dump( calendar[congress], calendar_file, indent=2, separators=(',', ': '), sort_keys=True, default=(lambda obj: sorted(list(obj)) if isinstance(obj, set) else json.JSONEncoder.default(obj)) )


