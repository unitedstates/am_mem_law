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
#   . ../congress/.env/bin/activate
#   export PYTHONPATH=../congress/tasks

import sys, os, os.path, glob
import datetime, time
import re
import json
import utils

# Get the congress project's data directory.
CONGRESSES_PATH = os.path.join(os.path.dirname(utils.__file__), os.path.join("..", utils.data_dir()))

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
					original_bill_number = "/".join(document['bill_numbers'])

					bill_description = document["description"]

					committees = []
					committee_names = document["committees"]

					for committee in committee_names:
						if document['chamber'] not in congress_committees:
							congress_committees[document['chamber']] = {}

						if committee not in congress_committees[document['chamber']]:
							congress_committees[document['chamber']][committee] = set()

						congress_committees[document['chamber']][committee].add(document['congress'])

						committee_info = {
							"committee": committee,
							"activity": [ "referral" ], # XXX
							"committee_id": None, # XXX
						}

						committees.append( committee_info )

					bill_status = "INTRODUCED"
					bill_title = None

					bill_title_match = re.search( "(An Act|A Bill),? (.+\.)$", bill_description )

					if bill_title_match:
						if bill_title_match.group(1) == "An Act":
							# If listed as an act, assume it has passed the other chamber.
							bill_status = "PASS_OVER:HOUSE" if document['chamber'] == "s" else "PASS_OVER:SENATE"
						elif re.search( "[Rr]eported", bill_description ):
							bill_status = "REPORTED"
						elif len(committees) > 0:
							bill_status = "REFERRED"

						bill_title = bill_title_match.group(2)

					bill_dates = document["dates"]

					if document['congress'] not in calendar:
						calendar[document['congress']] = {}

					actions = []

					# Sometimes the bill has multiple dates associated with it, so we'll treat each as a separate action.
					for bill_date in bill_dates:
						action = {
							"acted_at": bill_date,
							"text": bill_description,
						}

						# If there are committees associated with the resource, it's probably a referral action.
						if committee_names != []:
							action["type"] = "referral"
							action["committee"] = committee_names
						else:
							action["type"] = "action"

						actions.append( action )

						if ( action["text"] != "" ) or ( "committee" in action ):
							if bill_date not in calendar[document['congress']]:
								calendar[document['congress']][bill_date] = []

							calendar_item = {
								"source": "%s%s" % ( collection, document['volume'] ),
								"session": document['session'],
								"chamber": document['chamber'],
								"original_bill_number": original_bill_number,
								"bill_id": bill_id,
								"action": action,
							}

							calendar[document['congress']][bill_date].append( calendar_item )

					sources = [{
						"source": "ammem",
						"collection": document['collection'],
						"volume": document['volume'],
						"source_url": document['pages'][0]['link'],
					}]

					bill = {
						"bill_id": bill_id,
						"bill_type": document['bill_type'],
						"number": document['bill_stable_number'],
						"congress": document['congress'],

						"original_bill_number": original_bill_number,
						"session": document['session'],
						"chamber": document['chamber'],

						"actions": actions,
						"status": bill_status,
						"status_at": utils.format_datetime(document['dates'][-1]),

						"titles": [ { "type": "official", "as": "introduced", "title": bill_title } ] if bill_title else [],
						"official_title": bill_title,

						"description": bill_description,

						"committees": committees,

						"sources": sources,
						"updated_at": utils.format_datetime(datetime.datetime.fromtimestamp(time.time())),

						"urls": {
							"web": document['pages'][0]['link'],
							"tiff": document['pages'][0]['large_image_url'],
							"gif": document['pages'][0]['small_image_url'],
						},

					}

					bills.setdefault(document['congress'], {}).setdefault(document['bill_type'], {})[bill_id] = bill

print "Writing committees file..."

with open("historical-committees.json", "w") as commitees_file:
	json.dump( congress_committees, commitees_file, indent=2, separators=(',', ': '), sort_keys=True, default=(lambda obj: sorted(list(obj)) if isinstance(obj, set) else json.JSONEncoder.default(obj)) )

print "Writing bill data files..."

for congress in bills:
	for bill_type in bills[congress]:
		for bill_id in bills[congress][bill_type]:
			bill = bills[congress][bill_type][bill_id]

			# XXX: congress.utils.write()

			bill_dir = "%s/%d/bills/%s/%s%s" % ( CONGRESSES_PATH, congress, bill_type, bill_type, bill["number"] ) # XXX: congress.utils.data_dir()

			try:
				os.makedirs( bill_dir )
			except OSError:
				# Directory already exists, but we don't care.
				pass

			bill_path = "%s/data.json" % ( bill_dir )

			with open(bill_path, "w") as bill_file:
				json.dump( bill, bill_file, indent=2, separators=(',', ': '), sort_keys=True )

print "Writing calendar files..."

for congress in calendar:
	with open("%s/%s/calendar.json" % ( CONGRESSES_PATH, congress ), "w") as calendar_file:
		json.dump( calendar[congress], calendar_file, indent=2, separators=(',', ': '), sort_keys=True, default=(lambda obj: sorted(list(obj)) if isinstance(obj, set) else json.JSONEncoder.default(obj)) )


