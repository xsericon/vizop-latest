# -*- coding: utf-8 -*-
# Module ft_full_report: part of Vizop, (c) 2019 xSeriCon
# produces full export of a fault tree

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import os, os.path, wx # wx provides basic GUI functions

import core_classes, project_display, vizop_misc
from project_display import EditPanelAspectItem


class FTFullExportDialogueAspect(project_display.EditPanelAspectItem):

	def __init__(self, InternalName, ParentFrame, TopLevelFrame):
		project_display.EditPanelAspectItem.__init__(WidgetList=[], InternalName=InternalName,
			ParentFrame=ParentFrame, TopLevelFrame=TopLevelFrame)

	def OnFilenameTextWidget(self, Event): pass # write name back into Proj.FTFullExportFilename
	def OnSelectButton(self, Event): pass
	def OnFileTypeChoice(self, Event): pass # write name back into Proj.FTFullExportFileType
	def OnOverwriteCheck(self, Event): pass
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

	def Prefill(self, Proj, **Args):
		# prefill widget values
		# filename is fetched from last used filename in the project
		self.FilenameText.Widget.ChangeValue(Proj.FTFullExportFilename.strip())
		self.FilenameText.Widget.SelectAll()
		# file type is fetched from project
		RecognisedExtensions = [t.Extension for t in core_classes.ImageFileTypesSupported]
		if Proj.FTFullExportFileType in RecognisedExtensions: ExtensionToSelect = Proj.FTFullExportFileType
		else: ExtensionToSelect = info.DefaultImageFileType
		self.FiletypeChoice.Widget.SetSelection(RecognisedExtensions.index(ExtensionToSelect))
		# set filename status message
		self.UpdateFilenameStatusMessage()

	def UpdateFilenameStatusMessage(self):
		# update filename status message widget text
		FilePathSupplied = self.FilenameText.Widget.GetValue().strip()
		# 1. Filename text box empty, or whitespace only, or contains a directory path
		if (not FilePathSupplied) or os.path.isdir(FilePathSupplied):
			Message = _('Please provide a filename for the image')
		# 2. Path supplied is a writeable, nonexistent filename
		elif vizop_misc.IsWriteableAsNewFile(FilePathSupplied):
			Message = _('Ready to export to new file. Click Go')

def MakeFTFullExportAspect(MyEditPanel, Fonts, SystemFontNames, DateChoices):
	# make Control Panel aspect for PHAModel control
	# fonts (dict): internal font objects such as SmallHeadingFont
	# SystemFontNames (list of str): names of "real" fonts available on the platform
	# DateChoices (list of ChoiceItem): options for date to show in FT
	# make basic attribs needed for the aspect
	MyEditPanel.FTFullExportAspect = FTFullExportDialogueAspect(InternalName='FTFullExport', ParentFrame=MyEditPanel,
		TopLevelFrame=MyEditPanel.TopLevelFrame)
	ThisAspect = MyEditPanel.FTFullExportAspect
	# make widgets
	ThisAspect.HeaderLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
		_('Export full Fault Tree report')),
		ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'], NewRow=True)
	ThisAspect.FilenameLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Filename:')),
		ColLoc=0, ColSpan=1, NewRow=True)
	ThisAspect.FilenameText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE),
		MinSizeY=25, Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnFilenameTextWidget,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
		MinSizeX=200, ColLoc=1, ColSpan=1, DisplayMethod='StaticFromText')
	ThisAspect.SelectButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Select')),
		Handler=ThisAspect.OnSelectButton, Events=[wx.EVT_BUTTON], ColLoc=2, ColSpan=1,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
	ThisAspect.FileTypeLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Type:')),
		ColLoc=3, ColSpan=1)
	ThisAspect.FileTypeChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(100, 25),
		choices=[t.HumanName for t in core_classes.ImageFileTypesSupported]),
		Handler=ThisAspect.OnFileTypeChoice, Events=[wx.EVT_CHOICE], ColLoc=4, ColSpan=1)
	ThisAspect.OverwriteCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Overwrite')),
		Handler=ThisAspect.OnOverwriteCheck, Events=[wx.EVT_CHECKBOX], ColLoc=1, ColSpan=1, NewRow=True)
	ThisAspect.FilenameStatusMessage = UIWidgetItem(wx.StaticText(MyEditPanel, -1, ''),
		ColLoc=1, ColSpan=3, Font=Fonts['BoldFont'], NewRow=True)
	ThisAspect.ExportWhatLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Export what:')),
		ColLoc=0, ColSpan=1, NewRow=True)
	ThisAspect.ShowHeaderCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Header block')),
		Handler=ThisAspect.OnShowHeaderCheck, Events=[wx.EVT_CHECKBOX], ColLoc=2, ColSpan=1)
	ThisAspect.ShowFTCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Fault tree')),
		Handler=ThisAspect.OnShowFTCheck, Events=[wx.EVT_CHECKBOX], ColLoc=3, ColSpan=1)
	ThisAspect.ShowOnlySelectedCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Selected elements only')),
		Handler=ThisAspect.OnShowSelectedCheck, Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1)
	ThisAspect.PageLayoutLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
		_('Page layout')),
		ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'], NewRow=True)
	ThisAspect.PageSizeLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Page size:')),
		ColLoc=0, ColSpan=1, NewRow=True)
	ThisAspect.PageSizeChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(100, 25),
		choices=[t.HumanDescriptor for t in core_classes.PaperSizes]),
		Handler=ThisAspect.OnPageSizeChoice, Events=[wx.EVT_CHOICE], ColLoc=1, ColSpan=1)
	ThisAspect.PortraitRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Portrait'), style=wx.RB_GROUP),
		Handler=ThisAspect.OnPortraitRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=2)
	ThisAspect.LandscapeRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Landscape')),
		Handler=ThisAspect.OnLandscapeRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=3)
	ThisAspect.MarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Margins (mm):')),
		ColLoc=0, ColSpan=1, NewRow=True)
	ThisAspect.TopMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Top')),
		ColLoc=1, ColSpan=1)
	ThisAspect.TopMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
		DisplayMethod='StaticFromText')
	ThisAspect.BottomMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Bottom')),
		ColLoc=1, ColSpan=1, NewRow=True)
	ThisAspect.BottomMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
		DisplayMethod='StaticFromText')
	ThisAspect.LeftMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Left')),
		ColLoc=1, ColSpan=1, NewRow=True)
	ThisAspect.LeftMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
		DisplayMethod='StaticFromText')
	ThisAspect.RightMarginLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Right')),
		ColLoc=1, ColSpan=1, NewRow=True)
	ThisAspect.RightMarginText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnMarginTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100, ColLoc=2, ColSpan=1,
		DisplayMethod='StaticFromText')
	ThisAspect.PageNumberingLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Page numbers at:')),
		ColLoc=3, ColSpan=1)
	ThisAspect.PageNumberTopRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Top'), style=wx.RB_GROUP),
		Handler=ThisAspect.OnPageNumberTopRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
	ThisAspect.PageNumberBottomRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Bottom')),
		Handler=ThisAspect.OnPageNumberBottomRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
	ThisAspect.PageNumberNoneRadio = UIWidgetItem(wx.RadioButton(self, -1, _('None')),
		Handler=ThisAspect.OnPageNumberNoneRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=4)
	ThisAspect.PageNumberLeftRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Left'), style=wx.RB_GROUP),
		Handler=ThisAspect.OnPageNumberLeftRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
	ThisAspect.PageNumberCentreRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Centre')),
		Handler=ThisAspect.OnPageNumberCentreRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
	ThisAspect.PageNumberRightRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Right')),
		Handler=ThisAspect.OnPageNumberRightRadio, Events=[wx.EVT_RADIOBUTTON], ColLoc=5)
	ThisAspect.HowManyPagesLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Fit on how many pages:')),
		ColLoc=0, ColSpan=1, NewRow=True)
	ThisAspect.PagesAcrossLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Across')),
		ColLoc=1, ColSpan=1)
	ThisAspect.PagesAcrossText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnPagesAcrossTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
		ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
	ThisAspect.PagesDownLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Down')),
		ColLoc=3, ColSpan=1)
	ThisAspect.PagesDownText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnPagesDownTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
		ColLoc=4, ColSpan=1, DisplayMethod='StaticFromText')
	ThisAspect.NewPagePerRRCheck = UIWidgetItem(wx.CheckBox(self, -1, _('New page for each risk receptor')),
		Handler=ThisAspect.OnNewPagePerRRCheck, Events=[wx.EVT_CHECKBOX], ColLoc=5, ColSpan=2)
	ThisAspect.ZoomLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Zoom (%)')),
		ColLoc=0, ColSpan=1, NewRow=True)
	ThisAspect.ZoomText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnZoomTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
		ColLoc=1, ColSpan=1, DisplayMethod='StaticFromText')
	ThisAspect.StyleLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
		_('Style')),
		YGap=20, ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'], NewRow=True)
	ThisAspect.BlackWhiteCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Black & white')),
		Handler=ThisAspect.OnBlackWhiteCheck, Events=[wx.EVT_CHECKBOX], ColLoc=1, ColSpan=1)
	ThisAspect.FontLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Font:')),
		ColLoc=1, ColSpan=1)
	ThisAspect.FontChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(200, 25),
		choices=SystemFontNames),
		Handler=ThisAspect.OnFontChoice, Events=[wx.EVT_CHOICE], ColLoc=2, ColSpan=2)
	ThisAspect.DepictionLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
		_('Fault tree depiction')),
		YGap=20, ColLoc=0, ColSpan=2, Font=Fonts['SmallHeadingFont'], NewRow=True)
	ThisAspect.ConnectorsAcrossPagesCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Add connectors across page breaks')),
		Handler=ThisAspect.OnConnectorsAcrossPagesCheck, Events=[wx.EVT_CHECKBOX], ColLoc=0, ColSpan=2, NewRow=True)
	ThisAspect.CommentsCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Show comments')),
		Handler=ThisAspect.OnCommentsCheck, Events=[wx.EVT_CHECKBOX], ColLoc=2, ColSpan=1)
	ThisAspect.ActionsCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Show action items')),
		Handler=ThisAspect.OnActionsCheck, Events=[wx.EVT_CHECKBOX], ColLoc=3, ColSpan=1)
	ThisAspect.ParkingCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Show parking lot items')),
		Handler=ThisAspect.OnParkingCheck, Events=[wx.EVT_CHECKBOX], ColLoc=4, ColSpan=1)
	ThisAspect.CannotCalculateLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1,
		_('For values that cannot\nbe calculated, show')),
		ColLoc=0, ColSpan=2, NewRow=True)
	ThisAspect.CannotCalculateText = UIWidgetItem(wx.TextCtrl(MyEditPanel, -1, style=wx.TE_PROCESS_ENTER), MinSizeY=25,
		Events=[wx.EVT_TEXT_ENTER], Handler=ThisAspect.OnCannotCalculateTextCtrl,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, MinSizeX=100,
		ColLoc=2, ColSpan=1, DisplayMethod='StaticFromText')
	ThisAspect.CombineRRsCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Combine FTs for risk\nreceptors where possible')),
		Handler=ThisAspect.OnCombineRRsCheck, Events=[wx.EVT_CHECKBOX], ColLoc=3, ColSpan=2)
	ThisAspect.ExpandGatesCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Expand logic gates')),
		Handler=ThisAspect.OnExpandGatesCheck, Events=[wx.EVT_CHECKBOX], ColLoc=0, ColSpan=2, NewRow=True)
	ThisAspect.DateLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Show date:')),
		ColLoc=4, ColSpan=1)
	ThisAspect.DateChoice = UIWidgetItem(wx.Choice(MyEditPanel, -1, size=(100, 25),
		choices=[c.HumanName for c in DateChoices]),
		Handler=ThisAspect.OnDateChoice, Events=[wx.EVT_CHOICE], ColLoc=5, ColSpan=1)
	ThisAspect.CancelButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Cancel')),
		Handler=ThisAspect.OnCancelButton, Events=[wx.EVT_BUTTON], ColLoc=0, ColSpan=1, NewRow=True,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
	ThisAspect.GoButton = UIWidgetItem(wx.Button(MyEditPanel, -1, _('Go')),
		Handler=ThisAspect.OnGoButton, Events=[wx.EVT_BUTTON], ColLoc=2, ColSpan=1,
		Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)

	# make list of widgets in this aspect
	ThisAspect.WidgetList = [ThisAspect.HeaderLabel,
		ThisAspect.FilenameLabel, ThisAspect.FilenameText, ThisAspect.SelectButton, ThisAspect.FileTypeLabel,
			ThisAspect.FileTypeChoice,
		ThisAspect.OverwriteCheck,
		ThisAspect.FilenameStatusMessage,
		ThisAspect.ExportWhatLabel, ThisAspect.ShowHeaderCheck, ThisAspect.ShowFTCheck, ThisAspect.ShowOnlySelectedCheck,
		ThisAspect.PageLayoutLabel,
		ThisAspect.PageSizeLabel, ThisAspect.PageSizeChoice, ThisAspect.PortraitRadio, ThisAspect.LandscapeRadio,
		ThisAspect.MarginLabel, ThisAspect.TopMarginLabel, ThisAspect.TopMarginText, ThisAspect.PageNumberingLabel,
			ThisAspect.PageNumberTopRadio, ThisAspect.PageNumberLeftRadio,
		ThisAspect.BottomMarginLabel, ThisAspect.BottomMarginText, ThisAspect.PageNumberBottomRadio,
			ThisAspect.PageNumberCentreRadio,
		ThisAspect.LeftMarginLabel, ThisAspect.LeftMarginText, ThisAspect.PageNumberNoneRadio,
			ThisAspect.PageNumberRightRadio,
		ThisAspect.RightMarginLabel, ThisAspect.RightMarginText,
		ThisAspect.HowManyPagesLabel, ThisAspect.PagesAcrossLabel, ThisAspect.PagesAcrossText,
			ThisAspect.PagesDownLabel, ThisAspect.PagesDownText, ThisAspect.NewPagePerRRCheck,
		ThisAspect.ZoomLabel, ThisAspect.ZoomText,
		ThisAspect.StyleLabel,
		ThisAspect.BlackWhiteCheck, ThisAspect.FontLabel, ThisAspect.FontChoice,
		ThisAspect.DepictionLabel,
		ThisAspect.ConnectorsAcrossPagesCheck, ThisAspect.CommentsCheck, ThisAspect.ActionsCheck, ThisAspect.ParkingCheck,
		ThisAspect.CannotCalculateLabel, ThisAspect.CannotCalculateText, ThisAspect.CombineRRsCheck,
		ThisAspect.ExpandGatesCheck, ThisAspect.DateLabel, ThisAspect.DateChoice,
		ThisAspect.CancelButton, ThisAspect.GoButton]