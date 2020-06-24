# -*- coding: utf-8 -*-
# Module assoc_text_view: part of Vizop, (c) 2020 xSeriCon
# Codes a Viewport to display associated texts, i.e. action items and parking lot items

# library modules
import os, os.path, wx, platform # wx provides basic GUI functions
import xml.etree.ElementTree as ElementTree # XML handling

import core_classes, project_display, vizop_misc, info, utilities, faulttree, display_utilities
from project_display import EditPanelAspectItem
from display_utilities import UIWidgetItem

class PHAElementItem(object):
	# proxy for a PHA element. Provides information required to display info about the element, and to jump to it

	def __init__(self, ElementKindHumanName='', ElementHumanName='', ElementNumber='', HostKindHumanName='',
		HostHumanName='', ElementID='', HostID=''):
		# ElementKindHumanName: name of the kind of element, e.g. "initiating event"
		# ElementHumanName: name of the actual element, e.g. "Pump P-100 trips"
		# ElementNumber: currently displayed numbering of the element
		# HostKindHumanName: name of the kind of PHA model containing the element, e.g. "Fault Tree"
		# HostHumanName: name of the actual host PHA model, e.g. "SIF UC-1000"
		# ElementID: ID of the element
		# HostID: ID of the host PHA model
		assert isinstance(ElementKindHumanName, str)
		assert isinstance(ElementHumanName, str)
		assert isinstance(ElementNumber, str)
		assert isinstance(HostKindHumanName, str)
		assert isinstance(HostHumanName, str)
		assert isinstance(ElementID, str)
		assert isinstance(HostID, str)
		object.__init__(self)
		self.ElementKindHumanName = ElementKindHumanName
		self.ElementHumanName = ElementHumanName
		self.ElementNumber = ElementNumber
		self.HostKindHumanName = HostKindHumanName
		self.HostHumanName = HostHumanName
		self.ElementID = ElementID
		self.HostID = HostID

class AssocTextItemInDisplay(object):
	# data for associated text items for display. Reflects data held in the actual associated text items in datacore

	def __init__(self):
		object.__init__(self)
		self.ID = ''
		print('AT47 reminder, need to fetch ID of action items')
		self.Content = ''
		self.Numbering = ''
		self.FilteredIn = True # bool; whether this item shows up in the current filters. Defined only if filters are applied.
		self.Selected = False # bool; whether this item is currently selected by the user
		self.PHAElements = [] # list of PHAElementItem instances; all elements in which this AT appears

class AssocTextListViewport(display_utilities.ViewportBaseClass):
	# defines a viewport that lists associated texts for the whole project
	IsBaseClass = False
	InternalName = 'AssocTextList' # unique per class, used in messaging
	HumanName = _('Action item/parking lot list')
	PreferredKbdShortcut = 'A'
	NewPHAObjRequired = None # which datacore PHA object class this Viewport spawns on creation.
		# Should be None as the model doesn't create a PHA object
	# VizopTalks message when a new associated text list is created.
	# NB don't set Priority here, as it is overridden in DoNewViewportCommand()
	NewViewportVizopTalksArgs = {'Title': 'Action items/Parking lot list',
		'MainText': ''}
	NewViewportVizopTalksTips = []
	InitialEditPanelMode = 'Widgets'
	MinZoom = 0.1 # min and max zoom factors allowed for this Viewport
	MaxZoom = 9.99
	MenuCommandsAvailable = ['ShowActionItems'] # InternalNames of menu commands to enable when this Viewport is visible

	def __init__(self, Proj, PHAObjID, DisplDevice, ParentWindow, Fonts, SystemFontNames, **Args):
		# __init__ for class AssocTextListViewport
		# Args must include: OriginatingViewport (Viewport instance), AssocTextKind (str)
		# PHAObjID will be None, as this Viewport is at project level, not related to a specific PHA object
		assert isinstance(Args['OriginatingViewport'], display_utilities.ViewportBaseClass)
		assert Args['AssocTextKind'] in ['ActionItems', 'ParkingLot']
		display_utilities.ViewportBaseClass.__init__(self, Proj=Proj, PHAObjID=PHAObjID, DisplDevice=DisplDevice,
			ParentWindow=ParentWindow, **Args)
		self.SystemFontNames = SystemFontNames
		self.AssocTextKind = Args['AssocTextKind']
		# get connection to originating Viewport
		self.OriginatingViewport = Args['OriginatingViewport']
		# do initial setup of display
		self.SetupViewport(HostPanel=DisplDevice, Fonts=Fonts,
			SystemFontNames=SystemFontNames, DateChoices=Args['DateChoices'])
		# initialize attributes
		self.AssocTexts = [] # list of AssocTextItemInDisplay instances
		self.TextFilterValue = '' # currently applied text filter
		self.ActionChoices = []  # list of ChoiceItem instances; choices currently offered in Action choice box
		self.FilterApplied = False # whether filter is currently applied to AT display
		self.FilterText = '' # filter text currently applied to AT display; might not be the same as contents of TextCtrl
		self.InitializeActionChoices()

	def InitializeActionChoices(self):
		self.PromptOption = core_classes.ChoiceItem(XMLName='Prompt', HumanName=_('Select an action...'), Applicable=True)
		self.DeleteUnusedATsOption = core_classes.ChoiceItem(XMLName='DeleteUnused', HumanName=_('Delete unused items'))
		self.ExportAllOption = core_classes.ChoiceItem(XMLName='ExportAll', HumanName=_('Export all items'))
		self.ExportFilteredOption = core_classes.ChoiceItem(XMLName='ExportFiltered', HumanName=_('Export filtered items'))
		self.ExportSelectedOption = core_classes.ChoiceItem(XMLName='ExportSelected', HumanName=_('Export selected items'))
		self.AddToCurrentElementOption = core_classes.ChoiceItem(XMLName='AddToCurrent',
			HumanName=_('Add selected items to current element'))
		# make list of all possible options. Options will be displayed in the listed order
		self.AllActionChoices = [self.PromptOption, self.DeleteUnusedATsOption, self.ExportAllOption,
			self.ExportFilteredOption, self.ExportSelectedOption, self.AddToCurrentElementOption]

	def SetupViewport(self, HostPanel, Fonts, SystemFontNames, DateChoices):
		# setup sizers and widgets

		# TODO we will need a method to "re-setup viewport" when the Viewport is moved to a different display device.
		# This is because all the wx widgets belong to the panel. So they will have to be destroyed and remade.
		# This is probably a better approach than destroying and remaking the entire Viewport, so that references to
		# the Viewport object remain valid.

		def SetupHeaderSizer(HostPanel):
			# set up widgets for header. MainHeaderLabel is set in self.Prefill()
			# HostPanel: a wx.Panel instance. Widgets will be set to have HostPanel as parent.
			self.MainHeaderLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, ''),
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapX=20, GapY=10,
				ColLoc=1, ColSpan=10, Font=Fonts['BigHeadingFont'], NewRow=True)
			self.TextFilterLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, _('Filter on text:')),
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
#				ColLoc=1, ColSpan=1, NewRow=True)
				ColLoc=1, ColSpan=1)
			self.TextFilterText = UIWidgetItem(wx.TextCtrl(HostPanel, -1, style=wx.TE_PROCESS_ENTER),
				MinSizeY=25, Events=[wx.EVT_TEXT_ENTER], Handler=self.OnFilterText, GapX=10,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=3, ColSpan=1, DisplayMethod='StaticFromText')
			self.ActionLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, _('Select action:')),
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapX=20,
				ColLoc=5, ColSpan=1)
			self.ActionChoice = UIWidgetItem(wx.Choice(HostPanel, -1, size=(180, 25),
				choices=[]), GapX=10,
				Handler=self.OnActionChoice, Events=[wx.EVT_CHOICE], ColLoc=7, ColSpan=1)
			self.ActionGoButton = UIWidgetItem(wx.Button(HostPanel, -1, _('Go')),
				Handler=self.OnActionGoButton, Events=[wx.EVT_BUTTON],
				ColLoc=8, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.FinishedButton = UIWidgetItem(wx.Button(HostPanel, -1, _('Finished')), GapX=20,
				Handler=self.OnFinishedButton, Events=[wx.EVT_BUTTON],
				ColLoc=10, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.FixedWidgets = [self.MainHeaderLabel,
				self.TextFilterLabel, self.TextFilterText, self.ActionLabel, self.ActionChoice, self.ActionGoButton,
				self.FinishedButton]
			# make list of widgets that need to be bound to their handlers in ActivateWidgetsInPanel() and deleted on exit
			self.WidgetsToActivate = [self.MainHeaderLabel,
				self.TextFilterLabel, self.TextFilterText, self.ActionLabel, self.ActionChoice, self.ActionGoButton,
				self.FinishedButton]

		def SetupAssocTextListSizer(): pass

		# start of SetupViewport()
		self.MainSizer = wx.BoxSizer(orient=wx.VERTICAL)
		self.HeaderSizer = wx.GridBagSizer(vgap=0, hgap=0) # for header widgets
		self.AssocTextListSizer = wx.GridBagSizer(vgap=0, hgap=0) # for associated text list
		self.MainSizer.Add(self.HeaderSizer)
		self.MainSizer.Add(self.AssocTextListSizer)
		SetupHeaderSizer(HostPanel=HostPanel)
		SetupAssocTextListSizer()

	def OnFilterText(self, Event): # handle Enter key press in text filter TextCtrl
		pass

	def OnActionChoice(self, Event): # handle user selection in Action choice control
		pass

	def OnActionGoButton(self, Event): # handle user click on action Go button
		pass

	def OnFinishedButton(self, Event): # handle user click on Finished button
		print('AT165 in Finished button handler')
		self.StoreAttribsInProject()
		self.ExitViewportAndRevert()

	def PrepareFullDisplay(self, XMLTree):
		# display associated text list in our display device
		# first, unpack data from datacore
		self.UnpackDataFromDatacore(XMLTree)
		# build the display: prefill widgets and activate it
		self.ApplyFilters() # mark each associated text as whether currently visible, based on current filters
		self.Prefill(SystemFontNames=self.SystemFontNames)
		self.SetWidgetVisibility()
		# place header widgets in sizer, bind event handlers and register keyboard shortcuts
		display_utilities.ActivateWidgetsInPanel(Widgets=self.WidgetsToActivate, Sizer=self.HeaderSizer,
			ActiveWidgetList=[w for w in self.FixedWidgets if w.IsVisible],
			DefaultFont=self.DisplDevice.TopLevelFrame.Fonts['NormalWidgetFont'],
			HighlightBkgColour=self.DisplDevice.TopLevelFrame.ColScheme.BackHighlight)
		# display main sizer (containing all the visible widgets) in the display device
		self.DisplDevice.SetSizer(self.MainSizer)

	def UnpackDataFromDatacore(self, XMLTree):
		print('AT172 in UnpackDataFromDatacore')
		self.AssocTexts = [] # start with empty list of AT items
		# find the starting tag
		StartTag = XMLTree.find(info.PHAModelRedrawDataTag)
		# confirm it came from this Viewport class
		assert StartTag.get(info.PHAModelTypeTag) == self.InternalName
		# find subelement containing the kind of associated text
		ATKindEl = StartTag.find(info.AssociatedTextKindTag)
		# confirm it indicates we received action items
		assert ATKindEl.text == 'ActionItems'
		# fetch tag for each action item in the project
		for ThisATTag in StartTag.findall(info.AssociatedTextTag):
			# make an associated text instance, and store it in the list
			ThisAT = AssocTextItemInDisplay()
			self.AssocTexts.append(ThisAT)
			# fetch associated item numbering
			ThisAT.Numbering = ThisATTag.text
			# fetch AT content, responsibility, deadline and status
			ThisAT.Content = ThisAT.findtext(info.ContentTag)
			ThisAT.Responsibility = ThisAT.findtext(info.CoResponsibilityntentTag)
			ThisAT.Deadline = ThisAT.findtext(info.DeadlineTag)
			ThisAT.Status = ThisAT.findtext(info.StatusTag)
			# fetch ID and display name for each PHA element using this AT, if any
			for ThisElUsingTag in ThisATTag.findall(info.PHAElementTag):
				ThisElUsing = PHAElementItem(ElementHumanName=ThisElUsingTag.text,
					ElementID=ThisElUsingTag.get(info.IDTag))
				ThisAT.PHAElements.append(ThisElUsing)

	def ApplyFilters(self):
		print('AT175 in ApplyFilters')

	def Prefill(self, SystemFontNames): # prefill widgets for associated text display
		# set header to e.g. "Showing 5 of 10 action items in the project"
		self.MainHeaderLabel.Widget.SetLabel(_('Showing %d of %d %s in the project') % \
			([i.FilteredIn for i in self.AssocTexts].count(True), len(self.AssocTexts),
			self.AssocTextName(Plural=bool(len(self.AssocTexts) - 1))))
		self.TextFilterText.Widget.ChangeValue(self.TextFilterValue)
		# set available choices in "action" choice box
		self.UpdateActionChoices()
		# enable action Go button if any actions are available, apart from the prompt
		self.ActionGoButton.Widget.Enable(len(self.ActionChoices) > 1)

	def SetWidgetVisibility(self, **Args):
		# set IsVisible attribs for all widgets
		for ThisWidget in self.FixedWidgets: ThisWidget.IsVisible = True

	def AssocTextName(self, Plural=True):
		# return (str) name of associated text kind; plural if Plural (bool)
		assert isinstance(Plural, bool)
		return [(_('action item'), _('action items')), (_('parking lot item'), _('parking lot items'))][\
			['ActionItems', 'ParkingLot'].index(self.AssocTextKind)][int(Plural)]

	def UpdateActionChoices(self): # update choices available in "Action" choice box
		# set "Applicable" flag for each possible choice
		# enable "Delete unused ATs" option if not all ATs have associated PHA elements
		self.DeleteUnusedATsOption.Applicable = not all(i.PHAElements for i in self.AssocTexts)
		# enable "Export all" option if there are any ATs
		self.ExportAllOption.Applicable = bool(self.AssocTexts)
		# enable "Export filtered" option if filtering is applied and any ATs showed up in the filter
		self.ExportFilteredOption.Applicable = self.FilterApplied and any(i.FilteredIn for i in self.AssocTexts)
		# enable "Export selected" option and "Add to current element" option if any ATs are selected
		self.ExportSelectedOption.Applicable = self.AddToCurrentElementOption.Applicable = any(i.Selected for i in self.AssocTexts)
		# make list of currently available options
		self.ActionChoices = [a for a in self.AllActionChoices if a.Applicable]
		# set the text of the prompt option, depending on whether other options are available
		self.PromptOption.HumanName = _('Select an action...') if len(self.ActionChoices) > 1 \
			else _('(No actions available)')
		# set available options in choice box
		self.ActionChoice.Widget.Set([a.HumanName for a in self.ActionChoices])
		# set the current option as the prompt
		self.ActionChoice.Widget.SetSelection(self.ActionChoices.index(self.PromptOption))

	@classmethod
	def GetFullRedrawData(cls, Viewport=None, ViewportClass=None, **Args):
		# a datacore method. Provide data for redraw of this Viewport
		# return the data as XML string

		def MakeAssocTextLookupTable(Proj):
			# make and return dictionary with keys = action items, values = list of PHA elements containing the action item
			ATTable = {}
			for ThisPHAElement in Proj.WalkOverAllPHAElements():
				for ThisAT in getattr(ThisPHAElement, 'ActionItems', []):
					if ThisAT in ATTable: ATTable[ThisAT].append(ThisPHAElement)
					else: ATTable[ThisAT] = [ThisPHAElement]
			return ATTable

		# start of GetFullRedrawData()
		print('AT213 in GetFullRedrawData')
		Proj = Args['Proj']
		# get a lookup table of all action items in the project
		ATTable = MakeAssocTextLookupTable(Proj=Proj)
		# First, make the root element
		RootElement = ElementTree.Element(info.PHAModelRedrawDataTag)
		RootElement.set(info.PHAModelTypeTag, cls.InternalName)
		# add a subelement containing the kind of associated text
		ATKindEl = ElementTree.SubElement(RootElement, info.AssociatedTextKindTag)
		ATKindEl.text = 'ActionItems'
		AssocTextMasterList = Proj.ActionItems # identify master list containing all associated text items to show
		# add a tag for each action item in the project
		for ThisAssocTextItem in AssocTextMasterList:
			ATEl = ElementTree.SubElement(RootElement, info.AssociatedTextTag)
			# set element text = associated item numbering
			ATEl.text = ThisAssocTextItem.Numbering.HumanValue(PHAItem=ThisAssocTextItem, Host=AssocTextMasterList)[0]
			# make subelements for AT content, responsibility, deadline and status
			ContentEl = ElementTree.SubElement(ATEl, info.ContentTag)
			ContentEl.text = ThisAssocTextItem.Content
			ResponsibilityEl = ElementTree.SubElement(ATEl, info.ResponsibilityTag)
			ResponsibilityEl.text = ThisAssocTextItem.Responsibility
			DeadlineEl = ElementTree.SubElement(ATEl, info.DeadlineTag)
			DeadlineEl.text = ThisAssocTextItem.Deadline
			StatusEl = ElementTree.SubElement(ATEl, info.StatusTag)
			StatusEl.text = ThisAssocTextItem.Status
			# make subelement for each PHA element using this AT, if any. Set its text to the displayable name of the
			# element. Add an attribute containing the PHA element's ID.
			for ThisPHAElement in ATTable.get(ThisAssocTextItem, []):
				PHAElUsingEl = ElementTree.SubElement(ATEl, info.PHAElementTag)
				PHAElUsingEl.text = ThisPHAElement.HostPHAObj.HumanName + ' ' + \
					ThisPHAElement.Numbering.HumanValue(PHAItem=ThisPHAElement, Host=ThisPHAElement.Siblings)[0]
				PHAElUsingEl.set(info.IDTag, ThisPHAElement.ID)

		# populate any extra tags requested (currently used by undo for specifying display-specific tags)
		if 'ExtraXMLTagsAsDict' in Args:
			assert isinstance(Args['ExtraXMLTagsAsDict'], dict)
			for (ThisTag, ThisText) in Args['ExtraXMLTagsAsDict'].items():
				assert isinstance(ThisTag, str)
				assert isinstance(ThisText, str)
				ThisElement = ElementTree.SubElement(RootElement, ThisTag)
				ThisElement.text = ThisText
		if 'ExtraXMLTagsAsTags' in Args:
			assert isinstance(Args['ExtraXMLTagsAsTags'], ElementTree.Element)
			RootElement.append(Args['ExtraXMLTagsAsTags'])
		# TODO add info.FTDisplayAttribTag with zoom and pan data
		print('AT270 ending GetFullRedrawData with RootElement: ', ElementTree.tostring(RootElement))
		return RootElement

	def AllClickableObjects(self, **Args):
		# no graphical objects requiring special mouse click handlers
		return []

	def RenderInDC(self, DC, **Args):
		# currently no graphics to render in a DC. For future, may provide a zoom tool
		pass

	def StoreAttribsInProject(self):
		# send request to datacore to store AT Viewport settings in project
#		ThisViewport = self.ParentFrame.TopLevelFrame.CurrentViewport
#		# gets string containing information about export required
#		ShowWhat, PageNumberWhere, ShowTexts = self.MakeAttribStrings()
		vizop_misc.SendRequest(Socket=self.C2DSocketREQ,
			Command='RQ_PR_UpdateAssocTextFullViewAttribs',
			Proj=self.Proj.ID, Viewport=self.ID,
			AssocTextKind=self.AssocTextKind, FilterText=self.FilterText,
			ATsSelected=','.join([AT.ID for AT in self.AssocTexts if AT.Selected]))
		# next TODO: make handler for this command in datacore
