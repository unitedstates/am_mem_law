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

Generating Bill XML
-------------------

The bills.py script outputs files for each bill in the metadata, using a format compatible with output from the [unitedstates/congress](https://github.com/unitedstates/congress) project.

Files are output to `data/congresses/[congress]/...`, similar to what the congress project does.

In the pre-modern era of Congress, bills were not numbered as predictably as they are now. Different bill types were often not distinguished (even from offerings of amendment on existing bills), and the numbering sequence often restarted with new sessions of a single Congress. There were some instances of fractional bill numbers being used to preserve bill numbering order, and there was even an instance of a bill being numbered using roman numerals!

To get around this problem, this script *creates* sane bill numbers so that ever bill has a sane, persistent identifier. The number format is roughly `XYYYYZ`, where `X` is the session, `YYYY` is the (zero-padded) bill number, and `Z` is a representation of the fraction (usually `0`, but sometimes `5`). The original bill number as given in the original metadata is stored in the original_bill_number field.

There has been some effort made to map the old bill types to the modern bill types, but this is not always possible. In addition to the modern ones, the following bill types have been used:

* `hrcc`: A House report from the Court of Claims.
* `sr`: A Senate Resolution, a Senate Joint Resolution, or a Senate bill considered in the House.
* `unk`: The bill type is unknown.

The triple of congress, bill type, and number is unique.

