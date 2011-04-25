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

import string
import htmlentitydefs

NMTOKEN_CHARS=string.ascii_letters+string.digits+"_-.:"
NMSTART_CHARS=string.ascii_letters+"_"

pchar=string.ascii_letters+string.digits+"-_.!~*':@&=+$,"
scheme_char=string.ascii_letters+string.digits+"+-."

class XMLException(Exception): pass

def XMLString (src):
	dst=""
	if src:
		for c in src:
			if c=='&':
				dst=dst+"&amp;"
			elif c=='<':
				dst=dst+"&lt;"
			elif c=='>':
				dst=dst+"&gt;"
			elif c=='"':
				dst=dst+'&quot;'
			elif ord(c)>128:
				dst=dst+"&#"+str(ord(c))+';'
			else:
				dst=dst+c
	return dst

def EncodeComment (src):
	return src.replace('--','- - ')

def RelativeURL (uri):
	test=string.split(uri,':')
	if len(test)>1:
		if not test[0][0] in string.ascii_letters:
			return 1
		for c in test[0]:
			if not c in scheme_char:
				return 1
		return 0
	return 1

def EncodePathSegment (pathSegment):
	newPathSegment=""
	warn=0
	for c in pathSegment:
		if c in pchar:
			newPathSegment=newPathSegment+c
		elif ord(c)>255:
			# should really UTF-8 this but we'll cheat for now
			warn=1
			newPathSegment=newPathSegment+"?"
		else:
			newPathSegment=newPathSegment+'%'+string.zfill(hex(ord(c))[2:],2)
	if warn:
		print "Warning: replacing unicode character in path name: "+pathSegment
	return newPathSegment

def DecodePathSegment (pathSegment):
	newPathSegment=""
	hexStr=""
	for c in pathSegment:
		if c=="%":
			hexStr="0x"
		elif hexStr:
			if c in "0123456789ABCDEFabcdef":
				hexStr=hexStr+c
			else:
				newPathSegment=newPathSegment+'%'+hexStr[2:]
				hexStr=""
		else:
			newPathSegment=newPathSegment+c
		if len(hexStr)==4:
			newPathSegment=newPathSegment+chr(eval(hexStr))
			hexStr=""
	return newPathSegment


SCHARS=[0x20,0x09,0x0D,0x0A]

class XMLParser:
	def __init__(self,entityMap=None):
		self.entityMap=entityMap
		if not self.entityMap:
			self.entityMap={
				'quot':'"',
				'apos':"'",
				'amp':'&',
				'lt':'<',
				'gt':'>',
				'nbsp':unichr(160)				
				}
		
	def TokenizeString(self,input):
		self.input=input
		self.pos=0
		self.Consume(0)
		tokens=[]
		chars=[]
		while self.c:
			if self.ParseChar('<'):
				if self.ParseChar('/'):
					tag=self.ParseETag()
				else:
					# may return '<' if no name followed
					tag=self.ParseTag()
				if chars:
					tokens.append(string.join(chars,''))
					chars=[]
				tokens.append(tag)
			elif self.ParseChar('&'):
				chars.append(self.ParseReference())
			else:
				chars.append(self.c)
				self.Consume(1)
		if chars:
			tokens.append(string.join(chars,''))
			chars=[]
		return tokens
	
	def ParseTag(self):
		tag={}
		name=self.ParseName()
		if not name:
			return '<'
		tag['.name']=name
		while 1:
			self.SkipSpace()
			if not self.c:
				raise XMLException("unexpected end of tag")
			if self.ParseChar('>'):
				tag['.type']='STag'
				break
			elif self.ParseChar('/'):
				if self.ParseChar('>'):
					tag['.type']='EmptyElemTag'
					break
				else:
					print self.input[self.pos:]
					raise XMLException("expected: end of tag")
			else:
				aName=self.ParseName()
				if not aName:
					raise XMLException("expected: Attribute")
				self.SkipSpace()
				if not self.ParseChar('='):
					raise XMLException("expected: Eq")
				self.SkipSpace()
				aValue=self.ParseAttValue()
				tag[aName]=aValue
		return tag
	
	def ParseETag(self):
		tag={}
		tag['.name']=self.ParseName()
		tag['.type']='ETag'
		self.SkipSpace()
		if not self.ParseChar('>'):
			raise XMLException("unexpected end of tag")
		return tag
		
	def ParseAttValue(self):
		delim=None
		value=[]
		if self.ParseChar('"'):
			delim='"'
		elif self.ParseChar("'"):
			delim="'"
		else:
			raise XMLException("expected: AttValue")
		while 1:
			if not self.c:
				raise XMLException("unexpected end of AttValue")
			elif self.c==delim:
				self.Consume(1)
				break
			elif self.c=='&':
				self.Consume(1)
				value.append(self.ParseReference())
			else:
				value.append(self.c)
				self.Consume(1)
		return string.join(value,'')
	
	def ParseReference (self):
		if self.ParseChar('#'):
			if self.ParseChar('x'):
				value=unichr(int(self.ParseName(1),16))
			else:
				value=unichr(int(self.ParseName(1)))
		else:
			name=self.ParseName()
			value=self.entityMap.get(name.lower(),unichr(htmlentitydefs.name2codepoint.get(name.lower(),63)))
		# forgive the lack of a semi-colon
		self.ParseChar(';')
		return value
	
	def ParseName (self,numbersAllowed=0):
		name=[]
		# Names end with a space, '>', '/>' or ';'
		while self.c:
			if ord(self.c) in SCHARS:
				break
			if self.c in "<>/;=":
				break
			if name or numbersAllowed:
				if not (self.c in NMTOKEN_CHARS or ord(self.c)>128):
					break
			else:
				if not (self.c in NMSTART_CHARS or ord(self.c)>128):
					break
			name.append(self.c)
			self.Consume(1)
		return string.join(name,'')
	
	def SkipSpace (self):
		while self.c:
			if ord(self.c) in SCHARS:
				self.Consume(1)
			else:
				break
	
	def ParseChar (self,c):
		if self.c==c:
			self.Consume(1)
			return 1
		else:
			return 0
			
	def Consume(self,nChars):
		self.pos+=nChars
		self.c=self.input[self.pos:self.pos+1]
		
		




		

