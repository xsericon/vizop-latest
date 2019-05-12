# -*- coding: utf-8 -*-
# Module: projects. This file is part of Vizop. Copyright xSeriCon, 2018

# standard modules needed:
import os, shutil
import os.path
import xml.etree.ElementTree as ElementTree

# vizop modules needed:
from vizop_misc import IsReadableFile, IsWritableLocation, select_file_from_all
import settings, core_classes, info

"""
The projects module contains functions for handling entire Vizop projects, including project files.
"""

UsableProjDocTypes = ['VizopProject0.1'] # project doc types parsable by this version of Vizop
CurrentProjDocType = 'VizopProject0.1' # doc type written by this version of Vizop
HighestProjID = 0 # highest ID of all projects currently open (int)

class ProcessUnit(object): # object representing an area of the plant, e.g. "gas dryer"

	def __init__(self, Proj=None, UnitNumber='', ShortName='', LongName=''):
		object.__init__(self)
		assert isinstance(Proj, ProjectItem)
		assert isinstance(UnitNumber, str)
		assert isinstance(ShortName, str)
		assert isinstance(LongName, str)
		self.Proj = Proj
		Proj.MaxIDInProj += 1
		self.ID = str(Proj.MaxIDInProj)
		self.UnitNumber = UnitNumber
		self.ShortName = ShortName
		self.LongName = LongName

class Collaborator(object): # object representing a remote computer collaborating on this project

	def __init__(self, Proj=None, ShortName='', LongName=''):
		object.__init__(self)
		assert isinstance(Proj, ProjectItem)
		assert isinstance(ShortName, str)
		assert isinstance(LongName, str)
		self.Proj = Proj
		Proj.MaxIDInProj += 1
		self.ID = str(Proj.MaxIDInProj)
		self.ShortName = ShortName
		self.LongName = LongName

class ProjectFontItem(object): # virtual fonts for use with texts in PHA objects
			# To get actual face name (str) of a wx.Font, use font.GetFaceName()

	def __init__(self, HumanName=_('<undefined>'), RealFace=''):
		object.__init__(self)
		self.HumanName = HumanName
		self.RealFace = RealFace # actual face name of font associated with this instance

DefaultProjectFontItem = ProjectFontItem(_('<System default>'), '')

class ProjectItem(object): # class of PHA project instances

	def __init__(self, ID): # ID (int): unique ID to assign to ProjectItem instance
		assert isinstance(ID, int)
		object.__init__(self)
		self.ID = str(ID)
		self.EditAllowed = True # whether user can edit project in this Vizop instance. Eventually, this will be related to
			# (1) whether license valid, and (2) whether this Vizop instance is in 'master' mode
		self.ShortTitle = 'CHAZOP with chocolate sauce' # project short title for display
		self.ProjNo = '141688' # user's project reference number
		self.Description = 'A great excuse to spend 4 weeks in Seoul' # longer description of project
		self.MaxIDInProj = 0 # (int) highest ID of all objects in the project that are not contained in PHA models
		self.PHAObjs = [] # list of PHA objects, in order created
		self.ActiveViewports = [] # list of all currently active Viewports, in order created
			# (possibly we don't need this, as all Viewports should be attached to PHA objects)
		self.AllViewportShadows = [] # list of all Viewport shadows (belonging to datacore)
		self.IPLKinds = []
		self.CauseKinds = []
		self.RiskReceptors = [] # instances of RiskReceptorItem defined for this project
		self.NumberSystems = [] # instances of NumberSystemItem
		self.TolRiskModels = [] # instances of TolRiskModel subclasses
		self.CurrentTolRiskModel = None
		self.ProcessUnits = [ProcessUnit(Proj=self, UnitNumber='120', ShortName='Wash', LongName='Plastic washing area'),
							 ProcessUnit(Proj=self, UnitNumber='565', ShortName='Pyrolysis 1', LongName='Pyrolysis reactor no. 1')]
		self.Collaborators = [Collaborator(Proj=self, ShortName='Mary', LongName='Mary Simmons'),
							  Collaborator(Proj=self, ShortName='Rupert', LongName='Rupert McTavish')]
		self.RenderingForDisplay = [ [] ] # list of lists of FTDisplayObject; current hierarchy of fault tree as displayed
		self.Selected = [] # list of lists of currently selected PHA items, in reverse order of selection, per Viewport
		self.NextFTItemBackgroundColour = (0,0,255) # colour of next FT object to be created
		self.TextStyleItems = [] # default text styles used
		self.ProjectFonts = {'Default': DefaultProjectFontItem} # hash of ProjectFontItems and ProjectFontItem instances used in texts
		self.MostRecentNewPHAItemClass = None # Latest 'new' PHA item class for which text was created
		self.MostRecentInitialTextStyle = {'Default': None} # text styles applied to PHA objects
			# Ideally we would set 'Default': datacore.DefaultTextStyleItem but this would create circular import
		self.ForwardHistory = [] # list of MilestoneItem instances that were displayed before user clicked 'back' button
		self.BackwardHistory = [] # list of MilestoneItem instances recently displayed; for navigation
		self.UndoList = [] # list of undoable actions
		self.RedoList = [] # list of redoable actions
		self.SaveOnFly = False # bool; whether project is being saved on fly
		self.SandboxStatus = 'SandboxInactive' # str; whether sandbox is active
		self.OutputFilename = '' # str; full pathname of last file last used to save project in this Vizop instance.
			# If we are saving on fly, this contains the pathname of the project file to update
		self.EditNumber = 0 # int; incremented every time the project's dataset is changed



	def GetFTColumnWidth(self, FT): # return preferred distance, in canvas units, between left edges of a Fault Tree's columns (if in columns)
		# or between top edges of rows (if in rows)
		print("PR571 Warning, GetFTColumnWidth not implemented yet")
		return 100

	def FontKind(self, PHAObject=None): # return ProjectFontItem instance appropriate for PHAObject
		if not PHAObject: return self.ProjectFonts['Default'] # handle case when no PHAObject specified
		if PHAObject not in self.ProjectFonts: # never created text for this PHA item class before?
			# ProjectFontItem same as last new PHA item
			self.ProjectFonts[PHAObject] = self.ProjectFonts.get(self.MostRecentNewPHAItemClass, self.ProjectFonts['Default'])
			self.MostRecentNewPHAItemClass = PHAObject # this is now the last new PHA item class
		return self.ProjectFonts[PHAObject]
		# When the 'default' font for a PHA item class is changed, in general we need to create a new ProjectFontItem instance for it.
		# This would be done in the iWindow widget handler

def TestProjectsOpenable(ProjectFilenames, ReadOnly=False):
	"""
	Args: ProjectFilenames: list of str containing path of vizop project files (can be empty list)
	ReadOnly (bool): whether only read access is required to the files (not yet implemented)
	Function: test the files to see if they can be accessed and contain valid vizop projects that can be opened.
	Return: ProjOpenData: list of dict, one dict per file in the same order as ProjectFilenames
	dict contains keys: Openable (bool), Comment (str) - user feedback explaining why project is not openable
	"""
	# Temporary implementation: just test if it's a readable file
	ProjOpenData = [ {'Openable': False, 'Comment': ''} ] * len(ProjectFilenames) # set up template for return data
	# check project files in turn
	for (FileIndex, ProjFile) in enumerate(ProjectFilenames):
		ProjOpenData[FileIndex]['Openable'] = IsReadableFile(ProjFile)
	return ProjOpenData


def GetProjectFilenamesToOpen(parent_frame):
	"""
	Open dialogue box for selection of project file(s)

	   * parent_frame - parent of filename selection dialogue box

	Returns list of path names requested
	"""
	sm = settings.SettingsManager()
	try:
		working_dir = sm.get_config('UserWorkingDir')
	except KeyError:
		working_dir = os.path.expanduser('~')

	proj_file_ext = sm.get_config('ProjFileExt')

	file_list = select_file_from_all(message=_('Select Vizop project file(s) to open'),
							  default_path=working_dir,
							  wildcard='.'.join(['*', proj_file_ext]),
							  read_only=False, allow_multi_files=True,
							  parent_frame=parent_frame)

	if file_list:
		# at least one project file was selected - update the working directory
		working_dir = os.path.dirname(file_list[0])
		sm.set_value('UserWorkingDir', working_dir)

# core of the XML tree for project files
XMLTreeSkeleton = """<?xml version="1.0" encoding="iso-8859-1"?>
<!DOCTYPE vizop_project [
	<!ELEMENT vizop_version (#PCDATA)>
]>
<vizop_project>
<vizop_version>"%s"</vizop_version>
</vizop_project>
""" % CurrentProjDocType

#@Jack: TODO XML tree and rules work in progress
XMLTreeFormat = """
<Config>

	<!--This config file is to set rules for file input and output. There are two kinds of tags and attributes in this config. 

	The first one is Project structure. It is restricted within the structure of a project format. For example, VizopVersion tag cannot be created under tags other than VizopProject.-->

	<!--
	Rules tag stores the rules as below:

	•* indicates tags that contain values only, not other tags. (The * should not appear in the actual file.)
	•% indicates tags that can be repeated. (If non-% tags are repeated, only the first instance in each level will be used.) (The % should not appear in the actual file.)
	•B indicates tags that can contain <Bookmark> tags. (The B should not appear in the actual file.) The structure of a <Bookmark> tag is as follows:
			 <Bookmark>*% BookmarkSerialNumber
	</Bookmark>
	Bookmark serial numbers are in the order the bookmarks were created.
	•C indicates tags that can contain <Comment> child tags. (The C should not appear in the actual file.) The structure of a <Comment> tag is as follows:
			 <Comment>%B CommentSerialNumber
	</Comment>
	• indicates tags that contain numerical values. The value (real or integer) must come immediately after the tag, and before any child tags. The tag can optionally contain the following child tags:
	o   a <Unit> tag, whose value is the engineering unit of the numerical value. Valid values are: None, Prob (indicating probability), %, /yr, /hr, FIT, hr, day, wk, month, yr. All are non-case sensitive. If the <Unit> tag is absent, a default unit is taken (varies per parameter).
	o   a <Kind> tag, whose value indicates the kind of the number. Valid values are: Manual (value entered by user), Constant (value fixed to a defined constant), Calc (value calculated according to a formula), Lookup (value looked up in a 2D matrix), Category (one of a list of values defined separately), Linked (value fixed to that of another parameter) (all are non-case sensitive). Defaults to Manual. Currently only Manual is implemented, and other kinds will give undefined results.
	•	U indicates tags that can take an attribute “Status” (for use by Save On The Fly). For example, <Node Status=Deleted>. The Status attribute is optional. Recognised values are detailed in the “Project open and save” specification. Unrecognised values of Status will be ignored (normally silently; a message can be output if we are in Verbose mode).
	•	! indicates compulsory tags. If missing from the file, vizop can't open the project. All tags not marked ! can be omitted.
	-->

	<!--
	Uncommon attribute stores list of attribute that is not commonly used across all tags.
	-->

	<FileTypeVersion>
	0.1
	</FileTypeVersion>

	<CommonTagAttribute>
		<id/>
		<kind/>
		<unit/>
		<deleted/>

	</CommonTagAttribute>

	<ProjectStructure>
		<!--Fixed Structure Outer Tag-->
		<VizopProject rules="!" uncommon_attr="VizopVersion">
			<VizopVersion rules="!" uncommon_attr=""/>
			<ProjectName rules="!" uncommon_attr=""/>
			<Description rules="!" uncommon_attr=""/>
			<TeamMembers rules="!" uncommon_attr="">
				<TeamMember rules="!" uncommon_attr="">
					<ID rules="" uncommon_attr=""/>
					<Name rules="" uncommon_attr=""/>
					<Role rules="" uncommon_attr=""/>
					<Affiliation rules="" uncommon_attr=""/>
				</TeamMember>
			</TeamMembers>
			<EditNumber rules="" uncommon_attr=""/>
			<ShortTitle rules="" uncommon_attr=""/>
			<ProjNumber  rules="" uncommon_attr=""/>
		</VizopProject>
	</ProjectStructure>

	<!--The second format is not restricted. Can be use anywhere in the project and even outside the project-->
	<UnboundedStructure>
		<!--Unbounded Structure-->

		<ProcessUnit rules="%BU" uncommon_attr="">
			<ID rules="" uncommon_attr=""/>
			<UnitNumber rules="" uncommon_attr=""/>
			<ShortName rules="" uncommon_attr=""/>
			<LongName rules="" uncommon_attr=""/>
			<PHA rules="*%" uncommon_attr=""/>
		</ProcessUnit>

		<RecommendationReport rules="BU" uncommon_attr=""/>

		<RiskReceptor rules="" uncommon_attr="">
			<ID rules="" uncommon_attr=""/>
			<Name rules="" uncommon_attr=""/>
		</RiskReceptor>

		<NumberingSystem rules="" uncommon_attr="">
			<ID rules="" uncommon_attr=""/>
			<Chunk rules="" uncommon_attr="">
				<Type rules="" uncommon_attr=""/>
				<!--Logic to be done for type check-->
				<!--str-->
				<Value rules="" uncommon_attr=""/>
				<!--Parent-->
				<ID rules="" uncommon_attr=""/>
				<!--Serial-->
				<Fieldwidth rules="" uncommon_attr=""/>
				<PadChar rules="" uncommon_attr=""/>
				<StartAt rules="" uncommon_attr=""/>
				<SkipTo rules="" uncommon_attr=""/>
				<GapBefore rules="" uncommon_attr=""/>
				<Include rules="" uncommon_attr=""/>
				<NoValue rules="" uncommon_attr=""/>
			</Chunk>
			<Name rules="" uncommon_attr=""/>
		</NumberingSystem>

		<RiskMatrix rules="%BU" uncommon_attr="">
			<Category rules="" uncommon_attr="">
				<ID rules="" uncommon_attr=""/>
				<Name rules="" uncommon_attr=""/>
				<Description rules="" uncommon_attr=""/>
			</Category>
			<SeverityDimension rules="" uncommon_attr="">
				<Dimension rules="" uncommon_attr="">
					<Name rules="" uncommon_attr=""/>
					<Key rules="" uncommon_attr=""/>
				</Dimension>
			</SeverityDimension>
		</RiskMatrix>

		<FaultTree rules="%BU" uncommon_attr="GateStyle,OpMode">
			<HeaderData rules="C" uncommon_attr=""/>
			<FTColumn rules="%BU" uncommon_attr="">
				<FTElements rules="*%BC" uncommon_attr="">
					<FTEvent rules="%BC" uncommon_attr="Description,ConnectTo,IsSIFFailtureEvent,IsFinalEvent">
						<Value/>
						<ActionItem/>
						<CollapseGroup/>
						<ViewMode/>

					</FTEvent>
				</FTElements>
			</FTColumn>
		</FaultTree>

		<PHA rules="%BU" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
			<Node rules="*%" uncommon_attr=""/>
		</PHA>

		<Node rules="%BU" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
			<Cause rules="" uncommon_attr=""/>
		</Node>

		<Cause rules="%BU" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
		</Cause>

		<Alarm rules="%U" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
		</Alarm>

		<Constant rules="!" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
			<Name rules="!" uncommon_attr=""/>
			<LinkFrom rules="!" uncommon_attr=""/>
			<ConstValue rules="!" uncommon_attr=""/>

		</Constant>

		<Bookmark rules="!" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
		</Bookmark>

		<Comment rules="!" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
			<Text rules="*" uncommon_attr=""/>
			<CopiedTo rules="*%" uncommon_attr=""/>
			<Link rules="*" uncommon_attr=""/>
		</Comment>

		<Actionitem rules="!" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
		</Actionitem>

		<Value rules="!" uncommon_attr="">
			<ID rules="!" uncommon_attr=""/>
		</Value>

	</UnboundedStructure>
	<!--Constant Tag-->

</Config>
"""

def OpenProjectFiles(ProjectFilesToOpen, UsingTemplates=False, SaveOnFly=True, ProjectFilesToCreate=[]):
	# attempt to open project files in ProjectFilesToOpen (list). All files must already be checked as existent and readable.
	# UsingTemplates (bool): whether ProjectFilesToOpen contains templates rather than actual project files
	# SaveOnFly (bool): whether to create an output file for appending changes on-the-fly
	# If UsingTemplates and SaveOnFly, we need full pathnames in ProjectFilesToCreate for the output files.
	# return OpenProjects (list of Project instances), SuccessReport (list (1 item per project file in ProjectFilesToOpen) of dict:
	# {OpenedOK: bool, ProblemReport: str (human readable), and other items with file stats (eg number of nodes)}
	# first, integrity check of the args
	if SaveOnFly:
		assert (len(ProjectFilesToOpen) == len(ProjectFilesToCreate)), "PR117 need file names to create project files"
	ProjectsOpened = []
	SuccessReport = []
	for (ProjIndex, ProjFileName) in enumerate(ProjectFilesToOpen):
		ProjDocTree = ElementTree.parse(ProjFileName) # open file, convert into parsed tree
		# check if doc type is usable; if so, extract it into a new project
		# the following line finds the first node of type DOCTYPE, looks at its name
		FileVersion = ProjDocTree.find('vizopversion')
		if FileVersion is not None: # XML file contains a vizopversion element
			if FileVersion.text in UsableProjDocTypes:
				NewProj = CreateProject()
				OpenedOK, ProblemReport = PopulateProjectFromFile(NewProj, ProjDocTree)
				# if we succeeded in extracting the project file or template, and if saving on the fly, create the output file
				# Any problem report will be appended to the report from file opening (above)
				if OpenedOK and SaveOnFly:
					OutputFileOK, ProblemReport = SaveEntireProject(NewProj, ProjectFilesToCreate[ProjIndex], ProblemReport, Close=False)
					NewProj.SaveOnFly = OutputFileOK
				else:
					OutputFileOK = True # dummy value if no output file needed
				SuccessReport.append( {'OpenedOK': OpenedOK, 'OutputFileOK': OutputFileOK, 'ProblemReport': ProblemReport} )
				if OpenedOK:
					ProjectsOpened.append(NewProj)
			else: # proj doc file version is not usable by this version of Vizop
				ProblemReportText = {True: _('Unusable template file type %s'), False: _('Unusable project file type %s')}[UsingTemplates]
				SuccessReport.append( {'OpenedOK': False, 'ProblemReport': ProblemReportText % DocType(ProjDocTreeTop)} )
		else: # proj doc file doesn't seem to be a Vizop file
			SuccessReport.append( {'OpenedOK': False, 'ProblemReport': _("Doesn't seem to be a Vizop file")})
	return ProjectsOpened, SuccessReport

def CreateProjects(TemplateFiles, SaveOnFly, FilesToCreate):
	# Attempt to open template files in TemplateFiles (list) and make new projects from them.
	# All template files must already be checked as existent and readable.
	# SaveOnFly (bool): whether we should create project files for the projects.
	# FilesToCreate (list of str): full pathnames of project files to be created based on TemplateFiles
	# return OpenProjects (list of Project instances), SuccessReport (list (1 item per project file in ProjectFilesToOpen) of dict:
	# {OpenedOK: bool, ProblemReport: str (human readable), and other items with file stats (eg number of nodes)}
	return OpenProjectFiles(TemplateFiles, UsingTemplates=True, SaveOnFly=SaveOnFly, ProjectFilesToCreate=FilesToCreate)

def CreateProject():
	# create and initialize a new project object. Returns the object.
	global HighestProjID
	HighestProjID += 1
	NewProj = ProjectItem(ID=HighestProjID)
	SetupDefaultTolRiskModel(Proj=NewProj)
	return NewProj

def PopulateProjectFromFile(Proj, DocTreeTop):
	# reads all data from doc tree generated by minidom.parse(), of which DocTreeTop is the top node (as returned by parse()).
	# Creates all needed PHA objects in Proj (ProjectItem instance) and populates them with data from doc tree.
	# Returns (OpenedOK (bool): False if the project can't even be partially opened,
	# ProblemReport (str; empty if no problems found, otherwise provides human-readable description of problems))
	OpenedOK = True
	ProblemReport = '' # this is just dummy code for now
	return OpenedOK, ProblemReport

def SaveEntireProject(Proj, OutputFilename, ProblemReport='', Close=False):
	# Create a new file with OutputFilename (full path).
	# Write the entire data from Proj into it.
	# Append any problems to input arg ProblemReport.
	# If Close, close the file after writing.
	# Return: WriteOK (bool) - whether file written successfully;
	#         ProblemReport (str) - human readable description of any problem encountered.

	def AddToReport(ExistingReport, TextToAdd):
		# append TextToAdd (str) to ExistingReport (str) in a human-readable way
		# Return combined report (str)
		if ExistingReport:
			return ExistingReport + '\n' + TextToAdd
		else:
			return TextToAdd

	Report = ProblemReport # final report to return to user
	# First, try to create the project file
	if IsWritableLocation(os.path.dirname(OutputFilename)):
#		ProjFile = open(OutputFilename, 'w') # create the file
		WriteOK, WriteReport = WriteEntireProjectToFile(Proj, OutputFilename) # write all the data into the file
		Report = AddToReport(Report, WriteReport)
#		if Close: ProjFile.close()
	else:
		WriteOK = False
		Report = AddToReport(Report, _('Unable to write project file at %s') % os.path.dirname(OutputFilename) )
	return WriteOK, Report

def WriteEntireProjectToFile(Proj, ProjFilename):
	# write all data for Proj (ProjectItem) into ProjFilename (str), already confirmed as writable.
	# Return: WriteOK (bool) - whether data written successfully;
	#         ProblemReport (str) - human readable description of any problem encountered.
	# Make the XML tree, starting with the Document node.
	MyXMLTree = ElementTree.ElementTree() # create new XML structure
	MyXMLTree._setroot(ElementTree.fromstring(XMLTreeSkeleton)) # set the skeleton as the XML tree root element
	# later, add more code here to write all PHA objects into the XML tree
	# write the XML file
	try:
		MyXMLTree.write(ProjFilename, encoding="UTF-8", xml_declaration=True)
	except:
		return False, ''

	return True, ''
	# TODO items to include: core_classes.ConstantItem.AllConstants

def SetupDefaultTolRiskModel(Proj):
	# set up a default tolerable risk model (severity categories) in project instance Proj
	# Make risk receptors
	PeopleRiskReceptor = core_classes.RiskReceptorItem(XMLName='People', HumanName=_('People'))
	EnvironmentRiskReceptor = core_classes.RiskReceptorItem(XMLName='Environment', HumanName=_('Environment'))
	AssetsRiskReceptor = core_classes.RiskReceptorItem(XMLName='Assets', HumanName=_('Assets'))
	ReputationRiskReceptor = core_classes.RiskReceptorItem(XMLName='Reputation', HumanName=_('Reputation'))
	# make a tolerable risk model object; populate it with risk receptors
	TolRiskModel = core_classes.TolRiskFCatItem()
	TolRiskModel.RiskReceptors = [PeopleRiskReceptor, EnvironmentRiskReceptor, AssetsRiskReceptor, ReputationRiskReceptor]
	# make a tolerable risk matrix
	Severity0 = core_classes.CategoryNameItem(XMLName='0', HumanName=_('Negligible'), HumanDescription=_('No significant impact'))
	Severity1 = core_classes.CategoryNameItem(XMLName='1', HumanName=_('Minor'), HumanDescription=_('Small, reversible impact'))
	Severity2 = core_classes.CategoryNameItem(XMLName='2', HumanName=_('Moderate'), HumanDescription=_('Significant impact'))
	Severity3 = core_classes.CategoryNameItem(XMLName='3', HumanName=_('Severe'), HumanDescription=_('Major impact with long-term consequences'))
	MyTolFreqTable = core_classes.LookupTableItem()
	TolRiskModel.TolFreqTable = MyTolFreqTable
	MyTolFreqTable.HowManyDimensions = 1
	ThisDimension = 0 # which dimension of MyTolFreqTable we are setting up
	MyTolFreqTable.SeverityDimensionIndex = ThisDimension # which dimension of the table contains severity categories
	MyTolFreqTable.DimensionHumanNames = [_('Severity')]
	MyTolFreqTable.Keys = [ [Severity0, Severity1, Severity2, Severity3] ]
	# set tolerable frequency values. Listed here per RR in /yr
	TolFreqValues = [ [1e-2, 1e-3, 1e-4, 1e-5], [1e-2, 1e-3, 1e-4, 1e-5], [1e-1, 1e-2, 1e-3, 1e-4],
					  [5e-2, 5e-3, 5e-4, 5e-5] ]
	# populate tol freq table with empty value objects
	MyTolFreqTable.Values = [core_classes.UserNumValueItem() for ThisCat in MyTolFreqTable.Keys[0]]
	# put the required values from TolFreqValues into the value objects
	for ThisSevCatIndex in range(len(MyTolFreqTable.Keys[ThisDimension])):
		ThisTolFreqValue = MyTolFreqTable.Values[ThisSevCatIndex]
		for ThisRRIndex, ThisRR in enumerate(TolRiskModel.RiskReceptors):
			ThisTolFreqValue.SetMyValue(NewValue=TolFreqValues[ThisRRIndex][ThisSevCatIndex], RR=ThisRR)
		ThisTolFreqValue.SetMyUnit(core_classes.PerYearUnit)
	# put tol risk model into project
	Proj.TolRiskModels.append(TolRiskModel)
	Proj.CurrentTolRiskModel = TolRiskModel

def SaveOnFly(Proj, UpdateData=None):
	# save an update to an object in Proj (ProjectItem instance) in its output file.
	# Any procedure that changes the data set should call this procedure.
	# UpdateData (XML tree): data specifying the update to be saved
	# return Success (bool), ProblemReport (str) = '' if all is well
	assert isinstance(Proj, ProjectItem)
	assert isinstance(UpdateData, ElementTree.Element)
	if Proj.SaveOnFly: # should we save SIFs in this project?
		if Proj.SandboxStatus == 'SandboxActive': pass # for future implementation
		else: # not in sandbox; save now
			# check whether the project has ever been saved
			if Proj.OutputFileMade:
				# try to save changes and return any problem report to datacore
				return SaveChangesToProj(Proj, UpdateData=UpdateData)
			else: # try to save entire project
				Success, ProblemReport = SaveEntireProject(Proj, Proj.OutputFilename, Close=True)
				Proj.OutputFileMade = Success
				# return any problem report to datacore
				return Success, ProblemReport

def SaveChangesToProj(Proj, UpdateData=None, Task='Update'):
	# write updates to project file
	# UpdateData (XML tree): data specifying the update to be saved
	# Task (str): what type of action to save. Currently only 'Update' implemented
	# return Success (bool), ProblemReport (str) = '' if all is well
	assert isinstance(Proj, ProjectItem)
	assert isinstance(UpdateData, ElementTree.Element)
	assert Task == 'Update'
	Success = True; ProblemReport = ''
	# Step 1. Check that we can still access project's file for writing
	Success = IsReadableFile(Proj.OutputFilename) and IsWritableLocation(os.path.dirname(Proj.OutputFilename))
	if not Success: ProblemReport = "Can'tAccessProjectFileLocation"
	if Success:
		# Step 2. Copy the project file. First, make a file path with "_Restore" inserted before file extension
		FilenameHead, FilenameExt = os.path.splitext(Proj.OutputFilename) # split off file extension
		WorkingFilePath = FilenameHead + info.RestoreFileSuffix + FilenameExt
		try:
			shutil.copy2(Proj.OutputFilename, WorkingFilePath) # copy the file with metadata
		except IOError:
			Success = False; ProblemReport = "Can'tMakeWorkingFile"
	if Success:
		# Step 3. Open the working copy file
		TagToFind = '</' + info.ProjectRootTag + '>'
		try:
			ProjFile = open(WorkingFilePath, 'r+') # open file in update mode
			# Step 4. Remove and keep tail of working file
			# find existing final tag </vizop_project>, assuming it's within the final 50 chars of the file
			ProjFile.seek(-50, 2) # go to 50 chars before the end of the file
			Tail = ProjFile.read() # get file content from seek position to end
			if TagToFind not in Tail:
				Success = False; ProblemReport = "ProjectFileInvalid"
		except IOError: # problem with file access
			Success = False; ProblemReport = "Can'tReadWorkingFile"
	if Success:
		if Task == 'Update': # create an <Update> tag
			# create an XML element for the SIF
			UpdateElement = ElementTree.Element(tag=info.UpdateTag)
			# Step 5. put the update data into the Update element, and write it to file
			UpdateElement.append(UpdateData)
			try:
				ProjFile.seek(Tail.rindex(TagToFind) - len(Tail), 2) # go to start of tail in file
				# convert XML to string, and write into file
				ProjFile.write(ElementTree.tostring(UpdateElement))
				# Step 6. Add final tag (to ensure file is valid XML) + anything originally after it in the project file
#				ProjFile.write('</' + info.ProjectRootTag + '>') # old version, wrote only the tag itself
				ProjFile.write(Tail.rindex(TagToFind))
				# Step 7. Close working file
				ProjFile.close()
			except IOError:
				Success = False; ProblemReport = "Can'tWriteWorkingFile"
	if Success:
		# Step 8: delete the original project file, and Step 9: Rename working file to project file
		try:
			os.replace(WorkingFilePath, Proj.OutputFilename)
		except (IOError, OSError):
			Success = False; ProblemReport = "Can'tOverwriteProjectFile"
	return Success, ProblemReport

