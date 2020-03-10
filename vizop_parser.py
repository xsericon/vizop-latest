"""
Name: vizop_parser
"""
from faulttree import FTColumnInCore

"""[----------TEMPLATE---------- """
""" ----------TEMPLATE----------]""" 

"""[----------IMPORT---------- """
""""""
import xml.etree.ElementTree as ET
import xml
import string
import inspect
import projects, core_classes, faulttree, info
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
	# get the number of instance for a Class by using garbage collector
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
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, info.UnitNumberTag)
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
		MyXMLRoot_NumberSystem = ET.SubElement(MyXMLRoot, info.NumberSystemTag)

		for each_NumberSystem in Proj.NumberSystems:
			#TODO J: cannot map NumberSystem ID

			# create outer XML tag
			MyXMLRoot_NumberSystem_Chunk = ET.SubElement(MyXMLRoot_NumberSystem, info.NumberSystemTag)

			#each_NumberSystem: str
			if type(each_NumberSystem) == str:
				MyXMLRoot_NumberSystem_Chunk_Type = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.TypeTag)
				MyXMLRoot_NumberSystem_Chunk_Type.text = pS(info.NumberSystemStringType)

				MyXMLRoot_NumberSystem_Chunk_Value = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.ValueTag)
				MyXMLRoot_NumberSystem_Chunk_Value.text = pS(each_NumberSystem)

			#each_NumberSystem: core_classes.ParentNumberChunkItem
			elif type(each_NumberSystem) == core_classes.ParentNumberChunkItem:
				MyXMLRoot_NumberSystem_Chunk_Type = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.TypeTag)
				MyXMLRoot_NumberSystem_Chunk_Type.text = pS(info.NumberSystemParentType)

				MyXMLRoot_NumberSystem_Chunk_ID = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.IDAttribName)
				MyXMLRoot_NumberSystem_Chunk_ID.text = pS(each_NumberSystem.Source)

			#each_NumberSystem: core_classes.SerialNumberChunkItem
			elif type(each_NumberSystem) == core_classes.SerialNumberChunkItem:
				MyXMLRoot_NumberSystem_Chunk_Type = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.TypeTag)
				MyXMLRoot_NumberSystem_Chunk_Type.text = pS(info.NumberSystemSerialType)

				#FieldWidth
				MyXMLRoot_NumberSystem_Chunk_FieldWidth = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.FieldWidthTag)
				MyXMLRoot_NumberSystem_Chunk_FieldWidth.text = pS(str(each_NumberSystem.FieldWidth))

				#PadChar
				MyXMLRoot_NumberSystem_Chunk_PadChar = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.PadCharTag)
				MyXMLRoot_NumberSystem_Chunk_PadChar.text = pS(str(each_NumberSystem.PadChar))

				#StartSequenceAt
				MyXMLRoot_NumberSystem_Chunk_StartSequenceAt = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.StartSequenceAtTag)
				MyXMLRoot_NumberSystem_Chunk_StartSequenceAt.text  = pS(str(each_NumberSystem.StartSequenceAt))

				#SkipTo
				if each_NumberSystem.SkipTo is None:
					MyXMLRoot_NumberSystem_Chunk_SkipTo = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.SkipToTag)
					MyXMLRoot_NumberSystem_Chunk_SkipTo.text = pS(str(each_NumberSystem.SkipTo))

				#GapBefore
				MyXMLRoot_NumberSystem_Chunk_GapBefore = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.GapBeforeTag)
				MyXMLRoot_NumberSystem_Chunk_GapBefore.text = pS(str(each_NumberSystem.GapBefore))

				#IncludeInNumbering
				MyXMLRoot_NumberSystem_Chunk_IncludeInNumbering = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.IncludeInNumberingTag)
				MyXMLRoot_NumberSystem_Chunk_IncludeInNumbering.text = pS(str(each_NumberSystem.IncludeInNumbering))

				#NoValue
				MyXMLRoot_NumberSystem_Chunk_NoValue = ET.SubElement(MyXMLRoot_NumberSystem_Chunk, info.NoValueTag)
				MyXMLRoot_NumberSystem_Chunk_NoValue.text = pS(each_NumberSystem.NoValue)

			else:
				raise Exception('NumberSystem type incorrect.')

	# Risk Matrix
	if len(Proj.RiskMatrices) > 0:

		# LookupTableItem
		for each_RiskMatrix in Proj.RiskMatrices:
			assert type(each_RiskMatrix) == core_classes.LookupTableItem
			MyXMLRoot_RiskMatrix = ET.SubElement(MyXMLRoot, info.RiskMatrixTag)

			# <Category>
			# Map to Keys
			if len(each_RiskMatrix.Keys) > 0:
				each_Category: core_classes.CategoryNameItem
				# TODO J: cannot map the object attribute which stores the list of categories
				for each_Category in each_RiskMatrix.Value:

					#Category
					MyXMLRoot_RiskMatrix_Category = ET.SubElement(MyXMLRoot_RiskMatrix, info.CategoryTag)

					# ID
					# TODO J: cannot map Catergory ID
					"""
					MyXMLRoot_RiskMatrix_Category_ID = ET.SubElement(MyXMLRoot_RiskMatrix_Category, info.IDTag)
					MyXMLRoot_RiskMatrix_Category_ID.text = pS(each_Key.)
					"""

					# Name
					MyXMLRoot_RiskMatrix_Category_Name = ET.SubElement(MyXMLRoot_RiskMatrix_Category, info.NameTag)
					MyXMLRoot_RiskMatrix_Category_Name.text = pS(each_Category.HumanName)

					# Description
					MyXMLRoot_RiskMatrix_Category_Description = ET.SubElement(MyXMLRoot_RiskMatrix_Category,info.DescriptionTag)
					MyXMLRoot_RiskMatrix_Category_Description.text = pS(each_Category.HumanDescription)
					pass

				MyXMLRoot_RiskMatrix_SeverityDimensionIndex = ET.SubElement(MyXMLRoot_RiskMatrix, info.SeverityDimensionTag)
				MyXMLRoot_RiskMatrix_SeverityDimensionIndex.text = pS(str(each_RiskMatrix.SeverityDimensionIndex))

				# Dimension
				each_list_of_keys: core_classes.CategoryNameItem
				for each_list_of_keys in each_RiskMatrix.Keys:
					for inner_list in each_list_of_keys:
						MyXMLRoot_RiskMatrix_Dimension = ET.SubElement(MyXMLRoot_RiskMatrix, info.DimensionTag)

						# TODO J: what is the attribute
						"""
						MyXMLRoot_RiskMatrix_Dimension_Name = ET.SubElement(MyXMLRoot_RiskMatrix_Dimension, info.NameTag)
						MyXMLRoot_RiskMatrix_Dimension_Name.text = pS(inner_list.)

						MyXMLRoot_RiskMatrix_Dimension_Key = ET.SubElement(MyXMLRoot_RiskMatrix_Dimension, info.KeyTag)
						MyXMLRoot_RiskMatrix_Dimension_Key.text = pS(inner_list.)
						"""
						# ID
						# TODO J: cannot map Catergory ID

				# Value

				for each_value in each_RiskMatrix.Value:
					pass

				pass
			pass
		pass

	#Constants
	# J: TODO
	if len(Proj.Constants) > 0:
		# create outer XML tag
		MyXMLRoot_Constants = ET.SubElement(MyXMLRoot, info.ConstantsTag)

		for each_Constant in Proj.Constants:
			assert type(each_Constant) == core_classes.ConstantItem
			each_Constant: core_classes.ConstantItem
			MyXMLRoot_Constants_Constant = ET.SubElement(MyXMLRoot_Constants, info.ConstantTag)

			#ID
			MyXMLRoot_Constants_Constant_Id = ET.SubElement(MyXMLRoot_Constants_Constant, info.IDTag)
			MyXMLRoot_Constants_Constant_Id.text = each_Constant.ID

			#Name
			MyXMLRoot_Constants_Constant_Name = ET.SubElement(MyXMLRoot_Constants_Constant, info.NameTag)
			MyXMLRoot_Constants_Constant_Name.text = each_Constant.HumanName

			#ConstValue
			#MyXMLRoot_Constants_Constant_ConstValue = ET.SubElement(MyXMLRoot_Constants_Constant, info.ConstValueTag)
			#MyXMLRoot_Constants_Constant_ConstValue.text = each_Constant.


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

						#ID
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ID =  ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.IDTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ID.text = pS(str(each_FTEvent.ID))

						#IsIPL
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_IsIPL = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.IsIPLTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_IsIPL.text = pS(str(each_FTEvent.IsIPL))

						#EventType
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_EventType = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.EventTypeTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_EventType.text = pS(str(each_FTEvent.EventType))

						#NumberingID
						#TODO cannot map ID
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_Numbering = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.NumberingTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_Numbering.text = pS(str(each_FTEvent.NumberingID))

						#EventDescription
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_EventDescription = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.EventDescriptionTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_EventDescription.text = pS(str(each_FTEvent.EventDescription))

						#OldFreqValue
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_OldFreqValue = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.OldFreqValueTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_OldFreqValue.text = pS(each_FTEvent.OldFreqValue.XMLName)

						#OldProbValue
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_OldProbValue = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.OldProbValueTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_OldProbValue.text = pS(each_FTEvent.OldProbValue.XMLName)

						each_LastSelectedUnitPerQtyKind_Key: str
						for each_LastSelectedUnitPerQtyKind_Key in each_FTEvent.LastSelectedUnitPerQtyKind:
							# LastSelectedUnit
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.LastSelectedUnitTag)

							# QtyKind
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit_QtyKind = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit, info.QtyKindTag)
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit_QtyKind.text = pS(str(each_FTEvent.LastSelectedUnitPerQtyKind))

							#Unit
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit_Unit = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit, info.UnitTag)
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LastSelectedUnit_Unit.text = pS(str(each_FTEvent.LastSelectedUnitPerQtyKind.get(each_LastSelectedUnitPerQtyKind_Key)))

						#IsSIFFailureEventInRelevantOpmode
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_IsSIFFailureEventInRelevantOpmode = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent,info.IsSIFFailureEventInRelevantOpmodeTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_IsSIFFailureEventInRelevantOpmode.text = pS(str(each_FTEvent.IsSIFFailureEventInRelevantOpMode))

						#RiskReceptors
						if len(each_FTEvent.ApplicableRiskReceptors) > 0:
							'''
							tempRiskReceptorList = []
							for each_RiskReceptor in each_FTEvent.ApplicableRiskReceptors:
								tempRiskReceptorList.append(each_RiskReceptor.ID)
							'''
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_RiskReceptors = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.RiskReceptorsTag)
							each_RiskReceptor: core_classes.RiskReceptorItem
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_RiskReceptors.text = pS(','.join(list(map(lambda each_RiskReceptor: each_RiskReceptor.ID, each_FTEvent.ApplicableRiskReceptors))))

						#BackgColour
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_BackgColour = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.BackgColourTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_BackgColour.text = pS(str(each_FTEvent.BackgColour))

						#EventDescriptionComments
						if len(each_FTEvent.EventDescriptionComments) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_EventDescriptionComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.EventDescriptionCommentsTag)
							# J:since AssociatedTextItem does not have an ID, match core_classes.Comment instead
							each_EventDescriptionComment: core_classes.Comment
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_EventDescriptionComments.text = pS(','.join(list(map(lambda each_EventDescriptionComment: each_EventDescriptionComment.ID, each_FTEvent.EventDescriptionComments))))

						#ValueComments
						if len(each_FTEvent.ValueComments) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ValueComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.ValueCommentsTag)
							# J:since AssociatedTextItem does not have an ID, match core_classes.Comment instead
							each_ValueComment: core_classes.Comment
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ValueComments.text = pS(','.join(list(map(lambda each_ValueComment: each_ValueComment.ID, each_FTEvent.ValueComments))))

						#ShowDescriptionComments
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ShowDescriptionComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.ShowDescriptionCommentsTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ShowDescriptionComments.text = pS(str(each_FTEvent.ShowValueComments))

						#ShowValueComments
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ShowValueComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.ShowValueCommentsTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ShowValueComments.text = pS(str(each_FTEvent.ShowValueComments))

						#ConnectTo
						if len(each_FTEvent.ConnectTo) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ConnectTo = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.ConnectToTag)
							each_FTEvent.ConnectTo: faulttree.FTEventInCore
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_ConnectTo.text = pS(','.join(list(map(lambda each_FTEvent: each_FTEvent.ID, each_FTEvent.ConnectTo))))

						#LinkedFrom
						#TODO J: what is the type of LinkedFrom item?
						if len(each_FTEvent.LinkedFrom) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LinkedFrom = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent, info.LinkedFromTag)
							each_LinkedFromItem: faulttree.FTEventInCore.LinkedFrom
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTEvent_LinkedFrom.text = pS(','.join(list(map(lambda each_FTEvent: each_FTEvent.ID, each_FTEvent.ConnectTo))))

					if type(each_FTEvent) == faulttree.FTGateItemInCore:
						#FTGate

						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTGateTag)

						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ID = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate, info.IDTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ID.text = pS(each_FTEvent.ID)

						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_GateDescription = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate, info.GateDescriptionTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_GateDescription.text = pS(str(each_FTEvent.GateDescription))

						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ShowDescriptionComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate, info.ShowDescriptionCommentsTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ShowDescriptionComments.text = pS(str(each_FTEvent.ShowDescriptionComments))

						if len(each_FTEvent.ActionItems) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ActionItems = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate, info.ActionItemsTag)
							# J:since AssociatedTextItem does not have an ID, match core_classes.Comment instead
							each_ActionItem: core_classes.Comment
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ActionItems.text = pS(','.join(list(map(lambda each_ActionItem: each_ActionItem.ID, each_FTEvent.ActionItems))))

						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ShowActionItems = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate, info.ShowActionItemsTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ShowActionItems.text = pS(str(each_FTEvent.ShowActionItems))

					if type(each_FTEvent) == faulttree.FTConnectorItemInCore:
						#TODO J: In Out should be determined by flag Out: faulttree.FTConnectorItemInCore.Out?

						each_FTEvent: faulttree.FTConnectorItemInCore
						if (each_FTEvent.Out):
							# FTConnectorOut
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTConnectorOutTag)
						else:
							# FTConnectorIn
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column, info.FTConnectorInTag)

						# ID
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ID = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.IDTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ID.text = pS(str(each_FTEvent.ID))

						# ConnectorDescription
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ConnectorDescription = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.ConnectorDescriptionTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ConnectorDescription.text = pS(str(each_FTEvent.ConnectorDescription))

						# ConnectorDescriptionComments
						if len(each_FTEvent.ConnectorDescriptionComments) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ConnectorDescriptionComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector,info.ConnectorDescriptionCommentsTag)
							# J:since AssociatedTextItem does not have an ID, match core_classes.Comment instead
							each_ConnectorDescriptionComment: core_classes.Comment
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTGate_ActionItems.text = pS(','.join(list(map(lambda each_ConnectorDescriptionComment: each_ConnectorDescriptionComment.ID,each_FTEvent.ConnectorDescriptionComments))))

						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ShowDescriptionComments = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.ShowDescriptionCommentsTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ShowDescriptionComments.text = pS(str(each_FTEvent.ShowDescriptionComments))

						# BackgColour
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_BackgColour = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.BackgColourTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_BackgColour.text = pS(str(each_FTEvent.BackgColour))

						if(each_FTEvent.Out):

							pass

						else:
							#RelatedConnector
							if each_FTEvent.RelatedCX != None:
								each_FTEvent.RelatedCX: faulttree.FTConnectorItemInCore
								MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_RelatedConnector = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.RelatedConnectorTag)
								MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_RelatedConnector.text = pS(each_FTEvent.RelatedCX.ID)

							#ConnectTo
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ConnectTo = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.ConnectToTag)
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_ConnectTo.text = pS(str(each_FTEvent))

						#Numbering
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnectorIn_Numbering = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnectorIn, info.NumberingTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnectorIn_Numbering.text = pS(str(each_FTEvent))

						#Style
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_Style = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.StyleTag)
						MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_Style.text = pS(str(each_FTEvent.Style))

						#RiskReceptors
						if len(each_FTEvent.ApplicableRiskReceptors) > 0:
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_RiskReceptors = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector, info.RiskReceptorsTag)
							each_RiskReceptor: core_classes.RiskReceptorItem
							MyXMLRoot_FaultTrees_FaultTree_Columns_Column_FTConnector_RiskReceptors.text = pS(','.join(list(map(lambda each_RiskReceptor: each_RiskReceptor.ID,each_FTEvent.ApplicableRiskReceptors))))

			#TolRiskModel
			MyXMLRoot_FaultTrees_FaultTree_TolRiskModel = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.TolRiskModelTag)
			each_FaultTree.MyTolRiskModel: core_classes.TolRiskModel
			MyXMLRoot_FaultTrees_FaultTree_TolRiskModel = pS(each_FaultTree.MyTolRiskModel.ID)

			#Severity
			MyXMLRoot_FaultTrees_FaultTree_Severity = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.SeverityTag)

			each_list_of_keys: core_classes.RiskReceptorItem
			for each_list_of_keys in each_FaultTree.Severity:
				# RR
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Severity, info.RRTag)
				# Name
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_Name = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Severity_RR, info.NameTag)
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_Name.text = pS(each_list_of_keys.XMLName)
				# SeverityValue
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_SeverityValue = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_Severity_RR, info.SeverityValueTag)
				MyXMLRoot_FaultTrees_FaultTree_Severity_RR_SeverityValue.text = pS(each_FaultTree.Severity.get(each_list_of_keys))

				pass

			#TolFreq
			#TODO
			MyXMLRoot_FaultTrees_FaultTree_TolFreq = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.TolFreqTag)
			MyXMLRoot_FaultTrees_FaultTree_TolFreq.text = pS(str(each_FaultTree.TolFreq))

			#RRGrouping
			MyXMLRoot_FaultTrees_FaultTree_RRGrouping = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.RRGroupingTag)
			MyXMLRoot_FaultTrees_FaultTree_RRGrouping.text = pS(each_FaultTree.RRGroupingOption)

			if len(each_FaultTree.CollapseGroups) > 0:
				# CollapseGroups
				MyXMLRoot_FaultTrees_FaultTree_CollapseGroups = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree,info.CollapseGroupsTag)
				for each_CollapseGroup in CollapseGroups:
					assert type(each_CollapseGroup) == faulttree.FTCollapseGroupInCore
					# CollapseGroup
					each_CollapseGroup: faulttree.FTCollapseGroupInCore
					MyXMLRoot_FaultTrees_FaultTree_CollapseGroup = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree_CollapseGroups, info.CollapseGroupTag)
					MyXMLRoot_FaultTrees_FaultTree_CollapseGroup.text = pS(str(each_CollapseGroup.ID))

			#ModelGate
			if each_FaultTree.ModelGate != None:
				MyXMLRoot_FaultTrees_FaultTree_ModelGate = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.ModelGateTag)
				each_FaultTree.ModelGate: faulttree.FTGateItemInCore
				MyXMLRoot_FaultTrees_FaultTree_ModelGate.text = pS(str(each_FaultTree.ModelGate.ID))

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

# Timer decorator - Start
# Author: Jack Leung
import time
def timer(func):
    def runFunction(*args, **kwargs):
        beginTime = time.time()
        print("Function {0} is called.".format(func.__name__))
        func(*args,**kwargs)
        endTime = time.time() - beginTime
        #TODO: cannot show proper function name
        print("Function {0} has run for {1} seconds.".format(func.__name__, endTime))
    return runFunction
# Timer decorator - End

""" ----------TESTING AREA----------]"""  

"""[----------RUN MAIN PROGRAM---------- """
@timer
def main():
	projects.runUnitTest()
	pass

if __name__ == '__main__':
	main()
""" ----------RUN MAIN PROGRAM----------]"""  
