# -*- coding: utf-8 -*-
# Module: projects. This file is part of Vizop. Copyright xSeriCon, 2020

# standard modules needed:
import os, shutil, datetime, string
import os.path
import xml.etree.ElementTree as ElementTree

# vizop modules needed:
# from vizop_misc import IsReadableFile, IsWritableLocation, select_file_from_all, MakeXMLMessage, SocketWithName
#import vizop_parser
import settings, core_classes, info, faulttree, utilities, display_utilities, undo, vizop_misc

"""
The projects module contains functions for handling entire Vizop projects, including project files.
Code for project-wide features like action items is also here.
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

		self.MaxIDInProj = 0 # (int) highest ID of all objects in the project
		self.PHAObjs = [] # list of PHA objects existing locally, in order created; empty if datacore is remote
		self.PHAObjShadows = [] # list of info about PHA objects; used by control frame, as the project datacore may be
			# remote, so it may not have access to self.PHAObjs; same order as self.PHAObjs
		self.ClientViewports = [] # list of all actual Viewports (not Viewport shadows) in this Vizop instance,
			# whether visible or not. Client side attrib.
		self.AllViewportShadows = [] # list of all Viewport shadows (belonging to datacore)
		# should be ViewportShadow instances, but might be Viewport instances, i.e. ViewportBaseClass subclass instances FIXME
		self.ViewportsWithoutPHAObjs = [] # datacore: any Viewport instances that don't belong to PHA objects (e.g. action item view)
#		self.ArchivedViewportShadows = [] # datacore: Viewport shadows created and subsequently deleted; retained to
#		# allow retrieval of persistent attribs. Need not be stored in project file. This attrib is no longer used.
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
		self.Description = 'A great excuse to spend 4 weeks in Seoul' # longer description of project
		self.EditNumber = 0 # int; incremented every time the project's dataset is changed
		self.TeamMembers = [core_classes.TeamMember('101', 'Amy Stone', 'Consultant','ABC Consultants'),
			core_classes.TeamMember('102', 'Ben Smith', 'Project Manager','BigChemCo')] # list of team members
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
			for ThisID in XMLRoot.findtext(info.PHAElementTag).split(',')]
		ATKind = XMLRoot.findtext(info.AssociatedTextKindTag)
		ATListName = 'ActionItems' if ATKind == info.ActionItemLabel else 'ParkingLot'
		TargetATs = [utilities.ObjectWithID(getattr(self, ATListName), TargetID=ThisID)
			for ThisID in XMLRoot.findtext(info.AssociatedTextIDTag).split(',')]
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

	def ConvertProjectToXML(self, ProjectFilename):
		# convert project to XML. Return the root element of the XML tree

		def LegalString(InStr, Strip=True, FilterForbiddenChar=False, NoSpace=False) -> str:
			# return modified InStr (str). If Strip, remove leading and trailing white space.
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
			TopEl = ElementTree.SubElement(parent=StartEl, tag=SubElTag)
			for ThisTag, ThisAttribName in SubElements.items():
				SubEl = ElementTree.SubElement(parent=TopEl, tag=ThisTag)
				AttribType = type(getattr(DataObj, ThisAttribName))
				if AttribType is str:
					SubEl.text = LegalString(InStr=str(getattr(DataObj, ThisAttribName)))
				elif AttribType is bool:
					SubEl.text = utilities.Bool2Str(Input=getattr(DataObj, ThisAttribName), TrueStr='True',
						FalseStr='False')
				else:
					raise TypeError('Supplied attrib with type %s' % AttribType)
			return TopEl

		def AddAttribsInSubelements(StartEl, DataObj, SubElements):
			# add subelements to StartEl, whose text is the attrib value in DataObj specified in SubElements
			# (dict with keys = subelement tags, values = attrib names in DataObj)
			# Attrib values in DataObj can be str, int, bool, or None. If bool, they are converted to 'True' or 'False'.
			# If None, the value info.NoneTag is stored.
			assert isinstance(StartEl, ElementTree.Element)
			assert isinstance(SubElements, dict)
			for ThisTag, ThisAttribName in SubElements.items():
				SubEl = ElementTree.SubElement(parent=StartEl, tag=ThisTag)
				AttribType = type(getattr(DataObj, ThisAttribName))
				if AttribType is str:
					SubEl.text = LegalString(InStr=str(getattr(DataObj, ThisAttribName)))
				elif AttribType is int:
					SubEl.text = str(getattr(DataObj, ThisAttribName))
				elif AttribType is bool:
					SubEl.text = utilities.Bool2Str(Input=getattr(DataObj, ThisAttribName), TrueStr='True',
						FalseStr='False')
				elif getattr(DataObj, ThisAttribName) is None: SubEl.text = info.NoneTag
				else:
					raise TypeError('Supplied attrib with type %s' % AttribType)

		def AddValueElement(StartEl, ValueTag, ValueObj):
			# add a subelement with tag = ValueTag (str) to StartEl (an ElementTree element), containing all required
			# data for numerical value in ValueObj (instance of subclass of NumValueItem)
			# Return the value subelement XML subelement
			assert isinstance(StartEl, ElementTree.Element)
			assert isinstance(ValueTag, str)
			assert isinstance(ValueObj, core_classes.NumValueItem)
			TopTag = ElementTree.SubElement(parent=StartEl, tag=ValueTag)
			# add 'Kind' tag
			ValueKindHash = {core_classes.UserNumValueItem: info.UserTag, core_classes.ConstNumValueItem: info.ConstantTag,
				core_classes.LookupNumValueItem: info.LookupTag, core_classes.ParentNumValueItem: info.CopiedTag,
				core_classes.UseParentValueItem: info.LinkedFromTag}
			KindXML = ValueKindHash.get(type(ValueObj), info.UnknownTag)
			KindTag = ElementTree.SubElement(parent=TopTag, tag=KindXML)
			KindTag.text = KindXML
			# populate sub-elements for each number kind
			if KindXML in [info.UserTag, info.CopiedTag]:
				for ThisRR in ValueObj.ValueFamily.keys():
					ThisRRTag = ElementTree.SubElement(parent=TopTag, tag=info.RiskReceptorTag)
					ThisRRIDTag = ElementTree.SubElement(parent=ThisRRTag, tag=info.IDTag)
					ThisRRIDTag.text = ThisRR.ID
					ThisRRValueTag = ElementTree.SubElement(parent=ThisRRTag, tag=info.ValueTag)
					ThisRRValueTag.text = str(ValueObj.GetMyValue(RR=ThisRR))
					if ValueObj.InfinityFlagFamily[ThisRR]:
						ThisRRInfiniteTag = ElementTree.SubElement(parent=ThisRRTag, tag=info.InfiniteTag)
						ThisRRInfiniteTag.text = info.TrueLabel
				ThisUnitTag = ElementTree.SubElement(parent=TopTag, tag=info.UnitTag)
				ThisUnitTag.text = ValueObj.GetMyUnit().XMLName
				if KindXML == info.CopiedTag:
					ThisCopiedFromTag = ElementTree.SubElement(parent=TopTag, tag=info.CopiedFromTag)
					ThisCopiedFromTag.text = info.NoneTag if ValueObj.ParentPHAObj is None else ValueObj.ParentPHAObj.ID
			elif KindXML == info.ConstantTag:
				ThisIDTag = ElementTree.SubElement(parent=TopTag, tag=info.IDTag)
				ThisIDTag.text = info.NoneTag if ValueObj.Constant is None else ValueObj.Constant.ID
			elif KindXML == info.LookupTag:
				ThisIDTag = ElementTree.SubElement(parent=TopTag, tag=info.IDTag)
				ThisIDTag.text = info.NoneTag if ValueObj.LookupTable is None else ValueObj.LookupTable.ID
				# add <Value> tag: if no lookup value defined, store 'None' as text, else store a value item
				if ValueObj.InputValue is None:
					ThisValueTag = ElementTree.SubElement(parent=TopTag, tag=info.ValueTag)
					ThisValueTag.text = info.NoneTag
				else: AddValueElement(StartEl=ThisValueTag, ValueTag=info.ValueTag, ValueObj=ValueObj.InputValue)
			elif KindXML == info.LinkedFromTag: pass # TODO
				ThisLinkedFromTag = ElementTree.SubElement(parent=TopTag, tag=info.LinkedFromTag)
				ThisLinkedFromTag.text = info.NoneTag if ValueObj.ParentPHAObj is None else ValueObj.ParentPHAObj.ID
			return TopTag

		def AddProjectInformationTags(XMLRoot):
			# add project information tags to XMLRoot
			ShortTitleElement = ElementTree.SubElement(parent=XMLRoot, tag=info.ShortTitleTag)
			ShortTitleElement.text = LegalString(InStr=self.ShortTitle)
			ProjNumberElement = ElementTree.SubElement(parent=XMLRoot, tag=info.ProjNumberTag)
			ProjNumberElement.text = LegalString(InStr=self.ProjNumber)
			ProjDescriptionElement = ElementTree.SubElement(parent=XMLRoot, tag=info.DescriptionTag)
			ProjDescriptionElement.text = LegalString(InStr=self.Description)
			EditNumberElement = ElementTree.SubElement(parent=XMLRoot, tag=info.EditNumberTag)
			EditNumberElement.text = str(self.EditNumber)
			# add TeamMember tags
			TMTopElement = ElementTree.SubElement(parent=XMLRoot, tag=info.TeamMembersTag)
			for ThisTM in self.TeamMembers:
				TMElement = ElementTree.SubElement(parent=TMTopElement, tag=info.TeamMemberTag,
					attrib={info.NameTag: LegalString(InStr=ThisTM.Name), info.RoleTag: LegalString(InStr=ThisTM.Role),
					info.AffiliationTag: LegalString(InStr=ThisTM.Affiliation)})
				TMElement.text = ThisTM.ID

		def AddNumberingSystemTags(XMLRoot):
			# build a list of all unique numbering systems used in the project, and write numbering systems to XMLRoot
			AllNumberingSystems = GetAllNumberingSystems(Proj=self)
			# write a tag for each NS
			for ThisNSIndex, ThisNSElementList in enumerate(AllNumberingSystems):
				ThisNSElement = ElementTree.SubElement(parent=XMLRoot, tag=info.NumberSystemTag)
				# store an 'ID' for the NS = its index in AllNumberingSystems
				ThisIDTag = ElementTree.SubElement(parent=ThisNSElement, tag=info.IDTag)
				ThisIDTag.text = str(ThisNSIndex)
				ThisNS = ThisNSElementList[0].Numbering # pick the NS from one of the elements in the list
				# store Chunk subelements for this NS
				for ThisChunk in ThisNS.NumberStructure:
					ThisChunkTag = MakeStructuredElement(StartEl=ThisNSElement, SubElTag=info.NumberChunkTag,
						DataObj=ThisNS, SubElements={info.ShowInDisplayTag: 'ShowInDisplay',
						info.ShowInOutputTag: 'ShowInOutput', info.NumberChunkKindTag: 'XMLName'})
					# add specific XML tags for each chunk kind
					if ThisChunk.XMLName == info.NumberSystemStringType:
						ValueTag = ElementTree.SubElement(parent=ThisChunkTag, tag=info.ValueTag)
						ValueTag.text = LegalString(InStr=ThisChunk.Value)
					elif ThisChunk.XMLName == info.NumberSystemParentType:
						IDTag = ElementTree.SubElement(parent=ThisChunkTag, tag=info.IDTag)
						IDTag.text = ThisChunk.Source.ID
						LevelsTag = ElementTree.SubElement(parent=ThisChunkTag, tag=info.LevelsTag)
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
			SOInfo = [ ('ProcessUnits', info.ProcessUnitTag, {info.IDTag: info.IDAttribName,
				info.UnitNumberTag: info.UnitNumberAttribName,
				info.ShortNameTag: info.ShortNameAttribName, info.LongNameTag: info.LongNameAttribName} ),
				('RiskReceptors', info.RiskReceptorTag, {info.IDTag: info.IDAttribName, info.NameTag: 'Name'}) ]
			for ThisSOKindName, TagName, SubElements in SOInfo:
				for ThisSO in getattr(self, ThisSOKindName):
					ThisSOElement = MakeStructuredElement(StartEl=XMLRoot, SubElTag=TagName, DataObj=ThisSO,
						SubElements=SubElements)
			# add action items, with numbering tag
			for ThisActionItem in self.ActionItems:
				ThisATTag = ElementTree.SubElement(parent=XMLRoot, tag=info.ActionItemTag)
				AddAttribsInSubelements(StartEl=ThisATTag, DataObj=ThisActionItem,
					SubElements={info.IDTag: info.IDAttribName, 'Text': 'Content',
					info.ResponsibilityTag: 'Responsibility', info.DeadlineTag: 'Deadline',
					info.StatusTag: 'Status'})
				ThisNumberingTag = ElementTree.SubElement(parent=ThisATTag, tag=info.NumberingTag)
				ThisNumberingTag.text = str(NumberingSystemHash[ThisActionItem])
			# add parking lot items, with numbering tag
			for ThisParkingLotItem in self.ParkingLot:
				ThisATTag = ElementTree.SubElement(parent=XMLRoot, tag=info.ParkingLotItemTag)
				AddAttribsInSubelements(StartEl=ThisATTag, DataObj=ThisParkingLotItem,
					SubElements={info.IDTag: info.IDAttribName, 'Text': 'Content',
					info.ResponsibilityTag: 'Responsibility', info.DeadlineTag: 'Deadline',
					info.StatusTag: 'Status'})
				ThisNumberingTag = ElementTree.SubElement(parent=ThisATTag, tag=info.NumberingTag)
				ThisNumberingTag.text = str(NumberingSystemHash[ThisParkingLotItem])
			# add Constants
			for ThisConstant in self.Constants:
				ThisConstantTag = ElementTree.SubElement(parent=XMLRoot, tag=info.ConstantTag)
				AddAttribsInSubelements(StartEl=ThisATTag, DataObj=ThisActionItem,
					SubElements={info.IDTag: info.IDAttribName, info.NameTag: 'HumanName'})
				AddValueElement(StartEl=ThisConstantTag, ValueTag=info.ConstValueTag, ValueObj=ThisConstant)
			# add risk matrices
			for ThisMatrix in self.RiskMatrices:
				ThisMatrixTag = ElementTree.SubElement(parent=XMLRoot, tag=info.RiskMatrixTag)
				# store categories
				for ThisDimensionCatList in ThisMatrix.Keys:
					for ThisCat in ThisDimensionCatList:
						MakeStructuredElement(StartEl=ThisMatrixTag, SubElTag=info.CategoryTag, DataObj=ThisCat,
							SubElements={info.XMLNameTag: 'XMLName', info.HumanNameTag: 'HumanName',
							info.DescriptionTag: 'HumanDescription'})
				# store severity dimension index
				SeverityDimIndexTag = ElementTree.SubElement(parent=ThisMatrixTag, tag=info.SeverityDimensionTag)
				SeverityDimIndexTag.text = info.NoneTag if ThisMatrix.SeverityDimensionIndex is None \
					else str(ThisMatrix.SeverityDimensionIndex)
				# store dimension names and the keys in each dimension
				for ThisDimensionIndex in range(ThisMatrix.HowManyDimensions):
					DimensionTag = ElementTree.SubElement(parent=ThisMatrixTag, tag=info.DimensionTag)
					NameTag = ElementTree.SubElement(parent=DimensionTag, tag=info.NameTag)
					NameTag.text = ThisMatrix.DimensionHumanNames[ThisDimensionIndex]
					UnitTag = ElementTree.SubElement(parent=DimensionTag, tag=info.UnitTag)
					UnitTag.text = ThisMatrix.DimensionUnits[ThisDimensionIndex].XMLName
					# store keys for this dimension
					for ThisKey in ThisMatrix.Keys[ThisDimensionIndex]:
						KeyTag = ElementTree.SubElement(parent=DimensionTag, tag=info.KeyTag)
						XMLNameTag = ElementTree.SubElement(parent=KeyTag, tag=info.XMLNameTag)
						XMLNameTag.text = ThisKey.XMLName
				# store values for the matrix
				for ThisValue in utilities.flatten(ThisMatrix.Values):
					AddValueElement(StartEl=ThisMatrixTag, ValueTag=info.ValueTag, ValueObj=ThisValue)

		def AddPHAObjTags(XMLRoot, NumberingSystemHash):
			# add tags for each PHA object in the project. Return comment hash (dict):
			# Keys are comment IDs (str), values are comment texts (str)
			CommentHash = {}
			MaxCommentIDSoFar = 0
			for ThisPHAObj in self.PHAObjs:
				ThisPHAObjTag = ElementTree.SubElement(parent=XMLRoot, tag=info.PHAObjTag)
				ThisKindTag = ElementTree.SubElement(parent=ThisPHAObjTag, tag=info.KindTag)
				ThisKindTag.text = type(ThisPHAObj).InternalName
				ThisIDTag = ElementTree.SubElement(parent=ThisPHAObjTag, tag=info.IDTag)
				ThisIDTag.text = ThisPHAObj.ID
				# ask the PHA object to add all of its own data in ThisPHAObjTag, and return all comments found%%%
				ThisCommentHash, MaxCommentIDSoFar = ThisPHAObj.StoreAllDataInXML(StartTag=ThisPHAObjTag,
					NumberingSystemHash=NumberingSystemHash, MaxCommentIDSoFar=MaxCommentIDSoFar)
				assert isinstance(ThisCommentHash, dict)
				assert isinstance(MaxCommentIDSoFar, int)
				CommentHash.update(ThisCommentHash)
			return CommentHash

		# start of main procedure for ConvertProjectToXML()
		assert isinstance(ProjectFilename, str)
		# First, create XML tree containing root XML element
		MyXMLRoot = ElementTree.Element(tag=info.ProjectRootTag, attrib={info.VizopVersionTag: info.VERSION})
		MyXMLTree = ElementTree.ElementTree(element=MyXMLRoot)
#		# set the skeleton as the XML tree root element
#		MyXMLTree._setroot(ET.fromstring(projects.XMLTreeSkeleton))
#		MyXMLRoot = MyXMLTree.getroot()
		# add project information tags, including team members%%%
		AddProjectInformationTags(XMLRoot=MyXMLRoot)
		# add numbering system tags
		NumberingSystems = AddNumberingSystemTags(XMLRoot=MyXMLRoot)
		# make a numbering system hash for all numbered objects in the project:
		# keys are objects, values are numbering system indices
		NumberingSystemHash = {}
		for ThisIndex, ThisObjList in enumerate(NumberingSystems):
			NumberingSystemHash.update(dict([(ThisObj, ThisIndex) for ThisObj in ThisObjList]))
		# add structured object tags for simple objects
		AddSimpleStructuredObjectTags(XMLRoot=MyXMLRoot, NumberingSystemHash=NumberingSystemHash)
		# add tags for each PHA object
		AddPHAObjTags(XMLRoot=MyXMLRoot, NumberingSystemHash=NumberingSystemHash)

		#Process Units
		if len(self.ProcessUnits) > 0:
			# create outer XML tag
			MyXMLRoot_ProcessUnits = ET.SubElement(MyXMLRoot, info.ProcessUnitsTag)

			for each_ProcessUnit in self.ProcessUnits:
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
		if len(self.RiskReceptors) > 0:
			# create outer XML tag
			MyXMLRoot_RiskReceptors = ET.SubElement(MyXMLRoot, info.RiskReceptorsTag)

			for each_RiskReceptor in self.RiskReceptors:
				assert type(each_RiskReceptor) == core_classes.RiskReceptorItem
				MyXMLRoot_RiskReceptors_RiskReceptor = ET.SubElement(MyXMLRoot_RiskReceptors, info.RiskReceptorTag)

				# <ID [ID int as str] />
				MyXMLRoot_RiskReceptors_RiskReceptor_ID = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, info.IDTag)
				MyXMLRoot_RiskReceptors_RiskReceptor_ID.text = pS(str(each_RiskReceptor.ID))

				#<Name [HumanName as str] />
				MyXMLRoot_RiskReceptors_RiskReceptor_HumanName = ET.SubElement(MyXMLRoot_RiskReceptors_RiskReceptor, info.NameTag)
				MyXMLRoot_RiskReceptors_RiskReceptor_HumanName.text = pS(each_RiskReceptor.HumanName)

		# Numbering Systems
		if len(self.NumberSystems) > 0:
			# create outer XML tag
			MyXMLRoot_NumberSystem = ET.SubElement(MyXMLRoot, info.NumberSystemTag)

			for each_NumberSystem in self.NumberSystems:
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
					if each_NumberSystem.SkipTo is not None:
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
		if len(self.RiskMatrices) > 0:

			# LookupTableItem
			for each_RiskMatrix in self.RiskMatrices:
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
						#assert type(each_value) == core_classes.RiskReceptorItem
						# TODO how risk receptor contains a value? By which attribute?

						assert issubclass(type(each_value), core_classes.NumValueItem)
						MyXMLRoot_RiskMatrix_Entry = ET.SubElement(MyXMLRoot_RiskMatrix, info.EntryTag)

						if type(each_value) == core_classes.UserNumValueItem:
							# Kind
							MyXMLRoot_RiskMatrix_Entry_Kind = ET.SubElement(MyXMLRoot_RiskMatrix_Entry, info.KindTag)

							# RiskReceptor
							MyXMLRoot_RiskMatrix_Entry_RiskReceptor = ET.SubElement(MyXMLRoot_RiskMatrix_Entry, info.RiskReceptorTag)
							MyXMLRoot_RiskMatrix_Entry_RiskReceptor.text = None


							pass
						elif type(each_value) == core_classes.ConstantItem:

							pass
						elif type(each_value) == core_classes.LookupNumValueItem:

							pass
						elif type(each_value) == core_classes.CategoryNameItem:

							pass
						elif type(each_value) == core_classes.ParentNumValueItem:

							pass


						pass

					pass
				pass
			pass

		#Constants
		# J: TODO
		if len(self.Constants) > 0:
			# create outer XML tag
			MyXMLRoot_Constants = ET.SubElement(MyXMLRoot, info.ConstantsTag)

			for each_Constant in self.Constants:
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
		if len(self.FaultTree) > 0:
			# create outer XML tag
			MyXMLRoot_FaultTrees = ET.SubElement(MyXMLRoot, info.FaultTreesTag)

			each_FaultTree: faulttree.FTObjectInCore
			for each_FaultTree in self.FaultTrees:
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
								if each_FTEvent.RelatedCX is not None:
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
				if each_FaultTree.ModelGate is not None:
					MyXMLRoot_FaultTrees_FaultTree_ModelGate = ET.SubElement(MyXMLRoot_FaultTrees_FaultTree, info.ModelGateTag)
					each_FaultTree.ModelGate: faulttree.FTGateItemInCore
					MyXMLRoot_FaultTrees_FaultTree_ModelGate.text = pS(str(each_FaultTree.ModelGate.ID))

				pass

		#Comment
		if len(self.Comments) > 0:
			MyXMLRoot_Comments = ET.SubElement(MyXMLRoot, info.CommentsTag)

			each_Comment: core_classes.Comment
			for each_Comment in self.Comments:
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
	if vizop_misc.IsWritableLocation(os.path.dirname(OutputFilename)):
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
	# TODO make this into a method of class ProjectItem
	assert type(Proj) == ProjectItem
	assert type(ProjFilename) == str

	try:
		Proj.ConvertProjectToXML(Proj, ProjFilename)
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

del _ # remove dummy definition

"""[----------TESTING AREA---------- """

def runUnitTest():
	pass

""" ----------TESTING AREA----------]"""