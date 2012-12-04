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
import os, sys, re
from xml.sax import make_parser, handler, SAXParseException
import StringIO
from random import randint
try:
	import vobject
	GOT_VOBJECT=1
except:
	GOT_VOBJECT=0
	
RESPONSE_PREFIX="RESPONSE_"
OUTCOME_PREFIX="OUTCOME_"
FEEDBACK_PREFIX="FEEDBACK_"
CURRENT_FILE_NAME=None

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
		self.prepend_path=None
		self.create_error_files=None
		
		
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
eUnknownShape="Unknown shape"
eNoParentPackage="QTI object outside <questestinterop> element"
eInvalidStructure="QTI object in unexpected location"
eEmptyCondition="QTI <conditionvar> contained no expressions"
eUndeclaredResponse="Reference to undeclared response variable"
eUndeclaredOutcome="Reference to undeclared outcome variable"
eUnimplementedOperator="Unimplemented operator"
eDuplicateVariable="Duplicate variable name"
eIndexIntoMultiple="Index into multiple"
eUnexpectedContainer="Unexpected Container"
eUnexpectedVarAction="Unexpected Var Action"
eTooManySimilarVariables="Too many similar variables"
eDuplicateResponse="Duplicate Response"
eUnboundResponse="Unbound Response"
eNoParentItem="No parent item"
eNoParentMDContainer="No parent metadata container"

# Exceptions that should never happen!
assertElementOutsideRoot="Element outside root"

VIEWMAP={'administrator':'invigilator','adminauthority':'invigilator',
	'assessor':'scorer','author':'author','candidate':'candidate',
	'invigilator':'invigilator','proctor':'invigilator','psychometrician':'scorer',
	'tutor':'tutor',
	'scorer':'scorer'}

D2L_IDENTIFIER_REPLACER = re.compile(r'_(?:ans|str)$', flags=re.I)

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
			elif aName[:6]=='webct:':
				f=getattr(self,'SetAttribute_webct_'+aName[6:],0)
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
		token = token.strip()
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

	def GetInstructureHelperContainer(self):
		assert self.parent,QTIException(eNoParentMDContainer)
		return self.parent.GetInstructureHelperContainer()
	
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

	def CheckLocation (self, expected_parents, tag, do_assert=True):
		if not isinstance(self.parent, expected_parents):
			if do_assert:
				raise QTIException(eInvalidStructure,tag)
			else:
				print "Tag (%s) in unexpected location - parent: (%s)" % (tag, self.parent)
			return False
		return True


class Manifest(QTIObjectV1):
	def __init__(self, name, attrs, parent):
		self.resource=CPResource()
		self.resource.SetType("webcontent")
		self.parent = parent
		self.files={}
		self.path=None
		self.cp=None
	
	def SetPath (self,path):
		if self.path is None:
			self.path=path

	def SetCP(self,cp):
		self.cp=cp
		self.cp.AddResource(self.resource)

	def AddCPFile (self,uri):
		if uri[-4:].lower() in ['.xml', '.dat', '.qti']:
			return uri
		if self.files.has_key(uri):
			# We've already added this file to the content package
			return self.files[uri]
		cpf=CPFile()
		cpf.SetHREF(uri)
		root=self.GetRoot()
		path=root.ResolveURI(uri)
		cpf.SetDataPath(path)
		self.resource.AddFile(cpf,0)
		self.files[uri]=uri
		return uri

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

	def update_file_path(self, path):
		if len(self.files) == 1:
			uri = self.files.values()[0]
			if uri != path:
				self.resource.update_file_path(uri, path, self.GetRoot().ResolveURI(uri))


class Resources(QTIObjectV1):
	def __init__(self, name, attrs, parent):
		self.parent = parent
		self.in_manifest = self.CheckLocation((Manifest),"<resources>", False)
		if self.in_manifest:
			self.manifest = parent

	def AddCPFile(self, uri):
		if self.in_manifest:
			self.manifest.AddCPFile(uri)

class Resource(QTIObjectV1):
	def __init__(self, name, attrs, parent):
		self.parent = parent
		self.in_manifest = self.CheckLocation((Resources),"<resources>", False)
		if self.in_manifest:
			self.manifest = parent

	def AddCPFile(self, uri):
		if self.in_manifest:
			self.manifest.AddCPFile(uri)

class File(QTIObjectV1):
	def __init__(self, name, attrs, parent):
		self.parent = parent
		self.in_manifest = self.CheckLocation((Resource),"<file>", False)
		if self.in_manifest:
			self.manifest = parent
			self.ParseAttributes(attrs)

	def SetAttribute_href (self,href):
		if self.in_manifest:
			self.manifest.AddCPFile(href)


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
		self.parent = parent
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

	def GetBankId(self):
		if CURRENT_FILE_NAME:
			return CURRENT_FILE_NAME
		else:
			return None

	def GetBankName(self):
		return self.GetBankId
		
	def AddResource (self,resource):
		self.resources.append(resource)
		self.cp.AddResource(resource)

	def AddSection (self,id):
		pass
	
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


# InstructureHelperContainer
# --------------------
#
class InstructureHelperContainer(QTIMetadataContainer):
	def __init__(self):
		self.sessionControl=None
		self.showTotalScore=None
		self.whichAttemptToGrade=None
		self.assessmentType=None
		self.instructureMetadata=None
		self.bb_id=None
		self.bb_assessment_type=None
		self.bb_question_type=None
		self.question_type=None
		self.bb_max_score=None
		self.points_possible=None
		self.calculated=None
	
	def GetInstructureHelperContainer(self):
		return self
	
	def set_calculated(self, c):
		self.calculated = c
		self.SetQuestionType("Calculated")
		
	def SetMaxAttempts(self,attempts):
		if isinstance(self, QTIObjectBank): return
		if not self.sessionControl: self.sessionControl = ItemSessionControl()
		self.sessionControl.SetMaxAttempts(attempts)
	
	def SetShowFeedback(self, show):
		if not self.sessionControl: self.sessionControl = ItemSessionControl()
		self.sessionControl.SetShowFeedback(show)
		
	def SetWhichAttemptToGrade(self, which):
		self.whichAttemptToGrade = which
		
	def SetShowTotalScore(self, show):
		self.showTotalScore = show

	def AddMetaField(self, key, val):
		if not self.instructureMetadata: self.instructureMetadata = InstructureMetadata()
		self.instructureMetadata.AddMetaField(key, val)

	def SetPointsPossible(self, points):
		self.AddMetaField("points_possible", points)

	def SetAssessmentQuestionIdentiferref(self, ref):
		self.AddMetaField("assessment_question_identifierref", ref)
	
	def SetAssessmentType(self, type):
		self.assessmentType = type
	
	def StartMatchingList(self):
		if not self.instructureMetadata: self.instructureMetadata = InstructureMetadata()
		self.instructureMetadata.StartMatchingList()
	
	def AddMatchingItem(self, item):
		self.instructureMetadata.AddMatchingItem(item)

	def SetQuestionBank(self, name, id=None):
		self.AddMetaField("question_bank", name)
		if id:
			self.AddMetaField("question_bank_iden", id)

	def SetBBObjectID(self, id):
		self.SetAttribute_ident(id)
		self.bb_id = id
	
	def SetBBAssessmentType(self, type):
		""" Possible values for BB8: Test, Pool, Survey
		"""
		self.bb_assessment_type = type

	def SetBBQuestionType(self, type):
		"""These are the possible BB8 values:
		Multiple Choice, Calculated, Numeric, Either/Or, Essay, 
		File Upload, Fill in the Blank Plus, Fill in the Blank, 
		Hot Spot, Jumbled Sentence, Matching, Multiple Answer, 
		Multiple Choice, Opinion Scale, Ordering, Quiz Bowl, 
		Short Response, True/False
		"""
		self.bb_question_type = type
		self.AddMetaField("bb_question_type", type)

	def SetQuestionType(self, type):
		"""These are the known values:
		Matching - Only seen from respondus
		"""
		self.question_type = type
		self.AddMetaField("question_type", type)
	
	def SetBBMaxScore(self, max):
		self.bb_max_score = max
		self.AddMetaField("max_score", max)

# QTIObjectBank
# -------------
#
class QTIObjectBank(InstructureHelperContainer):
	"""
	<!ELEMENT objectbank (qticomment? , qtimetadata* , (section | item)+)>

	<!ATTLIST objectbank  %I_Ident; >
	"""
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.question_bank = None
		self.question_bank_name = None
		self.CheckLocation((QuesTestInterop),"<objectbank>")
		self.PrintWarning('Warning: objectbank not supported, looking inside for items')
		self.ParseAttributes(attrs)
		
	def SetAttribute_ident (self,id):
		self.question_bank = id

	def SetBankName(self, name):
		self.question_bank_name = name

	def GetBankId(self):
		return self.question_bank

	def GetBankName(self):
		if self.question_bank_name:
			return self.question_bank_name
		else:
			return self.question_bank

	def AddSection (self,id):
		pass
		
# mat_extension
# -------------
#
class WCTMatExtension(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.PrintWarning('Warning: mat_extension not supported, looking inside for needed data.')
		self.calc = None

	def GetCalculated(self):
		if not self.calc: self.calc = Calculated()
		return self.calc

	def add_formula(self, formula):
		self.GetCalculated()
		self.calc.formula = formula
		
	def AppendElement(self, data):
		self.parent.AppendElement(data)

	def CloseObject(self):
		if self.calc:
			self.GetInstructureHelperContainer().set_calculated(self.calc)
		

## D2L Calculated classes

class D2LVariable(QTIObjectV1):

	def __init__(self, name, attrs, parent):
		self.parent = parent
		self.CheckLocation((WCTMatExtension),"<variable>")
		self.calc = parent.GetCalculated()
		self.var = Var()
		self.ParseAttributes(attrs)

	def SetAttribute_name(self, name):
		self.var.name = name

	def set_min(self, min):
		self.var.min = min

	def set_max(self, max):
		self.var.max = max

	def set_decimal(self, val):
		self.var.scale = val

	def CloseObject(self):
		self.calc.add_var(self.var)

class D2LMinvalue(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((D2LVariable),"<minvalue>")

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.set_min(self.data)

class D2LMaxvalue(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((D2LVariable),"<maxvalue>")

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.set_max(self.data)

class D2LDecimalplaces(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((D2LVariable),"<decimalplaces>")

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.set_decimal(self.data)

class BBMatFormattedText(QTIObjectV1):
	"""Holds question and response data in BB8 exports.
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.type=None

	def SetAttribute_type(self, type):
		self.type = type

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.AppendElement(xhtml_text(self.data))

		
# webct:ContentObject
# -------------
#
class WCTContentObject(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.file_name = None
		self.file_path = None
		self.co_type
		self.in_manifest = self.CheckLocation((Manifest),"<webct:ContentObject>", False)
		self.ParseAttributes(attrs)

	def SetAttribute_webct_coType (self,type):
		self.co_type = type

	def CloseObject(self):
		if self.in_manifest and self.co_type == "webct.file" and self.file_name and self.file_path:
			self.parent.update_file_path(os.path.join(self.file_path, self.file_name))

# webct:Name
# -------------
#
class WCTName(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.in_content_object = self.CheckLocation((WCTContentObject),"<webct:WCTName>", False)

	def AddData (self,data):
		if self.in_content_object:
			self.parent.file_name = data

# webct:Path
# -------------
#
class WCTPath(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.in_content_object = self.CheckLocation((WCTContentObject),"<webct:WCTPath>", False)

	def AddData (self,data):
		if self.in_content_object:
			self.parent.file_path = data

# material_table
# -------------
#
class WCTMaterialTable(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.PrintWarning('Warning: material_table not supported, looking inside for needed data')

	def SetAttribute_label (self,id):
		pass


class WCTCalculatedAnswer(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.ihc = self.GetInstructureHelperContainer()
		self.calc = self.ihc.calculated
		self.CheckLocation((ItemProcExtension),"<calculated>")
		self.ParseAttributes(attrs)
	
	def SetAttribute_webct_precision(self, precision):
		self.calc.answer_scale = precision
	
	def SetAttribute_webct_toleranceType(self, type):
		self.calc.answer_tolerance_type = type
	
	def SetAttribute_webct_tolerance(self, tol):
		self.calc.answer_tolerance = tol
		
	def AddRule(self, rule):
		if rule.identifier and rule.identifier == "SCORE":
			if rule.expression and rule.expression.arguments:
				if rule.expression.arguments[1]:
					self.ihc.SetBBMaxScore(rule.expression.arguments[1].value)
		
# calculated
# -------------
#
class CalculatedNode(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.GetInstructureHelperContainer().SetBBQuestionType("Calculated")
		self.CheckLocation((ItemProcExtension, WCTMatExtension),"<calculated>")
		self.calc = Calculated()
	
	def add_var(self, var):
		self.calc.add_var(var)
		
	def add_var_set(self, var):
		self.calc.add_var_set(var)

	def add_formula (self, formula):
		self.calc.formula = formula
	
	def CloseObject(self):
		self.GetInstructureHelperContainer().set_calculated(self.calc)


# formula
# -------------
#
class CalculatedFormula(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode, CalculatedFormulas, WCTMatExtension),"<formula>")
		
	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.add_formula(self.data)

# formulas
# -------------
#
class CalculatedFormulas(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.CheckLocation((CalculatedNode),"<formulas>")
		self.ParseAttributes(attrs)

	def SetAttribute_decimal_places(self, places):
		self.parent.calc.formula_decimal_places = places

	def add_formula (self, formula):
		self.parent.calc.add_formula(formula)

	def CloseObject (self):
		pass

# answer_scale
# -------------
#
class BB8AnswerScale(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<answer_scale>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.answer_scale = self.data
		
# answer_tolerance
# -------------
#
class BB8AnswerTolerance(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<answer_tolerance>")
		self.ParseAttributes(attrs)
		
	def AddData (self,data):
		self.data=self.data+data
	
	def SetAttribute_type(self, type):
		self.parent.calc.answer_tolerance_type = type
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.answer_tolerance = self.data
		
# unit_points_percent
# -------------
#
class BB8UnitPointsPercent(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<unit_points_percent>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.unit_points_percent = self.data
		
# unit_required
# -------------
#
class BB8UnitRequired(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<unit_required>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.unit_required = self.data
		
# unit_value
# -------------
#
class BB8UnitValue(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<unit_value>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.unit_value = self.data
		
# unit_case_sensitive
# -------------
#
class BB8UnitCaseSensitive(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<unit_case_sensitive>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.unit_case_sensitive = self.data
		
# partial_credit_points_percent
# -------------
#
class BB8PartialCreditPointsPercent(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<partial_credit_points_percent>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.partial_credit_points_percent = self.data
		
# partial_credit_tolerance
# -------------
#
class BB8PartialCreditTolerance(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode),"<partial_credit_tolerance>")
		self.ParseAttributes(attrs)
		
	def AddData (self,data):
		self.data=self.data+data
	
	def SetAttribute_type(self, type):
		self.parent.calc.partial_credit_tolerance_type = type
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.calc.partial_credit_tolerance = self.data

# vars
# -------------
#
class BB8Vars(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.CheckLocation((CalculatedNode),"<vars>")
		self.calc = parent.calc
	
	def add_var(self, var):
		self.calc.add_var(var)

# var_sets
# -------------
#
class BB8VarSets(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.CheckLocation((CalculatedNode),"<var_sets>")
		self.calc = parent.calc
	
	def add_var_set(self, var):
		self.calc.add_var_set(var)
		
# var_set
# -------------
#
class CalculatedVarSet(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.CheckLocation((BB8VarSets, CalculatedNode),"<var_set>")
		self.var_set = VarSet()
		self.ParseAttributes(attrs)
	
	def SetAttribute_ident(self, iden):
		self.var_set.ident = iden
	
	def add_var(self, var):
		self.var_set.add_var(var)
	
	def set_answer(self, answer):
		self.var_set.answer=answer
	
	def CloseObject (self):
		self.parent.add_var_set(self.var_set)
		
# var
# -------------
#
class BB8Var(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedVarSet, BB8Vars),"<var>")
		self.var = Var()
		self.ParseAttributes(attrs)
	
	def SetAttribute_name(self, name):
		self.var.name = name
	
	def SetAttribute_scale(self, scale):
		self.var.scale = scale
	
	def set_min(self, min):
		self.var.min = min
	
	def set_max(self, max):
		self.var.max = max
	
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data and not self.data == "":
			self.var.data = self.data
		self.parent.add_var(self.var)
		
# var
# -------------
#
class WCTVar(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((CalculatedNode, CalculatedVarSet),"<var>")
		self.var = Var()
		self.ParseAttributes(attrs)
	
	def SetAttribute_webct_name(self, name):
		self.var.name = name
	
	def SetAttribute_webct_precision(self, scale):
		self.var.scale = scale
	
	def SetAttribute_webct_min(self, min):
		self.var.min = min
	
	def SetAttribute_webct_max(self, max):
		self.var.max = max
	
	def SetAttribute_webct_value(self, value):
		self.var.data = value
	
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.parent.add_var(self.var)

		
# min
# -------------
#
class BB8Min(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((BB8Var),"<min>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.set_min(self.data)
		
# max
# -------------
#
class BB8Max(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((BB8Var),"<max>")
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		self.parent.set_max(self.data)
		
# answer
# -------------
#
class CalculatedAnswer(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.value = None
		self.CheckLocation((CalculatedVarSet),"<answer>")
		self.ParseAttributes(attrs)
		
	def SetAttribute_webct_value(self, value):
		self.value = value
		self.parent.set_answer(value)
		
	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		if self.value: return
		self.data=self.data.strip()
		self.parent.set_answer(self.data)

				
# webct:matching_ext_flow
# -------------
#
class WCTMatchingExtFlow(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.GetInstructureHelperContainer().StartMatchingList()
		
	def SetAttribute_rshuffle (self,id):
		pass
		
	def SetAttribute_rhidden (self,id):
		pass
		
	def SetAttribute_labelType (self,id):
		pass
	
				
# webct:matching_text_ext
# -------------
#
class WCTMatchingTextExt(QTIObjectV1):
	"""
	"""
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		self.label = None
		
	def SetAttribute_rshuffle (self,id):
		pass
		
	def SetAttribute_label (self,label):
		pass
	
	def SetAttribute_xml_lang (self,lang):
		self.language=lang
	
	def AppendElement (self,element):
		self.GetInstructureHelperContainer().AddMatchingItem(element.text.strip())
	
# QTIAssessment
# -------------
#
class QTIAssessment(InstructureHelperContainer):
	"""
	<!ELEMENT assessment (qticomment? , duration? , qtimetadata* , objectives* , assessmentcontrol* , rubric* , presentation_material? , outcomes_processing* , assessproc_extension? , assessfeedback* , selection_ordering? , reference? , (sectionref | section)+)>
	
	<!ATTLIST assessment  %I_Ident;
						   %I_Title;
						   xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		global CURRENT_FILE_NAME
		InstructureHelperContainer.__init__(self)
		self.parent=parent
		self.parser=self.GetParser()
		self.fName=None
		self.assessment=AssessmentTest()
		self.question_bank = None
		# This is the manifest object
		self.resource=CPResource()
		self.resource.SetType("imsqti_assessment_xmlv2p1")
		self.educationalMetadata=None
		self.variables={'FEEDBACK':None}
		self.warnings={}
		self.msg=""
		self.ParseAttributes(attrs)
		if not self.assessment.identifier and CURRENT_FILE_NAME:
			self.SetAttribute_ident(CURRENT_FILE_NAME)
		elif not self.assessment.identifier:
			self.SetAttribute_ident("%s" % randint(1,100000))
		if attrs.has_key('ident'):
			print '-- Converting item id="'+attrs['ident']+'" --'
		if not self.assessment.language and self.parser.options.lang:
			self.assessment.SetLanguage(self.parser.options.lang)
		# Set the name of the file
		if not self.fName:
			cp=self.GetRoot().cp
			# Reserve space for our preferred file name
			self.fName=cp.GetUniqueFileName(os.path.join("assessmentTests",self.resource.id+".xml"))
		self.files={}
		
	def SetAttribute_ident (self,value):
		if self.assessment.identifier: return
		if ':' in value:
			print "Warning: assessment identifier with colon: replaced with hyphen when making resource identifier."
			value=string.join(string.split(value,':'),'-')
		value = self.resource.SetIdentifier(value)
		self.assessment.SetIdentifier(value)
		self.resource.GetLOM().GetGeneral().AddIdentifier(LOMIdentifier(None,value))
		cp=self.GetRoot().cp
		self.fName=cp.GetUniqueFileName(os.path.join("assessmentTests",self.resource.id+".xml"))

	def SetAttribute_title (self,value):
		self.assessment.SetTitle(value)
	
	def SetAttribute_xml_lang (self,lang):
		self.assessment.SetLanguage(lang)
		
	def GenerateQTIMetadata(self):
		self.resource.GetQTIMD()

	def SetBBAssessmentType(self, type):
		InstructureHelperContainer.SetBBAssessmentType(self,type)
		if type == 'Pool':
			self.question_bank = self.assessment.title
		
	def GenerateInstructureMetadata(self):
		"""This is the metadata that will appear in the manifest file.
		"""
		iMD = self.resource.GetInstructureMD()
		if self.showTotalScore: iMD.AddMetaField("show_score", self.showTotalScore.lower())
		if self.whichAttemptToGrade: iMD.AddMetaField("which_attempt_to_keep", self.whichAttemptToGrade.lower())
		if self.assessmentType: iMD.AddMetaField("quiz_type", self.assessmentType.lower())
		if self.bb_max_score: iMD.AddMetaField("max_score", self.bb_max_score)
		if self.bb_id: iMD.AddMetaField("bb8_object_id", self.bb_id)
		if self.bb_assessment_type: iMD.AddMetaField("bb8_assessment_type", self.bb_assessment_type)
		
	def SetDuration(self, duration):
		self.assessment.SetTimeLimit(duration)
		
	def AddSection(self, section):
		self.assessment.AddSection(section)
		
	def GetItemV1 (self):
		return self

	def GetBankId(self):
		return self.assessment.identifier

	def GetBankName(self):
		return self.assessment.title
	
	def DeclareOutcome (self,decvar):
		self.PrintWarning("Outcomes not supported on assessments: identifier: %s, type: %s, min: %s, max: %s" % (decvar.identifier,decvar.baseType, decvar.min, decvar.max))
		
	def PrintWarning (self,warning,force=0):
		if not self.warnings.has_key(warning):
			self.msg=self.msg+warning+'\n'
			self.warnings[warning]=1
		if force:
			self.parent.PrintWarning(warning,1)
	
	def CloseObject (self):
		if self.bb_assessment_type == 'Pool':
			# All the questions get the pool's name so we don't need a pool object
			return
		# Fix up the title
		if self.assessment.title:
			self.resource.GetLOM().GetGeneral().SetTitle(LOMLangString(self.assessment.title,self.assessment.language))
		#self.GenerateQTIMetadata()
		self.GenerateInstructureMetadata()
		if self.instructureMetadata: self.assessment.SetInstructureMetadata(self.instructureMetadata)
		# Add the resource to the root thing - and therefore the content package
		self.GetRoot().AddResource(self.resource)
		# Adding a resource to a cp may cause it to change identifier, but we don't mind.
		f=StringIO.StringIO()
		f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
		if not self.parser.options.noComment:
			f.write('<!--\n')
			f.write(EncodeComment(self.msg))
			f.write('\t-->\n\n')
		
		self.assessment.SetItemSessionControl(self.sessionControl)
		self.assessment.WriteXML(f)
		cpf=CPFile()
		cpf.SetHREF(self.fName)
		cpf.SetData(f.getvalue())
		f.close()
		self.resource.AddFile(cpf,1)
	
	
# QTISection
# ----------
#
class QTISection(InstructureHelperContainer):
	"""
	<!ELEMENT section (qticomment? , duration? , qtimetadata* , objectives* , sectioncontrol* , sectionprecondition* , sectionpostcondition* , rubric* , presentation_material? , outcomes_processing* , sectionproc_extension? , sectionfeedback* , selection_ordering? , reference? , (itemref | item | sectionref | section)*)>
	
	<!ATTLIST section  %I_Ident;
			%I_Title;
			xml:lang CDATA  #IMPLIED >
	"""
	def __init__(self,name,attrs,parent):
		InstructureHelperContainer.__init__(self)
		self.parent=parent
		self.CheckLocation((QTIAssessment,QTISection, QTIObjectBank, QuesTestInterop),"<section>")
		if isinstance(self.parent, QTIObjectBank):
			self.question_bank = self
		else:
			self.question_bank = None
		if hasattr(self.parent, 'question_bank'):
			self.question_bank = self.parent.question_bank
		self.parser=self.GetParser()
		self.section=AssessmentSection()
		self.ParseAttributes(attrs)

	def SetAttribute_ident (self,value):
		self.section.SetIdentifier(value)

	def SetAttribute_title (self,value):
		self.section.SetTitle(value)
	
	def SetAttribute_visible(self, visible):
		self.section.SetVisible(visible)

	def SetDuration(self, duration):
		#todo: if it's a testPart it can be set...
		pass
	
	def AddSection(self, section):
		self.section.AddSection(section)
		
	def SetOrderType (self,value):
		self.section.SetOrderType(value)
		
	def SetSelectionNumber(self, value):
		self.section.SetSelectionNumber(value)

	def AddSelectionExtension(self, key, value):
		self.section.AddSelectionExtension(key, value)
	
	def SetSequenceType(self, value):
		self.section.SetSequenceType(value)
		
	def SetOutcomeWeights(self, weights):
		self.section.SetOutcomeWeights(weights)
		
	def AddItemReference(self, ref, fName, weight=None, label=None):
		self.section.AddItemReference(ref, fName, weight, label)

	def GetBankId(self):
		if isinstance(self.parent, QTIObjectBank):
			return self.section.identifier
		else:
			return self.parent.GetBankId()

	def GetBankName(self):
		if isinstance(self.parent, QTIObjectBank):
			return self.section.title
		else:
			return self.parent.GetBankName()
		
	def GetItemV1 (self):
		return self
	
	def DeclareOutcome (self,decvar):
		self.PrintWarning("Outcomes not supported on section: identifier: %s, type: %s, min: %s, max: %s" % (decvar.identifier,decvar.baseType, decvar.min, decvar.max))
	
	def CloseObject (self):
		self.section.ProcessReferences()
		self.parent.AddSection(self.section)
		self.section.SetItemSessionControl(self.sessionControl)

# SelectionOrdering
# --------
#
class SelectionOrdering(QTIObjectV1):
	"""
	<!ELEMENT selection_ordering (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((QTISection, QTIAssessment),"<selection_ordering>")
		if isinstance(self.parent,QTISection):
			self.process=True
			self.ParseAttributes(attrs)
		else:
			self.PrintWarning("Warning: selection/ordering on assessment not supported.")
			self.process=False

	def AddData (self,data):
		self.data=self.data+data
	
	def SetOrderType (self,value):
		if self.process: self.parent.SetOrderType(value)
	
	def SetSelectionNumber(self, value):
		if self.process: self.parent.SetSelectionNumber(value)

	def AddSelectionExtension(self, key, value):
		if self.process: self.parent.AddSelectionExtension(key, value)
	
	def SetSequenceType(self, value):
		if self.process: self.parent.SetSequenceType(value)
		
	def SetAttribute_sequence_type (self,value):
		self.SetSequenceType(value)
	
	def CloseObject (self):
		pass
	
	
# Order
# --------
#
class Order(QTIObjectV1):
	"""
	<!ELEMENT order (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((SelectionOrdering),"<order>")
		self.ParseAttributes(attrs)

	def AddData (self,data):
		self.data=self.data+data
		
	def SetAttribute_order_type (self,value):
		self.parent.SetOrderType(value)
	
	
# Selection
# --------
#
class Selection(QTIObjectV1):
	"""
	<!ELEMENT selection (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((SelectionOrdering),"<selection>")
		self.ParseAttributes(attrs)

	def AddData (self,data):
		self.data=self.data+data
		
	def SetSelectionNumber(self, value):
		self.parent.SetSelectionNumber(value)

	def AddSelectionExtension(self, key, value):
		self.parent.AddSelectionExtension(key, value)
		
	def SetAttribute_sequence_type (self,value):
		self.parent.SetSequenceType(value)
	
	
# SelectionNumber
# --------
#
class SelectionNumber(QTIObjectV1):
	"""
	<!ELEMENT selection (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((Selection),"<selection_number>")

	def AddData (self,data):
		self.data=self.data+data
		
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data: self.parent.SetSelectionNumber(self.data)


# SourceBankRef
# --------
#
class SourceBankRef(QTIObjectV1):
	"""
	<!ELEMENT sourcebank_ref (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((Selection),"<sourcebank_ref>")

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data: self.parent.AddSelectionExtension('sourcebank_ref', self.data)


# SelectionExtension
# --------
#
class SelectionExtension(QTIObjectV1):
	"""
	<!ELEMENT selection_extension (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.CheckLocation((Selection),"<selection_extension>")

	def SetPointsPerItem(self, value):
		self.parent.SetPointsPerItem(value)

	def AddSelectionExtension(self, key, value):
		self.parent.AddSelectionExtension(key, value)


# PointsPerItem
# --------
#
class PointsPerItem(QTIObjectV1):
	"""
	<!ELEMENT points_per_item (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((SelectionExtension),"<points_per_item>")

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data: self.parent.AddSelectionExtension('points_per_item', self.data)


# SourceBankContext
# --------
#
class SourceBankContext(QTIObjectV1):
	"""
	<!ELEMENT points_per_item (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((SelectionExtension),"<sourcebank_context>")

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data: self.parent.AddSelectionExtension('sourcebank_context', self.data)


# SourceBankIsExternal
# --------
#
class SourceBankIsExternal(QTIObjectV1):
	"""
	<!ELEMENT points_per_item (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((SelectionExtension),"<sourcebank_is_external>")

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data: self.parent.AddSelectionExtension('sourcebank_is_external', self.data)


# OutcomesProcessing
# --------
#
class OutcomesProcessing(QTIObjectV1):
	"""
	<!ELEMENT outcomes_processing (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((QTISection, QTIAssessment),"<outcomes_processing>")
		self.outcome_weights={}

	def AddData (self,data):
		self.data=self.data+data
		
	def AddWeight(self, id, weight):
		self.outcome_weights[id] = weight
		
	def CloseObject (self):
		if isinstance(self.parent, QTISection):
			self.parent.SetOutcomeWeights(self.outcome_weights)

# ObjectsCondition
# --------
#
class ObjectsCondition(QTIObjectV1):
	"""
	<!ELEMENT objects_condition (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((ResProcessing, OutcomesProcessing),"<objects_condition>")
		self.item_weight=None
		self.item_identity=None

	def AddData (self,data):
		self.data=self.data+data
		
	def SetItemWeight(self, weight):
		self.item_weight = weight
		
	def SetItemIdentity(self, id):
		self.item_identity = id
		
	def CloseObject (self):
		if isinstance(self.parent, OutcomesProcessing) and self.item_identity and self.item_weight:
			self.parent.AddWeight(self.item_identity, self.item_weight)
			pass

# OutcomesMetaData
# --------
#
class OutcomesMetaData(QTIObjectV1):
	"""
	<!ELEMENT outcomes_metadata (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((ObjectsCondition),"<outcomes_metadata>")
		self.mdname=None
		self.ParseAttributes(attrs)

	def AddData (self,data):
		self.data=self.data+data
		
	def SetSelectionNumber(self, value):
		self.parent.SetSelectionNumber(value)
		
	def SetAttribute_mdname (self,value):
		self.mdname = value
		
	def CloseObject(self):
		self.data=self.data.strip()
		if self.mdname and self.mdname.lower() == "ident":
			if ':' in self.data:
				self.data=string.join(string.split(self.data,':'),'-')
			self.parent.SetItemIdentity(CPResource.FixIdentifier(self.data))

# ObjectsParameter
# --------
#
class ObjectsParameter(QTIObjectV1):
	"""
	<!ELEMENT objects_parameter (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.CheckLocation((ObjectsCondition),"<objects_parameter>")
		self.pname=None
		self.ParseAttributes(attrs)

	def AddData (self,data):
		self.data=self.data+data
		
	def SetSelectionNumber(self, value):
		self.parent.SetSelectionNumber(value)
		
	def SetAttribute_pname (self,value):
		self.pname = value
		
	def CloseObject(self):
		self.data=self.data.strip()
		if self.pname and self.pname.lower() == "qmd_weighting":
			self.parent.SetItemWeight(self.data)
		
# ItemRef
# --------
#
class ItemRef(QTIObjectV1):
	"""
	<!ELEMENT itemref (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.linkrefid=None
		self.clean_linkrefid=None
		self.CheckLocation((QTISection),"<itemref>")
		self.ParseAttributes(attrs)
		self.weight = None
		# Set the name of the file
		cp=self.GetRoot().cp
		# Reserve space for our preferred file name
		self.fName=cp.GetUniqueFileName(os.path.join("assessmentItems", self.clean_linkrefid+".xml"), dont_save=True)

	def AddData (self,data):
		self.data=self.data+data

	def SetWeight (self, weight):
		self.weight = weight
		
	def SetAttribute_linkrefid (self,value):
		self.linkrefid = value
		if ':' in value:
			print "Warning: item identifier with colon: replaced with hyphen when making resource identifier."
			value=string.join(string.split(value,':'),'-')
		self.clean_linkrefid = CPResource.FixIdentifier(value)

	def CloseObject(self):
		self.data=self.data.strip()
		if self.clean_linkrefid:
			self.parent.AddItemReference(self.clean_linkrefid, self.fName, self.weight)
# selection_metadata
# --------
#
class SelectionMetadata(QTIObjectV1):
	"""
	<!ELEMENT selection_metadata (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent = parent
		self.parent = self.GetItemV1()
		self.CheckLocation((QTISection),"<selection_metadata>")
		self.data=""
		self.linkrefid=None
		self.clean_linkrefid=None
		self.ParseAttributes(attrs)
		self.weight = None

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject(self):
		self.data=self.data.strip()
		if self.data:
			linkrefid = CPResource.FixIdentifier(self.data)
			# Set the name of the file
			cp=self.GetRoot().cp
			# Reserve space for our preferred file name
			self.fName=cp.GetUniqueFileName(os.path.join("assessmentItems", linkrefid+".xml"), dont_save=True)
			self.parent.AddItemReference(linkrefid, self.fName, self.weight)


# QTIItem
# -------
#
class QTIItem(InstructureHelperContainer):
	"""
	<!ELEMENT item (qticomment? , duration? , itemmetadata? , objectives* , itemcontrol* , itemprecondition* , itempostcondition* , (itemrubric | rubric)* , presentation? , resprocessing* , itemproc_extension? , itemfeedback* , reference?)>

	<!ATTLIST item  maxattempts CDATA  #IMPLIED
                 %I_Label;
                 %I_Ident;
                 %I_Title;
                 xml:lang    CDATA  #IMPLIED >
	""" 

	def __init__(self,name,attrs,parent):
		InstructureHelperContainer.__init__(self)
		self.fName=None
		self.parent=parent
		if hasattr(self.parent, 'question_bank') and self.parent.question_bank:
			self.SetQuestionBank(self.parent.GetBankName(), self.parent.GetBankId())
		self.parser=self.GetParser()
		self.item=AssessmentItem()
		self.resource=CPResource()
		self.resource.SetType("imsqti_item_xmlv2p0")
		self.resource.SetIdentifier("%s" % randint(1,100000))
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
		if not self.fName:
			cp=self.GetRoot().cp
			# Reserve space for our preferred file name
			self.fName=cp.GetUniqueFileName(os.path.join("assessmentItems", self.resource.id+".xml"))
		files_parent = self.parent
		while files_parent and not hasattr(files_parent, 'files'):
				files_parent = files_parent.parent
		if files_parent:
			self.files = files_parent.files
		else:
			self.files={}
	
	def SetAttribute_maxattempts (self,value):
		self.PrintWarning("Warning: maxattempts can not be controlled at item level, ignored: maxattempts='"+value+"'")
		self.PrintWarning("Note: in future, maxattempts will probably be controllable at assessment or assessment section level")

	def SetAttribute_label (self,value):
		self.item.SetLabel(value)
		self.resource.SetLabel(value)

	def SetAttribute_ident (self,value):
		if self.item.identifier: return
		if ':' in value:
			print "Warning: item identifier with colon: replaced with hyphen when making resource identifier."
			value=string.join(string.split(value,':'),'-')
		value = self.resource.SetIdentifier(value);
		self.item.SetIdentifier(value);
		self.resource.GetLOM().GetGeneral().AddIdentifier(LOMIdentifier(None,value))
		cp=self.GetRoot().cp
		self.fName=cp.GetUniqueFileName(os.path.join("assessmentItems", self.resource.id+".xml"))

	def SetAttribute_title (self,value):
		self.item.SetTitle(value)
	
	def SetAttribute_xml_lang (self,lang):
		self.item.SetLanguage(lang)

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
		if not identifier: identifier = 'no_id'
		if self.responses.has_key(identifier):
			self.PrintWarning('Warning: duplicate response identifier: %s' % identifier)
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
		
	
	def GenerateInstructureMetadata(self):
		"""This is the metadata that is listed on the manifest file
		"""
		iMD = self.resource.GetInstructureMD()
		if self.bb_question_type: iMD.AddMetaField("bb_question_type", self.bb_question_type)
		if self.question_type: iMD.AddMetaField("question_type", self.question_type)

	# Methods used in resprocessing
	
	def ResetResprocessing (self):
		if self.outcomes:
			self.PrintWarning("Warning: multiple <resprocessing> not supported, combining them into one.")
		self.item.ResetResponseProcessing()

	def DeclareOutcome (self,decvar):
		if self.outcomes.has_key(decvar.identifier):
			self.PrintWarning("Warning: multiple <outcomes> with same identifier, using last one.")
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
	
	def AddCPFile (self,uri, prepend_path=None):
		uri = string.replace(uri, "%%LINKPATH%%", "")
		if self.files.has_key(uri):
			# We've already added this file to the content package
			return self.files[uri]
		cpf=CPFile()
		if RelativeURL(uri):
			root=self.GetRoot()
			path=root.ResolveURI(uri)
			cpf.SetDataPath(path)
			if os.path.exists(cpf.dataPath):
				# find the last path component
				dName,fName=os.path.split(path)
				# Use this file name in the content package
				fName=root.cp.GetUniqueFileName(fName)
				cpLocation=EncodePathSegment(fName)
			else:
				# if the file doesn't exist in this package just leave the path alone
				cpLocation=uri
		else:
			cpLocation=uri
		#todo - add prepend path if set
		if prepend_path:
			cpLocation = "%s/%s" % (prepend_path, cpLocation)
		cpf.SetHREF(cpLocation)
		self.resource.AddFile(cpf,0)
		self.files[uri]=cpLocation
		return cpLocation

	def CloseObject (self):
		#Add reference to parent if it's a section
		if isinstance(self.parent,QTISection):
			self.parent.AddItemReference(self.resource.id, self.fName, None, self.resource.label)
			
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
		self.GenerateInstructureMetadata()
		if self.instructureMetadata: self.item.SetInstructureMetadata(self.instructureMetadata)
		if self.calculated: self.item.SetCalculated(self.calculated)
		
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
		self.CheckLocation((QTIItem), "<itemmetadata>")

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
		self.CheckLocation((ItemMetadata,QTIObjectBank,QTIAssessment,QTISection),"<qtimetadata>")


# assessmentmetadata
# -----------
#
class AssessmentMetadata(QTIObjectV1):
	"""
	<!ELEMENT assessmentmetadata>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		# itemmetadata, assessment, section, objectbank
		self.CheckLocation((QTIAssessment),"<assessmentmetadata>")


# sectionmetadata
# -----------
#
class SectionMetadata(QTIObjectV1):
	"""
	<!ELEMENT sectionmetadata>
	"""
	def __init__(self,name,attrs,parent):
		self.parent=parent
		# itemmetadata, assessment, section, objectbank
		self.CheckLocation((QTISection),"<sectionmetadata>")

class ItemProcExtension(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.container = self.GetInstructureHelperContainer()

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()

class BBBase(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.label = name
		self.container = self.GetInstructureHelperContainer()

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Converting proprietary Blackboard metadata field %s = %s" % (self.label, self.data))

# bbmd_asi_object_id
class BBObjectID(BBBase):
	def __init__(self,name,attrs,parent):
		BBBase.__init__(self, name, attrs, parent)
		self.CheckLocation((ItemMetadata,AssessmentMetadata, SectionMetadata),"<bbmd_asi_object_id>", False)

	def CloseObject (self):
		BBBase.CloseObject(self)
		self.container.SetBBObjectID(self.data)

# bbmd_assessmenttype
class BBAssessmentType(BBBase):
	def __init__(self,name,attrs,parent):
		BBBase.__init__(self, name, attrs, parent)
		self.CheckLocation((ItemMetadata,AssessmentMetadata, SectionMetadata),"<bbmd_assessmenttype>", False)

	def CloseObject (self):
		BBBase.CloseObject(self)
		self.container.SetBBAssessmentType(self.data)

# bbmd_questiontype
class BBQuestionType(BBBase):
	def __init__(self,name,attrs,parent):
		BBBase.__init__(self, name, attrs, parent)
		self.CheckLocation((ItemMetadata,AssessmentMetadata, SectionMetadata),"<bbmd_questiontype>")

	def CloseObject (self):
		BBBase.CloseObject(self)
		self.container.SetBBQuestionType(self.data)

# qmd_absolutescore_max
class BBMaxScore(BBBase):
	def __init__(self,name,attrs,parent):
		BBBase.__init__(self, name, attrs, parent)
		self.CheckLocation((ItemMetadata,AssessmentMetadata, SectionMetadata, QTIMetadataField),"<qmd_absolutescore_max>", False)

	def CloseObject (self):
		BBBase.CloseObject(self)
		self.container.SetBBMaxScore(self.data)


## D2L-specific properties

class D2LBase(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.label = name
		self.container = self.GetInstructureHelperContainer()

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Converting proprietary D2LD2LPoints metadata field %s = %s" % (self.label, self.data))


class D2LPoints(D2LBase):
	def __init__(self,name,attrs,parent):
		D2LBase.__init__(self, name, attrs, parent)
		if not self.CheckLocation(ItemRef,"<d2l_2p0:points>", False):
			return

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.parent.SetWeight(self.data)

class D2LAssessProcextension(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		QTIObjectV1.__init__(self,name,attrs,parent)
		if not self.CheckLocation(QTIAssessment,"<assess_procextension>", False):
			return
		self.PrintWarning('Warning: d2l meta data in assess_procextension not supported, looking inside for known settings')

	def AddSection (self,id):
		pass

class D2LTimeLimit(D2LBase):
	def __init__(self,name,attrs,parent):
		D2LBase.__init__(self, name, attrs, parent)
		if not self.CheckLocation(D2LAssessProcextension,"<d2l_2p0:time_limit>", False):
			return

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			try:
				# d2l time is in minutes, qti does time in seconds
				self.container.SetDuration("%s" % (float(self.data) * 60))
			except ValueError:
				self.PrintWarning("Warning: invalid time limit value: %s" % self.data)

class D2LPassword(D2LBase):
	def __init__(self,name,attrs,parent):
		D2LBase.__init__(self, name, attrs, parent)
		if not self.CheckLocation(D2LAssessProcextension,"<d2l_2p0:password>", False):
			return

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.container.AddMetaField("password", self.data)

class D2LAttemptsAllowed(D2LBase):
	def __init__(self,name,attrs,parent):
		D2LBase.__init__(self, name, attrs, parent)
		if not self.CheckLocation(D2LAssessProcextension,"<d2l_2p0:attempts_allowed>", False):
			return

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.container.SetMaxAttempts(self.data)

class D2LGradeItem(D2LBase):
	def __init__(self,name,attrs,parent):
		D2LBase.__init__(self, name, attrs, parent)
		if not self.CheckLocation(D2LAssessProcextension,"<grade_item>", False):
			return

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.container.AddMetaField("assignment_identifierref", self.data)

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
		self.CheckLocation((QTIMetadata),"<vocabulary>")
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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_maximumscore>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_levelofdifficulty>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_keywords>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_domain>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_topic>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_description>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_title>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_author>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_organisation>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_toolvendor>", False)

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
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_status>", False)

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
		self.container = self.GetInstructureHelperContainer()
		# itemmetadata
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<qmd_itemtype>", False)

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.container.SetQuestionType(self.data)
			self.PrintWarning("Warning: qmd_itemtype now replaced by qtiMetadata.interactionType in manifest")


class CanvasBase(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.label = name
		self.container = self.GetInstructureHelperContainer()
		# itemmetadata
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<wct_results_showFeedback>", False)

	def AddData (self,data):
		self.data=self.data+data
	
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Converting proprietary canvas metadata field %s = %s" % (self.label, self.data))

# points_possible
# -----------
#
class PointsPossible(CanvasBase):
	"""
	<!ELEMENT points_possible (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		CanvasBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		CanvasBase.CloseObject(self)
		if self.data:
			self.container.SetPointsPossible(self.data)

# assessment_question_identifierref
# -----------
#
class AssessmentQuestionIdentiferref(CanvasBase):
	"""
	<!ELEMENT assessment_question_identifierref (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		CanvasBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		CanvasBase.CloseObject(self)
		if self.data:
			self.container.SetAssessmentQuestionIdentiferref(self.data)

# bank_title
# -----------
#
class BankTitle(CanvasBase):
	"""
	<!ELEMENT bank_title (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		self.parent = parent
		CanvasBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		CanvasBase.CloseObject(self)
		if self.data:
			if hasattr(self.container, 'question_bank_name'):
				self.container.question_bank_name = self.data

class WCTBase(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.label = name
		self.container = self.GetInstructureHelperContainer()
		# itemmetadata
		self.CheckLocation((ItemMetadata,QTIMetadataField),"<wct_results_showFeedback>", False)

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Converting proprietary WebCT metadata field %s = %s" % (self.label, self.data))

# WCTShowFeedback
# -----------
#	
class WCTShowFeedback(WCTBase):
	"""
	<!ELEMENT wct_results_showFeedback (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)
	
	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetShowFeedback(self.data)

# WCTShowTotalScore
# -----------
#	
class WCTShowTotalScore(WCTBase):
	"""
	<!ELEMENT wct_results_showtotalscore (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)
	
	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetShowTotalScore(self.data)

# WCTMaxAttempts
# -----------
#	
class WCTMaxAttempts(WCTBase):
	"""
	<!ELEMENT wct_attempt_attemptsallowed (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)
	
	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetMaxAttempts(self.data)

# WCTWhichAttemptToGrade
# -----------
#	
class WCTWhichAttemptToGrade(WCTBase):
	"""
	<!ELEMENT wct_results_scoring (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)
	
	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetWhichAttemptToGrade(self.data)


# wct_questiontype
# -----------
#
class WCTQuestionType(WCTBase):
	"""
	<!ELEMENT wct_questiontype (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetBBQuestionType(self.data)

# RespondusQuestionType
# -----------
#

class RespondusQuestionType(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.label = name
		self.container = self.GetInstructureHelperContainer()

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		QTIObjectV1.CloseObject(self)
		if self.data:
			self.container.SetQuestionType(self.data)

# wct_questioncategory
# -----------
#
class WCTQuestionCategory(WCTBase):
	"""
	<!ELEMENT wct_questioncategory (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetQuestionBank(self.data)

# wct_fib_questionText
# -----------
#
class WCTFIBText(WCTBase):
	"""
	<!ELEMENT wct_fib_questionText (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			body = self.container.item.GetItemBody()
			body.blocks = [xhtml_text(self.data)]
			body.lock()

# QMDAssessmentType
# -----------
#	
class QMDAssessmentType(WCTBase):
	"""
	<!ELEMENT qmd_assessmenttype (#PCDATA)>
	"""
	def __init__(self,name,attrs,parent):
		WCTBase.__init__(self, name, attrs, parent)
	
	def CloseObject (self):
		WCTBase.CloseObject(self)
		if self.data:
			self.container.SetAssessmentType(self.data)

class QMDTimeLimit(QMDItemType):
	def __init__(self,name,attrs,parent):
		QMDItemType.__init__(self, name, attrs, parent)
		
	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			try:
				# convert time from minutes to seconds
				if not isinstance(self.container, QTIObjectBank):
					self.container.SetDuration("%s" % (float(self.data) * 60))
			except ValueError:
				self.PrintWarning("Warning: invalid time limit value: %s" % self.data)

class CCBase(QTIObjectV1):
	def __init__(self,name,attrs,parent):
		self.parent=parent
		self.data=""
		self.label = name
		self.container = self.GetInstructureHelperContainer()

	def AddData (self,data):
		self.data=self.data+data

	def CloseObject (self):
		self.data=self.data.strip()
		if self.data:
			self.PrintWarning("Converting common cartridge metadata field %s = %s" % (self.label, self.data))

class CCMaxAttempts(CCBase):
	def __init__(self,name,attrs,parent):
		CCBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		CCBase.CloseObject(self)
		if self.data:
			self.container.SetMaxAttempts(self.data)

class CCWeighting(CCBase):
	def __init__(self,name,attrs,parent):
		CCBase.__init__(self, name, attrs, parent)

	def CloseObject (self):
		CCBase.CloseObject(self)
		if self.data:
			self.container.SetPointsPossible(self.data)

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
	'timelimit':QMDTimeLimit,

	# Common Cartridge
	'cc_maxattempts':CCMaxAttempts,
	'cc_weighting':CCWeighting,

	# Custom Canvas fields
	'points_possible':PointsPossible,
	'question_type':QMDItemType,
	'bank_title':BankTitle,
	'assessment_question_identifierref':AssessmentQuestionIdentiferref,

	# These are custom WebCT (Blackboard Vista) fields
	'wct_results_showfeedback':WCTShowFeedback,
	'wct_results_showtotalscore':WCTShowTotalScore,
	'wct_attempt_attemptsallowed':WCTMaxAttempts,
	'wct_results_scoring':WCTWhichAttemptToGrade,
	'wct_fib_questiontext':WCTFIBText,
	'wct_questiontype':WCTQuestionType,
	'wct_questioncategory':WCTQuestionCategory,
	'assessmenttype':QMDAssessmentType,

    # These are custom Respondus fields -- note they use qti_metadatafield
    # rather than qtimetadatafield
    'respondusapi_qpoints':BBMaxScore,
    'respondusapi_qtype':RespondusQuestionType,

	# D2L Field
	'questiontype':QMDItemType
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
		self.CheckLocation((QTIMetadata),"<qtimetadatafield>", False)
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
		self.CheckLocation((QTIMetadataField),"<fieldlabel>")
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
		self.CheckLocation((QTIMetadataField),"<fieldentry>")
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
		self.CheckLocation((QTIItem,QTIAssessment,QTISection),"<duration>")

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
		self.CheckLocation((QTIItem),"<itemcontrol>")
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
		self.CheckLocation((QTIItem),"<presentation>")
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
		self.CheckLocation((QTIItem,QTIAssessment,QTISection),"<rubric>")
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
		self.CheckLocation((QTIItem,QTIAssessment,QTISection),"<objectives>")
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
		self.CheckLocation((FlowV1,Presentation),"<flow>")
		self.ParseAttributes(attrs)
		self.div_container=None
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

	def AppendToParent(self, element):
		if self.flowclass == 'RESPONSE_BLOCK' or self.flowclass == 'RIGHT_MATCH_BLOCK':
			if not self.div_container:
				self.div_container = xhtml_div()
				self.div_container.escaped = True
				self.div_container.SetClass(self.flowclass)
			self.div_container.AppendElement(element)
		else:
			self.parent.AppendElement(element)
	
	def AppendHTMLContainer (self,content, is_text=False):
		container=xhtml_div()
		container.escaped = True
		if is_text:
			container.SetClass('text')
		else:
			container.SetClass('html')
		container.AppendElement(xhtml_text(content))
		self.AppendToParent(container)

	def CloseObject (self):
		buffer=None
		is_text=False
		for child in self.children:
			if isinstance(child,HTML) and not child.escaped:
				if not buffer:
					buffer=StringIO.StringIO()
				if isinstance(child,xhtml_text):
					buffer.write(child.ExtractText())
					if isinstance(child, just_text):
						is_text = True
				else:
					child.WriteXML(buffer)
			else:
				if buffer:
					self.AppendHTMLContainer(buffer.getvalue(), is_text)
					buffer=None
				self.AppendToParent(child)
		if buffer:
			self.AppendHTMLContainer(buffer.getvalue(), is_text)
		if self.div_container:
			self.parent.AppendElement(self.div_container)

		
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
		self.CheckLocation((FlowMat,ItemFeedback,ResponseLabel,Rubric,Objectives,SolutionMaterial,HintMaterial),"<flow_mat>")
		self.ParseAttributes(attrs)
		self.flow_level=parent.GetFlowLevel()+1
		self.div_container=None
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
		self.CheckLocation((Presentation,FlowV1,ResponseLabel,ResponseThing,RenderThing,
			ItemFeedback,Rubric,Objectives,InterpretVar,SolutionMaterial,HintMaterial)
			,"<material>")
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
		self.prepend_path=None
		self.ParseAttributes(attrs)
		# material, altmaterial, reference
		self.CheckLocation((Material, WCTMatchingTextExt),"<"+name+">")
		
	def SetAttribute_label (self,value):
		self.label=value
	
	def SetAttribute_uri (self,value):
		self.uri=value.lstrip('/')
	
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
		self.uri=self.GetItemV1().AddCPFile(self.uri,self.prepend_path)
		
	def MakeImage (self):
		element=xhtml_img()
		self.AddCPFile()
		element.SetSrc(self.uri.replace('\\', '/'))
		if self.width:
			element.SetWidth(self.width)
		if self.height:
			element.SetHeight(self.height)
		if self.label:
			element.SetAlt(self.label)
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
			self.type="text/html"
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
			element=just_text()
			element.SetText(self.data)
			if self.label or self.language:
				# We need to wrap it in a span
				span=SimpleInline("span")
				span.SetLabel(self.label)
				span.SetLanguage(self.language)
				span.AppendElement(element)
				element=span
		elif self.type=='text/html':
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
class MatApplication(MatThing):
	"""
	<!ELEMENT matapplication (#PCDATA)>
	
	<!ATTLIST matapplication  apptype
						 %I_Apptype;
						 %I_Label;
						 %I_Uri;
						 %I_Entityref;
						 %I_Embedded; >

	MatApplication isn't actually supported. Some BB QTI uses this
	for images so it'll try to make an image if the extension is
	recognized as an image extension
	"""
	def __init__(self,name,attrs,parent):
		MatThing.__init__(self,name,attrs,parent)
		if not self.type:
			self.type="image/jpeg"
		self.embedded='Inline'

	def SetAttribute_apptype (self,value):
		pass

	def SetAttribute_embedded (self,value):
		self.embedded=value
	
	def CloseObject (self):
		if self.uri and not re.search(r'\.(jpg|png|gif)$', self.uri, re.I):
			self.PrintWarning("matapplication elements not supported")
			return
			
		element=None
		if self.entityRef:
			self.PrintWarning("Unsupported: inclusion of material through external entities: ignored "+self.entityRef)
		elif not self.uri:
			self.PrintWarning("Unsupported: inclusion of inline images")
		else:
			element=self.MakeImage()
		if element:
			self.parent.AppendElement(element)

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
		self.CheckLocation((Presentation,FlowV1),"<"+name+">")
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
		value = D2L_IDENTIFIER_REPLACER.sub('', value)
		self.identifier=self.ReadIdentifier(value,RESPONSE_PREFIX)

	def SetAttribute_respident (self,value):
		value = D2L_IDENTIFIER_REPLACER.sub('', value)
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
		self.CheckLocation((ResponseThing),"<render_choice>")
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
		self.CheckLocation((FlowLabel,RenderThing),"<response_label>")
	
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
		value = D2L_IDENTIFIER_REPLACER.sub('', value)
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
		if not self.identifier:
			return
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
		self.CheckLocation((RenderThing,FlowLabel),"<flow_label>")
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
		self.CheckLocation((QTIItem),"<itemfeedback>")
		
	def SetAttribute_view (self,value):
		if not (value.lower() in ['all','candidate']):
			self.PrintWarning("Warning: discarding view on feedback ("+value+")")
	
	def SetAttribute_ident (self,value):
		self.identifier = value
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
		self.CheckLocation((ItemFeedback),"<solution>")
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
		self.CheckLocation((Solution),"<solutionmaterial>")
	
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
		self.in_correct_location = self.CheckLocation((ItemFeedback),"<hint>", False)
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
		if self.in_correct_location:
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
		self.CheckLocation((Hint),"<hintmaterial>")
	
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
		self.CheckLocation((QTIItem),"<resprocessing>")
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
		self.CheckLocation((OutcomesProcessing,ResProcessing),"<outcomes>")


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
		self.CheckLocation((Outcomes),"<decvar>")
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
		self.CheckLocation((Outcomes),"<interpretvar>")
	
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
		self.CheckLocation((ResProcessing),"<respcondition>")
				
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
		self.CheckLocation((RespCondition, WCTCalculatedAnswer),"<setvar>")
			
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
			raise QTIException(eUnexpectedVarAction,self.action)
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
		self.CheckLocation((RespCondition),"<displayfeedback>")

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
		self.CheckLocation((RespCondition),"<conditionvar>")
	
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
		self.CheckLocation((ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1),"<and>")
	
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
		self.CheckLocation((ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1),"<or>")
	
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
		self.CheckLocation((ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1),"<not>")
	
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
		self.CheckLocation((ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1),"<not>")

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
		self.CheckLocation((ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1),"<varequal>")

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
		self.CheckLocation((ConditionVar,AndOperatorV1,OrOperatorV1,NotOperatorV1),"<varequal>")

	def SetAttribute_respident (self,value):
		value = D2L_IDENTIFIER_REPLACER.sub('', value)
		self.identifier=self.ReadIdentifier(value,RESPONSE_PREFIX)
		if self.GetInstructureHelperContainer().question_type == 'fillInMultiple':
			if not self.GetItemV1().GetResponse(self.identifier):
				self.GetItemV1().DeclareResponse(self.identifier,'single','string')
	
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
		if self.identifier:
			self.valExpression.SetIdentifier(self.identifier)
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
		'assess_procextension':D2LAssessProcextension,
        'and':AndOperatorV1,
        'and_objects':Unsupported,
        'and_selection':Unsupported,
        'and_test':Unsupported,
        'answer':CalculatedAnswer,
        'answer_scale':BB8AnswerScale,
        'answer_tolerance':BB8AnswerTolerance,
        'assessfeedback':Unsupported,
        'assessment':QTIAssessment,
        'assessmentcontrol':Unsupported,
        'assessproc_extension':Unsupported,
        'assessmentmetadata':AssessmentMetadata,
        'bbmd_asi_object_id':BBObjectID, # BB8 internal id
        'bbmd_assessmenttype':BBAssessmentType, # Test, Pool
        'bbmd_questiontype':BBQuestionType, # Multiple Choice, Calculated, Numeric, Either/Or, Essay, File Upload, Fill in the Blank Plus, Fill in the Blank, Hot Spot, Jumbled Sentence, Matching, Multiple Answer, Multiple Choice, Opinion Scale, Ordering, Quiz Bowl, Short Response, True/False
		'cc_maxattempts':QTIMetadataField,
		'cc_weighting':QTIMetadataField,
        'conditionvar':ConditionVar,
        'calculated':CalculatedNode,
        'd2l_2p0:attempts_allowed':D2LAttemptsAllowed,
        'd2l_2p0:points':D2LPoints,
        'd2l_2p0:time_limit':D2LTimeLimit,
        'd2l_2p0:password':D2LPassword,
		'decimalplaces':D2LDecimalplaces,
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
		'file':File,
        'flow':FlowV1,
        'flow_label':FlowLabel,
        'flow_mat':FlowMat,
        'formula':CalculatedFormula,
        'formulas':CalculatedFormulas,
		'grade_item':D2LGradeItem,
        'hint':Hint,
        'hintmaterial':HintMaterial,
        'interpretvar':InterpretVar,
        'item':QTIItem,
        'itemcontrol':ItemControl,
        'itemfeedback':ItemFeedback,
        'itemmetadata':ItemMetadata,
        'itempostcondition':Unsupported,
        'itemprecondition':Unsupported,
        'itemproc_extension':ItemProcExtension,
        'itemref':ItemRef,
        'itemrubric':Unsupported,
		'manifest':Manifest,
        'map_output':Unsupported,
        'mat_extension':WCTMatExtension,
        'mat_formattedtext':BBMatFormattedText,
        'matapplet':Unsupported,
        'matapplication':MatApplication,
        'mataudio':MatAudio,
        'matbreak':MatBreak,
        'matemtext':MatEmText,
        'material':Material,
        'material_ref':Unsupported,
        'material_table':WCTMaterialTable,
        'matimage':MatImage,
        'matref':Unsupported,
        'mattext':MatText,
        'matvideo':Unsupported,
        'max':BB8Max,
        'maxvalue':D2LMaxvalue,
        'min':BB8Min,
        'minvalue':D2LMinvalue,
        'not':NotOperatorV1,
        'not_objects':Unsupported,
        'not_selection':Unsupported,
        'not_test':Unsupported,
        'objectbank':QTIObjectBank,
        'objectives':Objectives,
        'objects_condition':ObjectsCondition,
        'objects_parameter':ObjectsParameter,
        'objectscond_extension':Unsupported,
        'or':OrOperatorV1,
        'or_objects':Unsupported,
        'or_selection':Skipped,
        'or_test':Unsupported,
        'order':Order,
        'order_extension':Unsupported,
        'other':OtherOperatorV1,
        'outcomes':Outcomes,
        'outcomes_feedback_test':Unsupported,
        'outcomes_metadata':OutcomesMetaData,
        'outcomes_processing':OutcomesProcessing,
        'partial_credit_points_percent':BB8PartialCreditPointsPercent,
        'partial_credit_tolerance':BB8PartialCreditTolerance,
        'points_per_item':PointsPerItem,
        'presentation':Presentation,
        'presentation_material':Unsupported,
        'processing_parameter':Unsupported,
        'qmd_absolutescore_max':BBMaxScore,
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
        'qmd_timelimit':QTIMetadataField,
        'qmd_toolvendor':QMDToolVendor,
        'qmd_topic':QMDTopic,
        'qmd_typeofsolution':Unsupported,
        'qmd_weighting':Unsupported,
        'qticomment':QTIComment,
        'qtimetadata':QTIMetadata,
        'qtimetadatafield':QTIMetadataField,
        'qti_metadatafield':QTIMetadataField,
        'questestinterop':QuesTestInterop,
        'reference':Unsupported,
        'render_choice':RenderChoice,
        'render_extension':Unsupported,
        'render_fib':RenderFib,
        'render_hotspot':RenderHotspot,
        'render_slider':RenderSlider,
		'resources':Resources,
		'resource':Resource,
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
        'selection':Selection,
        'selection_number':SelectionNumber,
        'selection_extension':SelectionExtension,
        'selection_metadata':SelectionMetadata,
        'selection_ordering':SelectionOrdering,
        'sequence_parameter':Unsupported,
        'setvar':SetVar,
        'solution':Solution,
        'solutionmaterial':SolutionMaterial,
        'sourcebank_ref':SourceBankRef,
        'sourcebank_context':SourceBankContext,
        'sourcebank_is_external':SourceBankIsExternal,
		'step':Unsupported,
        'test_variable':Unsupported,
        'unanswered':Unanswered,
        'unit_case_sensitive':BB8UnitCaseSensitive,
        'unit_points_percent':BB8UnitPointsPercent,
        'unit_required':BB8UnitRequired,
        'unit_value':BB8UnitValue,
        'var_extension':Unsupported,
        'varequal':VarEqual,
        'vargt':VarGT,
        'vargte':VarGTE,
		'variable':D2LVariable,
        'variable_test':Unsupported,
        'varinside':VarInside,
        'varlt':VarLT,
        'varlte':VarLTE,
        'var':BB8Var,
        'vars':BB8Vars,
        'var_set':CalculatedVarSet,
        'var_sets':BB8VarSets,
        'varsubset':VarSubset,
        'varsubstring':VarSubstring,
        'vocabulary':Vocabulary,
		'webct:answer':CalculatedAnswer,
		'webct:calculated':CalculatedNode,
		'webct:calculated_answer':WCTCalculatedAnswer,
		'webct:calculated_set':CalculatedVarSet,
		'webct:calculated_var':WCTVar,
		'webct:ContentObject':WCTContentObject,
		'webct:Name':WCTName,
		'webctfl:Path':WCTPath,
		'webct:formula':CalculatedFormula,
		'webct:matching_ext_flow':WCTMatchingExtFlow,
		'webct:matching_text_ext':WCTMatchingTextExt,
		'webct:var':WCTVar,
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
		self.manifest=None
		self.manifest_path=None
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
				# see if there is an imsmanifest and process it first
				# The order of the rest doesn't mater
				for i, v in enumerate(children):
					if v == "imsmanifest.xml":
						if i:
							children[0], children[i] = children[i], children[0]
						break
				self.ProcessFiles(path,children)
			elif fileName[-4:].lower() in ['.xml', '.dat', '.qti']:
				print "Processing file: "+path
				f=open(path,'r')
				try:
					self.Parse(f,path)
				finally:
					f.close()

	def DumpCP (self):
		if self.options.cpPath:
			self.cp.DumpToDirectory(self.options.cpPath, self.options.create_error_files)

	def Parse (self,f,path):
		global CURRENT_FILE_NAME
		CURRENT_FILE_NAME = path.split('/')[-1][:-4]
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
		CURRENT_FILE_NAME=None

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
				if isinstance(self.cObject,Manifest):
					if self.currPath.endswith("imsmanifest.xml"):
						self.cObject.SetCP(self.cp)
						self.cObject.SetPath(self.currPath)
						self.manifest = self.cObject
						self.manifest_path = self.currPath.replace("imsmanifest.xml", '')
					else:
						if self.manifest:
							self.cObject.SetCP(self.manifest.cp)
							self.cObject.SetPath(self.manifest.path)
							self.cObject.resource = self.manifest.resource

				if self.options.prepend_path and isinstance(self.cObject,(MatThing)):
					self.cObject.prepend_path = self.options.prepend_path
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
