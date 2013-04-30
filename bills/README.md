American Memory
===============

Metadata for the Library of Congress's [American Memory](http://memory.loc.gov/ammem/amlaw/lawhome.html) site, curated and corrected for better sustainability and accessibility.

Metadata Contents
-----------------

We are currently maintaining metadata for the following American Memory collections:

* `llhb`: Bills in the House of Representatives (6th Congress-42nd Congress (1799-1873), excluding the 12th Congress)
* `llsb`: Bills in the Senate (15th Congress-42nd Congress (1819-1873))
* `llsr`: Senate Resolutions/Joint Resolutions (dates?)

For more information about these and other collections, see the [unitedstates/am_mem_law](https://github.com/unitedstates/am_mem_law) project.

Metadata Format
---------------

Each volume in a collection has three associated files:

* `[collection][volume].txt`: The original CSV-like file from the Library of Congress, preserved for posterity. This will only change if the upstream file changes.
* `[collection][volume].json`: An updated and corrected JSON file for easy processing. This is probably the file you want to use if you want to use the data.
* `[collection][volume].csv`: A mostly-backwards-compatible CSV file maintained for potential future upstreaming. The contents of this file should match the JSON file, so you can use it if you want.

Scripts
-------

There are a couple of scripts that help to maintain and make use of the data.

### `process_metadata.py` ###

This script is what helps to keep the data in sync when changes are made. You probably don't need to run this script in order to use the data.

But if you do need to run it, it takes the following parameters:

* `--update`: Download fresh copies of the original Library of Congress files. (This does not currently work.)
* `--clobber`: Overwrite the JSON and CSV files using the data in the Library of Congress files. (This does not currently work.)
* `--source=json|csv|txt`: Specifies which file to use as the source when regenerating the data files. The default value is `json`; a value of `txt` will also set `--clobber`.
* `--collections=llhb,llsb,llsr`: Only run the script on the specified comma-separated list of collections. The default value is `llhb,llsb,llsr`; be sure that you only specify collections that exist.
* `--volume=030`: Only run the script on a single volume. Requires `--collections` to only specify a single collection.

Files are output to `data/collecctions/[collection]/[volume]/`.

### `bills.py` ###

This script outputs files for each bill in the metadata, using a format compatible with output from the [unitedstates/congress](https://github.com/unitedstates/congress) project.

It takes a single optional argument to specify a different location for the source data. By default, the script uses the data in the location used by this project.

Files are output to `data/congresses/[congress]/`.

#### Bill Numbering ####

In the pre-modern era of Congress, bills were not numbered as predictably as they are now. Different bill types were often not distinguished (even from offerings of amendment on existing bills), and the numbering sequence often restarted with new sessions of a single Congress. There were some instances of fractional bill numbers being used to preserve bill numbering order, and there was even an instance of a bill being numbered using roman numerals!

To get around this problem, this script renumbers bills to ensure bills are kept distinct. The number format is roughly `XYYYYZ`, where `X` is the session, `YYYY` is the (zero-padded) bill number, and `Z` is a representation of the fraction (usually `0`, but sometimes `5`).

There has been some effort made to map the old bill types to the modern bill types, but this is not always possible.

In addition to the modern ones, the following bill types have been used:

* `hrcc`: A House report from the Court of Claims.
* `sr`: A Senate Resolution, a Senate Joint Resolution, or a Senate bill considered in the House.
* `unk`: The bill type is unknown.

In cases where it seems a bill should be manually investigated to determine its categorization, the bill type has been prefixed with `ammem-[collection]-[volume]-` to keep it from being mixed in with the other bills.
