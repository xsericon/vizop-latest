# -*- coding: utf-8 -*-
# Module ft_full_report: part of Vizop, (c) 2019 xSeriCon
# produces full export of a fault tree

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import os, os.path, wx, platform # wx provides basic GUI functions

import core_classes, project_display, vizop_misc, info, utilities, faulttree, display_utilities
from project_display import EditPanelAspectItem
from display_utilities import UIWidgetItem

class FTFullExportViewport(faulttree.FTForDisplay):
	# defines a viewport that produces an export file containing a full depiction of a fault tree, and displays a
	# dialogue to get parameters from the user to control the export (e.g. which items to include, fonts, page settings)
	InternalName = 'FTFullExport' # unique per class, used in messaging
	HumanName = _('Fault Tree full export')
	PreferredKbdShortcut = 'E'
	NewPHAObjRequired = None # which datacore PHA object class this Viewport spawns on creation.
		# Should be None if the model shouldn't create a PHA object
	# VizopTalks message when a new FT is created. NB don't set Priority here, as it is overridden in DoNewViewportCommand()
	NewViewportVizopTalksArgs = {'Title': 'Fault tree full export',
		'MainText': 'Enter the settings you require, then click Go'}
	InitialEditPanelMode = 'Widgets'

	class FTFullExportDialogueAspect(project_display.EditPanelAspectItem):

		def OnFilenameTextWidget(self, Event): pass # write name back into Proj.FTFullExportFilename
		def OnSelectButton(self, Event): pass
		def OnFileTypeChoice(self, Event): pass # write name back into Proj.FTFullExportFileType
		def OnOverwriteCheck(self, Event): # handle click on Overwrite checkbox: store overwrite option
			self.Overwrite = self.OverwriteCheck.Widget.GetValue()

		def OnShowHeaderCheck(self, Event): pass
		def OnShowFTCheck(self, Event): pass
		def OnShowSelectedCheck(self, Event): pass
		def OnPageSizeChoice(self, Event): pass
		def OnPortraitRadio(self, Event): pass
		def OnLandscapeRadio(self, Event): pass
		def OnMarginTextCtrl(self, Event): pass
		def OnPageNumberTopRadio(self, Event): pass
		def OnPageNumberBottomRadio(self, Event): pass
		def OnPageNumberNoneRadio(self, Event): pass
		def OnPageNumberLeftRadio(self, Event): pass
		def OnPageNumberCentreRadio(self, Event): pass
		def OnPageNumberRightRadio(self, Event): pass
		def OnPagesAcrossTextCtrl(self, Event): pass
		def OnPagesDownTextCtrl(self, Event): pass
		def OnNewPagePerRRCheck(self, Event): pass
		def OnZoomTextCtrl(self, Event): pass
		def OnBlackWhiteCheck(self, Event): pass
		def OnFontChoice(self, Event): pass
		def OnConnectorsAcrossPagesCheck(self, Event): pass
		def OnCommentsCheck(self, Event): pass
		def OnActionsCheck(self, Event): pass
		def OnParkingCheck(self, Event): pass
		def OnCannotCalculateTextCtrl(self, Event): pass
		def OnCombineRRsCheck(self, Event): pass
		def OnExpandGatesCheck(self, Event): pass
		def OnDateChoice(self, Event): pass
		def OnCancelButton(self, Event): pass
		def OnGoButton(self, Event): pass

		def Prefill(self, Proj, FT, SystemFontNames):
			# prefill widget values
			# filename is fetched from last used filename in the project
			self.FilenameText.Widget.ChangeValue(Proj.FTFullExportFilename.strip())
			self.FilenameText.Widget.SelectAll()
			# file type is fetched from project
			RecognisedExtensions = [t.Extension for t in core_classes.ImageFileTypesSupported]
			if Proj.FTFullExportFileType in RecognisedExtensions: ExtensionToSelect = Proj.FTFullExportFileType
			else: ExtensionToSelect = info.DefaultImageFileType
			self.FileTypeChoice.Widget.SetSelection(RecognisedExtensions.index(ExtensionToSelect))
			# set overwrite checkbox
			self.OverwriteCheck.Widget.SetValue(self.Overwrite)
			# set filename status message
			self.UpdateFilenameStatusMessage()
			# set scope checkboxes
			self.ShowHeaderCheck.Widget.SetValue(Proj.FTExportShowHeader)
			self.ShowFTCheck.Widget.SetValue(Proj.FTExportShowFT)
			self.ShowOnlySelectedCheck.Widget.SetValue(Proj.FTExportShowOnlySelected)
			# set layout widget values
			# get user's preferred paper size from config file
			PaperSizeStr = vizop_misc.GetValueFromUserConfig('ExportPaperSize')
			if PaperSizeStr == '': PaperSizeStr = info.DefaultPaperSize
			PaperSizesStr = [p.HumanName for p in core_classes.PaperSizes]
			# use 0th paper size if preferred paper size isn't in list of available paper sizes
			TargetPaperSizeIndex = PaperSizesStr.index(PaperSizeStr) if PaperSizeStr in PaperSizesStr else 0
			TargetPaperSize = core_classes.PaperSizes[TargetPaperSizeIndex]
			self.PageSizeChoice.Widget.SetSelection(TargetPaperSizeIndex)
			# set landscape or portrait
			PaperOrientation = vizop_misc.GetValueFromUserConfig('ExportPaperOrientation')
			if PaperOrientation == '': PaperOrientation = info.DefaultPaperOrientation
			if PaperOrientation == 'Portrait': self.PortraitRadio.Widget.SetValue(True)
			elif PaperOrientation == 'Landscape': self.LandscapeRadio.Widget.SetValue(True)
			# set paper margin text boxes
			Margins = {} # store margin values
			for ThisWidget, ConfigName, Default in [
					(self.TopMarginText, 'ExportPaperTopMargin', info.DefaultPaperTopMargin),
					(self.BottomMarginText, 'ExportPaperBottomMargin', info.DefaultPaperBottomMargin),
					(self.LeftMarginText, 'ExportPaperLeftMargin', info.DefaultPaperLeftMargin),
					(self.RightMarginText, 'ExportPaperRightMargin', info.DefaultPaperRightMargin) ]:
				ThisMarginStr = vizop_misc.GetValueFromUserConfig(ConfigName)
				if ThisMarginStr == '': ThisMarginStr = Default
				Margins[ConfigName] = utilities.str2real(ThisMarginStr, meaninglessvalue=12) # used for function call later
				ThisWidget.Widget.ChangeValue(ThisMarginStr.strip())
			# set page number location radio buttons. Expected PageNumberPos is e.g. 'Top,Left'
			PageNumberPos = vizop_misc.GetValueFromUserConfig('ExportPageNumberPos')
			if PageNumberPos == '': PageNumberPos = info.DefaultPaperPageNumberPos
			for ThisWidget, Pos in [ (self.PageNumberTopRadio, 'Top'), (self.PageNumberBottomRadio, 'Bottom'),
					(self.PageNumberLeftRadio, 'Left'), (self.PageNumberRightRadio, 'Right'),
					(self.PageNumberNoneRadio, 'None') ]:
				ThisWidget.Widget.SetValue(Pos in PageNumberPos)
			# set black-and-white checkbox
			self.BlackWhiteCheck.Widget.SetValue(Proj.LastExportBlackAndWhite)
			# set font choice box; first choice is last font used in this project, then last font used by this user
			PreferredFontName = Proj.LastExportFontName
			if PreferredFontName in SystemFontNames: FontNameToUse = PreferredFontName
			else:
				LastUserFontName = vizop_misc.GetValueFromUserConfig('ExportFontName')
				if LastUserFontName in SystemFontNames: FontNameToUse = LastUserFontName
				# if last font name not found, select the first system font name, if any
				elif SystemFontNames: FontNameToUse = SystemFontNames[0]
				else: FontNameToUse = ''
			if FontNameToUse: self.FontChoice.Widget.SetSelection(SystemFontNames.index(FontNameToUse))
			# set depiction checkboxes
			self.ConnectorsAcrossPagesCheck.Widget.SetValue(Proj.FTConnectorsAcrossPages)
			ShowComments = 'Comments' in Proj.FTExportShowPeripheral
			ShowActions = 'Actions' in Proj.FTExportShowPeripheral
			ShowParking = 'Parking' in Proj.FTExportShowPeripheral
			self.CommentsCheck.Widget.SetValue(ShowComments)
			self.ActionsCheck.Widget.SetValue(ShowActions)
			self.ParkingCheck.Widget.SetValue(ShowParking)
			self.CannotCalculateText.Widget.SetValue(Proj.FTExportCannotCalculateText)
			self.CombineRRsCheck.Widget.SetValue(Proj.FTExportCombineRRs)
			self.ExpandGatesCheck.Widget.SetValue(Proj.FTExportExpandGates)
			# set date choice box
			DateChoicesInternalNames = [d.XMLName for d in core_classes.DateChoices]
			PreferredDateToShow = Proj.LastExportPreferredDateToShow
			if PreferredDateToShow in core_classes.DateChoices: DateToShow = PreferredDateToShow
			else:
				LastUserDateToShow = vizop_misc.GetValueFromUserConfig('ExportDateToShow')
				if LastUserDateToShow in DateChoicesInternalNames: DateToShow = LastUserDateToShow
				# if last date kind not found, select the date kind flagged as 'Default'
				else: DateToShow = core_classes.DateChoices[
					[getattr(d, 'Default', False) for d in core_classes.DateChoices].index(True)]
			self.DateChoice.Widget.SetSelection(core_classes.DateChoices.index(DateToShow))
			# set NewPagePerRRCheck
			self.NewPagePerRRCheck.Widget.SetValue(Proj.FTExportNewPagePerRR)
			# set zoom and pages across/down value widgets. Zoom value is the last value used in this project;
			# Pages across/down is the required number at this zoom level
			Zoom = Proj.FTFullExportZoom
			self.ZoomText.Widget.ChangeValue(str(Zoom))
			self.ZoomText.Widget.SelectAll()
			PageCountInput = {'FT': FT, 'Zoom': Zoom, 'ShowHeader': Proj.FTExportShowHeader,
				'ShowFT': Proj.FTExportShowFT, 'ShowOnlySelected': Proj.FTExportShowOnlySelected,
				'PageSizeLongAxis': TargetPaperSize.SizeLongAxis, 'PageSizeShortAxis': TargetPaperSize.SizeShortAxis,
				'Orientation': PaperOrientation, 'TopMargin': Margins['ExportPaperTopMargin'],
				'BottomMargin': Margins['ExportPaperBottomMargin'],
				'LeftMargin': Margins['ExportPaperLeftMargin'], 'RightMargin': Margins['ExportPaperRightMargin'],
				'PageNumberPos': PageNumberPos,
				'NewPagePerRR': Proj.FTExportNewPagePerRR, 'Font': FontNameToUse,
				'ConnectorsAcrossPages': Proj.FTConnectorsAcrossPages,
				'ShowComments': ShowComments, 'ShowActions': ShowActions, 'ShowParking': ShowParking,
				'CannotCalculateText': Proj.FTExportCannotCalculateText, 'CombineRRs': Proj.FTExportCombineRRs,
				'ExpandGates': Proj.FTExportExpandGates, 'DateKind': DateToShow }
			PageCountInfo = FT.GetPageCountInfo(**PageCountInput)
			self.PagesAcrossText.Widget.ChangeValue(str(PageCountInfo['PagesAcrossCount']))
			self.PagesAcrossText.Widget.SelectAll()
			self.PagesDownText.Widget.ChangeValue(str(PageCountInfo['PagesDownCount']))
			self.PagesDownText.Widget.SelectAll()

		def UpdateFilenameStatusMessage(self):
			# update filename status message widget text
			FilePathSupplied = self.FilenameText.Widget.GetValue().strip()
			# 1. Filename text box empty, or whitespace only, or contains a directory path
			if (not FilePathSupplied) or os.path.isdir(FilePathSupplied):
				Message = _('Please provide a filename for the export')
			# 2. Path supplied is a writeable, nonexistent filename
			elif vizop_misc.IsWriteableAsNewFile(FilePathSupplied):
				Message = _('Ready to export to new file. Click Go')
			# 3. Path points to an existent file that can be overwritten, and Overwrite check box is checked
			elif os.path.isfile(FilePathSupplied) and os.access(FilePathSupplied, os.W_OK) and \
					ThisAspect.OverwriteCheck.Widget.GetValue():
				Message = _('Ready to export. File will be overwritten when you click Go')
			# 4. Path points to an existent file that can be overwritten, and Overwrite check box is unchecked
			elif os.path.isfile(FilePathSupplied) and os.access(FilePathSupplied, os.W_OK) and \
					not ThisAspect.OverwriteCheck.Widget.GetValue():
				Message = _('File exists. Click "Overwrite", then "Go"')
			# 5. Path points to a writeable folder, but no extension is provided and it is needed (i.e. Windows)
			elif vizop_misc.IsWritableLocation(FilePathSupplied) and os.path.splitext(FilePathSupplied)[1] in ['', '.'] \
					and platform.system() == 'Windows':
				Message = _('Please provide a valid file extension, e.g. .pdf')
			# 6. Path points to a nonexistent folder, or a folder with no write access
			elif not vizop_misc.IsWritableLocation(FilePathSupplied):
				Message = _("%s can't write to that location") % info.PROG_SHORT_NAME
			# 99. Some other case we haven't thought of
			else: Message = _('You should buy a lottery ticket today')
			self.FilenameStatusMessage.Widget.SetLabel(Message)

		def SetWidgetVisibility(self, **Args):
			# set IsVisible attribs for all fixed and variable widgets
			for ThisWidget in self.WidgetList: ThisWidget.IsVisible = True

		def __init__(self, InternalName, ParentFrame, TopLevelFrame):
			project_display.EditPanelAspectItem.__init__(self, WidgetList=[], InternalName=InternalName,
				ParentFrame=ParentFrame, TopLevelFrame=TopLevelFrame, PrefillMethod=self.Prefill,
				SetWidgetVisibilityMethod=self.SetWidgetVisibility)
			self.Overwrite = False # whether to overwrite any existing file when exporting

	def MakeFTFullExportAspect(self, MyEditPanel, Fonts, SystemFontNames, DateChoices):
		# make Control Panel aspect for PHAModel control
		# fonts (dict): internal font objects such as SmallHeadingFont
		# SystemFontNames (list of str): names of "real" fonts available on the platform
		# DateChoices (list of ChoiceItem): options for date to show in FT
		# return the aspect
		# make basic attribs needed for the aspect
		MyEditPanel.FTFullExportAspect = FTFullExportViewport.FTFullExportDialogueAspect(InternalName='FTFullExport',
			ParentFrame=MyEditPanel, TopLevelFrame=MyEditPanel.TopLevelFrame)
		ThisAspect = MyEditPanel.FTFullExportAspect
		# make box sizers to contain groups of widgets
		FileBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('About the file to export'))
		FileBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		FileBoxSizer.Add(FileBoxSubSizer)
		ScopeBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('What to include in the export'))
		ScopeBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		ScopeBoxSizer.Add(ScopeBoxSubSizer)
		PageLayoutBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('Page layout'))
		PageLayoutBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		PageLayoutBoxSizer.Add(PageLayoutBoxSubSizer)
		StyleBoxSizer = wx.StaticBoxSizer(orient=wx.VERTICAL, parent=MyEditPanel, label=_('Fault Tree style'))
		StyleBoxSubSizer = wx.GridBagSizer(hgap=5, vgap=5)
		StyleBoxSizer.Add(StyleBoxSubSizer)
		# make header widget
		ThisAspect.HeaderLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
			_('Export full Fault Tree report')),
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapY=10,
			ColLoc=0, ColSpan=10, Font=Fonts['BigHeadingFont'], NewRow=True)
		ThisAspect.FileBox = UIWidgetItem(FileBoxSizer, HideMethod=lambda : FileBoxSizer.ShowItems(False),
			ShowMethod=lambda : FileBoxSizer.ShowItems(True), ColLoc=0, ColSpan=5, NewRow=True,
			SetFontMethod=lambda f: FileBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.FilenameLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Filename:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.FilenameText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE),
			MinSizeY=25, Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnFilenameTextWidget, GapX=5,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
			MinSizeX=300, ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
		ThisAspect.SelectButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Select')),
			Handler=ThisAspect.OnSelectButton, Events=[wx.EVT_BUTTON], ColLoc=3, ColSpan=1,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
		ThisAspect.FileTypeLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Type:')),
			ColLoc=4, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.FileTypeChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(70, 25),
			choices=[t.HumanName for t in core_classes.ImageFileTypesSupported]),
			Handler=ThisAspect.OnFileTypeChoice, Events=[wx.EVT_CHOICE], ColLoc=5, ColSpan=1)
		ThisAspect.OverwriteCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Overwrite')),
			Handler=ThisAspect.OnOverwriteCheck, Events=[wx.EVT_CHECKBOX], ColLoc=2, ColSpan=1, NewRow=True)
		ThisAspect.FilenameStatusMessage = UIWidgetItem(wx.StaticText(MyEditPanel, -1, ''),
			ColLoc=2, ColSpan=3, Font=Fonts['BoldFont'], NewRow=True)
		# add widgets to FileBoxSubSizer
		display_utilities.PopulateSizer(Sizer=FileBoxSubSizer, Widgets=[ThisAspect.FilenameLabel,
			ThisAspect.FilenameText, ThisAspect.SelectButton, ThisAspect.FileTypeLabel, ThisAspect.FileTypeChoice,
			ThisAspect.OverwriteCheck, ThisAspect.FilenameStatusMessage])
		# widgets in "scope" box
		ThisAspect.ScopeBox = UIWidgetItem(ScopeBoxSizer, HideMethod=lambda : ScopeBoxSizer.ShowItems(False),
			ShowMethod=lambda : ScopeBoxSizer.ShowItems(True), ColLoc=0, ColSpan=5, NewRow=True,
			SetFontMethod=lambda f: ScopeBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.ExportWhatLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Export what:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.ShowHeaderCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Header block')),
			Handler=ThisAspect.OnShowHeaderCheck, Events=[wx.EVT_CHECKBOX], ColLoc=1, ColSpan=1)
		ThisAspect.ShowFTCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Fault tree')),
			Handler=ThisAspect.OnShowFTCheck, Events=[wx.EVT_CHECKBOX], ColLoc=2, ColSpan=1)
		ThisAspect.ShowOnlySelectedCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Selected elements only')),
			Handler=ThisAspect.OnShowSelectedCheck, Events=[wx.EVT_CHECKBOX], ColLoc=3, ColSpan=1)
		ThisAspect.IncludeWhatLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Include:')), NewRow=True,
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.CommentsCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Comments')),
			Handler=ThisAspect.OnCommentsCheck, Events=[wx.EVT_CHECKBOX], ColLoc=1, ColSpan=1)
		ThisAspect.ActionsCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Action items')),
			Handler=ThisAspect.OnActionsCheck, Events=[wx.EVT_CHECKBOX], ColLoc=2, ColSpan=1)
		ThisAspect.ParkingCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Parking lot items')),
			Handler=ThisAspect.OnParkingCheck, Events=[wx.EVT_CHECKBOX], ColLoc=3, ColSpan=1)
		# add widgets to FileBoxSubSizer
		display_utilities.PopulateSizer(Sizer=ScopeBoxSubSizer, Widgets=[ThisAspect.ExportWhatLabel,
			ThisAspect.ShowHeaderCheck, ThisAspect.ShowFTCheck, ThisAspect.ShowOnlySelectedCheck,
			ThisAspect.IncludeWhatLabel, ThisAspect.CommentsCheck, ThisAspect.ActionsCheck, ThisAspect.ParkingCheck])
		# widgets in "page layout" box
		ThisAspect.PageLayoutBox = UIWidgetItem(PageLayoutBoxSizer, HideMethod=lambda : PageLayoutBoxSizer.ShowItems(False),
			ShowMethod=lambda : PageLayoutBoxSizer.ShowItems(True), ColLoc=5, ColSpan=5, RowSpan=2,
			SetFontMethod=lambda f: PageLayoutBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
#		ThisAspect.PageLayoutLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
#			_('Page layout')),
#			ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'])
		ThisAspect.PageSizeLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Page size:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.PageSizeChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(200, 25),
			choices=[t.FullNameForDisplay for t in core_classes.PaperSizes]),
			Handler=ThisAspect.OnPageSizeChoice, Events=[wx.EVT_CHOICE], ColLoc=1, ColSpan=3)
		ThisAspect.PortraitRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Portrait'), style=wx.RB_GROUP),
			Handler=ThisAspect.OnPortraitRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
		ThisAspect.LandscapeRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Landscape')),
			Handler=ThisAspect.OnLandscapeRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
		ThisAspect.MarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Margins (mm):')),
			ColLoc=0, ColSpan=1, NewRow=True, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.TopMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Top')),
			ColLoc=1, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.TopMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
			DisplayMethod='StaticFromText')
		ThisAspect.BottomMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Bottom')),
			ColLoc=1, ColSpan=1, NewRow=True, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.BottomMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
			DisplayMethod='StaticFromText')
		ThisAspect.LeftMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Left')),
			ColLoc=1, ColSpan=1, NewRow=True, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.LeftMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
			DisplayMethod='StaticFromText')
		ThisAspect.RightMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Right')),
			ColLoc=1, ColSpan=1, NewRow=True, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.RightMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
			DisplayMethod='StaticFromText')
		ThisAspect.PageNumberingLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Page numbers\nat:'),
			style=wx.ALIGN_RIGHT), ColLoc=3, ColSpan=1, RowSpan=2)
		ThisAspect.PageNumberTopRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Top'), style=wx.RB_GROUP),
			Handler=ThisAspect.OnPageNumberTopRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
		ThisAspect.PageNumberBottomRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Bottom')),
			Handler=ThisAspect.OnPageNumberBottomRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
		ThisAspect.PageNumberNoneRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('None')),
			Handler=ThisAspect.OnPageNumberNoneRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
		ThisAspect.PageNumberLeftRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Left'), style=wx.RB_GROUP),
			Handler=ThisAspect.OnPageNumberLeftRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
		ThisAspect.PageNumberCentreRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Centre')),
			Handler=ThisAspect.OnPageNumberCentreRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
		ThisAspect.PageNumberRightRadio = UIWidgetItem(wx.RadioButton(MyEditPanel, -1, _('Right')), GapY=10,
			Handler=ThisAspect.OnPageNumberRightRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
		ThisAspect.HowManyPagesLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Fit to how\nmany pages:')),
			ColLoc=0, ColSpan=1, RowSpan=2, NewRow=True, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.PagesAcrossLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Across')),
			ColLoc=1, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.PagesAcrossText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnPagesAcrossTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
			ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
		ThisAspect.ZoomLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Zoom (%)')),
			ColLoc=3, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.ZoomText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnZoomTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=50,
			ColLoc=4, ColSpan=1, DisplayMethod='StaticFromText')
		ThisAspect.PagesDownLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Down')), NewRow=True,
			ColLoc=1, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.PagesDownText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnPagesDownTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
			ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
		ThisAspect.NewPagePerRRCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('New page for each risk receptor')),
			Handler=ThisAspect.OnNewPagePerRRCheck, Events=[wx.EVT_CHECKBOX], ColLoc=3, ColSpan=3,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		# add widgets to PageLayoutBoxSubSizer
		display_utilities.PopulateSizer(Sizer=PageLayoutBoxSubSizer, Widgets=[ThisAspect.PageSizeLabel,
			ThisAspect.PageSizeChoice, ThisAspect.PortraitRadio, ThisAspect.LandscapeRadio,
			ThisAspect.MarginLabel, ThisAspect.TopMarginLabel, ThisAspect.TopMarginText,
			ThisAspect.BottomMarginLabel, ThisAspect.BottomMarginText, ThisAspect.PageNumberingLabel,
				ThisAspect.PageNumberTopRadio, ThisAspect.PageNumberLeftRadio,
			ThisAspect.LeftMarginLabel, ThisAspect.LeftMarginText, ThisAspect.PageNumberBottomRadio,
				ThisAspect.PageNumberCentreRadio,
			ThisAspect.RightMarginLabel, ThisAspect.RightMarginText, ThisAspect.PageNumberNoneRadio,
				ThisAspect.PageNumberRightRadio,
			ThisAspect.HowManyPagesLabel, ThisAspect.PagesAcrossLabel, ThisAspect.PagesAcrossText,
				ThisAspect.ZoomLabel, ThisAspect.ZoomText,
			ThisAspect.PagesDownLabel, ThisAspect.PagesDownText, ThisAspect.NewPagePerRRCheck])
		# make Style box and widgets
		ThisAspect.StyleBox = UIWidgetItem(StyleBoxSizer, HideMethod=lambda : StyleBoxSizer.ShowItems(False),
			ShowMethod=lambda : StyleBoxSizer.ShowItems(True), ColLoc=0, ColSpan=10, NewRow=True, GapY=20,
			SetFontMethod=lambda f: StyleBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
#		ThisAspect.StyleLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Style')),
#			YGap=20, ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'], NewRow=True)
		ThisAspect.FontLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Font:')),
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.FontChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(200, 25),
			choices=SystemFontNames),
			Handler=ThisAspect.OnFontChoice, Events=[wx.EVT_CHOICE], ColLoc=1, ColSpan=2)
		ThisAspect.ConnectorsAcrossPagesCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Add connectors across page breaks')),
			Handler=ThisAspect.OnConnectorsAcrossPagesCheck, Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1, GapX=20)
		ThisAspect.DateLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Show date:')), NewRow=True,
			ColLoc=0, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT)
		ThisAspect.DateChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(100, 25),
			choices=[c.HumanName for c in DateChoices]),
			Handler=ThisAspect.OnDateChoice, Events=[wx.EVT_CHOICE], ColLoc=1, ColSpan=1)
		ThisAspect.CombineRRsCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Combine FTs for risk receptors where possible')),
			Handler=ThisAspect.OnCombineRRsCheck, Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1)
		ThisAspect.CannotCalculateLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
			_('For values that cannot be calculated, show')), Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT,
			ColLoc=0, ColSpan=2, NewRow=True)
		ThisAspect.CannotCalculateText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
			Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnCannotCalculateTextCtrl,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
			ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
		ThisAspect.ExpandGatesCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Expand logic gates')),
			Handler=ThisAspect.OnExpandGatesCheck, Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1)
		ThisAspect.BlackWhiteCheck = UIWidgetItem(wx.CheckBox(MyEditPanel, -1, _('Monochrome')), NewRow=True,
			Handler=ThisAspect.OnBlackWhiteCheck, Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1)
#		ThisAspect.DepictionLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
#			_('Fault tree depiction')),
#			YGap=20, ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'], NewRow=True)
		display_utilities.PopulateSizer(Sizer=StyleBoxSubSizer, Widgets=[
			ThisAspect.FontLabel, ThisAspect.FontChoice, ThisAspect.ConnectorsAcrossPagesCheck,
			ThisAspect.DateLabel, ThisAspect.DateChoice, ThisAspect.CombineRRsCheck,
			ThisAspect.CannotCalculateLabel, ThisAspect.CannotCalculateText,
			ThisAspect.ExpandGatesCheck, ThisAspect.BlackWhiteCheck])
		ThisAspect.CancelButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Cancel')), GapX=100,
			Handler=ThisAspect.OnCancelButton, Events=[wx.EVT_BUTTON], ColLoc=1, ColSpan=1, NewRow=True,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
		ThisAspect.GoButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Go')), GapX=20,
			Handler=ThisAspect.OnGoButton, Events=[wx.EVT_BUTTON], ColLoc=3, ColSpan=1,
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)

		# make list of widgets in this aspect
		ThisAspect.WidgetList = [ThisAspect.HeaderLabel,
			ThisAspect.FileBox,
			ThisAspect.PageLayoutBox,
#			ThisAspect.FilenameLabel, ThisAspect.FilenameText, ThisAspect.SelectButton, ThisAspect.FileTypeLabel,
#				ThisAspect.FileTypeChoice,
#			ThisAspect.OverwriteCheck,
#			ThisAspect.FilenameStatusMessage,
#			ThisAspect.ExportWhatLabel, ThisAspect.ShowHeaderCheck, ThisAspect.ShowFTCheck, ThisAspect.ShowOnlySelectedCheck,
			ThisAspect.ScopeBox,
#			ThisAspect.PageLayoutLabel,
#			ThisAspect.PageSizeLabel, ThisAspect.PageSizeChoice, ThisAspect.PortraitRadio, ThisAspect.LandscapeRadio,
#			ThisAspect.MarginLabel, ThisAspect.TopMarginLabel, ThisAspect.TopMarginText, ThisAspect.PageNumberingLabel,
#				ThisAspect.PageNumberTopRadio, ThisAspect.PageNumberLeftRadio,
#			ThisAspect.BottomMarginLabel, ThisAspect.BottomMarginText, ThisAspect.PageNumberBottomRadio,
#				ThisAspect.PageNumberCentreRadio,
#			ThisAspect.LeftMarginLabel, ThisAspect.LeftMarginText, ThisAspect.PageNumberNoneRadio,
#				ThisAspect.PageNumberRightRadio,
#			ThisAspect.RightMarginLabel, ThisAspect.RightMarginText,
#			ThisAspect.HowManyPagesLabel, ThisAspect.PagesAcrossLabel, ThisAspect.PagesAcrossText,
#				ThisAspect.PagesDownLabel, ThisAspect.PagesDownText, ThisAspect.NewPagePerRRCheck,
#			ThisAspect.ZoomLabel, ThisAspect.ZoomText,
			ThisAspect.StyleBox,
#			ThisAspect.StyleLabel,
#			ThisAspect.BlackWhiteCheck, ThisAspect.FontLabel, ThisAspect.FontChoice,
#			ThisAspect.DepictionLabel,
#			ThisAspect.ConnectorsAcrossPagesCheck, ThisAspect.CommentsCheck, ThisAspect.ActionsCheck, ThisAspect.ParkingCheck,
#			ThisAspect.CannotCalculateLabel, ThisAspect.CannotCalculateText, ThisAspect.CombineRRsCheck,
#			ThisAspect.ExpandGatesCheck, ThisAspect.DateLabel, ThisAspect.DateChoice,
			ThisAspect.CancelButton, ThisAspect.GoButton]
		return MyEditPanel.FTFullExportAspect

	def GetPageCountInfo(self, Zoom, ShowHeader, ShowFT, ShowOnlySelected, PageSizeLongAxis, PageSizeShortAxis, Orientation,
		TopMargin, BottomMargin, LeftMargin, RightMargin, PageNumberPos, NewPagePerRR, Font, ConnectorsAcrossPages,
		ShowComments, ShowActions, ShowParking, CannotCalculateText, CombineRRs, ExpandGates, DateKind, **Args):
		# calculate the number of pages required to export the FT
#		# FT: a faulttree.FTForDisplay instance
		# return dict with args: PagesAcrossCount, PagesDownCount (2 x int)
#		assert type(FT).InternalName == 'FTTreeView' # confirming it's the correct class
		assert isinstance(Zoom, int)
		assert isinstance(ShowHeader, bool)
		assert isinstance(ShowFT, bool)
		assert isinstance(ShowOnlySelected, bool)
		assert isinstance(PageSizeLongAxis, (int, float))
		assert isinstance(PageSizeShortAxis, (int, float))
		assert Orientation in ['Portrait', 'Landscape']
		assert isinstance(TopMargin, (int, float))
		assert isinstance(BottomMargin, (int, float))
		assert isinstance(LeftMargin, (int, float))
		assert isinstance(RightMargin, (int, float))
		assert isinstance(PageNumberPos, str)
		assert isinstance(NewPagePerRR, bool)
		assert isinstance(Font, str)
		assert isinstance(ConnectorsAcrossPages, bool)
		assert isinstance(ShowComments, bool)
		assert isinstance(ShowActions, bool)
		assert isinstance(ShowParking, bool)
		assert isinstance(CannotCalculateText, str)
		assert isinstance(CombineRRs, bool)
		assert isinstance(ExpandGates, bool)
		assert DateKind in core_classes.DateChoices
		print('FR372 GetPageCountInfo: not implemented yet')
		return {'PagesAcrossCount': 2, 'PagesDownCount': 3}

	def __init__(self, Proj, PHAObj, DisplDevice, ParentWindow, Fonts, SystemFontNames, **Args):
		# __init__ for class FTFullExportViewport
		faulttree.FTForDisplay.__init__(self, Proj=Proj, PHAObj=PHAObj, DisplDevice=DisplDevice,
			ParentWindow=ParentWindow, **Args)
		self.SystemFontNames = SystemFontNames
		# make aspect object for dialogue
		self.DialogueAspect = self.MakeFTFullExportAspect(MyEditPanel=DisplDevice, Fonts=Fonts,
			SystemFontNames=SystemFontNames, DateChoices=Args['DateChoices'])

	def PrepareFullDisplay(self, XMLTree):
		# display dialogue in our display device to get export parameters from user
		print('FF434 starting PrepareFullDisplay')
		# first, unpack data into the FT
		super(type(self), self).PrepareFullDisplay(XMLTree)
#		self.UndoOnCancel = Args.get('UndoOnCancel', None)
		# build the dialogue: prefill widgets in new aspect and activate it
		self.DialogueAspect.Prefill(self.Proj, FT=self, SystemFontNames=self.SystemFontNames)
		self.DialogueAspect.SetWidgetVisibility()
		self.DialogueAspect.Activate()
		# display aspect's sizer (containing all the visible widgets) in the edit panel
		self.DisplDevice.SetSizer(self.DialogueAspect.MySizer)

	def RenderInDC(self, TargetDC, FullRefresh=True, **Args): pass
		# nothing to do here - this Viewport doesn't draw in a DC - we need this stub to override the superclass's method

# next to do:
# Build "destroy Viewport" function so that we can revert to the previous Viewport.
# Already added self.ViewportToRevertTo attrib to the Viewport object.