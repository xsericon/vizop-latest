# -*- coding: utf-8 -*-
# Module assoc_text_view: part of Vizop, (c) 2020 xSeriCon
# Codes a Viewport to display associated texts, i.e. action items and parking lot items

# library modules
import os, os.path, wx, platform # wx provides basic GUI functions
import xml.etree.ElementTree as ElementTree # XML handling

import core_classes, project_display, vizop_misc, info, utilities, faulttree, display_utilities, undo, projects
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
		self.GridRow = None # row number in grid at which this item is currently displayed, or None if not displayed

	def GetWhereUsedHumanText(self):
		# get human-readable text showing PHA elements where this AT is used
		return '\n'.join([_('%s %s in %s' % (p.ElementHumanName, p.ElementNumber, p.HostHumanName))
			for p in self.PHAElements ])

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
		# make list of internal names of columns to show in AT grid list, in display order. Eventually, this should be persistent
		# This list is what defines the actual display order of columns
		self.ATListColInternalNames = ['Number', 'Content', 'Responsibility', 'Deadline', 'Status', 'WhereUsed']
		# can add 'Selected' to provide a checkbox column, partially constructed in the rest of the code. See notes in
		# spec file 391
		self.SetupViewport(HostPanel=DisplDevice, Fonts=Fonts,
			SystemFontNames=SystemFontNames, DateChoices=Args['DateChoices'])
		# initialize attributes
		self.AssocTexts = [] # list of AssocTextItemInDisplay instances
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
		# This is because all the wx widgets belong to the panel. So they will have to be destroyed and remade, or
		# alternatively try Widget.Reparent().
		# This is probably a better approach than destroying and remaking the entire Viewport, so that references to
		# the Viewport object remain valid.

		def SetupHeaderSizer(HostPanel):
			# set up widgets for header. MainHeaderLabel is set in self.Prefill()
			# HostPanel: a wx.Panel instance. Widgets will be set to have HostPanel as parent.
			# Attrib 'Sizer' in each widget indicates which sizer it should be added to
			# return WidgetsToActivate for this sizer
			self.MainHeaderLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, ''), Sizer=self.HeaderSizer,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapX=self.OverallLeftMargin, GapY=10,
				ColLoc=1, ColSpan=10, Font=Fonts['BigHeadingFont'], NewRow=True)
			self.TextFilterLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, _('Filter on text:')),
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, Sizer=self.HeaderSizer,
				ColLoc=1, ColSpan=1)
			self.TextFilterText = UIWidgetItem(wx.TextCtrl(HostPanel, -1, style=wx.TE_PROCESS_ENTER),
				MinSizeY=25, Events=[wx.EVT_TEXT_ENTER], Handler=self.OnFilterText, GapX=10, Sizer=self.HeaderSizer,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=3, ColSpan=1, DisplayMethod='StaticFromText')
			self.ActionLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, _('Select action:')), Sizer=self.HeaderSizer,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapX=20,
				ColLoc=5, ColSpan=1)
			self.ActionChoice = UIWidgetItem(wx.Choice(HostPanel, -1, size=(180, 25),
				choices=[]), GapX=10, Sizer=self.HeaderSizer,
				Handler=self.OnActionChoice, Events=[wx.EVT_CHOICE], ColLoc=7, ColSpan=1)
			self.ActionGoButton = UIWidgetItem(wx.Button(HostPanel, -1, _('Go')), Sizer=self.HeaderSizer,
				Handler=self.OnActionGoButton, Events=[wx.EVT_BUTTON],
				ColLoc=8, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.FinishedButton = UIWidgetItem(wx.Button(HostPanel, -1, _('Finished')), GapX=20, Sizer=self.HeaderSizer,
				Handler=self.OnFinishedButton, Events=[wx.EVT_BUTTON], GapY=40,
				ColLoc=10, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.ATListGrid = UIWidgetItem(display_utilities.DraggableGrid(Parent=HostPanel, Viewport=self,
				ColumnInternalNames=self.ATListColInternalNames),
				NewRow=True, ColLoc=1, ColSpan=11,
				Sizer=self.HeaderSizer,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT)
			self.HeaderFixedWidgets = [self.MainHeaderLabel,
				self.TextFilterLabel, self.TextFilterText, self.ActionLabel, self.ActionChoice, self.ActionGoButton,
				self.FinishedButton, self.ATListGrid]
			# return list of widgets that need to be bound to their handlers in ActivateWidgetsInPanel() and deleted on exit
			return [self.MainHeaderLabel,
				self.TextFilterLabel, self.TextFilterText, self.ActionLabel, self.ActionChoice, self.ActionGoButton,
				self.FinishedButton, self.ATListGrid]

#		def SetupAssocTextListSizer(HostPanel):
#			# set up associated text list grid widget
#			# return WidgetsToActivate for this sizer. No longer used - had trouble with both sizers drawn on top of
#			# each other, so now using HeaderSizer only
#			self.TestLabel = UIWidgetItem(wx.StaticText(HostPanel, -1, 'Test'), Sizer=self.HeaderSizer,
#				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapX=20, GapY=10,
#				ColLoc=1, ColSpan=10, Font=Fonts['BigHeadingFont'], NewRow=True)
#			self.ATListFixedWidgets = [self.ATListGrid]
#			self.ATListFixedWidgets = [self.ATListGrid, self.TestLabel]
#			self.ATListFixedWidgets = []
#			self.HeaderFixedWidgets.extend([self.TestLabel])
#			# return list to include in self.WidgetsToActivate
#			return [self.ATListGrid]
#			return [self.TestLabel]

		# start of SetupViewport()
		self.MainSizer = wx.BoxSizer(orient=wx.VERTICAL)
		self.HeaderSizer = wx.GridBagSizer(vgap=0, hgap=0) # for header widgets
		self.OverallLeftMargin = 20 # gap on left edge inside panel
#		self.AssocTextListSizer = wx.GridBagSizer(vgap=0, hgap=0) # for associated text list
		self.MainSizer.Add(self.HeaderSizer)
#		self.MainSizer.Add(self.AssocTextListSizer)
		self.WidgetsToActivate = SetupHeaderSizer(HostPanel=HostPanel)
#		self.WidgetsToActivate = SetupHeaderSizer(HostPanel=HostPanel) + SetupAssocTextListSizer(HostPanel=HostPanel)

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
		# place header widgets in header sizer, bind event handlers and register keyboard shortcuts
		display_utilities.ActivateWidgetsInPanel(
			Widgets=[w for w in self.WidgetsToActivate if w.Sizer is self.HeaderSizer], Sizer=self.HeaderSizer,
			ActiveWidgetList=[w for w in self.HeaderFixedWidgets if w.IsVisible],
			DefaultFont=self.DisplDevice.TopLevelFrame.Fonts['NormalWidgetFont'],
			HighlightBkgColour=self.DisplDevice.TopLevelFrame.ColScheme.BackHighlight)
		# display main sizer (containing all the visible widgets) in the display device
		self.DisplDevice.SetSizer(self.MainSizer)
		self.MainSizer.Layout()

	def UnpackDataFromDatacore(self, XMLTree):
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
			# fetch associated item ID and numbering
			ThisAT.ID = ThisATTag.findtext(info.AssociatedTextIDTag)
			ThisAT.Numbering = ThisATTag.text
			# fetch AT content, responsibility, deadline and status
			ThisAT.Content = ThisATTag.findtext(info.ContentTag)
			ThisAT.Responsibility = ThisATTag.findtext(info.ResponsibilityTag)
			ThisAT.Deadline = ThisATTag.findtext(info.DeadlineTag)
			ThisAT.Status = ThisATTag.findtext(info.StatusTag)
			# fetch ID and display name for each PHA element using this AT, if any
			for ThisElUsingTag in ThisATTag.findall(info.PHAElementTag):
				ThisElUsing = PHAElementItem(ElementHumanName=ThisElUsingTag.text,
					ElementID=ThisElUsingTag.get(info.IDTag))
				ThisAT.PHAElements.append(ThisElUsing)

	def ApplyFilters(self, FilterText='', FilterApplied=False):
		print('AT175 in ApplyFilters')

	def Prefill(self, SystemFontNames=None, CurrentAT=None): # prefill widgets for associated text display
		# set header to e.g. "Showing 5 of 10 action items in the project"
		# CurrentAT (AssocTextItemInDisplay instance or None): the AT the user is currently working with
		assert isinstance(CurrentAT, AssocTextItemInDisplay) or (CurrentAT is None)
		self.MainHeaderLabel.Widget.SetLabel(_('Showing %d of %d %s in the project') % \
			([i.FilteredIn for i in self.AssocTexts].count(True), len(self.AssocTexts),
			self.AssocTextName(Plural=bool(len(self.AssocTexts) - 1))))
		self.TextFilterText.Widget.ChangeValue(self.FilterText)
		# set available choices in "action" choice box
		self.UpdateActionChoices()
		# enable action Go button if any actions are available, apart from the prompt
		self.ActionGoButton.Widget.Enable(len(self.ActionChoices) > 1)
		# populate action items list
		self.PopulateATList(CurrentAT=CurrentAT)

	def SetWidgetVisibility(self, **Args):
		# set IsVisible attribs for all widgets
		for ThisWidget in self.HeaderFixedWidgets: ThisWidget.IsVisible = True
#		for ThisWidget in self.HeaderFixedWidgets + self.ATListFixedWidgets: ThisWidget.IsVisible = True

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

	def PopulateATList(self, CurrentAT=None):
		# populate AT list grid with AT items to be displayed, and select appropriate items
		# CurrentAT (AssocTextItemInDisplay instance or None): the AT the user is currently working with. AT list will be
		#	scrolled to ensure it's visible
		GridWidget = self.ATListGrid.Widget # get the wx grid widget
		# first, empty the data table and remove existing data from the grid
		GridWidget.ClearSelection() # this must come before ClearGrid()
		OldNumberOfRows = GridWidget.DataTable.GetNumberRows()
		GridWidget.DataTable.data = []
		GridWidget.DataTable.rowLabels = []
		GridWidget.DataTable.colLabels = []
		GridWidget.ClearGrid()
		# populate column labels. First, make hash table of column internal names to human names
		ColLabelHumanNameHash = {'Selected': _('Select'), 'Number': _('Action item\nnumber'), 'Content': _('Content'),
			'Responsibility': _('Responsibility'), 'Deadline': _('Deadline'), 'Status': _('Status'),
			'WhereUsed': _('Where used')}
		ColHorizAlignments = {'Selected': wx.ALIGN_CENTRE, 'Number': wx.ALIGN_RIGHT, 'Content': wx.ALIGN_LEFT,
			'Responsibility': wx.ALIGN_LEFT, 'Deadline': wx.ALIGN_LEFT, 'Status': wx.ALIGN_CENTRE,
			'WhereUsed': wx.ALIGN_LEFT}
		ColCellRenderers = {'Selected': wx.grid.GridCellBoolRenderer, 'Number': wx.grid.GridCellStringRenderer,
			'Content': wx.grid.GridCellAutoWrapStringRenderer,
			'Responsibility': wx.grid.GridCellStringRenderer, 'Deadline': wx.grid.GridCellStringRenderer,
			'Status': wx.grid.GridCellStringRenderer,
			'WhereUsed': wx.grid.GridCellStringRenderer}
		self.ColCellEditors = {'Selected': wx.grid.GridCellBoolEditor, 'Number': wx.grid.GridCellTextEditor,
			'Content': wx.grid.GridCellTextEditor,
			'Responsibility': wx.grid.GridCellTextEditor, 'Deadline': wx.grid.GridCellTextEditor,
			'Status': wx.grid.GridCellTextEditor,
			'WhereUsed': wx.grid.GridCellTextEditor}
		ColReadOnly = {'Selected': False, 'Number': True,
			'Content': False,
			'Responsibility': False, 'Deadline': False,
			'Status': False,
			'WhereUsed': True}
		GridWidget.DataTable.colLabels = [ColLabelHumanNameHash[ThisColName]
			for ThisColName in self.ATListColInternalNames]
		# set cell attributes per column, including alignment and read-only status
		for ThisColIndex, ThisColLabel in enumerate(GridWidget.DataTable.identifiers):
			AttrObj = wx.grid.GridCellAttr()
			AttrObj.SetAlignment(hAlign=ColHorizAlignments[ThisColLabel], vAlign=wx.ALIGN_TOP)
			AttrObj.SetReadOnly(isReadOnly=ColReadOnly[ThisColLabel])
			GridWidget.SetColAttr(ThisColIndex, AttrObj)
		# populate rows
		RowIndex = -1
		CurrentATRowIndex = None
		for ATIndex, ThisAT in enumerate(self.AssocTexts):
			if ThisAT.FilteredIn: # show this AT only if it meets filter criteria
				RowIndex += 1 # keep counter of rows populated in grid
				ThisAT.GridRow = RowIndex
				if ThisAT == CurrentAT: CurrentATRowIndex = RowIndex # store row of current AT, so we can scroll to it
				# set renderer and editor to show/edit each cell in required format (string, checkbox etc)
				# TODO optimization: use SetColAttr() to define attribs for entire columns instead of row by row
				for ThisColIndex, ThisColLabel in enumerate(GridWidget.DataTable.identifiers):
					GridWidget.SetCellEditor(col=ThisColIndex, row=RowIndex, editor=self.ColCellEditors[ThisColLabel]())
					GridWidget.SetCellRenderer(col=ThisColIndex, row=RowIndex, renderer=ColCellRenderers[ThisColLabel]())
				GridWidget.DataTable.rowLabels.append(str(ATIndex + 1)) # populate row serial number, irrespective of filter
#				# try to set column 0 as boolean
#				A = wx.grid.GridCellAttr()
#				A.SetEditor(wx.grid.GridCellBoolEditor())
#				A.SetRenderer(wx.grid.GridCellBoolRenderer())
#				GridWidget.DataTable.SetColAttr(col=0, attr=A)
				# populate fields
				ThisRow = {'Selected': ThisAT.Selected, 'Number': ThisAT.Numbering, 'Content': ThisAT.Content,
					'Responsibility': ThisAT.Responsibility, 'Deadline': ThisAT.Deadline, 'Status': ThisAT.Status,
					'WhereUsed': ThisAT.GetWhereUsedHumanText()}
				# put data into table
				GridWidget.DataTable.data.append(ThisRow)
				# select row if appropriate
				if ThisAT.Selected: GridWidget.SelectRow(RowIndex, addToSelected=True)
			else: # this AT is filtered out; mark it as not shown in the grid
				ThisAT.GridRow = None
		# update the grid object: tell it to add or delete rows according to whether there are more or less than last time
		NewNumberOfRows = RowIndex + 1
		GridWidget.BeginBatch()
		if NewNumberOfRows > OldNumberOfRows:
			GridWidget.ProcessTableMessage(wx.grid.GridTableMessage(GridWidget.DataTable,
				wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, NewNumberOfRows - OldNumberOfRows))
		elif NewNumberOfRows < OldNumberOfRows:
			GridWidget.ProcessTableMessage(wx.grid.GridTableMessage(GridWidget.DataTable,
				wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, OldNumberOfRows - NewNumberOfRows,
				OldNumberOfRows - NewNumberOfRows))
		GridWidget.EndBatch()

		# set grid size
		PanelSizeX, PanelSizeY = self.DisplDevice.GetSize()
		VertScrollbarXAllowanceInPx = 10  # x-size to allow for scrollbar
		# define amount of width to allocate to each column. Row label column gets 1.0 by definition
		ColRelativeWidths = {'Selected': 1.0, 'Number': 2.0, 'Content': 10.0,
						'Responsibility': 5.0, 'Deadline': 3.0, 'Status': 2.0,
						'WhereUsed': 6.0}
		# allow X space for margins and panel's scrollbar
		TargetGridSizeX = PanelSizeX - (self.OverallLeftMargin * 2) - VertScrollbarXAllowanceInPx
		TotalRelativeWidth = 1.0 + sum(ColRelativeWidths.values())
		GridWidget.SetColMinimalAcceptableWidth(20) # minimum width to which user can resize columns
		# set column initial widths
#		for ThisColName in ColRelativeWidths.keys():
		for ThisColName in self.ATListColInternalNames:
			GridWidget.SetColSize(GridWidget.DataTable.identifiers.index(ThisColName),
				TargetGridSizeX * ColRelativeWidths[ThisColName] / TotalRelativeWidth)
		GridWidget.SetRowLabelSize(TargetGridSizeX / TotalRelativeWidth) # row label column

		# check if we need scrollbars for the grid, and set them up
		# TODO it would be nice if we could use the VISIBLE (not total) size for the panel
		GridSize = GridWidget.GetEffectiveMinSize()
		GridWidthInPx, GridHeightInPx = GridSize.width, GridSize.height
		if GridHeightInPx > PanelSizeY - 50: # -50 is to allow for widgets above the grid
			# we need vertical scrollbar: set it up
			GridWidget.SetScrollbars(20, 20, int(GridWidthInPx / 20), int(GridHeightInPx / 20), 0, 0)
			# scroll grid to ensure current AT is visible, if filtered-in
			if CurrentATRowIndex is not None:
				GridWidget.GoToCell(row=CurrentATRowIndex, col=0)

		# set up event handlers
#		GridWidget.Bind(wx.grid.EVT_GRID_EDITOR_CREATED, self.OnEditorCreated)
		# may need EditorCreated handler for future implementation of checkbox column
		GridWidget.Bind(wx.grid.EVT_GRID_CELL_CHANGED, self.OnCellEdited)

	def OnCellEdited(self, Event):
		# handle user editing of a grid cell
		print('AT417 in OnCellEdited')
		print('AT418 new cell content detected: ', self.ATListGrid.Widget.GetCellValue(row=Event.Row, col=Event.Col))
		# below, AttribChanged contains hash of {column internal names, AT attrib names} in case either of them changes
		self.ChangeAssociatedText(AssociatedTextObj=[AT for AT in self.AssocTexts if AT.GridRow == Event.Row][0],
			ATRow=Event.Row,
			AttribChanged={'Content': 'Content', 'Responsibility': 'Responsibility', 'Deadline': 'Deadline',
				'Status': 'Status'}[self.ATListColInternalNames[Event.Col]],
			NewAttribContent=self.ATListGrid.Widget.GetCellValue(row=Event.Row, col=Event.Col).strip())

#	def OnEditorCreated(self, Event):
#		print('AT406 in OnEditorCreated')
#		# check if the user is editing a boolean cell
#		if self.ColCellEditors[self.ATListColInternalNames[Event.Col]] is wx.grid.GridCellBoolEditor:
#			# turn off the flag requiring character input
#			self.ThisCheckBox = Event.Control
#			self.ThisCheckBox.WindowStyle |= wx.WANTS_CHARS
#			self.ThisCheckBox.Bind(wx.EVT_KEY_DOWN, self.OnCheckBoxKeyDown)
#			self.ThisCheckBox.Bind(wx.EVT_CHECKBOX, self.OnCheckBoxToggle)
#		Event.Skip()

	def ChangeAssociatedText(self, AssociatedTextObj, ATRow, AttribChanged, NewAttribContent):
		# handle request to change a text attrib of associated text AssociatedTextObj (AssocTextItemInDisplay instance)
		# ATRow (int): row number of affected AT in grid, or None if not visible; stored to assist undo to show the
		# correct row. None will be sent in XML as 'None'
		# AttribChanged: (str) one of 'Content', 'Responsibility', 'Deadline', 'Status'
		# NewAttribContent: (str) new value of the attrib
		print('AT447 in ChangeAssociatedText with AT ID: ', AssociatedTextObj.ID)
		assert isinstance(AssociatedTextObj, AssocTextItemInDisplay)
		assert isinstance(ATRow, int)
		assert 0 <= ATRow < len(self.AssocTexts) # however doesn't consider filtering
		assert AttribChanged in ['Content', 'Responsibility', 'Deadline', 'Status']
		assert isinstance(NewAttribContent, str)
		# We use the ArgsToSend dict so that we can get arg names from info module
		ArgsToSend = {info.AssociatedTextIDTag: AssociatedTextObj.ID, info.AttribNameTag: AttribChanged,
			info.NewAttribValueTag: NewAttribContent, info.ATRowTag: 'None' if ATRow is None else str(ATRow),
			info.ZoomTag: str(self.Zoom), info.FilterTextTag: self.FilterText,
			info.FilterAppliedTag: utilities.Bool2Str(self.FilterApplied)}
		vizop_misc.SendRequest(Socket=self.C2DSocketREQ, Command='RQ_AT_ChangeAssociatedText',
			Proj=self.Proj.ID, Viewport=self.ID, **ArgsToSend)

	@classmethod
	def GetFullRedrawData(cls, Viewport=None, ViewportClass=None, **Args):
		# a datacore method. Provide data for redraw of this Viewport.
		# Args needs 'Proj' as a minimum
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
			# make subelements for AT ID, content, responsibility, deadline and status
			IDEl = ElementTree.SubElement(ATEl, info.AssociatedTextIDTag)
			IDEl.text = ThisAssocTextItem.ID
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
		# TODO add info.DisplayAttribTag with zoom and pan data
		print('AT270 ending GetFullRedrawData with RootElement: ', ElementTree.tostring(RootElement))
		return RootElement

	def AllClickableObjects(self, **Args):
		# no graphical objects requiring special mouse click handlers
		return []

	def RenderInDC(self, DC, **Args):
		# currently no graphics to render in a DC. For future, may provide a zoom tool
		pass

	def StoreAttribsInProject(self):
		# send request to datacore to store AT Viewport settings in project's Viewport shadow, for persistence
		AttribsToSend = {info.ProjIDTag: self.Proj.ID, info.ViewportTag: self.ID,
			info.AssociatedTextKindTag: self.AssocTextKind,
			info.FilterTextTag: self.FilterText,
			info.ItemsSelectedTag: ','.join([AT.ID for AT in self.AssocTexts if AT.Selected])}
		vizop_misc.SendRequest(Socket=self.C2DSocketREQ,
			Command='RQ_PR_UpdateAssocTextFullViewAttribs', **AttribsToSend)

	def ExitViewportAndRevert(self):
		# exit from Viewport; destroy the Viewport; and request the hosting display device to revert
		# to the previous Viewport
		# first, remove all widgets from the sizer and active text widget list
		self.Deactivate(Widgets=self.WidgetsToActivate)
		self.HeaderSizer.Clear()
		# destroy the widgets
		for ThisWidget in self.WidgetsToActivate:
			ThisWidget.Widget.Destroy()
		# destroy this Viewport and switch to the previous Viewport (for now, just go to the first PHA model in the project)
		# TODO build mechanism to identify the last touched PHA model
		self.DisplDevice.TopLevelFrame.SwitchToPHAObj(Proj=self.Proj, TargetPHAObjID=self.Proj.PHAObjShadows[0].ID,
			TargetViewport=None, ViewportToDestroy=self)

	def Deactivate(self, Widgets=[], **Args): # deactivate widgets for this Viewport
		self.DisplDevice.TopLevelFrame.DeactivateWidgetsInPanel(Widgets=Widgets, **Args)
		# remove widgets from text widgets list, so that they're no longer checked in OnIdle
		self.DisplDevice.TextWidgActive = []

	@classmethod
	def HandleIncomingRequest(cls, MessageReceived=None, MessageAsXMLTree=None, **Args):
		# handle request received by this Viewport in datacore
		# Incoming message can be supplied as either an XML string or XML tree root element
		# MessageReceived (str or None): XML message containing request info
		# MessageAsXMLTree (XML element or None): root of XML tree
		# return Reply (Root object of XML tree)
		print('AT565 in HandleIncoming Request')
		assert isinstance(MessageReceived, bytes) or (MessageReceived is None)
		assert isinstance(Args, dict)
		# First, convert MessageReceived to an XML tree for parsing
		if MessageReceived is None:
			assert isinstance(MessageAsXMLTree, ElementTree.Element)
			XMLRoot = MessageAsXMLTree
		else: XMLRoot = ElementTree.fromstring(MessageReceived)
		Proj = Args['Proj'] # get ProjectItem object to which the current FT belongs
		# get the command - it's the tag of the root element
		Command = XMLRoot.tag
		# extract display-related parms to store in undo records
		Zoom = XMLRoot.findtext(info.ZoomTag)
		# prepare default reply if command unknown
		Reply = vizop_misc.MakeXMLMessage(RootName='Fail', RootText='CommandNotRecognised')
		if Command == 'RQ_PR_UpdateAssocTextFullViewAttribs': # store parms for associated text display
			Reply = cls.UpdateAssocTextFullViewAttribs(Proj=Proj, XMLRoot=XMLRoot)
		elif Command == 'RQ_AT_ChangeAssociatedText':
			Reply = cls.HandleChangeAssociatedTextRequest(Proj, XMLRoot, ViewportID=XMLRoot.findtext(info.ViewportTag),
				Zoom=Zoom)
		if Reply.tag == 'Fail': print('AT367 command not recognised: ', Command)
		return Reply

	@classmethod
	def HandleChangeAssociatedTextRequest(cls, Proj, XMLRoot, ViewportID, Zoom):
		# handle request from Viewport with ID=ViewportID to change text content of existing AssociatedText
		assert isinstance(XMLRoot, ElementTree.Element)
		assert isinstance(ViewportID, str)
		assert isinstance(Zoom, str)
		print('AT587 in HandleChangeAssociatedTextRequest: changing attrib, ID: ', XMLRoot.findtext(info.AttribNameTag), XMLRoot.findtext(info.AssociatedTextIDTag))
		# update the AssociatedText in the required AssociatedText list
		cls.DoChangeAssociatedText(Proj, ATID=XMLRoot.findtext(info.AssociatedTextIDTag),
			ChangedAttribName=XMLRoot.findtext(info.AttribNameTag), FilterText=XMLRoot.findtext(info.FilterTextTag),
			FilterApplied=utilities.Bool2Str(XMLRoot.findtext(info.FilterAppliedTag)),
			NewAttribValue=XMLRoot.findtext(info.NewAttribValueTag),
			ATRowInGrid=XMLRoot.findtext(info.ATRowTag),
			ViewportID=ViewportID, Redoing=False, Zoom=Zoom)
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	@classmethod
	def DoChangeAssociatedText(cls, Proj, ATID='', ChangedAttribName='', NewAttribValue='', ATRowInGrid='',
			ViewportID='', AssociatedTextKind='ActionItems', FilterText='', FilterApplied=False,
			Redoing=False, Zoom=1.0):
		# datacore method
		# Change value of ChangedAttribName (str) of AssociatedText with ID ATID (str) to NewAttribValue (str)
		# ATRowInGrid (int as str): row of grid at which this AT is displayed, or '' if not currently visible in grid
		# ViewportID: ID of Viewport from where the change AssociatedText request was made
		# FilterText (str) and FilterApplied (bool) indicate the current status of filtering, for storage in undo record
		# first find the associated text; could be action item or parking lot item
		ATToChange = utilities.ObjectWithID(Objects=Proj.ActionItems + Proj.ParkingLotItems, TargetID=ATID)
		OldAttribValue = getattr(ATToChange, ChangedAttribName)
		# change the attrib value
		setattr(ATToChange, ChangedAttribName, NewAttribValue)
		undo.AddToUndoList(Proj=Proj, Redoing=Redoing,
			UndoObj=undo.UndoItem(UndoHandler=cls.ChangeAssociatedText_Undo,
			RedoHandler=cls.ChangeAssociatedText_Redo, FilterText=FilterText, FilterApplied=FilterApplied,
			ATID=ATID,
			ChangedAttribName=ChangedAttribName,
			OldAttribValue=OldAttribValue,
			ATRowInGrid=ATRowInGrid,
			HumanText=_('change %s' % core_classes.AssociatedTextEnglishNamesSingular[AssociatedTextKind]),
			ViewportID=ViewportID, Zoom=Zoom))

	@classmethod
	def ChangeAssociatedText_Undo(cls, Proj, UndoRecord, **Args):
		# revert associated text attrib to previous value. Datacore method
		# find out which datacore socket to send messages on
		SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
		ATToChange = utilities.ObjectWithID(Objects=Proj.ActionItems + Proj.ParkingLotItems, TargetID=UndoRecord.ATID)
		setattr(ATToChange, UndoRecord.ChangedAttribName, UndoRecord.OldAttribValue)
		# request Control Frame to switch to the Viewport that was visible when the original edit was made
		cls.RedrawAfterUndoOrRedo(Proj, UndoRecord, SocketFromDatacore)
		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.AssociatedTextTag,
			Elements={info.IDTag: UndoRecord.ATID}))
#		# if this Viewport is currently visible, refresh the display
#		if any(v.IsOnDisplay for v in Proj.AllViewportShadows if v.ID == UndoRecord.ViewportID):
#			# restore previous filter settings, to ensure change is visible
#			self.ApplyFilters(FilterText=UndoRecord.FilterText, FilterApplied=UndoRecord.FilterApplied)
#			# repopulate full display
#			self.Prefill(self, SystemFontNames=self.SystemFontNames, CurrentAT=None)
#		else: # switch to AT list Viewport and redisplay
#			print('AT641 TODO: switch to AT list Viewport on undo')

	@classmethod
	def ChangeAssociatedText_Redo(cls, Proj, RedoRecord, **Args): pass # TODO

	@classmethod
	def RedrawAfterUndoOrRedo(cls, Proj, UndoRecord, SocketFromDatacore, SkipRefresh=False):
		# check if we should redraw. If this is an undo, and UndoRecord is avalanche-chained, don't refresh.
		# If this is a redo, don't refresh if UndoRecord.SkipRefresh is True.
		# If we should redraw,
		# instruct Control Frame to switch the requesting control frame to the Viewport that was visible when the original
		# text change was made, with the original zoom  restored, and scrolled so that the first changed row is on screen
		# and the changed attrib highlighted (so that the undo is visible to the user) (TODO)
		# SocketFromDatacore (socket object): socket to send redraw message from datacore to Control Frame
		# first, check whether to redraw
		if not SkipRefresh:
			# prepare data about zoom, highlight etc.
			DisplayAttribTag = cls.FetchDisplayAttribsFromUndoRecord(UndoRecord)
			RedrawDataXML = cls.GetFullRedrawData(Proj=Proj)
			MsgToControlFrame = ElementTree.Element(info.NO_RedrawAfterUndo)
			# add a ViewportID tag to the message, so that Control Frame knows which Viewport to redraw
			ViewportTag = ElementTree.Element(info.ViewportTag)
			ViewportTag.text = UndoRecord.ViewportID
			ViewportTag.append(DisplayAttribTag)
			MsgToControlFrame.append(ViewportTag)
			MsgToControlFrame.append(RedrawDataXML)
			vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket, Command=info.NO_RedrawAfterUndo, XMLRoot=MsgToControlFrame)

	@classmethod
	def FetchDisplayAttribsFromUndoRecord(cls, UndoRecord):
		# extract data about zoom, pan, highlight etc. from UndoRecord, build it into an XML tag DisplayAttribTag
		# and return the tag
		DisplaySpecificData = ElementTree.Element(info.DisplayAttribTag)
		for (UndoRecordAttribName, TagName) in [ ('ChangedAttribName', info.AttribNameTag),
				('Zoom', info.ZoomTag), ('PanX', info.PanXTag), ('PanY', info.PanYTag)]:
			if hasattr(UndoRecord, UndoRecordAttribName):
				ThisAttribTag = ElementTree.SubElement(DisplaySpecificData, TagName)
				ThisAttribTag.text = str(getattr(UndoRecord, UndoRecordAttribName))
		return DisplaySpecificData

	@classmethod
	def UpdateAssocTextFullViewAttribs(cls, Proj, XMLRoot):
		# a datacore function. Store attribs about this Viewport in datacore for persistence.
		# The attribs are stored in the Viewport shadow. They don't need to be saved in the project file, but need to
		# be used to restore the same settings when this Viewport is destroyed and re-created.
		print('AT375 storing attribs in datacore')
		# First, find the Viewport shadow
		print('AT630 Viewport shadows: ', [v.ID for v in Proj.AllViewportShadows])
		print('AT630 Archieved Viewport shadows: ', [v.ID for v in Proj.ArchivedViewportShadows])
		ViewportShadow = utilities.ObjectWithID(Proj.AllViewportShadows + Proj.ArchivedViewportShadows,
			TargetID=XMLRoot.findtext(info.ViewportTag))
		ViewportShadow.AssocTextKind = XMLRoot.findtext(info.AssociatedTextKindTag)
		ViewportShadow.FilterText = XMLRoot.findtext(info.FilterTextTag)
		ViewportShadow.ItemsSelectedCommaList = XMLRoot.findtext(info.ItemsSelectedTag) # string of AT ID's separated by commas
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def ReleaseDisplayDevice(self, DisplDevice, **Args):
		# wrap-up actions needed when display device is no longer showing associated texts list
		self.DisplDevice = None

# for display of assoc text list, consider class SIFListGridTable