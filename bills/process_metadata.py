#!/usr/bin/env python

import sys, os
import unicodecsv, json

options = {}

for arg in sys.argv[1:]:
	if arg.startswith("--"):
		if "=" in arg:
			key, value = arg.split("=")
		else:
			key, value = arg, True

		key = key.split("--")[1]

		options[key.lower()] = value

LL_PATH = options.get("path", "./data/collections/")

update = options.get("update", False)
source = options.get("source", "json")
clobber = options.get("clobber", (source == "txt"))
collections = options.get("collections", "llhb,llsb,llsr").split(",")
single_volume = options.get("volume", None)

if source not in [ "json", "csv", "txt" ]:
	# XXX: Issue an error about an unsupported source type.
	raise

if single_volume and (len(collections) > 1):
	# XXX: Issue an error about too many collections.
	raise

if clobber:
	# XXX: Issue warning about possible data loss.
	pass

if update:
	# XXX: Download metadata files from American Memory.
	pass

fields = {
	"llhb": [ ( "collection", None ), ( "volume", None ), ( "tiff_filename", None ), ( "congress", None ), ( "session", None ), ( "chamber", None ), ( "page", None ), ( "bill_numbers", "," ), ( "dates", "," ), ( "description", None ), ( "committees", "~" ) ],
	"llsb": [ ( "collection", None ), ( "volume", None ), ( "tiff_filename", None ), ( "congress", None ), ( "session", None ), ( "chamber", None ), ( "page", None ), ( "bill_numbers", "," ), ( "dates", "," ), ( "description", None ), ( "committees", "~" ) ],
	"llsr": [ ( "collection", None ), ( "volume", None ), ( "tiff_filename", None ), ( "congress", None ), ( "session", None ), ( "chamber", None ), ( "page", None ), ( "bill_numbers", "," ), ( "dates", "," ), ( "description", None ), ( "committees", "~" ) ],
}

for collection in collections:
	collection_dir = LL_PATH + collection
	volumes = [ single_volume ] if single_volume else os.listdir( collection_dir )
	for volume in volumes:
		metadata_path = "%s/%s/" % ( collection_dir, volume )
		metadata_filename = "%s%s" % ( collection, volume )
		txt_path = "%s%s.txt" % ( metadata_path, metadata_filename )
		json_path = "%s%s.json" % ( metadata_path, metadata_filename )
		csv_path = "%s%s.csv" % ( metadata_path, metadata_filename )

		with open(txt_path) as txt_file:
			print "Parsing text file for collection %s, volume %s..." % ( collection, volume )

			original_metadata = []
			# The American Memory metadata files are in an encoding similar or equal to IBM Code Page 850.
			txt_reader = unicodecsv.reader(txt_file, encoding="cp850")
			try:
				for line in txt_reader:
					row = {}
					for i in range(len(fields[collection])):
						field, separator = fields[collection][i]

						row[field] = line[i].strip() if (i < len(line)) else ""

						if separator:
							row[field] = row[field].split(separator)
					original_metadata.append(row)
			except unicodecsv.Error as e:
				print "Error parsing text file for collection %s, volume %s: %s" % ( collection, volume, e )

		metadata = original_metadata

		if ((not clobber) and (source == "json")):
			try:
				with open(json_path) as json_file:
					print "Parsing JSON file for collection %s, volume %s..." % ( collection, volume )

					metadata = json.load(json_file)
			except IOError:
				pass
		elif ((not clobber) and (source == "csv")):
			try:
				with open(csv_path) as csv_file:
					print "Parsing CSV file for collection %s, volume %s..." % ( collection, volume )

					metadata = []
					csv_reader = unicodecsv.reader(csv_file)
					try:
						for line in csv_reader:
							row = {}
							for i in range(len(fields[collection])):
								field, separator = fields[collection][i]

								line[i] = line[i].strip()
								row[field] = ( [] if ( line[i] == "" ) else line[i].split(separator) ) if separator else line[i]
							metadata.append(row)
					except unicodecsv.Error as e:
						print "Error parsing CSV file for collection %s, volume %s: %s" % ( collection, volume, e )
			except IOError:
				pass

		with open(json_path, "w") as json_file:
			json.dump(metadata, json_file, indent=2, separators=(',', ': '), sort_keys=True)

		with open(csv_path, "w") as csv_file:
			csv_writer = unicodecsv.writer(csv_file, quoting=unicodecsv.QUOTE_ALL)
			try:
				for line in metadata:
					row = []
					for ( field, separator ) in fields[collection]:
						if separator:
							line[field] = separator.join(line[field])

						row.append(line[field])
					csv_writer.writerow(row)
			except unicodecsv.Error as e:
				# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
				print "Error writing CSV file for collection %s, volume %s: %s" % ( collection, volume, e )
