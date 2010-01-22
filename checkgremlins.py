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
	
def CheckFile(fname):
	f=file(fname,"rb")
	data=f.read()
	f.close()
	pos=0
	for c in data:
		if ord(c)>=0x7F or (ord(c)<=0x1F and c not in "\r\n\t"):
			print 'Found chr(0x%2X) at after:\n%s'%(ord(c),data[pos-80:pos])
		pos+=1
	
if __name__ == '__main__':
	fileNames=[]
	for x in sys.argv[1:]:
		fileNames.append(x)
	for f in fileNames:
		print "Checking file: %s"%f
		CheckFile(f)
