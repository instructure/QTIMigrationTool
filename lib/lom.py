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

from xmlutils import *

class LOM:
	def __init__ (self):
		self.general=None
		self.lifecycle=None
		self.educational=[]
	
	def SuggestXMLID (self):
		if self.general:
			return self.general.SuggestXMLID()
		else:
			return None
		
	def GetGeneral (self):
		if not self.general:
			self.general=LOMGeneral()
		return self.general

	def GetLifecycle (self):
		if not self.lifecycle:
			self.lifecycle=LOMLifecycle()
		return self.lifecycle

	def AddEducational (self,educational):
		self.educational.append(educational)
	
	def WriteIMSXML (self,f,ns):
		if ns:
			f.write('\n<'+ns+'lom>')
		else:
			f.write('\n<lom xmlns="http://www.imsglobal.org/xsd/imsmd_rootv1p2p1"\
			xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\
			xsi:schemaLocation="http://www.imsglobal.org/xsd/imsmd_rootv1p2p1 imsmd_rootv1p2p1.xsd">')
		if self.general:
			self.general.WriteIMSXML(f,ns)
		if self.lifecycle:
			self.lifecycle.WriteIMSXML(f,ns)
		for edu in self.educational:
			edu.WriteIMSXML(f,ns)
		f.write('\n</'+ns+'lom>')
		
class LOMGeneral:
	def __init__ (self):
		self.identifier=[]
		self.title=None
		self.description=[]
		self.keyword=[]
		
	def SuggestXMLID (self):
		idStr=None
		for id in self.identifier:
			idStr=id.SuggestXMLID()
			if idStr:
				break
		return idStr

	def AddIdentifier(self,identifier):
		self.identifier.append(identifier)
	
	def SetTitle (self,title):
		self.title=title
		
	def AddDescription (self,description):
		self.description.append(description)

	def AddKeyword (self,keyword):
		self.keyword.append(keyword)
		
	def WriteIMSXML (self,f,ns):
		f.write('\n<'+ns+'general>')
		for ident in self.identifier:
			ident.WriteIMSXML(f,ns)
		if self.title:
			f.write('\n<'+ns+'title>')
			self.title.WriteIMSXML(f,ns)
			f.write('\n</'+ns+'title>')
		for desc in self.description:
			f.write('\n<'+ns+'description>')
			desc.WriteIMSXML(f,ns)
			f.write('\n</'+ns+'description>')
		for keyword in self.keyword:
			f.write('\n<'+ns+'keyword>')
			keyword.WriteIMSXML(f,ns)
			f.write('\n</'+ns+'keyword>')
		f.write('\n</'+ns+'general>')


class LOMLifecycle:
	def __init__(self):
		self.status=None
		self.contribute=[]
		
	def SetStatus(self,source,value):
		self.status=(source,value)
	
	def AddContributor(self,contributor):
		self.contribute.append(contributor)
		
	def WriteIMSXML (self,f,ns):
		f.write('\n<'+ns+'lifecycle>')
		if self.status:
			f.write('\n<'+ns+'status>\n<'+ns+'source>')
			self.status[0].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'source>\n<'+ns+'value>')
			self.status[1].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'value>\n</'+ns+'status>')
		for c in self.contribute:
			c.WriteIMSXML(f,ns)
		f.write('\n</'+ns+'lifecycle>')

class LOMContribute:
	def __init__(self):
		self.role=None
		self.entity=[]
		self.date=None
	
	def SetRole(self,source,value):
		self.role=(source,value)
	
	def AddEntity(self,vcard):
		self.entity.append(vcard)
	
	def SetDate(self,date):
		self.date=date
	
	def WriteIMSXML (self,f,ns):
		f.write('\n<'+ns+'contribute>')
		# role
		f.write('\n<'+ns+'role>\n<'+ns+'source>')
		self.role[0].WriteIMSXML(f,ns)
		f.write('\n</'+ns+'source>\n<'+ns+'value>')
		self.role[1].WriteIMSXML(f,ns)
		f.write('\n</'+ns+'value>\n</'+ns+'role>')
		for vcard in self.entity:
			f.write('\n<'+ns+'centity><'+ns+'vcard><![CDATA['+vcard.serialize()+']]></'+ns+'vcard></'+ns+'centity>')
		assert self.date is None
		f.write('\n</'+ns+'contribute>')
		
	
class LOMEducational:
	def __init__ (self):
		self.context=[]
		self.difficulty=None
		self.description=[]

	def AddContext (self,source,value):
		self.context.append([source,value])
		
	def SetDifficulty (self,source,value):
		self.difficulty=(source,value)
		
	def AddDescription (self,description):
		self.description.append(description)

	def WriteIMSXML (self,f,ns):
		f.write('\n<'+ns+'educational>')
		for context in self.context:
			f.write('\n<'+ns+'context>\n<'+ns+'source>')
			context[0].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'source>\n<'+ns+'value>')
			context[1].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'value>\n</'+ns+'context>')			
		if self.difficulty:
			f.write('\n<'+ns+'difficulty>\n<'+ns+'source>')
			self.difficulty[0].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'source>\n<'+ns+'value>')
			self.difficulty[1].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'value>\n</'+ns+'difficulty>')		
		if self.description[:1]:
			f.write('\n<'+ns+'description>')
			self.description[0].WriteIMSXML(f,ns)
			f.write('\n</'+ns+'description>')
		f.write('\n</'+ns+'educational>')
		# Actually, although LOM stipulates a minimum limit of 10 instances,
		# the IMS MD spec can only handle a single value.  If multiple descriptions
		# are present we generate additional education elements to surround them.
		if self.description[1:]:
			for desc in self.description[1:]:
				md=LOMEducational()
				md.AddDescription(desc)
				md.WriteIMSXML(f,ns)
	

class LOMIdentifier:
	def __init__ (self,catalog,entry):
		self.catalog=catalog
		self.entry=entry

	def SuggestXMLID (self):
		idStr=""
		if self.entry:
			for c in self.entry:
				if c in NMTOKEN_CHARS and not c==':':
					idStr=idStr+c
		return idStr
				
	def WriteIMSXML (self,f,ns):
		if self.catalog:
			f.write('\n<'+ns+'catalogentry>')
			if self.catalog:
				f.write('\n\t<'+ns+'catalog>'+XMLString(self.entry)+'</'+ns+'catalog>')
			if self.entry:
				f.write('\n\t<'+ns+'entry><'+ns+'langstring>'+XMLString(self.entry)+'</'+ns+'langstring></'+ns+'entry>')
			f.write('\n</'+ns+'catalogentry>')
		else:
			f.write('\n<'+ns+'identifier>'+XMLString(self.entry)+'</'+ns+'identifier>')


class LOMLangString:
	def __init__ (self,string,lang=None):
		self.lang=lang
		self.string=string
	
	def WriteIMSXML (self,f,ns):
		f.write('\n\t<'+ns+'langstring')
		if self.lang:
			f.write(' xml:lang="'+XMLString(self.lang)+'"')
		f.write('>'+XMLString(self.string)+'</'+ns+'langstring>')

