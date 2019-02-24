# -*- coding: utf-8 -*-
# This file is part of vizop. Copyright xSeriCon, 2018

"""vizop project_display module
This module handles display of general project settings
"""

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import wx, wx.grid # provides basic GUI functions
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED
# import zmq
import xml.etree.ElementTree as ElementTree # XML handling

# other vizop modules required here
import text, utilities, core_classes, info, vizop_misc, projects, art, display_utilities

class ProjectInfoModelInCore(core_classes.PHAModelBaseClass):
	# defines project settings info model, a sort of "PHA model" used to send project info to the project info Viewport.
	# It's handled and accessed only by DataCore, not directly by Viewports.
	IsBaseClass = False
	PreferredKbdShortcut = 'p'
	HumanName = _('Project information')
	InternalName = 'ProjInfo'
	CanBeCreatedManually = False
	DefaultViewportType = None # TODO add actual viewport type here, when coded

	def __init__(self, Proj, **Args):
		core_classes.PHAModelBaseClass.__init__(self, **Args)
		# ID is already assigned in PHAModelBaseClass.__init__
		# self.EditAllowed attrib is inherited from base class
		self.Proj = Proj
		# make hash used to find attribs from data given in commands
		self.StructuredObjLists = {'ProcessUnit': self.Proj.ProcessUnits}
		self.StructuredObjClasses = {'ProcessUnit': projects.ProcessUnit}

	def GetFullRedrawData(self, Viewport=None, ViewportClass=None, **Args):
		# return all data in ProjectDisplayModelInCore as an XML tree, for sending to Viewport to show project info

		def PopulateOverallData(XMLEl): # put overall project data into XML tree element XMLEl
			# set root element's text = ID (essential to have some root element text)
			XMLEl.text = self.ID
			# add project name, number and description
			TextItemInfo = [(self.Proj.ShortTitle, info.ProjNameTag), (self.Proj.ProjNo, info.ProjNoTag),
				(self.Proj.Description, info.DescriptionTag)]
			for ThisAttrib, ThisTag in TextItemInfo:
				ThisEl = ElementTree.SubElement(XMLEl, ThisTag)
				ThisEl.text = ThisAttrib
			# add process units
			for ThisProcessUnit in self.Proj.ProcessUnits:
				UnitEl = ElementTree.SubElement(XMLEl, info.ProcessUnitTag)
				UnitEl.text = 'OK' # dummy text, not currently used
				UnitEl.set(info.IDAttribName, ThisProcessUnit.ID) # put ID, short & long names into process unit tag
				UnitEl.set(info.UnitNumberAttribName, ThisProcessUnit.UnitNumber)
				UnitEl.set(info.ShortNameAttribName, ThisProcessUnit.ShortName)
				UnitEl.set(info.LongNameAttribName, ThisProcessUnit.LongName)
			# add collaborators
			for ThisCollaborator in self.Proj.Collaborators:
				CollEl = ElementTree.SubElement(XMLEl, info.CollaboratorTag)
				CollEl.text = 'OK' # dummy text, not currently used
				CollEl.set(info.IDAttribName, ThisCollaborator.ID) # put ID, short & long names into process unit tag
				CollEl.set(info.ShortNameAttribName, ThisCollaborator.ShortName)
				CollEl.set(info.LongNameAttribName, ThisCollaborator.LongName)

		# GetFullRedrawData main procedure
		# First, make the root element
		RootElement = ElementTree.Element(ViewportClass.InternalName)
		# populate with overall project-related data
		PopulateOverallData(RootElement)
		return RootElement

	def HandleIncomingRequest(self, MessageReceived=None, Args={}, MessageAsXMLTree=None):
		# handle request received by PHA model in datacore from a Viewport. Request can be to edit data
		# Incoming message can be supplied as either an XML string or XML tree root element
		# MessageReceived (str or None): XML message containing request info
		# MessageAsXMLTree (XML element or None): root of XML tree
		# return Reply (Root object of XML tree)
		# First, convert MessageReceived to an XML tree for parsing
		assert isinstance(MessageReceived, str) or (MessageReceived is None)
		assert isinstance(Args, dict)
		if MessageReceived is None:
			assert isinstance(MessageAsXMLTree, ElementTree.Element)
			XMLRoot = MessageAsXMLTree
		else: XMLRoot = ElementTree.fromstring(MessageReceived)
		Proj = Args['Proj'] # get ProjectItem object to which this request belongs
		# get the command - it's the tag of the root element
		Command = XMLRoot.tag
		# prepare default reply if command unknown
		Reply = vizop_misc.MakeXMLMessage(RootName='Fail', RootText='CommandNotRecognised')
		# process the command
		if Command == 'RQ_PI_ChangeValue':
			Reply = self.ChangeValue(Proj=Proj, AttribName=XMLRoot.findtext('Attrib'),
				NewValue=XMLRoot.findtext('NewValue'))
		elif Command == 'RQ_PI_ReorderUnit':
			Reply = self.ReorderUnit(Proj, UnitID=XMLRoot.findtext('Unit'), NewIndex=int(XMLRoot.findtext('NewIndex')))
		elif Command == 'RQ_PI_ChangeValueInStructuredObj':
			Reply = self.ChangeValueInStructuredObj(Proj=Proj, ObjectKind=XMLRoot.findtext('ObjectType'),
				InstanceID=XMLRoot.findtext('Instance'), AttribName=XMLRoot.findtext('Attrib'),
				NewValue=XMLRoot.findtext('NewValue'))
		elif Command == 'RQ_PI_AddStructuredObj':
			Reply = self.AddStructuredObj(Proj=Proj, ObjectKind=XMLRoot.findtext('ObjectType'),
				Index=XMLRoot.findtext('Index'))
		elif Command == 'RQ_PI_DeleteStructuredObj':
			Reply = self.DeleteStructuredObj(Proj=Proj, ObjectKind=XMLRoot.findtext('ObjectType'),
				Instances=[utilities.ObjectWithID(Proj.ProcessUnits, ThisID)
				for ThisID in XMLRoot.findtext('Units').split(',')])
		return Reply

	def ChangeValue(self, Proj, AttribName, NewValue):
		# process incoming request to change AttribName's value in Proj to NewValue. TODO add undo and save on fly
		assert isinstance(AttribName, str)
		assert hasattr(Proj, AttribName)
		assert isinstance(NewValue, str)
		setattr(Proj, AttribName, NewValue)
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def ReorderUnit(self, Proj, UnitID, NewIndex): # move process unit with ID=UnitID to position NewIndex in unit list
		# TODO add undo and save on fly
		assert isinstance(UnitID, str)
		assert isinstance(NewIndex, int)
		# find index of unit to move
		RelevantUnit = [u for u in Proj.ProcessUnits if u.ID == UnitID][0]
		Proj.ProcessUnits.remove(RelevantUnit) # remove from old position in list
		Proj.ProcessUnits.insert(NewIndex, RelevantUnit) # insert it to new position
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def ChangeValueInStructuredObj(self, Proj, ObjectKind, InstanceID, AttribName, NewValue):
		# change an attrib value in a structured object such as a ProcessUnit
		assert ObjectKind in ['ProcessUnit']
		assert isinstance(InstanceID, str)
		assert isinstance(AttribName, str)
		assert isinstance(NewValue, str)
		# get list containing object to edit
		ObjectListToEdit = self.StructuredObjLists[ObjectKind]
		# get specific object to edit
		ObjectInstanceToEdit = [i for i in ObjectListToEdit if i.ID == InstanceID][0]
		setattr(ObjectInstanceToEdit, AttribName, NewValue)
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def AddStructuredObj(self, Proj, ObjectKind, Index):
		# add new structured object (such as a ProcessUnit) to Proj at Index
		assert ObjectKind in ['ProcessUnit']
		IndexInt = int(Index)
		# get list containing object to edit
		ObjectListToEdit = self.StructuredObjLists[ObjectKind]
		assert 0 <= IndexInt <= len(ObjectListToEdit)
		# create new structured object
		NewObj = self.StructuredObjClasses[ObjectKind](Proj=Proj)
		# insert it into object list
		ObjectListToEdit.insert(IndexInt, NewObj)
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def DeleteStructuredObj(self, Proj, ObjectKind, Instances):
		# delete structured objects of kind ObjectKind (str) (such as a ProcessUnit) listed in Instances from list Proj
		assert ObjectKind in ['ProcessUnit']
		# get list containing object to edit
		ObjectListToEdit = self.StructuredObjLists[ObjectKind]
		# remove object instances specified
		for DoomedObj in Instances:
			# add a routine (e.g. projects.DeleteRefsToStructuredObj) to remove usages of the object in the project,
			# including creating Undo records
			# add to Undo list here (need to know the doomed object's index in the list)
			ObjectListToEdit.remove(DoomedObj)
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

class ProcessUnitForDisplay(object): # object representing an area of the plant, e.g. "gas dryer"

	def __init__(self, Proj, ProjInfoViewport, **Args):
		object.__init__(self)
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(Args['UnitNumber'], str)
		assert isinstance(Args['ShortName'], str)
		assert isinstance(Args['LongName'], str)
		self.ProjInfoViewport = ProjInfoViewport
		self.Proj = Proj
		self.ID = Args['ID'] # use same ID as datacore
		self.UnitNumber = Args['UnitNumber']
		self.ShortName = Args['ShortName']
		self.LongName = Args['LongName']

class CollaboratorForDisplay(object): # object representing a remote computer collaborating on this project

	def __init__(self, Proj, ProjInfoViewport, **Args):
		object.__init__(self)
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(Args['ShortName'], str)
		assert isinstance(Args['LongName'], str)
		self.ProjInfoViewport = ProjInfoViewport
		self.Proj = Proj
		self.ID = Args['ID']  # use same ID as datacore
		self.ShortName = Args['ShortName']
		self.LongName = Args['LongName']

class ProjectInfoModelForDisplay(display_utilities.ViewportBaseClass): # object containing all data needed to display project info
	IsBaseClass = False # should be done for every subclass of ViewportBaseClass
	CanBeCreatedManually = False # whether the user should be able to create a Viewport of this class from scratch
	InternalName = 'ProjectInfoViewport' # unique per class, used as XML tag in messaging
	HumanName = _('Project information')
	PreferredKbdShortcut = ''
	NewPHAObjRequired = ProjectInfoModelInCore # which datacore PHA object class this Viewport spawns on creation
	ImageSizeNoZoom = (20, 20) # initial no-zoom size of all button images
	AvailAspects = ['Overview', 'Risk']
	UnitsGridColNames = ['UnitNumber', 'ShortName', 'LongName'] # internal names of columns in Units grid
	UnitsAttribNamesPerGridCol = ['UnitNumber', 'ShortName', 'LongName'] # attrib names used in ProcessUnitForDisplay
		# instances, per column in the Units grid
	# hash of attrib names expected by PHA model (values) to corresponding names in Viewport (keys)
	PHAModelAttribNameHash = {'ShortTitle': 'ShortTitle', 'ProjNo': 'ProjNo', 'Description': 'Description'}

	def __init__(self, **Args): # project display object initiation. Args must include Proj and Fonts (dict)
		# and can include DisplDevice and ParentWindow
		display_utilities.ViewportBaseClass.__init__(self, **Args)
		self.Proj = Args['Proj']
		self.ID = None # assigned in display_utilities.CreateViewport()
		self.PHAObj = None # instance of ProjectInfoModelInCore shown in this Viewport (set in datacore.DoNewViewport())
		self.DisplDevice = Args.get('DisplDevice', None)
		self.Fonts = Args['Fonts']
		self.MaxIDInDisplayModel = 0 # highest ID of any element in this Viewport instance
		self.Zoom = 1.0 # ratio of canvas coords to screen coords (absolute ratio, not %)
		self.PanX = self.PanY = 0 # offset of drawing origin, in screen coords
		self.OffsetX = self.OffsetY = 0 # offset of Viewport in display panel, in screen coords;
			# referenced in utilities.CanvasCoordsViewport() but not currently used
		self.ParentWindow = Args.get('DisplDevice', None)
		# set up images used in FT
		self.ImagesNoZoom = {}
		self.ArtProvider = art.ArtProvider() # initialise art provider object
		for ThisImageName in self.ArtProvider.ImageCatalogue(OnlyWithPrefix=info.ProjInfoImagePrefix):
			# get the bitmap of each image, using image name as key including the prefix
			self.ImagesNoZoom[ThisImageName] = self.ArtProvider.get_image(name=ThisImageName,
				size=ProjectInfoModelForDisplay.ImageSizeNoZoom, conserve_aspect_ratio=True)
		self.PaintNeeded = True # whether to execute DoRedraw() in display device's OnPaint() handler (bool)
		self.Wipe() # initialize model-specific attribs
		self.InitializeWidgets() # create all widgets required for display
		self.WidgActive = [] # UIWidget objects currently on display (for use in CheckTextCtrlFocus handler)
		self.CurrentAspect = ProjectInfoModelForDisplay.AvailAspects[0] # which set of information is currently displayed
#		self.SetupNotebook() # set up notebook and put widgets into notebook pages
		# set up sizer
		self.MainSizer = wx.GridBagSizer(vgap=0, hgap=0) # make sizer for widgets; redundant if we use Notebook

	def Wipe(self): # wipe all the data in the project info model and re-initialize
		self.ShortName = ''
		self.ShortTitle = ''
		self.ProjNo = ''
		self.Description = ''
		self.ProcessUnits = []
		self.SelectedUnits = [] # which ProcessUnits items are currently selected
		self.Collaborators = []

	def SetupNotebook(self): # set up wx.Notebook used to display the data widgets. Currently not used
		# make dict of which widget sets are visible on each page
		WidgetList = {'Overview': self.ProjOverviewWidgets, 'Risk': self.RiskWidgets}
		assert WidgetList.keys() == ProjectInfoModelForDisplay.AvailAspects # make sure all aspects have widget lists
		self.MyNotebook = wx.Notebook(parent=self.ParentWindow, style=wx.NB_TOP)
		self.AspectPages = [] # build a list of Panels, one for each Aspect, to contain the widgets
		for ThisAspect in ProjectInfoModelForDisplay.AvailAspects:
			NewTab = wx.Panel(parent=self.MyNotebook)
			self.MyNotebook.AddPage(page=NewTab, text=ThisAspect)
			self.AspectPages.append(NewTab)
			# make a sizer for the page
			NewTab.MySizer = wx.GridBagSizer(vgap=0, hgap=0)
			# populate page with widgets
			self.PopulateSizer(ThisSizer=NewTab.MySizer, WidgetList=WidgetList[ThisAspect])
			# make widgets fit nicely into the page
			NewTab.SetSizer(NewTab.MySizer) # assigns sizer to this page
			NewTab.SetAutoLayout(True)
			NewTab.Fit()
		# put the notebook in a sizer of its own
		self.PanelSizer = wx.BoxSizer()
		self.PanelSizer.Add(self.MyNotebook, 1, wx.EXPAND)
		self.ParentWindow.SetSizer(self.PanelSizer)
		# select current tab
		self.MyNotebook.ChangeSelection(ProjectInfoModelForDisplay.AvailAspects.index(self.CurrentAspect))
		self.ParentWindow.TopLevelFrame.Refresh()

	def PrepareFullDisplay(self, XMLData): # instruct Viewport to fetch and set up all data needed to display project info

		def PopulateOverallData(XMLRoot):
			# extract data about the overall project from XMLRoot
			print("PD143 in PopulateOverallData with XML data: ", ElementTree.tostring(XMLRoot))

			TextItemInfo = [ ('ShortTitle', info.ProjNameTag), ('ProjNo', info.ProjNoTag),
				('Description', info.DescriptionTag) ]
			for Attrib, XMLTag in TextItemInfo:
				setattr(self, Attrib, XMLRoot.findtext(XMLTag, default=''))
			# populate data from XML tags with attributes
			AttribItemInfo = [ ('ProcessUnits', ProcessUnitForDisplay, info.ProcessUnitTag,
				[('ID', info.IDAttribName), ('UnitNumber', info.UnitNumberAttribName),
				 ('ShortName', info.ShortNameAttribName), ('LongName', info.LongNameAttribName)]),
				('Collaborators', CollaboratorForDisplay, info.CollaboratorTag,
				[('ID', info.IDAttribName), ('ShortName', info.ShortNameAttribName), ('LongName', info.LongNameAttribName)])]
			for ListName, ElClass, XMLTag, AttribList in AttribItemInfo:
				# find list of items to populate (e.g. ProcessUnits)
				ThisItemList = getattr(self, ListName)
				# fetch items from XML
				for ThisXMLEl in XMLRoot.findall(XMLTag):
					AttribDict = {}
					for ThisAttrib, AttribXMLName in AttribList: # fetch all required attribs from the XML tag
						AttribDict[ThisAttrib] = ThisXMLEl.get(AttribXMLName, '')
					ThisItemList.append(ElClass(ProjInfoViewport=self, Proj=self.Proj, **AttribDict))
			self.ProcessUnitsToDisplay = self.ProcessUnits[:]
			self.ProcessUnitsToDisplay_NoTextFilter = self.ProcessUnits[:]

		# main procedure for PrepareFullDisplay()
		self.Wipe() # start with blank values
		PopulateOverallData(XMLData.find(self.InternalName)) # extract project data
#		self.MyNotebook.Show()
		# set up required widgets in the sizer, and populate them (all lines below aren't needed if we switch back to Notebook)
		self.SetWidgets()
#		self.PopulateSizer(ThisSizer=self.MainSizer)
		# set data panel to use this Viewport's sizer
		self.ParentWindow.SetSizer(self.MainSizer) # assigns DataPanelSizer to Data Panel
		self.ParentWindow.SetAutoLayout(True)
		self.MainSizer.Layout()
		self.ParentWindow.Fit()

	def InitializeWidgets(self):
		# create all wx widgets used in this model
		ParentWindow = self.ParentWindow
		# create a horizontal line that can be used as a separator
		self.Line7Cells = display_utilities.UIWidgetItem(wx.StaticLine(ParentWindow, -1, size=(550, 5), style=wx.LI_HORIZONTAL), NewRow=True,
								   ColLoc=0, ColSpan=7, LeftMargin=10, GapY=10,
								   Flags=wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER)
		# aspect selector buttons
		self.OverviewAspectB = display_utilities.UIWidgetItem(wx.Button(ParentWindow, -1, _('Overview')),
			Handler=lambda Event: self.OnAspectButton(Event, Aspect='Overview'), Events=[wx.EVT_BUTTON],
			ColLoc=0, ColSpan=1, NewRow=True, LeftMargin=10, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
			Aspect='Overview')
		self.RiskAspectB = display_utilities.UIWidgetItem(wx.Button(ParentWindow, -1, _('Risk')),
			Handler=lambda Event: self.OnAspectButton(Event, Aspect='Risk'), Events=[wx.EVT_BUTTON],
			ColLoc=1, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, Aspect='Risk')
		self.FixedHeaderWidgets = [self.OverviewAspectB, self.RiskAspectB, self.Line7Cells]
		# Project overview widgets
		self.OverviewHeaderL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Project overview')),
			ColLoc=0, ColSpan=7, LeftMargin=10, GapY=20, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER_HORIZONTAL,
			NewRow=True, Font=self.Fonts['BigHeadingFont'], DisplayMethod='StaticHeader')
		self.ProjNoL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Project no')), ColLoc=0, ColSpan=1, LeftMargin=10,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, NewRow=True, DisplayMethod='StaticHeader')
		self.ProjNoW = display_utilities.UIWidgetItem(wx.TextCtrl(ParentWindow, -1), MinSizeY=25,
				Events=[], Handler=self.OnTextWidget,
				MinSizeX=100, ColLoc=1, ColSpan=2, DataAttrib='ProjNo', DisplayMethod='StaticFromText')
		self.ProjDescL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Description')), ColLoc=3, ColSpan=1,
							Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, DisplayMethod='StaticHeader')
		self.ProjDescW = display_utilities.UIWidgetItem(ExpandoTextCtrl(ParentWindow, -1), MinSizeY=25,
							Events=[], Handler=self.OnTextWidget, RowSpan=2,
							MinSizeX=300, ColLoc=4, ColSpan=2, DataAttrib='Description', DisplayMethod='StaticFromText')
		self.ProjShortNameL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Project name')),
			ColLoc=0, ColSpan=1, ShiftDown=1,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, DisplayMethod='StaticHeader')
		self.ProjShortNameW = display_utilities.UIWidgetItem(wx.TextCtrl(ParentWindow, -1), MinSizeY=25,
				Events=[], Handler=self.OnTextWidget, GapY=20, ShiftDown=1,
				MinSizeX=100, ColLoc=1, ColSpan=2, DataAttrib='ShortTitle', DisplayMethod='StaticFromText')
		self.UnitsL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Process units')), ColLoc=0, ColSpan=2,
									 LeftMargin=10, GapY=20, DisplayMethod='StaticHeader',
									 Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, NewRow=True,
									 Font=self.Fonts['SmallHeadingFont'])
		self.UnitsGrid = display_utilities.UIWidgetItem(display_utilities.DraggableGrid(ParentWindow,
			Viewport=self, ColumnInternalNames=ProjectInfoModelForDisplay.UnitsGridColNames), NewRow=True,
			SpecialDisplayMethod='PopulateUnitsGrid', ColLoc=0, ColSpan=3, RowSpan=3, LeftMargin=10, MinSizeX=400,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
			# RowSpan=3 to improve layout of buttons to the right of the grid
		self.DeleteUnitB = display_utilities.UIWidgetItem(wx.Button(ParentWindow, -1, _('Delete')),
						  Handler=self.OnDeleteUnitButton, Events=[wx.EVT_BUTTON], ColLoc=4, ColSpan=1,
						  Flags=wx.ALIGN_BOTTOM | wx.ALIGN_LEFT | wx.EXPAND)
		self.AddUnitB = display_utilities.UIWidgetItem(wx.Button(ParentWindow, -1, _('Add unit')), ShiftDown=1,
						  Handler=self.OnAddUnitButton, Events=[wx.EVT_BUTTON], ColLoc=4, ColSpan=1, GapY=20,
						  Flags=wx.ALIGN_TOP | wx.ALIGN_LEFT | wx.EXPAND)
		self.CollaboratorsL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Collaborators')), ColLoc=0, ColSpan=2,
									 LeftMargin=10, DisplayMethod='StaticHeader',
									 Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, NewRow=True,
									 Font=self.Fonts['SmallHeadingFont'])
		self.CollabCodeL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Access code')), ColLoc=0, ColSpan=1,
							Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, NewRow=True, DisplayMethod='StaticHeader')
		self.CollabCodeS = display_utilities.UIWidgetItem(wx.TextCtrl(ParentWindow, -1, _('')), ColLoc=1, ColSpan=1,
							Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT, ReadOnly=True)
		self.GetCollabCodeB = display_utilities.UIWidgetItem(wx.Button(ParentWindow, -1, _('Get code and invite\ncollaborator')),
						  Handler=self.OnGetCollabCodeButton, Events=[wx.EVT_BUTTON], ColLoc=2, ColSpan=1,
						  Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
		self.CollabNamesL = display_utilities.UIWidgetItem(wx.StaticText(ParentWindow, -1, _('Current\ncollaborators')),
			ColLoc=3, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT, DisplayMethod='StaticHeader')
		self.CollabNamesList = display_utilities.UIWidgetItem(wx.ListBox(ParentWindow, -1), MinSizeX=300,
			ColLoc=4, ColSpan=2, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
			SpecialDisplayMethod='PopulateCollaboratorsList')
		self.ProjOverviewWidgets = [self.OverviewHeaderL,
			self.ProjNoL, self.ProjNoW, self.ProjDescL, self.ProjDescW,
			self.ProjShortNameL, self.ProjShortNameW,
			self.UnitsL,
			self.UnitsGrid, self.DeleteUnitB, self.AddUnitB,
			self.CollaboratorsL,
			self.CollabCodeL, self.CollabCodeS, self.GetCollabCodeB, self.CollabNamesL, self.CollabNamesList]

		self.RiskWidgets = []

	def OnAspectButton(self, Event, Aspect): # user press on aspect selection button. Becomes redundant if using Notebook
		assert Aspect in self.AvailAspects
		self.CurrentAspect = Aspect
		self.SetWidgets()

	def OnTextWidget(self, Event=None, WidgetObj=None): # user type in text widget belonging to UIWidget object WidgetObj

		def DoTextWidget(WidgetObj, NewValue):
			# first, store undo information TODO
			# request PHA model to update value by sending message through zmq
			vizop_misc.SendRequest(Socket=self.D2CSocketREQ, Command='RQ_PI_ChangeValue',
				Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
				Attrib=self.PHAModelAttribNameHash[WidgetObj.DataAttrib], NewValue=NewValue)
			# set new value in Viewport
			setattr(self, WidgetObj.DataAttrib, NewValue)
			# write new (adjusted) value back to the widget
			getattr(WidgetObj, WidgetObj.DisplayMethod)(DataObj=self)

		assert (Event is not None) or (WidgetObj is not None) # one of these args must be supplied
		# find the data object associated with the wxwidget
#		if Event: # these 3 lines kept in case we ever want to call this handler directly instead of via CheckTextCtrlFocus()
#			wWidget = Event.GetEventObject()
#			WidgetObj = [w for w in self.WidgActive if w.Widget is wWidget][0]
		# check if value is locked
		if WidgetObj.ReadOnly: self.HandleAttemptToWriteReadOnlyWidget(WidgetObj)
		else: # not locked
			# get final value in the widget
			FinalValue = WidgetObj.Widget.GetValue()
			FinalValueAdjusted = FinalValue.strip() # this value will be stored
			# Test if the widget value is different from the existing value
			if utilities.TextWithoutSpecialChars(FinalValueAdjusted) != \
					utilities.TextWithoutSpecialChars(getattr(self, WidgetObj.DataAttrib)):
				DoTextWidget(WidgetObj, FinalValueAdjusted)

	def OnMoveGridRow(self, Event, FromRowIndex, ToRowIndex):
		# handler for user drag of grid row to reorder rows
		# Event: the wx.Event instance associated with the row move
		assert isinstance(FromRowIndex, int)
		assert isinstance(ToRowIndex, int)
		# check user changed the position of the row
		if FromRowIndex != ToRowIndex:
			# find out which grid was dragged (in case we have more than one on display)
			GridwxWidgetID = Event.GetId()
			GridWidget = [w for w in self.WidgActive if w.Widget.Id == GridwxWidgetID][0]
			if GridWidget == self.UnitsGrid: # user dragged row in Units grid
				UnitToMove = self.ProcessUnitsToDisplay[FromRowIndex]
				# strip the unit out of its old position
				self.ProcessUnits.remove(UnitToMove)
				# put the unit in its new position. TODO will the following line work correctly if list is filtered?
				# TODO same issue in SendRequest() call below
				self.ProcessUnits.insert(ToRowIndex, UnitToMove)
				self.RearrangeUnitLists() # reorder sub-lists of units
				# reapply filter, to update ProcessUnitsToDisplay lists (future)
#				self.OnDisplayUnitListFilterChoice(RefreshDisplay=False)
				# store Undo record; TODO consider if this should come before the preceding line, since sub-lists
				# lists are now updated; same for MoveToEnd and Swap
#				undo.AddToUndoList(Proj, undo.UndoItem(Undo40, Redo40, HumanText=_('reorder SIFs'),
#					SIFs=[SIFToMove], OldSIFIndices=OldSIFIndices, NewSIFIndices=[ToRowIndex],
#					DisplayedSIFs=Proj.SIFsDisplayedInSIFList[:]), Redoing=False, SuppressRepeats=False)
				self.UpdateUnitListDisplay()
				vizop_misc.SendRequest(Socket=self.D2CSocketREQ, Command='RQ_PI_ReorderUnit',
					   Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
					   Unit=UnitToMove.ID, NewIndex=str(ToRowIndex))
#				projects.SaveOnFly(Proj)

	def OnDeleteUnitButton(self, Event): # handle click on "delete unit" button
		# confirm that at least one unit is selected
		SelectedRows = self.UnitsGrid.Widget.GetSelectedRows()
		if bool(SelectedRows) and self.DisplDevice.TopLevelFrame.EditAllowed:
			# send command with Units = comma-separated list of IDs of units to remove
			vizop_misc.SendRequest(Socket=self.D2CSocketREQ, Command='RQ_PI_DeleteStructuredObj',
				Proj=self.Proj.ID, ObjectType='ProcessUnit',
				Units=','.join([self.ProcessUnitsToDisplay[i].ID for i in SelectedRows]))

	def OnAddUnitButton(self, Event): # handle click on "add unit" button
		# find out which is the highest numbered row in Units grid containing a selected cell
		IndividualSelectedCells = self.UnitsGrid.Widget.GetSelectedCells()
		SelectedRows = self.UnitsGrid.Widget.GetSelectedRows()
		SelectedBlockEnd = self.UnitsGrid.Widget.GetSelectionBlockBottomRight()
		HighestSelectedRow = max(max([r for (r, c) in IndividualSelectedCells] + [-1]), max(SelectedRows + [-1]),
			(SelectedBlockEnd + [(-1, -1)])[0][0])
		if self.DisplDevice.TopLevelFrame.EditAllowed:
			vizop_misc.SendRequest(Socket=self.D2CSocketREQ, Command='RQ_PI_AddStructuredObj',
				Proj=self.Proj.ID, ObjectType='ProcessUnit', Index=str(HighestSelectedRow + 1))

	def OnGetCollabCodeButton(self, Event): pass

	def HandleAttemptToWriteReadOnlyWidget(self, WidgetObj): pass

	def OnChangeNotebookTab(self, Event): pass
		# don't forget to clear self.WidgActive and possibly remove bindings

	def UpdateUnitListDisplay(self): # refresh unit list grid
		self.PopulateUnitsGrid()
		self.DisplDevice.Layout() # refresh sizer to handle any size changes

	def RearrangeUnitLists(self):
		# reorder selective unit lists to match the order in self.ProcessUnits
		# needs calling after any operation that changes the unit order in self.ProcessUnits
		self.ProcessUnitsToDisplay = [s for s in self.ProcessUnits if s in self.ProcessUnitsToDisplay]
		self.ProcessUnitsToDisplay_NoTextFilter = [s for s in self.ProcessUnits if
			s in self.ProcessUnitsToDisplay_NoTextFilter]
		self.SelectedUnits = [s for s in self.ProcessUnits if s in self.SelectedUnits]

	def PopulateCollaboratorsList(self, Font):
		# populate collaborator listbox widget with names of collaborators
		self.CollabNamesList.Widget.Set([ThisCollab.ShortName for ThisCollab in self.Collaborators])
		if Font: self.CollabNamesList.Widget.SetFont(Font)

	def SetWidgets(self):
		# set Data panel for editing of project information. Becomes redundant if using Notebook
		# First, remove and unbind all existing widgets
		self.RemoveWidgets()
		# Fill with required widgets
		MyWidgetList = {'Overview': self.ProjOverviewWidgets, 'Risk': self.RiskWidgets}[self.CurrentAspect]
		self.PopulateSizer(self.MainSizer, self.FixedHeaderWidgets + MyWidgetList)
		self.DisplDevice.FitInside() # makes scrollbars dis/appear as required
		self.SetAspectButtonStati()

	def RemoveWidgets(self):
		# remove all current widgets from data panel. Becomes redundant if using Notebook
		self.MainSizer.Clear(deleteWindows=False) # remove all widgets from sizer, including Gaps
		for w in self.WidgActive:
			for wEvent in w.Events: # remove bindings
				self.DisplDevice.Unbind(wEvent, w.Widget)
			w.Widget.Hide()
			# if w is temporary, destroy or trash the wx widget it contains (to avoid memory leak)
			if w.Lifespan == 'Destroy': w.Widget.Destroy()
		self.WidgActive = []
		self.MainSizer.Layout() # refresh sizer to remove old widgets

	def SetAspectButtonStati(self): # set un/pressed status of aspect buttons at top of data panel. Redundant (now using Notebook)
		# Currently sets selected button text to bold. Setting button colour doesn't work in macOS.
		for ThisWidget in self.FixedHeaderWidgets:
			if hasattr(ThisWidget, 'Aspect'):
				FontToUse = {True: self.Fonts['SmallHeadingFont'],
					False: self.Fonts['NormalFont']}[ThisWidget.Aspect == self.CurrentAspect]
				ThisWidget.Widget.SetFont(FontToUse)

	def PopulateSizer(self, ThisSizer, WidgetList=[]):
		# populate MainSizer with widgets appropriate for the required aspect, and set values and event handlers
		# assumes previous widgets in sizer have already been removed and hidden
		RowBase = 0 # which row of widgets in WidgetList we are filling
		ThisRowSpan = 1 # how many sizer rows are taken up by this row of widgets
		GapYAdded = False
		for w in WidgetList:
			# check whether widget should be shown
			if True: # placeholder for possible future conditional
				if w.NewRow or GapYAdded: # start a new row (sizer also treats y-gap as a row)
					RowBase += ThisRowSpan # skip forward the required number of rows
					if GapYAdded:
						RowBase += 1 # leave an empty sizer row for the GapY
						GapYAdded = False # reset flag
					ThisRowSpan = 1 # reset for new row
				# put widgets in sizer
				ThisSizer.Add(w.Widget, pos=(RowBase + w.ShiftDown + w.RowOffset, w.ColLoc + w.ColOffset),
					span=(w.RowSpan, w.ColSpan), flag=w.Flags | wx.LEFT, border=w.LeftMargin)
				# set widget minimum size, if required
				if (w.MinSizeX is not None) and (w.MinSizeY is not None):
					ThisSizer.SetItemMinSize(w.Widget, (w.MinSizeX, w.MinSizeY) )
				ThisRowSpan = max(ThisRowSpan, w.RowSpan)
				# set foreground and background colours - in case previously set
				w.Widget.SetForegroundColour(wx.NullColour)
				if w.NeedsHighlight:
					w.Widget.SetBackgroundColour(self.DisplDevice.ColScheme.BackHighlight)
					w.NeedsHighlight = False # to ensure no highlight next time widget is drawn
				else: w.Widget.SetBackgroundColour(wx.NullColour)
				# add y-gap in sizer, if required
				if w.GapY > 0:
					ThisSizer.Add( (10, w.GapY),
						pos=(RowBase + w.RowOffset + ThisRowSpan, w.ColLoc + w.ColOffset) )
					GapYAdded = True # flag to ensure we start new row and skip over sizer row containing gap
				# put widgets in "currently visible" list (for use in CheckTextCtrlFocus)
				self.WidgActive.append(w)
				# make widgets visible
				w.Widget.Show()
				# populate widgets with values and set fonts
				if w.DisplayMethod:
					getattr(w, w.DisplayMethod)(DataObj=self, Font=w.Font) # calls method of class UIWidget with string name w.DisplayMethod
				elif getattr(w, 'SpecialDisplayMethod', None):
					# use special method in this Viewport to populate widget
					getattr(self, w.SpecialDisplayMethod)(Font=w.Font)
				# set widget event handlers
				if w.Handler:
					for Event in w.Events:
						w.Widget.Bind(Event, w.Handler)
				if getattr(w, 'GapX', 0): # add empty space to the left of this widget
					ThisSizer.Add( (w.GapX, 10), pos=(RowBase + w.RowOffset, w.ColLoc + w.ColOffset - 1) )
		ThisSizer.Layout() # refresh sizer
		self.DisplDevice.FitInside() # trying to make the panel resize to fill the available space

	def RenderInDC(self, DC, FullRefresh=True):
		# draw display of project info in DC
		# FullRefresh (bool): whether to completely redraw the model
		# As this model mainly uses native widgets, it's rendered using a sizer in the display device, instead of drawing in the DC
		pass # TODO

	def AllClickableObjects(self, **Args): # return list of clickable graphical objects (not native widgets)
		return []

	def PopulateUnitsGrid(self, **Args): # special display method for Units grid
		# put Unit data into the grid widget of UnitsGrid for SIF list display
		# self.UnitsGrid is the UIWidget instance; GridWidget is the wx widget object
		# first, empty the data table and remove existing data from the grid
		GridWidget = self.UnitsGrid.Widget
		GridWidget.ClearSelection() # this must come before ClearGrid()
		OldNumberOfRows = GridWidget.DataTable.GetNumberRows()
		GridWidget.DataTable.data = []
		GridWidget.DataTable.rowLabels = []
		GridWidget.DataTable.colLabels = []
		GridWidget.ClearGrid()
		self.ProcessUnitsToDisplay = self.ProcessUnits[:] # display all process units (this is to allow possible future
			# filtering of process units)
		self.ProcessUnitsToDisplay_NoTextFilter = self.ProcessUnits[:] # for future filtering on a text
		# populate column labels
		ColLabelHumanNames = {'UnitNumber': _('Unit number'), 'ShortName': _('Short name'), 'LongName': _('Full name')}
		ColHorizAlignments = {'UnitNumber': wx.ALIGN_CENTER, 'ShortName': wx.ALIGN_LEFT, 'LongName': wx.ALIGN_LEFT}
		GridWidget.DataTable.colLabels = [ColLabelHumanNames[ThisColName] for ThisColName in self.UnitsGridColNames]
		# set cell alignments per column
		for ThisColIndex, ThisColLabel in enumerate(GridWidget.DataTable.identifiers):
			AttrObj = wx.grid.GridCellAttr()
			AttrObj.SetAlignment(hAlign=ColHorizAlignments[ThisColLabel], vAlign=wx.ALIGN_TOP)
			GridWidget.SetColAttr(ThisColIndex, AttrObj)
		for RowIndex, ThisUnit in enumerate(self.ProcessUnitsToDisplay):
			GridWidget.DataTable.rowLabels.append(self.ProcessUnits.index(ThisUnit) + 1)  # populate row serial number
			ThisRow = {}
			UnitNumberToDisplay = ThisUnit.UnitNumber.strip()
			if not UnitNumberToDisplay: UnitNumberToDisplay = _('<Undefined>')
			ShortNameToDisplay = ThisUnit.ShortName.strip()
			if not ShortNameToDisplay: ShortNameToDisplay = _('<Undefined>')
			LongNameToDisplay = ThisUnit.LongName.strip()
			if not LongNameToDisplay: LongNameToDisplay = _('<Undefined>')
			ThisRow['UnitNumber'] = UnitNumberToDisplay
			ThisRow['ShortName'] = ShortNameToDisplay
			ThisRow['LongName'] = LongNameToDisplay
			# put data into table
			GridWidget.DataTable.data.append(ThisRow)
			# select row if appropriate
			if ThisUnit in self.SelectedUnits: GridWidget.SelectRow(RowIndex, addToSelected=True)
		# update the grid object: tell it to add or delete rows according to whether there are more or less than last time
		GridWidget.BeginBatch()
		if len(self.ProcessUnitsToDisplay) > OldNumberOfRows:
			GridWidget.ProcessTableMessage(wx.grid.GridTableMessage(GridWidget.DataTable,
																	wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,
																	len(self.ProcessUnitsToDisplay) - OldNumberOfRows))
		elif len(self.ProcessUnitsToDisplay) < OldNumberOfRows:
			GridWidget.ProcessTableMessage(wx.grid.GridTableMessage(GridWidget.DataTable,
																	wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED,
																	OldNumberOfRows - len(self.ProcessUnitsToDisplay),
																	OldNumberOfRows - len(self.ProcessUnitsToDisplay)))
		GridWidget.EndBatch()
		# set grid size
		PanelSizeX, PanelSizeY = self.DisplDevice.GetSize()
		VertScrollbarXAllowanceInPx = 10  # x-size to allow for DataPanel's scrollbar
		# define amount of width to allocate to each column. Row label column gets 1.0
		ColRelativeWidths = {'UnitNumber': 3.0, 'ShortName': 3.0, 'LongName': 8.0}
		# calculated grid X size, taking up half of available width and allowing X space for margins & panel's scrollbar
		TargetGridSizeX = 0.5 * (PanelSizeX - (self.UnitsGrid.LeftMargin * 2) - VertScrollbarXAllowanceInPx)
		# TotalRelativeWidth = 1.0 + reduce(lambda a, b: a + b, ColRelativeWidths.values()) # old way with reduce(), RIP
		TotalRelativeWidth = 1.0 + sum(ColRelativeWidths.values())
		GridWidget.SetColMinimalAcceptableWidth(20)  # minimum width to which user can resize columns
		for ThisColName in ColRelativeWidths.keys():
			GridWidget.SetColSize(GridWidget.DataTable.identifiers.index(ThisColName),
								  TargetGridSizeX * ColRelativeWidths[ThisColName] / TotalRelativeWidth)
		GridWidget.SetRowLabelSize(TargetGridSizeX / TotalRelativeWidth) # row label column
		# check if we need scrollbars for the grid, and set them up
		GridSize = GridWidget.GetEffectiveMinSize()
		GridWidthInPx, GridHeightInPx = GridSize.width, GridSize.height
		if GridHeightInPx > PanelSizeY - 50:  # -50 is to allow for widgets above the grid
			GridWidget.SetScrollbars(20, 20, int(GridWidthInPx / 20), int(GridHeightInPx / 20), 0, 0)
			# scroll grid to ensure first currently selected unit is visible, if any
			if self.SelectedUnits:
				GridWidget.GoToCell(row=self.ProcessUnitsToDisplay.index(self.SelectedUnits[0]), col=0)
		# switch on grid editing if user is allowed to edit data
		CanEditGrid = self.DisplDevice.TopLevelFrame.EditAllowed
		GridWidget.EnableEditing(edit=CanEditGrid)
		if CanEditGrid:
			# set editor to use for each editable cell, and bind edit handler
			for ThisRow in range(len(self.ProcessUnitsToDisplay)):
				for ThisCol in range(len(self.UnitsGridColNames)):
					GridWidget.SetCellEditor(row=ThisRow, col=ThisCol, editor=wx.grid.GridCellTextEditor())
			GridWidget.Bind(wx.grid.EVT_GRID_CELL_CHANGE, lambda Event: self.OnEndEditGridCell(Event, Grid=GridWidget))

	def OnEndEditGridCell(self, Event, Grid): # handler for 'end editing grid cell"
		# Grid attrib: which grid wxWidget is edited (in case we have more than one grid)
		assert isinstance(Grid, display_utilities.DraggableGrid)
		# get unit edited, attrib edited and new value
		GridRow = Event.GetRow()
		GridCol = Event.GetCol()
		UnitEdited = self.ProcessUnits[GridRow]
		AttribNameEdited = self.UnitsAttribNamesPerGridCol[GridCol]
		NewValue = Grid.GetCellValue(row=GridRow, col=GridCol).strip()
		# check if user changed the value
		if NewValue != getattr(UnitEdited, AttribNameEdited):
			# get which kind of object was edited
			# ObjectKind: hash of wxWidget to name of object kind that was edited
			ObjectKind = {self.UnitsGrid.Widget: 'ProcessUnit'}
			# request PHA model to update value by sending message through zmq
			vizop_misc.SendRequest(Socket=self.D2CSocketREQ, Command='RQ_PI_ChangeValueInStructuredObj',
				Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID, ObjectType=ObjectKind[Grid],
				Instance=UnitEdited.ID, Attrib=AttribNameEdited, NewValue=NewValue)
			# write new value back to the grid
			Grid.SetCellValue(GridRow, GridCol, NewValue)

	def CheckTextCtrlFocus(self):
		# check which, if any, TextCtrl or ExpandoTextCtrl currently has focus, and call handler if a TextCtrl has
		# lost focus. We were previously using wx.EVT_KILL_FOCUS for this purpose.
		# This procedure is a workaround for Windows8.1 choking when wx.EVT_KILL_FOCUS is raised (no similar problem
		# in OS X 10.10).
		# first, find out which TextCtrl is focused
		NowFocused = ([w for w in self.WidgActive if isinstance(w.Widget, (wx.TextCtrl, ExpandoTextCtrl))
			if w.Widget.HasFocus()] + [None])[0]
		# has a TextCtrl lost focus?
		if hasattr(self, 'LastTextCtrlFocused'):
			# get UIWidget item that had focus last time this procedure ran (only TextCtrl's)
			LastWidget = self.LastTextCtrlFocused
			if LastWidget: # a TextCtrl had focus before
				if (LastWidget != NowFocused) and (LastWidget in self.WidgActive) and (LastWidget.Handler is not None)\
						and not getattr(LastWidget, 'SkipLoseFocus', False):
					# SkipLoseFocus means "ignore me when I lose focus"
					# Focus has changed, and the previously focused widget is still onscreen: call its handler
					LastWidget.Handler(Event=None, WidgetObj=LastWidget)
		# save focused TextCtrl (if any) for next time
		setattr(self, 'LastTextCtrlFocused', NowFocused)

	def ReleaseDisplayDevice(self, DisplDevice, **Args): # wrap-up actions needed when display device is no longer
		# showing this Viewport
		self.RemoveWidgets()
#		self.MyNotebook.Hide()
