#! /usr/bin/env python

"""Copyright (c) 2004-2008, University of Cambridge.

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
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."""


MIGRATION_VERSION="2008-06-12"

import os, sys
from stat import *
reload(sys)
sys.setdefaultencoding('utf8')

SPLASH_LOG=[
"IMS QTIv1.2 to QTIv2.1 Migration Tool, by Steve Lay",
"",
"Copyright (c) 2004 - 2008, University of Cambridge",
"GUI Code Copyright (c) 2004 - 2008, Pierre Gorissen",
"All Rights Reserved",
"See README file for licensing information",
"Version: %s"%MIGRATION_VERSION,
""
]	

HELP_TEXT=[
	"Usage: migrate.py [options] [--cpout=output directory] [input file|directory]",
	"",
	"Recognized options:",
	"  --ucvars           : force upper case variable names",
	"  --qmdextensions    : allows metadata extension fields",
	"  --lang=<language>  : set default language",
	"  --dtdloc=<path>    : set the directory containing the QTI DTD",
	"  --forcefibfloat    : force all fib's to float type",
	"  --nocomment        : suppress comments in version 2 output",
	"  --nogui            : run in batch mode only",
	"  --help             : display this message (implies --nogui)",
	"  --version          : display version information only (implies --nogui)"
	"  --overwrite		  : If the files already exist overwrite them"
	"  --pathprepend	  : A path to prepend to file references"
	"  --createerrorfiles : If a referenced file is not found create a dummy file in its place"
]


NO_GUI=0

if __name__ == '__main__':
	wd=os.path.dirname(__file__)
	sys.path.append(os.path.join(wd,"lib"))
	try:
		import imsqtiv1
	except:
		print "Problem loading extra modules in %s/lib"%wd
		print " ...error was: %s (%s)"%(str(sys.exc_info()[0]),str(sys.exc_info()[1]))
		sys.exit(1)
				
	options=imsqtiv1.QTIParserV1Options()
	fileNames=[]
	OVERWRITE=False
	for x in sys.argv[1:]:
		# check for options here
		if x[:8].lower()=="--cpout=":
			options.cpPath=os.path.abspath(x[8:])
		elif x.lower()=="--ucvars":
			options.ucVars=1
		elif x.lower()=="--qmdextensions":
			options.qmdExtensions=1
			if not options.vobject:
				SPLASH_LOG.append("Warning: qmd_author and qmd_organization support disabled")
				SPLASH_LOG.append(" ...try installing VObject.  See: http://vobject.skyhouseconsulting.com/")
		elif x.lower()=="--forcefibfloat":
			options.forceFloat=1
		elif x[:7].lower()=="--lang=":
			options.lang=x[7:]
		elif x.lower()=="--nocomment":
			options.noCmment=1
		elif x[:9].lower()=="--dtdloc=":
			options.dtdDir=os.path.abspath(x[9:])
		elif x.lower()=="--help":
			SPLASH_LOG=SPLASH_LOG+HELP_TEXT
			NO_GUI=1
		elif x.lower()=="--version":
			NO_GUI=1
			fileNames=[]
			break
		elif x.lower()=="--nogui":
			NO_GUI=1
		elif x.lower()=="--overwrite":
			OVERWRITE=1
		elif x[:14].lower()=="--pathprepend=":
			options.prepend_path = x[14:]
		elif x.lower()=="--createerrorfiles":
			options.create_error_files = 1
		else:
			fileNames.append(x)

	if not options.dtdDir:
		options.dtdDir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'schemas'))
	
	if options.cpPath and os.path.exists(options.cpPath):
		if os.path.isdir(options.cpPath):
			if OVERWRITE:
				SPLASH_LOG.append("Warning: CP Directory already exists, overwriting.")
			else:
				reply=raw_input("Warning: CP Directory already exists, overwrite? (Yes/No)>")
				if reply.lower()!="yes":
					options.cpPath=''
		else:
			SPLASH_LOG.append("Warning: --cpout points to file, ignoring")
			options.cpPath=''

	if not NO_GUI:
		try:
			import gui
		except:
			SPLASH_LOG.append("Problem loading GUI module, defaulting to command-line operation")
			SPLASH_LOG.append(" ...error was: %s (%s)"%(str(sys.exc_info()[0]),str(sys.exc_info()[1])))
			NO_GUI=1
	
	if NO_GUI:
		for line in SPLASH_LOG:
			print line
		parser=imsqtiv1.QTIParserV1(options)
		parser.ProcessFiles(os.getcwd(),fileNames)
		parser.DumpCP()
	else:
		print "Application is active..."
		print "Do not close this window because it will also close the GUI!"
		app = gui.MyApp(SPLASH_LOG,options,fileNames)
		app.MainLoop()		

	filenames=None
	parser=None
	sys.exit(0)
	
