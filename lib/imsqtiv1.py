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


MIGRATION_VERSION="Version: 2008-06-??"

from types import *
import string
import os, sys
from xml.sax import make_parser, handler, SAXParseException
import StringIO
try:
	import vobject
	GOT_VOBJECT=1
except:
	GOT_VOBJECT=0
	
RESPONSE_PREFIX="RESPONSE_"
OUTCOME_PREFIX="OUTCOME_"
FEEDBACK_PREFIX="FEEDBACK_"


from iso8601 import *
from xmlutils import *
from rtfutils import *
from lom import *
from imscp import *
from imsqti import *


# QTIParserV1Options
# ------------------
#
class QTIParserV1Options:
	def __init__(self):
		self.vobject=GOT_VOBJECT
		# settable options follow
		self.qmdExtensions=0
		self.ucVars=0
		self.forceFloat=0
		self.lang=''
		self.noComment=0
		self.dtdDir=''
		self.cpPath=''
		
		
# QTIException Class
# ------------------
#
class QTIException:
	def __init__ (self,msg,param=None):
		if param:
			self.msg=msg+": "+param
	
	def __str__(self):
		return self.msg

# Exceptions that might be expected to occurr
eUnknownElement="Unknown element"
eNoParentPackage="QTI object outside <questestinterop> element"
eInvalidStructure="QTI object in unexpected location"
eEmptyCondition="QTI <conditionvar> contained no expressions"
eUndeclaredResponse="Reference to undeclared response variable"
eUndeclaredOutcome="Reference to undeclared outcome variable"
eUnimplementedOperator="Unimplemented operator"
eDuplicateVariable="Duplicate variable name"

# Exceptions that should never happen!
assertElementOutsideRoot="Element outside root"

VIEWMAP={'administrator':'invigilator','adminauthority':'invigilator',
	'assessor':'scorer','author':'author','candidate':'candidate',
	'invigilator':'invigilator','proctor':'invigilator','psychometrician':'scorer',
	'tutor':'tutor',
	'scorer':'scorer'}


#
# QTIObjectV1
#
class QTIObjectV1:
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		
	def ParseAttributes (self,attrs):
		for aName in attrs.keys():
			if aName[:4]=='xml:':
				f=getattr(self,'SetAttribute_xml_'+aName[4:],0)
			else:
				f=getattr(self,'SetAttribute_'+aName,0)
			if f:
				f(attrs[aName])
			elif not (aName=='xmlns' or ':' in aName):
				# suppress warnings about any schema or namespace magic
				print "Unknown or unsupported attribute: "+aName

	def ReadYesNo (self,value,default):
		if value.lower()=="yes":
			return 1
		elif value.lower()=="no":
			return 0
		else:
			print 'Warning: bad value for yes/no, ignoring "'+value+'"'

	def ReadFloat (self,value,default):
		try:
			return float(value)
		except:
			print 'Warning: bad number for attribute, ignoring "'+value+'"'
			return default

	def ReadInteger (self,value,default):
		try:
			return int(value)
		except:
			print 'Warning: bad integer for attribute, ignoring "'+value+'"'
			return default

	def ReadIdentifier (self,value,prefix="ID-"):
		value=self.CheckNMTOKEN(value.strip(),prefix)
		if ":" in value:
			self.PrintWarning('Warning: removing colon from identifier "%s"'%value)
			value=value.replace(':','_')
		if "." in value:
			self.PrintWarning('Warning: removing period from identifier "%s"'%value)
			value=value.replace('.','_')
		return value
	
	def CheckNMTOKEN (self,token,prefix):
		unchecked=0
		newtoken=""
		bad=0
		for c in token:
			if not c in NMTOKEN_CHARS:
				if ord(c)<128:
					# character not allowed
					bad=1
					c="-"
				else:
					unchecked=1
			if not newtoken and not (c in NMSTART_CHARS):
				bad=1
				newtoken=prefix
			newtoken=newtoken+c
		if unchecked:
			self.PrintWarning('Warning: couldn\'t check NMTOKEN with non-ascii character(s): "%s"'%token)
		if bad:
			self.PrintWarning('Warning: replacing bad NMTOKEN "%s" with "%s"'%(token,newtoken))
		return newtoken
	
	def ReadView (self,value):
		view=value.strip().lower()
		if view!='all':
			if VIEWMAP.has_key(view):
				new_view=VIEWMAP[view]
				if new_view!=view:
					self.PrintWarning('Warning: changing '+view+' to '+new_view)
				view=new_view
			else:
				self.PrintWarning('Warning: ignoring unknown view ('+view+')')
		return view
			
	def ConvertAreaCoords (self,shape,value):
		# Code fixed up to be much more generous about use of strange separators.
		# Mixed comma and space seen in the wild!
		#coordStrs=string.split(string.join(string.split(value),''),',')
		coords=[]
		vStr=[]
		sep=0
		for c in value:
			if c in "0123456789.":
				if sep and vStr:
					coords.append(int(string.join(vStr,'')))
					sep=0
					vStr=[]
				vStr.append(c)
			else:
				sep=1
		if vStr:
			coords.append(int(string.join(vStr,'')))
		if shape=='rect':
			if len(coords)<4:
				self.PrintWarning("Error: not enough coordinates for rectangle, padding with zeros")
				while len(coords)<4:
					coords.append(0)
			coords=[coords[0],coords[1],coords[0]+coords[3]-1,coords[1]+coords[2]-1]
			self.PrintWarning("Warning: rectangle conversion assumes pixel-centred coordinates, watch out for off-by-one errors")
		elif shape=='ellipse':
			if len(coords)<4:
				self.PrintWarning("Error: not enough coordinates for ellipse, padding with zeros")
				while len(coords)<4:
					coords.append(0)
			if coords[2]==coords[3]:
				self.PrintWarning("Warning: ellipse conversion assumes pixel-centred coordinates, watch out for off-by-one errors")	
				r=coords[2]/2 # centre-pixel coordinate model again
				coords=[coords[0],coords[1],r]
				shape='circle'
			else:
				self.PrintWarning("Warning: ellipse shape is deprecated in version 2")
				coords=[coords[0],coords[1],coords[2]/2,coords[3]/2]
		return shape,coords
	
	def AddData (self,data):
		data=data.strip()
		if data:
			print "Ignoring data: "+XMLString(data)
	
	def CloseObject (self):
		pass
	
	def GetRoot (self):
		if not self.parent:
			return self
		else:
			return self.parent.GetRoot()
	
	def GetParser (self):
		return self.GetRoot().parser
		
	def GetItemV1 (self):
		assert self.parent,QTIException(eNoParentItem)
		return self.parent.GetItemV1()

	def GetMDContainer(self):
		assert self.parent,QTIException(eNoParentMDContainer)
		return self.parent.GetMDContainer()
	
	def SniffRenderHotspot (self):
		if self.parent:
			return self.parent.SniffRenderHotspot()
		else:
			return None

	def PrintWarning (self, warning, force=0):
		if not self.parent:
			print warning
		else:
			self.parent.PrintWarning(warning,force)


# Unsupported
# -----------
#
class Unsupported(QTIObjectV1):
	"""Unsupport QTI object"""
	
	def __init__(self,name,attrs,parent):
		self.parent=parent
		if not isinstance(parent,Unsupported):
			print "Unsupported element <"+name+">"

	def AddData (self,data):
		pass


# Skipped
# -------
#
class Skipped(QTIObjectV1):
	"""Skipped QTI object"""
	def __init__(self,name,attrs,parent):
		pass
		#print "Skipping element <"+name+">"

	def AddData (self,data):
		pass

		
# QuesTestInterop
# ---------------
#
class QuesTestInterop(QTIObjectV1):
	"""
	<!ELEMENT questestinterop (qticomment? , (objectbank | assessment | (section | item)+))>
	"""	
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.path=None
		self.cp=None
		self.parser=None
		self.resources=[]
		self.description=None
		
	def SetCP (self,cp):
		self.cp=cp
		
	def SetPath (self,path):
		self.path=path
	
	def SetParser (self,parser):
		self.parser=parser
		
	def SetLOMDescription (self,desc):
		self.description=desc
		
	def AddResource (self,resource):
		self.resources.append(resource)
		self.cp.AddResource(resource)
	
	def ResolveURI (self,uri):
		# The base URI of this XML file is self.path
		# resolve URI to make it a full path
		path,discard=os.path.split(self.path)
		segments=string.split(uri,'/')
		for segment in segments:
			if segment==".":
				continue
			elif segment=="..":
				path,discard=os.path.split(path)
			else:
				path=os.path.join(path,DecodePathSegment(segment))
		return path
	
	def CloseObject (self):
		if len(self.resources)==1 and self.description:
			# A description of the questestinterop object when it only contains one object is probably misplaced
			self.PrintWarning('Warning: found qticomment on a questestinterop with single item: treating as metadata for the item *not* the content package')
			self.resources[0].GetLOM().GetGeneral().AddDescription(self.description)
		elif self.description:
			self.cp.GetLOM().GetGeneral().AddDescription(self.description)
		
		
# QTIComment
# ----------
#
class QTIComment(QTIObjectV1):
	"""
	<!ELEMENT qticomment (#PCDATA)>
	
	<!ATTLIST qticomment  xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.data=""
		self.lang=None
		# appears almost everywhere, no point in checking
		QTIObjectV1.__init__(self,name,attrs,parent)
	
	def SetAttribute_xml_lang (self,lang):
		self.lang=lang

	def CloseObject (self):
		if isinstance(self.parent,QuesTestInterop):
			self.GetRoot().SetLOMDescription(LOMLangString(self.data,self.lang))
		else:
			self.PrintWarning('Warning: ignoring qticomment')
			
	def AddData (self,data):
		self.data=self.data+data	


# QTIMetadataContainer
# --------------------
#
class QTIMetadataContainer(QTIObjectV1):
	def GetMDContainer(self):
		return self
		
	def SetTitle(self,title):
		pass

	def AddKeyword(self,keyword):
		pass
	
	def AddDescription(self,description):
		pass

	def AddContributor(self,contributor):
		pass

	def SetStatus(self,source,value):
		pass
	
	def AddEducationalContext(self,context,lomValue):
		pass
		
	def AddEducationalDifficulty(self,difficulty,lomValue):
		pass

	def AddEducationalDescription (self,description):
		pass

	def SetMaximumScore(self,max):
		pass

	def SetToolVendor(self,vendor):
		pass



# QTIObjectBank
# -------------
#
class QTIObjectBank(QTIMetadataContainer):
	"""
	<!ELEMENT objectbank (qticomment? , qtimetadata* , (section | item)+)>

	<!ATTLIST objectbank  %I_Ident; >
	"""
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.PrintWarning('Warning: objectbank not supported, looking inside for items')
		
	def SetAttribute_ident (self,id):
		pass
		
	
# QTIAssessment
# -------------
#
class QTIAssessment(QTIMetadataContainer):
	"""
	<!ELEMENT assessment (qticomment? , duration? , qtimetadata* , objectives* , assessmentcontrol* , rubric* , presentation_material? , outcomes_processing* , assessproc_extension? , assessfeedback* , selection_ordering? , reference? , (sectionref | section)+)>
	
	<!ATTLIST assessment  %I_Ident;
						   %I_Title;
						   xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		#QTIObjectV1.__init__(self,name,attrs,parent)
		self.parent=parent
		self.parser=self.GetParser()
		self.assessment=AssessmentTest()
		# This is the manifest object
		self.resource=CPResource()
		self.resource.SetType("imsqti_item_xmlv2p0")
		self.educationalMetadata=None
		self.variables={'FEEDBACK':None}
		if attrs.has_key('ident'):
			print '-- Converting item id="'+attrs['ident']+'" --'
		self.warnings={}
		self.msg=""
		self.ParseAttributes(attrs)
		if not self.assessment.language and self.parser.options.lang:
			self.assessment.SetLanguage(self.parser.options.lang)
		# Set the name of the file
		cp=self.GetRoot().cp
		# Reserve space for our preferred file name
		self.fName=cp.GetUniqueFileName("assmnt_"+self.resource.id+".xml")
		self.files={}
		
	def SetAttribute_ident (self,value):
		self.assessment.SetIdentifier(value);
		self.resource.GetLOM().GetGeneral().AddIdentifier(LOMIdentifier(None,value))
		if ':' in value:
			print "Warning: assessment identifier with colon: replaced with hyphen when making resource identifier."
			value=string.join(string.split(value,':'),'-')
		self.resource.SetIdentifier(value);

	def SetAttribute_title (self,value):
		self.assessment.SetTitle(value)
	
	def SetAttribute_xml_lang (self,lang):
		self.assessment.SetLanguage(value)
		
	def GenerateQTIMetadata(self):
		qtiMD=self.resource.GetQTIMD()
		
	def SetDuration(self, duration):
		self.assessment.SetTimeLimit(duration)
	
	def CloseObject (self):
		# Fix up the title
		if self.assessment.title:
			self.resource.GetLOM().GetGeneral().SetTitle(LOMLangString(self.assessment.title,self.assessment.language))
		self.GenerateQTIMetadata()
		# Add the resource to the root thing - and therefore the content package
		self.GetRoot().AddResource(self.resource)
		# Adding a resource to a cp may cause it to change identifier, but we don't mind.
		f=StringIO.StringIO()
		f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
		if not self.parser.options.noComment:
			f.write('<!--\n')
			f.write(EncodeComment(self.msg))
			f.write('\t-->\n\n')
		self.assessment.WriteXML(f)
		cpf=CPFile()
		cpf.SetHREF(self.fName)
		cpf.SetData(f.getvalue())
		f.close()
		self.resource.AddFile(cpf,1)
	
	
# QTISection
# ----------
#
class QTISection(QTIMetadataContainer):
	"""
	<!ELEMENT section (qticomment? , duration? , qtimetadata* , objectives* , sectioncontrol* , sectionprecondition* , sectionpostcondition* , rubric* , presentation_material? , outcomes_processing* , sectionproc_extension? , sectionfeedback* , selection_ordering? , reference? , (itemref | item | sectionref | section)*)>
	
	<!ATTLIST section  %I_Ident;
			%I_Title;
			xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.parser=self.GetParser()
		self.section=AssessmentSection()
		
	def SetAttribute_ident (self,value):
		self.section.SetIdentifier(value);
		self.resource.GetLOM().GetGeneral().AddIdentifier(LOMIdentifier(None,value))
		if ':' in value:
			print "Warning: assessment identifier with colon: replaced with hyphen when making resource identifier."
			value=string.join(string.split(value,':'),'-')
		self.resource.SetIdentifier(value);

	def SetAttribute_title (self,value):
		self.section.SetTitle(value)
	
	def GenerateQTIMetadata(self):
		qtiMD=self.resource.GetQTIMD()
	
	def SetDuration(self, duration):
		#todo: if it's a testPart it can be set...
		pass

			
# QTIItem
# -------
#
class QTIItem(QTIMetadataContainer):
	"""
	<!ELEMENT item (qticomment? , duration? , itemmetadata? , objectives* , itemcontrol* , itemprecondition* , itempostcondition* , (itemrubric | rubric)* , presentation? , resprocessing* , itemproc_extension? , itemfeedback* , reference?)>

	<!ATTLIST item  maxattempts CDATA  #IMPLIED
                 %I_Label;
                 %I_Ident;
                 %I_Title;
                 xml:lang    CDATA  #IMPLIED >
	""" 

	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.parser=self.GetParser()
		self.item=AssessmentItem()
		self.resource=CPResource()
		self.resource.SetType("imsqti_item_xmlv2p0")
		self.educationalMetadata=None
		self.variables={'FEEDBACK':None}
		self.declareFeedback=0
		self.responses={}
		self.outcomes={}
		self.max=None
		self.interactions={}
		if attrs.has_key('ident'):
			print '-- Converting item id="'+attrs['ident']+'" --'
		self.warnings={}
		self.msg=""
		self.ParseAttributes(attrs)
		if not self.item.language and self.parser.options.lang:
			self.item.SetLanguage(self.parser.options.lang)
		# Set the name of the file
		cp=self.GetRoot().cp
		# Reserve space for our preferred file name
		self.fName=cp.GetUniqueFileName(self.resource.id+".xml")
		self.files={}
	
	def SetAttribute_maxattempts (self,value):
		self.PrintWarning("Warning: maxattempts can not be controlled at item level, ignored: maxattempts='"+value+"'")
		self.PrintWarning("Note: in future, maxattempts will probably be controllable at assessment or assessment section level")

	def SetAttribute_label (self,value):
		self.item.SetLabel(value)
	
	def SetAttribute_ident (self,value):
		self.item.SetIdentifier(value);
		self.resource.GetLOM().GetGeneral().AddIdentifier(LOMIdentifier(None,value))
		if ':' in value:
			print "Warning: item identifier with colon: replaced with hyphen when making resource identifier."
			value=string.join(string.split(value,':'),'-')
		self.resource.SetIdentifier(value);

	def SetAttribute_title (self,value):
		self.item.SetTitle(value)
	
	def SetAttribute_xml_lang (self,lang):
		self.item.SetLanguage(value)

	def GetItemV1 (self):
		return self
		
	def UniqueVarName (self,base):
		trynum=1
		while 1:
			tryname=base+string.zfill(trynum,2)
			if self.variables.has_key(tryname):
				trynum=trynum+1
				if trynum>99:
					raise QTIException(eTooManySimilarVariables,base)
			else:
				return tryname
	
	def DeclareResponse (self,identifier,cardinality,baseType,default=None):
		if self.responses.has_key(identifier):
			raise QTIException(eDuplicateResponse,identifier)
		if self.variables.has_key(identifier):
			self.PrintWarning('Warning: duplicate variable name, renaming response "'+identifier+'"')
			self.responses[identifier]=self.UniqueVarName(identifier)
		else:
			self.responses[identifier]=identifier
		declaration=ResponseDeclaration(self.responses[identifier],cardinality,baseType)
		if default:
			declaration.SetDefaultValue(DefaultValue(str(default)))
		self.item.DeclareVariable(declaration)
		self.variables[self.responses[identifier]]=declaration
		return self.responses[identifier]
		
	def DeclareFakeResponse (self,identifier,cardinality,baseType):
		if self.responses.has_key(identifier):
			raise QTIException(eDuplicateResponse,identifier)
		if self.variables.has_key(identifier):
			self.PrintWarning('Warning: duplicate variable name, renaming response "'+identifier+'"')
			self.responses[identifier]=self.UniqueVarName(identifier)
		else:
			self.responses[identifier]=identifier
		declaration=OutcomeDeclaration(self.responses[identifier],cardinality,baseType)
		self.item.DeclareVariable(declaration)
		self.variables[self.responses[identifier]]=declaration
		return self.responses[identifier]
		
	def GetResponse (self,identifier):
		if self.responses.has_key(identifier):
			return self.variables[self.responses[identifier]]
		else:
			return None

	def BindResponse (self,interaction,identifier):
		responseID=self.GetResponse(identifier).GetIdentifier()
		interaction.BindResponse(responseID)
		self.interactions[responseID]=interaction

	def GetInteraction (self,identifier):
		response=self.GetResponse(identifier)
		if response:
			responseID=response.GetIdentifier()
			if self.interactions.has_key(responseID):
				return self.interactions[responseID]
			else:
				raise QTIException(eUnboundResponse,identifier)
		else:
			return None	

	def GenerateQTIMetadata(self):
		qtiMD=self.resource.GetQTIMD()
		qtiMD.SetItemTemplate(0)
		qtiMD.SetComposite(len(self.responses.keys())>1)
		for interaction in self.interactions.values():
			if isinstance(interaction,ChoiceInteraction):
				qtiMD.AddInteractionType("choiceInteraction")
			elif isinstance(interaction,OrderInteraction):
				qtiMD.AddInteractionType("orderInteraction")
			elif isinstance(interaction,AssociateInteraction):
				qtiMD.AddInteractionType("associateInteraction")
			elif isinstance(interaction,ExtendedTextInteraction):
				qtiMD.AddInteractionType("extendedTextInteraction")
			elif isinstance(interaction,TextEntryInteraction):
				qtiMD.AddInteractionType("textEntryInteraction")
			elif isinstance(interaction,HotspotInteraction):
				qtiMD.AddInteractionType("hotspotInteraction")
			elif isinstance(interaction,SelectPointInteraction):
				qtiMD.AddInteractionType("selectPointInteraction")
			elif isinstance(interaction,GraphicOrderInteraction):
				qtiMD.AddInteractionType("graphicOrderInteraction")
			elif isinstance(interaction,SliderInteraction):
				qtiMD.AddInteractionType("sliderInteraction")
			else:
				print 'Warning: unexpected interaction type (whoops): %s!'%repr(interaction)
		if self.item.HasModalFeedback():
			qtiMD.SetFeedbackType('nonadaptive')
		else:
			qtiMD.SetFeedbackType('none')
			
	# Methods used in resprocessing
	
	def ResetResprocessing (self):
		if self.outcomes:
			self.PrintWarning("Warning: multiople <resprocessing> not supported, ignoring all but the last")
		self.item.ResetResponseProcessing()
		for outcome in self.outcomes.keys():
			print "Dropping outcome %s"%outcome
			del self.variables[self.outcomes[outcome]]
			del self.outcomes[outcome]
			
	def DeclareOutcome (self,decvar):
		if self.outcomes.has_key(decvar.identifier):
			raise QTIException(eDuplicateVariable,decvar.identifier)
		if self.variables.has_key(decvar.identifier):
			print 'Warning: duplicate variable name, renaming outcome "'+decvar.identifier+'"'
			self.outcomes[decvar.identifier]=self.UniqueVarName(decvar.identifier)
		else:
			self.outcomes[decvar.identifier]=decvar.identifier
		declaration=OutcomeDeclaration(self.outcomes[decvar.identifier],'single',decvar.baseType)
		if decvar.default:
			declaration.SetDefaultValue(DefaultValue(decvar.default))
		self.item.DeclareVariable(declaration)
		self.variables[self.outcomes[decvar.identifier]]=(declaration,decvar)

	def DeclareFeedback (self):
		if not self.declareFeedback:
			self.item.DeclareVariable(OutcomeDeclaration('FEEDBACK','multiple','identifier'))
			self.declareFeedback=1
		
	def GetOutcome (self,identifier):
		if self.outcomes.has_key(identifier):
			return self.variables[self.outcomes[identifier]][0]
		else:
			self.PrintWarning('Warning: reference to undeclared outcome, auto-declaring "%s" as type float'%identifier)
			if self.variables.has_key(identifier):
				print 'Warning: duplicate variable name, renaming outcome "'+identifier+'"'
				self.outcomes[identifier]=self.UniqueVarName(identifier)
			else:
				self.outcomes[identifier]=identifier
			declaration=OutcomeDeclaration(self.outcomes[identifier],'single','float')
			self.item.DeclareVariable(declaration)
			self.variables[self.outcomes[identifier]]=(declaration,None)
			return declaration
	
	def AddDescription(self,description):
		self.resource.GetLOM().GetGeneral().AddDescription(LOMLangString(description,self.item.language))
		
	def SetTitle(self,title):
		if self.item.title:
			# If the item has a title, we have to use it in the metadata
			self.AddDescription(title)
		else:
			self.resource.GetLOM().GetGeneral().SetTitle(LOMLangString(title,self.item.language))
		
	def AddEducationalDescription (self,description):
		if not self.educationalMetadata:
			self.educationalMetadata=LOMEducational()
		self.educationalMetadata.AddDescription(LOMLangString(description,self.item.language))

	def AddEducationalContext(self,context,lomValue):
		value=LOMLangString(context,"x-none")
		if lomValue:
			source=LOMLangString("LOMv1.0","x-none")
		else:
			source=LOMLangString("None","x-none")
		if not self.educationalMetadata:
			self.educationalMetadata=LOMEducational()
		self.educationalMetadata.AddContext(source,value)

	def AddEducationalDifficulty(self,difficulty,lomValue):
		value=LOMLangString(difficulty,"x-none")
		if lomValue:
			source=LOMLangString("LOMv1.0","x-none")
		else:
			source=LOMLangString("None","x-none")
		if not self.educationalMetadata:
			self.educationalMetadata=LOMEducational()
		self.educationalMetadata.SetDifficulty(source,value)
		
	def SetMaximumScore(self,max):
		self.max=max

	def AddKeyword(self,keyword):
		self.resource.GetLOM().GetGeneral().AddKeyword(LOMLangString(keyword,self.item.language))

	def SetToolVendor(self,vendor):
		self.resource.GetQTIMD().SetToolVendor(vendor)
		
	def SetDuration(self, duration):
		#todo: add comment warning
		pass
		
	def SetStatus(self,source,value):
		source=LOMLangString(source,'x-none')
		value=LOMLangString(value,'x-none')
		self.resource.GetLOM().GetLifecycle().SetStatus(source,value)
		
	def AddContributor(self,contributor):
		self.resource.GetLOM().GetLifecycle().AddContributor(contributor)
	
	def AddCPFile (self,uri):
		if self.files.has_key(uri):
			# We've already added this file to the content package
			return self.files[uri]
		cpf=CPFile()
		if RelativeURL(uri):
			root=self.GetRoot()
			path=root.ResolveURI(uri)
			# find the last path component
			dName,fName=os.path.split(path)
			# Use this file name in the content package
			fName=root.cp.GetUniqueFileName(fName)
			cpLocation=EncodePathSegment(fName)
			# But, what about the data!!
			cpf.SetDataPath(path)
		else:
			cpLocation=uri
		cpf.SetHREF(cpLocation)
		self.resource.AddFile(cpf,0)
		self.files[uri]=cpLocation
		return cpLocation

	def CloseObject (self):
		# Check devvar min/max constraints
		rp=self.item.GetResponseProcessing()
		for outcome in self.outcomes.keys():
			declaration,decvar=self.variables[self.outcomes[outcome]]
			if decvar and decvar.min:
				condition=ResponseCondition()
				ifTest=condition.GetResponseIf()
				var=VariableOperator(declaration.GetIdentifier())
				if decvar.baseType=='integer':
					val1=BaseValueOperator('integer',str(int(decvar.min)))
					val2=BaseValueOperator('integer',str(int(decvar.min)))
				else:
					val1=BaseValueOperator('float',str(decvar.min))
					val2=BaseValueOperator('float',str(decvar.min))
				ifTest.SetExpression(LTOperator(var,val1))
				ifTest.AddResponseRule(SetOutcomeValue(declaration.GetIdentifier(),val2))
				rp.AddResponseRule(condition)			
			if decvar and decvar.max:
				condition=ResponseCondition()
				ifTest=condition.GetResponseIf()
				var=VariableOperator(declaration.GetIdentifier())
				if decvar.baseType=='integer':
					val1=BaseValueOperator('integer',str(int(decvar.max)))
					val2=BaseValueOperator('integer',str(int(decvar.max)))
				else:
					val1=BaseValueOperator('float',str(decvar.max))
					val2=BaseValueOperator('float',str(decvar.max))
				ifTest.SetExpression(GTOperator(var,val1))
				ifTest.AddResponseRule(SetOutcomeValue(declaration.GetIdentifier(),val2))
				rp.AddResponseRule(condition)
		# Check maximum score
		if self.max:
			if len(self.outcomes.keys())!=1:
				self.PrintWarning("Warning: qmd_maximumscore ignored for %s, multiple (or zero) outcomes declared"%self.item.identifier)
			else:
				declaration,decvar=self.variables[self.outcomes.values()[0]]
				declaration.SetNormalMaximum(self.max)
		# If we defined educational metadata, it needs to be added to the resource now
		if self.educationalMetadata:
			self.resource.GetLOM().AddEducational(self.educationalMetadata)
		# Fix up the title
		if self.item.title:
			self.resource.GetLOM().GetGeneral().SetTitle(LOMLangString(self.item.title,self.item.language))
		self.GenerateQTIMetadata()
		# Add the resource to the root thing - and therefore the content package
		self.GetRoot().AddResource(self.resource)
		# Adding a resource to a cp may cause it to change identifier, but we don't mind.
		f=StringIO.StringIO()
		f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
		if not self.parser.options.noComment:
			f.write('<!--\n')
			f.write(EncodeComment(self.msg))
			f.write('\t-->\n\n')
		self.item.WriteXML(f)
		cpf=CPFile()
		cpf.SetHREF(self.fName)
		cpf.SetData(f.getvalue())
		f.close()
		self.resource.AddFile(cpf,1)
		
	def PrintWarning (self,warning,force=0):
		if not self.warnings.has_key(warning):
			self.msg=self.msg+warning+'\n'
			self.warnings[warning]=1
		if force:
			self.parent.PrintWarning(warning,1)


# ItemMetadata
# ------------
#
class ItemMetadata(QTIObjectV1):
	"""
	<!ELEMENT itemmetadata (qtimetadata* , qmd_computerscored? , qmd_feedbackpermitted? , qmd_hintspermitted? , qmd_itemtype? , qmd_levelofdifficulty? , qmd_maximumscore? , qmd_renderingtype* , qmd_responsetype* , qmd_scoringpermitted? , qmd_solutionspermitted? , qmd_status? , qmd_timedependence? , qmd_timelimit? , qmd_toolvendor? , qmd_topic? , qmd_weighting? , qmd_material* , qmd_typeofsolution?)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		# item
		assert isinstance(self.parent,QTIItem),QTIException(eInvalidStructure,"<itemmetadata>")


# QTIMetadata
# -----------
#
class QTIMetadata(QTIObjectV1):
	"""
	<!ELEMENT qtimetadata (vocabulary? , qtimetadatafield+)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		# itemmetadata, assessment, section, objectbank
		assert isinstance(self.parent,(ItemMetadata,QTIObjectBank,QTIAssessment,QTISection)),QTIException(eInvalidStructure,"<qtimetadata>")


# Vocabulary
# ----------
#
class Vocabulary(QTIObjectV1):
	"""
	<!ELEMENT vocabulary (#PCDATA)>
	
	<!ATTLIST vocabulary  %I_Uri;
						   %I_EntityRef;
						   vocab_type  CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.uri=None
		self.entityRef=None
		self.vocabType=None
		# qtimetadata
		assert isinstance(self.parent,QTIMetadata),QTIException(eInvalidStructure,"<vocabulary>")
		self.ParseAttributes(attrs)
		self.PrintWarning("Warning: qtimetadata vocabulary is ignored")
		
	def SetAttribute_uri (self,value):
		self.uri=value
	
	def SetAttribute_entityref (self,value):
		self.entityRef=value
		
	def SetAttribute_vocab_type (self,value):
		self.vocabType=value
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		pass
	
	
# QMDMaximumscore
# ---------------
#
class QMDMaximumscore(QTIObjectV1):
	"""
	<!ELEMENT qmd_maximumscore (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_maximumscore>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.ReadFloat(self.data.strip(),None)
		if self.data is not None:
			self.GetMDContainer().SetMaximumScore(self.data)


# QMDLevelOfDifficulty
# --------------------
#
QMDLevelOfDifficultyMap={
	"pre-school":("pre-school",0), # value is outside LOM defined vocab
	"school":("school",1),
	"he/fe":("higher education",1),
	"vocational":("vocational",0), # value is outside LOM defined vocab
	"professional development":("training",1)
	}

QMDDifficultyMap={
	"very easy":1,
	"easy":1,
	"medium":1,
	"difficult":1,
	"very difficult":1
	}
	
class QMDLevelOfDifficulty(QTIObjectV1):
	"""
	<!ELEMENT qmd_levelofdifficulty (#PCDATA)>
	
	IMS Definition says: The options are: "Pre-school", "School" or "HE/FE", "Vocational" and "Professional Development"
	so we bind this value to the "Context" in LOM if one of the QTI or LOM defined terms have been used, otherwise,
	we bind to Difficulty, as this seems to be more common usage.
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_levelofdifficulty>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip().lower()
		if self.data is not None:
			value=QMDLevelOfDifficultyMap.get(self.data,None)
			if value:
				self.GetMDContainer().AddEducationalContext(value[0],value[1])
			else:				
				self.GetMDContainer().AddEducationalDifficulty(self.data,QMDDifficultyMap.has_key(self.data))


# QMDKeywords
# -----------
#
class QMDKeywords(QTIObjectV1):
	"""
	Not defined by QTI v1
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_keywords>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=string.split(self.data,',')
		for keyword in self.data:
			k=keyword.strip()
			if k:
				self.GetMDContainer().AddKeyword(k)


# QMDDomain
# ---------
#
class QMDDomain(QTIObjectV1):
	"""
	Not defined by QTI v1
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_domain>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Warning: qmd_domain extension field will be added as LOM keyword")
			self.GetMDContainer().AddKeyword(self.data)


# QMDTopic
# --------
#
class QMDTopic(QTIObjectV1):
	"""
	<!ELEMENT qmd_topic (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_topic>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.GetMDContainer().AddEducationalDescription(self.data)


# QMDDescription
# --------------
#
class QMDDescription(QTIObjectV1):
	"""
	Not defined by QTI v1
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_description>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.GetMDContainer().AddDescription(self.data)


# QMDTitle
# --------
#
class QMDTitle(QTIObjectV1):
	"""
	Not defined by QTI v1
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_title>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.GetMDContainer().SetTitle(self.data)


# QMDContributor
# --------------
#
LOMContributorMap={
	'author':'author',
	'creator':'initiator',
	'owner':'publisher',
	}
class QMDContributor(QTIObjectV1):
	"""
	Not defined by QTI v1
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		if name[:4]=='qmd_':
			self.role=name[4:]
		else:
			self.role=name
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_author>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		if self.GetParser().options.vobject:				
			names=self.data.strip().split(',')
			if names:
				contributor=LOMContribute()
				if LOMContributorMap.has_key(self.role):
					contributor.SetRole(LOMLangString("LOMv1.0","x-none"),LOMLangString(self.role,"x-none"))
				else:
					contributor.SetRole(LOMLangString("None","x-none"),LOMLangString(self.role,"x-none"))
				for name in names:
					if not name.strip():
						continue
					vcard=vobject.vCard()
					vcard.add('n')
					vcard.n.value=vobject.vcard.Name(family=name,given='')
					vcard.add('fn')
					vcard.fn.value=name
					contributor.AddEntity(vcard)
				self.GetMDContainer().AddContributor(contributor)
		else:
			self.PrintWarning('Warning: qmd_%s support disabled'%self.role,1)
			self.PrintWarning('Warning: ignored qmd_%s value: %s'%(self.role,self.data))


# QMDOrganisation
# ---------------
#
class QMDOrganisation(QTIObjectV1):
	"""
	Not defined by QTI v1
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_organisation>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		if self.GetParser().options.vobject:
			name=self.data.strip()
			contributor=LOMContribute()
			contributor.SetRole(LOMLangString("LOMv1.0","x-none"),LOMLangString("unknown","x-none"))
			vcard=vobject.vCard()
			vcard.add('n')
			vcard.n.value=vobject.vcard.Name(family=name,given='')
			vcard.add('fn')
			vcard.fn.value=name
			vcard.add('org')
			vcard.org.value=[name]
			contributor.AddEntity(vcard)
			self.GetMDContainer().AddContributor(contributor)
		else:
			self.PrintWarning('Warning: qmd_organisation support disabled',1)
			self.PrintWarning('Warning: ignored qmd_organisation value: %s'%self.data)



# QMDToolVendor
# -------------
#
class QMDToolVendor(QTIObjectV1):
	"""
	<!ELEMENT qmd_toolvendor (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_toolvendor>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.GetMDContainer().SetToolVendor(self.data)


# QMDStatus
# ---------
#
QMDStatusMap={
	'draft':'LOMv1.0',
	'final':'LOMv1.0',
	'revised':'LOMv1.0',
	'unavailable':'LOMv1.0',
	'experimental':'QTIv1',
	'normal':'QTIv1',
	'retired':'QTIv1'
	}
	
class QMDStatus(QTIObjectV1):
	"""
	<!ELEMENT qmd_status (#PCDATA)>
	
	Specification says: "Experimental", "Normal" or "Retired"
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_status>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			source=QMDStatusMap.get(self.data.lower(),"None")
			self.GetMDContainer().SetStatus(source,self.data)


# QMDItemType
# -----------
#	
class QMDItemType(QTIObjectV1):
	"""
	<!ELEMENT qmd_itemtype (#PCDATA)>
	Specification says: "Logical Identifier", "XY co-ordinate", "String", "Numerical" and "Logical Group"
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# itemmetadata
		assert isinstance(self.parent,(ItemMetadata,QTIMetadataField)),QTIException(eInvalidStructure,"<qmd_itemtype>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Warning: qmd_itemtype now replaced by qtiMetadata.interactionType in manifest")


# QTIMetadataField
# ----------------
#
# qmd_computerscored
# qmd_feedbackpermitted
# qmd_hintspermitted
# qmd_itemtype
# qmd_levelofdifficulty
# qmd_maximumscore
# qmd_renderingtype
# qmd_responsetype
# qmd_scoringpermitted
# qmd_solutionspermitted
# qmd_status
# qmd_timedependence
# qmd_timelimit
# qmd_toolvendor
# qmd_topic
# qmd_weighting
# qmd_material
# qmd_typeofsolution 
#
MDFieldMap={
	'maximumscore':QMDMaximumscore,
	'marks':QMDMaximumscore,
	'name':QMDTitle,
	'syllabusarea':QMDTopic,
	'author':QMDContributor,
	'creator':QMDContributor,
	'owner':QMDContributor,
	'itemtype':QMDItemType,
	'item type':QMDItemType,
	'question type':QMDItemType,
	'status':QMDStatus,
	'layoutstatus':QMDStatus,
	}
class QTIMetadataField(QTIObjectV1):
	"""
	<!ELEMENT qtimetadatafield (fieldlabel , fieldentry)>
	
	<!ATTLIST qtimetadatafield  xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.lang=None
		self.label=None
		self.entry=None
		assert isinstance(self.parent,QTIMetadata),QTIException(eInvalidStructure,"<qtimetadatafield>")
		self.ParseAttributes(attrs)

	def SetAttribute_xml_lang (self,value):
		self.lang=value

	def SetLabel(self,value):
		self.label=value.lower()
		if self.label[:4]=="qmd_":
			self.label=self.label[4:]

	def SetEntry(self,value):
		self.entry=value
	
	def CloseObject (self):
		if MDFieldMap.has_key(self.label):
			mdf=MDFieldMap[self.label](self.label,{},self)
			mdf.AddData(self.entry)
			mdf.CloseObject()
		else:
			self.PrintWarning("Unmapped metadata field: %s=%s"%(self.label,self.entry),1)
		

# FieldLabel
# ----------
#
class FieldLabel(QTIObjectV1):
	"""
	<!ELEMENT fieldlabel (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		assert isinstance(self.parent,QTIMetadataField),QTIException(eInvalidStructure,"<fieldlabel>")
		self.data=""
	
	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.parent.SetLabel(self.data.strip())


# FieldEntry
# ----------
#
class FieldEntry(QTIObjectV1):
	"""
	<!ELEMENT fieldentry (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		assert isinstance(self.parent,QTIMetadataField),QTIException(eInvalidStructure,"<fieldentry>")
		self.data=""
	
	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.parent.SetEntry(self.data.strip())
	

# Duration
# --------
#
class Duration(QTIObjectV1):
	"""
	<!ELEMENT duration (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		# assessment, section, item
		assert isinstance(self.parent,(QTIItem,QTIAssessment,QTISection)),QTIException(eInvalidStructure,"<duration>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.SetDuration(self.data)

				
# ItemControl
# -----------
#
class ItemControl(QTIObjectV1):
	"""
	<!ELEMENT itemcontrol (qticomment?)>
	
	<!ATTLIST itemcontrol  %I_FeedbackSwitch;
							%I_HintSwitch;
							%I_SolutionSwitch;
							%I_View; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		# item
		assert isinstance(self.parent,QTIItem),QTIException(eInvalidStructure,"<itemcontrol>")
		self.PrintWarning("Warning: itemcontrol is currently outside the scope of version 2")

				
# Presentation
# ------------
#
class Presentation(QTIObjectV1):
	"""
	<!ELEMENT presentation (qticomment? , (flow | (material | response_lid | response_xy | response_str | response_num | response_grp | response_extension)+))>
	
	<!ATTLIST presentation  %I_Label;
							 xml:lang CDATA  #IMPLIED
							 %I_Y0;
							 %I_X0;
							 %I_Width;
							 %I_Height; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		assert isinstance(self.parent,QTIItem),QTIException(eInvalidStructure,"<presentation>")
		self.body=self.parent.item.GetItemBody()
		self.ParseAttributes(attrs)
		
	def SetAttribute_label (self,value):
		self.body.SetLabel(value)
		
	def SetAttribute_xml_lang (self,value):
		self.body.SetLanguage(value)

	def SetAttribute_y0 (self,value):
		self.PrintWarning("Warning: discarding y0 coordinate on presentation")
								
	def SetAttribute_x0 (self,value):
		self.PrintWarning("Warning: discarding x0 coordinate on presentation")

	def SetAttribute_width (self,value):
		self.PrintWarning("Warning: discarding width on presentation")

	def SetAttribute_height (self,value):
		self.PrintWarning("Warning: discarding height coordinate on presentation")

	def GetFlowLevel (self):
		return 0
	
	def AppendElement (self,element):
		if isinstance(element,Block):
			self.body.AppendBlock(element)


# Rubric
# ------
#
class Rubric(QTIObjectV1):
	"""
	<!ELEMENT rubric (qticomment? , (material+ | flow_mat+))>
	
	<!ATTLIST rubric  %I_View; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.view='all'
		# assessment, section, item
		assert isinstance(self.parent,(QTIItem,QTIAssessment,QTISection)),QTIException(eInvalidStructure,"<rubric>")
		self.ParseAttributes(attrs)
		if self.view=='all':
			self.PrintWarning('Warning: rubric with view="all" replaced by <div> with class="rubric"')
			self.rubric=xhtml_div()
			self.rubric.SetClass('rubric')
		else:
			self.rubric=RubricBlock()
			self.rubric.AppendView(self.view)
			
	def SetAttribute_view (self,value):
		self.view=self.ReadView(value)
	
	def GetFlowLevel (self):
		return 0
	
	def AppendElement (self,element):
		if isinstance(element,Block):
			self.rubric.AppendElement(element)
	
	def CloseObject (self):
		if isinstance(self.parent,QTIItem):
			self.parent.item.GetItemBody().AppendBlock(self.rubric)
		else:
			self.PrintWarning("Warning: ignoring assessment or section rubric")
	

# Objectives
# ----------
#
class Objectives(QTIObjectV1):
	"""
	<!ELEMENT objectives (qticomment? , (material+ | flow_mat+))>
	
	<!ATTLIST objectives  %I_View; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		# assessment, section, item
		assert isinstance(self.parent,(QTIItem,QTIAssessment,QTISection)),QTIException(eInvalidStructure,"<objectives>")
		self.objectives=[]
		self.rubric=None
		self.view='all'
		self.ParseAttributes(attrs)
		if self.view!='all':
			self.PrintWarning('Warning: objectives are now metadata, converting to rubric for view="'+self.view+'"')
			self.rubric=RubricBlock()
			self.rubric.AppendView(self.view)

	def SetAttribute_view (self,value):
		self.view=self.ReadView(value)
			
	def GetFlowLevel (self):
		return 0
	
	def AppendElement (self,element):
		if isinstance(element,Block):
			if self.rubric:
				self.rubric.AppendElement(element)
			else:
				self.objectives.append(element)
	
	def CloseObject (self):
		if isinstance(self.parent,QTIItem):
			if self.rubric:
				self.parent.item.GetItemBody().AppendBlock(self.rubric)
			else:
				objectivesStr=""
				for objective in self.objectives:
					objectivesStr=objectivesStr+objective.ExtractText()
				self.GetMDContainer().AddEducationalDescription(objectivesStr)
		else:
			self.PrintWarning("Warning: ignoring assessment or section objectives")
			

# FlowV1
# ------
#
class FlowV1(QTIObjectV1):
	"""
	<!ELEMENT flow (qticomment? , (flow | material | material_ref | response_lid | response_xy | response_str | response_num | response_grp | response_extension)+)>
	
	<!ATTLIST flow  %I_Class; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.flowclass=None
		assert isinstance(self.parent,(FlowV1,Presentation)),QTIException(eInvalidStructure,"<flow>")
		self.ParseAttributes(attrs)
		if isinstance(self.parent,FlowV1):
			self.flow_level=parent.GetFlowLevel()+1
		else:
			self.flow_level=0
		self.children=[]
		
	def SetAttribute_class (self,value):
		self.flowclass=value

	def AppendElement (self,element):
		self.children.append(element)
	
	def GetFlowLevel (self):
		return self.flow_level
	
	def CloseObject (self):
		pFlag=1
		for child in self.children:
			if not isinstance(child,Inline):
				pFlag=0
				break
		if pFlag:
			# All our children are inline, so we can be a simple <p>
			element=xhtml_p()
			if self.flowclass and self.flowclass.lower()!='block':
				element.SetClass(self.flowclass)
			for child in self.children:
				element.AppendElement(child)
			self.parent.AppendElement(element)
		else:
			divFlag=1
			if self.flowclass and self.flowclass.lower()!='block':
				element=xhtml_div()
				element.SetClass(self.flowclass)
			elif self.flow_level:
				element=xhtml_div()
				element.SetClass("flow_"+str(self.flow_level))
			else:
				element=self.parent
				divFlag=0
			# Complex content, group inlines into paragraphs
			p=None
			for child in self.children:
				if isinstance(child,Inline):
					if not p:
						p=xhtml_p()
					p.AppendElement(child)
				else:
					if p:
						element.AppendElement(p)
						p=None
					element.AppendElement(child)
			# left over p should be added, this was a bad bug!
			if p:
				element.AppendElement(p)
			if divFlag:
				self.parent.AppendElement(element)

		
# FlowMat
# -------
#
class FlowMat(FlowV1):
	"""
	<!ELEMENT flow_mat (qticomment? , (flow_mat | material | material_ref)+)>
	
	<!ATTLIST flow_mat  %I_Class; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.flowclass=None
		# flow_mat, objectives, rubric, assessfeedback, sectionfeedback, response_label,
		# itemfeedback, solutionmaterial, hintmaterial
		assert isinstance(self.parent,(FlowMat,ItemFeedback,ResponseLabel,Rubric,Objectives,SolutionMaterial,HintMaterial)),QTIException(eInvalidStructure,"<flow_mat>")
		self.ParseAttributes(attrs)
		self.flow_level=parent.GetFlowLevel()+1
		self.children=[]
		
		
# Material
# --------
#
class Material(QTIObjectV1):
	"""
	<!ELEMENT material (qticomment? , (mattext | matemtext | matimage | mataudio | matvideo | matapplet | matapplication | matref | matbreak | mat_extension)+ , altmaterial*)>
	
	<!ATTLIST material  %I_Label;
			xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		self.label=None
		self.language=None
		# interpretvar, objectives, rubric, flow_mat, reference, assessfeedback, sectionfeedback, itemrubric,
		# presentation, flow, response_lid, response_xy, response_str, response_num, response_grp, response_label,
		# render_choice, render_hotspot, render_slider, render_fib, itemfeedback, solutionmaterial,
		# hintmaterial
		assert isinstance(self.parent,(Presentation,FlowV1,ResponseLabel,ResponseThing,RenderThing,
			ItemFeedback,Rubric,Objectives,InterpretVar,SolutionMaterial,HintMaterial)
			),QTIException(eInvalidStructure,"<material>")
		self.elide=not (self.label or self.language)
		if isinstance(self.parent,(Presentation)):
			# Fix up top-level objects with no flow in them.
			self.parent=FlowV1('flow',{},parent)
			self.flowFlag=1
		elif isinstance(self.parent,(ItemFeedback,ResponseLabel,Rubric,Objectives,SolutionMaterial)):
			self.parent=FlowMat('flowmat',{},parent)
			self.flowFlag=1
		else:
			self.flowFlag=0
		self.children=[]
				
	def SetAttribute_label (self,value):
		self.label=value
	
	def SetAttribute_xml_lang (self,lang):
		self.language=lang
	
	def AppendElement (self,element):
		if self.elide:
			self.parent.AppendElement(element)
		else:
			assert not (element is None)
			self.children.append(element)
	
	def CloseObject (self):
		if not self.elide:
			spanFlag=1
			for child in self.children:
				if not isinstance(child,Inline):
					spanFlag=0
					break
			if spanFlag:
				element=SimpleInline("span")
			else:
				element=xhtml_div()
			if self.label:
				element.SetLabel(self.label)
			if self.language:
				element.SetLanguage(self.language)
			for child in self.children:
				element.AppendElement(child)
			self.parent.AppendElement(element)
		if self.flowFlag:
			self.parent.CloseObject()


# MatThing
# --------
#
class MatThing(QTIObjectV1):
	"""
	An Abstract class that attempts to repsent all aspects of material!
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.label=None
		self.type=None
		self.uri=None
		self.space=None
		self.language=None
		self.entityRef=None
		self.embedded=None
		self.data=""
		self.width=None
		self.height=None
		self.ParseAttributes(attrs)
		# material, altmaterial, reference
		assert isinstance(self.parent,Material),QTIException(eInvalidStructure,"<"+name+">")
		
	def SetAttribute_label (self,value):
		self.label=value
	
	def SetAttribute_uri (self,value):
		self.uri=value
	
	def SetAttribute_entityref (self,value):
		self.entityRef=value
		
	def AddData (self,data):
		self.data=self.data+data

	def MakeObject (self):
		element=xhtml_object()
		self.AddCPFile()
		element.SetData(self.uri)
		element.SetType(self.type)
		if self.label:
			element.SetLabel(self.label)
		if self.language:
			element.SetLanguage(self.language)
		if self.width:
			element.SetWidth(self.width)
		if self.height:
			element.SetHeight(self.height)
		return element
	
	def AddCPFile (self):
		self.uri=self.GetItemV1().AddCPFile(self.uri)
		
	def MakeImage (self):
		element=xhtml_img()
		self.AddCPFile()
		element.SetSrc(self.uri)
		if self.width:
			element.SetWidth(self.width)
		if self.height:
			element.SetHeight(self.height)
		return element

	def ParseTextTokens(self,tokens):
		#print tokens
		stack=[]
		for t in tokens:
			if type(t) is DictType:
				# a tag
				if t['.type']=='EmptyElemTag' or (t['.name'].lower() in ['hr','br','img'] and t['.type']=='STag'):
					# an empty tag
					self.startElement(t['.name'],t)
					self.endElement(t['.name'])
				elif t['.type']=='STag':
					self.startElement(t['.name'],t)
					stack.append(t)
				else:
					# only call endElement for elements we have started.
					while stack:
						tEnd=stack.pop()
						if tEnd['.name']==t['.name']:
							self.endElement(t['.name'])
							break
						else:
							# ommitted closing tag
							self.PrintWarning("Warning: dangling embedding formatting tags are not allowed, closing <%s>"%tEnd['.name'])
							self.endElement(tEnd['.name'])
			else:
				self.characters(t)
		while stack:
			tEnd=stack.pop()
			self.PrintWarning("Warning: dangling embedding formatting tags are not allowed, closing <%s>"%tEnd['.name'])
			self.endElement(tEnd['.name'])

	def startElement(self,name,attrs):
		newElement=None
		lcName=name.lower()
		if lcName in SimpleInlineNames:
			newElement=SimpleInline(lcName)
		elif lcName=='div':
			newElement=xhtml_div()
		elif lcName=='p':
			newElement=xhtml_p()
		elif lcName=='pre':
			newElement=xhtml_pre()
		elif lcName=='blockquote':
			newElement=xhtml_blockquote()
		elif lcName in ['ul','ol']:
			newElement=xhtml_ul(lcName)
		elif lcName=='li':
			newElement=xhtml_li()
		elif lcName=='br':
			newElement=xhtml_br()
		elif lcName=='img':
			# Argh, image inside text!
			newElement=xhtml_img()
			mappedURI=self.GetItemV1().AddCPFile(attrs.get('src',attrs.get('SRC',"")))
			newElement.SetSrc(mappedURI)
			width=attrs.get('width',attrs.get('WIDTH',""))
			if width:
				newElement.SetWidth(self.ReadInteger(width,0))
			height=attrs.get('height',attrs.get('HEIGHT',""))
			if height:
				newElement.SetHeight(self.ReadInteger(height,0))
		elif lcName=="table":
			newElement=xhtml_table()
			summary=attrs.get('summary',attrs.get('SUMMARY',""))
			if summary:
				newElement.SetSummary(summary)
		elif lcName=="tbody":
			newElement=xhtml_tbody()
		elif lcName=="tr":
			newElement=xhtml_tr()
		elif lcName in ["td","th"]:
			newElement=TableCell(lcName)
		elif lcName=='qtihtml':
			# ignore this
			pass
		else:
			newElement=SimpleInline("span")
			newElement.SetClass(name)
			self.PrintWarning('Warning: unsupported embedded formatting instruction replaced by <span class="%s">'%name,1)
		if newElement:
			if isinstance(newElement,BodyElement):
				newElement.SetID(attrs.get('id',None))
				if not newElement.classid:
					newElement.SetClass(attrs.get('class',None))
				newElement.SetLanguage(attrs.get('xml:lang',None))
				newElement.SetLabel(attrs.get('label',None))				
			if self.htmlData:
				if self.htmlElement:
					self.htmlElement.AppendElement(xhtml_text(self.htmlData))
				else:
					self.parent.AppendElement(xhtml_text(self.htmlData))				
				self.htmlData=""
			if self.htmlElement:
				self.htmlStack.append(self.htmlElement)
			self.htmlElement=newElement
	
	def characters(self,ch):
		self.htmlData=self.htmlData+ch
		
	def endElement(self,name):
		lcName=name.lower()
		if lcName=="qtihtml":
			if self.htmlData:
				self.parent.AppendElement(xhtml_text(self.htmlData))
				self.htmlData=""
		else:	
			if self.htmlData:
				self.htmlElement.AppendElement(xhtml_text(self.htmlData))
				self.htmlData=""
			if self.htmlStack:
				htmlParent=self.htmlStack.pop()
				htmlParent.AppendElement(self.htmlElement)
				self.htmlElement=htmlParent
			else:
				self.parent.AppendElement(self.htmlElement)
				self.htmlElement=None
		

#
# MatEmText
# ---------
#
class MatEmText(MatThing, handler.ContentHandler, handler.ErrorHandler):
	"""
	<!ELEMENT matemtext (#PCDATA)>
	
	<!ATTLIST matemtext  texttype    CDATA  'text/plain'
						  %I_Label;
						  %I_CharSet;
						  %I_Uri;
						  xml:space    (preserve | default )  'default'
						  xml:lang    CDATA  #IMPLIED
						  %I_EntityRef;
						  %I_Width;
						  %I_Height;
						  %I_Y0;
						  %I_X0; >
	"""
	def __init__(self,name,attrs,parent):
		MatThing.__init__(self,name,attrs,parent)
		if not self.type:
			self.type="text/plain"
		self.htmlData=""
				
	def SetAttribute_texttype (self,value):
		self.type=value
		
	def SetAttribute_charset (self,value):
		if value.lower()!='ascii-us':
			self.PrintWarning('Warning: charset attribute no longer supported: ignored charset="'+value+'"')

	def SetAttribute_xml_space (self,value):
		self.space=value
			
	def SetAttribute_xml_lang (self,lang):
		self.language=lang

	def SetAttribute_y0 (self,value):
		self.PrintWarning("Warning: discarding y0 coordinate on matemtext")
								
	def SetAttribute_x0 (self,value):
		self.PrintWarning("Warning: discarding x0 coordinate on matemtext")

	def SetAttribute_width (self,value):
		self.PrintWarning("Warning: discarding width on matemtext")

	def SetAttribute_height (self,value):
		self.PrintWarning("Warning: discarding height coordinate on matemtext")

	def CloseObject (self):
		if self.entityRef:
			self.PrintWarning("Unsupported: inclusion of material through external entities: ignored "+self.entityRef)
			element=None
		elif self.uri:
			self.PrintWarning("Warning: material included from external object referenced by matemtext will not be emphasized")
			element=self.MakeObject()
		else:
			element=self.MakeText()
		if element:			
			self.parent.AppendElement(element)

	def MakeText (self):
		if self.type=='text/plain':
#			if self.space.lower()!='preserve':
#				self.data=string.join(string.split(self.data.strip()),' ')
			element=SimpleInline('em')
			element.AppendElement(xhtml_text(self.data))
			if self.label or self.language:
				# We need to wrap it in a span
				span=SimpleInline("span")
				span.SetLabel(self.label)
				span.SetLanguage(self.language)
				span.AppendElement(element)
				element=span
		elif self.type=='text/html':
			self.PrintWarning("Warning: html markup in matemtext will be ignored")
			p=XMLParser()
			try:
				tokens=p.TokenizeString(self.data)
				self.ParseTextTokens(tokens)
			except XMLException:
				self.PrintWarning("Warning: failed to make well-formed XML out of embedded text/html (%s: %s)"%(str(sys.exc_info()[0]),str(sys.exc_info()[1])))
				self.PrintWarning("Warning: offending text/html will be left undecoded")
				self.characters(self.data)
			element=SimpleInline('em')
			element.AppendElement(xhtml_text(self.htmlData))
		elif self.type=='text/rtf':
			self.PrintWarning("Warning: rtf markup in matemtext will be ignored")
			p=RTFParser()
			try:
				tokens=p.TokenizeString(self.data)
				self.ParseTextTokens(tokens)
			except RTFException:
				self.PrintWarning("Warning: failed to make well-formed RTF out of embedded text/rtf (%s: %s)"%(str(sys.exc_info()[0]),str(sys.exc_info()[1])))
				self.PrintWarning("Warning: offending text/rtf will be left undecoded")
				self.characters(self.data)
			element=SimpleInline('em')
			element.AppendElement(xhtml_text(self.htmlData))
		else:
			self.PrintWarning('Unknown text type: ignored matemtext with texttype="%s" treated as text/plain'%self.type)
			self.characters(self.data)
			self.endElement('qtihtml')
			element=None
		return element

	def startElement(self,name,attrs):
		pass
	
	def characters(self,ch):
		self.htmlData=self.htmlData+ch
		
	def endElement(self,name):
		pass
		

# MatText
# -------
#
HTML_PATTERN_HINTS={'<br>':'<br/>',
	'<BR>':'<BR/>',
	'<hr>':'<hr/>',
	'<HR>':'<HR/>',
	'&nbsp;':'&#xA0;'}
	
class MatText(MatThing, handler.ContentHandler, handler.ErrorHandler):
	"""
	<!ELEMENT mattext (#PCDATA)>

	<!ATTLIST mattext  texttype    CDATA  'text/plain'
						%I_Label;
						%I_CharSet;
						%I_Uri;
						xml:space    (preserve | default )  'default'
						xml:lang    CDATA  #IMPLIED
						%I_EntityRef;
						%I_Width;
						%I_Height;
						%I_Y0;
						%I_X0; >
	"""
	def __init__(self,name,attrs,parent):
		MatThing.__init__(self,name,attrs,parent)
		if not self.type:
			self.type="text/plain"
		self.htmlStack=[]
		self.htmlElements=[]
		self.htmlElement=None
		self.htmlData=""
				
	def SetAttribute_texttype (self,value):
		self.type=value
		
	def SetAttribute_charset (self,value):
		if value.lower()!='ascii-us':
			self.PrintWarning('Warning: charset attribute no longer supported: ignored charset="'+value+'"')

	def SetAttribute_xml_space (self,value):
		self.space=value
			
	def SetAttribute_xml_lang (self,lang):
		self.language=lang

	def SetAttribute_y0 (self,value):
		self.PrintWarning("Warning: discarding y0 coordinate on mattext")
								
	def SetAttribute_x0 (self,value):
		self.PrintWarning("Warning: discarding x0 coordinate on mattext")

	def SetAttribute_width (self,value):
		self.PrintWarning("Warning: discarding width on mattext")

	def SetAttribute_height (self,value):
		self.PrintWarning("Warning: discarding height coordinate on mattext")

	def CloseObject (self):
		if self.entityRef:
			self.PrintWarning("Unsupported: inclusion of material through external entities: ignored "+self.entityRef)
			element=None
		elif self.uri:
			element=self.MakeObject()
		else:
			element=self.MakeText()
		if element:			
			self.parent.AppendElement(element)

	def MakeText (self):
		if self.type=='text/plain':
#			if self.space.lower()!='preserve':
#				self.data=string.join(string.split(self.data.strip()),' ')
			element=xhtml_text()
			element.SetText(self.data)
			if self.label or self.language:
				# We need to wrap it in a span
				span=SimpleInline("span")
				span.SetLabel(self.label)
				span.SetLanguage(self.language)
				span.AppendElement(element)
				element=span
		elif self.type=='text/html':
			p=XMLParser()
			try:
				tokens=p.TokenizeString(self.data)
				self.ParseTextTokens(tokens)
			except XMLException:
				self.PrintWarning("Warning: failed to make well-formed XML out of embedded text/html (%s: %s)"%(str(sys.exc_info()[0]),str(sys.exc_info()[1])))
				self.PrintWarning("Warning: offending text/html will be left undecoded")
				self.characters(self.data)
			self.endElement('qtihtml')				
			element=None
		elif self.type=='text/rtf':
			p=RTFParser()
			try:
				tokens=p.TokenizeString(self.data)
				self.ParseTextTokens(tokens)
			except RTFException:
				self.PrintWarning("Warning: failed to make well-formed RTF out of embedded text/rtf (%s: %s)"%(str(sys.exc_info()[0]),str(sys.exc_info()[1])))
				self.PrintWarning("Warning: offending text/rtf will be left undecoded")
				self.characters(self.data)
			element=None
			self.endElement('qtihtml')				
		else:
			self.PrintWarning('Unknown text type: ignored mattext with texttype="%s" treated as text/plain'%self.type)
			self.characters(self.data)
			self.endElement('qtihtml')
			element=None
		return element
	

# RawMaterial
# -----------
#
class RawMaterial(QTIObjectV1):
	"""
	Special class to catch tags not escaped in CDATA sections
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.name=name
		self.parent.AddData("<%s"%name)
		for a in attrs.keys():
			self.parent.AddData(' %s="%s"'%(a,XMLString(attrs[a])))
		self.parent.AddData(">")

	def AddData (self,data):
		self.parent.AddData(data)
	
	def CloseObject (self):
		self.parent.AddData("</%s>"%self.name)

# MatImage
# --------
#
class MatImage(MatThing):
	"""
	<!ELEMENT matimage (#PCDATA)>
	
	<!ATTLIST matimage  imagtype    CDATA  'image/jpeg'
						 %I_Label;
						 %I_Height;
						 %I_Uri;
						 %I_Embedded;
						 %I_Width;
						 %I_Y0;
						 %I_X0;
						 %I_EntityRef; >
	"""
	def __init__(self,name,attrs,parent):
		MatThing.__init__(self,name,attrs,parent)
		if not self.type:
			self.type="image/jpeg"
		self.embedded='base64'
		
	def SetAttribute_imagtype (self,value):
		self.type=value
		
	def SetAttribute_y0 (self,value):
		self.PrintWarning("Warning: discarding y0 coordinate on matimage")
								
	def SetAttribute_x0 (self,value):
		self.PrintWarning("Warning: discarding x0 coordinate on matimage")

	def SetAttribute_width (self,value):
		self.width=self.ReadInteger(value,None)

	def SetAttribute_height (self,value):
		self.height=self.ReadInteger(value,None)

	def SetAttribute_embedded (self,value):
		self.embedded=value
	
	def CloseObject (self):
		element=None
		if self.entityRef:
			self.PrintWarning("Unsupported: inclusion of material through external entities: ignored "+self.entityRef)
		elif not self.uri:
			self.PrintWarning("Unsupported: inclusion of inline images")
		else:
			if self.SniffRenderHotspot():
				element=self.MakeObject()
			else:
				element=self.MakeImage()
		if element:			
			self.parent.AppendElement(element)


# MatAudio
# --------
#
class MatAudio(MatThing):
	"""
	<!ELEMENT mataudio (#PCDATA)>
	
	<!ATTLIST mataudio  audiotype   CDATA  'audio/base'
						 %I_Label;
						 %I_Uri;
						 %I_Embedded;
						 %I_EntityRef; >
	"""
	def __init__(self,name,attrs,parent):
		MatThing.__init__(self,name,attrs,parent)
		if not self.type:
			self.type="audio/base"
		self.embedded='base64'
		
	def SetAttribute_audiotype (self,value):
		self.type=value
		
	def SetAttribute_embedded (self,value):
		self.embedded=value
		
	def CloseObject (self):
		element=None
		if self.entityRef:
			self.PrintWarning("Unsupported: inclusion of material through external entities: ignored "+self.entityRef)
		elif not self.uri:
			self.PrintWarning("Unsupported: inclusion of inline audio data")
		else:
			element=self.MakeObject()
		if element:			
			self.parent.AppendElement(element)


# MatBreak
# --------
#
class MatBreak(QTIObjectV1):
	"""
	<!ELEMENT matbreak EMPTY>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
	
	def CloseObject (self):
		self.parent.AppendElement(xhtml_br())
			

# ResponseThing
# -------------
#
class ResponseThing(QTIObjectV1):
	"""
	Abstract class for response_*
	"""
	def __init__(self,name,attrs,parent):
		self.name=name
		self.parent=parent
		self.cardinality="single"
		self.timing=0
		self.identifier=None
		self.preChildren=[]
		self.postChildren=[]
		self.interaction=None
		self.baseType='identifier'
		self.default=None
		self.index=0
		self.ParseAttributes(attrs)
		# presentation, flow
		assert isinstance(self.parent,(Presentation,FlowV1)),QTIException(eInvalidStructure,"<"+name+">")
		if isinstance(self.parent,(Presentation)):
			# Fix up top-level objects with no flow in them.
			self.parent=FlowV1('flow',{},parent)
			self.flowFlag=1
		else:
			self.flowFlag=0
				
	def SetAttribute_rcardinality (self,value):
		self.cardinality=value.lower()
	
	def SetAttribute_rtiming (self,value):
		self.timing=self.ReadYesNo(value,0)
	
	def SetAttribute_ident (self,value):
		self.identifier=self.ReadIdentifier(value,RESPONSE_PREFIX)
	
	def GetFlowLevel (self):
		return self.parent.GetFlowLevel()
	
	def AppendElement (self,element):
		if self.interaction:
			self.postChildren.append(element)
		else:
			self.preChildren.append(element)

	def BadInteraction (self,renderName):
		self.PrintWarning('Warning: ignoring <'+self.name+'> x <'+renderName+'>')

	def SetInteraction (self,interaction):
		self.interaction=interaction
	
	def SetDefault (self,default):
		self.default=default
	
	def GetIndexedIdentifier(self):
		self.index=self.index+1
		return self.identifier+'_INDEX_'+str(self.index)
		
	def CloseObject (self):
		if self.index:
			for child in self.preChildren:
				self.parent.AppendElement(child)
			self.GetItemV1().DeclareFakeResponse(self.identifier,self.cardinality,self.baseType)
			outcome=self.GetItemV1().GetResponse(self.identifier)
			self.rp=self.GetItemV1().item.GetResponseProcessing()
			if self.cardinality=='ordered':
				aggregateExpression=OrderedOperator()
			else:
				aggregateExpression=MultipleOperator()
			i=0
			while i<self.index:
				i=i+1
				indexIdentifier=self.GetItemV1().GetResponse(self.identifier+'_INDEX_'+str(i)).GetIdentifier()
				aggregateExpression.AddExpression(VariableOperator(indexIdentifier))
			self.rp.AddResponseRule(SetOutcomeValue(outcome.GetIdentifier(),aggregateExpression))
		else:
			if isinstance(self.interaction,BlockInteraction) and self.preChildren:
				promptFlag=1
				for child in self.preChildren:
					if not isinstance(child,Inline):
						promptFlag=0
						break
			else:
				promptFlag=0
			if promptFlag:
				prompt=self.interaction.GetPrompt()
				for child in self.preChildren:
					prompt.AppendElement(child)
			else:
				for child in self.preChildren:
					self.parent.AppendElement(child)
			# deal with indexing here
			self.GetItemV1().DeclareResponse(self.identifier,self.cardinality,self.baseType,self.default)
			if self.interaction:
				self.GetItemV1().BindResponse(self.interaction,self.identifier)
				self.parent.AppendElement(self.interaction)
		# Add the post children as if they were sitting outside anyway
		for child in self.postChildren:
			self.parent.AppendElement(child)
		if self.flowFlag:
			self.parent.CloseObject()


# ResponseLID
# -----------
#
class ResponseLID(ResponseThing):
	"""
	<!ELEMENT response_lid ((material | material_ref)? , (render_choice | render_hotspot | render_slider | render_fib | render_extension) , (material | material_ref)?)>
	
	<!ATTLIST response_lid  %I_Rcardinality;
							 %I_Rtiming;
							 %I_Ident; >
	"""
	def __init__(self,name,attrs,parent):
		ResponseThing.__init__(self,name,attrs,parent)
		self.baseType="identifier"


# ResponseXY
# ----------
#
class ResponseXY(ResponseThing):
	"""
	<!ELEMENT response_xy ((material | material_ref)? , (render_choice | render_hotspot | render_slider | render_fib | render_extension) , (material | material_ref)?)>
	
	<!ATTLIST response_xy  %I_Rcardinality;
							%I_Rtiming;
							%I_Ident; >
	"""
	def __init__(self,name,attrs,parent):
		ResponseThing.__init__(self,name,attrs,parent)
		self.baseType="point"
	

# ResponseStr
# -----------
#
class ResponseStr(ResponseThing):
	"""
	<!ELEMENT response_str ((material | material_ref)? , (render_choice | render_hotspot | render_slider | render_fib | render_extension) , (material | material_ref)?)>
	
	<!ATTLIST response_str  %I_Rcardinality;
							 %I_Ident;
							 %I_Rtiming; >
	"""
	def __init__(self,name,attrs,parent):
		ResponseThing.__init__(self,name,attrs,parent)
		self.baseType="string"


# ResponseNum
# -----------
#
class ResponseNum(ResponseThing):
	"""
	<!ELEMENT response_num ((material | material_ref)? , (render_choice | render_hotspot | render_slider | render_fib | render_extension) , (material | material_ref)?)>
	
	<!ATTLIST response_num  numtype         (Integer | Decimal | Scientific )  'Integer'
							 %I_Rcardinality;
							 %I_Ident;
							 %I_Rtiming; >	
	"""
	def __init__(self,name,attrs,parent):
		ResponseThing.__init__(self,name,attrs,parent)

	def SetAttribute_numtype (self,value):
		if value.lower()=='integer':
			self.baseType="integer"
		elif value.lower()=="decimal" or value.lower()=="scientific":
			self.baseType="float"
		else:
			self.PrintWarning("Warning: unrecognized numtype treated as float ("+value+")")
			self.baseType="float"
	
	def SetBaseType (self,value):
		self.baseType=value


# ResponseGrp
# -----------
#
class ResponseGrp(ResponseThing):
	"""
	<!ELEMENT response_grp ((material | material_ref)? , (render_choice | render_hotspot | render_slider | render_fib | render_extension) , (material | material_ref)?)>
	
	<!ATTLIST response_grp  %I_Rcardinality;
							 %I_Ident;
							 %I_Rtiming; >
	"""
	def __init__(self,name,attrs,parent):
		ResponseThing.__init__(self,name,attrs,parent)
		self.baseType="pair"
	


# RenderThing
# -----------
#
class RenderThing(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.preChildren=[]
		self.labels=[]
		self.postChildren=[]
		self.interactionThing=None
		self.labelThing=None
		# response_lid, response_xy, response_str, response_num, response_grp
		assert isinstance(self.parent,(ResponseThing)),QTIException(eInvalidStructure,"<render_choice>")
		self.ParseAttributes(attrs)
		
	def SetAttribute_minnumber (self,value):
		self.PrintWarning('Warning: minnumber attribute no no longer supported on render_*')
	
	def GetFlowLevel (self):
		return self.parent.GetFlowLevel()
	
	def AppendElement (self,element):
		if self.labels:
			self.postChildren.append(element)
		else:
			self.preChildren.append(element)

	def AppendLabel (self,label):
		if self.postChildren:
			# Oh dear, material sandwhiched between the choices
			self.PrintWarning("Error: deleting material between response_labels")
			self.postChildren=[]
		self.labels.append(label)
	
	def GetLabelThing (self):
		return self.labelThing

		
# RenderChoice
# ------------
#
class RenderChoice(RenderThing):
	"""
	<!ELEMENT render_choice ((material | material_ref | response_label | flow_label)* , response_na?)>
	
	<!ATTLIST render_choice  shuffle      (Yes | No )  'No'
							  %I_MinNumber;
							  %I_MaxNumber; >
	"""
	def __init__(self,name,attrs,parent):
		self.shuffle=0
		self.max=None
		RenderThing.__init__(self,name,attrs,parent)
		if isinstance(self.parent,ResponseLID):
			if self.parent.cardinality=='ordered':
				self.interactionThing=OrderInteraction
			else:
				self.interactionThing=ChoiceInteraction
			self.labelThing=SimpleChoice
		elif isinstance(self.parent,ResponseGrp):
			if self.parent.cardinality=='ordered':
				self.parent.BadInteraction(name+'.ordered')
			else:
				self.interactionThing=AssociateInteraction
				self.labelThing=SimpleAssociableChoice
		else:
			self.parent.BadInteraction(name)
		
	def SetAttribute_shuffle (self,value):
		self.shuffle=self.ReadYesNo(value,0)

	def SetAttribute_maxnumber (self,value):
		self.max=self.ReadInteger(value,None)
		
	def CloseObject (self):
		for child in self.preChildren:
			self.parent.AppendElement(child)
		if self.interactionThing:
			if self.interactionThing==OrderInteraction:
				interaction=OrderInteraction()
			elif self.interactionThing==ChoiceInteraction:
				interaction=ChoiceInteraction()
				if self.max:
					interaction.SetMaxChoices(self.max)
			elif self.interactionThing==AssociateInteraction:
				interaction=AssociateInteraction()
				if self.max:
					interaction.SetMaxAssociations(self.max)			
			interaction.SetShuffle(self.shuffle)
			for choice in self.labels:
				interaction.AddChoice(choice)
			self.parent.SetInteraction(interaction)
		for child in self.postChildren:
			self.parent.AppendElement(child)


# RenderHotspot
# -------------
#
class RenderHotspot(RenderThing):
	"""
	<!ELEMENT render_hotspot ((material | material_ref | response_label | flow_label)* , response_na?)>
	
	<!ATTLIST render_hotspot  %I_MaxNumber;
							   %I_MinNumber;
							   showdraw     (Yes | No )  'No' >
	"""
	def __init__(self,name,attrs,parent):
		self.showdraw=0
		self.max=None
		RenderThing.__init__(self,name,attrs,parent)
		if isinstance(self.parent,ResponseLID):
			if self.parent.cardinality=='ordered':
				self.interactionThing=GraphicOrderInteraction
			else:
				self.interactionThing=HotspotInteraction
			self.labelThing=HotspotChoice
		elif isinstance(self.parent,ResponseXY):
			if self.parent.cardinality=='ordered':
				self.PrintWarning('Warning: ordering of points (through <response_xy>) not supported')
			else:
				self.interactionThing=SelectPointInteraction
		else:
			self.BadInteraction(name)
			
	def SetAttribute_maxnumber (self,value):
		self.max=self.ReadInteger(value,None)

	def SetAttribute_showdraw (self,value):
		self.showdraw=self.ReadYesNo(value,0)			
		if self.showdraw:
			self.PrintWarning('Warning: ignoring showdraw="Yes", what did you really want to happen?') 

	def SniffRenderHotspot (self):
		return self

	def CloseObject (self):
		# Sift out all the images from the material
		images=ExtractImages(self.preChildren)
		images=images+ExtractImages(self.postChildren)
		# the rest of the material is passed up as normal
		for child in self.preChildren:
			self.parent.AppendElement(child)
		if len(images)>1:
			self.PrintWarning("Warning: graphic interaction can now take only one image, discarding extras")
			image=images[0]
		elif len(images)==0:
			self.PrintWarning("Warning: couldn't find an image inside a graphic interaction")
			image=None
		else:
			image=images[0]
		if image and self.interactionThing:
			if self.interactionThing==HotspotInteraction:
				interaction=HotspotInteraction()
				if self.max:
					interaction.SetMaxChoices(self.max)
				for choice in self.labels:
					interaction.AddChoice(choice)				
			elif self.interactionThing==GraphicOrderInteraction:
				interaction=GraphicOrderInteraction()
				for choice in self.labels:
					interaction.AddChoice(choice)
			else:
				interaction=SelectPointInteraction()
				if self.max:
					interaction.SetMaxChoices(self.max)
				# There are no labels
				if self.labels:
					self.PrintWarning("Warning: labels inside <response_xy>/<render_hotspot> ignored - consider use of areaMapping in version 2")
			interaction.SetGraphic(image)
			self.parent.SetInteraction(interaction)
		for child in self.postChildren:
			self.parent.AppendElement(child)


# RenderSlider
# ------------
#
class RenderSlider(RenderThing):
	"""
	<!ELEMENT render_slider ((material | material_ref | response_label | flow_label)* , response_na?)>
	
	<!ATTLIST render_slider  orientation  (Horizontal | Vertical )  'Horizontal'
							  lowerbound  CDATA  #REQUIRED
							  upperbound  CDATA  #REQUIRED
							  step        CDATA  #IMPLIED
							  startval    CDATA  #IMPLIED
							  steplabel    (Yes | No )  'No'
							  %I_MaxNumber;
							  %I_MinNumber; >
	"""
	def __init__(self,name,attrs,parent):
		self.orientation='horizontal'
		self.lowerbound=0
		self.upperbound=100
		self.step=None
		self.stepLabel=0
		self.default=None
		RenderThing.__init__(self,name,attrs,parent)
		self.interactionThing=None
		self.labelThing=None
		if (isinstance(self.parent,ResponseNum)):
			if self.parent.cardinality=='single':
				self.interactionThing=SliderInteraction
				if self.parent.baseType=='integer':
					self.lowerbound=int(self.lowerbound)
					self.upperbound=int(self.upperbound)
					if not (self.step is None):
						self.step=int(self.step)
					self.default=int(self.default)
			else:
				self.PrintWarning('Warning: ignoring '+self.parent.cardinality+' response <render_slider>')
		elif (isinstance(self.parent,ResponseLID)):
			if self.parent.cardinality=='single':
				self.interactionThing=ChoiceInteraction
				self.labelThing=SimpleChoice
		else:
			self.parent.BadInteraction(name)

	def SetAttribute_orientation (self,value):
		if value.strip().lower()=='horizontal':
			self.orientation='horizontal'
		elif value.strip().lower()=='vertical':
			self.orientation='vertical'
		else:
			self.PrintWarning('Warning: ignoring unrecognized orientation ('+value+')')

	def SetAttribute_lowerbound (self,value):
		self.lowerbound=self.ReadFloat(value,0)
	
	def SetAttribute_upperbound (self,value):
		self.upperbound=self.ReadFloat(value,0)
	
	def SetAttribute_step (self,value):
		self.step=self.ReadFloat(value,None)
	
	def SetAttribute_startval (self,value):
		self.default=self.ReadFloat(value,0)
	
	def SetAttribute_steplabel (self,value):
		self.steplabel=self.ReadYesNo(value,0)
	
	def SetAttribute_maxnumber (self,value):
		self.PrintWarning('Warning: maxnumber attribute meaningless on <render_slider>')
		
	def CloseObject (self):
		for child in self.preChildren:
			self.parent.AppendElement(child)
		if self.interactionThing:
			if self.interactionThing==SliderInteraction:
				interaction=SliderInteraction()
				interaction.SetBounds(self.lowerbound,self.upperbound)
				interaction.SetOrientation(self.orientation)
				if self.step:
					interaction.SetStep(self.step)
				if not (self.steplabel is None):
					interaction.SetStepLabel(self.stepLabel)
			else:
				interaction=ChoiceInteraction()
				interaction.SetClass('slider')
				interaction.SetShuffle(0)
				for choice in self.labels:
					interaction.AddChoice(choice)
				self.parent.SetDefault(self.default)
			self.parent.SetInteraction(interaction)
		for child in self.postChildren:
			self.parent.AppendElement(child)


# RenderFib
# ---------
#
class RenderFib(RenderThing):
	"""
	<!ELEMENT render_fib ((material | material_ref | response_label | flow_label)* , response_na?)>
	
	<!ATTLIST render_fib  encoding    CDATA  'UTF_8'
						   fibtype      (String | Integer | Decimal | Scientific )  'String'
						   rows        CDATA  #IMPLIED
						   maxchars    CDATA  #IMPLIED
						   prompt       (Box | Dashline | Asterisk | Underline )  #IMPLIED
						   columns     CDATA  #IMPLIED
						   %I_CharSet;
						   %I_MaxNumber;
						   %I_MinNumber; >
	"""
	def __init__(self,name,attrs,parent):
		self.fibtype='string'
		self.rows=1
		self.columns=0
		self.maxchars=None
		self.classid=None
		self.max=None
		self.children=[]
		RenderThing.__init__(self,name,attrs,parent)
		if self.GetParser().options.forceFloat:
			# force all fibs to be float, which means forcing parent response too
			self.fibtype='float'
			self.parent.baseType='float'
		if isinstance(self.parent,(ResponseNum,ResponseStr)):
			# may change later!
			self.interactionThing=ExtendedTextInteraction
			self.labelThing=StringType
			if isinstance(self.parent,ResponseNum):
				if self.fibtype!=self.parent.baseType:
					self.PrintWarning('Warning: fibtype does not match enclosing <response_num>, assuming float')
					self.parent.SetBaseType('float')
					self.fibtype='float'
			elif self.fibtype!='string':
				self.PrintWarning('Warning: numeric fibtype does not match enclosing <response_str>, assuming string')
				self.fibtype='string'
			# calculate the expectedLength
			if self.maxchars:
				if self.rows*self.columns:
					self.PrintWarning("Warning: ignoring rows x columns on render_fib in favour of maxchars")
			else:
				self.maxchars=self.rows*self.columns
				if self.maxchars:
					self.PrintWarning("Warning: converting rows x columns to expectedLength only")
		else:
			self.BadInteraction(name)

	def SetAttribute_encoding (self,value):
		if value.upper()!='UTF_8':
			self.PrintWarning('Warning: encoding attribute of render_fib not supported, ignored "'+value+'"')
	
	def SetAttribute_fibtype (self,value):
		v=value.strip().lower()
		if v=='string':
			self.fibtype='string'
		elif v=='integer':
			self.fibtype='integer'
		elif v in ['decimal','scientific']:
			self.fibtype='float'
		else:
			self.PrintWarning('Warning: unknown fibtype treated as string ('+value+')')

	def SetAttribute_rows (self,value):
		self.rows=self.ReadInteger(value,0)
	
	def SetAttribute_columns (self,value):
		self.columns=self.ReadInteger(value,0)
		
	def SetAttribute_maxchars (self,value):
		self.PrintWarning('Warning: maxchars on render_fib no longer strictly enforced.')
		self.maxchars=self.ReadInteger(value,0)

	def SetAttribute_prompt (self,value):
		self.PrintWarning('Warning: prompt style on render_fib no longer supported, converted to style class')
		self.classid=value.strip()
		
	def SetAttribute_minnumber (self,value):
		self.PrintWarning('Warning: minimum response no longer supported, ignoring minnumber="'+value+'"')
	
	def SetAttribute_maxnumber (self,value):
		self.max=self.ReadInteger(value,None)
		
	def SetAttribute_charset (self,value):
		if value.lower()!='ascii-us':
			self.PrintWarning('Warning: charset attribute no longer supported: ignored charset="'+value+'"')

	def AppendElement (self,element):
		self.children.append(element)

	def AppendLabel (self,label):
		self.children.append(label)
		self.labels.append(label)
			
	def CloseObject (self):
		if self.interactionThing:
			if self.labels and len(self.children)>len(self.labels):
				# There are response labels, treat them as TextEntryInteractions
				if self.parent.cardinality=='single' and len(self.labels)>1:
					self.PrintWarning("Warning: single response fib ignoring all but last <response_label>")
				if self.parent.cardinality=='single':
					for child in self.children:
						if type(child) in StringTypes:
							interaction=TextEntryInteraction()
							if self.fibtype!='string':
								interaction.SetBase(10)
							if self.maxchars:
								interaction.SetExpectedLength(self.maxchars)
							if self.classid:
								interaction.SetClass(self.classid)
							self.parent.SetInteraction(interaction)
						else:
							self.parent.AppendElement(child)
				else:
					for child in self.children:
						if type(child) in StringTypes:
							interaction=TextEntryInteraction()
							if self.fibtype!='string':
								interaction.SetBase(10)
							if self.maxchars:
								interaction.SetExpectedLength(self.maxchars)
							if self.classid:
								interaction.SetClass(self.classid)
							# now I have to bind this one myself!
							identifier=self.parent.GetIndexedIdentifier()
							self.GetItemV1().DeclareResponse(identifier,'single',self.parent.baseType,None)
							self.GetItemV1().BindResponse(interaction,identifier)
							self.parent.AppendElement(interaction)
						else:
							self.parent.AppendElement(child)
			else:
				# Choose an extended interaction
				interaction=ExtendedTextInteraction()
				if self.max:
					interaction.SetMaxStrings(self.max)
				elif self.parent.cardinality!='single':
					if self.labels:
						self.PrintWarning("Warning: no maxnumber for multiple text box, counting <response_label> instead")
						interaction.SetMaxStrings(len(self.labels))
					else:
						self.PrintWarning('Warning: no maxnumber for multiple text box, guessing maxnumber="1"')
						interaction.SetMaxStrings(1)
				if self.fibtype!='string':
					interaction.SetBase(10)
				if self.maxchars:
					interaction.SetExpectedLength(self.maxchars)
				if self.classid:
					interaction.SetClass(self.classid)
				self.parent.SetInteraction(interaction)
				

# ResponseLabel
# -------------
#
class ResponseLabel(QTIObjectV1):
	"""
	<!ELEMENT response_label (#PCDATA | qticomment | material | material_ref | flow_mat)*>
	
	<!ATTLIST response_label  rshuffle     (Yes | No )  'Yes'
							   rarea        (Ellipse | Rectangle | Bounded )  'Ellipse'
							   rrange       (Exact | Range )  'Exact'
							   labelrefid  CDATA  #IMPLIED
							   %I_Ident;
							   match_group CDATA  #IMPLIED
							   match_max   CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.rshuffle=0
		self.shape='default'
		self.labelrefid=None
		self.identifier=None
		self.matchGroup=[]
		self.matchMax=None
		self.children=[]
		self.data=""
		self.labelThing=self.parent.GetLabelThing()
		self.ParseAttributes(attrs)
		# flow_label, render_choice, render_hotspot, render_slider, render_fib
		assert isinstance(self.parent,(FlowLabel,RenderThing)),QTIException(eInvalidStructure,"<response_label>")
	
	def SetAttribute_rshuffle (self,value):
		self.rshuffle=self.ReadYesNo(value,1)
	
	def SetAttribute_rarea (self,value):
		shape=value.strip().lower()
		if shape=='rectangle':
			self.shape='rect'
		elif shape=='ellipse':
			self.shape='ellipse'
		elif shape=='bounded':
			self.shape='poly'
		else:
			raise QTIException(eUnknownShape)
	
	def SetAttribute_rrange (self,value):
		if value.lower()!='exact':
			self.PrintWarning('Warning: rrange is no longer supported, ignored "'+value+'"')
	
	def SetAttribute_labelrefid (self,value):
		self.PrintWarning("Warning: labelrefid is no longer supported in version 2, ignored "+value)
	
	def SetAttribute_ident (self,value):
		self.identifier=self.ReadIdentifier(value,RESPONSE_PREFIX)
	
	def SetAttribute_match_group (self,value):
		value=string.join(string.split(value),'')
		self.matchGroup=string.split(value,',')
	
	def SetAttribute_match_max (self,value):
		self.matchMax=self.ReadInteger(value,None)

	def GetFlowLevel (self):
		return self.parent.GetFlowLevel()

	def AppendElement (self,element):
		self.children.append(element)
	
	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		if self.labelThing==SimpleChoice:
			choice=SimpleChoice()
			choice.SetIdentifier(self.identifier)
			choice.SetFixed(not self.rshuffle)
			self.data=self.data.strip()
			if self.data and self.children:
				self.PrintWarning('Warning: ignoring PCDATA in <response_label>, "'+self.data+'"')
			elif self.data:
				element=xhtml_text()
				element.SetText(self.data)
				choice.AppendElement(element)
			else:
				for child in self.children:
					choice.AppendElement(child)
			self.parent.AppendLabel(choice)
		elif self.labelThing==SimpleAssociableChoice:
			choice=SimpleAssociableChoice()
			choice.SetIdentifier(self.identifier)
			choice.SetFixed(not self.rshuffle)
			if self.matchMax:
				choice.SetMatchMax(self.matchMax)
			if self.matchGroup:
				choice.SetMatchGroup(self.matchGroup)
			self.data=self.data.strip()
			if self.data and self.children:
				self.PrintWarning('Warning: ignoring PCDATA in <response_label>, "'+self.data+'"')
			elif self.data:
				element=xhtml_text()
				element.SetText(self.data)
				choice.AppendElement(element)
			else:
				for child in self.children:
					choice.AppendElement(child)
			self.parent.AppendLabel(choice)
		elif self.labelThing==HotspotChoice:
			choice=HotspotChoice()
			choice.SetIdentifier(self.identifier)
			self.shape,coords=self.ConvertAreaCoords(self.shape,self.data)
			choice.SetShape(self.shape,coords)
			labelStr=""
			for child in self.children:
				labelStr=labelStr+child.ExtractText()
			if labelStr:
				choice.SetHotspotLabel(labelStr)
			self.parent.AppendLabel(choice)
		elif self.labelThing==StringType:
			self.parent.AppendLabel(self.identifier)
		else:
			self.PrintWarning('Warning: ignoring <response_label iden="'+self.identifier+'">')


# FlowLabel
# ---------
#
class FlowLabel(QTIObjectV1):
	"""
	<!ELEMENT flow_label (qticomment? , (flow_label | response_label)+)>
	
	<!ATTLIST flow_label  %I_Class; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		# flow_label, render_choice, render_hotspot, render_slider, render_fib
		assert isinstance(self.parent,(RenderThing,FlowLabel)),QTIException(eInvalidStructure,"<flow_label>")
		self.PrintWarning("Warning: flow_label is no longer supported in version 2, ignoring")
	
	def SetAttribute_class (self,value):
		pass

	def GetFlowLevel (self):
		return self.parent.GetFlowLevel()
	
	def AppendLabel (self,label):
		self.parent.AppendLabel(label)
			
	def GetLabelThing (self):
		return self.parent.GetLabelThing()


# ItemFeedback
# ------------
#
class ItemFeedback(QTIObjectV1):
	"""
	<!ELEMENT itemfeedback ((flow_mat | material) | solution | hint)+>
	
	<!ATTLIST itemfeedback  %I_View;
							 %I_Ident;
							 %I_Title; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier=None
		self.view=None
		self.title=None
		self.feedback=ModalFeedback()
		self.ParseAttributes(attrs)
		# item
		assert isinstance(self.parent,QTIItem),QTIException(eInvalidStructure,"<itemfeedback>")
		
	def SetAttribute_view (self,value):
		if not (value.lower() in ['all','candidate']):
			self.PrintWarning("Warning: discarding view on feedback ("+value+")")
	
	def SetAttribute_ident (self,value):
		self.feedback.SetIdentifier(self.ReadIdentifier(value,FEEDBACK_PREFIX))
	
	def SetAttribute_title (self,value):
		self.feedback.SetTitle(value)
	
	def GetFlowLevel (self):
		return 0
	
	def AppendElement (self,element):
		self.feedback.AppendElement(element)			
	
	def CloseObject (self):
		self.GetItemV1().item.AddModalFeedback(self.feedback)


# Solution
# --------
#
class Solution(QTIObjectV1):
	"""
	<!ELEMENT solution (qticomment? , solutionmaterial+)>
	
	<!ATTLIST solution  %I_FeedbackStyle; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.feedbackstyle="complete"
		self.ParseAttributes(attrs)
		# itemfeedback
		assert isinstance(self.parent,ItemFeedback),QTIException(eInvalidStructure,"<solution>")
		self.div=xhtml_div()
		if self.feedbackstyle!="complete":
			solclass='solution.'+self.feedbackstyle
		else:
			solclass='solution'
		self.PrintWarning('Warning: solution material is being replaced by div with class="'+solclass+'"')
		self.div.SetClass(solclass)
		
	def SetAttribute_feedbackstyle (self,value):
		self.feedbackstyle=value.strip().lower()
	
	def GetFlowLevel (self):
		return 0
		
	def AppendElement (self,element):
		self.div.AppendElement(element)
	
	def CloseObject (self):
		self.parent.AppendElement(self.div)


# SolutionMaterial
# ----------------
#
class SolutionMaterial(QTIObjectV1):
	"""
	<!ELEMENT solutionmaterial (material+ | flow_mat+)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		# solution
		assert isinstance(self.parent,Solution),QTIException(eInvalidStructure,"<solutionmaterial>")
	
	def GetFlowLevel (self):
		return 0
		
	def AppendElement (self,element):
		self.parent.AppendElement(element)
			
	
# Hint
# ----
#
class Hint(QTIObjectV1):
	"""
	<!ELEMENT hint (qticomment? , hintmaterial+)>
	
	<!ATTLIST hint  %I_FeedbackStyle; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.feedbackstyle="complete"
		self.ParseAttributes(attrs)
		# itemfeedback
		assert isinstance(self.parent,ItemFeedback),QTIException(eInvalidStructure,"<hint>")
		self.div=xhtml_div()
		if self.feedbackstyle!="complete":
			hintclass='hint.'+self.feedbackstyle
		else:
			hintclass='hint'
		self.PrintWarning('Warning: hint material is being replaced by div with class="'+hintclass+'"')
		self.div.SetClass(hintclass)
		
	def SetAttribute_feedbackstyle (self,value):
		self.feedbackstyle=value.strip().lower()
	
	def GetFlowLevel (self):
		return 0
		
	def AppendElement (self,element):
		self.div.AppendElement(element)
	
	def CloseObject (self):
		self.parent.AppendElement(self.div)


# HintMaterial
# ------------
#
class HintMaterial(QTIObjectV1):
	"""
	<!ELEMENT hintmaterial (material+ | flow_mat+)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		# hint
		assert isinstance(self.parent,Hint),QTIException(eInvalidStructure,"<hintmaterial>")
	
	def GetFlowLevel (self):
		return 0
		
	def AppendElement (self,element):
		self.parent.AppendElement(element)


# ResponseProcessing
# ------------------
#
class ResProcessing(QTIObjectV1):
	"""
	<!ELEMENT resprocessing (qticomment? , outcomes , (respcondition | itemproc_extension)+)>
	
	<!ATTLIST resprocessing  %I_ScoreModel; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		# item
		assert isinstance(self.parent,QTIItem),QTIException(eInvalidStructure,"<resprocessing>")
		self.parent.ResetResprocessing()
		self.rp=parent.item.GetResponseProcessing()
		self.continueMode=1
		self.rpAddPoint=self.rp
		
	def SetAttribute_scoremodel (self,value):
		self.PrintWarning('Warning: scoremodel not supported, ignoring "'+value+'"')

	def AddRespCondition (self,expression,rules,continueFlag):
		if continueFlag:
			rc=ResponseCondition()
			rcif=rc.GetResponseIf()
			rcif.SetExpression(expression)
			for rule in rules:
				rcif.AddResponseRule(rule)
			if not self.continueMode:
				# Add an else to the current condition
				self.rpAddPoint=self.rpAddPoint.GetResponseElse()
			self.rpAddPoint.AddResponseRule(rc)
		else:
			if self.continueMode:
				rc=ResponseCondition()
				rcIf=rc.GetResponseIf()
				rcIf.SetExpression(expression)
				for rule in rules:
					rcIf.AddResponseRule(rule)
				self.rpAddPoint.AddResponseRule(rc)
				self.rpAddPoint=rc
			else:
				rcElseIf=ResponseElseIf()
				rcElseIf.SetExpression(expression)	
				for rule in rules:
					rcElseIf.AddResponseRule(rule)
				self.rpAddPoint.AddResponseElseIf(rcElseIf)
		self.continueMode=continueFlag						

		
# Outcomes
# --------
#
class Outcomes(QTIObjectV1):
	"""
	<!ELEMENT outcomes (qticomment? , (decvar , interpretvar*)+)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		# resprocessing, outcomes_processing, 
		assert isinstance(self.parent,ResProcessing),QTIException(eInvalidStructure,"<outcomes>")


# DecVar
# ------
#
class DecVar(QTIObjectV1):
	"""
	<!ELEMENT decvar (#PCDATA)>
	
	<!ATTLIST decvar  %I_VarName;
					   vartype     (Integer | 
									String | 
									Decimal | 
									Scientific | 
									Boolean | 
									Enumerated | 
									Set )  'Integer'
					   defaultval CDATA  #IMPLIED
					   minvalue   CDATA  #IMPLIED
					   maxvalue   CDATA  #IMPLIED
					   members    CDATA  #IMPLIED
					   cutvalue   CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier=None
		self.data=""
		self.baseType='integer'
		self.default=None
		self.min=None
		self.max=None
		self.ParseAttributes(attrs)
		# outcomes
		assert isinstance(self.parent,Outcomes),QTIException(eInvalidStructure,"<decvar>")
		if self.min or self.max:
			self.PrintWarning('Warning: min/max constraint on outcome will generate additional rules in responseProcessing')
			
	def SetAttribute_varname (self,value):
		self.identifier=self.ReadIdentifier(value,OUTCOME_PREFIX)
		if self.GetParser().options.ucVars:
			self.identifier=self.identifier.upper()
	
	def SetAttribute_vartype (self,value):
		lcvalue=value.lower()
		if lcvalue in ('integer','string','boolean'):
			self.baseType=lcvalue
		elif lcvalue=='decimal' or lcvalue=='scientific':
			self.baseType='float'
		elif lcvalue=='enumerated':
			self.baseType='identifier'
		elif lcvalue=='set':
			self.PrintWarning('Warning: treating vartype="Set" as equivalent to "Enumerated"')
			self.baseType='identifier'
		else:
			self.PrintWarning('Error: bad value for decvar, ignored decvar="'+value+'"')
		
	def SetAttribute_defaultval (self,value):
		self.default=value
	
	def SetAttribute_minvalue (self,value):
		self.min=self.ReadFloat(value,0)
	
	def SetAttribute_maxvalue (self,value):
		self.max=self.ReadFloat(value,1)

	def SetAttribute_members (self,value):
		self.PrintWarning('Warning: enumerated members no longer supported, ignoring "'+value+'"')
		
	def SetAttribute_cutvalue (self,value):
		self.PrintWarning('Warning: cutvalue on outcome will be ignored.')

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		data=self.data.strip()
		if data and (self.identifier=="SCORE" or self.identifier is None):
			self.identifier=self.ReadIdentifier(data,OUTCOME_PREFIX)
			if self.GetParser().options.ucVars:
				self.identifier=self.identifier.upper()
		if self.identifier is None:
			self.identifier="SCORE"
		self.GetItemV1().DeclareOutcome(self)
		
# InterpretVar
# ------------
#
class InterpretVar(QTIObjectV1):
	"""
	<!ELEMENT interpretvar (material | material_ref)>
	
	<!ATTLIST interpretvar  %I_View;
							 %I_VarName; >
	
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier=None
		self.ParseAttributes(attrs)
		self.interpretation=""
		# outcomes
		assert isinstance(self.parent,Outcomes),QTIException(eInvalidStructure,"<interpretvar>")
	
	def SetAttribute_varname (self,value):
		self.identifier=self.ReadIdentifier(value,OUTCOME_PREFIX)
		if self.GetParser().options.ucVars:
			self.identifier=self.identifier.upper()
	
	def SetAttribute_view (self,view):
		if view.strip().lower()!='all':
			self.PrintWarning('Warning: view restriction on outcome interpretation no longer supported ('+view+')')
	
	def AppendElement (self,element):
		self.interpretation=self.interpretation+element.ExtractText()
	
	def CloseObject (self):
		outcome=self.GetItemV1().GetOutcome(self.identifier)
		outcome.SetInterpretation(self.interpretation)


# RespCondition
# -------------
#
class RespCondition(QTIObjectV1):
	"""
	<!ELEMENT respcondition (qticomment? , conditionvar , setvar* , displayfeedback* , respcond_extension?)>
	
	<!ATTLIST respcondition  %I_Continue;
							  %I_Title; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.continueFlag=0
		self.expression=None
		self.rules=[]
		self.ParseAttributes(attrs)
		# resprocessing
		assert isinstance(self.parent,ResProcessing),QTIException(eInvalidStructure,"<respcondition>")
				
	def SetAttribute_continue (self,value):
		self.continueFlag=self.ReadYesNo(value,0)

	def SetAttribute_title (self,value):
		self.PrintWarning('Warning: titles on respconditions no longer supported, ignored "'+value+'"')

	def AddExpression (self,expression):
		self.expression=expression
	
	def AddRule (self,rule):
		self.rules.append(rule)
	
	def CloseObject (self):
		self.parent.AddRespCondition(self.expression,self.rules,self.continueFlag)


# SetVar
# ------
#
class SetVar(QTIObjectV1):
	"""
	<!ELEMENT setvar (#PCDATA)>
	
	<!ATTLIST setvar  %I_VarName;
					   action     (Set | Add | Subtract | Multiply | Divide )  'Set' >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier='SCORE'
		self.action='set'
		self.value=""
		self.ParseAttributes(attrs)
		# respcondition
		assert isinstance(self.parent,RespCondition),QTIException(eInvalidStructure,"<setvar>")
			
	def SetAttribute_varname (self,value):
		self.identifier=self.ReadIdentifier(value,OUTCOME_PREFIX)
		if self.GetParser().options.ucVars:
			self.identifier=self.identifier.upper()

	def SetAttribute_action (self,value):
		self.action=value.lower()
	
	def AddData (self,data):
		self.value=self.value+data

	def CloseObject (self):
		outcome=self.GetItemV1().GetOutcome(self.identifier)
		varExpression=VariableOperator(outcome.GetIdentifier())
		baseType=outcome.GetBaseType()
		assert outcome.GetCardinality()=='single',QTIException(eUnexpectedContainer,self.identifier)
		valExpression=BaseValueOperator(baseType,self.value)
		if self.action=='set':
			pass
		elif self.action=='add':
			expression=SumOperator()
			expression.AddExpression(varExpression)
			expression.AddExpression(valExpression)
			valExpression=expression
		elif self.action=='subtract':
			valExpression=SubtractOperator(varExpression,valExpression)
		elif self.action=='multiply':
			expression=ProductOperator()
			expression.AddExpression(varExpression)
			expression.AddExpression(valExpression)
			valExpression=expression
		elif self.action=='divide':
			valExpression=DivideOperator(varExpression,valExpression)
		else:
			raise QTIException(eUnexpectedVarAction,selt.action)
		self.parent.AddRule(SetOutcomeValue(outcome.GetIdentifier(),valExpression))

# DisplayFeedback
# ---------------
#
class DisplayFeedback(QTIObjectV1):
	"""
	<!ELEMENT displayfeedback (#PCDATA)>
	
	<!ATTLIST displayfeedback  feedbacktype  (Response | Solution | Hint )  'Response'
								%I_LinkRefId; >
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier=None
		self.ParseAttributes(attrs)
		# respcondition, outcomes_feedback_test
		assert isinstance(self.parent,RespCondition),QTIException(eInvalidStructure,"<displayfeedback>")

	def SetAttribute_feedbacktype (self,value):		
		if value.lower()!='response':
			self.PrintWarning("Warning: feedbacktype is unused and is being discarded ("+value+")")
	
	def SetAttribute_linkrefid (self,value):
		self.identifier=self.ReadIdentifier(value,FEEDBACK_PREFIX)
	
	def CloseObject (self):
		varExpression=VariableOperator("FEEDBACK")
		mExpression=MultipleOperator()
		mExpression.AddExpression(varExpression)
		mExpression.AddExpression(BaseValueOperator('identifier',self.identifier))
		self.parent.AddRule(SetOutcomeValue("FEEDBACK",mExpression))
		self.GetItemV1().DeclareFeedback()
		
	
# ConditionVar
# ------------
#
class ConditionVar(QTIObjectV1):
	"""
	<!ELEMENT conditionvar (not | and | or | unanswered | other | varequal | varlt | varlte | vargt | vargte | varsubset | varinside | varsubstring | durequal | durlt | durlte | durgt | durgte | var_extension)+>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.expressions=[]
		self.ParseAttributes(attrs)
		# respcondition
		assert isinstance(self.parent,RespCondition),QTIException(eInvalidStructure,"<conditionvar>")
	
	def AddExpression (self,expression):
		self.expressions.append(expression)
	
	def CloseObject (self):
		if len(self.expressions)>1:
			# implicit and
			expression=AndOperator()
			for sub_expression in self.expressions:
				expression.AddExpression(sub_expression)
			self.parent.AddExpression(expression)
		elif self.expressions:
			self.parent.AddExpression(self.expressions[0])
		else:
			self.PrintWarning("Warning: empty condition replaced with null operator")
			self.parent.AddExpression(NullOperator())


# AndOperatorV1
# -------------
#
class AndOperatorV1(QTIObjectV1):
	"""
	<!ELEMENT and (not | and | or | unanswered | other | varequal | varlt | varlte | vargt | vargte | varsubset | varinside | varsubstring | durequal | durlt | durlte | durgt | durgte)+>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		self.operator=AndOperator()
		# conditionvar, and, or, not
		assert isinstance(self.parent,(ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1)),QTIException(eInvalidStructure,"<and>")
	
	def AddExpression (self,expression):
		self.operator.AddExpression(expression)

	def CloseObject (self):
		self.parent.AddExpression(self.operator)

		
# OrOperatorV1
# ------------
#
class OrOperatorV1(QTIObjectV1):
	"""
	<!ELEMENT or (not | and | or | unanswered | other | varequal | varlt | varlte | vargt | vargte | varsubset | varinside | varsubstring | durequal | durlt | durlte | durgt | durgte)+>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		self.operator=OrOperator()
		# conditionvar, and, or, not
		assert isinstance(self.parent,(ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1)),QTIException(eInvalidStructure,"<or>")
	
	def AddExpression (self,expression):
		self.operator.AddExpression(expression)

	def CloseObject (self):
		self.parent.AddExpression(self.operator)


# NotOperatorV1
# -------------
#
class NotOperatorV1(QTIObjectV1):
	"""
	<!ELEMENT not (and | or | not | unanswered | other | varequal | varlt | varlte | vargt | vargte | varsubset | varinside | varsubstring | durequal | durlt | durlte | durgt | durgte)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		self.expressions=[]
		# conditionvar, and, or, not
		assert isinstance(self.parent,(ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1)),QTIException(eInvalidStructure,"<not>")
	
	def AddExpression (self,expression):
		self.expressions.append(expression)

	def CloseObject (self):
		if len(self.expressions)>1:
			self.PrintWarning("Warning: multiple expressions in <not> treated as implicity and")
			# implicit and
			expression=AndOperator()
			for sub_expression in self.expressions:
				expression.AddExpression(sub_expression)
			self.parent.AddExpression(NotOperator(expression))
		elif self.expressions:
			self.parent.AddExpression(NotOperator(self.expressions[0]))
		else:
			self.PrintWarning("Warning: replacing empty <not> with Null operator")
			self.parent.AddExpression(NullOperator())

		
# OtherOperator
# -------------
#
class OtherOperatorV1(QTIObjectV1):
	"""
	<!ELEMENT other (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ParseAttributes(attrs)
		# conditionvar, and, or, not
		assert isinstance(self.parent,(ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1)),QTIException(eInvalidStructure,"<not>")

	def AddData (self,data):
		# We ignore the data in <other> as it is sometimes put there for compatibility with other systems.
		pass
	
	def CloseObject (self):
		self.PrintWarning("Warning: replacing <other/> with the base value true - what did you want me to do??")
		self.parent.AddExpression(BaseValueOperator('boolean','true'))


# Unanswered
# ----------
#
class Unanswered(QTIObjectV1):
	"""
	<!ELEMENT unanswered (#PCDATA)>
	
	<!ATTLIST unanswered  %I_RespIdent; >
	
	Similar to the var* tests, but we replace unanswered with an isNull operator.
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier=None
		self.ParseAttributes(attrs)
		# conditionvar, not, and, or
		assert isinstance(self.parent,(ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1)),QTIException(eInvalidStructure,"<varequal>")

	def SetAttribute_respident (self,value):
		self.identifier=self.ReadIdentifier(value,RESPONSE_PREFIX)
	
	def CloseObject (self):
		response=self.GetItemV1().GetResponse(self.identifier)
		if response:
			expression=IsNullOperator(VariableOperator(response.GetIdentifier()))
		else:
			self.PrintWarning("Warning: test of undeclared response replaced with Null operator")
			expression=NullOperator()
		self.parent.AddExpression(expression)


# VarThing
# --------
#
class VarThing(QTIObjectV1):
	"""
	Abstract class for var* tests
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.identifier=None
		self.index=None
		self.value=""
		self.ParseAttributes(attrs)
		# conditionvar, not, and, or
		assert isinstance(self.parent,(ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1)),QTIException(eInvalidStructure,"<varequal>")

	def SetAttribute_respident (self,value):
		self.identifier=self.ReadIdentifier(value,RESPONSE_PREFIX)
	
	def SetAttribute_index (self,value):
		self.index=self.ReadInteger(value,None)
	
	def AddData (self,data):
		self.value=self.value+data

	def MakeVariableExpression (self):
		response=self.GetItemV1().GetResponse(self.identifier)
		if response:
			self.varExpression=VariableOperator(response.GetIdentifier())
			self.varCardinality=response.GetCardinality()
			self.varBaseType=response.GetBaseType()
			if self.index:
				if self.varCardinality=='multiple':
					raise QTIException(eIndexIntoMultiple)
				elif self.varCardinality=='single':
					self.PrintWarning("Warning: index ignored for response variable of cardinality single")
				else:
					self.varExpression=IndexOperator(self.varExpression,self.index)
					self.varCardinality='single'
		else:
			self.PrintWarning("Warning: test of undeclared response replaced with Null operator")
			self.varExpression=NullOperator()
			self.varCardinality='single'
			self.varBaseType='identifier'
				
	def MakeSingleValue (self,baseType):
		# sort out lexical representation of point and pair values before constructing
		# the base value operator in future.
		if baseType in ('pair','directedPair'):
			self.value=self.value.replace(',',' ')
		elif baseType=='identifier':
			self.value=self.CheckNMTOKEN(self.value,RESPONSE_PREFIX)
		self.valExpression=BaseValueOperator(baseType,self.value)
		self.valCardinality='single'
		
	
# VarEqual
# --------
#
class VarEqual(VarThing):
	"""
	<!ELEMENT varequal (#PCDATA)>
	
	<!ATTLIST varequal  %I_Case;
						 %I_RespIdent;
						 %I_Index; >	
	"""
	def __init__(self,name,attrs,parent):
		self.caseFlag=0
		VarThing.__init__(self,name,attrs,parent)

	def SetAttribute_case (self,value):
		self.caseFlag=self.ReadYesNo(value,0)
	
	def CloseObject (self):
		self.MakeVariableExpression()
		self.MakeSingleValue(self.varBaseType)
		if self.varCardinality=='single':
			# simple test of equality
			if self.varBaseType=='identifier' or self.varBaseType=='pair':
				if not self.caseFlag:
					self.PrintWarning("Warning: case-insensitive comparison of identifiers not supported in version 2")
				expression=MatchOperator(self.varExpression,self.valExpression)
			elif self.varBaseType=='integer':
				expression=MatchOperator(self.varExpression,self.valExpression)
			elif self.varBaseType=='string':
				expression=StringMatchOperator(self.varExpression,self.valExpression,self.caseFlag)
			elif self.varBaseType=='float':
				self.PrintWarning("Warning: equality operator with float values is deprecated")
				expression=EqualOperator(self.varExpression,self.valExpression)
			else:
				raise QTIException(eUnimplementedOperator,"varequal("+self.varBaseType+")")
		else:
			# This test simply becomes a member-test operation
			if self.varBaseType=='identifier' or self.varBaseType=='pair':
				if not self.caseFlag:
					self.PrintWarning("Warning: case-insensitive comparison of identifiers not supported in version 2")
			elif self.varBaseType=='string':
				if not self.caseFlag:
					self.PrintWarning("Warning: member operation cannot be case-insensitive when baseType is string")
			elif self.varBaseType=='float':
				self.PrintWarning("Warning: member operation is deprecated when baseType is float")
			else:
				raise QTIException(eUnimplementedOperator,"varequal("+self.varBaseType+")")
			expression=MemberOperator(self.valExpression,self.varExpression)
		self.parent.AddExpression(expression)
		
	
# VarLT
# -----
#
class VarLT(VarThing):
	"""
	<!ELEMENT varlt (#PCDATA)>
	
	<!ATTLIST varlt  %I_RespIdent;
					   %I_Index; >
	"""
	def __init__(self,name,attrs,parent):
		VarThing.__init__(self,name,attrs,parent)

	def CloseObject (self):
		self.MakeVariableExpression()
		self.MakeSingleValue(self.varBaseType)
		if self.varCardinality=='single':
			if self.varBaseType in ['integer','float']:
				expression=LTOperator(self.varExpression,self.valExpression)
			elif self.varBaseType=='string':
				self.PrintWarning("Warning: varlt not supported on String in QTI v2, re-run with --forcefibfloat to treat string fibs as numbers",1)
				expression=CustomOperator("varlt")
				expression.AddExpression(self.varExpression)
				expression.AddExpression(self.valExpression)
			else:
				self.PrintWarning('Warning: varlt not support for type "%s", replacing with NULL'%self.varBaseType)
				expression=NullOperator()
		else:
			self.PrintWarning('Warning: varlt not support for cardinality "%s", replacing with NULL'%self.varCardinality)
			expression=NullOperator()
		self.parent.AddExpression(expression)


# VarLTE
# ------
#
class VarLTE(VarThing):
	"""
	<!ELEMENT varlte (#PCDATA)>
	
	<!ATTLIST varlte  %I_RespIdent;
					  %I_Index; >
	"""
	def __init__(self,name,attrs,parent):
		VarThing.__init__(self,name,attrs,parent)

	def CloseObject (self):
		self.MakeVariableExpression()
		self.MakeSingleValue(self.varBaseType)
		if self.varCardinality=='single':
			if self.varBaseType in ['integer','float']:
				expression=LTEOperator(self.varExpression,self.valExpression)
			elif self.varBaseType=='string':
				self.PrintWarning("Warning: varlte not supported on String in QTI v2, re-run with --forcefibfloat to treat string fibs as numbers",1)
				expression=CustomOperator("varlte")
				expression.AddExpression(self.varExpression)
				expression.AddExpression(self.valExpression)
			else:
				self.PrintWarning('Warning: varlte not support for type "%s", replacing with NULL'%self.varBaseType)
				expression=NullOperator()
		else:
			self.PrintWarning('Warning: varlte not support for cardinality "%s", replacing with NULL'%self.varCardinality)
			expression=NullOperator()
		self.parent.AddExpression(expression)


	
# VarGT
# -----
#
class VarGT(VarThing):
	"""
	<!ELEMENT vargt (#PCDATA)>
	
	<!ATTLIST vargt  %I_RespIdent;
					   %I_Index; >
	"""
	def __init__(self,name,attrs,parent):
		VarThing.__init__(self,name,attrs,parent)

	def CloseObject (self):
		self.MakeVariableExpression()
		self.MakeSingleValue(self.varBaseType)
		if self.varCardinality=='single':
			if self.varBaseType in ['integer','float']:
				expression=GTOperator(self.varExpression,self.valExpression)
			elif self.varBaseType=='string':
				self.PrintWarning("Warning: vargt not supported on String in QTI v2, re-run with --forcefibfloat to treat string fibs as numbers",1)
				expression=CustomOperator("vargt")
				expression.AddExpression(self.varExpression)
				expression.AddExpression(self.valExpression)
			else:
				self.PrintWarning('Warning: vargt not support for type "%s", replacing with NULL'%self.varBaseType)
				expression=NullOperator()
		else:
			self.PrintWarning('Warning: vargt not support for cardinality "%s", replacing with NULL'%self.varCardinality)
			expression=NullOperator()
		self.parent.AddExpression(expression)


# VarGTE
# ------
#
class VarGTE(VarThing):
	"""
	<!ELEMENT vargte (#PCDATA)>
	
	<!ATTLIST vargte  %I_RespIdent;
					   %I_Index; >
	"""
	def __init__(self,name,attrs,parent):
		VarThing.__init__(self,name,attrs,parent)

	def CloseObject (self):
		self.MakeVariableExpression()
		self.MakeSingleValue(self.varBaseType)
		if self.varCardinality=='single':
			if self.varBaseType in ['integer','float']:
				expression=GTEOperator(self.varExpression,self.valExpression)
			elif self.varBaseType=='string':
				self.PrintWarning("Warning: vargte not supported on String in QTI v2, re-run with --forcefibfloat to treat string fibs as numbers",1)
				expression=CustomOperator("vargte")
				expression.AddExpression(self.varExpression)
				expression.AddExpression(self.valExpression)
			else:
				self.PrintWarning('Warning: vargte not support for type "%s", replacing with NULL'%self.varBaseType)
				expression=NullOperator()
		else:
			self.PrintWarning('Warning: vargte not support for cardinality "%s", replacing with NULL'%self.varCardinality)
			expression=NullOperator()
		self.parent.AddExpression(expression)


# VarSubset
# ---------
#
class VarSubset(VarThing):
	"""
	<!ELEMENT varsubset (#PCDATA)>
	
	<!ATTLIST varsubset  %I_RespIdent;
						  setmatch     (Exact | Partial )  'Exact'
						  %I_Index; >
	"""
	def __init__(self,name,attrs,parent):
		self.exactmatch=1
		VarThing.__init__(self,name,attrs,parent)

	def SetAttribute_setmatch (self,value):
		if value.lower()=='partial':
			self.exactmatch=0
		elif value.lower()!='exact':
			self.PrintWarning('Warning: unrecognized setmatch value "'+value+'"') 
	
	def CloseObject (self):
		if self.index:
			self.PrintWarning("Warning: ignoring index on varsubset")
			self.index=None
		self.MakeVariableExpression()
		# sort out lexical representation of point and pair values before constructing
		# the base value operator in future.  Also, sort out multiple value forms for
		# other baseTypes, e.g. comma-separated list of integers.
		self.MakeSingleValue(self.varBaseType)
		if self.varCardinality=='single':
			if self.valCardinality=='single':
				# err, this looks like a simple test of equality...
				self.PrintWarning("Warning: varsubset is being substituted with single match ("+self.identifier+")")
				expression=MatchOperator(self.varExpression,self.valExpression)
			else:
				self.PrintWarning("Error: can't match a subset against a response with single cardinality ("+self.identifier+")")
				expression=None
		else:
			# cardinality=='multiple' or cardinality=='ordered'
			if self.valCardinality=='single':
				# look up a single value in a set, member operation
				expression=MemberOperator(self.valExpression,self.varExpression)
			else:
				# note that varCardinality==valCardinality is gauranteed!
				expression=ContainsOperator(self.varExpression,self.valExpression)
		if expression:
			self.parent.AddExpression(expression)
		


# VarSubtring
# -----------
#
class VarSubstring(VarThing):
	"""
	<!ELEMENT varsubstring (#PCDATA)>
	
	<!ATTLIST varsubstring  %I_Index;
							 %I_RespIdent;
							 %I_Case; >
	"""
	def __init__(self,name,attrs,parent):
		self.caseFlag=0
		VarThing.__init__(self,name,attrs,parent)

	def SetAttribute_case (self,value):
		self.caseFlag=self.ReadYesNo(value,0)
	
	def CloseObject (self):
		self.MakeVariableExpression()
		self.MakeSingleValue(self.varBaseType)
		if self.varBaseType!='string':
			self.PrintWarning("Warning: varsubstring test of non string replaced with null")
			expression=NullOperator()
		elif self.varCardinality!='single':
			self.PrintWarning("Warning: varsubstring test on container replaced with null")
			expression=NullOperator()
		else:
			expression=StringMatchOperator(self.varExpression,self.valExpression,self.caseFlag,1)
		self.parent.AddExpression(expression)


# VarInside
# ---------
#
class VarInside(VarThing):
	"""
	<!ELEMENT varinside (#PCDATA)>
	
	<!ATTLIST varinside  areatype     (Ellipse | Rectangle | Bounded )  #REQUIRED
						  %I_RespIdent;
						  %I_Index; >
	"""
	def __init__(self,name,attrs,parent):
		self.shape='default'
		VarThing.__init__(self,name,attrs,parent)

	def SetAttribute_areatype (self,value):
		shape=value.strip().lower()
		if shape=='rectangle':
			self.shape='rect'
		elif shape=='ellipse':
			self.shape='ellipse'
		elif shape=='bounded':
			self.shape='poly'
		else:
			raise QTIException(eUnknownShape)
	
	def CloseObject (self):
		# This is the clever bit, got hunt down the interaction bound to this response
		self.shape,coords=self.ConvertAreaCoords(self.shape,self.value)
		self.MakeVariableExpression()
		self.parent.AddExpression(InsideOperator(self.varExpression,self.shape,coords))
		
	
# QTIParserV1 Class
# -----------------
#
QTIASI_ELEMENTS={
        'altmaterial':Unsupported,
        'and':AndOperatorV1,
        'and_objects':Unsupported,
        'and_selection':Unsupported,
        'and_test':Unsupported,
        'assessfeedback':Unsupported,
        'assessment':QTIAssessment,
        'assessmentcontrol':Unsupported,
        'assessproc_extension':Unsupported,
        'conditionvar':ConditionVar,
        'decvar':DecVar,
        'displayfeedback':DisplayFeedback,
        'duration':Duration,
        'durequal':Unsupported,
        'durgt':Unsupported,
        'durgte':Unsupported,
        'durlt':Unsupported,
        'durlte':Unsupported,
        'fieldentry':FieldEntry,
        'fieldlabel':FieldLabel,
        'flow':FlowV1,
        'flow_label':FlowLabel,
        'flow_mat':FlowMat,
        'hint':Hint,
        'hintmaterial':HintMaterial,
        'interpretvar':InterpretVar,
        'item':QTIItem,
        'itemcontrol':ItemControl,
        'itemfeedback':ItemFeedback,
        'itemmetadata':ItemMetadata,
        'itempostcondition':Unsupported,
        'itemprecondition':Unsupported,
        'itemproc_extension':Unsupported,
        'itemref':Unsupported,
        'itemrubric':Unsupported,
        'map_output':Unsupported,
        'mat_extension':Unsupported,
        'matapplet':Unsupported,
        'matapplication':Unsupported,
        'mataudio':MatAudio,
        'matbreak':MatBreak,
        'matemtext':MatEmText,
        'material':Material,
        'material_ref':Unsupported,
        'matimage':MatImage,
        'matref':Unsupported,
        'mattext':MatText,
        'matvideo':Unsupported,
        'not':NotOperatorV1,
        'not_objects':Unsupported,
        'not_selection':Unsupported,
        'not_test':Unsupported,
        'objectbank':QTIObjectBank,
        'objectives':Objectives,
        'objects_condition':Unsupported,
        'objects_parameter':Unsupported,
        'objectscond_extension':Unsupported,
        'or':OrOperatorV1,
        'or_objects':Unsupported,
        'or_selection':Unsupported,
        'or_test':Unsupported,
        'order':Unsupported,
        'order_extension':Unsupported,
        'other':OtherOperatorV1,
        'outcomes':Outcomes,
        'outcomes_feedback_test':Unsupported,
        'outcomes_metadata':Unsupported,
        'outcomes_processing':Unsupported,
        'presentation':Presentation,
        'presentation_material':Unsupported,
        'processing_parameter':Unsupported,
        'qmd_computerscored':Unsupported,
        'qmd_feedbackpermitted':Unsupported,
        'qmd_hintspermitted':Unsupported,
        'qmd_itemtype':QMDItemType,
        'qmd_levelofdifficulty':QMDLevelOfDifficulty,
        'qmd_material':Unsupported,
        'qmd_maximumscore':QMDMaximumscore,
        'qmd_renderingtype':Unsupported,
        'qmd_responsetype':Unsupported,
        'qmd_scoringpermitted':Unsupported,
        'qmd_solutionspermitted':Unsupported,
        'qmd_status':QMDStatus,
        'qmd_timedependence':Unsupported,
        'qmd_timelimit':Unsupported,
        'qmd_toolvendor':QMDToolVendor,
        'qmd_topic':QMDTopic,
        'qmd_typeofsolution':Unsupported,
        'qmd_weighting':Unsupported,
        'qticomment':QTIComment,
        'qtimetadata':QTIMetadata,
        'qtimetadatafield':QTIMetadataField,
        'questestinterop':QuesTestInterop,
        'reference':Unsupported,
        'render_choice':RenderChoice,
        'render_extension':Unsupported,
        'render_fib':RenderFib,
        'render_hotspot':RenderHotspot,
        'render_slider':RenderSlider,
        'respcond_extension':Unsupported,
        'respcondition':RespCondition,
        'response_extension':Unsupported,
        'response_grp':ResponseGrp,
        'response_label':ResponseLabel,
        'response_lid':ResponseLID,
        'response_na':Unsupported,
        'response_num':ResponseNum,
        'response_str':ResponseStr,
        'response_xy':ResponseXY,
        'resprocessing':ResProcessing,
        'rubric':Rubric,
        'section':QTISection,
        'sectioncontrol':Unsupported,
        'sectionfeedback':Unsupported,
        'sectionpostcondition':Unsupported,
        'sectionprecondition':Unsupported,
        'sectionproc_extension':Unsupported,
        'sectionref':Unsupported,
        'selection':Unsupported,
        'selection_extension':Unsupported,
        'selection_metadata':Unsupported,
        'selection_ordering':Unsupported,
        'sequence_parameter':Unsupported,
        'setvar':SetVar,
        'solution':Solution,
        'solutionmaterial':SolutionMaterial,
        'sourcebank_ref':Unsupported,
        'test_variable':Unsupported,
        'unanswered':Unanswered,
        'var_extension':Unsupported,
        'varequal':VarEqual,
        'vargt':VarGT,
        'vargte':VarGTE,
        'variable_test':Unsupported,
        'varinside':VarInside,
        'varlt':VarLT,
        'varlte':VarLTE,
        'varsubset':VarSubset,
        'varsubstring':VarSubstring,
        'vocabulary':Vocabulary
	}

class QTIParserV1(handler.ContentHandler, handler.ErrorHandler):
	"""QTI Parser"""
	def __init__(self,options):
		self.options=options
		self.parser=make_parser()
		self.parser.setFeature(handler.feature_namespaces,0)
		self.parser.setFeature(handler.feature_validation,0)
		self.parser.setContentHandler(self)
		self.parser.setErrorHandler(self)
		self.parser.setEntityResolver(self)
		self.elements=QTIASI_ELEMENTS
		if self.options.qmdExtensions:
			self.elements['qmd_keywords']=QMDKeywords
			self.elements['qmd_domain']=QMDDomain
			self.elements['qmd_description']=QMDDescription
			self.elements['qmd_title']=QMDTitle
			self.elements['qmd_author']=QMDContributor
			self.elements['qmd_organisation']=QMDOrganisation
		self.cp=ContentPackage()
		self.currPath=None
	
	def ProcessFiles (self,basepath,files):
		f=None
		for fileName in files:
			path=os.path.join(basepath,fileName)
			if os.path.isdir(path):
				print "Processing directory: : "+path
				children=os.listdir(path)
				self.ProcessFiles(path,children)
			elif fileName[-4:].lower()=='.xml':
				print "Processing file: "+path
				f=open(path,'r')
				try:
					self.Parse(f,path)
				finally:
					f.close()

	def DumpCP (self):
		if self.options.cpPath:
			self.cp.DumpToDirectory(self.options.cpPath)
					
	def Parse (self,f,path):
		self.currPath=path
		self.gotRoot=0
		self.cObject=None
		self.objStack=[]
		self.skipMode=0
		try:
			self.parser.parse(f)
		except SAXParseException:
			if self.gotRoot:
				print "WARNING: Error following final close tag ignored"
				print str(sys.exc_info()[0])+": "+str(sys.exc_info()[1])
			else:
				print "ERROR: parsing %s"%path
				print "       ("+str(sys.exc_info()[0])+": "+str(sys.exc_info()[1])+")"
		self.currPath=None

	def resolveEntity(self,publicID,systemID):
		print "Resolving: PUBLIC %s SYSTEM %s"%(publicID,systemID)
		if self.options.dtdDir:
			systemID=os.path.join(self.options.dtdDir,'ims_qtiasiv1p2.dtd')
		print "Returning: %s"%systemID
		return systemID
	
	def startElement(self, name, attrs):
		parent=self.cObject
		if parent is None:
			assert not self.gotRoot, QTIException(assertElementOutsideRoot)
		self.objStack.append(self.cObject)
		if self.skipMode:
			self.cObject=Skipped(name,attrs,parent)
		elif isinstance(self.cObject,(MatThing,RawMaterial)):
			# tags inside MatThing should have been escaped in CDATA sections
			self.cObject=RawMaterial(name,attrs,parent)
		else:
			if self.elements.has_key(name):
				self.cObject=self.elements[name](name,attrs,parent)
				if isinstance(self.cObject,QuesTestInterop):
					self.cObject.SetCP(self.cp)
					self.cObject.SetPath(self.currPath)
					self.cObject.SetParser(self)
			else:
				self.cObject=Unsupported(name,attrs,parent)
			if isinstance(self.cObject,Unsupported):
				self.skipMode=len(self.objStack)
	
	def characters(self,ch):
		self.cObject.AddData(ch)
			
	def endElement(self,name):
		parent=self.objStack.pop()
		self.cObject.CloseObject()
		if self.skipMode>len(self.objStack):
			self.skipMode=0
		if parent is None:
			# This must be the end of the parse
			self.gotRoot=1
		else:
			self.cObject=parent


	
"""
<?xml version='1.0' encoding='UTF-8' ?>

<!--Generated by Turbo XML 2.3.1.100.-->

<!--	*******************************************************		-->
<!--																-->
<!--	TITLE:		ims_qtiasiv1p2p1.dtd							-->
<!--	TYPE:		IMS Question and Test Interoperability			-->
<!--				Assessment, Section, Item structure	and			-->
<!--				Objects-bank.									-->
<!--																-->
<!--	REVISION HISTORY:											-->
<!--	Date	        Author										-->
<!--	====	        ======										-->
<!--	14th Feb 2003	Colin Smythe								-->
<!--																-->
<!--	This specification has been approved as a Final release.	-->
<!--																-->
<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--					ROOT DEFINITION								-->
<!--	*******************************************************		-->

<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--					ENTITY DEFINITIONS							-->
<!--	*******************************************************		-->
<!ENTITY % I_Testoperator " testoperator  (EQ | NEQ | LT | LTE | GT | GTE )  #REQUIRED">

<!ENTITY % I_Pname " pname CDATA  #REQUIRED">

<!ENTITY % I_Class " class CDATA  'Block'">

<!ENTITY % I_Mdoperator " mdoperator  (EQ | NEQ | LT | LTE | GT | GTE )  #REQUIRED">

<!ENTITY % I_Mdname " mdname CDATA  #REQUIRED">

<!ENTITY % I_Title " title CDATA  #IMPLIED">

<!ENTITY % I_Label " label CDATA  #IMPLIED">

<!ENTITY % I_Ident " ident CDATA  #REQUIRED">

<!ENTITY % I_View " view  (All | 
          Administrator | 
          AdminAuthority | 
          Assessor | 
          Author | 
          Candidate | 
          InvigilatorProctor | 
          Psychometrician | 
          Scorer | 
          Tutor )  'All'">

<!ENTITY % I_FeedbackSwitch " feedbackswitch  (Yes | No )  'Yes'">

<!ENTITY % I_HintSwitch " hintswitch  (Yes | No )  'Yes'">

<!ENTITY % I_SolutionSwitch " solutionswitch  (Yes | No )  'Yes'">

<!ENTITY % I_Rcardinality " rcardinality  (Single | Multiple | Ordered )  'Single'">

<!ENTITY % I_Rtiming " rtiming  (Yes | No )  'No'">

<!ENTITY % I_Uri " uri CDATA  #IMPLIED">

<!ENTITY % I_X0 " x0 CDATA  #IMPLIED">

<!ENTITY % I_Y0 " y0 CDATA  #IMPLIED">

<!ENTITY % I_Height " height CDATA  #IMPLIED">

<!ENTITY % I_Width " width CDATA  #IMPLIED">

<!ENTITY % I_Embedded " embedded CDATA  'base64'">

<!ENTITY % I_LinkRefId " linkrefid CDATA  #REQUIRED">

<!ENTITY % I_VarName " varname CDATA  'SCORE'">

<!ENTITY % I_RespIdent " respident CDATA  #REQUIRED">

<!ENTITY % I_Continue " continue  (Yes | No )  'No'">

<!ENTITY % I_CharSet " charset CDATA  'ascii-us'">

<!ENTITY % I_ScoreModel " scoremodel CDATA  #IMPLIED">

<!ENTITY % I_MinNumber " minnumber CDATA  #IMPLIED">

<!ENTITY % I_MaxNumber " maxnumber CDATA  #IMPLIED">

<!ENTITY % I_FeedbackStyle " feedbackstyle  (Complete | Incremental | Multilevel | Proprietary )  'Complete'">

<!ENTITY % I_Case " case  (Yes | No )  'No'">

<!ENTITY % I_EntityRef " entityref ENTITY  #IMPLIED">

<!ENTITY % I_Index " index CDATA  #IMPLIED">

<!ELEMENT qmd_computerscored (#PCDATA)>

<!ELEMENT qmd_feedbackpermitted (#PCDATA)>

<!ELEMENT qmd_hintspermitted (#PCDATA)>

<!ELEMENT qmd_renderingtype (#PCDATA)>

<!ELEMENT qmd_responsetype (#PCDATA)>

<!ELEMENT qmd_scoringpermitted (#PCDATA)>

<!ELEMENT qmd_solutionspermitted (#PCDATA)>

<!ELEMENT qmd_timedependence (#PCDATA)>

<!ELEMENT qmd_timelimit (#PCDATA)>

<!ELEMENT qmd_material (#PCDATA)>

<!ELEMENT qmd_typeofsolution (#PCDATA)>

<!ELEMENT qmd_weighting (#PCDATA)>

<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--				COMMON OBJECT DEFINITIONS						-->
<!--	*******************************************************		-->

<!ELEMENT matvideo (#PCDATA)>

<!ATTLIST matvideo  videotype   CDATA  'video/avi'
                     %I_Label;
                     %I_Uri;
                     %I_Width;
                     %I_Height;
                     %I_Y0;
                     %I_X0;
                     %I_Embedded;
                     %I_EntityRef; >
<!ELEMENT matapplet (#PCDATA)>

<!ATTLIST matapplet  %I_Label;
                      %I_Uri;
                      %I_Y0;
                      %I_Height;
                      %I_Width;
                      %I_X0;
                      %I_Embedded;
                      %I_EntityRef; >
<!ELEMENT matapplication (#PCDATA)>

<!ATTLIST matapplication  apptype     CDATA  #IMPLIED
                           %I_Label;
                           %I_Uri;
                           %I_Embedded;
                           %I_EntityRef; >

<!ELEMENT matref EMPTY>

<!ATTLIST matref  %I_LinkRefId; >
<!ELEMENT material_ref EMPTY>

<!ATTLIST material_ref  %I_LinkRefId; >
<!ELEMENT altmaterial (qticomment? , (mattext | matemtext | matimage | mataudio | matvideo | matapplet | matapplication | matref | matbreak | mat_extension)+)>

<!ATTLIST altmaterial  xml:lang CDATA  #IMPLIED >

<!ELEMENT durequal (#PCDATA)>

<!ATTLIST durequal  %I_Index;
                     %I_RespIdent; >
<!ELEMENT durlt (#PCDATA)>

<!ATTLIST durlt  %I_Index;
                  %I_RespIdent; >
<!ELEMENT durlte (#PCDATA)>

<!ATTLIST durlte  %I_Index;
                   %I_RespIdent; >
<!ELEMENT durgt (#PCDATA)>

<!ATTLIST durgt  %I_Index;
                  %I_RespIdent; >
<!ELEMENT durgte (#PCDATA)>

<!ATTLIST durgte  %I_Index;
                   %I_RespIdent; >

<!ELEMENT presentation_material (qticomment? , flow_mat+)>

<!ELEMENT reference (qticomment? , (material | mattext | matemtext | matimage | mataudio | matvideo | matapplet | matapplication | matbreak | mat_extension)+)>

<!ELEMENT selection_ordering (qticomment? , sequence_parameter* , selection* , order?)>

<!ATTLIST selection_ordering  sequence_type CDATA  #IMPLIED >
<!ELEMENT outcomes_processing (qticomment? , outcomes , objects_condition* , processing_parameter* , map_output* , outcomes_feedback_test*)>

<!ATTLIST outcomes_processing  %I_ScoreModel; >
<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--					EXTENSION DEFINITIONS						-->
<!--	*******************************************************		-->
<!ELEMENT mat_extension ANY>

<!ELEMENT var_extension ANY>

<!ELEMENT response_extension ANY>

<!ELEMENT render_extension ANY>

<!ELEMENT assessproc_extension ANY>

<!ELEMENT sectionproc_extension ANY>

<!ELEMENT itemproc_extension ANY>

<!ELEMENT respcond_extension ANY>

<!ELEMENT selection_extension ANY>

<!ELEMENT objectscond_extension (#PCDATA)>

<!ELEMENT order_extension ANY>

<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--				ASSESSMENT OBJECT DEFINITIONS					-->
<!--	*******************************************************		-->
<!ELEMENT assessmentcontrol (qticomment?)>

<!ATTLIST assessmentcontrol  %I_HintSwitch;
                              %I_SolutionSwitch;
                              %I_View;
                              %I_FeedbackSwitch; >
<!ELEMENT assessfeedback (qticomment? , (material+ | flow_mat+))>

<!ATTLIST assessfeedback  %I_View;
                           %I_Ident;
                           %I_Title; >
<!ELEMENT sectionref (#PCDATA)>

<!ATTLIST sectionref  %I_LinkRefId; >
<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--				SECTION OBJECT DEFINITIONS						-->
<!--	*******************************************************		-->
<!ELEMENT sectionprecondition (#PCDATA)>

<!ELEMENT sectionpostcondition (#PCDATA)>

<!ELEMENT sectioncontrol (qticomment?)>

<!ATTLIST sectioncontrol  %I_FeedbackSwitch;
                           %I_HintSwitch;
                           %I_SolutionSwitch;
                           %I_View; >
<!ELEMENT itemref (#PCDATA)>

<!ATTLIST itemref  %I_LinkRefId; >
<!ELEMENT sectionfeedback (qticomment? , (material+ | flow_mat+))>

<!ATTLIST sectionfeedback  %I_View;
                            %I_Ident;
                            %I_Title; >
<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--					ITEM OBJECT DEFINITIONS						-->
<!--	*******************************************************		-->
<!ELEMENT itemprecondition (#PCDATA)>

<!ELEMENT itempostcondition (#PCDATA)>

<!ELEMENT itemrubric (material)>

<!ATTLIST itemrubric  %I_View; >

<!ELEMENT response_na ANY>

<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--		SELECTION AND ORDERING OBJECT DEFINITIONS				-->
<!--	*******************************************************		-->
<!ELEMENT selection (sourcebank_ref? , selection_number? , selection_metadata? , (and_selection | or_selection | not_selection | selection_extension)?)>

<!ELEMENT order (order_extension?)>

<!ATTLIST order  order_type CDATA  #REQUIRED >
<!ELEMENT selection_number (#PCDATA)>

<!ELEMENT selection_metadata (#PCDATA)>

<!ATTLIST selection_metadata  %I_Mdname;
                               %I_Mdoperator; >
<!ELEMENT sequence_parameter (#PCDATA)>

<!ATTLIST sequence_parameter  %I_Pname; >
<!ELEMENT sourcebank_ref (#PCDATA)>

<!ELEMENT and_selection (selection_metadata | and_selection | or_selection | not_selection)+>

<!ELEMENT or_selection (selection_metadata | and_selection | or_selection | not_selection)+>

<!ELEMENT not_selection (selection_metadata | and_selection | or_selection | not_selection)>

<!--	+++++++++++++++++++++++++++++++++++++++++++++++++++++++		-->
<!--	*******************************************************		-->
<!--			OUTCOMES PREOCESSING OBJECT DEFINITIONS				-->
<!--	*******************************************************		-->
<!ELEMENT objects_condition (qticomment? , (outcomes_metadata | and_objects | or_objects | not_objects)? , objects_parameter* , map_input* , objectscond_extension?)>

<!ELEMENT map_output (#PCDATA)>

<!ATTLIST map_output  %I_VarName; >
<!ELEMENT map_input (#PCDATA)>

<!ATTLIST map_input  %I_VarName; >
<!ELEMENT outcomes_feedback_test (test_variable , displayfeedback+)>

<!ATTLIST outcomes_feedback_test  %I_Title; >
<!ELEMENT outcomes_metadata (#PCDATA)>

<!ATTLIST outcomes_metadata  %I_Mdname;
                              %I_Mdoperator; >
<!ELEMENT and_objects (outcomes_metadata | and_objects | or_objects | not_objects)+>

<!ELEMENT or_objects (outcomes_metadata | and_objects | or_objects | not_objects)+>

<!ELEMENT not_objects (outcomes_metadata | and_objects | or_objects | not_objects)>

<!ELEMENT test_variable (variable_test | and_test | or_test | not_test)>

<!ELEMENT processing_parameter (#PCDATA)>

<!ATTLIST processing_parameter  %I_Pname; >
<!ELEMENT and_test (variable_test | and_test | or_test | not_test)+>

<!ELEMENT or_test (variable_test | and_test | or_test | not_test)+>

<!ELEMENT not_test (variable_test | and_test | or_test | not_test)>

<!ELEMENT variable_test (#PCDATA)>

<!ATTLIST variable_test  %I_VarName;
                          %I_Testoperator; >
<!ELEMENT objects_parameter (#PCDATA)>

<!ATTLIST objects_parameter  %I_Pname; >
"""