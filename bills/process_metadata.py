#!/usr/bin/env python

import sys, os
import csv, json

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

if source not in [ "json", "csv", "txt" ]:
	# XXX: Issue an error about an unsupported source type.
	raise

if clobber:
	# XXX: Issue warning about possible data loss.
	pass

if update:
	# XXX: Download metadata files from American Memory.
	pass

fields = {
	"llhb": [ "collection", "volume", "tiff_filename", "congress", "session", "chamber", "page", "bill_number", "dates", "description", "committees" ],
	"llsb": [ "collection", "volume", "tiff_filename", "congress", "session", "chamber", "page", "bill_number", "dates", "description", "committees" ],
	"llsr": [ "collection", "volume", "tiff_filename", "congress", "session", "chamber", "page", "bill_number", "dates", "description", "committees" ],
}

for collection in collections:
	collection_dir = LL_PATH + collection
	for volume in os.listdir( collection_dir ):
		metadata_path = "%s/%s/" % ( collection_dir, volume )
		metadata_filename = "%s%s" % ( collection, volume )
		txt_path = "%s%s.txt" % ( metadata_path, metadata_filename )
		json_path = "%s%s.json" % ( metadata_path, metadata_filename )
		csv_path = "%s%s.csv" % ( metadata_path, metadata_filename )

		with open(txt_path) as txt_file:
			print "Parsing text file for collection %s, volume %s..." % ( collection, volume )

			original_metadata = []
			txt_reader = csv.reader(txt_file)
			try:
				for line in txt_reader:
					row = {}
					for i in range(len(fields[collection])):
						# The American Memory metadata files are in an encoding similar or equal to IBM Code Page 850.
						row[fields[collection][i]] = line[i].decode("cp850").encode("utf-8") if (i < len(line)) else ""
					original_metadata.append(row)
			except csv.Error as e:
				# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
				print "Error parsing text file for collection %s, volume %s: %s" % ( collection, volume, e )
				continue

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
					csv_reader = csv.reader(csv_file)
					try:
						for line in csv_reader:
							row = {}
							for i in range(len(fields[collection])):
								row[fields[collection][i]] = line[i]
							metadata.append(row)
					except csv.Error as e:
						# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
						print "Error parsing CSV file for collection %s, volume %s: %s" % ( collection, volume, e )
						continue
			except IOError:
				pass

		with open(json_path, "w") as json_file:
			json.dump(metadata, json_file, indent=2, separators=(',', ': '), sort_keys=True)

		with open(csv_path, "w") as csv_file:
			csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
			try:
				for line in metadata:
					row = []
					for field in fields[collection]:
						row.append(line[field].encode("utf-8"))
					csv_writer.writerow(row)
			except csv.Error as e:
				# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
				print "Error writing CSV file for collection %s, volume %s: %s" % ( collection, volume, e )
