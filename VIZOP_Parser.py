"""
Name: VIZOP_Parser
Version: 0.4
Last Modified: 20190331
Python version: 3.6.3
"""

"""
Version: 0.4
	Applied Enum 
	Applied node rule in function createNode
	Create function ic
	Updated function convertXmlToProject
	Updated	function processString
	Updated function isInType

Version: 0.3
	Updated	function processString
	Updated	function isInType
"""

"""[----------TEMPLATE---------- """
""" ----------TEMPLATE----------]""" 

"""[----------IMPORT---------- """
""""""
import xml.etree.ElementTree as ET
import string
import inspect
from enum import Enum
""" ----------IMPORT----------]""" 

"""[----------CHARACTER CHECK---------- """

class Chars:
	#Avoid sensitive/unparsable symbol
	VALID_CHARS = "!#$%()*+,-.:;=?@[]^_`{|}~ %s%s" + string.ascii_letters + string.digits
	
""" ----------CHARACTER CHECK----------]""" 

"""[----------ENUM---------- """
#Store all naming conventions in Enum

class Node_Tags(Enum):
	"""
	Put reserved tag names here
	"""
	VIZOPPROJECT = 'VizopProject'
	VIZOPVERSION = 'VizopVersion'
	PROJECT = 'Project'
	PROJECT_NAME = 'Project_Name'
	PROJECT_NUMBER = 'ProjectNumber'
	PROJECT_DESCRIPTION = 'ProjectDescription'
	PROJECT_TEAMMEMBERS = 'ProjectTeammembers'
	PROJECT_TEAMMEMBER_ID = 'ProjectTeamMemberID'
	PROJECT_TEAMMEMBER_NAME = 'ProjectTeamMemberName'
	PROJECT_TEAMMEMBER_ROLE = 'ProjectTeamMemberRole'
	PROJECT_TEAMMEMBER_AFFILIATION = 'ProjectTeamMemberAffiliation'
	HUMANNAME = 'HumanName'
	
	PROJECT_TEAMMEMBER = 'ProjectTeammember'
	DESCRIPTION = 'Description'
	TEAM_MEMBERS = 'Team_Members'
	TEAM_MEMBER = 'Team_Member'
	EDIT_NUMBER = 'Edit_Number'
	ID = 'ID'
	NAME = 'Name'
	TYPE = 'Type'
	ROLE = 'Role'
	AFFILIATION = 'Affiliation'
	SHORTTITLE = 'ShortTitle'
	PROJNUMBER = 'ProjNumber'
	EDITNUMBER = 'EditNumber'
	PROCESSUNIT = 'ProcessUnit'
	UNITNUMBER = 'UnitNumber'
	SHORTNAME = 'ShortName'
	LONGNAME = 'LongName'
	RISKRECEPTOR = 'RiskReceptor'
	NUMBERINGSYSTEM = 'NumberingSystem'
	CHUNK = 'Chunk'
	STRVALUE = 'strValue'
	FIELDWIDTH = 'Fieldwidth'
	PADCHAR = 'PadChar'
	STARTAT = 'StartAt'
	SKIPTO = 'SkipTo'
	GAPBEFORE = 'GapBefore'
	INCLUDE = 'Include'
	NOVALUE = 'NoValue'
	CATEGORY = 'Category'
	DIMENSION = 'Dimension'
	SEVERITYDIMENSION = 'SeverityDimension'
	ENTRY = 'Entry'
	CONSTANT = 'Constant'
	LINKFROM = 'LinkFrom'
	CONSTVALUE = 'ConstValue'
	PHA = 'PHA'
	PHAOBJECT = 'PHAObject'
	RECOMMENDATIONREPORT = 'RecommendationReport'
	RISKMATRIX = 'RiskMatrix'
	FAULTTREE = 'FaultTree'
	COLUMN = 'Column'
	FTCOLUMN = 'FTColumn'
	NODE = 'Node'
	CAUSE = 'Cause'
	ALARM = 'Alarm'
	BOOKMARK = 'Bookmark'
	COMMENT = 'Comment'
	TEXT = 'Text'
	COPIEDTO = 'CopiedTo'
	LINK = 'Link'
	FTEVENT = 'FTEvent'
	VALUE = 'Value'
	ACTIONITEM = 'ActionItem'
	COLLAPSEGROUP = 'CollapseGroup'
	VIEWMODE = 'ViewMode'
	FTGATE = 'FTGate'
	FTCONNECTOR = 'FTConnector'
	DEADLINE = 'Deadline'
	RESPONSIBLE = 'Responsible'
	HEADERDATA = 'HeaderData'

class Node_Attrs(Enum):
	ID = 'Id'
	KIND = 'kind'

class Node_Types(Enum):
	TEST = 'Test'
	NAME = 'Name'
	NUMBER = 'Number'
	VALUE = 'Value'
	BOOKMARK = 'Bookmark'
	COMMENT = 'Comment'
	ACTION_ITEM = 'Action_Item'
	PHA_OBJECT = 'PHA_Object'
	PROCESS_UNIT = 'Process_Unit'

class Node_Value_Attrs(Enum):
	NODE_VALUE_ATTR_UNIT_NAME = 'Unit'
	NODE_VALUE_ATTR_VALUEKIND_NAME = 'value_kind'
	
class Node_NumberingSystem_Types(Enum):
	STR = 'str'
	PARENT = 'Parent'
	SERIAL = 'Serial'

class Node_Numerical_Unit_Types(Enum):
	"""
	#change to attribute
	a <Unit> tag, whose value is the engineering unit of the numerical value. Valid values are: None, Prob (indicating probability), %, /yr, /hr, FIT, hr, day, wk, month, yr. All are non-case sensitive. If the <Unit> tag is absent, a default unit is taken (varies per parameter).
	"""
	
	NONE = 'None'
	PROBABILITY = 'Prob'
	PERCENTAGE = '%'
	PERYEAR = '/yr'
	PERHOUR = '/hr'
	FIT = 'FIT'
	HOUR = 'hr'
	DAY = 'day'
	WEEK = 'wk'
	MONTH = 'month'
	YEAR = 'yr'

class Node_Numerical_Valuekinds(Enum):
	"""
	#change to attribute
	a <Kind> tag, whose value indicates the kind of the number. Valid values are: Manual (value entered by user), Constant (value fixed to a defined constant), Calc (value calculated according to a formula), Lookup (value looked up in a 2D matrix), Category (one of a list of values defined separately), Linked (value fixed to that of another parameter) (all are non-case sensitive). Defaults to Manual. Currently only Manual is implemented, and other kinds will give undefined results.
	"""
	
	MANUAL = 'Manual'
	CONSTANT = 'Constant'
	CALC = 'Calc'
	LOOKUP = 'Lookup'
	CATEGORY = 'Category'
	LINKED = 'Linked'

class Node_Status(Enum):
	DELETED = 'Deleted'

class Node_Boolean_Tag_True(Enum):
	"""
	Boolean tag values are written as True or False. When reading the file, any of the following is considered as True: True, Yes, Y, 1 (not case-sensitive). Any other value is considered as False. If the Boolean value is to be defined as “unset”, the tag should be omitted.
	"""
	B_TRUE = 'True'
	B_YES = 'Yes'
	B_Y = 'Y'
	B_ONE = '1'

class Node_Boolean_Tag_Unset(Enum):
	#Other value would be set as FALSE
	UNSET = ('unset')
	
class Node_DataTypes(Enum):
	T_STRING = 'str'
	T_TEXT = 'text'
	T_INTEGER = 'int'

class Node_Kinds(Enum):
	USER = 'User'
	CONSTANT = 'Constant'	
	LOOKUP = 'Lookup'
	CATEGORY = 'Category'
	COPIED = 'Copied'
	COPIEDFROM = 'CopiedFrom'

class Limits(Enum):
	#TO-DO
	NODEID_LOWERLIMIT = 0
	NODEID_UPPERLIMIT = 99999


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
	
def ic(StringInput, eNumAttr):
	assert type(StringInput) == str
	#TODO assert type(eNumAttr) == 
	#assert 
	
	#compare string ignore case
	return StringInput.lower() == eNumAttr.value.lower()
	
""" ----------UTIL----------]""" 
	
""" ----------ENUM----------]""" 

"""[----------NODE CLASS---------- """
class Node():
	"""
	Element IDs are unique for all elements (including comments) across entire project.
	"""
	#current node id
	cur_node_id = None
	
	node_id_set = set([])

	def __init__(self, \
	#[----------Compulsory in creation----------
	ParentNodes, \
	ChildNodes, \
	node_type, \
	node_kind, \
	node_tag_name, \
	#----------Compulsory in creation----------]
	#[----------Default/Optional in initialisation----------
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
	#----------Default/Optional in initialisation----------]
	
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
		assert isInType(node_type, Node_Types)
		assert type(node_kind) == str
		assert isInType(node_kind, Node_Kinds)
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
			if node_bookmark is not None:
				self.node_bookmark = node_bookmark
				pass
		
		if CAN_COMMENT:
			if node_comment is not None:
				self.node_comment = node_comment
				pass
		
		self.node_values = []
		if len(node_values) != 0:
			if self.CAN_REPEAT:
				self.node_values = self.node_values + node_values
			else:
				self.node_values.append(processString(node_values[0]))
				assert len(self.node_values) == 1
		
		self.node_attrs = {Node_Attrs.KIND.value:self.node_kind, Node_Attrs.ID.value:str(self.element_id)}
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

def createNode(input_ParentNodes, input_ChildNodes, input_node_type, input_node_kind, input_node_tag_name, input_node_values = []):
	"""
	#createNodeWrapper
	"""
	#TO-DO
	#Put in constructor and dictionary
	
	assert isInType(input_node_tag_name, Node_Tags)

	input_VALUE_ONLY = False
	input_CAN_REPEAT = False
	input_CAN_BOOKMARK = False
	input_CAN_COMMENT = False
	input_CONTAIN_NUMERICAL_VALUES = False
	input_CAN_TAKE_ATTRIBUTE_STATUS = False
	input_IS_COMPULSORY = False
	
	if ic(input_node_tag_name,Node_Tags.PROCESSUNIT) \
	or ic(input_node_tag_name,Node_Tags.RISKMATRIX) \
	or ic(input_node_tag_name,Node_Tags.FAULTTREE) \
	or ic(input_node_tag_name,Node_Tags.FTCOLUMN):
		#<ProcessUnit>%BU
		#<RiskMatrix>%BU
		#<FaultTree>%BU
		#<FTColumn>%BU
		input_CAN_REPEAT = True
		input_CAN_BOOKMARK = True
		input_CAN_TAKE_ATTRIBUTE_STATUS = True
	elif ic(input_node_tag_name,Node_Tags.RECOMMENDATIONREPORT):
		#<RecommendationReport>BU
		input_CAN_BOOKMARK = True
		input_CAN_TAKE_ATTRIBUTE_STATUS = True
		
	elif ic(input_node_tag_name,Node_Tags.PHA) \
	or ic(input_node_tag_name,Node_Tags.COLUMN)\
	or ic(input_node_tag_name,Node_Tags.NODE) \
	or ic(input_node_tag_name,Node_Tags.CAUSE) \
	or ic(input_node_tag_name,Node_Tags.COPIEDTO):
		#<PHA>*%
		#<Column>*%
		#<Node>*%
		#<Cause>*%
		#<CopiedTo>*%
		input_VALUE_ONLY = True
		input_CAN_REPEAT = True
	
	elif ic(input_node_tag_name, Node_Tags.ALARM) \
	or ic(input_node_tag_name, Node_Tags.COMMENT):
		#<Alarm>%U
		#<Comment>%U
		input_CAN_REPEAT = True
		input_CAN_TAKE_ATTRIBUTE_STATUS = True		

	elif ic(input_node_tag_name,Node_Tags.TEXT) \
	or ic(input_node_tag_name,Node_Tags.LINK):
		#<Text>*
		#<Link>*
		input_VALUE_ONLY = True

	elif ic(input_node_tag_name,Node_Tags.FTEVENT) \
	or ic(input_node_tag_name,Node_Tags.FTGATE) \
	or ic(input_node_tag_name,Node_Tags.FTCONNECTOR):
		#<FTEvent>%BC
		#<FTGate>%BC
		#<FTConnector>%BC
		input_CAN_REPEAT = True
		input_CAN_BOOKMARK = True
		input_CAN_COMMENT = True
	
	elif ic(input_node_tag_name,Node_Tags.VALUE):
		#<Value>C
		input_CAN_COMMENT = True
	
	elif ic(input_node_tag_name,Node_Tags.ACTIONITEM):
		#<ActionItem>%C
		input_CAN_REPEAT = True
		input_CAN_COMMENT = True
		
	elif ic(input_node_tag_name,Node_Tags.COLLAPSEGROUP):
		#<CollapseGroup>%
		input_CAN_REPEAT = True
	
	else:
		pass
	
	newNode = Node(ParentNodes = input_ParentNodes, \
	ChildNodes = input_ChildNodes, \
	node_type = input_node_type, \
	node_kind = input_node_kind, \
	node_tag_name = input_node_tag_name, \
	node_values = input_node_values, \
	VALUE_ONLY = input_VALUE_ONLY, \
	CAN_REPEAT = input_CAN_REPEAT, \
	CAN_BOOKMARK = input_CAN_BOOKMARK, \
	CAN_COMMENT = input_CAN_COMMENT, \
	CONTAIN_NUMERICAL_VALUES = input_CONTAIN_NUMERICAL_VALUES, \
	CAN_TAKE_ATTRIBUTE_STATUS = input_CAN_TAKE_ATTRIBUTE_STATUS, \
	IS_COMPULSORY = input_IS_COMPULSORY)
	return newNode

""" ----------NODE CLASS----------]""" 

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
		formattedString = '_'.join(formattedString.split(' '))
	
	return formattedString
	

def getNumberOfInstance(input_class):
	#get the number of instance for a Class by using garbage collector
	import gc
	return ('Number of {} in memory:{}'.format(input_class,len(list(filter(lambda x: isinstance(x, input_class), gc.get_objects())))))


"""[----------Project > XML---------- """
#Convert from project to XML
def createNewProject():
	pass

def convertProjectToXml(Project):
	assert type(Project) == Node
	
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

""" ----------Project > XML----------]""" 

"""[----------XML > Project---------- """
#Convert from XML to Project

def convertXmlToProject():
	tree = ET.parse('TestXML.xml')
	root = tree.getroot()
	ET.dump(tree)
	pass

def iterateRoot(node, root):
	current_node = node
	for each_ChildRoot in root:
		inner_Node = createNode(input_ParentNodes = set([current_node]), input_ChildNodes = set([]), input_node_type = Node_Types.NAME, input_node_kind = Node_Kinds.USER , input_node_tag_name = each_ChildRoot.tag, input_node_attrs = each_ChildRoot.attrib)

		iterateXML(inner_Node,each_ChildRoot)
	return (node)

""" ----------XML > Project----------]""" 

"""[----------TESTING AREA---------- """

def testCreateProject(Parent = None, Event = None):
	#Initiate id of objects

	Node.cur_node_id = 1
	Bookmark.cur_bookmark_id = 1
	Comment.cur_comment_id = 1
	
	Bookmark1 = Bookmark(isBookmarked = True)
	Comment1 = Comment('Comment test')
	
	#<Project>
	Project = createNode(input_ParentNodes = set([]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'Project', input_node_values = ['VIZOP'])
		#<VizopProject>
	VizopProject = createNode(input_ParentNodes = set([Project]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'VizopProject', input_node_values = [])
			#<VizopProject_Version>
	VizopProject_Version = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'VizopVersion', input_node_values = ['1.0'])
			#<VizopProject_ShortTitle>
	VizopProject_ShortTitle = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ShortTitle', input_node_values = ['V'])
			#<ProjectNumber>
	ProjectNumber = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectNumber', input_node_values = ['0001'])
			#<ProjectEditNumber>
	ProjectEditNumber = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'EditNumber', input_node_values = ['0001'])
			#<ProjectName>
	ProjectName = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'VizopVersion', input_node_values = ['1.0'])
			#<ProjectDescription>
	ProjectDescription = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectDescription', input_node_values = ['The purpose of this project is to...'])

			#<ProjectTeamMembers>
	ProjectTeamMembers = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMembers', input_node_values = [])
				#<ProjectTeamMember>
	ProjectTeamMember = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMember', input_node_values = [])
					#<ProjectTeamMemberID>
	ProjectTeamMemberID = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberID', input_node_values = ['1'])
					#<ProjectTeamMemberName>
	ProjectTeamMemberName = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberName', input_node_values = ['John'])
					#<ProjectTeamMemberRole>
	ProjectTeamMemberRole = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberRole', input_node_values = ['Team Lead'])
					#<ProjectTeamMemberAffiliation>
	ProjectTeamMemberAffiliation = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberAffiliation', input_node_values = ['Mary'])
					#<ProjectTeamMember>
	ProjectTeamMember = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMember', input_node_values = [])
					#<ProjectTeamMemberID>
	ProjectTeamMemberID = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberID', input_node_values = ['2'])
					#<ProjectTeamMemberName>
	ProjectTeamMemberName = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberName', input_node_values = ['Mary'])
					#<ProjectTeamMemberRole>
	ProjectTeamMemberRole = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberRole', input_node_values = ['Consultant'])
					#<ProjectTeamMemberAffiliation>
	ProjectTeamMemberAffiliation = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberAffiliation', input_node_values = ['John'])

			#<ProcessUnit>
	ProcessUnit = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Process_Unit', input_node_kind = 'User', input_node_tag_name = 'ProcessUnit', input_node_values = [])
				#<ProcessUnit_ID>
	ProcessUnit_ID = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Number', input_node_kind = 'User', input_node_tag_name = 'ID', input_node_values = ['0001'])
				#<ProcessUnit_UnitNumber>
	ProcessUnit_UnitNumber = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'UnitNumber', input_node_values = ['John'])
				#<ProcessUnit_ShortName>
	ProcessUnit_ShortName = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ShortName', input_node_values = ['UnitShortName'])
				#<ProcessUnit_LongName>
	ProcessUnit_LongName = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'LongName', input_node_values = ['UnitLongName'])
	
			#<RiskReceptor>
	RiskReceptor = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Process_Unit', input_node_kind = 'User', input_node_tag_name = 'RiskReceptor', input_node_values = [])
				#<RiskReceptor_ID>
	RiskReceptor_ID = createNode(input_ParentNodes = set([RiskReceptor]), input_ChildNodes = set([]), input_node_type = 'Number', input_node_kind = 'User', input_node_tag_name = 'ID', input_node_values = ['0001'])
				#<RiskReceptor_HumanName>
	RiskReceptor_HumanName = createNode(input_ParentNodes = set([RiskReceptor]), input_ChildNodes = set([]), input_node_type = 'Number', input_node_kind = 'User', input_node_tag_name = 'HumanName', input_node_values = ['0001'])

			#<PHAObject>
	PHAObject = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'PHAObject', input_node_values = [])
				#<FT>
	FT = createNode(input_ParentNodes = set([PHAObject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'PHAObject')
				#<AlarmRationalization>
	AlarmRationalization = createNode(input_ParentNodes = set([PHAObject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'PHAObject')
	
			#<NumberingSystem>
	NumberingSystem = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'NumberingSystem', input_node_values = [])
				#<NumberingSystem_ID>
	NumberingSystem_ID = createNode(input_ParentNodes = set([NumberingSystem]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ID', input_node_values = [])
				#<Chunk>
	NumberingSystem_Chunk = createNode(input_ParentNodes = set([NumberingSystem]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'Chunk', input_node_values = [])
					#<Type>
	NumberingSystem_Chunk_Type = createNode(input_ParentNodes = set([NumberingSystem]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'Type', input_node_values = ['str'])
						#<strValue>

	print ('getNumberOfInstance:{}'.format(getNumberOfInstance(Node)))
	print ('convertProjectToXml:{}'.format(convertProjectToXml(Project)))

""" ----------TESTING AREA----------]"""  

"""[----------RUN MAIN PROGRAM---------- """
def main():
	pass

if __name__ == '__main__':
	main()
""" ----------RUN MAIN PROGRAM----------]"""  
