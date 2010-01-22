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

import string

class RTFException(Exception): pass

class RTFState:
	def __init__(self):
		self.uc=1
		self.ignoreGroup=0
		self.ResetFormatting()
		
	def Clone(self):
		s=RTFState()
		s.uc=self.uc
		s.ignoreGroup=self.ignoreGroup
		return s
	
	def ResetFormatting(self):
		self.bold=0
		self.italic=0
		self.size=0
		
	def GetFormatTags(self):
		tags=[]
		if self.bold:
			tags.append('b')
		if self.italic:
			tags.append('i')
		if self.size>0:
			tags.append('big')
		elif self.size<0:
			tags.append('small')			
		return tags
					
RTFIgnorable={
	# We don't bother with rtf version checks or anything
	"rtf":1,
	# As we are embedded in XML CDATA sections we don't bother with charset stuff
	"ansi":1,
	"mac":1,
	"pc":1,
	"pca":1,
	"ansicpg":1,
	# We ignore all font commands
	"deff":1,
	# We don't care about the view
	"viewkind":1,
	# We don't support positional formatting
	"li":1,
	"sb":1,
	"sa":1,
	"tx":1,
	# underline is not in our QTI profile, harsh but fair
	"ulw":1,
	}
	
class RTFParser:
	def __init__(self):
		self.ResetParser()
		
	def ResetParser(self):
		self.tokens=[]
		self.chars=[]
		self.formatTags=[]
		self.state=RTFState()
		self.stack=[]
		self.popen=0
		
	def HandleUnknown(self,name,param):
		if not RTFIgnorable.has_key(name) and not self.state.ignoreGroup:
			print "Ignoring unknown RTF Control word: %s"%name
	
	def HandleUnknownSymbol(self,symbol):
		print 'Ignoring unknown RTF Control symbol: "%s"'%symbol
		pass
	
	def Handle_uc(self,name,param):
		self.state.uc=param
	
	def Handle_u(self,name,param):
		if not self.state.ignoreGroup:
			self.chars.append(unichr(param))
			self.Consume(self.state.uc)
	
	def Handle_fonttbl(self,name,param):
		self.state.ignoreGroup=1
	
	def Handle_fcharset(self,name,param):
		if param==2:
			print "Warning: RTF content defines unsupported Symbol font, check for bad characters"
		elif param:
			print "Warning: RTF content defines unsupported fcharset, check for bad characters"
	
	def Handle_pard(self,name,param):
		# reset default paragraph properties
		pass

	def Handle_plain(self,name,param):
		# reset default character formatting
		self.state.ResetFormatting()
		self.StateChanged()
	
	def Handle_par(self,name,param):
		# End of paragraph
		self.EndString()
		if self.popen:
			self.tokens.append({'.name':'p','.type':'ETag'})
		self.tokens.append({'.name':'p','.type':'STag'})
		self.popen=1
		
	def Handle_line(self,name,param):
		# line break
		self.EndString()
		self.tokens.append({'.name':'br','.type':'EmptyElemTag'})
	
	def Handle_tab(self,name,param):
		self.chars.append('\t')
	
	def Handle_lquote(self,name,param):
		self.chars.append(unichr(0x2018))
		
	def Handle_rquote(self,name,param):
		self.chars.append(unichr(0x2019))
		
	def Handle_ldblquote(self,name,param):
		self.chars.append(unichr(0x201C))
		
	def Handle_rdblquote(self,name,param):
		self.chars.append(unichr(0x201D))
		
	def Handle_b(self,name,param):
		if param is None:
			param=1
		self.state.bold=param
		self.StateChanged()
										
	def Handle_i(self,name,param):
		if param is None:
			param=1
		self.state.italic=param
		self.StateChanged()

	def Handle_fs(self,name,param):
		# font size specification; 24 is default (units are 0.5pt)
		if param<22:
			self.state.size=-1
		elif param>26:
			self.state.size=1
		else:
			self.state.size=0
		self.StateChanged()
		
	def Handle_f(self,name,param):
		# so you want to set the font then?
		pass
	
	def Handle_lang(self,name,param):
		print "Warning: RTF language specification currently ignored (%i)"%param

	def TokenizeString(self,input):
		self.ResetParser()
		self.input=input
		self.pos=0
		self.Consume(0)
		while self.c:
			if self.ParseChar('\\'):
				if self.c.isalpha():
					# Control Word
					cword=self.ParseControlWord()
					# Horribly, we use introspection here
					getattr(self,"Handle_%s"%cword['.name'],self.HandleUnknown)(cword['.name'],cword.get('.param',None))
				else:
					# Control symbol
					cword={'.name':self.c}
					self.Consume(1)
					getattr(self,"Handle_X%2X"%ord(cword['.name']),self.HandleUnknownSymbol)(cword['.name'])					
			elif self.ParseChar('{'):
				# start of a group
				self.stack.append(self.state)
				self.state=self.state.Clone()
			elif self.ParseChar('}'):
				# end of a group
				if self.stack:
					self.state=self.stack.pop()
					self.StateChanged()
				else:
					raise RTFException('too many "}" at "%s..."'%self.input[self.pos:self.pos+8])
			else:
				if not self.state.ignoreGroup:
					self.chars.append(self.c)
				self.Consume(1)
		self.EndString()
		if self.popen:
			self.tokens.append({'.name':'p','.type':'ETag'})
		return self.tokens

	def ParseControlWord(self):
		cword={}
		name=self.ParseLetterSequence()
		cword['.name']=name
		if self.c==" ":
			self.Consume(1)
		elif self.c.isdigit() or self.c=="-":
			param=self.ParseNumber()
			if self.c==" ":
				self.Consume(1)
			cword['.param']=param
		return cword
			
	def ParseLetterSequence(self):
		name=[]
		while self.c:
			# strictly speaking these should be lower case
			# and they are supposed to be no more than 32 chars
			if self.c.isalpha():
				name.append(self.c)
				self.Consume(1)
			else:
				break
		return string.join(name,'')
		
	def ParseNumber(self):
		num=[]
		if self.c=="-":
			value=-1
			self.Consume(1)
		else:
			value=1
		while self.c:
			if self.c.isdigit():
				num.append(self.c)
				self.Consume(1)
			else:
				break
		if not num:
			raise RTFException('bad control word at "%s..."'%self.input[self.pos:self.pos+8])
		else:
			return value*int(string.join(num,''))
			
	def ParseChar (self,c):
		if self.c==c:
			self.Consume(1)
			return 1
		else:
			return 0

	def StateChanged(self):
		newFormat=self.state.GetFormatTags()
		if newFormat!=self.formatTags:
			self.EndString()
			self.formatTags=newFormat
		
	def EndString(self):
		if self.chars:
			if self.formatTags:
				for t in self.formatTags:
					self.tokens.append({'.name':t,'.type':'STag'})
			self.tokens.append(string.join(self.chars,''))
			if self.formatTags:
				self.formatTags.reverse()
				for t in self.formatTags:
					self.tokens.append({'.name':t,'.type':'ETag'})				
			self.chars=[]
			
	def Consume(self,nChars):
		self.pos+=nChars
		self.c=self.input[self.pos:self.pos+1]
		