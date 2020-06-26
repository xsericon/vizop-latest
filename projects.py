# -*- coding: utf-8 -*-
# Module: projects. This file is part of Vizop. Copyright xSeriCon, 2019

# standard modules needed:
import os, shutil, datetime
import os.path
import xml.etree.ElementTree as ElementTree

# vizop modules needed:
from vizop_misc import IsReadableFile, IsWritableLocation, select_file_from_all
#import settings, core_classes, info, vizop_parser, faulttree
import settings, core_classes, info, faulttree, utilities, display_utilities

"""
The projects module contains functions for handling entire Vizop projects, including project files.
"""

UsableProjDocTypes = ['VizopProject0.1'] # project doc types parsable by this version of Vizop
CurrentProjDocType = 'VizopProject0.1' # doc type written by this version of Vizop
HighestProjID = 0 # highest ID of all projects currently open (int)
def _(DummyArg): return DummyArg # dummy definition of _(); the real definition is elsewhere
	# TODO this won't translate for one-time calls when an object is created. Need a 'Translate' function in vizop_misc?

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

		self.MaxIDInProj = 0 # (int) highest ID of all objects in the project
		self.PHAObjs = [] # list of PHA objects existing locally, in order created; empty if datacore is remote
		self.PHAObjShadows = [] # list of info about PHA objects; used by control frame, as the project datacore may be
			# remote, so it may not have access to self.PHAObjs; same order as self.PHAObjs
		self.ActiveViewports = [] # list of all actual Viewports (not Viewport shadows) currently displayed in a display device.
			# This attrib is used on the "display side" (client side) project instance, not in datacore
		self.AllViewportShadows = [] # list of all Viewport shadows (belonging to datacore)
		# should be ViewportShadow instances, but might be Viewport instances, i.e. ViewportBaseClass subclass instances FIXME
		self.ViewportsWithoutPHAObjs = [] # datacore: any Viewport instances that don't belong to PHA objects (e.g. action item view)
		self.ArchivedViewportShadows = [] # datacore: Viewport shadows created and subsequently deleted; retained to
		# allow retrieval of persistent attribs. Need not be stored in project file.
		self.IPLKinds = []
		self.CauseKinds = []
		self.RiskReceptors = [core_classes.RiskReceptorItem(XMLName='People', HumanName=_('People'))] # instances of RiskReceptorItem defined for this project
		self.NumberSystems = [core_classes.SerialNumberChunkItem()] # instances of NumberSystemItem. Not used;
			# to get number systems, call GetAllNumberingSystems()
		self.TolRiskModels = [] # instances of TolRiskModel subclasses
		self.CurrentTolRiskModel = None
		self.Constants = [] # instances of ConstantItem
		# the following is for testing
		TestConstant = core_classes.ConstantItem(HumanName='Alarm failure', ID=self.GetNewID())
		TestConstant.SetMyValue(0.1)
		TestConstant.SetMyUnit(core_classes.ProbabilityUnit)
		self.Constants.append(TestConstant)
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
		self.FTFullExportFilename = '' # str; last used full pathname for exporting full FT, including any extension
		self.FTFullExportFileType = '' # str; must be '' or the Extension attrib of an instance of core_classes.ImageFileType
		self.FTFullExportZoom = 1.0 # float; last zoom level used for exporting FT
		self.FTConnectorsAcrossPages = True # in FT export, whether to draw connecting arrows at page breaks
		self.FTExportShowPeripheral = 'Comments,Actions,Parking' # in FT export, which additional texts to show
		self.FTExportCannotCalculateText = _('Not calculated') # in FT export, what to show when value cannot be calc'd
		self.FTExportCombineRRs = True # in FT export, combine RRs into a single FT where possible (if False, show a
			# separate FT for each risk receptor, even if the resulting FTs are identical)
		self.FTExportExpandGates = True # in FT export, whether to show full data in logic gates (if False, a small
			# logic gate depiction will be shown instead)
		self.FTExportShowWhat = 'Header,FT' # in FT export, what sections to show; can include Header, FT, OnlySelected
		self.FTExportNewPagePerRR = False # in FT export, whether to start a new page for each risk receptor
		self.LastExportPageSize = core_classes.PaperSizeA4 # instance of core_classes.PaperSizes
		self.FTExportPaperOrientation = 'Portrait'
		self.ExportPaperMargins = {'Left': 10, 'Right': 10, 'Top': 10, 'Bottom': 10} # paper margins in mm
		self.ExportPageNumberLoc = 'Top,Centre' # must include one of Top, Bottom, None and one of Left, Centre, Right
		self.LastExportBlackAndWhite = False # bool; whether last export was in black and white
		self.LastExportFontName = '' # str; system name of font used for last export, e.g. 'Arial'
		self.LastExportPreferredDateToShow = None # ChoiceItem or None; one of the items in core_classes.DateChoices;
			# represents date choice used for last export, e.g. today or last edited date
		# make a default numbering object for comment numbering, containing only a serial number; likewise for associated texts
		self.DefaultCommentNumbering = core_classes.NumberingItem()
		self.DefaultCommentNumbering.NumberStructure = [core_classes.SerialNumberChunkItem()]
		self.DefaultAssociatedTextNumbering = core_classes.NumberingItem()
		self.DefaultAssociatedTextNumbering.NumberStructure = [core_classes.SerialNumberChunkItem()]
		self.ActionItems = [] # list of AssociatedText instances for entire project
		self.ParkingLotItems = [] # list of AssociatedText instances

		# Attributes saved in actual project file
		self.VizopVersion = CurrentProjDocType # str; Vizop Version
		self.ShortTitle = 'CHAZOP of gas treatment plant'  # project short title for display
		self.ProjNumber = 141688 # int; user's project reference number
		self.Description = 'A great excuse to spend 4 weeks in Seoul'  # longer description of project
		self.EditNumber = 0 # int; incremented every time the project's dataset is changed
		self.TeamMembers = [core_classes.TeamMember(1, 'Amy Stone', 'Consultant','Amy'),
			core_classes.TeamMember(2, 'Ben Smith', 'Project Manager','Ben')] # list of team members
		self.RiskMatrices = [core_classes.LookupTableItem()] # list of risk matrix

	def GetNewID(self):
		# get and return ID for new object in self (str). This should be called only for datacore-side project instances
		assert isinstance(self.MaxIDInProj, int)
		self.MaxIDInProj += 1
		return str(self.MaxIDInProj)

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

	def AssignDefaultNameToPHAObj(self, PHAObj): # assigns a default HumanName to PHAObj
		# The default name is e.g. "Fault Tree", then the date in YYYYMMMDD, then '-' and a serial number
		assert isinstance(PHAObj, core_classes.PHAModelBaseClass)
		HumanNameStub = type(PHAObj).HumanName + ' ' + datetime.date.today().strftime('%Y%b%d') + '-'
		SkipLength = len(utilities.StripSpaces(HumanNameStub))
		# check if any other PHA objects in this project have the same HumanNameStub (ignoring spaces).
		# If so, find the highest among their serial suffixes
		HighestSuffix = max([utilities.str2int(utilities.StripSpaces(p.HumanName)[SkipLength:]) for p in self.PHAObjs ]
			+ [0])
		# assign HumanName to PHAObj
		PHAObj.HumanName = HumanNameStub + str(HighestSuffix + 1)

	def AssignDefaultNameToViewport(self, Viewport): # assigns a default HumanName to Viewport
		# FIXME this should be a datacore-side function; currently called on client side
		# The default name is the parent PHA object e.g. "Fault Tree", then "View", then '-' and a serial number
		assert isinstance(Viewport, display_utilities.ViewportBaseClass)
		ParentPHAObjID = Viewport.PHAObjID
		HumanNameStub = type(Viewport).HumanName + '-'
		SkipLength = len(utilities.StripSpaces(HumanNameStub))
		# check if any other Viewports in this PHA object have the same HumanNameStub (ignoring spaces).
		# If so, find the highest among their serial suffixes
		HighestSuffix = max([utilities.str2int(utilities.StripSpaces(v.HumanName)[SkipLength:])
			for v in self.ActiveViewports if v.PHAObjID == ParentPHAObjID] + [0])
		# assign HumanName to Viewport
		Viewport.HumanName = HumanNameStub + str(HighestSuffix + 1)

	def WalkOverAllPHAElements(self):
		# a generator yielding PHA elements from all PHA models in the project. For datacore or display version of FT
		for ThisPHAObj in self.PHAObjs:
			for ThisPHAElement in ThisPHAObj.WalkOverAllElements():
				yield ThisPHAElement
		return

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

def SaveEntireProjectRequest(Parent=None, event=None):
	# save entire project
	# variables and methods for testing purpose

	test_OutputPath = './test_projectfile/'
	test_OutputFileName = 'test_OutputXML.xml'

	Proj = CreateProject()
	SaveEntireProject(Proj, test_OutputPath + test_OutputFileName)
	pass

def SaveEntireProject(Proj: ProjectItem, OutputFilename, ProblemReport='', Close=False):
	# Create a new file with OutputFilename (full path).
	# Write the entire data from Proj into it.
	# Append any problems to input arg ProblemReport.
	# If Close, close the file after writing.
	# Return: WriteOK (bool) - whether file written successfully;
	#         ProblemReport (str) - human readable description of any problem encountered.
	assert type(Proj) == ProjectItem
	assert type(OutputFilename) == str

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
	assert type(Proj) == ProjectItem
	assert type(ProjFilename) == str

	try:
		vizop_parser.convertProjectToXml(Proj, ProjFilename)
		ProblemReport = ''
	except Exception as e:
		ProblemReport = e
		return False, ProblemReport

	return True, ProblemReport
	# TODO items to include: core_classes.ConstantItem.AllConstants

def SetupDefaultTolRiskModel(Proj):
	# set up a default tolerable risk model (severity categories) in project instance Proj
	# Make risk receptors
	PeopleRiskReceptor = core_classes.RiskReceptorItem(XMLName='People', HumanName=_('People'))
	EnvironmentRiskReceptor = core_classes.RiskReceptorItem(XMLName='Environment', HumanName=_('Environment'))
	AssetsRiskReceptor = core_classes.RiskReceptorItem(XMLName='Assets', HumanName=_('Assets'))
	ReputationRiskReceptor = core_classes.RiskReceptorItem(XMLName='Reputation', HumanName=_('Reputation'))
	# make a tolerable risk model object; populate it with risk receptors
	TolRiskModel = core_classes.TolRiskFCatItem(Proj)
	TolRiskModel.HumanName = 'Company X default risk matrix'
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

def GetAllNumberingSystems(Proj):
	# returns list of lists. Each inner list represents one unique numbering system in the entire project.
	# Each inner list contains all project objects using that numbering system.
	# Example: NumberSystem1 is used by Gate1 and Gate2; Numbersystem2 is used by FTEvent1 and FTEvent2.
	# The returned list will be: [ [Gate1, Gate2] , [FTEvent1, FTEvent2] ]
	assert isinstance(Proj, ProjectItem)
	NumSystems = [] # a list of all unique number systems found
	NumSystemsUsageLists = [] # list of lists of PHA objects, for return
	# iterate over all PHA objects that contain number systems
	for ThisPHAObj in Proj.PHAObjs:
		for ThisElement in ThisPHAObj.GetAllObjsWithNumberSystems():
			ThisNumSystem = ThisElement.Numbering
			# check for a matching number system in NumSystems (can't just use 'in' as they are different objects)
			MatchFound = False
			for (ThisIndex, ExistingNumSystem) in enumerate(NumSystems):
				if ThisNumSystem == ExistingNumSystem: # found a match; add the PHA object to the usage list
					NumSystemsUsageLists[ThisIndex].append(ThisElement)
					MatchFound = True
					break # don't search any more
			if not MatchFound: # no match; add it as a new numbering system
				NumSystems.append(ThisElement.Numbering)
				NumSystemsUsageLists.append( [ThisElement] )
	return NumSystemsUsageLists

del _ # remove dummy definition

"""[----------TESTING AREA---------- """

def runUnitTest():
	pass

""" ----------TESTING AREA----------]"""