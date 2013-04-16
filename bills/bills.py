#!/usr/bin/env python

import sys
import os
import datetime, time
import re
import csv
import json

# XXX: congress.utils.format_datetime()
from pytz import timezone

###

# Path to LL metadata.
LL_PATH = sys.argv[1]

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
#			print "Bill %s in %s, volume %s (%s-%s) has an invalid date: %s" % ( bill_no, code, volume, congress, session, bill_dates[0] )
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


codes = [ "llhb", "llsb" ]
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

bill_no_pattern = re.compile( "^([A-Za-z.\s]*?)\s*([\dLXVI]+(?: 1/2)?)$" )

for code in codes:
	code_dir = LL_PATH + code
	for volume in os.listdir( code_dir ):
		with open( code_dir + "/" + volume + "/" + code + volume + ".txt" ) as metadata:
			print "Parsing %s, volume %s..." % ( code, volume )

			reader = csv.reader( metadata )
			try:
				for image in reader:
					if image[0] != code:
						raise ValueError( "Unexpected code" )

					if image[1] != volume:
						raise ValueError( "Unexpected volume" )

					image_name = image[2][0:image[2].index( "." )]
					resource_number = image_name[0:4]
					resource_number_set = "%s00" % resource_number[0:2]

					page_no = 1 if image[6] == "" else int( image[6] )

					main_resource_number = "%04d" % ( int( resource_number ) - ( page_no - 1 ) )

					ampage_url = "http://memory.loc.gov/cgi-bin/ampage?collId=%s&fileName=%s/%s%s.db&recNum=%04d" % ( code, volume, code, volume, ( int( image_name[0:4] ) - 1 ) )

					urls = {
						"web": ampage_url,
						"tiff": image_path_template % ( code, volume, resource_number_set, image_name, "tif" ),
						"gif": image_path_template % ( code, volume, resource_number_set, image_name, "gif" ),
					}

					congress = str( int( image[3] ) )
					session = str( int( image[4] ) )
					chamber = image[5]

					if chamber != chambers[code]:
						raise ValueError( "Unexpected chamber" )

					bill_no = image[7].strip()

					bill_no_matches = bill_no_pattern.search( bill_no )

					# The bill number provided doesn't match the expected format, so we have to ensure we use a unique one.
					if bill_no_matches is None:
						print "Unexpected bill number in %s, volume %s (%s-%s): %s" % ( code, volume, congress, session, bill_no )
						bill_type = "ammem-%s-%s-unk" % ( code, volume )
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
							unknown_bill_types[bill_type_orig].add( "%s-%s" % ( code, volume ) )

							bill_type = "ammem-%s-%s-%s" % ( code, volume, bill_type_orig )

					bill_id = "%s%s-%s" % ( bill_type, bill_number, congress )

					bill_dates = image[8].split( "," )

					actions = []

					# Sometimes the bill has multiple dates associated with it, so we'll treat each as a separate action.
					for bill_date in bill_dates:
						action = {
							"acted_at": format_bill_date( bill_date ),
						}

						actions.append( action )

					bill_date = format_bill_date( bill_dates[-1] ) # XXX: congress.bill_info.latest_status()

					if bill_date is None:
						# Certain dates have typos (like invalid values for month or day, or extra digits).
						print "Bill %s in %s, volume %s (%s-%s) has an invalid date: %s" % ( bill_no, code, volume, congress, session, bill_dates[-1] )

					bill_description = image[9]

					committees = []

					try:
						committee_names = image[10]
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

					if page_no != 1:
						if ( bill_description != "" ) or ( committee_names != "" ):
							print "Page %d of bill %s in %s, volume %s (%s-%s) has extra information!" % ( page_no, bill_no, code, volume, congress, session )
						else:
							# If we know the real bill_id, append the additional information to the main bill entry.
							# Otherwise, let it have its own bill entry.
							if bill_id in bills[congress][bill_type]:
								bills[congress][bill_type][bill_id]["urls"][page_no] = urls
								bills[congress][bill_type][bill_id]["metadata"].append( image )
								continue

					sources = []

					source = {
						"source": "ammem",
						"code": code,
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

						"urls": { page_no: urls },
					}

					if congress not in bills:
						bills[congress] = {}

					if bill_type not in bills[congress]:
						bills[congress][bill_type] = {}

					bills[congress][bill_type][bill_id] = bill
			except csv.Error as e:
				# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
				print "Error parsing %s, volume %s: %s" % ( code, volume, e )
				continue

# XXX
print bill_no_types
print unknown_bill_types

for congress in bills:
	for bill_type in bills[congress]:
		for bill_id in bills[congress][bill_type]:
			bill = bills[congress][bill_type][bill_id]

			# XXX: congress.utils.write()

			bill_dir = "%s/%s/bills/%s/%s%s" % ( "data", congress, bill_type, bill_type, bill["number"] ) # XXX: congress.utils.data_dir()

			try:
				os.makedirs( bill_dir )
			except OSError:
				# Directory already exists, but we don't care.
				pass

			bill_path = "%s/data.json" % ( bill_dir )

			print "Writing %s..." % ( bill_path )
			open( bill_path, "w" ).write( json.dumps( bill, indent=2, ensure_ascii=False ) )
