QTI Migration Tool
------------------

This is the QTI migration tool, use is governed by the license at the bottom of
this file.

For up to date information about the migration tool and related initiatives go
to http://qtitools.caret.cam.ac.uk/ - Please direct any comments to
swl10@cam.ac.uk

Instructure Modifications
------------

This tool has been modified by Instructure. Many of the modifications conform to
the QTI 2.0 specifications, but some don't. So buyers beware!

For instructions on using this tool with Canvas see this project's wiki page:
https://github.com/instructure/QTIMigrationTool/wiki


Installation
------------

The migration tool can work either in batch mode activated from the command line
or using a graphical user interface (GUI).

* Windows

Simply download the installer program and run it.

* Mac OS X

Simply download the application disk image.  To install the application just
drag it from the mounted disk image to the Applications folder.

* Unix/Linux

Follow the source release installation instructions below.

* Installing the Source

To install the source distribution you will need a version 2 python interpreter
to be installed on your system.  Python is available as a simple installer for
most popular platforms, for more details see:

http://www.python.org/

The GUI mode requires wxPython to be installed.  wxPython is available for
Windows, Mac and Unix/Linux based systems.  The installation is straightforward
on most modern versions of these operating systems.  For details of how to
download and install it for your system see:

http://www.wxpython.org/

Finally, if you install the vobject package into your Python interpreter the
migration tool can use it to enhance the --qmdextensions option.  This tool
has been tested against version 0.6.0 of vobject, for more details, see:

http://vobject.skyhouseconsulting.com/

Once you have installed Python (and optionally, wxPython and vobject) you should
simply unpack the source distribution into the desired location in the file
system.


Running
-------

On some systems you may be able to open the migration tool directly from your
GUI just by double-clicking the "migrate.py" file.  However, the migration tool
can always be run from the command line.  On Windows machines you must use the
*DOS* command line, on MacOS X you should use the terminal.  Windows users are
advised to familiarize themselves with the instructions for running python
scripts from the DOS command line:

http://www.python.org/doc/faq/windows/#how-do-i-run-a-python-program-under-windows

To run the tool you must change to the directory in which the tool resides and
then run the migrate.py script.

By default, the tool launches in GUI mode if it can.  If you don't have wxPython
installed, or you use the --nogui option, the tool uses batch mode instead. When
running in GUI mode command line options can be used to set the initial states
of the corresponding controls.

* Batch mode

To force batch mode, pass --nogui an argument to the migrate.py command.

You pass the paths of the QTI version 1 files to process as arguments.  If you
pass the name of a directory then it is scanned recursively for QTI xml files
(which are assumed to be all files with the extension ".xml").

The tool writes some messages to the standard output, mainly to report on
progress and to flag unsupported conversion features.

By default, the migration tool just examines the version 1 items for problems
without generating an output content package.  To actually convert the items you
will need to pass it the path of a directory in which to write its output files,
this is passed as a special path prefixed with the string --cpout= (see example
below).

migrate.py --nogui MyQTIv1Items.xml --cpout=Package

This example uses batch mode to convert all the items in the XML file
MyQTIv1Items.xml and places them in a directory called Package.  In QTI version
1, a single XML document could contain many items.  In version 2.0 multiple
items are grouped together using an IMS Content Package instead.  The migration
tool generates an appropriate manifest file automatically and places it in the
output directory.

* GUI Mode

The GUI allows you to select a "Single QTIv1.2 File" or a "Full Directory" to
process.  To generate a content package you must select a directory using the
control in the "Save files to..." box.

To convert the files use the "Convert..." button.

You can control the destination of the status messages and error reports by
toggling the "Show Output Log" menu item in the "File" menu.

* Options

You can use options to tweak the behaviour of the migration tool.  Options can
be specified on the command line.  In GUI mode they are available from the
Options menu.  A full list is given below.

Once you have got a basic migration of your content, you might like to use the
--qmdextensions and --ucvars options as these usually improve the resulting
output at the risk of deviating slightly from the proper interpretatin of the
original (version 1.x) QTI specification.  Similarly, use of --lang is highly
recommended for improving the quality of the resulting metadata.


Troubleshooting
---------------

I've tried to make the migration tool as tolerant as possible so that it
produces some output for all items, even if the migration is incomplete.
However, sometimes the tool refuses to parse the input files completely and
just stops.  Have a look at the section on problems with graphical characters
(below) and do check that your input files are at least well formed XML files.

Check the comments that the tool writes at the top of each version 2 file it
generates, they sometimes contain important information about decisions made
during the migration.

If you are dissatisfied with the result of migrating your QTI data or the tool
exits with an error without generating any output *please* do send me a sample
QTI (version 1.x) file demonstrating the problem so that I can use it to improve
future versions.  It is often possible to fix migration problems quickly and to
incorporate changes for the next release so that everyone benefits.


Migration Tool Options
----------------------

--cpout=<path to package directory>
"Save files to... Select Directory" in the GUI

Used to specify an output directory for the content package to be written to.
Without this option the migration tool will only examine the version 1 files and
report problems without generating a content package.

--ucvars
"Options: Force Uppercase" in the GUI

Version 1 of the QTI specification was unclear on whether or not variable names
would be treated case sensitively or not.  From version 2.0 onwards all variable
names are treated case sensitively.  Some old content may assume that
comparisons are case-insensitive.  Watch out for errors reported in the output
like "reference to undeclared outcome" - this may indicate a case-mismatch
between references and declared variables.  The tool auto-declares missing
outcomes so these errors are not fatal but the resulting output won't work as
expected!  If you specify this option, the migration tool will force all
identifiers to upper-case before processing them.

--qmdextensions
"Options: Allow Metadata Extensions" in the GUI

Some metadata tags are in use that were not part of QTI version 1 itself.  You
can turn on support for these metadata extensions with this flag.  Specifically,
the following tags are then recognized:

	<qmd_keywords>
	<qmd_domain>        (treated as a keyword)
	<qmd_description>
	<qmd_title>
	<qmd_author>        (requires vobject support, see above)
	<qmd_organisation>  (requires vobject support, see above)

--lang=<language>
"Options: Default Language" in the GUI

This option allows you to provide a default language for items migrated by the
tool. If there is no language specified for an item then it is treated as if
<language> was specified instead.  Note that this option also affects metadata
which is read from the item tag itself in version 1 of QTI.  In fact, one of its
main purposes is to ensure that the metadata values are appropriately language
tagged when migrating them into the manifest of the content package.

--nocomment
"Options: Suppress Comment" in the GUI

The migration tool generates warning messages during conversion which it adds
to the top of each output files in the form of an XML comment immediately
following the XML declaration.  This option suppresses the generation of these
comments.

--dtdloc=<path>
"Options: Force DTD Location" in the GUI

Files that contain a SYSTEM idenifier pointing at a non-existent file will cause
the migration tool to fail.  The only ways to overcome this are (a) to put a
copy of the required DTD in the specified location, (b) remove the SYSTEM
identifier from the DOCTYPE declaration at the top of the file or (c) use the
--dtdloc option to tell the migration tool the *directory* where it can find
the DTD.

--forcefibfloat
"Options: Force Float" in the GUI

Some implementations blurred the distinction between string and numeric
variables.  As a result, some content creates fill-in-the-blank or 'fib'
questions that obtain string type values from the user that are then treated as
numbers during response processing.  There is no general fix for this in the
migration tool but the --forcefibfloat option forces all fibs to be treated as
if they had been declared as floats instead.  Only use this option if you know
that your content suffers from this problem.

--nogui

As of version 20080610 the migration tool will launch in GUI mode if wxPython is
installed.  You can force the tool to run in batch mode with this option.

--help

Print a help message (implies --nogui)

--version

Print version information (implies --nogui)


Graphic Character Problems: fixwinchars.py
------------------------------------------

Sometimes, the migration tool fails with an "Invalid Token" message, generated
by the XML parser.  These messages might be caused by the additional graphic
characters often used by Windows.  These characters, including 'smart' quotes,
are not portable between systems and cannot be included in XML files without an
appropriate XML declaration.  The source release contains a simple script to
help solve this problem. You pass it the name of a file (or files) and it will
examine them for special graphical characters.  If it finds some, it will
replace them with XML character entity references to the appropriate Unicode
characters.

BE CAREFUL: files are changed in place so only ever run this script on a copy of
your files!  For safety, fixwinchars will only process files that start with a
'<' character.

fixwinchars.py MyWindowsFile.xml

The output of the script might look like something this:

Fixing 2 chars in file: MyWindowsFile.xml
chr(0x96) -> &#x2013;
chr(0x96) -> &#x2013;

If there is nothing to be done, no output is generated.

You can force all non-ascii characters to be encoded by passing the --ascii
option, you should use this option if your file is missing the XML declaration
all together (or has been incorrectly labelled as being UTF-8):

fixwinchars.py --ascii MyWindowsFile.xml


Building the Binary Executables
-------------------------------

The source release contains all the files necessary to build the binary
executable files.

For Windows, you will need py2exe. The compile.bat file contains the command
required to trigger the build given a typical Python 2.5 installation:

python setup_migrate.py py2exe --packages encodings

The executable files are created in the dist directory. These can be packaged into
an installer using the Inno Setup tool, a suitable installation script is provided in
migrate_w32.iss.

For Mac OS, you will need to install py2app and setuptools.  You can then build
the binary application using the command:

python build.py py2app

To build the binary releases you *must* have VObject installed.

python: http://www.python.org/download/
py2exe: http://www.py2exe.org/
Inno Setup: http://www.jrsoftware.org/isinfo.php
VObject: http://vobject.skyhouseconsulting.com/

All needed tools are available for free download.

Change Log
----------


Version: 20080612

New features:

* Integrated Pierre Gorissen's GUI interface code into the source release to
speed up production of Windows (and now Mac) binary distributions.

* Added --nocomment option


Version: 20080604

Bug fix release to correct "Non-ASCII character" problem.


Version: 20080602

New features:

* Added rudimentary (but effective) support for the parsing of embedded RTF
  code in mattext

* Significantly improved parsing of embedded HTML code in mattext, including
support for HTML code with missing CDATA sections delimitters, better code to
handle omitted tags and a wider range of supported tags (including basic
tables and img elements in mattext).

* Added support for copying media files into the content package, previously
  this had to be done by hand after the migration.

* Added automated generation of QTI specific metadata in the manifest and added
support for <qtimetadata> and the following legacy tags:
	<qmd_itemtype>
	<qmd_levelofdifficulty>
	<qmd_maximumscore>
	<qmd_status>
	<qmd_toolvendor>
	<qmd_topic>

* Improved generated XML to ensure validation against latest IMS schemas.

* Relaxed various validation issues to generate warnings instead of terminating
the migration process.

* Reduced verbosity when skipping unsupported tags

* Added --ucvars option

* Added --qmdextensions option

* Added --forcefibfloag option

* Added --lang option

* Added --dtdloc option

* Bundled the related fixwinchars script with this release

Bugs fixed:

* Fixed a bug that allowed invalid identifiers to be migrated unchanged.

* Fixed a bug which occasionally caused truncation of content when processing
embedded formatting tags.

* Fixed a bug caused by the use of language tags on the top level questestinterp.

* Fixed a bug caused by the use of multiple response processing sections in a
single item


Version: 20070424

Changed the errors trapped by the XML parser to prevent the tool exiting out
when faced with badly formed input files during a batch run.


Version: 20060915

Added support for the unanswered tag to accompany my XSLT pre-processor for
converting content from the QAed authoring tool.

Changed the QTI schema location hint in the output to point to the version of
the schema published on the IMS website.


Version: 20050610

This version of the tool represents an improvement on the earlier version
distributed as a Windows executable through SURF SiX.  Though the modifications
are fairly minor.

This version is functionally identical to the one that was used at the
CETIS/LIFE project CodeBash event in Bolton, April 2005.


Acknowledgements
----------------

Thanks to Pierre Gorissen for providing the GUI code and the Windows binary
executable and installer.

Thanks to all those people who have offered me content to test the migration
process on.  In particular, thanks to all the attendees at the CETIS Code Bashes
with a special thank you to Dick Bacon for loaning me the Physical Sciences item
bank.


License
-------

Copyright (c) 2004-2008, University of Cambridge.
GUI Code Copyright (c) 2004-2008, Pierre Gorissen

All rights reserved.

Redistribution and use of this software in source and binary forms
(where applicable), with or without modification, are permitted
provided that the following conditions are met:

 *  Redistributions of source code must retain the above copyright
    notice, this list of conditions, and the following disclaimer.

 *  Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions, and the following
    disclaimer in the documentation and/or other materials provided with
    the distribution.

 *  Neither the name of the University of Cambridge, nor the names of
    any other contributors to the software, may be used to endorse or
    promote products derived from this software without specific prior
    written permission.

THIS SOFTWARE IS PROVIDED ``AS IS'', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
