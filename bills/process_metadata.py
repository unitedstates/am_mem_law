#!/usr/bin/env python

import sys, os
import re
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
	"llhb": [ ( "collection", None, r"llhb" ), ( "volume", None, r"[0-9]{3}" ), ( "tiff_filename", None, r"[0-9]{8}\.tif" ), ( "congress", None, r"[0-9]{3}" ), ( "session", None, r"[0-9]{3}" ), ( "chamber", None, r"[hs]" ), ( "page", None, r"[0-9]*" ), ( "bill_numbers", ",", r"(?:[A-Za-z.\s]*?)\s*(?:[\dLXVI]+(?: 1/2)?)?\s*" ), ( "dates", ",", r"[0-9]{8}" ), ( "description", None, r".*?" ), ( "committees", "~", r"\s*(?:|\.|Revolutionary [^~]*|Military [^~]*|Whole House [^~]*|(?:Committed to (?:a|the) )?(?:(?:Joint(?: Library)?|Select) )?[Cc][oe]mmitt?e[ed]s?,?[^~]*)" ) ],
	"llsb": [ ( "collection", None, r"llsb" ), ( "volume", None, r"[0-9]{3}" ), ( "tiff_filename", None, r"[0-9]{8}\.tif" ), ( "congress", None, r"[0-9]{3}" ), ( "session", None, r"[0-9]{3}" ), ( "chamber", None, r"[hs]" ), ( "page", None, r"[0-9]*" ), ( "bill_numbers", ",", r"(?:[A-Za-z.\s]*?)\s*(?:[\dLXVI]+(?: 1/2)?)?\s*" ), ( "dates", ",", r"[0-9]{8}" ), ( "description", None, r".*?" ), ( "committees", "~", r"\s*(?:|\.|Revolutionary [^~]*|Military [^~]*|Whole House [^~]*|(?:Committed to (?:a|the) )?(?:(?:Joint(?: Library)?|Select) )?[Cc][oe]mmitt?e[ed]s?,?[^~]*)" ) ],
	"llsr": [ ( "collection", None, r"llsr" ), ( "volume", None, r"[0-9]{3}" ), ( "tiff_filename", None, r"[0-9]{8}\.tif" ), ( "congress", None, r"[0-9]{3}" ), ( "session", None, r"[0-9]{3}" ), ( "chamber", None, r"[hs]" ), ( "page", None, r"[0-9]*" ), ( "bill_numbers", ",", r"(?:[A-Za-z.\s]*?)\s*(?:[\dLXVI]+(?: 1/2)?)?\s*" ), ( "dates", ",", r"[0-9]{8}" ), ( "description", None, r".*?" ), ( "committees", "~", r"\s*(?:|\.|Revolutionary [^~]*|Military [^~]*|Whole House [^~]*|(?:Committed to (?:a|the) )?(?:(?:Joint(?: Library)?|Select) )?[Cc][oe]mmitt?e[ed]s?,?[^~]*)" ) ],
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

			regexp_pieces = []

			# Because of issues with unescaped quotes, we can't use a normal CSV parser.
			# Instead, we construct a regular expression based on the expected values of each field.
			for field_data in fields[collection]:
				field, separator, data_pattern = field_data

				if separator:
					field_pattern = r'(' + data_pattern + r"(?:" + separator + data_pattern + r')*)'
				else:
					field_pattern = r'(' + data_pattern + r')'

				regexp_pieces.append(r'"(?:' + field_pattern + r'|)"')

			regexp = re.compile(",".join(regexp_pieces))

			original_metadata = []

			for line in txt_file:
				# Ignore blank lines.
				if line.strip() == "":
					continue

				line_matches = regexp.match(line)
				if line_matches:
					row = {}

					match_groups = line_matches.groups()
					for i in range(len(match_groups)):
						field, separator, _ = fields[collection][i]

						if match_groups[i] is not None:
							# The American Memory metadata files are in an encoding similar or equal to IBM Code Page 850.
							row[field] = match_groups[i].decode("cp850").strip()

							if separator:
								row[field] = row[field].split(separator) if row[field] != "" else []
						else:
							row[field] = [] if separator else ""

					original_metadata.append(row)
				else:
					# XXX
					print line

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
							# Blank line.
							if len(line) == 0:
								continue

							row = {}
							for i in range(len(fields[collection])):
								field, separator, _ = fields[collection][i]

								if (i < len(line)):
									line.append( "" )

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
					for ( field, separator, _ ) in fields[collection]:
						if separator:
							line[field] = separator.join(line[field])

						row.append(line[field])
					csv_writer.writerow(row)
			except unicodecsv.Error as e:
				# XXX: The CSV chokes on quoted values with newline characters (possibly \r\n)
				print "Error writing CSV file for collection %s, volume %s: %s" % ( collection, volume, e )
