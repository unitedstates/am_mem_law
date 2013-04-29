#!/usr/bin/env python

import sys, os
import datetime, time
import re
import json

# XXX: congress.utils.format_datetime()
from pytz import timezone

###

# Path to LL metadata.
LL_PATH = sys.argv[1] if len(sys.argv) > 1 else "./data/collections/"

###

def format_bill_date( bill_date_orig ):
#	try:
#		# Most dates are of a Ymd format.
#		bill_date = datetime.datetime.strptime( bill_date_orig, "%Y%m%d" )
#	except ValueError:
#		try:
#			# Sometimes a bill doesn't specify a day, so it's encoded as '00'.
#			bill_date = datetime.datetime.strptime( bill_date_orig, "%Y%m00" )
#		except ValueError:
#			# Certain dates have typos (like invalid values for month or day, or extra digits).
#			print "Bill %s in %s, volume %s (%s-%s) has an invalid date: %s" % ( bill_no, collection, volume, congress, session, bill_dates[0] )
#			continue
#
#	# For some reason, datetime doesn't support years < 1900.
#	return ( "%04d-%02d-%02d" % ( bill_date.year, bill_date.month, bill_date.day ) )

	bill_date_matches = re.search( "^([0-9]{4})([0-9]{2})([0-9]{2})$", bill_date_orig )

	if bill_date_matches is None:
		return None

	year = bill_date_matches.group( 1 )
	month = bill_date_matches.group( 2 )
	day = bill_date_matches.group( 3 )

	return ( "%s-%s-%s" % ( year, month, day ) ) #( "%04d-%02d-%02d" % ( year, month, day ) )


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

# XXX
bill_no_types = set()
unknown_bill_types = {}
orphaned_pages = []

bill_no_pattern = re.compile( "^([A-Za-z.\s]*?)\s*([\dLXVI]+(?: 1/2)?)$" )

for collection in collections:
	collection_dir = LL_PATH + collection
	for volume in os.listdir( collection_dir ):
		try:
			with open( collection_dir + "/" + volume + "/" + collection + volume + ".json" ) as json_file:
				print "Parsing JSON file for collection %s, volume %s..." % ( collection, volume )

				metadata = json.load(json_file)
				for image in metadata:
					if image["collection"] != collection:
						raise ValueError( "Unexpected collection" )

					if image["volume"] != volume:
						raise ValueError( "Unexpected volume" )

					image_name = image["tiff_filename"][0:image["tiff_filename"].index( "." )]

					resource_number = image_name[0:4]
					resource_page = image_name[4:8]

					resource_number_set = "%s00" % resource_number[0:2]

					page_no = 1 if image["page"] == "" else int( image["page"] )

					main_resource_number = "%04d" % ( int( resource_number ) - ( page_no - 1 ) )

					ampage_url = "http://memory.loc.gov/cgi-bin/ampage?collId=%s&fileName=%s/%s%s.db&recNum=%04d" % ( collection, volume, collection, volume, ( int( resource_number ) - 1 ) )

					urls = {
						"web": ampage_url,
						"tiff": image_path_template % ( collection, volume, resource_number_set, image_name, "tif" ),
						"gif": image_path_template % ( collection, volume, resource_number_set, image_name, "gif" ),
					}

					congress = str( int( image["congress"] ) )
					session = str( int( image["session"] ) )
					chamber = image["chamber"]

					if chamber != chambers[collection]:
						raise ValueError( "Unexpected chamber" )

					bill_no = image["bill_number"].strip()

					bill_no_matches = bill_no_pattern.search( bill_no )

					# The bill number provided doesn't match the expected format, so we have to ensure we use a unique one.
					if bill_no_matches is None:
						print "Unexpected bill number in %s, volume %s (%s-%s): %s" % ( collection, volume, congress, session, bill_no )
						bill_type = "ammem-%s-%s-unk" % ( collection, volume )
						bill_number = main_resource_number
					else:
						bill_type_orig = bill_no_matches.group( 1 )
						bill_number = bill_no_matches.group( 2 ).replace( " 1/2", ".5" ) # XXX: Some bills have been assigned fractional numbers.

						# XXX
						bill_no_types.add( bill_type_orig )

						# If we don't recognize the bill type provided, create a special bill type that we'll know to check later.
						if bill_type_orig in bill_types:
							bill_type = bill_types[bill_type_orig]
						else:
							# XXX
							if bill_type_orig not in unknown_bill_types:
								unknown_bill_types[bill_type_orig] = set()
							unknown_bill_types[bill_type_orig].add( "%s-%s" % ( collection, volume ) )

							bill_type = "ammem-%s-%s-%s" % ( collection, volume, bill_type_orig.lower().replace( '.', '' ).replace( ' ', '' ) )

					bill_id = "%s%s-%s" % ( bill_type, bill_number, congress )

					bill_description = image["description"]

					committees = []

					try:
						committee_names = image["committees"]
					except IndexError:
						# Some entries don't have a committee field, so we'll have to fudge it.
						committee_names = ""

					for committee in committee_names.split( "~" ):
						if committee != "":
							committee_info = {
								"committee": committee,
								"activity": [], # XXX
								"committee_id": None, # XXX
							}

							committees.append( committee_info )

					bill_dates = image["dates"].split( "," )

					actions = []

					# Sometimes the bill has multiple dates associated with it, so we'll treat each as a separate action.
					for bill_date in bill_dates:
						action = {
							"acted_at": format_bill_date( bill_date ),
							"text": bill_description,
						}

						if committee_names != "":
							action["committee"] = committee_names

						actions.append( action )

					bill_date = format_bill_date( bill_dates[-1] ) # XXX: congress.bill_info.latest_status()

					if bill_date is None:
						# Certain dates have typos (like invalid values for month or day, or extra digits).
						print "Bill %s in collection %s, volume %s (%s-%s) has an invalid date: %s" % ( bill_no, collection, volume, congress, session, bill_dates[-1] )

					# If this is a secondary page or another resource about the same bill, append the data to the existing entry.
					if ( congress in bills ) and ( bill_type in bills[congress] ) and ( bill_id in bills[congress][bill_type] ):
						# If this contains new information about the bill, extract it.
						if ( page_no == 1 ) or ( ( page_no != 1 ) and ( ( bill_description != "" ) or ( committee_names != "" ) ) ):
							bills[congress][bill_type][bill_id]["actions"].extend( actions )
							bills[congress][bill_type][bill_id]["committees"].extend( committees )

						bills[congress][bill_type][bill_id]["metadata"].append( image )

						if main_resource_number not in bills[congress][bill_type][bill_id]["urls"]:
							bills[congress][bill_type][bill_id]["urls"][main_resource_number] = {}

						bills[congress][bill_type][bill_id]["urls"][main_resource_number][page_no] = urls

						continue

					# Check for orphaned pages.
					if page_no != 1:
						print "Page %d of bill %s in collection %s, volume %s (%s-%s) has extra information!" % ( page_no, bill_no, collection, volume, congress, session )
						orphaned_pages.append( bill_id )

					sources = []

					source = {
						"source": "ammem",
						"collection": collection,
						"volume": volume,
						"source_url": ampage_url,
					}

					sources.append( source )

					bill = {
						"metadata": [ image ], # The original metadata, before parsing.

						"bill_id": bill_id,
						"bill_type": bill_type,
						"number": bill_number,
						"congress": congress,

						"session": session,
						"chamber": chamber,

						"actions": actions,
						"status_at": bill_date,

						"description": bill_description,

						"committees": committees,

						"sources": sources,
						"updated_at": timezone( "US/Eastern" ).localize( datetime.datetime.fromtimestamp( time.time() ).replace( microsecond=0 ) ).isoformat(), # XXX: congress.utils.format_datetime()

						"urls": { main_resource_number: { page_no: urls } },
					}

					if congress not in bills:
						bills[congress] = {}

					if bill_type not in bills[congress]:
						bills[congress][bill_type] = {}

					bills[congress][bill_type][bill_id] = bill
		except IOError as e:
			# XXX: If the JSON file doesn't exist, ignore this volume and move on.
			print "Error parsing collection %s, volume %s: %s" % ( collection, volume, e )
			continue

for congress in bills:
	for bill_type in bills[congress]:
		for bill_id in bills[congress][bill_type]:
			bill = bills[congress][bill_type][bill_id]

			# XXX: congress.utils.write()

			bill_dir = "%s/%s/bills/%s/%s%s" % ( "data/congresses", congress, bill_type, bill_type, bill["number"] ) # XXX: congress.utils.data_dir()

			try:
				os.makedirs( bill_dir )
			except OSError:
				# Directory already exists, but we don't care.
				pass

			bill_path = "%s/data.json" % ( bill_dir )

			print "Writing %s..." % ( bill_path )
			with open(bill_path, "w") as json_file:
				json.dump( bill, json_file, indent=2, separators=(',', ': '), sort_keys=True )

# XXX
print "All Bill Types:", bill_no_types
print "Unrecognized Bill Types:", unknown_bill_types
print "Bills with Orphaned Pages:", orphaned_pages
