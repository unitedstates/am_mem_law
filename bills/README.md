American Memory Bills
=====================

Normalized metadata for the bills and resolutions collections of the Library of Congress's [American Memory Century of Lawmaking](http://memory.loc.gov/ammem/amlaw/lawhome.html) site, curated and corrected for better sustainability and accessibility.

By Gordon Hemsley (@GPHemsley) and Joshua Tauberer (@tauberer).

Collections
-----------

We have cleaned up the metadata for the following American Memory collections:

* `llhb`: Bills in the House of Representatives, 6th Congress-42nd Congress (1799-1873), excluding the 12th Congress
* `llsb`: Bills in the Senate, 16th Congress-42nd Congress (1819-1873)
* `llsr`: Senate Resolutions/Joint Resolutions, 18th Congress-42nd Congress (1823-1873), excluding the 20th and 24th Congresses

Source Data
-----------

Each collection is divided into a number of volumes. The volumes are apparently numbered according to the order
in which the Library of Congress scanned the physical volumes, which was out of chronological order.

We have copied the original metadata files from the Library of Congress to the "source" directory and applied a few select corrections (see the git history for details). The files are named:

	source/[collection][volume].txt

These files look like CSV but are actually hard to parse correctly (see process_metadata.py). They were originally downloaded from URLs such as:

	http://memory.loc.gov:8081/ll/llsb/007/llsb007.txt

A mirror of the originals (including metadata from other collections) are also currently stored at http://www.govtrack.us/data/misc/am_mem_law_metadata.tgz (187M). The file llsb004.txt appears to have been accidentally truncated on the memory.loc.gov website. Some day we'll check with the Library of Congress about whether they have the rest of the file.

Each original metadata record represents a single physical page of a document printed in one of the volumes. A document could be a bill or resolution, or an amendment to a bill or resolution, or perhaps other
sorts of bill/resolution-related document. Some documents are somehow related to multiple bills.
(In the JSON format described below, the bill_numbers field is an array.)

Processing the Data
-------------------

Our script process_metadata.py will read in each source file and generate two cleaner files:

* csv/[collection][volume].csv: The same information converted into a UTF-8 encoded CSV file, with some field normalization.
* json/[collection][volume].json: The same information coverted to JSON (see notes below).

The CSV format preserves the logical intent of the original. Each row is a page of a document. In the JSON format, the pages of each document are grouped together, so the records of the JSON file are documents (not pages) and the page information is stored in the 'pages' field inside each document.

To run, just execute:

	python process_metadata.py
	
Here's some example output from `json/llhb045.json`:

	  {
		"bill_numbers": [
		  "H.R. 2"
		],
		"bill_stable_number": 200020,
		"bill_type": "hr",
		"chamber": "h",
		"collection": "llhb",
		"committees": [
		  "Committee of the Whole House"
		],
		"congress": 13,
		"dates": [
		  "1813-12-20"
		],
		"description": "Read the first and second time and committed to a committee of the whole House on Wednesday next. A Bill To authorise the Secretary of the Treasury to subscribe, in behalf of the United States, for seven hundred and fifty shares in the capital stock of the Chesapeake and Delaware Canal Company.",
		"pages": [
		  {
			"image": "00020000.tif",
			"large_image_url": "http://memory.loc.gov/ll/llhb/045/0000/00020000.tif",
			"link": "http://memory.loc.gov/cgi-bin/ampage?collId=llhb&fileName=045/llhb045.db&recNum=1",
			"page": null,
			"record_number": 2,
			"small_image_url": "http://memory.loc.gov/ll/llhb/045/0000/00020000.gif"
		  },
		  {
			"image": "00030002.tif",
			"large_image_url": "http://memory.loc.gov/ll/llhb/045/0000/00030002.tif",
			"link": "http://memory.loc.gov/cgi-bin/ampage?collId=llhb&fileName=045/llhb045.db&recNum=2",
			"page": 2,
			"record_number": 3,
			"small_image_url": "http://memory.loc.gov/ll/llhb/045/0000/00030002.gif"
		  }
		],
		"session": 2,
		"volume": 45
	  },
	  
Bill Numbering
--------------
	
In the pre-modern era of Congress, bills were not numbered as predictably as they are now. Different bill types were often not distinguished (even from offerings of amendment on existing bills), and the numbering sequence often restarted with new sessions of a single Congress. There were some instances of fractional bill numbers being used to preserve bill numbering order, and there was even an instance of a bill being numbered using roman numerals!

To get around this problem, this script *creates* sane bill numbers so that ever bill has a sane, persistent identifier. The number format is roughly `XYYYYZ`, where `X` is the session, `YYYY` is the (zero-padded) bill number, and `Z` is a representation of the fraction (usually `0`, but sometimes `1` and `5`). This is stored in the bill_stable_id field. The corresponding bill type is stored in bill_type, which follows the bill type naming conventions in unitedstates/congress (only 'hr', 's', and 'sjres' types are present in this data). The triple of congress, bill type, and bill_stable_id is unique.

Not all bills have an identifiable bill number. Some records are for multiple bills, or don't actually show a bill number. No bill_stable_id or bill_type fields will be present on these records.


Generating Bill Files
---------------------

The bills.py script outputs files for each bill in the metadata, using a format compatible with output from the [unitedstates/congress](https://github.com/unitedstates/congress) project.

To run, you'll need the Congress project installed and its virtual environment activated. Then execute:

	source ../path/to/congress/virt/bin/activate
	export PYTHONPATH=../path/to/congress/tasks
	python bills.py

Files are output to the congress project's data directory using the same naming conventions as modern bills. The same example from above will be found in `data/13/bills/hr/hr200020/data.json` and looks like:

	{
	  "actions": [
		{
		  "acted_at": "1813-12-20",
		  "committee": [
			"Committee of the Whole House"
		  ],
		  "text": "Read the first and second time and committed to a committee of the whole House on Wednesday next. A Bill To authorise the Secretary of the Treasury to subscribe, in behalf of the United States, for seven hundred and fifty shares in the capital stock of the Chesapeake and Delaware Canal Company.",
		  "type": "referral"
		}
	  ],
	  "bill_id": "hr2000020-13",
	  "bill_type": "hr",
	  "chamber": "h",
	  "committees": [
		{
		  "activity": [
			"referral"
		  ],
		  "committee": "Committee of the Whole House",
		  "committee_id": null
		}
	  ],
	  "congress": 13,
	  "description": "Read the first and second time and committed to a committee of the whole House on Wednesday next. A Bill To authorise the Secretary of the Treasury to subscribe, in behalf of the United States, for seven hundred and fifty shares in the capital stock of the Chesapeake and Delaware Canal Company.",
	  "number": "2000020",
	  "official_title": "To authorise the Secretary of the Treasury to subscribe, in behalf of the United States, for seven hundred and fifty shares in the capital stock of the Chesapeake and Delaware Canal Company.",
	  "original_bill_number": "H.R. 2",
	  "session": 2,
	  "sources": [
		{
		  "collection": "llhb",
		  "source": "ammem",
		  "source_url": "http://memory.loc.gov/cgi-bin/ampage?collId=llhb&fileName=045/llhb045.db&recNum=1",
		  "volume": 45
		}
	  ],
	  "status": "REFERRED",
	  "status_at": null,
	  "titles": [
		{
		  "as": "introduced",
		  "title": "To authorise the Secretary of the Treasury to subscribe, in behalf of the United States, for seven hundred and fifty shares in the capital stock of the Chesapeake and Delaware Canal Company.",
		  "type": "official"
		}
	  ],
	  "updated_at": "2013-08-18T15:28:02-04:00",
	  "urls": {
		"gif": "http://memory.loc.gov/ll/llhb/045/0000/00020000.gif",
		"tiff": "http://memory.loc.gov/ll/llhb/045/0000/00020000.tif",
		"web": "http://memory.loc.gov/cgi-bin/ampage?collId=llhb&fileName=045/llhb045.db&recNum=1"
	  }
	}


