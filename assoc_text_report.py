# -*- coding: utf-8 -*-
# Module assoc_text_report: part of Vizop, (c) 2020 xSeriCon
# Codes the dialogue and export of a report of action items and parking lot items
import os, os.path, wx, platform # wx provides basic GUI functions

import display_utilities, project_display, info, core_classes, vizop_misc, excel_export, projects, utilities
from display_utilities import UIWidgetItem
import xml.etree.ElementTree as ElementTree # XML handling

class AssocTextReportViewport(display_utilities.ViewportBaseClass):
	# defines a viewport that produces an export file containing a list of associated texts (action items or parking
	# lot items), and encodes a
	# dialogue to get parameters from the user to control the export (e.g. which items to include, fonts)
	IsBaseClass = False
	InternalName = 'ATReport' # unique per class, used in messaging
	HumanName = _('Action item/Parking lot report')
	PreferredKbdShortcut = 'R'
	NewPHAObjRequired = None # which datacore PHA object class this Viewport spawns on creation.
		# Should be None if the model shouldn't create a PHA object
	# VizopTalks message when this Viewport is created. NB don't set Priority here, as it is overridden in DoNewViewportCommand()
	NewViewportVizopTalksArgs = {'Title': 'Action item/Parking lot report',
		'MainText': 'Enter the settings you require, then click Go'}
	NewViewportVizopTalksTips = []
	InitialEditPanelMode = 'Widgets'

	def __init__(self, Proj, PHAObjID, DisplDevice, ParentWindow, Fonts, SystemFontNames, **Args):
		# __init__ for class AssocTextReportViewport
		assert Args[info.AssociatedTextKindTag] in [info.ActionItemLabel, info.ParkingLotItemLabel]
		display_utilities.ViewportBaseClass.__init__(self, Proj=Proj, PHAObjID=PHAObjID, DisplDevice=DisplDevice,
			ParentWindow=ParentWindow, **Args)
		self.SystemFontNames = SystemFontNames
		self.AssocTextKind = Args[info.AssociatedTextKindTag]
		# make aspect object for dialogue
		assert Args[info.ItemsToIncludeTag] in [info.AllItemsLabel, info.FilteredItemsLabel, info.NotSpecifiedLabel]
		self.DialogueAspect = self.MakeATReportDialogueAspect(MyEditPanel=DisplDevice, Fonts=Fonts,
															  SystemFontNames=SystemFontNames, DateChoices=Args['DateChoices'], ATKind=self.AssocTextKind,
															  ItemsToInclude=Args[info.ItemsToIncludeTag])
		# get connection to originating Viewport
		assert isinstance(Args['OriginatingViewport'], display_utilities.ViewportBaseClass)
		self.OriginatingViewport = Args['OriginatingViewport']
		self.AssocTexts = [] # list of AssocTextItemInDisplay instances TODO populate me
#		# get requested scope of export
#		self.ScopeRequestedOnInit = Args[info.ItemsToIncludeTag]
#		print('AR36 making ATR viewport with scope: ', Args[info.ItemsToIncludeTag])


	def PrepareFullDisplay(self, XMLData):
		# display dialogue in our display device to get export parameters from user
		# first, unpack data from datacore
		self.UnpackDataFromDatacore(XMLData)
		# build the dialogue: prefill widgets in new aspect and activate it
		self.DialogueAspect.Prefill(self.Proj, SystemFontNames=self.SystemFontNames)
		self.DialogueAspect.SetWidgetVisibility()
		self.DialogueAspect.Activate(WidgetsToActivate=self.DialogueAspect.WidgetsToActivate[:],
			TextWidgets=self.DialogueAspect.TextWidgets)
		# display aspect's sizer (containing all the visible widgets) in the edit panel
		self.DisplDevice.SetSizer(self.DialogueAspect.MySizer)

	def RenderInDC(self, TargetDC, FullRefresh=True, **Args): pass
		# nothing to do here - this Viewport doesn't draw in a DC - we need this stub to override the superclass's method

#	class ATReportDialogueAspect(project_display.EditPanelAspectItem): # class definition is lower down

	def MakeATReportDialogueAspect(self, MyEditPanel, Fonts, SystemFontNames, DateChoices, ATKind, ItemsToInclude):
		# make edit panel aspect for defining associated text report
		# fonts (dict): internal font objects such as SmallHeadingFont
		# SystemFontNames (list of str): names of "real" fonts available on the platform
		# DateChoices (list of ChoiceItem): options for date to show in report (not currently used)
		# ItemsToInclude (str): one of 'AllItems' or 'FilteredItems' - which ATs were requested on entry to the Viewport
		# return the aspect
		assert ATKind in [info.ActionItemLabel, info.ParkingLotItemLabel]
		assert ItemsToInclude in [info.AllItemsLabel, info.FilteredItemsLabel, info.NotSpecifiedLabel]
		# First, make basic attribs needed for the aspect
		MyEditPanel.ATReportDialogueAspect = AssocTextReportViewport.ATReportDialogueAspect(InternalName='ATReport',
			ParentFrame=MyEditPanel, TopLevelFrame=MyEditPanel.TopLevelFrame)
		ThisAspect = MyEditPanel.ATReportDialogueAspect
		ThisAspect.Viewport = self
		ThisAspect.TextWidgets = []
		ThisAspect.ATKind = ATKind
		ThisAspect.ItemsRequestedOnInit = ItemsToInclude
		# make box sizers to contain groups of widgets
		FileBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('About the file to produce'))
		FileBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		FileBoxSizer.Add(FileBoxSubSizer)
		ScopeBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('What to include in the report'))
		ScopeBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		ScopeBoxSizer.Add(ScopeBoxSubSizer)
		PageLayoutBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('Page layout'))
		PageLayoutBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		PageLayoutBoxSizer.Add(PageLayoutBoxSubSizer)
		StyleBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('Report style'))
		StyleBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		StyleBoxSizer.Add(StyleBoxSubSizer)
		ActionBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=' ')
		ActionBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		ActionBoxSizer.Add(ActionBoxSubSizer)
		# make widgets for File box
		ThisAspect.HeaderLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
			{info.ActionItemLabel: _('Export action items report'),
			info.ParkingLotItemLabel: _('Export parking lot report')}[ATKind]),
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapY=10,
			ColLoc=0, ColSpan=10, Font=Fonts['BigHeadingFont'], NewRow=True)
		ThisAspect.FileBox = UIWidgetItem(FileBoxSizer, HideMethod=lambda : FileBoxSizer.ShowItems(False),
			ShowMethod=lambda : FileBoxSizer.ShowItems(True), ColLoc=0, ColSpan=5, NewRow=True,
			SetFontMethod=lambda f: FileBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.FilenameLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Filename:'),
			style=wx.ALIGN_RIGHT | wx.ALIGN_CENTER_VERTICAL),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.FilenameText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER),
			MinSizeY=25, Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnFilenameTextWidget, GapX=5,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
			MinSizeX=300, ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
		ThisAspect.SelectButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Select')),
			Handler=ThisAspect.OnSelectButton, Events=[wx.EVT_BUTTON], ColLoc=3, ColSpan=1,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
		ThisAspect.OverwriteCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Overwrite')),
			Handler=ThisAspect.OnOverwriteCheck, Events=[wx.EVT_CHECKBOX], ColLoc=2, ColSpan=1, NewRow=True)
		ThisAspect.FilenameStatusMessage = UIWidgetItem(wx.StaticText(MyEditPanel, -1, ''),
			ColLoc=2, ColSpan=3, Font=Fonts['BoldFont'], NewRow=True)
		# add widgets to FileBoxSubSizer, and populate list of text widgets
		ThisAspect.TextWidgets.extend(display_utilities.PopulateSizer(Sizer=FileBoxSubSizer, Widgets=[ThisAspect.FilenameLabel,
			ThisAspect.FilenameText, ThisAspect.SelectButton,
			ThisAspect.OverwriteCheck, ThisAspect.FilenameStatusMessage]))

		# widgets in "scope" box
		ThisAspect.ScopeBox = UIWidgetItem(ScopeBoxSizer, HideMethod=lambda : ScopeBoxSizer.ShowItems(False),
			ShowMethod=lambda : ScopeBoxSizer.ShowItems(True), ColLoc=0, ColSpan=5, NewRow=True,
			SetFontMethod=lambda f: ScopeBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.ExportWhatLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Export what:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.ShowHeaderCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Header block')),
			Handler=ThisAspect.OnShowHeaderCheck, Events=[wx.EVT_CHECKBOX], ColLoc=1, ColSpan=1, XMLLabel=info.HeaderLabel)
		ThisAspect.AllItemsRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1,
			{info.ActionItemLabel: _('All action items'),
			info.ParkingLotItemLabel: _('All parking lot items')}[ATKind],
			style=wx.RB_GROUP), XMLLabel=info.AllItemsLabel,
			Handler=ThisAspect.OnAllItemsRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
		ThisAspect.FilteredItemsRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Only filtered items')),
			Handler=ThisAspect.OnFilteredItemsRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5,
			XMLLabel=info.FilteredItemsLabel)
		ThisAspect.ShowEditNumberCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Show edit number')),
			Handler=ThisAspect.OnShowEditNumberCheck, Events=[wx.EVT_CHECKBOX], ColLoc=1, ColSpan=1, NewRow=True,
			XMLLabel=info.EditNumberLabel)
		# add widgets to ScopeBoxSubSizer, and populate list of text widgets
		ThisAspect.TextWidgets.extend(display_utilities.PopulateSizer(Sizer=ScopeBoxSubSizer,
			Widgets=[ThisAspect.ExportWhatLabel,
			ThisAspect.ShowHeaderCheck, ThisAspect.AllItemsRadio,
			ThisAspect.FilteredItemsRadio]))

		# widgets in "page layout" box
		ThisAspect.PageLayoutBox = UIWidgetItem(PageLayoutBoxSizer, HideMethod=lambda : PageLayoutBoxSizer.ShowItems(False),
			ShowMethod=lambda : PageLayoutBoxSizer.ShowItems(True), ColLoc=5, ColSpan=5, RowSpan=2,
			SetFontMethod=lambda f: PageLayoutBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.PageSizeLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Page size:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.PageSizeChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(200, 25),
			choices=[t.FullNameForDisplay for t in core_classes.PaperSizes]),
			Handler=ThisAspect.OnPageSizeChoice, Events=[wx.EVT_CHOICE], ColLoc=1, ColSpan=3)
		ThisAspect.PortraitRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Portrait'), style=wx.RB_GROUP),
			Handler=ThisAspect.OnPortraitRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
		ThisAspect.LandscapeRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Landscape')),
			Handler=ThisAspect.OnLandscapeRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
		# add widgets to PageLayoutBoxSubSizer, and populate list of text widgets
		ThisAspect.TextWidgets.extend(display_utilities.PopulateSizer(Sizer=PageLayoutBoxSubSizer,
			Widgets=[ThisAspect.PageSizeLabel,
			ThisAspect.PageSizeChoice, ThisAspect.PortraitRadio,
			ThisAspect.LandscapeRadio]))

		# make Style box and widgets
		ThisAspect.StyleBox = UIWidgetItem(StyleBoxSizer, HideMethod=lambda : StyleBoxSizer.ShowItems(False),
			ShowMethod=lambda : StyleBoxSizer.ShowItems(True), ColLoc=0, ColSpan=9, NewRow=True,
			SetFontMethod=lambda f: StyleBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.FontLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Font:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.FontChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(200, 25),
			choices=SystemFontNames),
			Handler=ThisAspect.OnFontChoice, Events=[wx.EVT_CHOICE], ColLoc=1, ColSpan=2)
		ThisAspect.ShowResponsibilityCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Show responsibility field')),
			Handler=lambda Event: ThisAspect.OnShowFieldCheck(Event=Event, FieldName=info.ResponsibilityLabel),
			Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1, GapX=20)
		ThisAspect.ShowDeadlineCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Show deadline field')),
			Handler=lambda Event: ThisAspect.OnShowFieldCheck(Event=Event, FieldName=info.DeadlineLabel),
			Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1, GapX=20, NewRow=True)
		ThisAspect.ShowStatusCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Show status field')),
			Handler=lambda Event: ThisAspect.OnShowFieldCheck(Event=Event, FieldName=info.StatusLabel),
			Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1, GapX=20, NewRow=True)
		ThisAspect.ShowPlacesUsedCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Show \'Places used\' field')),
			Handler=lambda Event: ThisAspect.OnShowFieldCheck(Event=Event, FieldName=info.WhereUsedLabel),
			Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1, GapX=20, NewRow=True)
		# add widgets to StyleBoxSubSizer, and populate list of text widgets
		ThisAspect.TextWidgets.extend(display_utilities.PopulateSizer(Sizer=StyleBoxSubSizer,
			Widgets=[ThisAspect.FontLabel, ThisAspect.FontChoice, ThisAspect.ShowResponsibilityCheck,
				ThisAspect.ShowDeadlineCheck, ThisAspect.ShowStatusCheck, ThisAspect.ShowPlacesUsedCheck]))

		# make Action box and widgets
		ThisAspect.ActionBox = UIWidgetItem(ActionBoxSizer, HideMethod=lambda : ActionBoxSizer.ShowItems(False),
			ShowMethod=lambda : ActionBoxSizer.ShowItems(True), ColLoc=9, ColSpan=1,
			SetFontMethod=lambda f: ActionBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.CancelButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Cancel')), GapX=42, NewRow=True,
			Handler=ThisAspect.OnCancelButton, Events=[wx.EVT_BUTTON], ColLoc=1, ColSpan=1, GapY=15,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
		ThisAspect.GoButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Go')), NewRow=True,
			Handler=ThisAspect.OnGoButton, Events=[wx.EVT_BUTTON], ColLoc=1, ColSpan=1,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
		display_utilities.PopulateSizer(Sizer=ActionBoxSubSizer, Widgets=[ThisAspect.CancelButton, ThisAspect.GoButton])

		# make required lists
		ThisAspect.WidgetList = [ThisAspect.HeaderLabel,
			ThisAspect.FileBox, ThisAspect.PageLayoutBox, ThisAspect.ScopeBox, ThisAspect.StyleBox,
			ThisAspect.ActionBox]
		ThisAspect.WidgetsToActivate = [ThisAspect.HeaderLabel,
			ThisAspect.FilenameLabel, ThisAspect.FilenameText, ThisAspect.SelectButton,
			ThisAspect.OverwriteCheck, ThisAspect.FilenameStatusMessage,
			ThisAspect.ExportWhatLabel,
			ThisAspect.ShowHeaderCheck, ThisAspect.AllItemsRadio,
			ThisAspect.FilteredItemsRadio,
			ThisAspect.PageSizeLabel,
			ThisAspect.PageSizeChoice, ThisAspect.PortraitRadio,
			ThisAspect.LandscapeRadio,
			ThisAspect.FontLabel, ThisAspect.FontChoice, ThisAspect.ShowResponsibilityCheck,
			ThisAspect.ShowDeadlineCheck, ThisAspect.ShowStatusCheck,
			ThisAspect.ShowPlacesUsedCheck,
			ThisAspect.CancelButton, ThisAspect.GoButton]
		return ThisAspect

	class ATReportDialogueAspect(project_display.EditPanelAspectItem):

		def __init__(self, InternalName, ParentFrame, TopLevelFrame):
			project_display.EditPanelAspectItem.__init__(self, WidgetList=[], InternalName=InternalName,
				ParentFrame=ParentFrame, TopLevelFrame=TopLevelFrame, PrefillMethod=self.Prefill,
				SetWidgetVisibilityMethod=self.SetWidgetVisibility)
			print('AR61 initializing dialogue aspect')
			self.Overwrite = False # whether to overwrite any existing file when exporting

		def OnFilenameTextWidget(self, Event=None, WidgetObj=None):
			# get filename provided by user
			UserFilename = self.FilenameText.Widget.GetValue().strip()
			# update filename status text, Go button status etc
			FilenameStatus = self.UpdateWidgetStatus()
			# write name back into widget, if filename is usable
			if FilenameStatus not in ['CannotWrite', 'NoAccess', 'Other']:
				self.FilenameText.Widget.ChangeValue(UserFilename)

		def UpdateWidgetStatus(self):
			# update enabled/disabled status of all widgets
			ThisViewport = self.ParentFrame.TopLevelFrame.CurrentViewport
			# First, check whether requested filename is usable
			UserFilename = self.FilenameText.Widget.GetValue().strip()
			FilenameStatus = self.UpdateFilenameStatusMessage(UserFilePath=UserFilename)
			# set status of Go button %%% working here
			SomeATsAreSelected = any(ThisViewport.OriginatingViewport.GetSelectedATs()) if \
				hasattr(ThisViewport.OriginatingViewport, 'GetSelectedATs') else False
			FilenameUsable = FilenameStatus in ['ReadyToMakeNewFile', 'ReadyToOverwrite']
			ContentIsNonzero = self.ShowHeaderCheck.Widget.IsChecked() or \
				(SomeATsAreSelected or self.AllItemsRadio.Widget.GetValue())
			self.GoButton.Widget.Enable(FilenameUsable and ContentIsNonzero)
			return FilenameStatus, SomeATsAreSelected

		def UpdateFilenameStatusMessage(self, UserFilePath=''):
			# update filename status message widget text based UserFilePath (str; what's currently in the Filename
			# text box)
			# return FilenameStatus (str)
			assert isinstance(UserFilePath, str)
			# check status of UserFilePath
			PathStati = [] # using a list in case there's more than one file path - for compatibility with ft_full_report
			for ThisPath in [UserFilePath]:
				# is the path a writeable path with no existing file?
				if vizop_misc.IsWriteableAsNewFile(ThisPath): ThisPathStatus = 'CanWrite'
				# is the path a writeable path, with an existing file?
				elif os.path.isfile(ThisPath) and os.access(ThisPath, os.W_OK): ThisPathStatus = 'NeedToOverwrite'
				# is the path unusable?
				else: ThisPathStatus = 'CannotWrite'
				PathStati.append(ThisPathStatus)
			# 1. Filename text box empty, or whitespace only, or contains a directory path
			if (not UserFilePath) or os.path.isdir(UserFilePath):
				Message = _('Please provide a filename for the export')
				FilenameStatus = 'NotFilename'
			# 2. Paths to use are all writeable, nonexistent filenames
			elif PathStati.count('CanWrite') == len(PathStati):
				Message = _('Ready to export to new file. Click Go')
				FilenameStatus = 'ReadyToMakeNewFile'
			# 3. Paths point to at least 1 existent file that can be overwritten, and Overwrite check box is checked
			elif (PathStati.count('NeedToOverwrite') > 0) and ('CannotWrite' not in PathStati)  and \
					self.OverwriteCheck.Widget.GetValue():
				Message = _('Ready to export. Existing file(s) will be overwritten when you click Go')
				FilenameStatus = 'ReadyToOverwrite'
			# 4. Path points to an existent file that can be overwritten, and Overwrite check box is unchecked
			elif (PathStati.count('NeedToOverwrite') > 0) and ('CannotWrite' not in PathStati) and \
					not self.OverwriteCheck.Widget.GetValue():
				Message = _('File exists. Click "Overwrite", then "Go"')
				FilenameStatus = 'FileExists'
			# 5. Path points to a writeable folder, but no extension is provided and it is needed (i.e. Windows)
			elif vizop_misc.IsWritableLocation(UserFilePath) and os.path.splitext(UserFilePath)[1] in ['', '.'] \
					and platform.system() == 'Windows':
				Message = _('Please provide a valid file extension, e.g. .pdf')
				FilenameStatus = 'NeedExtension'
			# 6. Path points to a nonexistent folder, or a folder with no write access
			elif not vizop_misc.IsWritableLocation(UserFilePath):
				Message = _("%s can't write to that location") % info.PROG_SHORT_NAME
				FilenameStatus = 'NoAccess'
			# 99. Some other case we haven't thought of
			else:
				Message = _('You should buy a lottery ticket today')
				FilenameStatus = 'Other'
			self.FilenameStatusMessage.Widget.SetLabel(Message)
			return FilenameStatus

		def OnSelectButton(self, Event):
			# fetch and check any filename provided in the filename textctrl
			UserFilename = self.FilenameText.Widget.GetValue().strip()
			if UserFilename: # if user has entered a filename, provide it as default
				DefaultBasename = os.path.basename(UserFilename)
			else:
				# get last used export filename from project
				DefaultBasename = self.Proj.ATExportFilename
			# get the wildcard to use in the filename dialogue box
			DefaultExtension = info.ExcelExtension
			Wildcard = '*' + os.extsep + DefaultExtension
			# get default directory = directory in filename textctrl, last export save directory or project save directory, if any
			if os.path.exists(os.path.dirname(UserFilename)): DefaultDirectory = os.path.dirname(UserFilename)
			elif os.path.exists(os.path.dirname(self.Proj.ATExportFilename)):
				DefaultDirectory = os.path.dirname(self.Proj.ATExportFilename)
			elif os.path.exists(os.path.dirname(self.Proj.OutputFilename)):
				DefaultDirectory = os.path.dirname(self.Proj.OutputFilename)
			else: DefaultDirectory = info.DefaultUserDirectory
			(GetFilenameSuccess, SaveFilename) = vizop_misc.GetFilenameForSave(self.TopLevelFrame,
				DialogueTitle={info.ActionItemLabel: _('Select filename  for action item report'),
				info.ParkingLotItemLabel: _('Select filename for parking lot report')}[self.ATKind],
				DefaultDir=DefaultDirectory,
				DefaultFile=DefaultBasename, Wildcard=Wildcard, DefaultExtension=DefaultExtension)
			if GetFilenameSuccess:
				# write pathname into filename textctrl
				self.FilenameText.Widget.ChangeValue(SaveFilename)
				# update filename status text, Go button status etc
				FilenameStatus = self.UpdateWidgetStatus()

		def OnOverwriteCheck(self, Event): # handle click on Overwrite checkbox: store overwrite option
			self.Overwrite = self.OverwriteCheck.Widget.GetValue()
			# update filename status text, Go button status etc
			FilenameStatus = self.UpdateWidgetStatus()

		def OnShowHeaderCheck(self, Event): # handle click on "show header" checkbox
			pass

		def OnAllItemsRadio(self, Event): # handle click on "show all items" radio button
			pass

		def OnFilteredItemsRadio(self, Event): # handle click on "show filtered items" radio button
			pass

		def OnShowEditNumberCheck(self, Event): # handle click on "show edit number" checkbox
			pass

		def OnPageSizeChoice(self, Event): # handle change of page size choice
			SelectedSize = core_classes.PaperSizes[self.PageSizeChoice.Widget.GetSelection()]
			# store new page size in user config
			vizop_misc.StoreValueInUserConfig(ConfigName='ExportPaperSize', Value=SelectedSize.XMLName)

		def OnPortraitRadio(self, Event):  # handle click on "portrait" radio button
			pass

		def OnLandscapeRadio(self, Event):  # handle click on "landscape" radio button
			pass

		def OnFontChoice(self, Event): # handle change of font selection
			pass

		def OnShowFieldCheck(self, Event, FieldName): # handle click in checkbox for "show <field>"
			assert FieldName in [info.ResponsibilityLabel, info.DeadlineLabel, info.StatusLabel, info.WhereUsedLabel]
			pass # no further action needed at present

		def OnCancelButton(self, Event):  # handle click on "cancel" button
			self.StoreAttribsInProject() # %%% working here, need to code this
			self.ExitViewportAndRevert()

		def OnGoButton(self, Event):  # handle click on "go" button
			ShowWhat = self.MakeAttribStrings()
			ExportInput = {'FilePath': self.FilenameText.Widget.GetValue().strip(),
				'FileType': info.ExcelExtension,
				'ShowWhat': ShowWhat,
				'PageSizeLongAxis': core_classes.PaperSizes[self.PageSizeChoice.Widget.GetSelection()].SizeLongAxis,
				'PageSizeShortAxis': core_classes.PaperSizes[self.PageSizeChoice.Widget.GetSelection()].SizeShortAxis,
				'Orientation': 'Portrait' if self.PortraitRadio.Widget.GetValue() else 'Landscape',
				'FontName': self.ParentFrame.TopLevelFrame.SystemFontNames[self.FontChoice.Widget.GetSelection()] }
#				'DateKind': core_classes.DateChoices[self.DateChoice.Widget.GetSelection()] }
			self.Viewport.DoExportATsToFile(**ExportInput)
#			self.ParentFrame.TopLevelFrame.CurrentViewport.DoExportATsToFile(**ExportInput)
			self.StoreAttribsInProject()
			self.ExitViewportAndRevert()

		def StoreAttribsInProject(self):
			# send request to datacore to store parameters in project
			ThisViewport = self.ParentFrame.TopLevelFrame.CurrentViewport
			# gets string containing information about export required
			ShowWhat = self.MakeAttribStrings()
			vizop_misc.SendRequest(Socket=ThisViewport.C2DSocketREQ,
				Command='RQ_ZZ_UpdateATExportAttribs',
				Proj=self.Proj.ID,
				PHAObj='None' if ThisViewport.PHAObjID is None else ThisViewport.PHAObjID, Viewport=ThisViewport.ID,
				Filename=self.FilenameText.Widget.GetValue().strip(),
				FileType=info.ExcelExtension,
				ExportWhat=ShowWhat,
				PageSize=core_classes.PaperSizes[self.PageSizeChoice.Widget.GetSelection()].XMLName,
				PaperOrientation=info.PortraitLabel if self.PortraitRadio.Widget.GetValue() else info.LandscapeLabel,
				Font=self.ParentFrame.TopLevelFrame.SystemFontNames[self.FontChoice.Widget.GetSelection()])
				# next line retained for future use, as we may add a "show what date" choice, like ft_full_report
#				DateToShow=core_classes.DateChoices[self.DateChoice.Widget.GetSelection()].XMLName)

		def MakeAttribStrings(self):
			# return ShowWhat (1 x str) containing information about export required
			# make string containing labels of parts of table to be exported, e.g. 'Header,EditNumber,ATs'
			ShowWhat = ','.join([w.XMLLabel for w in [self.ShowHeaderCheck, self.ShowEditNumberCheck]
				if w.Widget.IsChecked()] + \
				[w.XMLLabel for w in [self.AllItemsRadio, self.FilteredItemsRadio] if w.Widget.GetValue()])
			return ShowWhat

		def ExitViewportAndRevert(self):
			# exit from AT report Viewport; destroy the Viewport; and request the hosting display device to revert
			# to the previous Viewport
			# first, remove all widgets from the sizer and active text widget list
			self.Deactivate(Widgets=self.WidgetsToActivate)
			self.MySizer.Clear()
			# destroy the widgets
			for ThisWidget in self.WidgetsToActivate:
				ThisWidget.Widget.Destroy()
			# destroy this Viewport and switch to the previous Viewport (for now, just go to the first PHA model in the project)
			# TODO build mechanism to identify the last touched PHA model (also needed in other Viewports' Exit())
			self.TopLevelFrame.SwitchToPHAObj(Proj=self.Proj, TargetPHAObjID=self.Proj.PHAObjShadows[0].ID,
				TargetViewport=None, ViewportToDestroy=self.TopLevelFrame.CurrentViewport)

		def Prefill(self, Proj, SystemFontNames):
			# prefill widget values in the dialogue
			self.Proj = Proj # used in widget handlers
			FilenameStatus, SomeATsAreSelected = self.UpdateWidgetStatus()
			# filename is fetched from last used filename in the project
			self.FilenameText.Widget.ChangeValue(Proj.ATExportFilename.strip())
			self.FilenameText.Widget.SelectAll()
			# set overwrite checkbox
			self.OverwriteCheck.Widget.SetValue(self.Overwrite)
			# set scope checkboxes and radio buttons
			self.ShowHeaderCheck.Widget.SetValue(info.HeaderLabel in Proj.ATExportShowWhat)
			if self.ItemsRequestedOnInit == info.AllItemsLabel or not SomeATsAreSelected:
				self.AllItemsRadio.Widget.SetValue(True)
			elif self.ItemsRequestedOnInit == info.FilteredItemsLabel:
				self.FilteredItemsRadio.Widget.SetValue(True)
			elif self.ItemsRequestedOnInit == info.NotSpecifiedLabel: # using this route when starting from menu
				self.FilteredItemsRadio.Widget.SetValue(SomeATsAreSelected and \
					(info.FilteredItemsLabel in Proj.ATExportShowWhat))
				self.AllItemsRadio.Widget.SetValue(not self.FilteredItemsRadio.Widget.GetValue())
			self.ShowEditNumberCheck.Widget.SetValue(info.EditNumberLabel in Proj.ATExportShowWhat)
			# set layout widget values
			# get user's preferred paper size from config file
			PaperSizeStr = vizop_misc.GetValueFromUserConfig('ExportPaperSize')
			if PaperSizeStr == '': PaperSizeStr = info.DefaultPaperSize
			PaperSizesStr = [p.HumanName for p in core_classes.PaperSizes]
			# use 0th paper size if preferred paper size isn't in list of available paper sizes
			TargetPaperSizeIndex = PaperSizesStr.index(PaperSizeStr) if PaperSizeStr in PaperSizesStr else 0
			self.PageSizeChoice.Widget.SetSelection(TargetPaperSizeIndex)
			# set paper orientation from value stored in project
			if Proj.ATExportPaperOrientation == info.PortraitLabel:
				self.PortraitRadio.Widget.SetValue(True)
			elif Proj.ATExportPaperOrientation == info.LandscapeLabel:
				self.LandscapeRadio.Widget.SetValue(True)
			# set font choice box; first choice is last font used in this project, then last font used by this user
			PreferredFontName = Proj.LastExportFontName
			if PreferredFontName in SystemFontNames:
				FontNameToUse = PreferredFontName
			else:
				LastUserFontName = vizop_misc.GetValueFromUserConfig('ExportFontName')
				if LastUserFontName in SystemFontNames:
					FontNameToUse = LastUserFontName
				# if last font name not found, select the first system font name, if any
				elif SystemFontNames:
					FontNameToUse = SystemFontNames[0]
				else:
					FontNameToUse = ''
			if FontNameToUse: self.FontChoice.Widget.SetSelection(SystemFontNames.index(FontNameToUse))
			# set depiction checkboxes
			# set date choice box (for later development)
#			DateChoicesInternalNames = [d.XMLName for d in core_classes.DateChoices]
#			PreferredDateToShow = Proj.LastExportPreferredDateToShow
#			if PreferredDateToShow in core_classes.DateChoices:
#				DateToShow = PreferredDateToShow
#			else:
#				LastUserDateToShow = vizop_misc.GetValueFromUserConfig('ExportDateToShow')
#				if LastUserDateToShow in DateChoicesInternalNames:
#					DateToShow = LastUserDateToShow
#				# if last date kind not found, select the date kind flagged as 'Default'
#				else:
#					DateToShow = core_classes.DateChoices[
#						[getattr(d, 'Default', False) for d in core_classes.DateChoices].index(True)]
#			self.DateChoice.Widget.SetSelection(core_classes.DateChoices.index(DateToShow))

		def SetWidgetVisibility(self, **Args):
			# set IsVisible attribs for all fixed and variable widgets
			for ThisWidget in self.WidgetList: ThisWidget.IsVisible = True

	def DoExportATsToFile(self, **ExportInput):
		# handle request to proceed with export of ATs to Excel file
		print('AR364 in DoExportATsToFile')
		self.DoExportToExcel(**ExportInput)

	@classmethod
	def GetFullRedrawData(cls, Viewport=None, ViewportClass=None, **Args):
		# a datacore method. Provide data for redraw of this Viewport.
		# Args needs 'Proj' as a minimum:
		#	Proj (ProjectItem instance)
		#	AssocTextKind (str; info.ActionItemLabel or info.ParkingLotItemLabel) (now changed: this is in Viewport.RedrawData)
		# return the data as XML string
		# currently this method is identical to the one in class AssocTextListViewport.
		# TODO reuse same code - could be done via decorator, as for UnpackDataFromDatacore()

		def MakeAssocTextLookupTable(Proj, ATKind):
			# make and return dictionary with keys = ATs, values = list of PHA elements containing the AT
			# We assume the element's attrib containing the AT is named the same as AssocTextKind; if not,
			# its ATs won't be found
			assert ATKind in (info.ActionItemLabel, info.ParkingLotItemLabel)
			ATTable = {}
			for ThisPHAElement in Proj.WalkOverAllPHAElements():
				for ThisAT in getattr(ThisPHAElement, ATKind, []):
					if ThisAT in ATTable:
						ATTable[ThisAT].append(ThisPHAElement)
					else:
						ATTable[ThisAT] = [ThisPHAElement]
			return ATTable

		# start of GetFullRedrawData()
		assert Viewport.RedrawData[info.AssociatedTextKindTag] in (info.ActionItemLabel, info.ParkingLotItemLabel)
		Proj = Args['Proj']
		# find out what kind of AT is required, from the Viewport shadow's redraw data
		ATKind = Viewport.RedrawData[info.AssociatedTextKindTag]
		print('AR505 AT kind requested: ', ATKind)
		# get a lookup table of all ATs of the appropriate kind in the project
		ATTable = MakeAssocTextLookupTable(Proj=Proj, ATKind=ATKind)
		# First, make the root element
		RootElement = ElementTree.Element(info.PHAModelRedrawDataTag)
		RootElement.set(info.PHAModelTypeTag, cls.InternalName)
		# add a subelement containing the kind of associated text
		ATKindEl = ElementTree.SubElement(RootElement, info.AssociatedTextKindTag)
		ATKindEl.text = ATKind
		# identify master list containing all associated text items to show
		AssocTextMasterList = Proj.ActionItems if ATKind == info.ActionItemLabel else Proj.ParkingLot
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
			# TODO put this code for getting displayable name in a more general place. It'll be needed elsewhere
			for ThisPHAElement in ATTable.get(ThisAssocTextItem, []):
				PHAElUsingEl = ElementTree.SubElement(ATEl, info.PHAElementTag)
				DisplayableElementName = ': ' + ThisPHAElement.HumanName if ThisPHAElement.HumanName else ''
				DisplayableElementNumbering = \
				ThisPHAElement.Numbering.HumanValue(PHAItem=ThisPHAElement, Host=ThisPHAElement.Siblings)[0]
				if DisplayableElementNumbering: DisplayableElementNumbering = ' ' + DisplayableElementNumbering
				DisplayableHostName = ThisPHAElement.HostPHAObj.HumanName if ThisPHAElement.HostPHAObj.HumanName else \
					type(ThisPHAElement.HostPHAObj).HumanName
				PHAElUsingEl.text = ThisPHAElement.ClassHumanName + \
									DisplayableElementNumbering + \
									DisplayableElementName + ' ' + _('in') + ' ' + DisplayableHostName
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
		return RootElement

	def AllClickableObjects(self, **Args):
		# no graphical objects requiring special mouse click handlers
		return []

	def RenderInDC(self, DC, **Args):
		# currently no graphics to render in a DC. For future, may provide a zoom tool
		pass

	@classmethod
	def GetClassAttribsOnInit(cls, XMLRoot):
		# return dict of attrib names and values that need to be stored in this Viewport's ViewportShadow when created.
		# Values must be str (as they will be supplied directly to an XML tree)
		# This is an optional datacore side class method for Viewports
		assert isinstance(XMLRoot, ElementTree.Element)
		assert info.AssociatedTextKindTag in [t.tag for t in XMLRoot]
		return {info.AssociatedTextKindTag: XMLRoot.findtext(info.AssociatedTextKindTag)}

	@classmethod
	def GetClassAttribsRequired(cls, **Args):
		# optional client side method - similar to GetClassAttribsOnInit(), but using Args instead of XMLRoot
		assert info.AssociatedTextKindTag in Args
		return {info.AssociatedTextKindTag: Args[info.AssociatedTextKindTag]}

	@classmethod
	def HandleIncomingRequest(cls, MessageReceived=None, MessageAsXMLTree=None, **Args):
		# handle request received by this Viewport in datacore
		# Incoming message can be supplied as either an XML string or XML tree root element
		# MessageReceived (str or None): XML message containing request info
		# MessageAsXMLTree (XML element or None): root of XML tree
		# return Reply (Root object of XML tree)
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
		# handle incoming commands
		if Command == 'RQ_ZZ_UpdateATExportAttribs': cls.UpdateATExportAttribs(Proj, XMLRoot)
		if Reply.tag == 'Fail': print('AR591 command not recognised: ', Command)
		return Reply

	def ReleaseDisplayDevice(self, DisplDevice, **Args):
		# wrap-up actions needed when display device is no longer showing associated texts report dialogue
		self.DisplDevice = None

	@classmethod
	def UpdateATExportAttribs(cls, Proj, XMLRoot):
		# store attribs for AT report dialogue in project
		assert isinstance(Proj, projects.ProjectItem)
		Proj.ATExportFilename = XMLRoot.findtext('Filename')
		Proj.ATExportShowWhat = XMLRoot.findtext('ExportWhat')
		Proj.LastExportPageSize = utilities.InstanceWithAttribValue(ObjList=core_classes.PaperSizes,
			AttribName='XMLName', TargetValue=XMLRoot.findtext('PageSize'),
			NotFoundValue=core_classes.PaperSizes[0])
		Proj.ATExportPaperOrientation = XMLRoot.findtext('PaperOrientation')
		Proj.LastExportFontName = XMLRoot.findtext('Font')
#		Proj.LastExportPreferredDateToShow = utilities.InstanceWithAttribValue(ObjList=core_classes.DateChoices,
#			AttribName='XMLName', TargetValue=XMLRoot.findtext('DateToShow'),
#			NotFoundValue=core_classes.DateChoices[0])
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def DoExportToExcel(self, FontName='', FilePath='',
				FileType='',
				ShowWhat='',
				PageSizeLongAxis=0,
				PageSizeShortAxis=0,
				Orientation='',**Args):
		# build export Excel workbook of associated texts

		def GetEmptyCell(MergeToRight=False):
			# make and return new empty cell object. MergedToRight is set according to MergeToRight arg
			assert isinstance(MergeToRight, bool)
			return excel_export.ExcelTable_Component(MergeToRight=MergeToRight, RelPosDirection=info.RightLabel)

		def MakeSummaryTable(Borders=None):
			# build structure of table summarising the number of ATs shown, and other data
			# return the Table
			assert isinstance(Borders, excel_export.ExcelTable_Border)
			ST = excel_export.ExcelTable_Table(GapBelow=1, TopBorder=Borders, BottomBorder=Borders,
				LeftBorder=Borders, RightBorder=Borders)
			Col1CellCount = 3 # number of horizontally merged cells in each table column
			Col2CellCount = 3

			# header row
			HeaderRowFirstCell = excel_export.ExcelTable_Component(BottomBorder=NormalInnerBorder,
				Content={info.ActionItemLabel: 'ACTION ITEMS', info.ParkingLotItemLabel: 'PARKING LOT'}[self.AssocTextKind],
				VertAlignment=info.CentreLabel, HorizAlignment=info.CentreLabel, FontStyle=TitleFont,
				BackgColour=TitleBackgColour, RelWidth=1.0, MergeToRight=True)
			ST.Components.append(HeaderRowFirstCell)
			# fill up to end of table on right
			HeaderRowCells = [HeaderRowFirstCell]
			for i in range(Col1CellCount + Col2CellCount - 2):
				HeaderRowCells.append(GetEmptyCell(MergeToRight=True))
			HeaderRowCells.append(GetEmptyCell())
			# connect each cell to the one on the left
			for (ThisIndex, ThisCell) in enumerate(HeaderRowCells[1:]):
				ThisCell.PositionRelativeTo = HeaderRowCells[ThisIndex]
			ST.Components.extend(HeaderRowCells)

			# report date and edit number row
			DateLabelCell = excel_export.ExcelTable_Component(BottomBorder=NormalInnerBorder,
				Content=_('Date: '), PositionRelativeTo=HeaderRowFirstCell, RelPosDirection=info.BelowLabel,
				VertAlignment=info.TopLabel, HorizAlignment=info.LeftLabel, FontStyle=NormalFont,
				BackgColour=NormalBackgColour, RelWidth=1.0, MergeToRight=True)
			DateRowCells = [DateLabelCell]
			# fill up to end of column 1
			for i in range(Col1CellCount - 2):
				DateRowCells.append(GetEmptyCell(MergeToRight=True))
			DateRowLastCell = GetEmptyCell()
			DateRowCells.append(DateRowLastCell)
			DateRowLastCell.RightBorder = LightInnerBorder
			EditNumberCell = excel_export.ExcelTable_Component(BottomBorder=NormalInnerBorder,
				Content=_('Edit number: %d ' % self.Proj.EditNumber), PositionRelativeTo=DateRowLastCell,
				RelPosDirection=info.RightLabel,
				VertAlignment=info.TopLabel, HorizAlignment=info.LeftLabel, FontStyle=NormalFont,
				BackgColour=NormalBackgColour, RelWidth=1.0, MergeToRight=True)
			DateRowCells.append(EditNumberCell)
			# fill up to end of column 2
			for i in range(Col2CellCount - 2):
				DateRowCells.append(GetEmptyCell(MergeToRight=True))
			DateRowCells.append(GetEmptyCell())
			# connect each cell to the one on the left
			for (ThisIndex, ThisCell) in enumerate(DateRowCells[1:]):
				ThisCell.PositionRelativeTo = DateRowCells[ThisIndex]
			ST.Components.extend(DateRowCells)

			# status name and count header row
			StatusNameLabelCell = excel_export.ExcelTable_Component(BottomBorder=NormalInnerBorder,
				Content=_('Status'), PositionRelativeTo=DateLabelCell, RelPosDirection=info.BelowLabel,
				VertAlignment=info.CentreLabel, HorizAlignment=info.CentreLabel, FontStyle=Header1Font,
				BackgColour=NormalBackgColour, RelWidth=1.0, MergeToRight=True)
			StatusHeaderRowCells = [StatusNameLabelCell]
			# fill up to end of column 1
			for i in range(Col1CellCount - 2):
				StatusHeaderRowCells.append(GetEmptyCell(MergeToRight=True))
			StatusHeaderRowLastCell = GetEmptyCell()
			StatusHeaderRowCells.append(StatusHeaderRowLastCell)
			StatusHeaderRowLastCell.RightBorder = LightInnerBorder
			StatusCountLabelCell = excel_export.ExcelTable_Component(BottomBorder=NormalInnerBorder,
				Content=_('Number of items'), PositionRelativeTo=StatusHeaderRowLastCell,
				RelPosDirection=info.RightLabel,
				VertAlignment=info.CentreLabel, HorizAlignment=info.CentreLabel, FontStyle=Header1Font,
				BackgColour=NormalBackgColour, RelWidth=1.0, MergeToRight=True)
			StatusHeaderRowCells.append(StatusCountLabelCell)
			# fill up to end of column 2
			for i in range(Col2CellCount - 2):
				StatusHeaderRowCells.append(GetEmptyCell(MergeToRight=True))
			StatusHeaderRowCells.append(GetEmptyCell())
			# connect each cell to the one on the left
			for (ThisIndex, ThisCell) in enumerate(StatusHeaderRowCells[1:]):
				ThisCell.PositionRelativeTo = StatusHeaderRowCells[ThisIndex]
			ST.Components.extend(StatusHeaderRowCells)

			# rows for each AT status
			StatusCounts = self.GetATStatusCounts()
			RowStartReference = StatusNameLabelCell # position reference for the start of 1st row
			for (ThisStatus, ThisStatusCount) in StatusCounts.items():
				StatusNameCell = excel_export.ExcelTable_Component(BottomBorder=LightInnerBorder,
					Content=ThisStatus, PositionRelativeTo=RowStartReference, RelPosDirection=info.BelowLabel,
					VertAlignment=info.TopLabel, HorizAlignment=info.LeftLabel, FontStyle=NormalFont,
					BackgColour=NormalBackgColour, RelWidth=1.0, MergeToRight=True)
				StatusRowCells = [StatusNameCell]
				RowStartReference = StatusNameCell # reference for starting next row
				# fill up to end of column 1
				for i in range(Col1CellCount - 2):
					StatusRowCells.append(GetEmptyCell(MergeToRight=True))
				StatusNameRowLastCell = GetEmptyCell()
				StatusRowCells.append(StatusNameRowLastCell)
				StatusNameRowLastCell.RightBorder = LightInnerBorder
				# status count for this row
				StatusCountCell = excel_export.ExcelTable_Component(BottomBorder=LightInnerBorder,
					Content=ThisStatus, PositionRelativeTo=StatusNameRowLastCell, RelPosDirection=info.RightLabel,
					VertAlignment=info.TopLabel, HorizAlignment=info.CentreLabel, FontStyle=NormalFont,
					BackgColour=NormalBackgColour, RelWidth=1.0, MergeToRight=True)
				StatusRowCells.append(StatusCountCell)
				# fill up to end of column 2
				for i in range(Col2CellCount - 2):
					StatusRowCells.append(GetEmptyCell(MergeToRight=True))
				StatusCountRowLastCell = GetEmptyCell()
				StatusRowCells.append(StatusCountRowLastCell)
				# connect each cell to the one on the left
				for (ThisIndex, ThisCell) in enumerate(StatusRowCells[1:]):
					ThisCell.PositionRelativeTo = StatusRowCells[ThisIndex]
				ST.Components.extend(StatusRowCells)
			return ST

		def MakeATTable(Borders=None):
			# build structure of table listing the required ATs
			# return the Table
			assert isinstance(Borders, excel_export.ExcelTable_Border)
			ATT = excel_export.ExcelTable_Table(GapBelow=1, TopBorder=Borders, BottomBorder=Borders,
				LeftBorder=Borders, RightBorder=Borders)
			Col1CellCount = 3 # number of horizontally merged cells in each table column
			Col2CellCount = 3
			print('AR791 to complete routine to set up table structure')
			return ATT

		# main procedure for DoExportToExcel()%%%
		assert isinstance(FontName, str)
		assert isinstance(FilePath, str)
		assert FileType == info.ExcelExtension
		assert isinstance(ShowWhat, str)
		assert isinstance(PageSizeLongAxis, (int, float))
		assert isinstance(PageSizeShortAxis, (int, float))
		assert 0 < PageSizeShortAxis <= PageSizeLongAxis
		assert Orientation in [info.PortraitLabel, info.LandscapeLabel]
		OuterBorderColour = (0x00, 0x00, 0x00) # black
		InnerBorderColour = (0x80, 0x80, 0x80) # mid grey
		TitleBackgColour = (0x6E, 0xDF, 0x6F) # pale green
		NormalBackgColour = (0xff, 0xff, 0xff) # white
		TitleFont = wx.Font(wx.FontInfo(14).FaceName(FontName).Bold())
		Header1Font = wx.Font(wx.FontInfo(12).FaceName(FontName).Bold())
		NormalFont = wx.Font(wx.FontInfo(12).FaceName(FontName))
		XLWorkbook = excel_export.SetupWorkbook()
		TabName = _({info.ActionItemLabel: 'Action items', info.ParkingLotItemLabel: 'Parking lot'}[self.AssocTextKind])
		TabColour = (200,200,255)
		XLWorksheet = excel_export.SetupWorksheet(WB=XLWorkbook, TabName=TabName, TabColour=TabColour)
		# make border objects
		HeavyBorder = excel_export.ExcelTable_Border(Style='medium', Colour=OuterBorderColour)
		NormalInnerBorder = excel_export.ExcelTable_Border(Style='thin', Colour=InnerBorderColour)
		LightInnerBorder = excel_export.ExcelTable_Border(Style='hair', Colour=InnerBorderColour)
		AbsWSWidth = PageSizeShortAxis if Orientation == info.PortraitLabel else PageSizeLongAxis
		# make a ExcelSheet object to populate with tables
		MySheet = excel_export.ExcelTable_Sheet(TabName=TabName, TabColour=TabColour,
			TargetWidth=AbsWSWidth)
		# make the tables and put them in MySheet
		MySheet.Tables.append(MakeSummaryTable(Borders=HeavyBorder))
#		MySheet.Tables.append(MakeATTable(Borders=HeavyBorder))
		# generate the Excel spreadsheet
		MySheet.PopulateSheet(WS=XLWorksheet, AbsSheetWidth=AbsWSWidth)
		# write the Excel spreadsheet to file
		excel_export.WriteWBToFile(WB=XLWorkbook, FilePath=FilePath)

	def GetATStatusCounts(self, Scope=info.AllItemsLabel):
		# make and return dict with keys = AT statuses, values = number of ATs in Scope
		# status matching is case insensitive. The case returned for each status is the first one encountered
		assert Scope in [info.AllItemsLabel, info.FilteredItemsLabel]
		FilteredOnly = (Scope == info.FilteredItemsLabel)
		StatusCounts = {} # values are counts of ATs with each status, keys in uppercase
		StatusHash = {} # keys are uppercase stati, values are the casing of the first such status encountered
		for ThisAT in self.AssocTexts:
			if (not FilteredOnly) or ThisAT.FilteredIn:
				# is this AT's status already in StatusCounts? If so, add to the count; else add a new key
				if ThisAT.Status.upper() in StatusCounts.keys():
					StatusCounts[ThisAT.Status.upper()] += 1
				else:
					StatusCounts[ThisAT.Status.upper()] = 1
					StatusHash[ThisAT.Status.upper()] = ThisAT.Status
		return dict( [(StatusHash[s], StatusCounts[s]) for s in StatusCounts.keys()] )

	def UnpackDataFromDatacore(self, XMLTree):
		# this method is the same as in class AssocTextListViewport
		self.AssocTexts = [] # start with empty list of AT items
		# find the starting tag
		StartTag = XMLTree.find(info.PHAModelRedrawDataTag)
		# confirm it came from this Viewport class
		assert StartTag.get(info.PHAModelTypeTag) == self.InternalName
		# find subelement containing the kind of associated text
		ATKindEl = StartTag.find(info.AssociatedTextKindTag)
		# confirm it indicates we received action items or parking lot items
		print('AR837 ATKindEl.text, self.AssocTextKind: ', ATKindEl.text, self.AssocTextKind)
		assert ATKindEl.text == self.AssocTextKind
		# fetch tag for each associated text in the project
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
				ThisElUsing = project_display.PHAElementItem(ElementHumanName=ThisElUsingTag.text,
					ElementID=ThisElUsingTag.get(info.IDTag))
				ThisAT.PHAElements.append(ThisElUsing)

class AssocTextItemInDisplay(object):
	# data for associated text items for display. Reflects data held in the actual associated text items in datacore

	def __init__(self):
		object.__init__(self)
		self.ID = ''
		self.Content = ''
		self.Responsibility = ''
		self.Deadline = ''
		self.Status = ''
		self.Numbering = ''
		self.FilteredIn = True # bool; whether this item shows up in the current filters. Defined only if filters are applied.
		self.Selected = False # bool; whether this item is currently selected by the user
		self.PHAElements = [] # list of PHAElementItem instances; all elements in which this AT appears
		self.GridRow = None # row number in grid at which this item is currently displayed, or None if not displayed

	def GetWhereUsedHumanText(self):
		# get human-readable text showing PHA elements where this AT is used
		return '\n'.join([_('%s %s in %s' % (p.ElementHumanName, p.ElementNumber, p.HostHumanName))
			for p in self.PHAElements ])

# %%% working here - transferring methods from ft_full_report. May still need:
# StoreAttribsInProject
# ExitViewportAndRevert
# Deactivate
# GetMilestoneData
