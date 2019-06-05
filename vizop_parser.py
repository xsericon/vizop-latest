"""
Name: vizop_Parser
Last Modified: 20190605
Python version: 3.6.3
"""

"""[----------TEMPLATE---------- """
""" ----------TEMPLATE----------]""" 

"""[----------IMPORT---------- """
""""""
import xml.etree.ElementTree as ET
from lxml import etree as lxmletree
import string
import inspect
from enum import Enum
import projects, core_classes
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

def getNumberOfInstance(input_class):
	#get the number of instance for a Class by using garbage collector
	import gc
	return ('Number of {} in memory:{}'.format(input_class,len(list(filter(lambda x: isinstance(x, input_class), gc.get_objects())))))

def autoGenerateTagID():
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

	#ShortTitle
	if Proj.ShortTitle != '':
		MyXMLRoot_ShortTitle = ET.SubElement(MyXMLRoot, 'ShortTitle')
		MyXMLRoot_ShortTitle.text = pS(str(Proj.ShortTitle))

	#ProjNumber
	if Proj.ProjNumber != '':
		MyXMLRoot_ProjNumber = ET.SubElement(MyXMLRoot, 'ProjNumber')
		MyXMLRoot_ProjNumber.text = pS(str(Proj.ProjNumber))

	#Description
	if Proj.Description != '':
		MyXMLRoot_Description = ET.SubElement(MyXMLRoot, 'Description')
		MyXMLRoot_Description.text = pS(str(Proj.Description))

	#EditNumber
	if Proj.EditNumber != '':
		MyXMLRoot_EditNumber = ET.SubElement(MyXMLRoot, 'EditNumber')
		MyXMLRoot_EditNumber.text = pS(str(Proj.EditNumber))

	#TeamMembers
	if len(Proj.TeamMembers) > 0 :
		MyXMLRoot_TeamMembers = ET.SubElement(MyXMLRoot, 'TeamMembers')

		#TeamMember
		each_teamMember: core_classes.TeamMember
		for each_teamMember in Proj.TeamMembers:
			MyXMLRoot_TeamMembers_TeamMember = ET.SubElement(MyXMLRoot_TeamMembers, 'TeamMember')
			assert type(each_teamMember) == core_classes.TeamMember

			#<ID [ID int as str] />
			MyXMLRoot_TeamMembers_TeamMember_ID = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'ID')
			MyXMLRoot_TeamMembers_TeamMember_ID.text =  pS(str(each_teamMember.iD))

			#<Name [Name as str] />
			MyXMLRoot_TeamMembers_TeamMember_Name = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'Name')
			MyXMLRoot_TeamMembers_TeamMember_Name.text = pS(each_teamMember.name)

			#<Role [Role as str] />
			MyXMLRoot_TeamMembers_TeamMember_Role = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'Role')
			MyXMLRoot_TeamMembers_TeamMember_Role.text = pS(each_teamMember.role)

			#< Affiliation[Affiliation as str] / >
			MyXMLRoot_TeamMembers_TeamMember_Affiliation = ET.SubElement(MyXMLRoot_TeamMembers_TeamMember, 'Affiliation')
			MyXMLRoot_TeamMembers_TeamMember_Affiliation.text = pS(each_teamMember.affiliation)

	#Process Units
	if len(Proj.ProcessUnits) > 0:
		MyXMLRoot_ProcessUnits = ET.SubElement(MyXMLRoot, 'ProcessUnits')

		for each_ProcessUnit in Proj.ProcessUnits:
			MyXMLRoot_ProcessUnits_ProcessUnit = ET.SubElement(MyXMLRoot_ProcessUnits, 'ProcessUnit')
			assert type(each_ProcessUnit) == projects.ProcessUnit

			# <ID [ID int as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_ID = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'ID')
			MyXMLRoot_ProcessUnits_ProcessUnit_ID.text = pS(str(each_ProcessUnit.ID))

			#<UnitNumber [UnitNumber as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'UnitNumber')
			MyXMLRoot_ProcessUnits_ProcessUnit_UnitNumber.text = pS(str(each_ProcessUnit.UnitNumber))

			#<ShortName [ShortName as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_ShortName = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'ShortName')
			MyXMLRoot_ProcessUnits_ProcessUnit_ShortName.text = pS(str(each_ProcessUnit.ShortName))

			#<LongName [LongName as str] />
			MyXMLRoot_ProcessUnits_ProcessUnit_LongName = ET.SubElement(MyXMLRoot_ProcessUnits_ProcessUnit, 'LongName')
			MyXMLRoot_ProcessUnits_ProcessUnit_LongName.text = pS(str(each_ProcessUnit.LongName))

	#Risk Receptors
	if len(Proj.RiskReceptors) > 0:
		MyXMLRoot_RiskReceptors = ET.SubElement(MyXMLRoot, 'RiskReceptors')

		for each_RiskReceptor in Proj.RiskReceptors:
			print(type(each_RiskReceptor))
			assert type(each_RiskReceptor) == core_classes.RiskReceptorItem
			MyXMLRoot_RiskReceptors_RiskReceptor = ET.SubElement(MyXMLRoot_RiskReceptors, 'RiskReceptor')

			# <ID [ID int as str] />
			MyXMLRoot_RiskReceptors_RiskReceptor_ID = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, 'ID')
			MyXMLRoot_RiskReceptors_RiskReceptor_ID.text = pS(str(each_RiskReceptor.ID))

			#<Name [HumanName as str] />
			MyXMLRoot_RiskReceptors_RiskReceptor_HumanName = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, 'Name')
			MyXMLRoot_RiskReceptors_RiskReceptor_HumanName.text = pS(each_RiskReceptor.HumanName)




	# later, add more code here to write all PHA objects into the XML tree
	# write the XML file
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
