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

class QTIMetadata:
	def __init__ (self):
		self.itemTemplate=None
		self.timeDependent=None
		self.composite=None
		self.interactionTypes={}
		self.feedbackType=None
		self.solutionAvailable=None
		self.toolName=None
		self.toolVersion=None
		self.toolVendor=None

	def SetItemTemplate(self,itemTemplate):
		self.itemTemplate=itemTemplate
		
	def SetTimeDependent(self,timeDependent):
		self.timeDependent=timeDependent
		
	def SetComposite(self,composite):
		self.composite=composite
	
	def AddInteractionType(self,interactionType):
		self.interactionTypes[interactionType]=1
		
	def SetFeedbackType(self,feedbackType):
		self.feedbackType=feedbackType

	def SetSolutionAvailable(self,solutionAvailable):
		self.solutionAvailable=solutionAvailable

	def SetToolName(self,name):
		self.toolName=name
	
	def SetToolVersion(self,version):
		self.toolVersion=version
	
	def SetToolVendor(self,vendor):
		self.toolVendor=vendor
	
	def WriteXML (self,f,ns):
		if ns:
			f.write('\n<'+ns+'qtiMetadata>')
		else:
			f.write('\n<qtiMetadata xmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"\
			xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\
			xsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 imsqti_v2p1.xsd">')
		if self.itemTemplate is not None:
			if self.itemTemplate:
				value="true"
			else:
				value="false"
			f.write('\n<'+ns+'itemTemplate>'+value+'</'+ns+'itemTemplate>')
		if self.timeDependent is not None:
			if self.timeDependent:
				value="true"
			else:
				value="false"
			f.write('\n<'+ns+'timeDependent>'+value+'</'+ns+'timeDependent>')
		if self.composite is not None:
			if self.composite:
				value="true"
			else:
				value="false"
			f.write('\n<'+ns+'composite>'+value+'</'+ns+'composite>')			
		for interactionType in self.interactionTypes.keys():
			f.write('\n<'+ns+'interactionType>'+XMLString(interactionType)+'</'+ns+'interactionType>')
		if self.feedbackType is not None:
			f.write('\n<'+ns+'feedbackType>'+XMLString(self.feedbackType)+'</'+ns+'feedbackType>')
		if self.solutionAvailable is not None:
			if self.solutionAvailable:
				value="true"
			else:
				value="false"
			f.write('\n<'+ns+'solutionAvailable>'+value+'</'+ns+'solutionAvailable>')			
		if self.toolName:
			f.write('\n<'+ns+'toolName>'+XMLString(self.toolName)+'</'+ns+'toolName>')
		if self.toolVersion:
			f.write('\n<'+ns+'toolVersion>'+XMLString(self.toolVersion)+'</'+ns+'toolVersion>')
		if self.toolVendor:
			f.write('\n<'+ns+'toolVendor>'+XMLString(self.toolVendor)+'</'+ns+'toolVendor>')
		f.write('\n</'+ns+'qtiMetadata>')

class InstructureMetadata:
	def __init__ (self):
		self.fields = None
		self.matching_items = None
	
	def AddMetaField(self, type, value):
		if not self.fields: self.fields = {}
		self.fields[type] = value
	
	def StartMatchingList(self):
		if not self.matching_items: self.matching_items = []
		self.matching_items.append([])
	
	def AddMatchingItem(self, item):
		index = len(self.matching_items) - 1
		self.matching_items[index].append(item)
	
	def WriteXML (self,f,ns=""):
		if self.fields or self.matching_items:
			f.write('\n<%sinstructureMetadata>' % ns)
			
			if self.fields:
				for name, val in self.fields.items():
					f.write('\n<%sinstructureField name="%s" value="%s" />' %(ns, name, val))
			
			if self.matching_items and len(self.matching_items) > 1:
				f.write('\n<%smatchingAnswers>' % ns)
				for answer in self.matching_items[0]:
					f.write('\n<%smatchingAnswer>%s</%smatchingAnswer>' % (ns,answer,ns))
				f.write('\n</%smatchingAnswers>' % ns)
				f.write('\n<%smatchingMatches>' % ns)
				for match in self.matching_items[1]:
					f.write('\n<%smatchingMatch>%s</%smatchingMatch>' % (ns,match,ns))
				f.write('\n</%smatchingMatches>' % ns)
				
			f.write('\n</%sinstructureMetadata>' % ns)
		
class ItemSessionControl:
	"""
	http://www.imsglobal.org/question/qtiv2p1pd2/imsqti_infov2p1pd2.html#element10029
	"""
	def __init__(self):
		self.maxAttempts=None
		self.showFeedback=None
		self.allowReview=None
		self.showSolution=None
		self.allowComment=None
		self.allowSkipping=None
		self.validateResponses=None
	
	def SetMaxAttempts(self, value):
		self.maxAttempts = value
	
	def SetShowFeedback(self, value):
		self.showFeedback = value
	
	def SetAllowReview(self, value):
		self.allowReview = value
	
	def SetShowSolution(self, value):
		self.showSolution = value
	
	def SetAllowComment(self, value):
		self.allowComment = value
	
	def SetAllowSkipping(self, value):
		self.allowSkipping = value
	
	def SetValidateResponses(self, value):
		self.validateResponses = value
		
	def WriteXML (self,f):
		f.write('\n<itemSessionControl')
		if self.maxAttempts: f.write(' maxAttempts="'+XMLString(self.maxAttempts)+'"')
		if self.showFeedback: f.write(' showFeedback="'+XMLString(self.showFeedback)+'"')
		if self.allowReview: f.write(' allowReview="'+XMLString(self.allowReview)+'"')
		if self.showSolution: f.write(' showSolution="'+XMLString(self.showSolution)+'"')
		if self.allowComment: f.write(' allowComment="'+XMLString(self.allowComment)+'"')
		if self.allowSkipping: f.write(' allowSkipping="'+XMLString(self.allowSkipping)+'"')
		if self.validateResponses: f.write(' validateResponses="'+XMLString(self.validateResponses)+'"')
		f.write('/>')

def convert_duration_to_seconds(duration):
	"""The duration is in the ISO 8601 format: PnYnMnDTnHnMnS
	This function converts that to seconds.
	The format that it is actually in however is: HnMnSn
	"""
	import re
	hours, minutes, seconds = re.search(r'(?:H([\d]*))?(?:M([\d]*))?(?:S([\d]*))?', duration).group(1,2,3)
	
	if not hours and not minutes and not seconds:
		return duration
	
	duration = 0
	if seconds: duration += int(seconds)
	if minutes: duration += int(minutes) * 60
	if hours: duration += int(hours) * 60 * 60
	
	if duration > 0:
		return duration
	else:
		return None

class AssessmentTest:
	def __init__ (self):
		self.identifier=""
		self.title=""
		self.language=None
		self.toolName=None
		self.toolVersion=None
		self.timeLimit=None
		self.variables={}
		self.parts = [TestPart()]
		self.instructureMetadata=None
	
	def SetIdentifier (self,identifier):
		self.identifier=identifier

	def SetTitle (self,title):
		self.title=title

	def SetTimeLimit (self,timeLimit):
		self.timeLimit=convert_duration_to_seconds(timeLimit)

	def SetLanguage (self,language):
		self.language=language
	
	def SetToolName (self, tool_name):
		self.toolName = tool_name
	
	def SetToolVersion (self, tool_version):
		self.toolVersion = tool_version
		
	def AddSection(self, section, part_index=0):
		self.parts[part_index].AddSection(section)
		
	def AddPart(self, section):
		self.parts.append(section)
		
	def SetItemSessionControl(self, control, part_index=0):
		self.parts[part_index].SetItemSessionControl(control)

	def SetInstructureMetadata(self, md):
		self.instructureMetadata = md
	
	def WriteXML (self,f):
		f.write('<assessmentTest')
		f.write('\n\txmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"')
		f.write('\n\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
		f.write('\n\txsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"')
		f.write('\n identifier="'+XMLString(self.identifier)+'"')
		f.write('\n title="%s"' % XMLString(self.title))
		if self.language:
			f.write('\n xml:lang="'+XMLString(self.language)+'"')
		if self.toolName:
			f.write('\n toolName="'+XMLString(self.toolName)+'"')
		if self.toolVersion:
			f.write('\n toolVersion="'+XMLString(self.toolVersion)+'"')
		f.write('>')
		if self.timeLimit:
			f.write('\n<timeLimits maxTime="%s"/>' % self.timeLimit)

		if self.instructureMetadata:
			self.instructureMetadata.WriteXML(f)
		
		for part in self.parts:
			part.WriteXML(f)
		
		f.write('\n</assessmentTest>\n')


class TestPart:
	def __init__ (self):
		self.identifier="BaseTestPart"
		self.timeLimit=None
		self.navigationMode=None
		self.submissionMode=None
		self.sections = []
		self.itemSessionControl=None
	
	def SetItemSessionControl(self, control):
		self.itemSessionControl = control
		
	def SetIdentifier (self,identifier):
		self.identifier=identifier
		
	def SetNavigationMode (self,navigationMode):
		self.navigationMode=navigationMode
		
	def SetSubmissionMode (self,submissionMode):
		self.submissionMode=submissionMode
		
	def SetTimeLimit (self,timeLimit):
		self.timeLimit=convert_duration_to_seconds(timeLimit)
	
	def AddSection(self, section):
		self.sections.append(section)
		
	def WriteXML (self,f):
		f.write('\n<testPart')
		f.write(' identifier="'+XMLString(self.identifier)+'"')
		if self.navigationMode: f.write('\n navigationMode="'+XMLString(self.navigationMode)+'"')
		if self.submissionMode: f.write('\n submissionMode="'+XMLString(self.submissionMode)+'"')
		f.write('>')
		if self.timeLimit: f.write('\n<timeLimits maxTime="%s"/>' % self.timeLimit)
		if self.itemSessionControl: self.itemSessionControl.WriteXML(f)
		
		for sections in self.sections:
			sections.WriteXML(f)
		
		f.write('\n</testPart>')

class AssessmentSection:
	def __init__ (self):
		self.identifier=""
		self.title=""
		self.visible=None
		self.required=None
		self.fixed=None
		self.keepTogether=None
		self.timeLimit=None
		self.randomOrdering=None
		self.selectNumber=None
		self.withReplacement=None
		self.items = []
		self.outcomeWeights=None
		self.references={}
		self.itemSessionControl=None
		self.selection_extensions = {}
	
	def SetItemSessionControl(self, control):
		self.itemSessionControl = control
		
	def SetIdentifier (self,identifier):
		self.identifier=identifier

	def AddSelectionExtension(self, key, value):
		self.selection_extensions[key] = value
	
	def SetTitle (self,title):
		self.title=title
		
	def SetVisible (self,visible):
		self.visible=visible
		
	def SetRequired (self,required):
		self.required=required
		
	def SetFixed (self,fixed):
		self.fixed=fixed
		
	def SetKeepTogether (self,keepTogether):
		self.keepTogether=keepTogether
	
	def SetTimeLimit (self,timeLimit):
		self.timeLimit=convert_duration_to_seconds(timeLimit)
		
	def AddSection(self, section):
		self.items.append(section)
	
	def AddItemReference(self, reference, fName, weight=None, label=None):
		ref = AssessmentItemRef(reference, fName, weight, label)
		self.items.append(ref)
		self.references[reference] = ref
		
	def SetOutcomeWeights(self, weights):
		self.outcomeWeights = weights
		
	def SetOrderType (self,value):
		""" The type will be one of: fixed, sequential, random
		http://www.imsglobal.org/question/qtiv1p2/imsqti_asi_saov1p2.html#1404826
		"""
		if value.lower() == "random":
			self.randomOrdering = True
		
	def SetSelectionNumber(self, value):
		"""This is how many questions from a group should be selected"""
		self.selectNumber = value

	def SetSequenceType(self, value):
		"""Possible values: repeat, normal"""
		if value.lower() == "repeat":
			self.withReplacement = True
			
	def ProcessReferences(self):
		if self.outcomeWeights:
			for id, weight in self.outcomeWeights.items():
				if self.references.has_key(id):
					self.references[id].SetWeight(weight)
		
	def WriteXML (self,f):
		f.write('\n<assessmentSection')
		f.write(' identifier="'+XMLString(self.identifier)+'"')
		if self.title: f.write('\n title="'+XMLString(self.title)+'"')
		if self.visible: f.write('\n visible="'+XMLString(self.visible)+'"')
		if self.required: f.write('\n required="'+XMLString(self.required)+'"')
		if self.fixed: f.write('\n fixed="'+XMLString(self.fixed)+'"')
		if self.keepTogether: f.write('\n keepTogether="'+XMLString(self.keepTogether)+'"')
		f.write('>')
		if self.timeLimit: f.write('\n<timeLimits maxTime="%s"/>' % self.timeLimit)
		if self.randomOrdering: f.write('\n<ordering shuffle="true"/>')
		if self.itemSessionControl: self.itemSessionControl.WriteXML(f)
		if self.selectNumber or self.withReplacement or len(self.selection_extensions) > 0:
			f.write('\n<selection')
			if self.selectNumber: f.write(' select="%s"' % self.selectNumber)
			if self.withReplacement: f.write(' withReplacement="%s"' % self.withReplacement)
			if len(self.selection_extensions) > 0:
				f.write('>\n')
				f.write('\n<selectionExtension>')
				for key, val in self.selection_extensions.items():
					f.write('\n<' + key + '>' + val + '</' + key + '>')
				f.write('\n</selectionExtension>')
				f.write('\n</selection>')
			else:
				f.write(' />')
		
		for item in self.items:
			item.WriteXML(f)
		
		f.write('\n</assessmentSection>')
		
class AssessmentItemRef:
	def __init__(self, iden, href, weight=None, label=None):
		self.identifier=iden
		self.weight=weight
		self.href=href
		self.label=label
	
	def SetIdentifier(self, value):
		self.identifier=value
	
	def SetWeight(self, weight):
		self.weight=weight

	def SetLabel(self, label):
		self.label=label
		
	def SetHREF(self, href):
		self.href = href
	
	def WriteXML(self,f):
		#<assessmentItemRef identifier="set01" href="rtest01-set01.xml"/>
		f.write('\n<assessmentItemRef')
		f.write(' identifier="%s"' % XMLString(self.identifier))
		f.write(' href="../%s"' % XMLString(self.href))
		if self.label:
			f.write(' label="%s"' % XMLString(self.label))
		if self.weight:
			f.write(">")
			f.write('\n<weight identifier="%s" value="%s"/>' % (0, self.weight))
			f.write('\n</assessmentItemRef>')
		else:
			f.write('/>')

class AssessmentItem:
	def __init__ (self):
		self.identifier=""
		self.title=""
		self.label=None
		self.language=None
		self.adaptive=0
		self.timeDependent=0
		self.toolName=None
		self.toolVersion=None
		self.variables={}
		self.itemBody=None
		self.responseProcessing=None
		self.modalFeedback=[]
		self.instructureMetadata=None
		self.calculated=None
		
	def SetIdentifier (self,identifier):
		self.identifier=identifier
		
	def SetTitle (self,title):
		self.title=title

	def SetLabel (self,label):
		self.label=label
		
	def SetLanguage (self,language):
		self.language=language

	def DeclareVariable (self,variable):
		if self.variables.has_key(variable.GetIdentifier()):
			raise QTIException(eDuplicateVariable,variable.GetIdentifier())
		self.variables[variable.GetIdentifier()]=variable
	
	def ResetResponseProcessing (self):
		if not self.responseProcessing:
			self.responseProcessing=None
			for vName in self.variables.keys():
				v=self.variables[vName]
				if isinstance(v,OutcomeDeclaration):
					del self.variables[vName]
					
	def GetItemBody (self):
		if not self.itemBody:
			self.itemBody=ItemBody()
		return self.itemBody

	def GetResponseProcessing (self):
		if not self.responseProcessing:
			self.responseProcessing=ResponseProcessing()
		return self.responseProcessing

	def AddModalFeedback (self,feedback):
		self.modalFeedback.append(feedback)
	
	def HasModalFeedback (self):
		return len(self.modalFeedback)>0
	
	def SetInstructureMetadata(self, md):
		self.instructureMetadata = md
		
	def SetCalculated(self, c):
		self.calculated = c
	
	def WriteXML (self,f):
		f.write('<assessmentItem')
		f.write('\n\txmlns="http://www.imsglobal.org/xsd/imsqti_v2p1"')
		f.write('\n\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
		f.write('\n\txsi:schemaLocation="http://www.imsglobal.org/xsd/imsqti_v2p1 http://www.imsglobal.org/xsd/imsqti_v2p1.xsd"')
		f.write(' identifier="'+XMLString(self.identifier)+'"')
		f.write('\n title="'+XMLString(self.title)+'"')
		if self.label:
			f.write('\n label="'+XMLString(self.label)+'"')
		if self.language:
			f.write('\n xml:lang="'+XMLString(self.language)+'"')
		if self.adaptive:
			f.write('\n adaptive="true"')
		else:
			f.write('\n adaptive="false"')
		if self.timeDependent:
			f.write('\n timeDependent="true"')
		else:
			f.write('\n timeDependent="false"')
		if self.toolName:
			f.write('\n toolName="'+XMLString(self.toolName)+'"')
		if self.toolVersion:
			f.write('\n toolVersion="'+XMLString(self.toolVersion)+'"')
		f.write('>')
		
		if self.instructureMetadata:
			self.instructureMetadata.WriteXML(f)
			
		vars=self.variables.keys()
		vars.sort()
		for var in vars:
			varDeclaration=self.variables[var]
			if isinstance(varDeclaration,ResponseDeclaration):
				varDeclaration.WriteXML(f)
		for var in vars:
			varDeclaration=self.variables[var]
			if isinstance(varDeclaration,OutcomeDeclaration):
				varDeclaration.WriteXML(f)
		# templateDeclarations
		# templateProcessing
		if self.itemBody:
			self.itemBody.WriteXML(f)
		if self.responseProcessing:
			self.responseProcessing.WriteXML(f)
		for feedback in self.modalFeedback:
			feedback.WriteXML(f)
		if self.calculated: self.calculated.WriteXML(f)
		f.write('\n</assessmentItem>\n')


class VariableDeclaration:
	def __init__ (self,identifier,cardinality,baseType):
		self.identifier=identifier
		self.cardinality=cardinality
		self.baseType=baseType
		self.default=None
	
	def GetIdentifier (self):
		return self.identifier
			
	def GetCardinality (self):
		return self.cardinality
	
	def GetBaseType (self):
		return self.baseType

	def SetDefaultValue (self,value):
		self.default=value
		
	def GetDefaultValue (self):
		return self.default
		
	
class ResponseDeclaration(VariableDeclaration):
	def WriteXML (self,f):
		f.write('\n<responseDeclaration identifier="'+self.identifier+
			'" cardinality="'+self.cardinality+
			'" baseType="'+self.baseType+'"')
		if self.default:
			f.write('>')
			self.default.WriteXML(f)
			f.write('</responseDeclaration>')
		else:
			f.write('/>')
		

class OutcomeDeclaration(VariableDeclaration):
	def __init__ (self,identifier,cardinality,baseType):
		VariableDeclaration.__init__(self,identifier,cardinality,baseType)
		self.interpretation=None
		self.normalMaximum=None
		
	def SetInterpretation (self,value):
		self.interpretation=value

	def SetNormalMaximum (self,value):
		self.normalMaximum=value
		
	def WriteXML (self,f):
		f.write('\n<outcomeDeclaration identifier="'+self.identifier+
			'" cardinality="'+self.cardinality+
			'" baseType="'+self.baseType+'"')
		if self.interpretation:
			f.write(' interpretation="'+XMLString(self.interpretation)+'"')
		if self.normalMaximum:
			f.write(' normalMaximum="'+str(self.normalMaximum)+'"')
		if self.default:
			f.write('>')
			self.default.WriteXML(f)
			f.write('</outcomeDeclaration>')
		else:
			f.write('/>')

class DefaultValue:
	def __init__ (self,value=""):
		self.value=value
		self.interpretation=None
	
	def SetInterpretation (self,interpretation):
		self.interpretation=interpretation
	
	def WriteXML (self,f):
		f.write('\n<defaultValue')
		if self.interpretation:
			f.write(' interpretation="'+XMLString(self.interpretation)+'">')
		else:
			f.write(">")
		f.write('<value>'+XMLString(self.value)+'</value>')
		f.write("</defaultValue>")


class BodyElement:
	def __init__ (self):
		self.id=None
		self.classid=None
		self.language=None
		self.label=None
		
	def SetID (self,id):
		self.id=id
	
	def SetClass (self,classid):
		self.classid=classid
	
	def SetLanguage (self,language):
		self.language=language
	
	def SetLabel (self,label):
		self.label=label

	def ExtractText (self):
		self.PrintWarning("Warning: trying to extract text from non-text object")
		return "<missing object>"
	
	def ExtractImages (self):
		return []
	
	def WriteXMLAttributes (self,f):
		if self.id:
			f.write(' id="'+XMLString(self.id)+'"')
		if self.classid:
			f.write(' class="'+XMLString(self.classid)+'"')
		if self.language:
			f.write(' xml:lang="'+XMLString(self.language)+'"')
		if self.label:
			f.write(' label="'+XMLString(self.label)+'"')

	def WriteXML (self,f):
		pass
		
class ObjectFlow: pass

class Flow(BodyElement,ObjectFlow): pass

class Block(Flow): pass

class Inline(Flow): pass

class HTML:
	def __init__ (self):
		self.escaped = False

SimpleInlineNames=['a','abbr','acronym','b','big','cite','code','dfn','em','i','kbd',
	'q','samp','small','span','strong','sub','sup','tt','var']

class SimpleInline(Inline,HTML):
	def __init__ (self,name):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.name=name
		self.elements=[]
		
	def AppendElement(self,element):
		self.elements.append(element)
	
	def WriteXML (self,f):
		f.write("\n<"+self.name)
		BodyElement.WriteXMLAttributes(self,f)
		f.write(">")
		for element in self.elements:
			element.WriteXML(f)
		f.write("</"+self.name+">")

	def ExtractText (self):
		text=""
		for element in self.elements:
			text=text+element.ExtractText()
		return text

	def ExtractImages (self):
		return ExtractImages(self.elements)
	
		
class AtomicBlock(Block,HTML):
	def __init__ (self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.elements=[]
		
	def AppendElement(self,element):
		self.elements.append(element)

	def ExtractText (self):
		text=""
		for element in self.elements:
			text=text+element.ExtractText()
		return text

	def ExtractImages (self):
		return ExtractImages(self.elements)


class SimpleBlock(Block,HTML):
	def __init__ (self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.elements=[]
		
	def AppendElement(self,element):
		self.elements.append(element)
		
	def ExtractText (self):
		text=""
		for element in self.elements:
			text=text+element.ExtractText()
		return text

	def ExtractImages (self):
		return ExtractImages(self.elements)


class ItemBody(BodyElement):
	def __init__ (self):
		BodyElement.__init__(self)
		self.blocks=[]
		self.locked = False
		
	def AppendBlock (self,block):
		if not self.locked:
			self.blocks.append(block)

	def lock(self, lock=True):
		self.locked = lock
		
	def WriteXML (self,f):
		f.write('\n<itemBody')
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for block in self.blocks:
			block.WriteXML(f)
		f.write('\n</itemBody>')

	def ExtractImages (self):
		return ExtractImages(self.blocks)
		

class RubricBlock(BodyElement):
	def __init__ (self):
		BodyElement.__init__(self)
		self.blocks=[]
		self.view=[]
	
	def AppendView (self,view):
		if not view in self.view:
			self.view.append(view)
		
	def AppendElement (self,block):
		self.blocks.append(block)
		
	def WriteXML (self,f):
		if not self.view:
			view=['all']
		else:
			view=self.view
		f.write('\n<rubricBlock')
		BodyElement.WriteXMLAttributes(self,f)
		f.write(' view="'+string.join(view,' ')+'">')
		for block in self.blocks:
			block.WriteXML(f)
		f.write('\n</rubricBlock>')

class ModalFeedback(BodyElement):
	def __init__ (self):
		BodyElement.__init__(self)
		self.outcomeIdentifier="FEEDBACK"
		self.identifier=None
		self.showHide='show'
		self.title=None
		self.elements=[]
	
	def SetOutcomeIdentifier (self,identifier):
		self.outcomeIdentifier=identifier

	def SetShowHide (self,showHide):
		self.showHide=showHide
		
	def SetIdentifier (self,identifier):
		self.identifier=identifier
	
	def SetTitle (self,title):
		self.title=title
	
	def AppendElement (self,element):
		self.elements.append(element)
		
	def WriteXML (self,f):
		f.write('\n<modalFeedback')
		f.write(' outcomeIdentifier="'+XMLString(self.outcomeIdentifier)+'"')
		f.write(' showHide="'+XMLString(self.showHide)+'"')
		f.write(' identifier="'+XMLString(self.identifier)+'"')
		f.write('>')
		for element in self.elements:
			element.WriteXML(f)
		f.write('</modalFeedback>')
		
def ExtractImages (elements):
	images=[]
	i=0
	while i<len(elements):
		element=elements[i]
		if isinstance(element,xhtml_object) and element.type[:6]=='image/':
			images.append(element)
			del elements[i]
		else:
			images=images+element.ExtractImages()
			i=i+1
	return images

class xhtml_div(Block,HTML):
	def __init__ (self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.elements=[]

	def AppendElement (self,element):
		assert not (element is None),"Adding None to xhtml_div"
		self.elements.append(element)
	
	def WriteXML (self,f):
		f.write('\n<div')
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for element in self.elements:
			element.WriteXML(f)
		f.write('</div>')

	def ExtractImages (self):
		return ExtractImages(self.elements)

class xhtml_blockquote(SimpleBlock):

	def __init__(self):
		SimpleBlock.__init__(self)
		
	def WriteXML (self,f):
		f.write("\n<blockquote")
		BodyElement.WriteXMLAttributes(self,f)
		f.write(">")
		for element in self.elements:
			element.WriteXML(f)
		f.write("</blockquote>")


class xhtml_ul(Block,HTML):
	def __init__ (self,name="ul"):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.listItems=[]
		self.name=name
	
	def AppendElement (self,element):
		if isinstance(element,xhtml_text):
			assert not element.text.strip(),"PCDATA in <"+self.name+">"
		else:
			assert isinstance(element,xhtml_li),"Adding non-list item to list: %s"%repr(element)
			self.listItems.append(element)

	def WriteXML (self,f):
		f.write('\n<'+self.name)
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for listItem in self.listItems:
			listItem.WriteXML(f)
		f.write('</'+self.name+'>')
		
class xhtml_li(BodyElement,HTML):
	def __init__ (self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.elements=[]
	
	def AppendElement (self,element):
		self.elements.append(element)
	
	def WriteXML (self,f):
		f.write('\n<li')
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for element in self.elements:
			element.WriteXML(f)
		f.write('</li>')
		
class xhtml_p(AtomicBlock):

	def __init__(self):
		AtomicBlock.__init__(self)
	
	def WriteXML (self,f):
		f.write("\n<p")
		BodyElement.WriteXMLAttributes(self,f)
		f.write(">")
		for element in self.elements:
			element.WriteXML(f)
		f.write("</p>")
				
class xhtml_pre(AtomicBlock):

	def __init__(self):
		AtomicBlock.__init__(self)
		
	def WriteXML (self,f):
		f.write("\n<pre")
		BodyElement.WriteXMLAttributes(self,f)
		f.write(">")
		for element in self.elements:
			element.WriteXML(f)
		f.write("</pre>")
								
class xhtml_object(Inline,HTML):
	def __init__ (self):
		HTML.__init__(self)
		self.data=None
		self.type=None
		self.height=None
		self.width=None
		
	def SetData (self,data):
		self.data=data
	
	def SetType (self,type):
		self.type=type
	
	def SetHeight (self,height):
		self.height=height
	
	def SetWidth (self,width):
		self.width=width

	def WriteXML (self,f):
		f.write("<object")
		if self.data:
			f.write(' data="'+XMLString(self.data)+'"')
		if self.type:
			f.write(' type="'+XMLString(self.type)+'"')
		if self.width:
			f.write(' width="'+str(self.width)+'"')
		if self.width:
			f.write(' height="'+str(self.height)+'"')
		f.write("/>")

class xhtml_table(Block,HTML):
	def __init__(self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.tableBody=[]
		self.summary=None
	
	def SetSummary (self,summary):
		self.summary=summary
		
	def AppendElement (self,element):
		if isinstance(element,xhtml_text):
			assert not element.text.strip(),"PCDATA in <table>"
		elif isinstance(element,xhtml_tbody):
			self.tableBody.append(element)
		else:
			assert isinstance(element,xhtml_tr),"Adding non-table tag to table: %s"%repr(element)
			if not self.tableBody:
				# An implied table body
				self.tableBody.append(xhtml_tbody())
			self.tableBody[0].AppendElement(element)

	def WriteXML (self,f):
		f.write('\n<table')
		BodyElement.WriteXMLAttributes(self,f)
		if self.summary:
			f.write(' summary="'+XMLString(self.summary)+'"')
		f.write('>')
		for tbody in self.tableBody:
			tbody.WriteXML(f)
		f.write('</table>')

class xhtml_tbody(BodyElement,HTML):
	def __init__(self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.rows=[]
	
	def AppendElement (self,element):
		if isinstance(element,xhtml_text):
			assert not element.text.strip(),"PCDATA in <tbody>"
		else:
			assert isinstance(element,xhtml_tr),"Adding non-table tag to tbody: %s"%repr(element)
			self.rows.append(element)
	
	def WriteXML (self,f):
		f.write('\n<tbody')
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for tr in self.rows:
			tr.WriteXML(f)
		f.write('</tbody>')
		
class xhtml_tr(BodyElement,HTML):
	def __init__(self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.cells=[]
	
	def AppendElement (self,element):
		if isinstance(element,xhtml_text):
			assert not element.text.strip(),"PCDATA in <tr>"
		else:
			assert isinstance(element,TableCell),"Adding non-table cell tag to tr: %s"%repr(element)
			self.cells.append(element)
	
	def WriteXML (self,f):
		f.write('\n<tr')
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for tcell in self.cells:
			tcell.WriteXML(f)
		f.write('</tr>')

class TableCell(BodyElement,HTML):
	def __init__(self,name="td"):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.name=name
		self.elements=[]
	
	def AppendElement (self,element):
		self.elements.append(element)
	
	def WriteXML (self,f):
		f.write('\n<'+self.name)
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		for element in self.elements:
			element.WriteXML(f)
		f.write('</'+self.name+'>')			
	
	
class xhtml_img(Inline,HTML):
	def __init__ (self):
		BodyElement.__init__(self)
		HTML.__init__(self)
		self.src=None
		self.alt=""
		self.longdesc=None
		self.height=None
		self.width=None
		
	def SetSrc (self,src):
		self.src=src
	
	def SetAlt (self,alt):
		self.alt=alt
	
	def SetLongDesc (self,longdesc):
		self.longdesc=None
	
	def SetHeight (self,height):
		self.height=height
	
	def SetWidth (self,width):
		self.width=width

	def WriteXML (self,f):
		f.write("<img")
		if self.src:
			f.write(' src="'+XMLString(self.src)+'"')
		f.write(' alt="'+XMLString(self.alt)+'"')
		if self.longdesc:
			f.write(' longdesc="'+XMLString(self.longdesc)+'"')
		if self.width:
			f.write(' width="'+str(self.width)+'"')
		if self.width:
			f.write(' height="'+str(self.height)+'"')
		f.write("/>")

class xhtml_br(Inline,HTML):
	def __init__ (self):
		HTML.__init__(self)
		
	def WriteXML (self,f):
		f.write("<br/>\n")
		
class xhtml_text(Inline,HTML):
	def __init__ (self,text=""):
		HTML.__init__(self)
		self.text=text
		
	def SetText (self, text):
		self.text=text
	
	def WriteXML (self,f):
		f.write(XMLString(self.text))

	def ExtractText (self):
		return self.text

class just_text(xhtml_text):
	def __init__(self, text=""):
		xhtml_text.__init__(self, text)

class Interaction:
	def __init__ (self):
		self.response=None

	def BindResponse (self,response):
		self.response=response
		
	def WriteXMLAttributes (self,f):
		f.write(' responseIdentifier="'+self.response+'"')
	
class BlockInteraction(Block,Interaction):
	def __init__ (self):
		BodyElement.__init__(self)
		Interaction.__init__(self)
		self.prompt=None
	
	def GetPrompt (self):
		if not self.prompt:
			self.prompt=Prompt()
		return self.prompt

class InlineInteraction(Inline,Interaction): pass

class Prompt:
	def __init__ (self):
		self.elements=[]

	def AppendElement (self,element):
		self.elements.append(element)
				
	def WriteXML (self,f):
		f.write('\n<prompt><div class="html">')
		for element in self.elements:
			element.WriteXML(f)
		f.write('</div></prompt>')
		
class ChoiceInteraction(BlockInteraction):
	def __init__ (self):
		BlockInteraction.__init__(self)
		self.shuffle=0
		self.maxChoices=1
		self.choices=[]
		
	def SetShuffle (self,shuffle):
		self.shuffle=shuffle
	
	def SetMaxChoices (self,maxChoices):
		self.maxChoices=maxChoices

	def WriteXML (self,f):
		f.write("\n<choiceInteraction")
		Interaction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		if self.shuffle:
			f.write(' shuffle="true"')
		else:
			f.write(' shuffle="false"')
		f.write(' maxChoices="'+str(self.maxChoices)+'"')
		f.write('>')
		if self.prompt:
			self.prompt.WriteXML(f)
		for choice in self.choices:
			choice.WriteXML(f)
		f.write('\n</choiceInteraction>')
		
	def AddChoice (self,choice):
		self.choices.append(choice)
				
class OrderInteraction(BlockInteraction):
	def __init__ (self):
		BlockInteraction.__init__(self)
		self.shuffle=0
		self.choices=[]
		
	def SetShuffle (self,shuffle):
		self.shuffle=shuffle
	
	def WriteXML (self,f):
		f.write("\n<orderInteraction")
		Interaction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		if self.shuffle:
			f.write(' shuffle="true"')
		else:
			f.write(' shuffle="false"')
		f.write('>')
		if self.prompt:
			self.prompt.WriteXML(f)
		for choice in self.choices:
			choice.WriteXML(f)
		f.write('\n</orderInteraction>')
		
	def AddChoice (self,choice):
		self.choices.append(choice)
				
class AssociateInteraction(BlockInteraction):
	def __init__ (self):
		BlockInteraction.__init__(self)
		self.shuffle=0
		self.maxAssociations=1
		self.choices=[]
		
	def SetShuffle (self,shuffle):
		self.shuffle=shuffle
	
	def SetMaxAssociations (self,maxAssociations):
		self.maxAssociations=maxAssociations

	def WriteXML (self,f):
		f.write("\n<associateInteraction")
		Interaction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		if self.shuffle:
			f.write(' shuffle="true"')
		else:
			f.write(' shuffle="false"')
		f.write(' maxAssociations="'+str(self.maxAssociations)+'"')
		f.write('>')
		if self.prompt:
			self.prompt.WriteXML(f)
		for choice in self.choices:
			choice.WriteXML(f)
		f.write('\n</associateInteraction>')
		
	def AddChoice (self,choice):
		self.choices.append(choice)
				
class Choice:
	def __init__ (self):
		self.identifier=""
		self.fixed=None
		
	def SetIdentifier (self,identifier):
		assert not (identifier is None)
		self.identifier=identifier
	
	def GetIdentifier (self):
		return self.identifier
	
	def SetFixed (self,fixed):
		self.fixed=fixed
	
	def WriteXMLAttributes (self,f):
		f.write(' identifier="'+XMLString(self.identifier)+'"')
		if self.fixed:
			f.write(' fixed="true"')
		elif not (self.fixed is None):
			f.write(' fixed="false"')
		
class SimpleChoice(Choice,BodyElement):
	def __init__ (self):
		BodyElement.__init__(self)
		Choice.__init__(self)
		self.elements=[]
		
	def AppendElement (self,element):
		self.elements.append(element)

	def WriteXML (self,f):
		f.write("\n<simpleChoice")
		BodyElement.WriteXMLAttributes(self,f)
		Choice.WriteXMLAttributes(self,f)
		f.write('>')
		for element in self.elements:
			element.WriteXML(f)
		f.write("</simpleChoice>")

class AssociableChoice(Choice):
	def __init__ (self):
		Choice.__init__(self)
		self.elements=[]
		self.matchMax=0
		self.matchGroup=[]
				
	def AppendElement (self,element):
		self.elements.append(element)

	def SetMatchMax (self,max):
		self.matchMax=max
	
	def SetMatchGroup (self,group):
		self.matchGroup=group

	def WriteXMLAttributes (self,f):
		Choice.WriteXMLAttributes(self,f)
		f.write(' matchMax="'+str(self.matchMax)+'"')
		if self.matchGroup:
			f.write(' matchGroup="'+string.join(self.matchGroup,' ')+'"')
		
class SimpleAssociableChoice(AssociableChoice):
	def __init__ (self):
		AssociableChoice.__init__(self)
	
	def WriteXML (self,f):
		f.write("\n<simpleAssociableChoice")
		AssociableChoice.WriteXMLAttributes(self,f)
		f.write('>')
		for element in self.elements:
			element.WriteXML(f)
		f.write("</simpleAssociableChoice>")

class  StringInteraction:
	def __init__(self):
		self.base=None
		self.stringIdentifier=None
		self.expectedLength=None
	
	def SetBase (self,base):
		self.base=base
	
	def SetStringIdentifier (self,identifier):
		self.stringIdentifier=identifier
	
	def SetExpectedLength (self,length):
		self.expectedLength=length
	
	def WriteXMLAttributes (self,f):
		if self.stringIdentifier:
			f.write(' stringIdentifier="'+self.stringIdentifier+'"')
		if self.base:
			f.write(' base="'+str(self.base)+'"')
		if self.expectedLength:
			f.write(' expectedLength="'+str(self.expectedLength)+'"')

class  ExtendedTextInteraction(BlockInteraction,StringInteraction):
	def __init__(self):
		BlockInteraction.__init__(self)
		StringInteraction.__init__(self)
		self.maxStrings=None

	def SetMaxStrings (self,maxStrings):
		self.maxStrings=maxStrings
	
	def WriteXML (self,f):
		f.write("\n<extendedTextInteraction")
		Interaction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		StringInteraction.WriteXMLAttributes(self,f)
		if self.maxStrings:
			f.write(' maxStrings="'+str(self.maxStrings)+'"')
		if self.prompt:
			f.write(">")
			self.prompt.WriteXML(f)
			f.write("</extendedTextInteraction>")
		else:
			f.write("/>")

class TextEntryInteraction (InlineInteraction,StringInteraction):
	def __init__(self):
		BodyElement.__init__(self)
		Interaction.__init__(self)
		StringInteraction.__init__(self)
		
	def WriteXML (self,f):
		f.write("\n<textEntryInteraction")
		Interaction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		StringInteraction.WriteXMLAttributes(self,f)
		f.write("/>")

class GraphicInteraction (BlockInteraction):
	def __init__(self):
		BlockInteraction.__init__(self)
		self.graphic=None

	def SetGraphic (self,graphic):
		self.graphic=graphic

	def WriteXMLAttributes (self,f):
		Interaction.WriteXMLAttributes(self,f)
		
class HotspotInteraction (GraphicInteraction):
	def __init__ (self):
		GraphicInteraction.__init__(self)
		self.maxChoices=1
		self.choices=[]
	
	def SetMaxChoices (self,maxChoices):
		self.maxChoices=maxChoices
	
	def AddChoice (self,choice):
		self.choices.append(choice)
	
	def WriteXML (self,f):
		f.write("\n<hotspotInteraction")
		GraphicInteraction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		if self.maxChoices:
			f.write(' maxChoices="'+str(self.maxChoices)+'"')
		f.write('>')
		if self.prompt:
			self.prompt.WriteXML(f)
		self.graphic.WriteXML(f)
		for choice in self.choices:
			choice.WriteXML(f)
		f.write('</hotspotInteraction>')

class SelectPointInteraction (GraphicInteraction):
	def __init__ (self):
		GraphicInteraction.__init__(self)
		self.maxChoices=1
	
	def SetMaxChoices (self,maxChoices):
		self.maxChoices=maxChoices
	
	def WriteXML (self,f):
		f.write("\n<selectPointInteraction")
		GraphicInteraction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		if self.maxChoices:
			f.write(' maxChoices="'+str(self.maxChoices)+'"')
		f.write('>')
		if self.prompt:
			self.prompt.WriteXML(f)
		self.graphic.WriteXML(f)
		f.write('</selectPointInteraction>')

class GraphicOrderInteraction (GraphicInteraction):
	def __init__ (self):
		GraphicInteraction.__init__(self)
		self.choices=[]
	
	def AddChoice (self,choice):
		self.choices.append(choice)
	
	def WriteXML (self,f):
		f.write("\n<graphicOrderInteraction")
		GraphicInteraction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		f.write('>')
		self.graphic.WriteXML(f)
		for choice in self.choices:
			choice.WriteXML(f)
		f.write('</graphicOrderInteraction>')

class Hotspot:
	def __init__(self):
		self.shape="default"
		self.coords=[]
		self.hotspotLabel=None
	
	def SetShape (self,shape,coords):
		self.shape=shape
		self.coords=coords
	
	def SetHotspotLabel (self,value):
		self.hotspotLabel=value
	
	def WriteXMLAttributes (self,f):
		f.write(' shape="'+XMLString(self.shape)+'"')
		cStrs=[]
		for c in self.coords:
			cStrs.append(str(c))
		f.write(' coords="'+string.join(cStrs,' ')+'"')
		if self.hotspotLabel:
			f.write(' hotspotLabel="'+XMLString(self.hotspotLabel)+'"')
		
class HotspotChoice (Choice,Hotspot):
	def __init__ (self):
		Choice.__init__(self)
		Hotspot.__init__(self)
		
	def WriteXML (self,f):
		f.write('\n<hotspotChoice')
		Choice.WriteXMLAttributes(self,f)
		Hotspot.WriteXMLAttributes(self,f)
		f.write('/>')
								
class  SliderInteraction(BlockInteraction):
	def __init__(self):
		BlockInteraction.__init__(self)
		self.lowerBound=0
		self.upperBound=0
		self.orientation=None
		self.reverse=None
		self.step=None
		self.stepLabel=None
		
	def SetBounds (self,lowerBound,upperBound):
		self.lowerBound=lowerBound
		self.upperBound=upperBound

	def SetStep (self,step):
		self.step=step
	
	def SetStepLabel (self,stepLabel):
		self.stepLabel=stepLabel
		
	def SetOrientation (self,orientation):
		self.orientation=orientation
	
	def SetReverse (self,reverse):
		self.reverse=reverse
				
	def WriteXML (self,f):
		f.write("\n<sliderInteraction")
		Interaction.WriteXMLAttributes(self,f)
		BodyElement.WriteXMLAttributes(self,f)
		f.write(' lowerBound="'+str(self.lowerBound)+'"')
		f.write(' upperBound="'+str(self.upperBound)+'"')
		if not (self.step is None):
			f.write(' step="'+str(self.step)+'"')
		if self.stepLabel:
			f.write(' stepLabel="true"')
		elif not (self.stepLabel is None):
			f.write(' stepLabel="false"')
		if self.orientation:
			f.write(' orientation="'+XMLString(self.orientation)+'"')
		if self.reverse:
			f.write(' reverse="true"')
		elif not (self.reverse is None):
			f.write(' reverse="false"')			
		if self.prompt:
			f.write(">")
			self.prompt.WriteXML(f)
			f.write("</sliderInteraction>")
		else:
			f.write("/>")

class ResponseProcessing:
	def __init__ (self):
		self.rules=[]
		
	def AddResponseRule (self,rule):
		self.rules.append(rule)
	
	def WriteXML (self,f):
		if self.rules:
			f.write('\n<responseProcessing>')
			for rule in self.rules:
				rule.WriteXML(f)
			f.write('\n</responseProcessing>')
			
class ResponseRule:
	def WriteXML (self,f):
		f.write("<responseRule>")

class SetOutcomeValue(ResponseRule):
	def __init__ (self,identifier,expression):
		self.identifier=identifier
		self.expression=expression
	
	def WriteXML (self,f):
		f.write('\n<setOutcomeValue identifier="'+XMLString(self.identifier)+'">')
		self.expression.WriteXML(f)
		f.write('</setOutcomeValue>')
	
class ResponseCondition(ResponseRule):
	def __init__ (self):
		self.responseIf=ResponseIf()
		self.responseElseIf=[]
		self.responseElse=None
		
	def GetResponseIf (self):
		return self.responseIf
	
	def AddResponseElseIf (self,rElseIf):
		self.responseElseIf.append(rElseIf)

	def GetResponseElse (self):
		if not self.responseElse:
			self.responseElse=ResponseElse()
		return self.responseElse
	
	def WriteXML (self,f):
		f.write('\n<responseCondition>')
		self.responseIf.WriteXML(f)
		for item in self.responseElseIf:
			item.WriteXML(f)
		if self.responseElse:
			self.responseElse.WriteXML(f)
		f.write('\n</responseCondition>')
			
class ResponseIf:
	def __init__ (self):
		self.expression=None
		self.rules=[]
		
	def SetExpression (self,expression):
		self.expression=expression
	
	def AddResponseRule (self,rule):
		self.rules.append(rule)
	
	def WriteXML (self,f):
		f.write('\n<responseIf>')
		if self.expression:
			self.expression.WriteXML(f)
		for rule in self.rules:
			rule.WriteXML(f)
		f.write('\n</responseIf>')
	
class ResponseElseIf:
	def __init__ (self):
		self.expression=None
		self.rules=[]
		
	def SetExpression (self,expression):
		self.expression=expression

	def AddResponseRule (self,rule):
		self.rules.append(rule)
	
	def WriteXML (self,f):
		f.write('\n<responseElseIf>')
		self.expression.WriteXML(f)
		for rule in self.rules:
			rule.WriteXML(f)
		f.write('\n</responseElseIf>')

class ResponseElse:
	def __init__ (self):
		self.rules=[]
		
	def AddResponseRule (self,rule):
		self.rules.append(rule)
	
	def WriteXML (self,f):
		f.write('\n<responseElse>')
		for rule in self.rules:
			rule.WriteXML(f)
		f.write('\n</responseElse>')

class Expression:
	def WriteXML (self,f):
		f.write("<expression>")
		
class BinaryOperator(Expression):
	def __init__ (self,leftExpression,rightExpression,name):
		self.name=name
		self.left=leftExpression
		self.right=rightExpression

	def WriteXML (self,f):
		f.write("<"+self.name+">")
		self.left.WriteXML(f)
		self.right.WriteXML(f)
		f.write("</"+self.name+">")

class MultiOperator(Expression):
	def __init__ (self,name):
		self.name=name
		self.arguments=[]
		
	def AddExpression(self,expression):
		self.arguments.append(expression)
	
	def WriteXML (self,f):
		f.write("<"+self.name+">")
		for argument in self.arguments:
			argument.WriteXML(f)
		f.write("</"+self.name+">")
	
class NotOperator(Expression):
	def __init__ (self,expression):
		self.expression=expression
		
	def WriteXML (self,f):
		f.write("<not>")
		self.expression.WriteXML(f)
		f.write("</not>")

class AndOperator(MultiOperator):
	def __init__ (self):
		MultiOperator.__init__(self,"and")
		
class OrOperator(MultiOperator):
	def __init__ (self):
		MultiOperator.__init__(self,"or")

class SumOperator(MultiOperator):
	def __init__ (self):
		MultiOperator.__init__(self,"sum")

class ProductOperator(MultiOperator):
	def __init__ (self):
		MultiOperator.__init__(self,"product")

class MultipleOperator(MultiOperator):
	def __init__ (self):
		MultiOperator.__init__(self,"multiple")
		
class OrderedOperator(MultiOperator):
	def __init__ (self):
		MultiOperator.__init__(self,"ordered")

class CustomOperator(MultiOperator):
	def __init__(self,opClass):
		MultiOperator.__init__(self,"customOperator")
		self.opClass=opClass
	
	def WriteXML (self,f):
		f.write("<customOperator")
		if self.opClass:
			f.write(' class="%s"'%XMLString(self.opClass))
		f.write('>')
		for argument in self.arguments:
			argument.WriteXML(f)
		f.write("</customOperator>")
		
class SubtractOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"subtract")
		
class DivideOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"divide")

class MatchOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"match")

class EqualOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"equal")

class LTOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"lt")

class LTEOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"lte")

class GTOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"gt")

class GTEOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"gte")

class MemberOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"member")

class ContainsOperator(BinaryOperator):
	def __init__ (self,leftExpression,rightExpression):
		BinaryOperator.__init__(self,leftExpression,rightExpression,"contains")

class StringMatchOperator(Expression):
	def __init__ (self,leftExpression,rightExpression,caseSensitive,substring=0):
		self.left=leftExpression
		self.right=rightExpression
		self.caseSensitive=caseSensitive
		self.substring=substring
		
	def WriteXML (self,f):
		f.write('<stringMatch ')
		if self.caseSensitive:
			f.write(' caseSensitive="true"')
		else:
			f.write(' caseSensitive="false"')
		if self.substring:
			f.write(' substring="true"')
		else:
			f.write(' substring="false"')
		f.write('>')
		self.left.WriteXML(f)
		self.right.WriteXML(f)
		f.write("</stringMatch>")

class VariableOperator(Expression):
	def  __init__ (self,identifier):
		self.identifier=identifier
		
	def WriteXML (self,f):
		f.write('<variable identifier="'+XMLString(self.identifier)+'"/>')

class IndexOperator(Expression):
	def __init__ (self,expression,index):
		self.index=index
		self.expression=expression
	
	def WriteXML (self,f):
		f.write('<index n="'+str(self.index)+'">')
		self.expression.WriteXML(f)
		f.write('</index>')

class BaseValueOperator(Expression):
	def __init__ (self,baseType,value):
		self.baseType=baseType
		self.value=value
		self.identifier=None

	def SetIdentifier(self, identifier):
		self.identifier=identifier

	def WriteXML (self,f):
		res = '<baseValue baseType="'+XMLString(self.baseType)+'"'
		if self.identifier != None:
			res = res + ' identifier="'+XMLString(self.identifier)+'"'
		res = res + '>'+XMLString(self.value)+'</baseValue>'
		f.write(res)

class IsNullOperator(Expression):
	def __init__ (self,expression):
		self.expression=expression
		
	def WriteXML (self,f):
		f.write("<isNull>")
		self.expression.WriteXML(f)
		f.write("</isNull>")

class NullOperator(Expression):
	def WriteXML (self,f):
		f.write("<null/>")

class InsideOperator(Expression):
	def __init__(self,expression,shape,coords):
		self.expression=expression
		self.shape=shape
		self.coords=coords

	def WriteXML (self,f):
		f.write('<inside shape="'+XMLString(self.shape)+'"')
		cStrs=[]
		for c in self.coords:
			cStrs.append(str(c))
		f.write(' coords="'+string.join(cStrs,' ')+'">')
		self.expression.WriteXML(f)
		f.write("</inside>")


class Calculated:
	def __init__(self):
		self.formula=None
		self.answer_scale=None
		self.answer_tolerance=None
		self.answer_tolerance_type=None
		self.unit_points_percent=None
		self.unit_required=None
		self.unit_value=None
		self.unit_case_sensitive=None
		self.partial_credit_points_percent=None
		self.partial_credit_tolerance=None
		self.partial_credit_tolerance_type=None
		self.var_sets=[]
		self.vars=[]
		self.formula_decimal_places=None
		self.formulas=[]
	
	def add_var_set(self, vs):
		self.var_sets.append(vs)
	
	def add_var(self, var):
		self.vars.append(var)

	def add_formula(self, formula):
		self.formulas.append(formula)
		
	def WriteXML(self, f):
		f.write('\n<itemproc_extension>')
		f.write('\n<calculated>')
		if self.formula: f.write('\n<formula>%s</formula>' % XMLString(self.formula))
		if self.formulas:
			decimals = ""
			if self.formula_decimal_places: decimals = ' decimal_places="%s"' % self.formula_decimal_places
			f.write('\n<formulas%s>' % decimals)
			for formula in self.formulas:
				f.write('<formula>%s</formula>' % formula)
			f.write('\n</formulas>')
		if self.answer_scale: f.write('\n<answer_scale>%s</answer_scale>' % XMLString(self.answer_scale))
		if self.answer_tolerance: f.write('\n<answer_tolerance type="%s">%s</answer_tolerance>' % (self.answer_tolerance_type, XMLString(self.answer_tolerance)))
		if self.unit_points_percent: f.write('\n<unit_points_percent>%s</unit_points_percent>' % XMLString(self.unit_points_percent))
		if self.unit_value: f.write('\n<unit_value>%s</unit_value>' % XMLString(self.unit_value))
		if self.unit_required: f.write('\n<unit_required>%s</unit_required>' % XMLString(self.unit_required))
		if self.unit_case_sensitive: f.write('\n<unit_case_sensitive>%s</unit_case_sensitive>' % XMLString(self.unit_case_sensitive))
		if self.partial_credit_points_percent: f.write('\n<partial_credit_points_percent>%s</partial_credit_points_percent>' % XMLString(self.partial_credit_points_percent))
		if self.partial_credit_tolerance: f.write('\n<partial_credit_tolerance type="%s">%s</partial_credit_tolerance>' % (self.partial_credit_tolerance_type, XMLString(self.partial_credit_tolerance)))
		f.write('\n<vars>')
		for var in self.vars:
			var.WriteXML(f)
		f.write('\n</vars>')
		f.write('\n<var_sets>')
		for var in self.var_sets:
			var.WriteXML(f)
		f.write('\n</var_sets>')
		f.write('\n</calculated>')
		f.write('\n</itemproc_extension>')
		

class VarSet:
	def __init__(self):
		self.vars=[]
		self.answer=None
		self.ident=None

	def add_var(self, var):
		self.vars.append(var)
	
	def WriteXML(self, f):
		f.write('<var_set')
		if self.ident: f.write(' ident="%s"' % XMLString(self.ident))
		f.write('>')
		for var in self.vars:
			var.WriteXML(f)
		if self.answer: f.write('\n<answer>%s</answer>' % XMLString(self.answer))
		f.write('\n</var_set>')

class Var:
	def __init__(self):
		self.name=None
		self.scale=None
		self.min=None
		self.max=None
		self.data=None
	
	def WriteXML(self,f):
		f.write('\n<var')
		if self.name: f.write(' name="%s"' % XMLString(self.name))
		if self.scale: f.write(' scale="%s"' % XMLString(self.scale))
		f.write('>')
		
		if self.data:
			f.write(XMLString(self.data))
		else:
			if self.min: f.write('\n<min>%s</min>' % XMLString(self.min))
			if self.max: f.write('\n<max>%s</max>' % XMLString(self.max))
			f.write("\n")
		
		f.write('</var>')



