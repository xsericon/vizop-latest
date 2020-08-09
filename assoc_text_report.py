# -*- coding: utf-8 -*-
# Module assoc_text_report: part of Vizop, (c) 2020 xSeriCon
# Codes the dialogue and export of a report of action items and parking lot items
import os, os.path, wx, platform # wx provides basic GUI functions

import display_utilities, project_display

class AssocTextReportViewport(display_utilities.ViewportBaseClass):
	# defines a viewport that produces an export file containing a list of associated texts (action items or parking
	# lot items), and encodes a
	# dialogue to get parameters from the user to control the export (e.g. which items to include, fonts)
	InternalName = 'ATReport' # unique per class, used in messaging
	HumanName = _('Action item/Parking lot report')
	PreferredKbdShortcut = 'R'
	NewPHAObjRequired = None # which datacore PHA object class this Viewport spawns on creation.
		# Should be None if the model shouldn't create a PHA object
	# VizopTalks message when a new FT is created. NB don't set Priority here, as it is overridden in DoNewViewportCommand()
	NewViewportVizopTalksArgs = {'Title': 'Action item/Parking lot report',
		'MainText': 'Enter the settings you require, then click Go'}
	NewViewportVizopTalksTips = []
	InitialEditPanelMode = 'Widgets'

	class ATReportDialogueAspect(project_display.EditPanelAspectItem):

		def __init__(self, InternalName, ParentFrame, TopLevelFrame):
			project_display.EditPanelAspectItem.__init__(self, WidgetList=[], InternalName=InternalName,
				ParentFrame=ParentFrame, TopLevelFrame=TopLevelFrame, PrefillMethod=self.Prefill,
				SetWidgetVisibilityMethod=self.SetWidgetVisibility)
			self.Overwrite = False # whether to overwrite any existing file when exporting

	def MakeATReportDialogueAspect(self, MyEditPanel, Fonts, SystemFontNames, DateChoices):
		# make edit panel aspect for defining associated text report
		# fonts (dict): internal font objects such as SmallHeadingFont
		# SystemFontNames (list of str): names of "real" fonts available on the platform
		# DateChoices (list of ChoiceItem): options for date to show in report (not currently used)
		# return the aspect
		# make basic attribs needed for the aspect
		MyEditPanel.ATReportDialogueAspect = AssocTextReportViewport.ATReportDialogueAspect(InternalName='ATReport',
			ParentFrame=MyEditPanel, TopLevelFrame=MyEditPanel.TopLevelFrame)
		ThisAspect = MyEditPanel.ATReportDialogueAspect
		ThisAspect.TextWidgets = []
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
			_('Export action items report')),
			Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND, GapY=10,
			ColLoc=0, ColSpan=10, Font=Fonts['BigHeadingFont'], NewRow=True)
		ThisAspect.FileBox = UIWidgetItem(FileBoxSizer, HideMethod=lambda : FileBoxSizer.ShowItems(False),
			ShowMethod=lambda : FileBoxSizer.ShowItems(True), ColLoc=0, ColSpan=5, NewRow=True,
			SetFontMethod=lambda f: FileBoxSizer.GetStaticBox().SetFont, Font=Fonts['SmallHeadingFont'])
		ThisAspect.FilenameLabel = UIWidgetItem(wx.StaticText(MyEditPanel, -1, _('Filename stub:'),
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

	class ATReportDialogueAspect(project_display.EditPanelAspectItem):

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
				(SomeATsAreSelected or self.ShowAllATsCheck.Widget.IsChecked())
			self.GoButton.Widget.Enable(FilenameUsable and ContentIsNonzero)
			return FilenameStatus

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
				DialogueTitle=_('Select filename  for action item/parking lot export'), DefaultDir=DefaultDirectory,
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



