"""
Name: vizop_parser
Python version: 3.6.3
"""
from faulttree import FTColumnInCore

"""[----------TEMPLATE---------- """
""" ----------TEMPLATE----------]""" 

"""[----------IMPORT---------- """
""""""
import xml.etree.ElementTree as ET
import xml
from lxml import etree as lxmletree
import string
import inspect
from enum import Enum
import projects, core_classes, faulttree, info
import logging
""" ----------IMPORT----------]""" 

"""[----------CHARACTER CHECK---------- """
class Chars:
	#Avoid sensitive/unparsable symbol
	VALID_CHARS = "!#$%()*+,-.:;=?@[]^_`{|}~ %s%s" + string.ascii_letters + string.digits
""" ----------CHARACTER CHECK----------]"""

"""[----------UTIL---------- """
def pS(inputString, trimString = True, filterForbiddenChar = True, noSpace = False) -> str:
	# process string
	assert type(inputString) == str
	assert type(trimString) == bool
	assert type(filterForbiddenChar) == bool
	assert type(noSpace) == bool
	
	formattedString = inputString
	if trimString:
		formattedString = formattedString.strip()
	
	if filterForbiddenChar:
		formattedString = ''.join(c for c in formattedString if c in Chars.VALID_CHARS)

	if noSpace:
		formattedString = '_'.join(formattedString.split(' '))
	
	return formattedString

def getNumberOfInstance(input_class):
	#get the number of instance for a Class by using garbage collector
	import gc
	return ('Number of {} in memory:{}'.format(input_class,len(list(filter(lambda x: isinstance(x, input_class), gc.get_objects())))))

def autoGenerateTagID(elementRoot): #void
	# generate unique ID for all elements
	print (type(elementRoot))
	assert type(elementRoot) == xml.etree.ElementTree.Element, type(elementRoot)

	iD = 1
	for each_Element in elementRoot.iter():
		each_Element.set('TagID', str(iD))
		iD = iD + 1
	pass

def isInType(StringInput, EnumClass):
	assert type(StringInput) == str
	assert inspect.isclass(EnumClass)
	for t in EnumClass:
		if t.value.lower() == StringInput.lower():
			return True
	return False

def getTypeByValue(StringInput, EnumClass):
	assert type(StringInput) == str
	assert inspect.isclass(EnumClass)
	for t in EnumClass:
		if t.value.lower() == StringInput.lower():
			return t
	return None

def ic(StringInput, eNumAttr) -> bool:
	# ignore case parser method
	assert type(StringInput) == str
	# TODO assert type(eNumAttr) ==
	# assert

	# compare string ignore case
	return StringInput.lower() == eNumAttr.value.lower()

""" ----------UTIL----------]"""

"""[----------Project > XML---------- """
def convertProjectToXml(Proj, ProjectFilename):
	# convert project to XML
	# void, convert from Project Item to pre-defined XML project
	assert type(Proj) == projects.ProjectItem
	assert type(ProjectFilename) == str

	# write XML tree to actual file
	MyXMLTree = ET.ElementTree() # create new XML structure

	# set the skeleton as the XML tree root element
	MyXMLTree._setroot(ET.fromstring(projects.XMLTreeSkeleton))
	MyXMLRoot = MyXMLTree.getroot()

	# create sub-elements according to project item file structure
	# J: generic parser could be created for simple string parsing

	# ShortTitle
	if Proj.ShortTitle != '':
		MyXMLRoot_ShortTitle = ET.SubElement(MyXMLRoot, info.ShortTitleTag)
		MyXMLRoot_ShortTitle.text = pS(str(Proj.ShortTitle))

	# ProjNumber
	if Proj.ProjNumber != '':
		MyXMLRoot_ProjNumber = ET.SubElement(MyXMLRoot, info.ProjNumberTag)
		MyXMLRoot_ProjNumber.text = pS(str(Proj.ProjNumber))

	# Description
	if Proj.Description != '':
		MyXMLRoot_Description = ET.SubElement(MyXMLRoot, info.DescriptionTag)
		MyXMLRoot_Description.text = pS(str(Proj.Description))

	# EditNumber
	if Proj.EditNumber != '':
		MyXMLRoot_EditNumber = ET.SubElement(MyXMLRoot, info.EditNumberTag)
		MyXMLRoot_EditNumber.text = pS(str(Proj.EditNumber))

	# TeamMembers
	if len(Proj.TeamMembers) > 0 :
		# create outer XML tag
		MyXMLRoot_TeamMembers = ET.SubElement(MyXMLRoot, info.TeamMembersTag)

		# TeamMember
		each_teamMember: core_classes.TeamMember
		for each_teamMember in Proj.TeamMembers:
			MyXMLRoot_TeamMembers_TeamMember = ET.SubElement(MyXMLRoot_TeamMembers, info.TeamMemberTag)
			assert type(each_teamMember) == core_classes.TeamMember

			# <ID [ID int as str] />
			MyXMLRoot_TeamMembers_TeamMember_ID = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, info.IDTag)
			MyXMLRoot_TeamMembers_TeamMember_ID.text =  pS(str(each_teamMember.iD))

			# <Name [Name as str] />
			MyXMLRoot_TeamMembers_TeamMember_Name = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, info.NameTag)
			MyXMLRoot_TeamMembers_TeamMember_Name.text = pS(each_teamMember.name)

			# <Role [Role as str] />
			MyXMLRoot_TeamMembers_TeamMember_Role = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, info.RoleTag)
			MyXMLRoot_TeamMembers_TeamMember_Role.text = pS(each_teamMember.role)

			# < Affiliation[Affiliation as str] / >
			MyXMLRoot_TeamMembers_TeamMember_Affiliation = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, info.AffiliationTag)
			MyXMLRoot_TeamMembers_TeamMember_Affiliation.text = pS(each_teamMember.affiliation)

	#Process Units
	if len(Proj.ProcessUnits) > 0:
		# create outer XML tag
		MyXMLRoot_ProcessUnits = ET.SubElement(MyXMLRoot, info.ProcessUnitsTag)

		for each_ProcessUnit in Proj.ProcessUnits:
			MyXMLRoot_ProcessUnits_ProcessUnit = ET.SubElement(MyXMLRoot_ProcessUnits, info.ProcessUnitTag)
			assert type(each_ProcessUnit) == projects.ProcessUnit

			# <ID [ID int as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_ID = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, info.IDTag)
			MyXMLRoot_ProcessUnits_ProcessUnit_ID.text = pS(str(each_ProcessUnit.ID))

			# <UnitNumber [UnitNumber as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, info.UnitNumber)
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber.text = pS(str(each_ProcessUnit.UnitNumber))

			# <ShortName [ShortName as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_ShortName = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, info.ShortNameTag)
			MyXMLRoot_ProcessUnits_ProcessUnit_ShortName.text = pS(str(each_ProcessUnit.ShortName))

			# <LongName [LongName as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_LongName = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, info.LongNameTag)
			MyXMLRoot_ProcessUnits_ProcessUnit_LongName.text = pS(str(each_ProcessUnit.LongName))

	#Risk Receptors
	if len(Proj.RiskReceptors) > 0:
		# create outer XML tag
		MyXMLRoot_RiskReceptors = ET.SubElement(MyXMLRoot, info.RiskReceptorsTag)

		for each_RiskReceptor in Proj.RiskReceptors:
			assert type(each_RiskReceptor) == core_classes.RiskReceptorItem
			MyXMLRoot_RiskReceptors_RiskReceptor = ET.SubElement(MyXMLRoot_RiskReceptors, info.RiskReceptorTag)

			# <ID [ID int as str] />
			MyXMLRoot_RiskReceptors_RiskReceptor_ID = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, info.IDTag)
			MyXMLRoot_RiskReceptors_RiskReceptor_ID.text = pS(str(each_RiskReceptor.ID))

			#<Name [HumanName as str] />
			MyXMLRoot_RiskReceptors_RiskReceptor_HumanName = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, info.NameTag)
			MyXMLRoot_RiskReceptors_RiskReceptor_HumanName.text = pS(each_RiskReceptor.HumanName)

	# Numbering Systems
	if len(Proj.NumberSystems) > 0:
		# create outer XML tag
		MyXMLRoot_NumberSystems = ET.SubElement(MyXMLRoot, info.NumberSystemsTag)

		for each_NumberSystem in Proj.NumberSystems:
			# create outer XML tag
			MyXMLRoot_NumberSystems_NumberSystem = ET.SubElement(MyXMLRoot_NumberSystems, info.NumberSystemsTag)

			if type(each_NumberSystem) == str:

				MyXMLRoot_NumberSystems_NumberSystem_Type = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.TypeTag)
				MyXMLRoot_NumberSystems_NumberSystem_Type.text = pS(info.NumberSystemStringType)

				MyXMLRoot_NumberSystems_NumberSystem_Value = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.ValueTag)
				MyXMLRoot_NumberSystems_NumberSystem_Value.text = pS(each_NumberSystem)
				pass

			elif type(each_NumberSystem) == core_classes.ParentNumberChunkItem:
				#TODO need to map object ID

				#MyXMLRoot_NumberSystems_NumberSystem_Type = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.TypeTag)
				#MyXMLRoot_NumberSystems_NumberSystem_Type.text = pS(info.NumberSystemParentType)

				#MyXMLRoot_NumberSystems_NumberSystem_ID = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.IDTag)
				#MyXMLRoot_NumberSystems_NumberSystem_ID.text = pS(str(each_NumberSystem.ID))
				pass

			elif type(each_NumberSystem) == core_classes.SerialNumberChunkItem:
				MyXMLRoot_NumberSystems_NumberSystem_Type = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.NumberSystemSerialType)

				#FieldWidth
				MyXMLRoot_NumberSystems_NumberSystem_FieldWidth = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.FieldWidthTag)
				MyXMLRoot_NumberSystems_NumberSystem_FieldWidth.text = pS(str(each_NumberSystem.FieldWidth))

				#PadChar
				MyXMLRoot_NumberSystems_NumberSystem_PadChar = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.PadCharTag)
				MyXMLRoot_NumberSystems_NumberSystem_PadChar.text = pS(str(each_NumberSystem.PadChar))

				#StartSequenceAt
				MyXMLRoot_NumberSystems_NumberSystem_StartSequenceAt = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.StartSequenceAtTag)
				MyXMLRoot_NumberSystems_NumberSystem_StartSequenceAt.text  = pS(str(each_NumberSystem.StartSequenceAt))

				#SkipTo
				if each_NumberSystem.SkipTo != None:
					MyXMLRoot_NumberSystems_NumberSystem_SkipTo = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.SkipToTag)
					MyXMLRoot_NumberSystems_NumberSystem_SkipTo.text = pS(str(each_NumberSystem.SkipTo))

				#GapBefore
				MyXMLRoot_NumberSystems_NumberSystem_GapBefore = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.GapBeforeTag)
				MyXMLRoot_NumberSystems_NumberSystem_GapBefore.text = pS(str(each_NumberSystem.GapBefore))

				#IncludeInNumbering
				MyXMLRoot_NumberSystems_NumberSystem_IncludeInNumbering = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.IncludeInNumberingTag)
				MyXMLRoot_NumberSystems_NumberSystem_IncludeInNumbering.text = pS(str(each_NumberSystem.IncludeInNumbering))

				#NoValue
				MyXMLRoot_NumberSystems_NumberSystem_NoValue = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, info.NoValueTag)
				MyXMLRoot_NumberSystems_NumberSystem_NoValue.text = pS(each_NumberSystem.NoValue)

			elif:
				raise Exception('NumberSystem type incorrect.')
				pass

	# Risk Matrix
	if len(Proj.RiskMatrices) > 0:
		# create outer XML tag
		MyXMLRoot_RiskMatrices = ET.SubElement(MyXMLRoot, info.RiskMatricesTag)

		# LookupTableItem
		for each_RiskMatrix in Proj.RiskMatrices:
			assert type(each_RiskMatrix) == core_classes.LookupTableItem
			MyXMLRoot_RiskMatrices_RiskMatrix = ET.SubElement(MyXMLRoot_RiskMatrices, info.RiskMatrixTag)

			# <Category>
			# J: TODO: could not map Category


			# <SeverityDimension [SeverityDimensionIndex int as str] />
			if each_RiskMatrix.SeverityDimensionIndex != None:
				MyXMLRoot_RiskMatrices_RiskMatrix_SeverityDimension = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix, info.SeverityDimensionTag)
				MyXMLRoot_RiskMatrices_RiskMatrix_SeverityDimension.text = each_RiskMatrix.SeverityDimensionIndex

			if len(each_RiskMatrix.DimensionUnits) > 0:
				MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix,info.DimensionsTag)

				for each_DimensionUnit in each_RiskMatrix.DimensionUnits:
					assert type(each_DimensionUnit) == core_classes.UnitItem
					MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits, info.DimensionTag)

					#Name
					MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit_Name = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit, info.NameTag)
					MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit_Name.text = pS(each_DimensionUnit.HumanName)

			#Key
			# J: TODO
			if len(each_RiskMatrix.Keys) > 0:
				MyXMLRoot_RiskMatrices_RiskMatrix_Key = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix, info.KeyTag)
				MyXMLRoot_RiskMatrices_RiskMatrix_Key.text = ''

			#Entry
			if len(each_RiskMatrix.Values) > 0:
				MyXMLRoot_RiskMatrices_RiskMatrix_Entries = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix, info.EntriesTag)

				for each_Value in each_RiskMatrix.Values:
					MyXMLRoot_RiskMatrices_RiskMatrix_Entries_Entry = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix_Entries, info.EntryTag)
					MyXMLRoot_RiskMatrices_RiskMatrix_Entries_Entry.text = pS(str(each_Value))

	#Constants
	# J: TODO
	if len(Proj.Constants) > 0:
		# create outer XML tag
		MyXMLRoot_Constants = ET.SubElement(MyXMLRoot, info.ConstantsTag)

		for each_Constant in Proj.Constants:
			assert type(each_Constant) == core_classes.ConstantItem
			MyXMLRoot_Constants_Constant = ET.SubElement(MyXMLRoot_Constants, info.ConstantTag)

			# J: TODO cannot map id
			#MyXMLRoot_Constants_Constant_Id = ET.SubElement(MyXMLRoot_Constants_Constant, 'ID')
			#MyXMLRoot_Constants_Constant_Id.text = ''

			# J: TODO cannot map LinkFrom
			#MyXMLRoot_Constants_Constant_LinkFrom = ET.SubElement(MyXMLRoot_Constants_Constant, 'LinkFrom')
			#MyXMLRoot_Constants_Constant_LinkFrom.text = ''

			# J: TODO cannot map ConstValue
			#MyXMLRoot_Constants_Constant_Value = ET.SubElement(MyXMLRoot_Constants_Constant, 'ConstValue')
			#MyXMLRoot_Constants_Constant_Value.text = ''

	# RecommendationReport
	# J: TODO cannot map RecommendationReport

	#FaultTree
	if len(Proj.FaultTree) > 0:
		# create outer XML tag
		MyXMLRoot_FaultTrees = ET.SubElement(MyXMLRoot, info.FaultTreesTag)

		each_FaultTree: faulttree.FTObjectInCore
		for each_FaultTree in Proj.FaultTrees:
			assert type(each_FaultTree) == faulttree.FTObjectInCore

			MyXMLRoot_FaultTrees_FaultTree = ET.SubElement(MyXMLRoot_FaultTrees, info.FaultTreeTag)

			#ID
			MyXMLRoot_FaultTrees_FaultTree_Id = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.IDTag)
			MyXMLRoot_FaultTrees_FaultTree_Id.text = pS(str(each_FaultTree.ID))

			#SIFName
			MyXMLRoot_FaultTrees_FaultTree_SIFName = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.SIFNameTag)
			MyXMLRoot_FaultTrees_FaultTree_SIFName.text = pS(str(each_FaultTree.SIFName))

			#OpMode
			MyXMLRoot_FaultTrees_FaultTree_OpMode = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.OpModeTag)
			MyXMLRoot_FaultTrees_FaultTree_OpMode.text = pS(str(each_FaultTree.OpMode.XMLName))

			#Rev
			MyXMLRoot_FaultTrees_FaultTree_Rev = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.RevTag)
			MyXMLRoot_FaultTrees_FaultTree_Rev.text = pS(each_FaultTree.Rev)

			#TargetRiskRedMeasure
			MyXMLRoot_FaultTrees_FaultTree_TargetRiskRedMeasure = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.TargetRiskRedMeasureTag)
			MyXMLRoot_FaultTrees_FaultTree_TargetRiskRedMeasure.text = pS(each_FaultTree.TargetRiskRedMeasure)

			#SILTargetValue
			MyXMLRoot_FaultTrees_FaultTree_SILTargetValue = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.SILTargetValueTag)
			MyXMLRoot_FaultTrees_FaultTree_SILTargetValue.text = pS(each_FaultTree.SILTargetValue)

			#BackgColour
			MyXMLRoot_FaultTrees_FaultTree_BackgColour = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.BackgColour)
			MyXMLRoot_FaultTrees_FaultTree_BackgColour.text = pS(each_FaultTree.BackgColour)

			#TextColour
			MyXMLRoot_FaultTrees_FaultTree_TextColour = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.TextColour)
			MyXMLRoot_FaultTrees_FaultTree_TextColour.text = pS(each_FaultTree.TextColour)

			#Columns
			MyXMLRoot_FaultTrees_FaultTree_Columns = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.ColumnsTag)

			each_Column: FTColumnInCore
			for each_Column in each_FaultTree.Columns:
				#Column
				MyXMLRoot_FaultTrees_FaultTree_Columns_Column = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns,info.FTColumnTag)


				for each_FTEvent in each_Column:

					if type(each_FTEvent) == faulttree.FTEventInCore:
						#FTEvent
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTEventTag)


					if type(each_FTEvent) == faulttree.FTGateItemInCore:
						#FTGate
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTGateTag)


					if type(each_FTEvent) == faulttree.FTConnectorItemInCore:
						#FTConnectorIn
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnectorIn = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTConnectorInTag)


					if type(each_FTEvent) == faulttree.FTConnectorItemInCore:
						#FTConnectorOut
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnectorOut = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTConnectorOutTag)

				pass

			#TolRiskModel
			#TODO canot map TolRiskModel
			MyXMLRoot_FaultTrees_FaultTree_TolRiskModel = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info)
			MyXMLRoot_FaultTrees_FaultTree_TolRiskModel = pS(each_FaultTree.MyTolRiskModel)

			#Severity
			MyXMLRoot_FaultTrees_FaultTree_Severity = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.SeverityTag)

			#Name
			each_Key: core_classes.RiskReceptorItem
			for each_Key in each_FaultTree.Severity:
				# RR
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Severity, info.RRTag)
				# Name
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_Name = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Severity_RR, info.NameTag)
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_Name.text = pS(each_Key.XMLName)
				# SeverityValue
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_SeverityValue = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Severity_RR, info.SeverityValueTag)
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_SeverityValue.text = pS(each_FaultTree.Severity.get(each_Key))


				pass


			pass

	#Comment
	if len(Proj.Comments) > 0:
		MyXMLRoot_Comments = ET.SubElement(MyXMLRoot, info.CommentsTag)

		each_Comment: core_classes.Comment
		for each_Comment in Proj.Comments:
			assert type(each_Comment) == core_classes.Comment
			MyXMLRoot_Comments_Comment = ET.SubElement(MyXMLRoot_Comments,info.CommentTag)

			MyXMLRoot_Comments_Comment_Id = ET.SubElement(MyXMLRoot_Comments_Comment, info.IDTag)
			MyXMLRoot_Comments_Comment_Id.text = pS(str(each_Comment.iD))

			MyXMLRoot_Comments_Comment_Content = ET.SubElement(MyXMLRoot_Comments_Comment, info.ContentTag)
			MyXMLRoot_Comments_Comment_Content.text = pS(str(each_Comment.content))

			MyXMLRoot_Comments_Comment_isVisible = ET.SubElement(MyXMLRoot_Comments_Comment, info.isVisibleTag)
			MyXMLRoot_Comments_Comment_isVisible.text = pS(str(each_Comment.isVisible))

			MyXMLRoot_Comments_Comment_showInReport = ET.SubElement(MyXMLRoot_Comments_Comment, info.showInReportTag)
			MyXMLRoot_Comments_Comment_showInReport.text = pS(str(each_Comment.showInReport))

	#Bookmark
	if len(Proj.Bookmarks) > 0:
		MyXMLRoot_Bookmarks = ET.SubElement(MyXMLRoot, info.BookmarksTag)

		each_Bookmark: core_classes.Bookmark
		for each_Bookmark in Proj.Bookmarks:
			assert type(each_Bookmark) == core_classes.Bookmark
			MyXMLRoot_Bookmarks_Bookmark = ET.SubElement(MyXMLRoot_Bookmarks,info.BookmarkTag)

			MyXMLRoot_Bookmarks_Bookmark_ID = ET.SubElement(MyXMLRoot_Bookmarks_Bookmark, info.IDTag)
			MyXMLRoot_Bookmarks_Bookmark_ID.text = pS(str(each_Bookmark.iD))

			MyXMLRoot_Bookmarks_Bookmark_isDeleted = ET.SubElement(MyXMLRoot_Bookmarks_Bookmark, info.isDeletedTag)
			MyXMLRoot_Bookmarks_Bookmark_isDeleted.text = pS(str(each_Bookmark.isDeleted))

	pass

	# later, add more code here to write all PHA objects into the XML tree
	# write the XML file

	# generate tag Id for all element
	autoGenerateTagID(MyXMLRoot)

	MyXMLTree.write(ProjectFilename, encoding="UTF-8", xml_declaration=True)

	'''
	#J: Display XML tree on screen
	ET.dump(MyXMLTree)
	'''
	pass

""" ----------Project > XML----------]""" 

"""[----------XML > Project---------- """


""" ----------XML > Project----------]""" 

"""[----------TESTING AREA---------- """

def testCheckType(stringInput: str) -> str:
	pass

""" ----------TESTING AREA----------]"""  

"""[----------RUN MAIN PROGRAM---------- """
def main():
	pass

if __name__ == '__main__':
	main()
""" ----------RUN MAIN PROGRAM----------]"""  
