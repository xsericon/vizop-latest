# -*- coding: utf-8 -*-
# Module: projects. This file is part of Vizop. Copyright xSeriCon, 2020

# standard modules needed:
import os, shutil, datetime, string, copy, wx
import os.path
import xml.etree.ElementTree as ElementTree
from platform import system

# vizop modules needed:
# from vizop_misc import IsReadableFile, IsWritableLocation, select_file_from_all, MakeXMLMessage, SocketWithName
import settings, core_classes, info, faulttree, utilities, display_utilities, undo, vizop_misc

"""
The projects module contains functions for handling entire Vizop projects, including project files.
Code for project-wide features like action items is also here.
"""

CurrentProjDocType = 'VizopProject0.1' # doc type written by this version of Vizop
HighestProjID = 0 # highest ID of all projects currently open (int)
def _(DummyArg): return DummyArg # dummy definition of _(); the real definition is elsewhere
	# TODO this won't translate for one-time calls when an object is created. Need a 'Translate' function in vizop_misc?

class ProcessUnit(object): # object representing an area of the plant, e.g. "gas dryer"

	def __init__(self, ID=None, Proj=None, UnitNumber='', ShortName='', LongName=''):
		object.__init__(self)
		assert (isinstance(ID, str) and ID != '') or (ID is None)
		assert isinstance(Proj, ProjectItem)
		assert isinstance(UnitNumber, str)
		assert isinstance(ShortName, str)
		assert isinstance(LongName, str)
		self.Proj = Proj
		# if ID is supplied (during reload from project file), reuse the ID provided, else fetch a new ID
		if ID is None:
			Proj.MaxIDInProj += 1
			self.ID = str(Proj.MaxIDInProj)
		else: self.ID = ID
		self.UnitNumber = UnitNumber
		self.ShortName = ShortName
		setattr(self, info.LongNameAttribName, LongName)

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
		setattr(self, info.LongNameAttribName, LongName)

class ProjectFontItem(object): # virtual fonts for use with texts in PHA objects
			# To get actual face name (str) of a wx.Font, use font.GetFaceName()

	def __init__(self, HumanName=_('<undefined>'), RealFace=''):
		object.__init__(self)
		self.HumanName = HumanName
		self.RealFace = RealFace # actual face name of font associated with this instance

DefaultProjectFontItem = ProjectFontItem(_('<System default>'), '')

class ProjectItem(object): # class of PHA project instances
	# below: attrib lists containing project-level objects with numbering
	ListsOfObjsWithNumbering = ['ActionItems', 'ParkingLot']

	def __init__(self, ID): # ID (int): unique ID to assign to ProjectItem instance
		assert isinstance(ID, int)
		object.__init__(self)
		self.ID = str(ID)
		self.EditAllowed = True # whether user can edit project in this Vizop instance. Eventually, this will be related to
			# (1) whether license valid, and (2) whether this Vizop instance is in 'master' mode
		self.Fonts, self.SystemFontNames = SetupFonts() # ideally this would be global, not per project
		self.MaxIDInProj = 0 # (int) highest ID of all objects in the project
		self.PHAObjs = [] # list of PHA objects existing locally, in order created; empty if datacore is remote
		self.PHAObjShadows = [] # list of info about PHA objects; used by control frame, as the project datacore may be
			# remote, so it may not have access to self.PHAObjs; same order as self.PHAObjs
		self.ClientViewports = [] # list of all actual Viewports (not Viewport shadows) in this Vizop instance,
			# whether visible or not. Client side attrib.
		self.AllViewportShadows = [] # list of all Viewport shadows (belonging to datacore)
		self.ViewportsWithoutPHAObjs = [] # datacore: any Viewport instances that don't belong to PHA objects (e.g. action item view)
#		self.ArchivedViewportShadows = [] # datacore: Viewport shadows created and subsequently deleted; retained to
#		# allow retrieval of persistent attribs. Need not be stored in project file. This attrib is no longer used.
		self.IPLKinds = []
		self.CauseKinds = []
		# instances of RiskReceptorItem defined for this project. This is temporary; currently it gets overwritten in
		# SetupDefaultTolRiskModel()
#		self.RiskReceptors = [core_classes.RiskReceptorItem(ID='DefaultNewProj', XMLName='People', HumanName=_('People'))]
		self.RiskReceptors = []
		self.NumberSystems = [core_classes.SerialNumberChunkItem()] # instances of NumberSystemItem. Not used;
			# to get number systems, call GetAllNumberingSystems()
		self.CurrentTolRiskModel = None
		self.Constants = [] # instances of ConstantItem
		# the following is for testing
		TestConstant = core_classes.ConstantItem(HumanName='Alarm failure', ID=self.GetNewID())
		TestConstant.Value.SetMyValue(0.1)
		TestConstant.Value.SetMyUnit(core_classes.ProbabilityUnit)
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
		self.MilestonesForUndo = [] # list of MilestoneItem instances for reverting display when undoing.
			# This is a client-side list in the project shadow, because milestones act on Viewports
			# (whereas undo objects are on datacore side)
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
		self.ATExportFilename = '' # str; last used full pathname for exporting associated texts, including extension
		# make a default numbering object for comment numbering, containing only a serial number; likewise for associated texts
		self.ATExportShowWhat = 'Header,EditNumber,ATs'
		self.ATExportPaperOrientation = info.PortraitLabel
		self.DefaultCommentNumbering = core_classes.NumberingItem()
		self.DefaultCommentNumbering.NumberStructure = [core_classes.SerialNumberChunkItem()]
		self.DefaultAssociatedTextNumbering = core_classes.NumberingItem()
		self.DefaultAssociatedTextNumbering.NumberStructure = [core_classes.SerialNumberChunkItem()]
		self.ActionItems = [] # list of AssociatedText instances for entire project
		self.ParkingLot = [] # list of AssociatedText instances

		# Attributes saved in project file
		self.VizopVersion = CurrentProjDocType # str; Vizop Version
		self.ShortTitle = 'CHAZOP of gas treatment plant' # project short title for display
		self.ProjNumber = '141688' # str; user's project reference number
		self.Description = 'Gas Desulfurization Upgrade Project, Seoul' # longer description of project
		self.EditNumber = 0 # int; incremented every time the project's dataset is changed
		self.TeamMembers = [core_classes.TeamMember('101', 'Amy Stone', 'Consultant','ABC Consultants'),
			core_classes.TeamMember('102', 'Ben Smith', 'Project Manager','BigChemCo')] # list of team members
		self.RiskMatrices = [] # list of LookupTableItem instances

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
		# Client side method
		# The default name is the parent PHA object e.g. "Fault Tree", then "View", then '-' and a serial number
		assert isinstance(Viewport, display_utilities.ViewportBaseClass)
		ParentPHAObjID = Viewport.PHAObjID
		HumanNameStub = type(Viewport).HumanName + '-'
		SkipLength = len(utilities.StripSpaces(HumanNameStub))
		# check if any other Viewports in this PHA object have the same HumanNameStub (ignoring spaces).
		# If so, find the highest among their serial suffixes
		HighestSuffix = max([utilities.str2int(utilities.StripSpaces(v.HumanName)[SkipLength:])
			for v in self.ClientViewports if v.PHAObjID == ParentPHAObjID] + [0])
		# assign HumanName to Viewport
		Viewport.HumanName = HumanNameStub + str(HighestSuffix + 1)

	def WalkOverAllPHAElements(self):
		# a generator yielding PHA elements from all PHA models in the project. For datacore or display version of FT
		for ThisPHAObj in self.PHAObjs:
			for ThisPHAElement in ThisPHAObj.WalkOverAllElements():
				yield ThisPHAElement
		return

	def GetMostRecentMilestoneWithSelectedElements(self):
		# search through backward history to find most recent Milestone containing a Viewport with selected elements
		# This will skip over Viewports with "selectable" elements if no elements were actually selected
		# Returns the milestone found, or None if no suitable milestone found
		ThisMilestoneIndex = len(self.BackwardHistory) - 1
		MilestoneFound = None
		while (ThisMilestoneIndex >= 0) and (MilestoneFound is None):
			ThisMilestone = self.BackwardHistory[ThisMilestoneIndex]
			if ThisMilestone.ViewportData.get('SelectedElementIDs', []):
				MilestoneFound = ThisMilestone
			ThisMilestoneIndex -= 1
		return MilestoneFound

	def AddExistingAssociatedTextsToElements(self, XMLRoot):
		# add ATs to elements in the project.
		# XMLRoot will contain tags:
		#	PHAObjID: ID PHA object containing target elements
		#	PHAElementIDs: Comma-separated list of target element IDs
		#	AssociatedTextIDs: Comma-separated list of IDs of existing ATs (action items or parking lot items)
		#	info.ViewportTag: ID of Viewport that raised the request (for undo)
		# returns reply message
		TargetPHAObj = utilities.ObjectWithID(self.PHAObjs, TargetID=XMLRoot.findtext(info.PHAObjTag))
		AllElementsInPHAObj = [e for e in TargetPHAObj.WalkOverAllElements()]
		TargetElements = [utilities.ObjectWithID(AllElementsInPHAObj, TargetID=ThisID)
			for ThisID in XMLRoot.findtext(info.PHAElementTag).replace(',', ' ').split()]
		ATKind = XMLRoot.findtext(info.AssociatedTextKindTag)
		ATListName = 'ActionItems' if ATKind == info.ActionItemLabel else 'ParkingLot'
		TargetATs = [utilities.ObjectWithID(getattr(self, ATListName), TargetID=ThisID)
			for ThisID in XMLRoot.findtext(info.AssociatedTextIDTag).replace(',', ' ').split()]
		# add undo record
		undo.AddToUndoList(Proj=self, Redoing=False,
			UndoObj=undo.UndoItem(UndoHandler=self.AddExistingAssociatedTextsToElements_Undo,
			RedoHandler=self.AddExistingAssociatedTextsToElements_Redo,
			MilestoneID=XMLRoot.findtext(info.MilestoneIDTag),
			PHAObj=TargetPHAObj, PHAElements=TargetElements, ATs=TargetATs, ATListName=ATListName,
			HumanText=_('add %s to element(s)' % core_classes.AssociatedTextEnglishNamesPlural[ATKind]),
			ViewportID=XMLRoot.findtext(info.ViewportTag)))
		# add the ATs to the elements
		for ThisEl in TargetElements:
			for ThisAT in TargetATs:
				TargetATList = getattr(ThisEl, ATListName, None)
				if TargetATList: # can this element support this kind of AT?
					if not (ThisAT in TargetATList): # is the AT not already in the element?
						TargetATList.append(ThisAT) # attach the AT to the element
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')
		# TODO: add save on fly

	def AddExistingAssociatedTextsToElements_Undo(self, Proj, UndoRecord, **Args):
		assert isinstance(Proj, ProjectItem)
		assert isinstance(UndoRecord, undo.UndoItem)
		# find out which datacore socket to send messages on
		SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
		# remove the ATs added to the elements
		for ThisPHAElement in [e for e in UndoRecord.PHAObj.WalkOverAllElements() if e in UndoRecord.PHAElements]:
			for ThisAT in UndoRecord.ATs:
				getattr(ThisPHAElement, UndoRecord.ATListName).remove(ThisAT)
		# request Control Frame to switch to the milestone that was visible when the original edit was made, and refresh
		# all other visible Viewports
#		RedrawDataXML = cls.GetFullRedrawData(Proj=Proj) # not sure if needed here
		MsgToControlFrame = ElementTree.Element(info.NO_RedrawAfterUndo)
		ProjTag = ElementTree.Element(info.ProjIDTag)
		ProjTag.text = self.ID
		# add a ViewportID tag to the message, so that Control Frame knows which Viewport to redraw
		ViewportTag = ElementTree.Element(info.ViewportTag)
		ViewportTag.text = UndoRecord.ViewportID
		# add a milestoneID tag
		MilestoneTag = ElementTree.Element(info.MilestoneIDTag)
		MilestoneTag.text = UndoRecord.MilestoneID
		MsgToControlFrame.append(ViewportTag)
		MsgToControlFrame.append(MilestoneTag)
		MsgToControlFrame.append(ProjTag)
#		MsgToControlFrame.append(RedrawDataXML)
		# Refresh this and all other visible Viewports, using controlframe.UpdateAllViewports()
		vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket, Command=info.NO_RedrawAfterUndo,
							   XMLRoot=MsgToControlFrame)
#		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.FTTag,
#			Elements={info.IDTag: self.ID, info.ComponentHostIDTag: UndoRecord.ComponentHost.ID}))
		# TODO add required data to the Save On Fly data
		return {'Success': True}

	def AddExistingAssociatedTextsToElements_Redo(self, Proj, RedoRecord, **Args):
		print('PR266 in redo handler')

	def FindViewportOfClass_Client(self, TargetClass=None, MatchAttribs={}):
		# client side method
		# check whether client-side project contains a Viewport of class TargetClass, with its UniqueAttribs matching
		# values provided in MatchAttribs. (Any extra attribs in MatchAttribs are ignored)
		# return matching Viewport instance, or None if none found
		assert issubclass(TargetClass, display_utilities.ViewportBaseClass)
		assert isinstance(MatchAttribs, dict)
		assert all([isinstance(k, str) for k in MatchAttribs.keys()])
		MatchingViewport = None
		for ThisViewport in self.ClientViewports:
			if isinstance(ThisViewport, TargetClass):
				# check match for any attribs in UniqueAttribs
				# check every attrib in ThisViewport's UniqueAttribs matches value supplied in MatchAttribs,
				# ignoring any attribs missing from MatchAttribs
				if all([(getattr(ThisViewport, k) == MatchAttribs.get(k, None)) or \
				   (k not in MatchAttribs.keys()) for k in getattr(ThisViewport, 'UniqueAttribs', [])]):
					MatchingViewport = ThisViewport
					break
		return MatchingViewport

	def GetAllObjsWithNumberSystems(self):
		# generator returning all project-level objects containing a numbering item.
		for ThisAttribName in self.ListsOfObjsWithNumbering:
			for ThisObj in getattr(self, ThisAttribName):
				yield ThisObj

	def ConvertProjectToXML(self):
		# convert project to XML. Return an ElementTree object containing all elements of the XML tree

		def MakeStructuredElement(StartEl, SubElTag, DataObj, SubElements):
			# make a subelement of StartEl (XML element) with tag = SubElTag (str).
			# Populate it with its own subelements based on DataObj (an object from which values are obtained)
			# based on SubElements (dict with keys = subelement tags, values = attrib names in DataObj)
			# Attrib values in DataObj can be str or bool. If bool, they are converted to 'True' or 'False'
			# return the top-level subelement
			assert isinstance(StartEl, ElementTree.Element)
			assert isinstance(SubElTag, str)
			assert SubElTag.strip() # ensure not empty string
			assert isinstance(SubElements, dict)
			TopEl = ElementTree.SubElement(StartEl, SubElTag)
			for ThisTag, ThisAttribName in SubElements.items():
				SubEl = ElementTree.SubElement(TopEl, ThisTag)
				AttribType = type(getattr(DataObj, ThisAttribName))
				if AttribType is str:
					SubEl.text = LegalString(InStr=str(getattr(DataObj, ThisAttribName)))
				elif AttribType is bool:
					SubEl.text = utilities.Bool2Str(Input=getattr(DataObj, ThisAttribName), TrueStr='True',
						FalseStr='False')
				else:
					raise TypeError('Supplied attrib with type %s' % AttribType)
			return TopEl

		def AddProjectInformationTags(XMLRoot):
			# add project information tags to XMLRoot
			ShortTitleElement = ElementTree.SubElement(XMLRoot, info.ShortTitleTag)
			ShortTitleElement.text = LegalString(InStr=self.ShortTitle)
			ProjNumberElement = ElementTree.SubElement(XMLRoot, info.ProjNumberTag)
			ProjNumberElement.text = LegalString(InStr=self.ProjNumber)
			ProjDescriptionElement = ElementTree.SubElement(XMLRoot, info.DescriptionTag)
			ProjDescriptionElement.text = LegalString(InStr=self.Description)
			EditNumberElement = ElementTree.SubElement(XMLRoot, info.EditNumberTag)
			EditNumberElement.text = str(self.EditNumber)
			MaxIDElement = ElementTree.SubElement(XMLRoot, info.MaxIDTag)
			MaxIDElement.text = self.GetNewID()
			# add TeamMember tags
			TMTopElement = ElementTree.SubElement(XMLRoot, info.TeamMembersTag)
			for ThisTM in self.TeamMembers:
				TMElement = ElementTree.SubElement(TMTopElement, info.TeamMemberTag,
					attrib={info.IDTag: ThisTM.ID, info.NameTag: LegalString(InStr=ThisTM.Name),
					info.RoleTag: LegalString(InStr=ThisTM.Role),
					info.AffiliationTag: LegalString(InStr=ThisTM.Affiliation)})
				TMElement.text = ThisTM.ID

		def AddNumberingSystemTags(XMLRoot):
			# build a list of all unique numbering systems used in the project, and write numbering systems to XMLRoot
			AllNumberingSystems = GetAllNumberingSystems(Proj=self)
			# write a tag for each NS
			for ThisNSIndex, ThisNSElementList in enumerate(AllNumberingSystems):
				ThisNSElement = ElementTree.SubElement(XMLRoot, info.NumberSystemTag)
				# store an 'ID' for the NS = its index in AllNumberingSystems
				ThisIDTag = ElementTree.SubElement(ThisNSElement, info.IDTag)
				ThisIDTag.text = str(ThisNSIndex)
				# store tags for other NS-level attribs
				ThisNS = ThisNSElementList[0].Numbering # pick the NS from one of the elements in the list
				AddAttribsInSubelements(StartEl=ThisNSElement, DataObj=ThisNS,
					SubElements={info.ShowInDisplayTag: 'ShowInDisplay', info.ShowInOutputTag: 'ShowInOutput'})
				# store Chunk subelements for this NS
				for ThisChunk in ThisNS.NumberStructure:
					# make <Chunk> subelement
					ThisChunkTag = ElementTree.SubElement(ThisNSElement, info.NumberChunkTag)
					# add tag for the chunk kind
					ThisKindTag = ElementTree.SubElement(ThisChunkTag, info.NumberChunkKindTag)
					ThisKindTag.text = type(ThisChunk).XMLName
					# add specific XML tags for each chunk kind
					if ThisChunk.XMLName == info.NumberSystemStringType:
						ValueTag = ElementTree.SubElement(ThisChunkTag, info.ValueTag)
						ValueTag.text = LegalString(InStr=ThisChunk.Value)
					elif ThisChunk.XMLName == info.NumberSystemParentType:
						IDTag = ElementTree.SubElement(ThisChunkTag, info.IDTag)
						IDTag.text = ThisChunk.Source.ID
						LevelsTag = ElementTree.SubElement(ThisChunkTag, info.LevelsTag)
						LevelsTag.text = str(ThisChunk.HierarchyLevels)
					elif ThisChunk.XMLName == info.NumberSystemSerialType:
						AddAttribsInSubelements(StartEl=ThisChunkTag, DataObj=ThisChunk,
							SubElements={info.FieldWidthTag: 'FieldWidth', info.PadCharTag: 'PadChar',
							info.StartSequenceAtTag: 'StartSequenceAt', info.GapBeforeTag: 'GapBefore',
							info.IncludeInNumberingTag: 'IncludeInNumbering', info.NoValueTag: 'NoValue',
							info.SkipToTag: 'SkipTo'})
			return AllNumberingSystems

		def AddSimpleStructuredObjectTags(XMLRoot, NumberingSystemHash):
			# add tags for simple cases of structured objects: process units, risk receptors, constants, action items,
			# and parking lot items
			# SOInfo contains a tuple for some kinds of structured object:
			# Attrib name in project, XML tag,
			# SubElements (dict with keys = XML tags for individual attribs, values = attrib names)
			print('PR416 saving RRs with ID, HumanName: ', [(r.ID, r.HumanName) for r in self.RiskReceptors])
			SOInfo = [ ('ProcessUnits', info.ProcessUnitTag, {info.IDTag: info.IDAttribName,
				info.UnitNumberTag: info.UnitNumberAttribName,
				info.ShortNameTag: info.ShortNameAttribName, info.LongNameTag: info.LongNameAttribName} ),
				('RiskReceptors', info.RiskReceptorTag, {info.IDTag: info.IDAttribName,
				info.XMLNameTag: 'XMLName', info.HumanNameTag: 'HumanName'}) ]
			for ThisSOKindName, TagName, SubElements in SOInfo:
				for ThisSO in getattr(self, ThisSOKindName):
					ThisSOElement = MakeStructuredElement(StartEl=XMLRoot, SubElTag=TagName, DataObj=ThisSO,
						SubElements=SubElements)
			# add action items, with numbering tag
			for ThisActionItem in self.ActionItems:
				ThisATTag = ElementTree.SubElement(XMLRoot, info.ActionItemTag)
				AddAttribsInSubelements(StartEl=ThisATTag, DataObj=ThisActionItem,
					SubElements={info.IDTag: info.IDAttribName, 'Text': 'Content',
					info.ResponsibilityTag: 'Responsibility', info.DeadlineTag: 'Deadline',
					info.StatusTag: 'Status'})
				ThisNumberingTag = ElementTree.SubElement(ThisATTag, info.NumberingTag)
				ThisNumberingTag.text = str(NumberingSystemHash[ThisActionItem])
			# add parking lot items, with numbering tag
			for ThisParkingLotItem in self.ParkingLot:
				ThisATTag = ElementTree.SubElement(XMLRoot, info.ParkingLotItemTag)
				AddAttribsInSubelements(StartEl=ThisATTag, DataObj=ThisParkingLotItem,
					SubElements={info.IDTag: info.IDAttribName, 'Text': 'Content',
					info.ResponsibilityTag: 'Responsibility', info.DeadlineTag: 'Deadline',
					info.StatusTag: 'Status'})
				ThisNumberingTag = ElementTree.SubElement(ThisATTag, info.NumberingTag)
				ThisNumberingTag.text = str(NumberingSystemHash[ThisParkingLotItem])
			# add Constants
			for ThisConstant in self.Constants:
				ThisConstantTag = ElementTree.SubElement(XMLRoot, info.ConstantTag)
				# add ID and HumanName tag attribs
				ThisConstantTag.set(info.IDTag, getattr(ThisConstant, info.IDAttribName))
				ThisConstantTag.set(info.HumanTag, getattr(ThisConstant, 'HumanName'))
#				AddAttribsInSubelements(StartEl=ThisConstantTag, DataObj=ThisConstant,
#					SubElements={info.IDTag: info.IDAttribName, info.NameTag: 'HumanName'})
				print('PR451 storing a constant with RR id:', [r.ID for r in ThisConstant.Value.ValueFamily.keys()])
				AddValueElement(StartEl=ThisConstantTag, ValueTag=info.ValueTag, ValueObj=ThisConstant.Value)
			# add risk matrices
			for ThisMatrix in self.RiskMatrices:
				ThisMatrixTag = ElementTree.SubElement(XMLRoot, info.RiskMatrixTag)
				ThisMatrixIDTag = ElementTree.SubElement(ThisMatrixTag, info.IDTag)
				ThisMatrixIDTag.text = ThisMatrix.ID
				ThisMatrixNameTag = ElementTree.SubElement(ThisMatrixTag, info.HumanNameTag)
				ThisMatrixNameTag.text = ThisMatrix.HumanName
				# store categories
				for ThisDimensionCatList in ThisMatrix.Keys:
					for ThisCat in ThisDimensionCatList:
						MakeStructuredElement(StartEl=ThisMatrixTag, SubElTag=info.CategoryTag, DataObj=ThisCat,
							SubElements={info.XMLNameTag: 'XMLName', info.HumanNameTag: 'HumanName',
							info.DescriptionTag: 'HumanDescription'})
				# store severity dimension index
				SeverityDimIndexTag = ElementTree.SubElement(ThisMatrixTag, info.SeverityDimensionTag)
				SeverityDimIndexTag.text = info.NoneTag if ThisMatrix.SeverityDimensionIndex is None \
					else str(ThisMatrix.SeverityDimensionIndex)
				# store dimension names and the keys in each dimension
				for ThisDimensionIndex in range(ThisMatrix.HowManyDimensions):
					DimensionTag = ElementTree.SubElement(ThisMatrixTag, info.DimensionTag)
					NameTag = ElementTree.SubElement(DimensionTag, info.NameTag)
					NameTag.text = ThisMatrix.DimensionHumanNames[ThisDimensionIndex]
					UnitTag = ElementTree.SubElement(DimensionTag, info.UnitTag)
					UnitTag.text = ThisMatrix.DimensionUnits[ThisDimensionIndex].XMLName
					# store keys for this dimension
					for ThisKey in ThisMatrix.Keys[ThisDimensionIndex]:
						KeyTag = ElementTree.SubElement(DimensionTag, info.KeyTag)
						XMLNameTag = ElementTree.SubElement(KeyTag, info.XMLNameTag)
						XMLNameTag.text = ThisKey.XMLName
				# store values for the matrix
				for ThisValue in utilities.Flatten(ThisMatrix.Values):
					AddValueElement(StartEl=ThisMatrixTag, ValueTag=info.ValueTag, ValueObj=ThisValue)

		def AddPHAObjTags(XMLRoot, NumberingSystemHash):
			# add tags for each PHA object in the project. Return comment hash (dict):
			# Keys are comment IDs (str), values are comment texts (str)
			CommentHash = {}
			MaxCommentIDSoFar = 0
			for ThisPHAObj in self.PHAObjs:
				ThisPHAObjTag = ElementTree.SubElement(XMLRoot, info.PHAObjTag)
#				ThisKindTag = ElementTree.SubElement(ThisPHAObjTag, info.KindTag)
#				ThisKindTag.text = type(ThisPHAObj).InternalName
				ThisIDTag = ElementTree.SubElement(ThisPHAObjTag, info.IDTag)
				ThisIDTag.text = ThisPHAObj.ID
				# no need to add Kind tag here - it's done in individual PHA models' StoreAllDataInXML()
				# ask the PHA object to add all of its own data in ThisPHAObjTag, and return all comments found
				ThisCommentHash, MaxCommentIDSoFar = ThisPHAObj.StoreAllDataInXML(StartTag=ThisPHAObjTag,
					NumberingSystemHash=NumberingSystemHash, MaxCommentIDSoFar=MaxCommentIDSoFar)
				assert isinstance(ThisCommentHash, dict)
				assert isinstance(MaxCommentIDSoFar, int)
				CommentHash.update(ThisCommentHash)
			return CommentHash

		def AddViewportTags(XMLRoot):
			# add tags for each Viewport in the project
			for ThisViewport in self.AllViewportShadows: # not sure if we also need to look at self.ViewportsWithoutPHAObjs
				ThisViewportTag = ElementTree.SubElement(XMLRoot, info.ViewportTag)
#				ThisKindTag = ElementTree.SubElement(ThisViewportTag, info.KindTag)
#				ThisKindTag.text = ThisViewport.MyClass.InternalName
				ThisIDTag = ElementTree.SubElement(ThisViewportTag, info.IDTag)
				ThisIDTag.text = ThisViewport.ID
				# no need to add Kind tag here - it's done in StoreViewportCommonDataInXML()
				# add tag containing ID of any associated PHA object
				ThisPHAObjTag = ElementTree.SubElement(ThisViewportTag, info.PHAObjTag)
				ThisPHAObjTag.text = ThisViewport.PHAObjID if ThisViewport.PHAObjID else info.NoneTag
				# add tag indicating any display device currently showing this Viewport
				ThisDisplDeviceTag = ElementTree.SubElement(ThisViewportTag, info.DisplayDeviceTag)
				ThisDisplDeviceTag.text = info.NoneTag if ThisViewport.DisplDeviceID is None \
					else ThisViewport.DisplDeviceID
				# store persistent attribs subelement-tree (originally supplied from client-side Viewport)
				if ThisViewport.PersistentAttribs is not None:
					ThisPATag = ElementTree.SubElement(ThisViewportTag, info.PersistentAttribsTag)
					ThisPATag.append(ThisViewport.PersistentAttribs)

		def AddAssociatedTextTags(XMLRoot, NumberingSystemHash):
			# add tags for action items and parking lot
			for ThisATKindName, ThisATKindTag in [('ActionItems', info.ActionItemTag),
				('ParkingLot', info.ParkingLotItemTag)]:
				for ThisAT in getattr(self, ThisATKindName):
					ThisATTag =  ElementTree.SubElement(XMLRoot, ThisATKindTag)
					AddAttribsInSubelements(StartEl=ThisATTag, DataObj=ThisAT,
						SubElements={info.IDTag: 'ID', info.ContentTag: 'Content',
						info.ResponsibilityTag: info.ResponsibilityLabel, info.DeadlineTag: info.DeadlineLabel,
						info.StatusTag: info.StatusLabel})
					# add Numbering tag
					ThisNumberingTag = ElementTree.SubElement(ThisATTag, info.NumberingTag)
					ThisNumberingTag.text = NumberingSystemHash[ThisAT]

		# start of main procedure for ConvertProjectToXML()
		# First, create XML tree containing root XML element
		MyXMLRoot = ElementTree.Element(info.ProjectRootTag, attrib={info.VizopVersionTag: info.VERSION})
		MyXMLTree = ElementTree.ElementTree(element=MyXMLRoot)
		# add project information tags, including team members
		AddProjectInformationTags(XMLRoot=MyXMLRoot)
		# add numbering system tags, and obtain a list of lists of similarly-numbered objects in the entire project)
		NumberingSystems = AddNumberingSystemTags(XMLRoot=MyXMLRoot)
		# make a numbering system hash for all numbered objects in the project:
		# keys are objects, values are numbering system indices (stored as str, so they can go as-is into XML)
		NumberingSystemHash = {}
		for ThisIndex, ThisObjList in enumerate(NumberingSystems):
			NumberingSystemHash.update(dict([(ThisObj, str(ThisIndex)) for ThisObj in ThisObjList]))
		# add structured object tags for simple objects
		AddSimpleStructuredObjectTags(XMLRoot=MyXMLRoot, NumberingSystemHash=NumberingSystemHash)
		# add tags for each PHA object
		CommentHash = AddPHAObjTags(XMLRoot=MyXMLRoot, NumberingSystemHash=NumberingSystemHash)
		# add Viewport tags
		AddViewportTags(XMLRoot=MyXMLRoot)
		# add comment tags
		for (ThisCommentID, ThisCommentText) in CommentHash.items():
			ThisCommentTag = ElementTree.SubElement(MyXMLRoot, info.CommentTag)
			ThisCommentIDTag = ElementTree.SubElement(ThisCommentTag, info.IDTag)
			ThisCommentIDTag.text = ThisCommentID
			ThisCommentContentTag = ElementTree.SubElement(ThisCommentTag, info.ContentTag)
			ThisCommentContentTag.text = LegalString(InStr=ThisCommentText, Strip=True, FilterForbiddenChar=False)
		# add action item and parking lot tags
		AddAssociatedTextTags(XMLRoot=MyXMLRoot, NumberingSystemHash=NumberingSystemHash)
		return MyXMLTree

	def UnpackXMLToProject(self, MyXMLRoot):
		# fetch data from XML tree starting at MyXMLRoot (ElementTree.Element instance) and load it into project,
		# overwriting existing data

		def FetchAttribFromXML(XMLRoot, Tag, DestinationObj, AttribName, TypeConverter=str,
			DefaultIfNoTag='', DefaultIfTagEmpty=''):
			# find Tag as a top-level child of XMLRoot.
			# Put its text into attrib AttribName of object DestinationObj, converted by TypeConverter (callable)
			# Store default values DefaultIfNoTag or DefaultIfTagEmpty (can be any type) in AttribName if appropriate.
			assert isinstance(XMLRoot, ElementTree.Element)
			assert isinstance(Tag, str)
			assert Tag # ensure it's not blank
			assert isinstance(AttribName, str)
			assert AttribName
			assert callable(TypeConverter)
			TargetTag = XMLRoot.find(Tag)
			if TargetTag is None: setattr(DestinationObj, AttribName, DefaultIfNoTag)
			else:
				TextFound = TargetTag.text
				setattr(DestinationObj, AttribName, TypeConverter(TextFound) if TextFound else DefaultIfTagEmpty)

		def UnpackProjectInformation(XMLRoot):
			# fetch project information from XMLRoot
			FetchAttribFromXML(XMLRoot=XMLRoot, Tag=info.ShortTitleTag, DestinationObj=self, AttribName='ShortTitle')
			FetchAttribFromXML(XMLRoot=XMLRoot, Tag=info.ProjNumberTag, DestinationObj=self, AttribName='ProjNumber')
			FetchAttribFromXML(XMLRoot=XMLRoot, Tag=info.DescriptionTag, DestinationObj=self, AttribName='Description')
			FetchAttribFromXML(XMLRoot=XMLRoot, Tag=info.EditNumberTag, DestinationObj=self, AttribName='EditNumber',
				TypeConverter=utilities.str2int)
			FetchAttribFromXML(XMLRoot=XMLRoot, Tag=info.MaxIDTag, DestinationObj=self, AttribName='MaxIDInProj',
				TypeConverter=utilities.str2int)
			# fetch TeamMember data
			self.TeamMembers = []
			TMTopTag = XMLRoot.find(info.TeamMembersTag)
			if TMTopTag:
				for ThisTeamMemberTag in TMTopTag.findall(info.TeamMemberTag):
					# create team member instance, fetching ID, Name, Role and Affiliation attribs from tag
					NewTeamMember = core_classes.TeamMember(**ThisTeamMemberTag.attrib)
					# TODO create problem message and/or delete the new team member if ID is blank or not unique
					self.TeamMembers.append(NewTeamMember)
			return [] # no problem reports defined yet

		def FetchNumberingSystemTags(XMLRoot):
			# fetch all unique numbering systems from XMLRoot, and return them in an ordered list
			# We assume the order in the XML file matches the "ID" stored in each numbering system tag, and we don't
			# pay attention to the actual ID (TODO it would be better to use ID rather than order)
			assert isinstance(XMLRoot, ElementTree.Element)
			NumberChunkKinds = dict( (k.XMLName, k) for k in core_classes.NumberChunkTypes )
			NumberingSystems = []
			ProblemReports = []
			ParentNumberChunks = []
			for ThisNSTag in XMLRoot.findall(info.NumberSystemTag):
				NewNS = core_classes.NumberingItem()
				NumberingSystems.append(NewNS)
				# fetch NS-level attribs
				FetchAttribFromXML(XMLRoot=ThisNSTag, Tag=info.ShowInDisplayTag, DestinationObj=NewNS,
					AttribName='ShowInDisplay', TypeConverter=utilities.str_to_bool)
				FetchAttribFromXML(XMLRoot=ThisNSTag, Tag=info.ShowInOutputTag, DestinationObj=NewNS,
					AttribName='ShowInOutput', TypeConverter=utilities.str_to_bool)
				# fetch number chunks
				for ThisChunkTag in ThisNSTag.findall(info.NumberChunkTag):
					# find out chunk kind
					ThisKind = ThisChunkTag.findtext(info.NumberChunkKindTag)
					if ThisKind in NumberChunkKinds.keys(): # valid kind found; TODO make problem message if not
						ThisChunk = NumberChunkKinds[ThisKind]()
						NewNS.NumberStructure.append(ThisChunk)
						# fetch specific attribs for each chunk kind
						if ThisKind == info.NumberSystemStringType:
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.ValueTag, DestinationObj=ThisChunk,
								AttribName='Value')
						elif ThisKind == info.NumberSystemParentType:
							# fetch ID of parent numbering object. Later, we'll reconnect it to the actual object
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.IDTag, DestinationObj=ThisChunk,
								AttribName='SourceID')
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.LevelsTag, DestinationObj=ThisChunk,
								AttribName='HierarchyLevels', TypeConverter=utilities.str2int)
							ParentNumberChunks.append(ThisChunk) # store chunk for reconnecting later
						elif ThisKind == info.NumberSystemSerialType:
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.FieldWidthTag, DestinationObj=ThisChunk,
								AttribName='FieldWidth', TypeConverter=utilities.str2int)
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.PadCharTag, DestinationObj=ThisChunk,
								AttribName='PadChar')
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.StartSequenceAtTag, DestinationObj=ThisChunk,
								AttribName='StartSequenceAt', TypeConverter=utilities.str2int)
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.GapBeforeTag, DestinationObj=ThisChunk,
								AttribName='GapBefore', TypeConverter=utilities.str2int)
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.IncludeInNumberingTag, DestinationObj=ThisChunk,
								AttribName='IncludeInNumbering', TypeConverter=utilities.str_to_bool)
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.NoValueTag, DestinationObj=ThisChunk,
								AttribName='NoValue')
							FetchAttribFromXML(XMLRoot=ThisChunkTag, Tag=info.SkipToTag, DestinationObj=ThisChunk,
								AttribName='SkipTo',
								TypeConverter=lambda s: utilities.str2int(s, MeaninglessValue=None))
			return NumberingSystems, ProblemReports, ParentNumberChunks

		def FetchCommentTags(XMLRoot):
			# fetch all comments from XMLRoot, and return them in a hash:
			# keys are comment IDs, values are comment objects
			# also return ProblemReports (list of ProblemReportItem instances)
			assert isinstance(XMLRoot, ElementTree.Element)
			CommentHash = {}
			ProblemReports = []
			for ThisCommentTag in XMLRoot.findall(info.CommentTag):
				NewComment = core_classes.AssociatedTextItem(Proj=self)
				# fetch comment ID and content
				ThisCommentID = ThisCommentTag.findtext(info.IDTag)
				FetchAttribFromXML(XMLRoot=ThisCommentTag, Tag=info.ContentTag, DestinationObj=NewComment,
					AttribName='Content')
				# add comment to hash
				CommentHash[ThisCommentID] = NewComment
			return CommentHash, ProblemReports
			# TODO confirm comment IDs are unique, and comment contents are nonblank

		def FetchAssociatedTexts(XMLRoot, NumberingSystems):
			# fetch all associated texts (action items and parking lot items) from XMLRoot, and return them in a hash:
			# keys are AT IDs, values are AT objects
			# also return ProblemReports (list of ProblemReportItem instances)
			assert isinstance(XMLRoot, ElementTree.Element)
			assert isinstance(NumberingSystems, list)
			self.ActionItems = [] # clear project's lists of ATs
			self.ParkingLot = []
			MyActionItems = {} # used for hash to attach ATs to host objects later
			MyParkingLotItems = {}
			ProblemReports = []
			for ThisATKindTag, ThisATHash, ProjLevelList in [(info.ActionItemTag, MyActionItems, self.ActionItems),
				(info.ParkingLotItemTag, MyParkingLotItems, self.ParkingLot)]:
				for ThisATInstanceTag in XMLRoot.findall(ThisATKindTag):
					NewAT = core_classes.AssociatedTextItem(Proj=self)
					# fetch AT attribs
					FetchAttribFromXML(XMLRoot=ThisATInstanceTag, Tag=info.IDTag, DestinationObj=NewAT,
						AttribName='ID')
					FetchAttribFromXML(XMLRoot=ThisATInstanceTag, Tag=info.ContentTag, DestinationObj=NewAT,
						AttribName='Content')
					FetchAttribFromXML(XMLRoot=ThisATInstanceTag, Tag=info.ResponsibilityTag, DestinationObj=NewAT,
						AttribName='Responsibility')
					FetchAttribFromXML(XMLRoot=ThisATInstanceTag, Tag=info.DeadlineTag, DestinationObj=NewAT,
						AttribName='Deadline')
					FetchAttribFromXML(XMLRoot=ThisATInstanceTag, Tag=info.StatusTag, DestinationObj=NewAT,
						AttribName='Status')
					# attach numbering item to AT
					# TODO check numbering provided is an integer in range(len(NumberingSystems))
					NewAT.Numbering = copy.copy(NumberingSystems[int(ThisATInstanceTag.findtext(info.NumberingTag))])
					# add AT to hash. TODO confirm IDs are unique and nonblank
					ThisATHash[NewAT.ID] = NewAT
					# add AT to project's list
					ProjLevelList.append(NewAT)
			return MyActionItems, MyParkingLotItems, ProblemReports

		def FetchSimpleStructuredObjectTags(XMLRoot, NumberingSystems):
			# unpack structured object data from XMLRoot into project for objects:
			# process units, risk receptors, constants, and risk matrices
			# return ProblemReports (list of ProblemReportItem instances) and ParentNumValueInstances (list)
			# first, unpack process units
			ProblemReports = []
			ParentNumValueInstances = []
			self.ProcessUnits = []
			for ThisProcessUnitTag in XMLRoot.findall(info.ProcessUnitTag):
				PUID = ThisProcessUnitTag.findtext(info.IDTag)
				# TODO ensure ID is unique and nonblank
				PUUnitNumber = ThisProcessUnitTag.findtext(info.UnitNumberTag)
				PUShortName = ThisProcessUnitTag.findtext(info.ShortNameTag)
				PULongName = ThisProcessUnitTag.findtext(info.LongNameTag)
				self.ProcessUnits.append(ProcessUnit(Proj=self, ID=PUID, UnitNumber=PUUnitNumber, ShortName=PUShortName,
					LongName=PULongName))
			# unpack risk receptors
			self.RiskReceptors = []
			for ThisRRTag in XMLRoot.findall(info.RiskReceptorTag):
				RRID = ThisRRTag.findtext(info.IDTag)
				# TODO ensure ID is unique and nonblank
				RRXMLName = ThisRRTag.findtext(info.XMLNameTag)
				RRHumanName = ThisRRTag.findtext(info.HumanNameTag)
				self.RiskReceptors.append(core_classes.RiskReceptorItem(ID=RRID, XMLName=RRXMLName, HumanName=RRHumanName))
			# unpack Constants
			self.Constants = []
			for ThisConstantTag in XMLRoot.findall(info.ConstantTag):
				# make new constant, applying ID and HumanName attribs from XML tag
				NewConstant = core_classes.ConstantItem(**ThisConstantTag.attrib)
				self.Constants.append(NewConstant)
				NewConstant.Value, NewProblemReports, NewParentNumValueInstances = UnpackValueFromXML(Proj=self,
					XMLEl=ThisConstantTag.find(info.ValueTag))
				ProblemReports.extend(NewProblemReports)
				ParentNumValueInstances.extend(NewParentNumValueInstances)
			# add risk matrices
			self.RiskMatrices = []
			for ThisMatrixTag in XMLRoot.findall(info.RiskMatrixTag):
				NewMatrix = core_classes.LookupTableItem(ID=ThisMatrixTag.findtext(info.IDTag))
				self.RiskMatrices.append(NewMatrix)
				# fetch HumanName
				NewMatrix.HumanName = ThisMatrixTag.findtext(info.HumanNameTag)
				# fetch severity dimension index
				SeverityDimIndexText = ThisMatrixTag.findtext(info.SeverityDimensionTag)
				NewMatrix.SeverityDimensionIndex = None if SeverityDimIndexText == info.NoneTag \
					else utilities.str2int(s=SeverityDimIndexText)
				# fetch dimensions
				for ThisDimensionTag in ThisMatrixTag.findall(info.DimensionTag):
					# fetch dimension name and unit
					NewMatrix.DimensionHumanNames.append(ThisDimensionTag.findtext(info.NameTag))
					NewMatrix.DimensionUnits.append(utilities.InstanceWithAttribValue(
						ObjList=core_classes.AllSelectableUnits, AttribName='XMLName',
						TargetValue=ThisDimensionTag.findtext(info.UnitTag)))
				# fetch all categories across all dimensions
				AllCategories = []
				for ThisCategoryTag in ThisMatrixTag.findall(info.CategoryTag):
					AllCategories.append(core_classes.CategoryNameItem(XMLName=ThisCategoryTag.findtext(info.XMLNameTag),
						HumanName=ThisCategoryTag.findtext(info.HumanNameTag),
						HumanDescription=ThisCategoryTag.findtext(info.DescriptionTag)))
				# split categories into sublists per dimension. FIXME not correct; length of each sublist should
				# not be equal, but should reflect the number of categories in each dimension
				NewMatrix.Keys = utilities.SplitList(InList=AllCategories,
					HowManySublists=len(NewMatrix.DimensionHumanNames))
				# restore HowManyDimensions
				NewMatrix.HowManyDimensions = len(NewMatrix.DimensionHumanNames)
				# fetch all values for the matrix
				AllValues = []
				for ThisValueTag in ThisMatrixTag.findall(info.EntryTag):
					NewValue, NewProblemReports, NewParentNumValueInstances = UnpackValueFromXML(Proj=self,
						XMLEl=ThisValueTag)
					AllValues.append(NewValue)
					ProblemReports.extend(NewProblemReports)
					ParentNumValueInstances.extend(NewParentNumValueInstances)
				# split values into nested sublists for matrix's Values attrib, but no split for the last dimension
				if NewMatrix.HowManyDimensions == 1: NewMatrix.Values = AllValues
				else: NewMatrix.Values = utilities.SplitListNested(InList=AllValues,
					HowManySublistsPerLevel=[len(d) for d in NewMatrix.Keys[:-1]])
			return ProblemReports, ParentNumValueInstances

		def FetchPHAObjTags(XMLRoot, NumberingSystems, Comments, ActionItems, ParkingLotItems):
			# find PHAObj tags in XMLRoot and request respective PHA model class to unpack the data from them
			assert isinstance(XMLRoot, ElementTree.Element)
			ProblemReports = []
			ParentNumValueInstances = []
			ElementHash = {}
			for ThisPHAObjTag in XMLRoot.findall(info.PHAObjTag):
				# fetch PHA object's kind, and find PHA model class from kind
				ThisKind = ThisPHAObjTag.findtext(info.KindTag)
				ThisPHAObjClass = utilities.InstanceWithAttribValue(
					ObjList=core_classes.PHAModelMetaClass.PHAModelClasses, AttribName='InternalName',
					TargetValue=ThisKind, NotFoundValue=None)
				# make the new PHA object, using its previous ID
				NewPHAObj = self.CreatePHAObj(PHAModelClass=ThisPHAObjClass, ID=ThisPHAObjTag.findtext(info.IDTag))
				# get the new PHA object to populate itself from the XML data
				NewProblemReports, NewParentNumValueInstances, NewElementHash = NewPHAObj.FetchAllDataFromXML(Proj=self,
					StartTag=ThisPHAObjTag, NumberingSystems=NumberingSystems,
					Comments=Comments, ActionItems=ActionItems, ParkingLotItems=ParkingLotItems)
				ProblemReports.extend(NewProblemReports)
				ParentNumValueInstances.extend(NewParentNumValueInstances)
				ElementHash.update(NewElementHash)
			return ProblemReports, ParentNumValueInstances, ElementHash

		def FetchViewportData(XMLRoot):
			# find Viewport tags in XMLRoot and unpack the data into new Viewport shadows
			assert isinstance(XMLRoot, ElementTree.Element)
			ProblemReports = []
			# create and populate a Viewport shadow for each Viewport tag in XMLRoot
			for ThisViewportTag in XMLRoot.findall(info.ViewportTag):
				# fetch Viewport's kind
				ThisKind = ThisViewportTag.findtext(info.KindTag)
				# fetch any associated PHA object
				ThisPHAObjIDInXML = ThisViewportTag.findtext(info.PHAObjTag)
				ThisPHAObj = None if ThisPHAObjIDInXML == info.NoneTag else utilities.ObjectWithID(Objects=self.PHAObjs,
					TargetID=ThisPHAObjIDInXML)
				ThisDisplDeviceInXML = ThisViewportTag.findtext(info.DisplayDeviceTag)
				ThisDisplDeviceID = None if ThisDisplDeviceInXML == info.NoneTag else ThisDisplDeviceInXML
				# get the required Viewport's class
				ViewportClass = utilities.InstanceWithAttribValue(
					ObjList=display_utilities.ViewportMetaClass.ViewportClasses, AttribName='InternalName',
					TargetValue=ThisKind, NotFoundValue=None)
				ViewportIDToUse = ThisViewportTag.findtext(info.IDTag)
				# make the new client-side Viewport
				NewViewport, D2CSocketNo, C2DSocketNo, VizopTalksArgs, VizopTalksTips = display_utilities.CreateViewport(
					Proj=self,
					ViewportClass=ViewportClass, DisplDevice=None, PHAObj=ThisPHAObj, Fonts=self.Fonts,
					ID=ViewportIDToUse, SystemFontNames=self.SystemFontNames)
				# make the new Viewport shadow, using its previous ID
				NewViewportShadow = DatacoreDoNewViewport(XMLRoot=None, Proj=self,
					ViewportClass=ViewportClass, ViewportID=ViewportIDToUse,
					HumanName='', PHAObj=ThisPHAObj, Chain='NoChain', DisplDeviceID=ThisDisplDeviceID,
					ReturnRequired='NewViewport', D2CSocketNo=D2CSocketNo, C2DSocketNo=C2DSocketNo)
				# fetch any persistent attribs from XMLRoot
				ThisPAElement = ThisViewportTag.find(info.PersistentAttribsTag)
				if ThisPAElement is not None:
					NewViewportShadow.PersistentAttribs = ThisPAElement
				# TODO: 1. apply persistent attribs to client side viewport; 2. do any actions derived from
				# PostProcessDoNewViewport()
			return ProblemReports

		def ReconnectElementLinks(ElementHash):
			# restore all links between elements. Link targets are unpacked as element ID lists during unpacking.
			# These ID lists need to be replaced with the actual element objects, which could be in any PHA object in the
			# project.
			# ElementHash is a dict with keys = element IDs, values = elements for all elements across the project
			assert isinstance(ElementHash, dict)
			for ThisElID, ThisEl in ElementHash.items():
				if getattr(ThisEl, 'ConnectToID', None) is not None:
					ThisEl.ConnectTo = [ElementHash[i] for i in ThisEl.ConnectToID.replace(',', ' ').split()]
					del ThisEl.ConnectToID # remove for memory conservation and to avoid it becoming out of date
				if getattr(ThisEl, 'LinkedFromID', None) is not None:
					ThisEl.LinkedFrom = [ElementHash[i] for i in ThisEl.LinkedFromID.replace(',', ' ').split()]
					del ThisEl.LinkedFromID
				if getattr(ThisEl, 'RelatedCXID', None) is not None:
					ThisEl.RelatedCX = ElementHash[ThisEl.RelatedCXID]
					del ThisEl.RelatedCXID

		def ReconnectNumberLinks(ParentNumValueInstances, ElementHash):
			# reconnect "linked" and "copied from" number instances to their parents.
			# Also connect references to constants.
			# (Similar function to ReconnectElementLinks() )
			# ParentNumValueInstances is a list of NumValueItem instances needing reconnecting
			# ElementHash is a dict with keys = element IDs, values = elements for all elements across the project
			ProblemReports = []
			for ThisNum in ParentNumValueInstances:
				print('PR856 trying to reconnect referenced number to parent or constant')
				if hasattr(ThisNum, 'ParentPHAElementID'): # reconnect to parent PHA element
					ThisNum.ParentPHAObj = ElementHash[ThisNum.ParentPHAElementID]
					del ThisNum.ParentPHAElementID
				if hasattr(ThisNum, 'ConstantID'): # reconnect to constant
					ThisNum.Constant = utilities.ObjectWithID(Objects=self.Constants, TargetID=ThisNum.ConstantID)
					del ThisNum.ConstantID
			return ProblemReports

		def ReconnectParentNumberChunks(ParentNumberChunks, ElementHash):
			# In Numbering systems, any parent number chunk has been unpacked with an ID reference to the parent
			# PHA object. It now needs to be reconnected to the actual object.
			# Potential gotcha: if the parent numbering object isn't a PHA element, it won't be in ElementHash
			assert isinstance(ParentNumberChunks, list)
			assert isinstance(ElementHash, dict)
			ProblemReports = []
			for ThisPNC in ParentNumberChunks:
				ThisPNC.Source = ElementHash[ThisPNC.SourceID]
				del ThisPNC.SourceID
			return ProblemReports

		# start of main procedure for UnpackXMLToProject()
		# each chunk of data can return problems found as ProblemReportItem instances
		ParentNumValueInstances = [] # instances of objects needing referenced object IDs to be replaced with actual
		#	objects after objects are fetched
		# fetch project information
		ProblemReports = UnpackProjectInformation(XMLRoot=MyXMLRoot)
		# build a list of unique numbering systems
		NumberingSystems, NewProblemReports, ParentNumberChunks = FetchNumberingSystemTags(XMLRoot=MyXMLRoot)
		ProblemReports.extend(NewProblemReports)
		# fetch comments (as dict with keys = comment IDs, values = comment objects)
		Comments, NewProblemReports = FetchCommentTags(XMLRoot=MyXMLRoot)
		ProblemReports.extend(NewProblemReports)
		# fetch action items and parking lot items
		ActionItems, ParkingLotItems, NewProblemReports = FetchAssociatedTexts(XMLRoot=MyXMLRoot,
			NumberingSystems=NumberingSystems)
		ProblemReports.extend(NewProblemReports)
		# fetch structured object tags for simple objects
		ProblemReports, NewParentNumValueInstances = FetchSimpleStructuredObjectTags(XMLRoot=MyXMLRoot,
			NumberingSystems=NumberingSystems)
		ProblemReports.extend(NewProblemReports)
		ParentNumValueInstances.extend(NewParentNumValueInstances)
		# fetch data for each PHA object
		NewProblemReports, NewParentNumValueInstances, ElementHash = FetchPHAObjTags(XMLRoot=MyXMLRoot,
			NumberingSystems=NumberingSystems, Comments=Comments,
			ActionItems=ActionItems, ParkingLotItems=ParkingLotItems)
		ProblemReports.extend(NewProblemReports)
		ParentNumValueInstances.extend(NewParentNumValueInstances)
		# fetch Viewport data
		NewProblemReports = FetchViewportData(XMLRoot=MyXMLRoot)
		ProblemReports.extend(NewProblemReports)
		# restore all kinds of links between elements (except for links between numbers within elements)
		ReconnectElementLinks(ElementHash)
		# reconnect ParentNumberChunkItem number chunks in all objects to their respective parent objects
		NewProblemReports = ReconnectNumberLinks(ParentNumValueInstances, ElementHash)
		ProblemReports.extend(NewProblemReports)
		# reconnect parent number chunks to their respective parent objects
		NewProblemReports = ReconnectParentNumberChunks(ParentNumberChunks, ElementHash)
		ProblemReports.extend(NewProblemReports)
		return ProblemReports

	def CreatePHAObj(self, PHAModelClass, **NewPHAObjArgs):
		# create a new PHA object of the class specified, and store it in this project. Return the new PHA object
		# NewPHAObjArgs can include 'ID', which will be applied to the new PHA object
		assert issubclass(PHAModelClass, core_classes.PHAModelBaseClass)
		NewPHAObj = PHAModelClass(Proj=self, **NewPHAObjArgs)
		self.PHAObjs.append(NewPHAObj)
		self.PHAObjShadows.append(NewPHAObj) # put the same object in the shadows list, for local display devices to access
		return NewPHAObj

	def MakeAssocTextLookupTable(self, ATKind):
		# make and return dictionary with keys = ATs, values = list of PHA elements containing the AT
		# We assume the element's attrib containing the AT is named the same as AssocTextKind; if not,
		# its ATs won't be found
		assert ATKind in (info.ActionItemLabel, info.ParkingLotItemLabel)
		ATTable = {}
		for ThisPHAElement in self.WalkOverAllPHAElements():
			for ThisAT in getattr(ThisPHAElement, ATKind, []):
				if ThisAT in ATTable: ATTable[ThisAT].append(ThisPHAElement)
				else: ATTable[ThisAT] = [ThisPHAElement]
		return ATTable

def LegalString(InStr, Strip=True, FilterForbiddenChar=False, NoSpace=False) -> str:
	# return modified InStr (str) for storing in XML. If Strip, remove leading and trailing white space.
	# If FilterForbiddenChar, remove any char not in approved list. If NoSpace, replace all spaces with _
	ValidChars = "!#$%()*+,-.:;=?@[]^_`{|}~ '\"" + string.ascii_letters + string.digits
	assert type(InStr) == str
	assert type(Strip) == bool
	assert type(FilterForbiddenChar) == bool
	assert type(NoSpace) == bool
	FormattedString = InStr
	if Strip: FormattedString = FormattedString.strip()
	if FilterForbiddenChar:
		FormattedString = ''.join(c for c in FormattedString if c in ValidChars)
	if NoSpace:
		FormattedString = '_'.join(FormattedString.split(' '))
	return FormattedString

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
		ProjOpenData[FileIndex]['Openable'] = vizop_misc.IsReadableFile(ProjFile)
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

	file_list = vizop_misc.select_file_from_all(message=_('Select Vizop project file(s) to open'),
							  default_path=working_dir,
							  wildcard='.'.join(['*', proj_file_ext]),
							  read_only=False, allow_multi_files=True,
							  parent_frame=parent_frame)
	if file_list:
		# at least one project file was selected - update the working directory
		working_dir = os.path.dirname(file_list[0])
		sm.set_value('UserWorkingDir', working_dir)
	return file_list

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
	if UsingTemplates:
		assert (len(ProjectFilesToOpen) == len(ProjectFilesToCreate)), "PR117 need file names to create project files"
	ProjectsOpened = []
	SuccessReport = []
	for (ProjIndex, ProjFileName) in enumerate(ProjectFilesToOpen):
		ProjDocTree = ElementTree.parse(ProjFileName) # open file, convert into parsed tree
		XMLRoot = ProjDocTree.getroot()
		# check if doc type is usable; if so, extract it into a new project
		FileVersion = XMLRoot.attrib.get(info.VizopVersionTag, None)
		if FileVersion is not None: # Root element contains a VizopVersion attrib
			if FileVersion in info.UsableProjDocVersions:
				NewProj = CreateProject()
				ProblemReports = NewProj.UnpackXMLToProject(MyXMLRoot=XMLRoot)
				OpenedOK = not any(r.Fatal for r in ProblemReports)
#				OpenedOK, ProblemReport = PopulateProjectFromFile(NewProj, XMLRoot) # %%%
				# if we succeeded in extracting the project file or template, and if saving on the fly, create the output file
				# Any problem report will be appended to the report from file opening (above)
				if OpenedOK and SaveOnFly:
					OutputFileOK, ProblemReport = SaveEntireProject(NewProj, ProjectFilesToCreate[ProjIndex],
						ProblemReport, Close=False)
					NewProj.SaveOnFly = OutputFileOK
				else:
					OutputFileOK = True # dummy value if no output file needed
				SuccessReport.append( {'OpenedOK': OpenedOK, 'OutputFileOK': OutputFileOK, 'ProblemReport': ''} )
				if OpenedOK:
					ProjectsOpened.append(NewProj)
			else: # proj doc file version is not usable by this version of Vizop
				ProblemReportText = {True: _('Unusable template file type %s'), False: _('Unusable project file type %s')}[UsingTemplates]
				SuccessReport.append( {'OpenedOK': False, 'ProblemReport': ProblemReportText % DocType(ProjDocTreeTop)} )
		else: # proj doc file doesn't seem to be a Vizop file
			SuccessReport.append( {'OpenedOK': False, 'ProblemReport': _("Doesn't seem to be a Vizop file")})
	# TODO make use of ProblemReports (list of ProblemReportItem instances)
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

# def PopulateProjectFromFile(Proj, DocTreeTop):
# redundant
# 	# reads all data from doc tree generated by minidom.parse(), of which DocTreeTop is the top node (as returned by parse()).
# 	# Creates all needed PHA objects in Proj (ProjectItem instance) and populates them with data from doc tree.
# 	# Returns (OpenedOK (bool): False if the project can't even be partially opened,
# 	# ProblemReport (str; empty if no problems found, otherwise provides human-readable description of problems))
# 	OpenedOK = True
# 	ProblemReport = '' # this is just dummy code for now
# 	return OpenedOK, ProblemReport

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
	if vizop_misc.IsWritableLocation(os.path.dirname(OutputFilename)):
#		ProjFile = open(OutputFilename, 'w') # create the file
		# write all the data into the file
		WriteOK, WriteReport = WriteEntireProjectToFile(Proj, OutputFilename, Close=Close)
		Report = AddToReport(Report, WriteReport)
	else:
		WriteOK = False
		Report = AddToReport(Report, _('Unable to write project file at %s') % os.path.dirname(OutputFilename) )
	return WriteOK, Report

def WriteEntireProjectToFile(Proj, ProjFilename, Close):
	# write all data for Proj (ProjectItem) into ProjFilename (str), already confirmed as writable.
	# Close the file if Close (bool)
	# Return: WriteOK (bool) - whether data written successfully;
	#         ProblemReport (str) - human readable description of any problem encountered.
	# Make the XML tree, starting with the Document node.
	# TODO make this into a method of class ProjectItem
	assert type(Proj) == ProjectItem
	assert type(ProjFilename) == str
	assert isinstance(Close, bool)
#	ProjFile = open(ProjFilename, 'w') # create the file
	XMLRoot = Proj.ConvertProjectToXML()
	print('PR708 writing XML to file')
	XMLRoot.write(ProjFilename, encoding="UTF-8", xml_declaration=True)
	ProblemReport = ''
#	if Close: ProjFile.close()
	return True, ProblemReport

def SetupDefaultTolRiskModel(Proj):
	# probably now redundant; we're not using default model any more
	# set up a default tolerable risk model (severity categories) in project instance Proj
	# Make risk receptors (temporary; eventually this should happen during project initialization)
	PeopleRiskReceptor = core_classes.RiskReceptorItem(ID='NewPeople', XMLName='People', HumanName=_('People'))
	EnvironmentRiskReceptor = core_classes.RiskReceptorItem(ID=Proj.GetNewID(), XMLName='Environment', HumanName=_('Environment'))
	AssetsRiskReceptor = core_classes.RiskReceptorItem(ID=Proj.GetNewID(), XMLName='Assets', HumanName=_('Assets'))
	ReputationRiskReceptor = core_classes.RiskReceptorItem(ID=Proj.GetNewID(), XMLName='Reputation', HumanName=_('Reputation'))
	# make a tolerable risk model object; populate it with risk receptors
	TolRiskModel = core_classes.TolRiskFCatItem(Proj)
	TolRiskModel.HumanName = 'Company X default risk matrix'
	TolRiskModel.RiskReceptors = [PeopleRiskReceptor, EnvironmentRiskReceptor, AssetsRiskReceptor, ReputationRiskReceptor]
	Proj.RiskReceptors = TolRiskModel.RiskReceptors[:] # temporary
	# make a tolerable risk matrix
	Severity0 = core_classes.CategoryNameItem(XMLName='0', HumanName=_('Negligible'), HumanDescription=_('No significant impact'))
	Severity1 = core_classes.CategoryNameItem(XMLName='1', HumanName=_('Minor'), HumanDescription=_('Small, reversible impact'))
	Severity2 = core_classes.CategoryNameItem(XMLName='2', HumanName=_('Moderate'), HumanDescription=_('Significant impact'))
	Severity3 = core_classes.CategoryNameItem(XMLName='3', HumanName=_('Severe'), HumanDescription=_('Major impact with long-term consequences'))
	MyTolFreqTable = core_classes.LookupTableItem(ID=Proj.GetNewID())
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
	MyTolFreqTable.Values = [core_classes.UserNumValueItem(DefaultRR=False) for ThisCat in MyTolFreqTable.Keys[0]]
	# put the required values from TolFreqValues into the value objects
	for ThisSevCatIndex in range(len(MyTolFreqTable.Keys[ThisDimension])):
		ThisTolFreqValue = MyTolFreqTable.Values[ThisSevCatIndex]
		for ThisRRIndex, ThisRR in enumerate(TolRiskModel.RiskReceptors):
			ThisTolFreqValue.SetMyValue(NewValue=TolFreqValues[ThisRRIndex][ThisSevCatIndex], RR=ThisRR)
		ThisTolFreqValue.SetMyUnit(core_classes.PerYearUnit)
		print('PR1188 risk receptors in matrix values: ', len(ThisTolFreqValue.ValueFamily))
	# put tol risk model into project
	Proj.RiskMatrices.append(TolRiskModel)
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
	Success = vizop_misc.IsReadableFile(Proj.OutputFilename) and vizop_misc.IsWritableLocation(os.path.dirname(Proj.OutputFilename))
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
	# iterate over all PHA objects that contain number systems, plus the project itself (to capture e.g. action items)
	for ThisPHAObj in [Proj] + Proj.PHAObjs:
		for ThisElement in ThisPHAObj.GetAllObjsWithNumberSystems():
			ThisNumSystem = ThisElement.Numbering
			# check for a matching number system in NumSystems (can't just use 'in' as they are different objects,
			# so we use == as the NumberingSystem class implements a __eq__ method)
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

def AddAttribsInSubelements(StartEl, DataObj, SubElements):
	# add subelements to StartEl, whose text is the attrib value in DataObj specified in SubElements
	# (dict with keys = subelement tags, values = attrib names in DataObj)
	# Attrib values in DataObj can be str, int, bool, or None. If bool, they are converted to 'True' or 'False'.
	# If None, the value info.NoneTag is stored.
	assert isinstance(StartEl, ElementTree.Element)
	assert isinstance(SubElements, dict)
	for ThisTag, ThisAttribName in SubElements.items():
		SubEl = ElementTree.SubElement(StartEl, ThisTag)
		AttribType = type(getattr(DataObj, ThisAttribName))
		if AttribType is str:
			SubEl.text = LegalString(InStr=str(getattr(DataObj, ThisAttribName)))
		elif AttribType is int:
			SubEl.text = str(getattr(DataObj, ThisAttribName))
		elif AttribType is bool:
			SubEl.text = utilities.Bool2Str(Input=getattr(DataObj, ThisAttribName), TrueStr='True',
											FalseStr='False')
		elif getattr(DataObj, ThisAttribName) is None:
			SubEl.text = info.NoneTag
		else:
			raise TypeError('Supplied attrib with type %s' % AttribType)

def AddAttribIDsInSubelements(StartEl, DataObj, SubElements):
	# add subelements to StartEl, whose text is the ID attrib of the attrib value in DataObj specified in SubElements
	# (dict with keys = subelement tags, values = attrib names in DataObj)
	# If the attrib value is None, the value info.NoneTag is stored.
	assert isinstance(StartEl, ElementTree.Element)
	assert isinstance(SubElements, dict)
	for ThisTag, ThisAttribName in SubElements.items():
		SubEl = ElementTree.SubElement(StartEl, ThisTag)
		ThisAttrib = getattr(DataObj, ThisAttribName)
		SubEl.text = info.NoneTag if ThisAttrib is None else ThisAttrib.ID

def AddIDListAttribsInSubelements(StartEl, DataObj, SubElements):
	# add subelements to StartEl, with tags = keys in SubElements (dict)
	# Values in SubElements are names of attribs in DataObj. Those attribs should be lists of objects with IDs.
	# The text of the subelements is a comma-separated list of those IDs.
	assert isinstance(StartEl, ElementTree.Element)
	assert isinstance(SubElements, dict)
	for ThisTag, ThisAttribName in SubElements.items():
		SubEl = ElementTree.SubElement(StartEl, ThisTag)
		SubEl.text = ','.join(ThisObj.ID for ThisObj in getattr(DataObj, ThisAttribName))

def AddValueElement(StartEl, ValueTag, ValueObj):
	# add a subelement with tag = ValueTag (str) to StartEl (an ElementTree element), containing all required
	# data for numerical value in ValueObj (instance of subclass of NumValueItem)
	# Return the value XML subelement
	assert isinstance(StartEl, ElementTree.Element)
	assert isinstance(ValueTag, str)
	assert isinstance(ValueObj, core_classes.NumValueItem)
	TopTag = ElementTree.SubElement(StartEl, ValueTag)
	# add 'Kind' tag
	ValueKindHash = {core_classes.UserNumValueItem: info.UserTag, core_classes.ConstNumValueItem: info.ConstantTag,
		core_classes.LookupNumValueItem: info.LookupTag, core_classes.ParentNumValueItem: info.CopiedTag,
		core_classes.UseParentValueItem: info.LinkedFromTag}
	KindXML = ValueKindHash.get(type(ValueObj), info.UnknownTag)
	KindTag = ElementTree.SubElement(TopTag, info.KindTag)
	KindTag.text = KindXML
	# populate sub-elements for each number kind
	if KindXML in [info.UserTag, info.CopiedTag]:
		for ThisRR in ValueObj.ValueFamily.keys():
			ThisRRTag = ElementTree.SubElement(TopTag, info.RiskReceptorTag)
			ThisRRIDTag = ElementTree.SubElement(ThisRRTag, info.IDTag)
			ThisRRIDTag.text = ThisRR.ID
			# write number value. Invalid numbers (e.g. undefined) are stored as InvalidNumberLabel
			ThisRRValueTag = ElementTree.SubElement(ThisRRTag, info.ValueTag)
			ThisRRValueTag.text = str(ValueObj.GetMyValue(RR=ThisRR, InvalidResult=info.InvalidNumberLabel))
			# TODO also store SigFigs and Sci per RR?
			if ValueObj.InfinityFlagFamily[ThisRR]:
				ThisRRInfiniteTag = ElementTree.SubElement(ThisRRTag, info.InfiniteTag)
				ThisRRInfiniteTag.text = info.TrueLabel
		ThisUnitTag = ElementTree.SubElement(TopTag, info.UnitTag)
		ThisUnitTag.text = ValueObj.GetMyUnit().XMLName
		if KindXML == info.CopiedTag:
			ThisCopiedFromTag = ElementTree.SubElement(TopTag, info.CopiedFromTag)
			ThisCopiedFromTag.text = info.NoneTag if ValueObj.ParentPHAObj is None else ValueObj.ParentPHAObj.ID
	elif KindXML == info.ConstantTag:
		ThisIDTag = ElementTree.SubElement(TopTag, info.IDTag)
		ThisIDTag.text = info.NoneTag if ValueObj.Constant is None else ValueObj.Constant.ID
	elif KindXML == info.LookupTag:
		ThisIDTag = ElementTree.SubElement(TopTag, info.IDTag)
		ThisIDTag.text = info.NoneTag if ValueObj.LookupTable is None else ValueObj.LookupTable.ID
		# add <Value> tag: if no lookup value defined, store 'None' as text, else store a value item
		if ValueObj.InputValue is None:
			ThisValueTag = ElementTree.SubElement(TopTag, info.ValueTag)
			ThisValueTag.text = info.NoneTag
		else: AddValueElement(StartEl=ThisValueTag, ValueTag=info.ValueTag, ValueObj=ValueObj.InputValue)
	elif KindXML == info.LinkedFromTag:
		ThisLinkedFromTag = ElementTree.SubElement(TopTag, info.LinkedFromTag)
		ThisLinkedFromTag.text = info.NoneTag if ValueObj.ParentPHAObj is None else ValueObj.ParentPHAObj.ID
	return TopTag

def UnpackValueFromXML(Proj, XMLEl):
	# fetch a numerical value from XMLEl (<Value> tag as ElementTree.Element instance) and populate it as a
	# NumValueItem subclass instance
	# return the new NumValueItem instance and ProblemReports list
	# also return ParentNumValueInstances (list of ParentNumValueItem instances needing to have parent attrib set)
	assert isinstance(Proj, ProjectItem)
	assert isinstance(XMLEl, ElementTree.Element)
	ParentNumValueInstances = []
	ProblemReports = []
	# first, find number kind
	NumberKind = XMLEl.findtext(info.KindTag)
	if not (NumberKind in core_classes.NumValueKindHash.keys()):
		ProblemReports.append(core_classes.ProblemReportItem(HumanDescription=_('Unrecognised number kind')))
	NewNumber = core_classes.NumValueKindHash[NumberKind]()
	# fetch specific data for each number kind
	if NumberKind in ['User', 'Copied']:
		# fetch risk receptors
		for ThisRRTag in XMLEl.findall(info.RiskReceptorTag):
			ThisRRID = ThisRRTag.findtext(info.IDTag)
			if ThisRRID == info.GenericRRID: # use generic RR
				RRToUse = core_classes.DefaultRiskReceptor
			else: # create new RR
				RRToUse = utilities.ObjectWithID(Objects=Proj.RiskReceptors, TargetID=ThisRRID)
				NewNumber.AddRiskReceptor(RR=RRToUse)
			# fetch value per risk receptor, checking if value is set as infinite
			if utilities.Bool2Str(Input=ThisRRTag.findtext(info.InfiniteTag, default='False')):
				NewNumber.SetToInfinite(RR=RRToUse)
			else: # finite value
				ThisRRValue = ThisRRTag.findtext(info.ValueTag)
				# check if number value is invalid
				if ThisRRValue == info.InvalidNumberLabel: NewNumber.SetToUndefined(RR=RRToUse)
				else: NewNumber.SetMyValue(NewValue=utilities.str2real(s=ThisRRValue), RR=RRToUse)
		# fetch unit
		NewNumber.SetMyUnit(utilities.InstanceWithAttribValue(ObjList=core_classes.AllSelectableUnits,
			AttribName='XMLName', TargetValue=XMLEl.findtext(info.UnitTag)))
		# TODO unpack SigFigs, Sci
		if NumberKind == 'Copied':
			# fetch Parent PHA element's ID (later, will be replaced by the actual object)
			NewNumber.ParentPHAElementID = XMLEl.findtext(info.CopiedFromTag)
			ParentNumValueInstances.append(NewNumber)
	elif NumberKind == 'Constant':
		# fetch constant's ID, and attach the value object's ID (later, will be replaced by the actual object.
		# We can't attach the actual object yet, because it might be another constant that's not yet unpacked)
		ThisConstantID = XMLEl.findtext(info.IDTag)
		NewNumber.ConstantID = None if ThisConstantID == info.NoneTag else ThisConstantID
		ParentNumValueInstances.append(NewNumber)
	elif NumberKind == 'Lookup':
		# fetch lookup table's ID, and attach the actual table object
		ThisLookupTableID = XMLEl.findtext(info.IDTag)
		NewNumber.LookupTable = None if ThisLookupTableID == info.NoneTag else \
			utilities.ObjectWithID(Objects=Proj.RiskMatrices, TargetID=ThisLookupTableID)
		# fetch value object - a NumValueItem instance (or None) placed in NewNumber.InputValue
		ThisValueTag = XMLEl.find(info.ValueTag)
		if ThisValueTag.text == info.NoneTag: NewNumber.InputValue = None
		else:
			NewNumber.InputValue, NewProblemReports, NewParentNumValueInstances = UnpackValueFromXML(Proj=Proj,
				XMLEl=ThisValueTag)
			ProblemReports.extend(NewProblemReports)
			ParentNumValueInstances.extend(NewParentNumValueInstances)
	elif NumberKind == 'LinkedFrom':
		# fetch Parent PHA element's ID (later, will be replaced by the actual object)
		LinkedFromID = XMLEl.findtext(info.LinkedFromTag)
		NewNumber.ParentPHAElementID = None if LinkedFromID == info.NoneTag else LinkedFromID
		ParentNumValueInstances.append(NewNumber)
	return NewNumber, ProblemReports, ParentNumValueInstances

def StoreViewportCommonDataInXML(Viewport, StartTag):
	# create an XML element as a subelement of StartTag (ElementTree.Element) and populate it with common Viewport
	# data required to be stored in project file.
	# Return the <Viewport> tag, so that individual Viewport subclasses can add their own specific tags.
	# (This method belongs more naturally in module display_utilities as a method of ViewportBaseClass, but we can't
	# put it there as that would create a circular import.)
	assert isinstance(StartTag, ElementTree.Element)
	# First, make top level XML element
	TopTag = ElementTree.SubElement(StartTag, info.ViewportTag)
	# Add common tags
	projects.AddAttribsInSubelements(StartEl=TopTag, DataObj=Viewport,
		SubElements={info.KindTag: 'InternalName', info.IDTag: 'ID', info.PHAObjTag: 'PHAObjID',
		info.PanXTag: 'PanX', info.PanYTag: 'PanY'})
	projects.AddAttribIDsInSubelements(StartEl=TopTag, DataObj=Viewport,
		SubElements={info.DisplayDeviceTag: 'DisplDevice', info.ViewportToRevertToTag: 'ViewportToRevertTo'})
	# add Zoom tag
	ThisZoomTag = ElementTree.SubElement(TopTag, info.ZoomTag)
	ThisZoomTag.text = str(Viewport.Zoom)
	return TopTag

def FetchObjsFromIDList(IDList, ObjList):
	# extract and return list of objects from ObjList whose ID attrib is in IDList, in order of IDList
	# It is assumed that every object in ObjList has an ID attrib, and that every ID in IDList is included in ObjList
	# IDList can be either a list, or a string containing IDs separated by commas
	assert isinstance(IDList, (list, str))
	assert isinstance(ObjList, list)
	IDsToFind = IDList.replace(',', ' ').split() if isinstance(IDList, str) else IDList
	return [utilities.ObjectWithID(Objects=ObjList, TargetID=i) for i in IDsToFind]

def MakeXMLMessageForDrawViewport(Proj, MessageHead, PHAObj, Viewport, ViewportID, MilestoneID=None):
	# make and return XML element containing message required for SwitchToViewport, with all required redraw data
	# MessageHead: command string required as XML root, e.g. 'RP_NewViewport'
	# PHAObj: PHAObj to which Viewport belongs, or None if Viewport doesn't have an associated PHAObj
	# MilestoneID: ID of any milestone in Proj.MilestonesForUndo that should be applied when Viewport is drawn, or None
	assert isinstance(MessageHead, str)
	assert isinstance(PHAObj, core_classes.PHAModelBaseClass) or (PHAObj is None)
	assert isinstance(Viewport, ViewportShadow)
	assert isinstance(ViewportID, str)
	assert isinstance(MilestoneID, str) or (MilestoneID is None)
	# fetch full redraw data for Viewport from PHA object, or from the Viewport itself if it doesn't have a PHAObj
	if PHAObj is None:
		RedrawXMLData = Viewport.MyClass.GetFullRedrawData(Proj=Proj, Viewport=Viewport)
	else:
		RedrawXMLData = PHAObj.GetFullRedrawData(Viewport=Viewport, ViewportClass=Viewport.MyClass)
	# put ID of PHA object, followed by full redraw data, into XML element
	Reply = vizop_misc.MakeXMLMessage(RootName=MessageHead, RootText=ViewportID,
		Elements={info.IDTag: getattr(PHAObj, 'ID', '')})
	Reply.append(RedrawXMLData)
	# add milestone ID tag, if required
#		print('PR3138 adding milestoneID tag: ', MilestoneID)
	if MilestoneID is not None:
		MilestoneTag = ElementTree.Element(info.MilestoneIDTag)
		MilestoneTag.text = MilestoneID
		Reply.append(MilestoneTag)
	return Reply

def DatacoreDoNewViewport_Undo(Proj, UndoRecord, **Args): # undo creation of new Viewport
	global UndoChainWaiting # FIXME move this variable elsewhere, maybe as an attrib of Proj
	assert isinstance(Proj, ProjectItem)
	assert isinstance(UndoRecord, undo.UndoItem)
	# find out which datacore socket to send messages on
	SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
	# find and remove the new Viewport object
	ViewportToRemove = UndoRecord.ViewportShadow
	Proj.AllViewportShadows.remove(ViewportToRemove)
	# tell Control Frame what we did
	Notification = vizop_misc.MakeXMLMessage(RootName='NO_NewViewport_Undo', RootText=ViewportToRemove.ID,
		Elements={info.MilestoneIDTag: UndoRecord.MilestoneID, info.SkipRefreshTag: UndoRecord.Chain,
		info.ViewportTypeTag: ViewportToRemove.MyClass.InternalName,
		info.ChainWaitingTag: utilities.Bool2Str(Args['ChainWaiting']),
		info.ProjIDTag: Proj.ID})
	vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket,
		Command='NO_NewViewport_Undo', XMLRoot=Notification)
	SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.ViewportTag,
		Elements={info.IDTag: ViewportToRemove.ID, info.DeleteTag: ''}))
	UndoChainWaiting = Args.get('ChainWaiting', False)
	return {'Success': True}

def DatacoreDoNewViewport_Redo(Proj, RedoRecord, **Args): # redo creation of new Viewport
	# fetch the previously created Viewport shadow from the Redo record
	RecoveredViewport = RedoRecord.ViewportShadow
	# find the PHA object owning the Viewport, if any
	ThisPHAObj = RecoveredViewport.PHAObj
	if ThisPHAObj:
		ThisPHAObj.Viewports.append(RecoveredViewport) # add Viewport to list in the PHA object
		# fetch full redraw data of Viewport
		RedrawXMLData = ThisPHAObj.GetFullRedrawData(Viewport=RecoveredViewport, ViewportClass=RecoveredViewport.MyClass)
	else: # handling Viewport with no associated PHA object
		Proj.ViewportsWithoutPHAObjs.append(RecoveredViewport) # add Viewport to list in the PHA object
		# fetch full redraw data of Viewport
		RedrawXMLData = RecoveredViewport.MyClass.GetFullRedrawData(Viewport=RecoveredViewport,
			ViewportClass=RecoveredViewport.MyClass)
	# send ID of PHA model, followed by full redraw data, as reply to ControlFrame
	Notification = vizop_misc.MakeXMLMessage(RootName='NO_NewViewport_Redo', RootText=RecoveredViewport.ID,
		Elements={info.ProjIDTag: ThisPHAObj.ID, info.ViewportTypeTag: RecoveredViewport.MyClass.InternalName,
		info.ChainWaitingTag: utilities.Bool2Str(Args['ChainWaiting']),
		info.ChainedTag: utilities.Bool2Str(Args['ChainUndo']) })
	Notification.append(RedrawXMLData)
	# store undo record
	undo.AddToUndoList(Proj, Redoing=True, UndoObj=undo.UndoItem(UndoHandler=DatacoreDoNewViewport_Undo,
		RedoHandler=DatacoreDoNewViewport_Redo, ViewportShadow=RecoveredViewport, Chain=Args['ChainUndo'],
		MilestoneID=RedoRecord.MilestoneID,
		HumanText=_('new Viewport: %s' % RecoveredViewport.MyClass.HumanName)))
	# send the info to control frame as a notification
	vizop_misc.SendRequest(Socket=ControlFrameWithID(Args['RequestingControlFrameID']).C2FREQSocket.Socket,
		Command='NO_NewViewport_Redo', XMLRoot=Notification)
	return {'Success': True, 'Notification': Notification}

def DatacoreDoNewViewport(XMLRoot=None, Proj=None, ViewportClass=None, ViewportID=None, HumanName='',
	PHAObj=None, Chain='NoChain', DisplDeviceID=None, ReturnRequired='ReplyCommand',
	D2CSocketNo=None, C2DSocketNo=None):
	# datacore function to handle request for new Viewport from any Control Frame (local or remote)
	# It creates a Viewport shadow, i.e. an object that allows the datacore to know that a Viewport exists in
	# one of the Control Frames (local or remote). The new Viewport shadow is stored in either its PHA object's
	# Viewports list, or in Proj.ViewportsWithoutPHAObjs
	# Input data is supplied in XMLRoot, an XML ElementTree root element, or as separate attribs
	# including Chain (str: 'NoChain' or 'Stepwise'): whether this call is chained from another event, e.g. new PHA model
	# D2CSocketNo, C2DSocketNo: socket numbers supplied by display_utilities.CreateViewport()
	# Return data depends on ReturnRequired. If it's 'NewViewport', return the Viewport shadow instance;
	# if it's 'ReplyCommand', return reply data (XML tree) to send back to respective Control Frame
	assert ReturnRequired in ['NewViewport', 'ReplyCommand']
	# First, get the attribs needed to make the Viewport in the datacore
	if XMLRoot is None: # this branch is used when loading Viewport shadows from project file
		ThisProj = Proj
		NewViewportClass = ViewportClass
		NewViewportID = ViewportID
		NewViewportHumanName = HumanName
		ExistingPHAObj = PHAObj
		DisplDeviceIDToUse = DisplDeviceID
		D2CSocketNoToUse = D2CSocketNo
		C2DSocketNoToUse = C2DSocketNo
	else: # this branch is used when creating new Viewports. Tag "ProjID" in the XML is ignored
		ThisProj = Proj
#		ThisProj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		ClassList = display_utilities.ViewportMetaClass.ViewportClasses # list of all user-requestable Viewports
		NewViewportClass = ClassList[[Cls.InternalName for Cls in ClassList].index(XMLRoot.find('ViewportClass').text)]
		NewViewportID = XMLRoot.find('Viewport').text
		NewViewportHumanName = XMLRoot.find(info.HumanNameTag).text
		PHAModelID = XMLRoot.find(info.PHAModelIDTag).text # will be '' if this Viewport has no associated PHAModel
		ExistingPHAObj = utilities.ObjectWithID(ThisProj.PHAObjs, PHAModelID) if PHAModelID else None
		DisplDeviceIDToUse = XMLRoot.find(info.DisplayDeviceTag).text
		D2CSocketNoToUse = int(XMLRoot.find(info.D2CSocketNoTag).text)
		C2DSocketNoToUse = int(XMLRoot.find(info.C2DSocketNoTag).text)
	Chain = 'Stepwise' # TODO need 'NoChain' if we are adding new Viewport to existing PHA model
	# check if we can proceed to create the Viewport; we may need editing rights (TODO remove this requirement)
	if Proj.EditAllowed:
		# make the Viewport shadow
		NewViewport = ViewportShadow(ThisProj, NewViewportID, MyClass=NewViewportClass, DisplDeviceID=DisplDeviceIDToUse,
			 HumanName=NewViewportHumanName,
			 D2CSocketNumber=D2CSocketNoToUse,
			 C2DSocketNumber=C2DSocketNoToUse, PHAObj=ExistingPHAObj, XMLRoot=XMLRoot)
		# attach existing PHA object to the Viewport
		NewViewport.PHAObj = ExistingPHAObj
		# set DatacoreHandler, telling NewViewport where to find datacore request handlers. FIXME this might point to ViewportShadow!
		NewViewport.DatacoreHandler = ExistingPHAObj if ExistingPHAObj else NewViewport
		NewViewport.IsOnDisplay = (DisplDeviceIDToUse is not None) # set flag that ensures NewViewport will get redrawn
		# store Viewport shadow in the appropriate list
		if ExistingPHAObj is None:
			ThisProj.ViewportsWithoutPHAObjs.append(NewViewport) # add Viewport to list in the project
		else:
			ExistingPHAObj.Viewports.append(NewViewport) # add Viewport to list in the PHA object
		if ReturnRequired == 'NewViewport': Reply = NewViewport
		else:
			# fetch full redraw data of new PHA object, and include in reply message to send to control frame
			Reply = MakeXMLMessageForDrawViewport(Proj=ThisProj, MessageHead='RP_NewViewport',
				PHAObj=ExistingPHAObj,
				Viewport=NewViewport, ViewportID=NewViewportID)
			undo.AddToUndoList(ThisProj, UndoObj=undo.UndoItem(UndoHandler=DatacoreDoNewViewport_Undo,
				RedoHandler=DatacoreDoNewViewport_Redo, ViewportShadow=NewViewport, Chain=Chain,
				MilestoneID=XMLRoot.find(info.MilestoneIDTag).text,
				HumanText=_('new Viewport: %s') % NewViewportClass.HumanName))
	else: # couldn't make Viewport because it needs a new PHA model and editing is blocked. Redundant
		NewViewport = None
		Reply = vizop_misc.MakeXMLMessage(RootName='RP_NewViewport', RootText="Null",
			Elements={'CantComply': 'EditingBlocked'})
	# return new Viewport, or info to send back to control frame as a reply message (via ListenToSocket)
	return Reply

class ViewportShadow(object): # defines objects that represent Viewports in the datacore.
	# These are not the actual (visible) Viewports - those live in the client side controlframe (local or remote)
	# and aren't directly accessible by the datacore.

	def __init__(self, Proj, ID, MyClass=None, D2CSocketNumber=None, C2DSocketNumber=None, PHAObj=None,
			 HumanName='', XMLRoot=None, DisplDeviceID=None):
		# ID (str) is the same as the ID of the corresponding "real" Viewport
		# MyClass (ViewportClasses instance): class of actual Viewport shadowed by this one
		# D2CSocketNumber and C2DSocketNumber (2 x int): socket numbers assigned in display_utilities.CreateViewport
		# PHAObj: PHA object owning the real Viewport (if any) or None (if Viewport is not owned by a PHA object)
		# HumanName: HumanName assigned to the real Viewport
		assert isinstance(Proj, ProjectItem)
		assert isinstance(ID, str)
		assert MyClass in display_utilities.ViewportMetaClass.ViewportClasses
		assert isinstance(D2CSocketNumber, int)
		assert isinstance(C2DSocketNumber, int)
		assert isinstance(HumanName, str)
		assert isinstance(DisplDeviceID, str)
		object.__init__(self)
		self.ID = ID
		self.MyClass = MyClass
		self.HumanName = HumanName
		self.DisplDeviceID = DisplDeviceID # None if this Viewport is currently not displayed
		self.PHAObjID = getattr(PHAObj, 'ID', '') # storing ID, not the actual PHAObj, for consistency with real Viewports
		self.PersistentAttribs = None # None, or an XML root element containing attribs that can be reused when the
			# Viewport is recreated, and also to be stored in project file. The XML element is stored in the project file
			# as-is, and also (TODO) messaged as-is to the Viewport whenever redraw data is requested
		# Grab any additional attribs required by this Viewport class
		if hasattr(MyClass, 'GetClassAttribsOnInit'):
			self.RedrawData = MyClass.GetClassAttribsOnInit(XMLRoot=XMLRoot)
			print('CF3823 grabbed attribs on viewport init: ', MyClass.GetClassAttribsOnInit(XMLRoot=XMLRoot))
		self.IsOnDisplay = False # whether the Viewport shadow is currently displayed on any display device
		# set up sockets using socket numbers provided
		self.C2DSocketREP, self.C2DSocketREPObj, C2DSocketNumberReturned = vizop_misc.SetupNewSocket(SocketType='REP',
			SocketLabel='C2DREP_' + self.ID,
			PHAObj=PHAObj, Viewport=self, SocketNo=C2DSocketNumber, BelongsToDatacore=True, AddToRegister=True)
		self.D2CSocketREQ, self.D2CSocketREQObj, D2CSocketNumberReturned = vizop_misc.SetupNewSocket(SocketType='REQ',
			SocketLabel=info.ViewportOutSocketLabel + '_' + self.ID,
			PHAObj=PHAObj, Viewport=self, SocketNo=D2CSocketNumber, BelongsToDatacore=True, AddToRegister=True)
		# put the new viewport shadow into the project's list
		Proj.AllViewportShadows.append(self)

def SetupFonts():
	Fonts = {}
	Fonts['BigHeadingFont'] = core_classes.FontInstance(Size=18, Bold=True)
	if system() == 'Darwin': # slightly larger font size on macOS than Windows
		Fonts['NormalFont'] = core_classes.FontInstance(Size=12, Bold=False)
		Fonts['BoldFont'] = core_classes.FontInstance(Size=12, Bold=True)
		Fonts['SmallHeadingFont'] = core_classes.FontInstance(Size=14, Bold=True)
		Fonts['NormalWidgetFont'] = core_classes.FontInstance(Size=12, Bold=False)
		Fonts['BoldWidgetFont'] = core_classes.FontInstance(Size=12, Bold=True)
	else:
		Fonts['NormalFont'] = core_classes.FontInstance(Size=11, Bold=False)
		Fonts['BoldFont'] = core_classes.FontInstance(Size=11, Bold=True)
		Fonts['SmallHeadingFont'] = core_classes.FontInstance(Size=13, Bold=True)
		Fonts['NormalWidgetFont'] = core_classes.FontInstance(Size=11, Bold=False)
		Fonts['BoldWidgetFont'] = core_classes.FontInstance(Size=11, Bold=True)
	e = wx.FontEnumerator()
	e.EnumerateFacenames()
	return Fonts, e.GetFacenames()

del _ # remove dummy definition

"""[----------TESTING AREA---------- """

def runUnitTest():
	pass

""" ----------TESTING AREA----------]"""