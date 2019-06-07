"""
Name: vizop_Parser
Last Modified: 20190607
Python version: 3.6.3
"""

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
import projects, core_classes, faulttree
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
		MyXMLRoot_ShortTitle = ET.SubElement(MyXMLRoot, 'ShortTitle')
		MyXMLRoot_ShortTitle.text = pS(str(Proj.ShortTitle))

	# ProjNumber
	if Proj.ProjNumber != '':
		MyXMLRoot_ProjNumber = ET.SubElement(MyXMLRoot, 'ProjNumber')
		MyXMLRoot_ProjNumber.text = pS(str(Proj.ProjNumber))

	# Description
	if Proj.Description != '':
		MyXMLRoot_Description = ET.SubElement(MyXMLRoot, 'Description')
		MyXMLRoot_Description.text = pS(str(Proj.Description))

	# EditNumber
	if Proj.EditNumber != '':
		MyXMLRoot_EditNumber = ET.SubElement(MyXMLRoot, 'EditNumber')
		MyXMLRoot_EditNumber.text = pS(str(Proj.EditNumber))

	# TeamMembers
	if len(Proj.TeamMembers) > 0 :
		# create outer XML tag
		MyXMLRoot_TeamMembers = ET.SubElement(MyXMLRoot, 'TeamMembers')

		# TeamMember
		each_teamMember: core_classes.TeamMember
		for each_teamMember in Proj.TeamMembers:
			MyXMLRoot_TeamMembers_TeamMember = ET.SubElement(MyXMLRoot_TeamMembers, 'TeamMember')
			assert type(each_teamMember) == core_classes.TeamMember

			# <ID [ID int as str] />
			MyXMLRoot_TeamMembers_TeamMember_ID = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'ID')
			MyXMLRoot_TeamMembers_TeamMember_ID.text =  pS(str(each_teamMember.iD))

			# <Name [Name as str] />
			MyXMLRoot_TeamMembers_TeamMember_Name = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'Name')
			MyXMLRoot_TeamMembers_TeamMember_Name.text = pS(each_teamMember.name)

			# <Role [Role as str] />
			MyXMLRoot_TeamMembers_TeamMember_Role = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'Role')
			MyXMLRoot_TeamMembers_TeamMember_Role.text = pS(each_teamMember.role)

			# < Affiliation[Affiliation as str] / >
			MyXMLRoot_TeamMembers_TeamMember_Affiliation = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'Affiliation')
			MyXMLRoot_TeamMembers_TeamMember_Affiliation.text = pS(each_teamMember.affiliation)

	#Process Units
	if len(Proj.ProcessUnits) > 0:
		# create outer XML tag
		MyXMLRoot_ProcessUnits = ET.SubElement(MyXMLRoot, 'ProcessUnits')

		for each_ProcessUnit in Proj.ProcessUnits:
			MyXMLRoot_ProcessUnits_ProcessUnit = ET.SubElement(MyXMLRoot_ProcessUnits, 'ProcessUnit')
			assert type(each_ProcessUnit) == projects.ProcessUnit

			# <ID [ID int as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_ID = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'ID')
			MyXMLRoot_ProcessUnits_ProcessUnit_ID.text = pS(str(each_ProcessUnit.ID))

			# <UnitNumber [UnitNumber as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'UnitNumber')
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber.text = pS(str(each_ProcessUnit.UnitNumber))

			# <ShortName [ShortName as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_ShortName = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'ShortName')
			MyXMLRoot_ProcessUnits_ProcessUnit_ShortName.text = pS(str(each_ProcessUnit.ShortName))

			# <LongName [LongName as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_LongName = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'LongName')
			MyXMLRoot_ProcessUnits_ProcessUnit_LongName.text = pS(str(each_ProcessUnit.LongName))

	#Risk Receptors
	if len(Proj.RiskReceptors) > 0:
		# create outer XML tag
		MyXMLRoot_RiskReceptors = ET.SubElement(MyXMLRoot, 'RiskReceptors')

		for each_RiskReceptor in Proj.RiskReceptors:
			assert type(each_RiskReceptor) == core_classes.RiskReceptorItem
			MyXMLRoot_RiskReceptors_RiskReceptor = ET.SubElement(MyXMLRoot_RiskReceptors, 'RiskReceptor')

			# <ID [ID int as str] />
			MyXMLRoot_RiskReceptors_RiskReceptor_ID = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, 'ID')
			MyXMLRoot_RiskReceptors_RiskReceptor_ID.text = pS(str(each_RiskReceptor.ID))

			#<Name [HumanName as str] />
			MyXMLRoot_RiskReceptors_RiskReceptor_HumanName = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, 'Name')
			MyXMLRoot_RiskReceptors_RiskReceptor_HumanName.text = pS(each_RiskReceptor.HumanName)

	# Numbering Systems
	if len(Proj.NumberSystems) > 0:
		# create outer XML tag
		MyXMLRoot_NumberSystems = ET.SubElement(MyXMLRoot, 'NumberSystems')

		for each_NumberSystem in Proj.NumberSystems:
			assert type(each_NumberSystem) == core_classes.SerialNumberChunkItem
			MyXMLRoot_NumberSystems_NumberSystem = ET.SubElement(MyXMLRoot_NumberSystems, 'NumberSystem')

			#FieldWidth
			MyXMLRoot_NumberSystems_NumberSystem_FieldWidth = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, 'FieldWidth')
			MyXMLRoot_NumberSystems_NumberSystem_FieldWidth.text = pS(str(each_NumberSystem.FieldWidth))

			#PadChar
			MyXMLRoot_NumberSystems_NumberSystem_PadChar = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, 'PadChar')
			MyXMLRoot_NumberSystems_NumberSystem_PadChar.text = pS(str(each_NumberSystem.PadChar))

			#StartSequenceAt
			MyXMLRoot_NumberSystems_NumberSystem_StartSequenceAt = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, 'StartSequenceAt')
			MyXMLRoot_NumberSystems_NumberSystem_StartSequenceAt.text  = pS(str(each_NumberSystem.StartSequenceAt))

			#SkipTo
			if each_NumberSystem.SkipTo != None:
				MyXMLRoot_NumberSystems_NumberSystem_SkipTo = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, 'SkipTo')
				MyXMLRoot_NumberSystems_NumberSystem_SkipTo.text = pS(str(each_NumberSystem.SkipTo))

			#GapBefore
			MyXMLRoot_NumberSystems_NumberSystem_GapBefore = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, 'GapBefore')
			MyXMLRoot_NumberSystems_NumberSystem_GapBefore.text = pS(str(each_NumberSystem.GapBefore))

			#IncludeInNumbering
			MyXMLRoot_NumberSystems_NumberSystem_IncludeInNumbering = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem, 'IncludeInNumbering')
			MyXMLRoot_NumberSystems_NumberSystem_IncludeInNumbering.text = pS(str(each_NumberSystem.IncludeInNumbering))

			#NoValue
			MyXMLRoot_NumberSystems_NumberSystem_NoValue = ET.SubElement(MyXMLRoot_NumberSystems_NumberSystem,'NoValue')
			MyXMLRoot_NumberSystems_NumberSystem_NoValue.text = pS(each_NumberSystem.NoValue)

	# Risk Matrix
	if len(Proj.RiskMatrices) > 0:
		# create outer XML tag
		MyXMLRoot_RiskMatrices = ET.SubElement(MyXMLRoot, 'RiskMatrices')

		# LookupTableItem
		for each_RiskMatrix in Proj.RiskMatrices:
			assert type(each_RiskMatrix) == core_classes.LookupTableItem
			MyXMLRoot_RiskMatrices_RiskMatrix = ET.SubElement(MyXMLRoot_RiskMatrices, 'RiskMatrix')

			# <Category>
			# J: TODO: could not map Category

			# <SeverityDimension [SeverityDimensionIndex int as str] />
			if each_RiskMatrix.SeverityDimensionIndex != None:
				MyXMLRoot_RiskMatrices_RiskMatrix_SeverityDimension = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix, 'SeverityDimension')
				MyXMLRoot_RiskMatrices_RiskMatrix_SeverityDimension.text = each_RiskMatrix.SeverityDimensionIndex

			if len(each_RiskMatrix.DimensionUnits) > 0:
				MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix,'Dimensions')

				for each_DimensionUnit in each_RiskMatrix.DimensionUnits:
					assert type(each_DimensionUnit) == core_classes.UnitItem
					MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits, 'Dimension')

					#Name
					MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit_Name = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit, 'Name')
					MyXMLRoot_RiskMatrices_RiskMatrix_DimensionUnits_DimensionUnit_Name.text = pS(each_DimensionUnit.HumanName)

			#Key
			# J: TODO
			if len(each_RiskMatrix.Keys) > 0:
				MyXMLRoot_RiskMatrices_RiskMatrix_Key = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix, 'Key')
				MyXMLRoot_RiskMatrices_RiskMatrix_Key.text = ''

			#Entry
			if len(each_RiskMatrix.Values) > 0:
				MyXMLRoot_RiskMatrices_RiskMatrix_Entries = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix, 'Entries')

				for each_Value in each_RiskMatrix.Values:
					MyXMLRoot_RiskMatrices_RiskMatrix_Entries_Entry = ET.SubElement(MyXMLRoot_RiskMatrices_RiskMatrix_Entries, 'Entry')
					MyXMLRoot_RiskMatrices_RiskMatrix_Entries_Entry.text = pS(str(each_Value))

	#Constants
	# J: TODO
	if len(Proj.Constants) > 0:
		# create outer XML tag
		MyXMLRoot_Constants = ET.SubElement(MyXMLRoot, 'Constants')

		for each_Constant in Proj.Constants:
			assert type(each_Constant) == core_classes.ConstantItem
			MyXMLRoot_Constants_Constant = ET.SubElement(MyXMLRoot_Constants, 'Constant')

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
		MyXMLRoot_FaultTrees = ET.SubElement(MyXMLRoot, 'FaultTrees')

		for each_FaultTree in Proj.FaultTrees:
			assert type(each_FaultTree) == faulttree.FTObjectInCore
			MyXMLRoot_FaultTrees_FaultTree = ET.SubElement(MyXMLRoot_FaultTrees, 'FaultTree')

			# J: TODO
			#GateStyle= (style of logic gates used throughout this FT)
			#if faulttree.FTGateItemInCore != None:
				#MyXMLRoot_FaultTrees_FaultTree.set('GateStyle', faulttree.FTGateItemInCore)

			# J: TODO
			#Attribs: OpMode= (SIF operating mode)
			#if faulttree.OpModeType.XMLName != None:
				#MyXMLRoot_FaultTrees_FaultTree.set('OpMode', pS(faulttree.OpModeType.XMLName))

			#ID
			MyXMLRoot_FaultTrees_FaultTree_Id = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, 'Id')
			MyXMLRoot_FaultTrees_FaultTree_Id.text = pS(str(each_FaultTree.ID))

			#J: TODO
			#Header Data C
			#MyXMLRoot_FaultTrees_FaultTree_HeaderData = ET.SubElement()
			#MyXMLRoot_FaultTrees_FaultTree_HeaderData.text = pS(str())

			# J: TODO
			#FTColumn

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
# @Jack: TODO XML tree and rules work in progress
XMLTreeFormat = """
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
			<xsd:element name="VizopProject">
			<xsd:complexType>
			<xsd:sequence>
				<xsd:element name="VizopVersion" type="xsd:integer" minOccurs="0"/>
				<xsd:element name="ProjectName" type="xsd:string" minOccurs="0"/>
				<xsd:element name="Description" type="xsd:string" minOccurs="0"/>
				<xsd:element name="TeamMembers" minOccurs="0">
				<xsd:complexType>
				<xsd:sequence>
						<xsd:element name="TeamMember"  minOccurs="0">
						<xsd:complexType>
						<xsd:sequence>
							<xsd:element name="ID" type="xsd:integer" />
							<xsd:element name="Name" type="xsd:string" />
							<xsd:element name="Role" type="xsd:string"/>
							<xsd:element name="Affiliation" type="xsd:string" />
						</xsd:sequence>
						</xsd:complexType>
						</xsd:element>
				</xsd:sequence>
				</xsd:complexType>
				</xsd:element>
				<xsd:element name="EditNumber" type="xsd:string" minOccurs="0"/>
				<xsd:element name="ShortTitle" type="xsd:string" minOccurs="0"/>
				<xsd:element name="ProjNumber" type="xsd:string" minOccurs="0"/>	
				<xsd:element name="ProjectComponent" minOccurs="0">
				<xsd:complexType>
				<xsd:sequence>

					<xsd:element name="ProcessUnit">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:string"/>
						<xsd:element name="UnitNumber" type="xsd:integer"/>
						<xsd:element name="ShortName" type="xsd:string"/>
						<xsd:element name="LongName" type="xsd:string"/>
						<xsd:element name="PHA" type="xsd:string"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="RecommendationReport" type="xsd:string" minOccurs="0"/>

					<xsd:element name="RiskReceptor">
						<xsd:complexType>
						<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
						<xsd:element name="Name" type="xsd:string"/>
						</xsd:sequence>
						</xsd:complexType>
					</xsd:element>

					<xsd:element name="NumberingSystem">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
						<xsd:element name="Chunk">
						<xsd:complexType>
						<xsd:sequence>
							<xsd:element name="Type" type="xsd:string">/
							<xsd:element name="Value" type="xsd:string"/>
							<xsd:element name="ID" type="xsd:string"/>
							<xsd:element name="Fieldwidth" type="xsd:string"/>
							<xsd:element name="PadChar" type="xsd:string"/>
							<xsd:element name="StartAt" type="xsd:string"/>
							<xsd:element name="SkipTo" type="xsd:string"/>
							<xsd:element name="GapBefore" type="xsd:string"/>
							<xsd:element name="Include" type="xsd:string"/>
							<xsd:element name="Include" type="xsd:string"/>
							<xsd:element name="NoValue" type="xsd:string"/>
						</xsd:sequence>
						</xsd:complexType>
						</xsd:element>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="RiskMatrix">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="Category">
						<xsd:complexType>
						<xsd:sequence>
							<xsd:element name="ID" type="xsd:string"/>
							<xsd:element name="Name" type="xsd:string"/>
							<xsd:element name="Description" type="xsd:integer"/>
						</xsd:sequence>
						</xsd:complexType>
						</xsd:element>
						<xsd:element name="SeverityDimension">
						<xsd:complexType>
						<xsd:sequence>
							<xsd:element name="Dimension"/>
							<xsd:complexType>
							<xsd:sequence>
								<xsd:element name="Name" type="xsd:string"/>
								<xsd:element name="Key" type="xsd:string"/>
							</xsd:complexType>
							</xsd:element>
						</xsd:sequence>
						</xsd:complexType>
						</xsd:element>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="FaultTree">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="HeaderData" type="xsd:string"/>
						<xsd:element name="FTColumn">
						<xsd:complexType>
						<xsd:sequence>

							<xsd:element name="FTElements">
							<xsd:complexType>
							<xsd:sequence>

								<xsd:element name="FTEvent">
								<xsd:complexType>
								<xsd:sequence>

									<xsd:element name="Value" type="xsd:string"/>
									<xsd:element name="ActionItem" type="xsd:string"/>
									<xsd:element name="CollapseGroup" type="xsd:integer"/>
									<xsd:element name="ViewMode" type="xsd:integer"/>

								</xsd:sequence>
								</xsd:complexType>
								</xsd:element>

							</xsd:sequence>
							</xsd:complexType>

						</xsd:sequence>
						</xsd:complexType>
						</xsd:element>

					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="PHA">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
						<xsd:element name="Node" type="xsd:string"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="PHA">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
						<xsd:element name="Node" type="xsd:string"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="PHA">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
						<xsd:element name="Node" type="xsd:string"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="Node">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="Cause">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="Alarm">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="Constant">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
						<xsd:element name="Name" type="xsd:integer"/>
						<xsd:element name="LinkFrom" type="xsd:integer"/>
						<xsd:element name="ConstValue" type="xsd:integer"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

					<xsd:element name="Bookmark">
					<xsd:complexType>
					<xsd:sequence>
						<xsd:element name="ID" type="xsd:integer"/>
					</xsd:sequence>
					</xsd:complexType>
					</xsd:element>

				</xsd:sequence>
				</xsd:complexType>
				</xsd:element>
			</xsd:sequence>
			</xsd:complexType>
			</xsd:element>
		 </xsd:schema>
"""

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
