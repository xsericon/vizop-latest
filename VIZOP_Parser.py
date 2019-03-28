"""
Name: VIZOP_Parser
Version: 0.3
Last Modified: 20190328
Python version: 3.6.3
"""

"""[----------TEMPLATE---------- """
""" ----------TEMPLATE----------]""" 

"""[----------IMPORT---------- """
""""""
import xml.etree.ElementTree as ET
import string
""" ----------IMPORT----------]""" 
class Chars:
	VALID_CHARS = "!#$%()*+,-.:;=?@[]^_`{|}~ %s%s" + string.ascii_letters + string.digits

class Node():
	"""
	Element IDs are unique for all elements (including comments) across entire project.
	"""
	#current node id
	cur_node_id = None

	NODE_ID_NAME = 'id'
	NODE_KIND_NAME = 'kind'

	NODE_TYPES = ('Test','Name','Number','Value','Bookmark','Comment','Action_Item','PHA_Object','Process_Unit')

	NODE_VALUE_ATTR_UNIT_NAME = 'unit'
	NODE_VALUE_ATTR_VALUEKIND_NAME = 'value_kind'
	
	NODE_NUMBERINGSYSTEM_TYPE = ('str','Parent','Serial')
	
	"""
	#change to attribute
	a <Unit> tag, whose value is the engineering unit of the numerical value. Valid values are: None, Prob (indicating probability), %, /yr, /hr, FIT, hr, day, wk, month, yr. All are non-case sensitive. If the <Unit> tag is absent, a default unit is taken (varies per parameter).
	"""
	NODE_NUMERICAL_UNIT_TYPE = ('None','Prob','%','/yr','/hr','FIT','hr','day','wk','month','yr')
	
	"""
	#change to attribute
	a <Kind> tag, whose value indicates the kind of the number. Valid values are: Manual (value entered by user), Constant (value fixed to a defined constant), Calc (value calculated according to a formula), Lookup (value looked up in a 2D matrix), Category (one of a list of values defined separately), Linked (value fixed to that of another parameter) (all are non-case sensitive). Defaults to Manual. Currently only Manual is implemented, and other kinds will give undefined results.
	"""
	NODE_NUMERICAL_VALUEKIND = ('Manual','Constant','Calc','Lookup','Category','Linked')
	
	NODE_STATUS = ('Deleted',)
	
	"""
	Boolean tag values are written as True or False. When reading the file, any of the following is considered as True: True, Yes, Y, 1 (not case-sensitive). Any other value is considered as False. If the Boolean value is to be defined as “unset”, the tag should be omitted.
	"""
	NODE_BOOLEAN_TAG_TRUE = ('True', 'Yes', 'Y', '1')
	#Other value would be set as FALSE
	NODE_BOOLEAN_TAG_UNSET = ('unset')
	
	"""
	NODE_DATA_TYPES
	"""
	NODE_DATA_TYPES = ('str', 'text', 'int')
	
	NODE_KINDS = ('User','Constant','Lookup','Category','Copied','CopiedFrom')
	
	def __init__(self, \
	#----------[Compulsory in creation----------
	ParentNodes, \
	ChildNodes, \
	node_type, \
	node_kind, \
	node_tag_name, \
	#----------Compulsory]----------
	#----------[Default/Optional in initialisation----------
	node_values = [], \
	node_attrs = {}, \
	node_bookmark = None, \
	node_comment = None, \
	LinkParentNodes = set([]), \
	LinkChildNodes = set([]), \
	VALUE_ONLY = False, \
	value_attrs = {}, \
	CAN_REPEAT = False, \
	CAN_BOOKMARK = False, \
	CAN_COMMENT = False, \
	CONTAIN_NUMERICAL_VALUES = False, \
	CAN_TAKE_ATTRIBUTE_STATUS = False, \
	IS_COMPULSORY = False):
	#----------Optional]----------
	
		"""
		Type test assertion
		"""
		assert type(ParentNodes) == set
		for ParentNode in ParentNodes:
			assert type(ParentNode) == Node
		assert type(ChildNodes) == set
		for ChildNode in ChildNodes:
			assert type(ChildNode) == Node

		assert type(node_type) == str
		assert node_type in Node.NODE_TYPES
		assert type(node_kind) == str
		assert node_kind in Node.NODE_KINDS
		assert type(node_tag_name) == str
		assert type(node_values) == list
		for node_value in node_values:
			assert type(node_value) == str
		
		if node_bookmark is not None:
			assert type(node_bookmark) == Bookmark
		if node_comment is not None:
			assert type(node_comment) == Comment
		
		assert type(node_attrs) == dict
		
		assert type(LinkParentNodes) == set
		for LinkParentNode in LinkParentNodes:
			assert type(LinkParentNode) == Node
		assert type(LinkChildNodes) == set
		for LinkChildNode in LinkChildNodes:
			assert type(LinkChildNode) == Node
			
		assert type(node_type) == str
		assert type(VALUE_ONLY) == bool 
		assert type(CAN_REPEAT) == bool
		assert type(CAN_BOOKMARK) == bool
		assert type(CAN_COMMENT) == bool
		assert type(CONTAIN_NUMERICAL_VALUES) == bool
		assert type(CAN_TAKE_ATTRIBUTE_STATUS) == bool
		assert type(IS_COMPULSORY) == bool

		"""  
		* indicates tags that contain values only, not other tags. (The * should not appear in the actual file.) 
		"""
		self.VALUE_ONLY = VALUE_ONLY
		
		"""
		% indicates tags that can be repeated. (If non-% tags are repeated, only the first instance in each level will be used.) (The % should not appear in the actual file.)
		"""
		self.CAN_REPEAT = CAN_REPEAT
		
		"""
		B indicates tags that can contain <Bookmark> tags. (The B should not appear in the actual file.)
		"""
		self.CAN_BOOKMARK = CAN_BOOKMARK
		
		"""
		C indicates tags that can contain <Comment> child tags. (The C should not appear in the actual file.) 
		"""
		self.CAN_COMMENT = CAN_COMMENT
		
		"""
		N indicates tags that contain numerical values. The value (real or integer) must come immediately after the tag, and before any child tags. The tag can optionally contain the following attr: Unit, ValueKind
		"""
		self.CONTAIN_NUMERICAL_VALUES = CONTAIN_NUMERICAL_VALUES
		
		"""
		U indicates tags that can take an attribute “Status” (for use by Save On The Fly). For example, <Node Status=Deleted>. The Status attribute is optional. Recognised values are detailed in the “Project open and save” specification. Unrecognised values of Status will be ignored (normally silently; a message can be output if we are in Verbose mode).
		"""
		self.CAN_TAKE_ATTRIBUTE_STATUS = CAN_TAKE_ATTRIBUTE_STATUS
		
		"""
		! indicates compulsory tags. If missing from the file, vizop can't open the project. All tags not marked ! can be omitted.
		"""
		self.IS_COMPULSORY = IS_COMPULSORY
		
		"""
		J: We use Pythonic way to write values of a class i.e. values are not encapsulated, can be called/changed directly even outside the Class
		For any Class methods that have special edition, create a new method. For example, connectNodes() - as connecting nodes need to be bi-lateral
		"""
		self.element_id = Node.cur_node_id

		self.ParentNodes = set([])
		for each_ParentNode in ParentNodes:
			if not each_ParentNode.VALUE_ONLY:
				Node.connectNodes(ParentNodeInput = each_ParentNode,ChildNodeInput = self)

		self.ChildNodes = set([])
		
		if not VALUE_ONLY:
			for each_ChildNode in ChildNodes:
				Node.connectNodes(ParentNodeInput = self, ChildNodeInput = each_ChildNode)

		self.node_type = node_type
		
		self.node_kind = node_kind

		self.node_tag_name = processString(node_tag_name, noSpace = True)
		
		if CAN_BOOKMARK:
			self.node_bookmark = node_bookmark
			pass
		
		if CAN_COMMENT:
			self.node_comment = node_comment
			pass
		
		self.node_values = []
		if len(node_values) != 0:
			if self.CAN_REPEAT:
				self.node_values = self.node_values + node_values
			else:
				self.node_values.append(processString(node_values[0]))
				assert len(self.node_values) == 1
		
		self.node_attrs = {Node.NODE_KIND_NAME:self.node_kind, Node.NODE_ID_NAME:str(self.element_id)}
		self.node_attrs.update(node_attrs)
		
		self.value_attrs = {}
		if self.CONTAIN_NUMERICAL_VALUES:
			# Currently only Manual is implemented
			value_attrs.update({NODE_VALUE_ATTR_UNIT_NAME:'None', NODE_VALUE_ATTR_VALUEKIND_NAME:'Manual'})
			pass

		self.LinkParentNodes = set([])
		for each_LinkParentNode in LinkParentNodes:
			Node.connectNodes(LinkParentNodeInput = each_LinkParentNode,LinkChildNodeInput = self)
		
		self.LinkChildNodes = set([])
		for each_LinkChildNode in LinkChildNodes:
			Node.connectNodes(LinkParentNodeInput = self,LinkChildNodeInput = each_LinkChildNode)
		
		Node.cur_node_id = Node.cur_node_id + 1

	"""
	J: overriding __repr__  for class string presentation 
	"""
	def __repr__(self):
		#J: to show relationship of a node and its address in memory
		return ("<{}>ParentNodes:{}, ChildNodes:{}, #{}, memory_address:{}</{}>".format(self.node_tag_name, \
		list(map(lambda x: '#'+str(x.element_id), self.ParentNodes)), list(map(lambda x: '#'+str(x.element_id), self.ChildNodes)), self.element_id, id(self), self.node_tag_name))
	
	"""
	J: We put special data change methods here
	"""
	def connectNodes(ParentNodeInput, ChildNodeInput):
		assert type(ParentNodeInput) == Node
		assert type(ChildNodeInput) == Node
	
		ParentNodeInput.ChildNodes.add(ChildNodeInput)
		ChildNodeInput.ParentNodes.add(ParentNodeInput)
		pass
		
	def connectLinkNodes(LinkParentNodeInput, LinkChildNodeInput):
		assert type(LinkParentNodeInput) == Node
		assert type(LinkChildNodeInput) == Node
	
		LinkParentNodeInput.LinkChildNodes.add(LinkChildNodeInput)
		LinkChildNodeInput.LinkParentNodes.add(LinkParentNodeInput)
		pass


class Bookmark():
	cur_bookmark_id = None
	def __init__(self, isBookmarked):
		assert type(isBookmarked) == bool
		self.id = Bookmark.cur_bookmark_id
		self.isBookmarked = isBookmarked
		Bookmark.cur_bookmark_id = Bookmark.cur_bookmark_id + 1
	
	def __repr__(self):
		return 'Bookmark_id:{}'.format(self.id)
	
class Comment():
	cur_comment_id = None
	def __init__(self, comment_content):
		assert type(comment_content) == str
		self.id = Comment.cur_comment_id
		Comment.cur_comment_id = Comment.cur_comment_id + 1
	
	def __repr__(self):
		return 'Comment_id:{}'.format(self.id)

def createNewProject():
	pass

def convertXmlToProject():
	#TO-DO
	tree = ET.parse('TestXML.xml')
	root = tree.getroot()
	ET.dump(tree)
	pass
	
def convertProjectToXml(Project):
	
	Root = ET.Element(Project.node_tag_name)
	MyXMLTree = ET.ElementTree(element=Root)

	iterateNode(Project, Root)
	
	try:
	#J: Write XML tree to actual file
		MyXMLTree.write("TestXML.xml", encoding="UTF-8", xml_declaration=True)
	
	#J: Display XML tree on screen
	#ET.dump(MyXMLTree)
	except:
		return False
	
	return True

def main():
	testCreateProject()
	convertXmlToProject()

	pass

"""[----------UTIL---------- """
def processString(inputString, trimString = True, filterForbiddenChar = True, noSpace = False):
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
		formattedString = ''.join(formattedString.split(' '))
	
	return formattedString
	
def isInType(StringInput, TypeInput):
	#check if input in type
	assert type(StringInput) == str
	assert type(TypeInput) in (set,list,tuple)
	LowerCaseList = list(map(lambda x: x.lower(),TypeInput))
	return StringInput.lower() in LowerCaseList

def getNumberOfInstance(input_class):
	#get the number of instance for a Class by using garbage collector
	import gc
	return ('Number of {} in memory:{}'.format(input_class,len(list(filter(lambda x: isinstance(x, input_class), gc.get_objects())))))

""" ----------UTIL----------]""" 
	
"""[----------TESTING AREA---------- """
def testCreateProject():
	#Initiate id of objects 
	Node.cur_node_id = 1
	Bookmark.cur_bookmark_id = 1
	Comment.cur_comment_id = 1
	
	Bookmark1 = Bookmark(isBookmarked = True)
	Comment1 = Comment('Comment test')
	
	#<Project>
	Project = Node(ParentNodes = set([]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'Project', node_values = ['VIZOP'])
		#<VizopProject>
	VizopProject = Node(ParentNodes = set([Project]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'VizopProject', node_values = [])
			#<VizopProject_Version>
	VizopProject_Version = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'VizopVersion', node_values = ['1.0'])
			#<VizopProject_ShortTitle>
	VizopProject_ShortTitle = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ShortTitle', node_values = ['V'])
			#<ProjectNumber>
	ProjectNumber = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectNumber', node_values = ['0001'])
			#<ProjectEditNumber>
	ProjectEditNumber = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'EditNumber', node_values = ['0001'])
			#<ProjectName>
	ProjectName = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'VizopVersion', node_values = ['1.0'])
			#<ProjectDescription>
	ProjectDescription = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectDescription', node_values = ['The purpose of this project is to...'], CAN_BOOKMARK = True, node_bookmark = Bookmark1)

			#<ProjectTeamMembers>
	ProjectTeamMembers = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMembers', node_values = [])
				#<ProjectTeamMember>
	ProjectTeamMember = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMember', node_values = [])
					#<ProjectTeamMemberID>
	ProjectTeamMemberID = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberID', node_values = ['1'])
					#<ProjectTeamMemberName>
	ProjectTeamMemberName = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberName', node_values = ['John'])
					#<ProjectTeamMemberRole>
	ProjectTeamMemberRole = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberRole', node_values = ['Team Lead'])
					#<ProjectTeamMemberAffiliation>
	ProjectTeamMemberAffiliation = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberAffiliation', node_values = ['Mary'])
					#<ProjectTeamMember>
	ProjectTeamMember = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMember', node_values = [])
					#<ProjectTeamMemberID>
	ProjectTeamMemberID = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberID', node_values = ['2'])
					#<ProjectTeamMemberName>
	ProjectTeamMemberName = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberName', node_values = ['Mary'])
					#<ProjectTeamMemberRole>
	ProjectTeamMemberRole = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberRole', node_values = ['Consultant'])
					#<ProjectTeamMemberAffiliation>
	ProjectTeamMemberAffiliation = Node(ParentNodes = set([ProjectTeamMembers]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ProjectTeamMemberAffiliation', node_values = ['John'])

			#<ProcessUnit>
	ProcessUnit = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Process_Unit', node_kind = 'User', node_tag_name = 'ProcessUnit', node_values = [])
				#<ProcessUnit_ID>
	ProcessUnit_ID = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Number', node_kind = 'User', node_tag_name = 'ID', node_values = ['0001'])
				#<ProcessUnit_UnitNumber>
	ProcessUnit_UnitNumber = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'UnitNumber', node_values = ['John'])
				#<ProcessUnit_ShortName>
	ProcessUnit_ShortName = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ShortName', node_values = ['UnitShortName'])
				#<ProcessUnit_LongName>
	ProcessUnit_LongName = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'LongName', node_values = ['UnitLongName'])
	
			#<RiskReceptor>
	RiskReceptor = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'Process_Unit', node_kind = 'User', node_tag_name = 'RiskReceptor', node_values = [])
				#<RiskReceptor_ID>
	RiskReceptor_ID = Node(ParentNodes = set([RiskReceptor]), ChildNodes = set([]), node_type = 'Number', node_kind = 'User', node_tag_name = 'ID', node_values = ['0001'])
				#<RiskReceptor_HumanName>
	RiskReceptor_HumanName = Node(ParentNodes = set([RiskReceptor]), ChildNodes = set([]), node_type = 'Number', node_kind = 'User', node_tag_name = 'HumanName', node_values = ['0001'])

			#<PHAObject>
	PHAObject = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'PHA_Object', node_kind = 'User', node_tag_name = 'PHAObject', node_values = [])
				#<FT>
	FT = Node(ParentNodes = set([PHAObject]), ChildNodes = set([]), node_type = 'PHA_Object', node_kind = 'User', node_tag_name = 'PHAObject')
				#<AlarmRationalization>
	AlarmRationalization = Node(ParentNodes = set([PHAObject]), ChildNodes = set([]), node_type = 'PHA_Object', node_kind = 'User', node_tag_name = 'PHAObject')
	
			#<NumberingSystem>
	NumberingSystem = Node(ParentNodes = set([VizopProject]), ChildNodes = set([]), node_type = 'PHA_Object', node_kind = 'User', node_tag_name = 'NumberingSystem', node_values = [])
				#<NumberingSystem_ID>
	NumberingSystem_ID = Node(ParentNodes = set([NumberingSystem]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'ID', node_values = [])
				#<Chunk>
	NumberingSystem_Chunk = Node(ParentNodes = set([NumberingSystem]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'Chunk', node_values = [])
					#<Type>
	NumberingSystem_Chunk_Type = Node(ParentNodes = set([NumberingSystem]), ChildNodes = set([]), node_type = 'Name', node_kind = 'User', node_tag_name = 'Type', node_values = ['str'])
						#<strValue>

	print ('getNumberOfInstance:{}'.format(getNumberOfInstance(Node)))
	print ('convertProjectToXml:{}'.format(convertProjectToXml(Project)))

def iterateNode(node, root):
	#iterate through all the nodes and sub-nodes to form an XML tree
	for each_ChildNode in node.ChildNodes:
		#create inner root for all sub elements (all child nodes)
		inner_root = ET.SubElement(root, each_ChildNode.node_tag_name)
		#create all XML attributes
		for each_key, each_value in each_ChildNode.node_attrs.items():
			inner_root.set(each_key, each_value)
		#bookmark
		if hasattr(each_ChildNode, 'node_bookmark'):
			inner_root_bookmark = ET.SubElement(inner_root, 'Bookmark')
			inner_root_bookmark.set('id', str(each_ChildNode.node_bookmark.id))
			inner_root_bookmark.text = str(each_ChildNode.node_bookmark.isBookmarked)
		#comment
		if hasattr(each_ChildNode, 'node_comment'):
			inner_root_comment = ET.SubElement(inner_root, Node.NODE_TYPES_COMMENT_NAME)
			inner_root_comment.set('id', str(each_ChildNode.node_comment.id))
			inner_root_comment.text = str(each_ChildNode.node_bookmark.comment_content)
		#create all values
		for each_node_values in each_ChildNode.node_values:
			inner_root_value = ET.SubElement(inner_root, 'Value')
			inner_root_value.text = each_node_values

		iterateNode(each_ChildNode, inner_root)
	return (root)
""" ----------TESTING AREA----------]"""  

"""[----------RUN MAIN PROGRAM---------- """
if __name__ == '__main__':
	main()
""" ----------RUN MAIN PROGRAM----------]"""  
