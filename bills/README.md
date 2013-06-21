American Memory
===============

Metadata for the Library of Congress's [American Memory](http://memory.loc.gov/ammem/amlaw/lawhome.html) site, curated and corrected for better sustainability and accessibility.

By Gordon Hemsley (@GPHemsley) and Joshua Tauberer (@tauberer).

Collections
-----------

We are currently maintaining metadata for the following American Memory collections:

* `llhb`: Bills in the House of Representatives, 6th Congress-42nd Congress (1799-1873), excluding the 12th Congress
* `llsb`: Bills in the Senate, 16th Congress-42nd Congress (1819-1873)
* `llsr`: Senate Resolutions/Joint Resolutions, 18th Congress-42nd Congress (1823-1873), excluding the 20th and 24th Congresses

For more information about these and other collections, see the [unitedstates/am_mem_law](https://github.com/unitedstates/am_mem_law) project.

Data Format
-----------

Each collection is divided into a number of volumes. The volumes are apparently numbered according to the order
in which the Library of Congress scanned the physical volumes, which was out of chronological order.

Each volume is stored in three files:

* source/[collection][volume].txt: The original data file from the American Memory collection, with select corrections. This file looks like CSV but it is hard to parse (see process_metadata.py).
* csv/[collection][volume].csv: The same information converted into a UTF-8 encoded CSV file, with some field normalization.
* json/[collection][volume].json: The same information coverted to JSON (see notes below).

We use process_metadata.py to convert the original source file to CSV and JSON format.

Each original metadata record represents a single physical page of a document printed in the record. In the JSON
format, the pages of each document are grouped together, so the records of the JSON file are documents (not pages)
and the page information is stored in the 'pages' field inside each document.

A document could be a bill or resolution, or an amendment to a bill or resolution, or perhaps other
sorts of bill/resolution-related document. Some documents are somehow related to multiple bills.
In the JSON, the bill_numbers field is an array.

### `bills.py` ###

This script outputs files for each bill in the metadata, using a format compatible with output from the [unitedstates/congress](https://github.com/unitedstates/congress) project.

Files are output to `data/congresses/[congress]/...`, similar to what the congress project does.

#### Bill Numbering ####

In the pre-modern era of Congress, bills were not numbered as predictably as they are now. Different bill types were often not distinguished (even from offerings of amendment on existing bills), and the numbering sequence often restarted with new sessions of a single Congress. There were some instances of fractional bill numbers being used to preserve bill numbering order, and there was even an instance of a bill being numbered using roman numerals!

To get around this problem, this script renumbers bills to ensure bills are kept distinct. The number format is roughly `XYYYYZ`, where `X` is the session, `YYYY` is the (zero-padded) bill number, and `Z` is a representation of the fraction (usually `0`, but sometimes `5`).

There has been some effort made to map the old bill types to the modern bill types, but this is not always possible.

In addition to the modern ones, the following bill types have been used:

* `hrcc`: A House report from the Court of Claims.
* `sr`: A Senate Resolution, a Senate Joint Resolution, or a Senate bill considered in the House.
* `unk`: The bill type is unknown.

In cases where it seems a bill should be manually investigated to determine its categorization, the bill type has been prefixed with `ammem-[collection]-[volume]-` to keep it from being mixed in with the other bills.
