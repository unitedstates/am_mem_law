#!/usr/bin/env python

import sys
import os
import datetime
import csv
import json

###

# Path to LL metadata.
LL_PATH = sys.argv[1]

###

codes = [ "llhb", "llsb" ]
chambers = { "llhb": "h", "llsb": "s" }

bills = {}

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

					image_name = image[2]
					congress = image[3]
					session = image[4]
					chamber = image[5]

					if chamber != chambers[code]:
						raise ValueError( "Unexpected chamber" )

					bill_no = image[7]
					page_no = image[6]

					bill_dates = image[8].split( "," )

					# XXX: The date of action sometimes differs from the date of printing, so both are listed.
#					if len( bill_dates ) > 1:
#						print "Bill %s in %s-%s-%s has multiple dates!" % ( bill_no, code, congress, session )

					try:
						# Most dates are of a Ymd format.
						bill_date = datetime.datetime.strptime( bill_dates[0], "%Y%m%d" )
					except ValueError:
						try:
							# Sometimes a bill doesn't specify a day, so it's encoded as '00'.
							bill_date = datetime.datetime.strptime( bill_dates[0], "%Y%m00" )
						except ValueError:
							# Certain dates have typos (like invalid values for month or day, or extra digits).
							print "Bill %s in %s-%s-%s has an invalid date: %s" % ( bill_no, code, congress, session, bill_dates[0] )
							continue

					# For some reason, datetime doesn't support years < 1900.
					bill_date = "%04d-%02d-%02d" % ( bill_date.year, bill_date.month, bill_date.day )

					bill_description = image[9]

					try:
						committee_info = image[10]
					except IndexError:
						# Some entries don't have a committee field, so we'll have to fudge it.
						committee_info = ""

					if page_no != "":
						if ( bill_description != "" ) or ( committee_info != "" ):
							print "Page %s of bill %s in %s-%s-%s has extra information!" % ( page_no, bill_no, code, congress, session )
						else:
							# XXX: For now, ignore secondary pages; we may want to revisit this.
							continue

					bill = {
						"congress": congress,
						"session": session,
						"chamber": chamber,
						"number": bill_no,
						"date": bill_date,
						"description": bill_description,
						"committees": committee_info.split( "~" ),
					}

					if congress not in bills:
						bills[congress] = {}

					if session not in bills[congress]:
						bills[congress][session] = {}

					if chamber not in bills[congress][session]:
						bills[congress][session][chamber] = []

					bills[congress][session][chamber].append( bill )
			except csv.Error as e:
				# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
				print "Error parsing %s, volume %s: %s" % ( code, volume, e )
				continue


for congress in bills:
	for session in bills[congress]:
		for chamber in bills[congress][session]:
			bill_dir = "bills/%s/%s" % ( congress, session )

			try:
				os.makedirs( bill_dir )
			except OSError:
				# Directory already exists, but we don't care.
				pass

			bill_path = "%s/%s.json" % ( bill_dir, chamber )

			print "Writing %s..." % ( bill_path )
			open( bill_path, "w" ).write( json.dumps( bills[congress][session][chamber], indent=2, ensure_ascii=False ) )