#!/usr/bin/env python

import sys, os
import datetime, time
import re
import json

# XXX: congress.utils.format_datetime()
from pytz import timezone

###

# Path to LL metadata.
LL_PATH = "./data/collections"

for arg in sys.argv[1:]:
	if not arg.startswith("--"):
		LL_PATH = arg
		break

verbose = "--verbose" in sys.argv

###

# Path to congresses metadata.
CONGRESSES_PATH = "./data/congresses"

###

def format_bill_date( bill_date_orig ):
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
congress_committees = {}

# XXX
bill_no_types = set()
unknown_bill_types = {}
orphaned_pages = []

bill_no_pattern = re.compile( "^([A-Za-z.\s]*?)\s*([\dLXVI]+(?: 1/2)?)$" )

print "Parsing bill collection files..."

for collection in collections:
	collection_dir = "%s/%s" % ( LL_PATH, collection )
	large_volumes = set()
	for volume in os.listdir( collection_dir ):
		try:
			with open( "%s/%s/%s%s.json" % ( collection_dir, volume, collection, volume ) ) as json_file:
				if verbose:
					print "Parsing JSON file for collection %s, volume %s..." % ( collection, volume )

				metadata = json.load(json_file)
				for image in metadata:
					if image["collection"] != collection:
						raise ValueError( "Unexpected collection" )

					if image["volume"] != volume:
						raise ValueError( "Unexpected volume" )

					image_name = image["tiff_filename"][0:image["tiff_filename"].index( "." )]

					resource_page = image_name[4:8]

					# Certain volumes have more than 10,000 resources.
					# These use 5 digits for the resource number and 3 digits for the page number.
					# We assume any resource with a "page number" greater than 1000 is one of these.
					# But we also have to keep track of them, to handle resource numbers that end in zero.
					if (volume in large_volumes) or (int( resource_page ) >= 1000):
						large_volumes.add(volume)

						resource_number = image_name[0:5]
						resource_page = image_name[5:8]
						resource_number_prefix = resource_number[0:3]
						resource_number_pattern = "%05d"
					else:
						resource_number = image_name[0:4]
						resource_number_prefix = resource_number[0:2]
						resource_number_pattern = "%04d"

					resource_number_set = "%s00" % resource_number_prefix

					page_no = 1 if image["page"] == "" else int( image["page"] )

					main_resource_number = resource_number_pattern % ( int( resource_number ) - ( page_no - 1 ) )

					ampage_url = "http://memory.loc.gov/cgi-bin/ampage?collId=%s&fileName=%s/%s%s.db&recNum=%04d" % ( collection, volume, collection, volume, ( int( resource_number ) - 1 ) )

					urls = {
						"web": ampage_url,
						"tiff": image_path_template % ( collection, volume, resource_number_set, image_name, "tif" ),
						"gif": image_path_template % ( collection, volume, resource_number_set, image_name, "gif" ),
					}

					congress = int( image["congress"] )
					session = int( image["session"] )
					chamber = image["chamber"]

					if chamber != chambers[collection]:
						raise ValueError( "Unexpected chamber" )

					# XXX: Ensure the few resources that are associated with multiple bills fail to parse as a valid bill.
					bill_no = ",".join(image["bill_numbers"])

					bill_no_matches = bill_no_pattern.search( bill_no )

					# The bill number provided doesn't match the expected format, so we have to ensure we use a unique one.
					if bill_no_matches is None:
						print "Unexpected bill number in %s, volume %s (%d-%d): %s" % ( collection, volume, congress, session, bill_no )
						bill_type = "ammem-%s-%s-unk" % ( collection, volume )
						bill_number = main_resource_number
					else:
						bill_type_orig = bill_no_matches.group( 1 )
						bill_number = bill_no_matches.group( 2 )

						# Handle fractional, recycled, or unusual bill numbers.
						try:
							bad_bill_number = False

							bill_number = int( float( bill_number.replace( " 1/2", ".5" ) ) * 10 )
							bill_number = str( ( session * 100000 ) + bill_number )
						except:
							print "Unexpected bill number in %s, volume %s (%d-%d): %s" % ( collection, volume, congress, session, bill_no )
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
							unknown_bill_types[bill_type_orig].add( "%s-%s" % ( collection, volume ) )

							bill_type = "ammem-%s-%s-%s" % ( collection, volume, bill_type_orig.lower().replace( '.', '' ).replace( ' ', '' ) )

					bill_id = "%s%s-%d" % ( bill_type, bill_number, congress )

					bill_description = image["description"]

					bill_title_match = re.search( "(?:An Act|A Bill),? (.+\.)$", bill_description )

					if bill_title_match:
						bill_title = bill_title_match.group(1)
					else:
						bill_title = None

					committees = []
					committee_names = image["committees"]

					for committee in committee_names:
						if chamber not in congress_committees:
							congress_committees[chamber] = {}

						if committee not in congress_committees[chamber]:
							congress_committees[chamber][committee] = set()

						congress_committees[chamber][committee].add(congress)

						committee_info = {
							"committee": committee,
							"activity": [], # XXX
							"committee_id": None, # XXX
						}

						committees.append( committee_info )

					bill_dates = image["dates"]

					actions = []

					# Sometimes the bill has multiple dates associated with it, so we'll treat each as a separate action.
					for bill_date in bill_dates:
						action = {
							"acted_at": format_bill_date( bill_date ),
							"text": bill_description,
						}

						# If there are no committees associated with the resource, it's probably a secondary page.
						if (page_no == 1) or (committee_names != []):
							action["committee"] = committee_names

						actions.append( action )

					bill_date = format_bill_date( bill_dates[-1] ) # XXX: congress.bill_info.latest_status()

					if bill_date is None:
						# Certain dates have typos (like invalid values for month or day, or extra digits).
						print "Bill %s in collection %s, volume %s (%d-%d) has an invalid date: %s" % ( bill_no, collection, volume, congress, session, bill_dates[-1] )

					# If this is a secondary page or another resource about the same bill, append the data to the existing entry.
					if ( congress in bills ) and ( bill_type in bills[congress] ) and ( bill_id in bills[congress][bill_type] ):
						# If this contains new information about the bill, extract it.
						if ( page_no == 1 ) or ( ( page_no != 1 ) and ( ( bill_description != "" ) or ( committee_names != [] ) ) ):
							bills[congress][bill_type][bill_id]["actions"].extend( actions )
							bills[congress][bill_type][bill_id]["committees"].extend( committees )

						if main_resource_number not in bills[congress][bill_type][bill_id]["urls"]:
							bills[congress][bill_type][bill_id]["urls"][main_resource_number] = {}

						bills[congress][bill_type][bill_id]["urls"][main_resource_number][page_no] = urls

						continue

					# Check for orphaned pages.
					if page_no != 1:
						print "Page %d of bill %s in collection %s, volume %s (%d-%d) is probably an orphan." % ( page_no, bill_no, collection, volume, congress, session )
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
						"bill_id": bill_id,
						"bill_type": bill_type,
						"number": bill_number,
						"congress": str( congress ),

						"original_bill_number": bill_no,
						"session": str( session ),
						"chamber": chamber,

						"actions": actions,
						"status": "REFERRED" if len(committees) > 1 else "INTRODUCED", # XXX: We could probably extract more of this information.
						"status_at": bill_date,

						"titles": [ { "type": "official", "as": "introduced", "title": bill_title } ] if bill_title else [],
						"official_title": bill_title,

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

print "Writing committees file..."

with open("%s/committees.json" % ( CONGRESSES_PATH ), "w") as json_file:
	json.dump( congress_committees, json_file, indent=2, separators=(',', ': '), sort_keys=True, default=(lambda obj: sorted(list(obj)) if isinstance(obj, set) else json.JSONEncoder.default(obj)) )

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

			if verbose:
				print "Writing %s..." % ( bill_path )

			with open(bill_path, "w") as json_file:
				json.dump( bill, json_file, indent=2, separators=(',', ': '), sort_keys=True )

# XXX
print "All Bill Types:", bill_no_types
print "Unrecognized Bill Types:", unknown_bill_types
print "Bills with Orphaned Pages:", orphaned_pages
