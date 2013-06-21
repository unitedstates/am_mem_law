#!/usr/bin/env python

# You'll need the Congress project's tasks directory to be on your path:
# export PYTHONPATH=../congress/tasks

import sys, os, glob
import datetime, time
import re
import json
from utils import format_datetime

###

# Path to congresses metadata.
CONGRESSES_PATH = "./data/congresses"

###

collections = [ "llhb", "llsb" ]
image_path_template = "http://memory.loc.gov/ll/%s/%s/%s/%s.%s"

chambers = { "llhb": "h", "llsb": "s" }
bill_types = {
	"No.": "hr", # Early House bills were just listed as "No."
	"H.R.": "hr", # Note: Some House bills originally listed with "No." were transcribed as "H.R."
	"H.R. No.": "hr", # A small number of House bills are listed as "H.R. No."
	"": "hr", # House bills in certain Congresses are listed only by number.
	"H.R.C.C.": "hrcc", # House Court of Claims report
	"S.": "s",
	#"S.R.": "sjres", # "S.R." is either a Senate Joint Resolution or a Senate bill considered in the House
}

bills = {}
congress_committees = {}
calendar = {}

# XXX
bill_no_types = set()
unknown_bill_types = {}

bill_no_pattern = re.compile( "^([A-Za-z.\s]*?)\s*([\dLXVI]+(?: 1/2)?)$" )

print "Parsing bill collection files..."

for collection in collections:
	large_volumes = set()
	for volume_fn in glob.glob("json/" + collection + "*.json"):
			with open(volume_fn) as json_file:
				print volume_fn, "..."

				metadata = json.load(json_file)
				for document in metadata:
					tiff_filename = document['pages'][-1]["image"]
					image_name = tiff_filename[0:tiff_filename.index( "." )]

					resource_page = image_name[4:8]

					# Certain volumes have more than 10,000 resources.
					# These use 5 digits for the resource number and 3 digits for the page number.
					# We assume any resource with a "page number" greater than 1000 is one of these.
					# But we also have to keep track of them, to handle resource numbers that end in zero.
					if (volume_fn in large_volumes) or (int( resource_page ) >= 1000):
						large_volumes.add(volume_fn)

						resource_number = image_name[0:5]
						resource_page = image_name[5:8]
						resource_number_prefix = resource_number[0:3]
						resource_number_pattern = "%05d"
					else:
						resource_number = image_name[0:4]
						resource_number_prefix = resource_number[0:2]
						resource_number_pattern = "%04d"

					resource_number_set = "%s00" % resource_number_prefix

					main_resource_number = resource_number_pattern % int( resource_number )
					
					ampage_url = "http://memory.loc.gov/cgi-bin/ampage?collId=%s&fileName=%s/%s%s.db&recNum=%04d" % ( collection, document['volume'], collection, document['volume'], ( int( resource_number ) - 1 ) )

					urls = {
						"web": ampage_url,
						"tiff": image_path_template % ( document['collection'], document['volume'], resource_number_set, image_name, "tif" ),
						"gif": image_path_template % ( document['collection'], document['volume'], resource_number_set, image_name, "gif" ),
					}

					if document['chamber'] != chambers[collection]:
						raise ValueError( "Unexpected chamber" )

					if document['congress'] not in calendar:
						calendar[document['congress']] = {}

					# XXX: Ensure the few resources that are associated with multiple bills fail to parse as a valid bill.
					bill_no = ",".join(document["bill_numbers"])

					bill_no_matches = bill_no_pattern.search( bill_no )

					# The bill number provided doesn't match the expected format, so we have to ensure we use a unique one.
					if bill_no_matches is None:
						print "Invalid bill number in %s, volume %s (%d-%d): %s" % ( document['collection'], document['volume'], document['congress'], document['session'], bill_no )
						bill_type = "ammem-%s-%s-unk" % ( document['collection'], document['volume'] )
						bill_number = main_resource_number
					else:
						bill_type_orig = bill_no_matches.group( 1 )
						bill_number = bill_no_matches.group( 2 )

						# Handle fractional, recycled, or unusual bill numbers.
						try:
							bad_bill_number = False

							bill_number = int( float( bill_number.replace( " 1/2", ".5" ) ) * 10 )
							bill_number = str( ( document['session'] * 100000 ) + bill_number )
						except:
							print "Unexpected bill number in %s, volume %s (%d-%d): %s" % ( document['collection'], document['volume'], document['congress'], document['session'], bill_no )
							bad_bill_number = True

						# XXX
						bill_no_types.add( bill_type_orig )

						# If we don't recognize the bill type provided, create a special bill type that we'll know to check later.
						if (bill_type_orig in bill_types) and (not bad_bill_number):
							bill_type = bill_types[bill_type_orig]
						else:
							# XXX
							if bill_type_orig not in unknown_bill_types:
								unknown_bill_types[bill_type_orig] = set()
							unknown_bill_types[bill_type_orig].add( "%s-%s" % ( document['collection'], document['volume'] ) )

							bill_type = "ammem-%s-%s-%s" % ( document['collection'], document['volume'], bill_type_orig.lower().replace( '.', '' ).replace( ' ', '' ) )

					bill_id = "%s%s-%d" % ( bill_type, bill_number, document['congress'] )

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
								"original_bill_number": bill_no,
								"bill_id": bill_id,
								"action": action,
							}

							calendar[document['congress']][bill_date].append( calendar_item )

					sources = [{
						"source": "ammem",
						"collection": collection,
						"volume": document['volume'],
						"source_url": ampage_url,
					}]

					bill = {
						"bill_id": bill_id,
						"bill_type": bill_type,
						"number": bill_number,
						"congress": document['congress'],

						"original_bill_number": bill_no,
						"session": document['session'],
						"chamber": document['chamber'],

						"actions": actions,
						"status": bill_status,
						"status_at": format_datetime(document['dates'][-1]),

						"titles": [ { "type": "official", "as": "introduced", "title": bill_title } ] if bill_title else [],
						"official_title": bill_title,

						"description": bill_description,

						"committees": committees,

						"sources": sources,
						"updated_at": format_datetime(datetime.datetime.fromtimestamp(time.time())),

						"urls": urls,
					}

					bills.setdefault(document['congress'], {}).setdefault(bill_type, {})[bill_id] = bill

print "Writing committees file..."

with open("committees.json", "w") as commitees_file:
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

# XXX
print "All Bill Types:", bill_no_types
print "Unrecognized Bill Types:", unknown_bill_types
