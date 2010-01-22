#! /usr/bin/env python

"""Copyright (c) 2008, University of Cambridge.

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

import os, sys, string

CharFixMap={
	0x80:"&#x20AC;",
	0x82:"&#x201A;",
	0x83:"&#x192;",
	0x84:"&#x201E;",
	0x85:"&#x2026;",
	0x86:"&#x2020;",
	0x87:"&#x2021;",
	0x88:"&#x2C6;",
	0x89:"&#x2030;",
	0x8A:"&#x160;",
	0x8B:"&#x2039;",
	0x8C:"&#x152;",
	0x8E:"&#x17D;",
	0x91:"&#x2018;",
	0x92:"&#x2019;",
	0x93:"&#x201C;",
	0x94:"&#x201D;",
	0x95:"&#x2022;",
	0x96:"&#x2013;",
	0x97:"&#x2014;",
	0x98:"&#x2DC;",
	0x99:"&#x2122;",
	0x9A:"&#x161;",
	0x9B:"&#x203A;",
	0x9C:"&#x153;",
	0x9E:"&#x17E;",
	0x9F:"&#x178;",
	}
	
def FixFile(fname,asciiMode,forceMode=0):
	f=file(fname,"rb")
	header=f.read(4)
	if len(header)<4:
		# ignore very short files
		return
	if (ord(header[0]) in (0x00, 0xFE, 0xFF,0xEF)) or ord(header[1])==0:
		# File probably starts with a BOM or is in a 16-bit wide format, so skip it.
		return
	if ord(header[0])!=0x3C and not forceMode:
		return
	data=header+f.read()
	f.close()
	fix=0
	for c in data:
		if ord(c)>=0x80 and ord(c)<=0x9F:
			fix+=1
		elif asciiMode and ord(c)>=0xA0:
			fix+=1
	if not fix:
		return
	print "Fixing %i chars in file: %s"%(fix,fname)
	output=[]
	for c in data:
		cout=CharFixMap.get(ord(c),c)
		if asciiMode and c==cout and ord(c)>=0x80:
			cout="&#x%2X;"%ord(c)
		output.append(cout)
		if c!=cout:
			print "chr(0x%2X) -> %s"%(ord(c),cout)
	outStr=string.join(output,'')
	f=file(fname,"wb")
	f.write(outStr)
	f.close()
	
if __name__ == '__main__':
	fileNames=[]
	asciiMode=0
	for x in sys.argv[1:]:
		# check for options here
		if x.lower()=="--ascii":
			asciiMode=1
		else:
			fileNames.append(x)
	for f in fileNames:
		FixFile(f,asciiMode)
