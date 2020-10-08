# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright xSeriCon, 2020
"""Implements the Welcome screen"""

import gettext, wx
import os.path

#install _() into Python's global namespace so that we can use gettext to
#translate the entire application without having to initialise it in every module
import info
from vizop_misc import get_sys_runtime_files_dir
gettext.install(info.PROG_SHORT_NAME, os.path.join(get_sys_runtime_files_dir(),'locale'))

# vizop modules required
import art, undo, projects
from vizop_misc import RegisterKeyPressHandler, ClearKeyPressRegister, IsReadableFile, IsWritableLocation,\
	OnAboutRequest, GetFilenameForSave, EnsureFilenameHasExtension
from settings import SettingsManager

# other modules required
# from locale import getdefaultlocale # used to obtain current locale, hence language settings. Beazley p286
from getpass import getuser # gets currently logged in username (Unix, Windows only)
from platform import system # gets name of OS; see Beazley p329

KeyPressHash = [] # list of tuples: (keystroke code, handling routines when those keystrokes are detected,
# dict of args to supply to handler)

def InitializeVizop():
	"""Runs all the initialisation tasks needed for Vizop startup.
	Tasks like loading state information, setting up callbacks for config
	changes etc. should all go in this function.
	"""  
#	UserProfileFilename = {'Linux': '%s/.vizop/profile', 'Windows': '%s\\AppData\\Local\\Vizop\\profile.config',
#						   'Darwin': '%s./Vizop/profile'}.get(system(), '') % UserHomeDirectory
#	try:
#		# where to find datafiles needed at runtime
#		RuntimeFileDirectory = {'Linux': '%s/Documents/Computing/Vizop/Runtime',
#							'Windows': '%s\\AppData\\Local\\Vizop\\Runtime',
#							'Darwin': '%s/.vizop/Runtime'}[system()] % UserHomeDirectory
#	except KeyError:
#		RuntimeFileDirectory = ''
#		print("Vizop: WARNING: Unknown platform - don't know where to find Runtime files (problem code: ST62)")
	#in case the config files have been changed since the last program exit, update the
	#size of the recent projects list

	#register callback functions to deal with config changes during program execution
	sm = SettingsManager()
	sm.register_config_change_callback('RecentProjectsListMaxSize', ResizeRecentProjectsList)
	# set UserHomeDir to user's home directory, e.g. /Users/peter
	sm.set_value('UserHomeDir', os.path.expanduser('~' + getuser())) # Beazley p283
	
	#add our art provider to the stack of providers. We add it to the bottom, so that
	#default icons will be used in preference to our own. It also means that GetSizeHint()
	#will query a built-in provider rather than ours
#	wx.ArtProvider.Insert(art.ArtProvider())
	wx.ArtProvider.PushBack(art.ArtProvider())


def GetAvailProjTemplates():
	"""Returns a list of the project templates available (pathnames as str).
	
	Returns a list of absolute paths to the template files. Only files that are
	readable are returned. Currently, no check that the files are actually Vizop project templates.
	"""
	templates_dir = os.path.join(get_sys_runtime_files_dir(), info.ProjTemplateFolderTail)

	# get a list of complete paths to files in the templates dir
	if os.path.isdir(templates_dir) and os.access(templates_dir, os.R_OK):
		# get list of all files in the templates directory.
		# Assumes all files are template files (FIXME), but filters out dot files (beginning with .).
		flist = [os.path.join(templates_dir,f) for f in os.listdir(templates_dir) if not f.startswith('.')]
	else:
		flist = []
	# only return readable files in the list
	return [f for f in flist if IsReadableFile(f)]


def ResizeRecentProjectsList():
	"""
	Updates the length of the recent projects list
	to the size specified by the 'RecentProjectsListMaxSize' config.
	"""
	sm = SettingsManager()
	new_size = sm.get_config('RecentProjectsListMaxSize')
	
	try:
		old_list = sm.get_config('RecentProjectsList')
	except KeyError:
		old_list = []
	sm.set_value('RecentProjectsList', old_list[:new_size])


class NoProjectOpenFrame(wx.Frame):
	# Define the welcome window that appears whenever no project is open, including at launch of vizop

	def __init__(self, parent, ID, title, ColourScheme):
		global KeyPressHash
		self.ColourScheme = ColourScheme
		wx.Frame.__init__(self, parent, wx.ID_ANY, title, size=(600, 400))
		self.settings_manager = SettingsManager()
		self.Centre() # places window in centre of screen, Rappin p235. TODO need to place in centre of primary display
		
		# set up sizers to contain the objects on the welcome frame
		self.sizer1 = wx.BoxSizer(wx.HORIZONTAL)
		
		# set up logo
		self.sizer1.Add(LogoPanel(self, self.ColourScheme), 1, wx.ALIGN_LEFT | wx.EXPAND)
		# set up button area
		# set correct shortcut key text for 'Exit' key
		ExitShortcutKey = {'Linux': 'Ctrl + Q', 'Windows': 'Ctrl + Q', 'Darwin': info.CommandSymbol + 'Q'}.get(system(),
			'Ctrl + Q')
		# info per button: (text in button, x and y location, handling routine, keyboard shortcut, internal name)
		ButtonInfo = [(_('Open recent project | R'), 40, 40, self.OnOpenRecentButton, ord('r'), 'Recent'),
					  (_('Open existing project | O'), 40, 90, self.OnOpenExistingButton, ord('o'), 'Existing'),
					  (_('Start new project | N'), 40, 140, self.OnNewButton, ord('n'), 'New'),
					  (_('Join a project collaboration | J'), 40, 190, self.OnJoinCollaborationButton, ord('j'), 'Join'),
					  (_('About Vizop | T'), 40, 240, self.OnAbout, ord('t'), 'About'),
					  (_('Exit | ' + ExitShortcutKey), 40, 290, self.OnExitButton, [wx.WXK_CONTROL, ord('q')], 'Exit') ]

		# get the current recent project list, or create a new one if it doesn't exist
		try:
			RecentProjList = self.settings_manager.get_config('RecentProjectsList')
		except KeyError:
			RecentProjList = []
		# get filename of all available project templates
		self.ProjTemplates = GetAvailProjTemplates()

		panel3 = wx.Panel(self) # panel to hold the buttons
		panel3.SetBackgroundColour(ColourScheme.BackBright)
		KeyPressHash = ClearKeyPressRegister(KeyPressHash)
		for (ButtonText, x, y, ButtonHandler, Key, Name) in ButtonInfo:
			# set up each button in the welcome frame
			RegisterKey = True # whether to register the keypress 
			b = wx.Button(panel3, -1, ButtonText, pos=(x, y), size=(220, 40))
			b.Bind(wx.EVT_BUTTON, ButtonHandler)
			b.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL))
			b.SetForegroundColour('navy')
			if (Name == 'Recent') and not RecentProjList:
				b.Disable() # disable Recent projects button if none available
				RegisterKey = False
			if (Name == 'New') and not self.ProjTemplates:
				b.Disable() # disable New project button if no templates available
				RegisterKey = False
			if RegisterKey: KeyPressHash = RegisterKeyPressHandler(KeyPressHash, Key, ButtonHandler)
		
		panel3.SetFocus() # enable button bar to handle Tab, Space, Enter keys
		self.sizer1.Add(panel3, 1, wx.EXPAND)
		self.sizer1.SetItemMinSize(1, (300, 400))

		self.Bind(wx.EVT_IDLE, self.OnIdle)
		# Lay out sizers
		self.SetMinSize((600,400))
		self.SetSizer(self.sizer1) # assigns sizer1 to fill Welcome frame
		self.SetAutoLayout(True)
		self.sizer1.FitInside(self)
		self.Show(True)


	def OnIdle(self, Event): # during idle time, handle keystrokes for shortcuts. This procedure is repeated in module datacore
		global KeyPressHash
		# initialise storage object used to remember keys pressed last time, for chord detection in correct order
		if not hasattr(self, 'PrevChordKeys'): self.PrevChordKeys = []
		KeysDownThisTime = [] # prepare list of key codes that are 'hit' and match any keys in KeyPressHash
		KeyPressIndexHit = None # which item (index in KeyPressHash) is to be invoked
		for (HashIndex, (KeyStroke, Handler, Args)) in enumerate(KeyPressHash): # check each keystroke registered in KeyPressHash
			if type(KeyStroke) is int:
				if wx.GetKeyState(KeyStroke):
					KeysDownThisTime.append(KeyStroke)
					if not (KeyStroke in self.PrevChordKeys):
						KeyPressIndexHit = HashIndex # KeyStroke has been detected this time, but not last time
			elif type(KeyStroke) is list: # key chord handling
				ChordFulfilled = True
				for k in KeyStroke: # check each key in KeyStroke
					if wx.GetKeyState(k): KeysDownThisTime.append(k)
					else: ChordFulfilled = False
				# check that (1) all keys in KeyStroke are pressed, AND
				# (2) not all of them were pressed last time (i.e. >=1 of them is newly pressed)
				if ChordFulfilled and not set(KeyStroke).issubset(set(self.PrevChordKeys)):
					KeyPressIndexHit = HashIndex # invoke handler if keystroke detected
		self.PrevChordKeys = KeysDownThisTime # store currently-pressed keys for comparison next time
		# Must do the line above BEFORE invoking Handler - else KeyStrokes newly defined in Handler may falsely activate
		if (KeyPressIndexHit is not None):
			(KeyStroke, Handler, Args) = KeyPressHash[KeyPressIndexHit]
			Handler(**Args) # invoke handler
	
	def WrapUpAfterOpeningProjects(self, ProjFiles, TemplateFiles, RequestToQuit=False, SaveOnFly=True):
		# after successful opening of project file(s) from welcome frame, perform tidying up
		# ProjFiles is list of paths of valid project files to be opened or created (str)
		# TemplateFiles is list of paths of valid template files to be used to create new projects, using the filepaths
		# in ProjFiles (str)
		# RequestToQuit (bool): whether vizop should quit now, on user's request
		# SaveOnFly (bool): whether new project should be saved on the fly
		# set return values
		NoProjectOpenFrameData.Data = {'ProjectFilesToOpen': ProjFiles, 'TemplateFilesToSpawnFrom': TemplateFiles,
						   'RequestToQuit': RequestToQuit, 'SaveOnFly': SaveOnFly}
		self.Destroy() # destroy welcome frame

	def WrapUpAfterJoinCollaborationRequest(self):
		# perform tidying up and exit welcome frame after receiving request to collaborate on remote project
		# similar to WrapUpAfterOpeningProjects() except there's no open project to handle
		NoProjectOpenFrameData.Data = {'ProjectFilesToOpen': [], 'TemplateFilesToSpawnFrom': [],
			'RequestToQuit': False, 'SaveOnFly': False, 'OpenCollaboration': True}
		self.Destroy() # destroy welcome frame

	def DisableKeypresses(self): # temporarily suppress all keypress handlers, to avoid inadvertent behaviour
		global KeyPressHash
		self.OldKPR = KeyPressHash[:]
		KeyPressHash = ClearKeyPressRegister(KeyPressHash) # to avoid inadvertent behaviour from key presses


	def ReinstateKeypresses(self): # reinstate keyboard shortcuts
		global KeyPressHash
		KeyPressHash = self.OldKPR

	def HandleNewFileRequest(self, Filenames, NewFilenames=[], NewProjects=False, SaveOnFly=True):
		# Check NewFilenames can be opened.
		# Check whether Filenames (list of paths) contains openable project templates.
		# NewFilename: full paths of files to create for new project
		# NewProjects (bool): whether the Filenames are templates to use for creation of new projects (always True)
		# SaveOnFly (bool): if creating new project, whether work should be saved on the fly
		# If any openable projects, call WrapUpAfterOpeningProjects() to close Welcome Frame and send data to datacore.
		# Return values: OpenableProjFiles (list of paths that contain valid and openable projects)
		#       ProjOpenData (list of dict of data for each file, returned from projects.TestProjectsOpenable)
		ProjOpenData = projects.TestProjectsOpenable(Filenames, ReadOnly=False) # find out if the projects can be opened
		# expected return value (ProjOpenData): a list of dict, one for each project file in Filenames
		# dict keys are: Openable (bool), Comment (str) - explaining why project is not openable (for user feedback)
		# make list of openable/creatable project files
		OpenableProjFiles = [Filenames[i] for i in range(len(Filenames))
							 if ProjOpenData[i]['Openable']
							 if (IsWritableLocation(os.path.dirname(NewFilenames[i])) or not SaveOnFly)]
		# Note, the writability check is duplicated in projects.SaveEntireProject() and might be redundant here
		if OpenableProjFiles: # can any of the selected project files be opened?
			if NewProjects: # tidy up and exit Welcome Frame
				self.WrapUpAfterOpeningProjects(ProjFiles=NewFilenames, TemplateFiles=OpenableProjFiles,
												SaveOnFly=SaveOnFly)
			else:
				self.WrapUpAfterOpeningProjects(ProjFiles=OpenableProjFiles, TemplateFiles=[])
		return OpenableProjFiles, ProjOpenData

	def HandleOpenFileRequest(self, Filenames, NewFilenames=[], NewProjects=False, SaveOnFly=True):
		# Check whether Filenames (list of existing paths) contains openable projects.
		# NewFilename: full paths of files to create for new project (redundant, now using HandleNewFileRequest() )
		# NewProjects (bool): whether the Filenames are templates to use for creation of new projects - always False
		# SaveOnFly (bool): if creating new project, whether work should be saved on the fly
		# If any openable projects, call WrapUpAfterOpeningProjects() to close Welcome Frame and send data to datacore.
		# Return values: OpenableProjFiles (list of paths that contain valid and openable projects)
		#       ProjOpenData (list of dict of data for each file, returned from projects.TestProjectsOpenable)
		ProjOpenData = projects.TestProjectsOpenable(Filenames, ReadOnly=False) # find out if the projects can be opened
		# expected return value (ProjOpenData): a list of dict, one for each project file in Filenames
		# dict keys are: Openable (bool), Comment (str) - explaining why project is not openable (for user feedback)
		# make list of openable/creatable project files
		OpenableProjFiles = [Filenames[i] for i in range(len(Filenames))
							 if ProjOpenData[i]['Openable']
							 if (IsWritableLocation(os.path.dirname(Filenames[i])) or not SaveOnFly)]
		# Note, the writability check is duplicated in projects.SaveEntireProject() and might be redundant here
		if OpenableProjFiles: # can any of the selected project files be opened?
			if NewProjects: # tidy up and exit Welcome Frame
				self.WrapUpAfterOpeningProjects(ProjFiles=NewFilenames, TemplateFiles=OpenableProjFiles,
												SaveOnFly=SaveOnFly)
			else:
				self.WrapUpAfterOpeningProjects(ProjFiles=OpenableProjFiles, TemplateFiles=[])
		return OpenableProjFiles, ProjOpenData

	def OnOpenRecentButton(self, event=None): # handle user request to Open Recent Project
		self.DisableKeypresses()
		OpenSuccess = False # whether valid project files are identified for opening
		# read recent projects list from cache file
		try:
			recent_projects_list = self.settings_manager.get_config('RecentProjectsList')
		except KeyError:
			#recent_projects_list does not exist - so create it
			recent_projects_list = []
			self.settings_manager.set_value('RecentProjectsList', recent_projects_list)

		RPDisplayList = [] # build list of recent projects in display-friendly format
		for ProjFilename in reversed(recent_projects_list): 
			RPDisplayList.append(_('%s in %s') % (os.path.basename(ProjFilename), os.path.dirname(ProjFilename)))
		DialogueBox = wx.MultiChoiceDialog(self, _('Which project(s) would you like to open?'),
										   _('Choose a vizop project file to open'), RPDisplayList) # set up standard selection dialogue
		if DialogueBox.ShowModal() == wx.ID_OK: # user clicked OK
			FilenamesSelected = [] # make list of filenames selected
			for index in DialogueBox.GetSelections(): FilenamesSelected.append(recent_projects_list[index])
			OpenableProjFiles, ProjOpenData = self.HandleOpenFileRequest(FilenamesSelected)
			OpenSuccess = bool(OpenableProjFiles)
		# allow user to continue working in Welcome Frame if no projects can be opened. TODO give user feedback
		if not OpenSuccess:
			self.ReinstateKeypresses()


	def OnOpenExistingButton(self, Event=None):
		# handle click on Open Existing button
		self.DisableKeypresses()
		FilenamesSelected = projects.GetProjectFilenamesToOpen(self)
		if FilenamesSelected: # did user select any files to open?
			OpenableProjFiles, ProjOpenData = self.HandleOpenFileRequest(FilenamesSelected)
			OpenSuccess = bool(OpenableProjFiles) # using OpenSuccess for consistency with other handlers
		else: OpenSuccess = False
		# allow user to continue working in Welcome Frame if no projects can be opened. TODO give user feedback
		if not OpenSuccess:
			self.ReinstateKeypresses()

	def OnNewButton(self, event=None):
		# handle click on New project button
		self.DisableKeypresses()
		# get project filename extension
		SettingsMgr = SettingsManager()
		ProjFileExt = SettingsMgr.get_config('ProjFileExt')
		OpenSuccess = False # whether valid project files are identified for opening
		# let the user select a template
		DialogueBox = SelectTemplateDialogue(parent=self, title=_('Vizop: Choose a template'),
											 ColourScheme=self.ColourScheme, ProjTemplates=self.ProjTemplates)
		if DialogueBox.ShowModal() == wx.ID_OK:
			# get the template file and project filename to create from the user
			TargetTemplateFile, ProjFilename, SaveOnFly = DialogueBox.ReturnData
			# force the project filename to have expected extension
			ProjFilename = EnsureFilenameHasExtension(ProjFilename, ProjFileExt)
			CreatableProjFiles, ProjOpenData = self.HandleNewFileRequest(
				[TargetTemplateFile], NewFilenames=[ProjFilename], NewProjects=True, SaveOnFly=SaveOnFly)
			OpenSuccess = bool(CreatableProjFiles)
		# allow user to continue working in Welcome Frame if no projects can be created. TODO give user feedback
		if not OpenSuccess:
			self.ReinstateKeypresses()

	def OnJoinCollaborationButton(self, Event=None): # handle user request to join collaboration%%%
		DialogueBox = JoinCollaborationDialogue(parent=self, title=_('Vizop: Join a collaboration'),
			ColourScheme=self.ColourScheme)
		if DialogueBox.ShowModal() == wx.ID_OK: pass

	def OnAbout(self, event=None):
		OnAboutRequest(Parent=self, event=None)

	def OnExitButton(self, event=None):
		self.DisableKeypresses()
		NoProjectOpenFrameData.Data = {'RequestToQuit': True} # store return data used by 'heart' module
		self.Destroy()

class NoProjectOpenFramePersistent(object):
	# a persistent object used for returning data from NoProjectOpenFrame after it is Destroy()ed.

	def __init__(self):
		object.__init__(self)

NoProjectOpenFrameData = NoProjectOpenFramePersistent() # make an instance of the data return object


class LogoPanel(wx.Panel):
	"""Holds the logo and welcome message.
	"""
	def __init__(self, Parent, ColourScheme):
		wx.Panel.__init__(self, Parent)
		sizer = wx.GridSizer(rows=2, cols=1, vgap=0, hgap=0)
		art_provider = art.ArtProvider()
	
		logo = art_provider.get_image('vizopLogo', (200, 200), conserve_aspect_ratio=True)
		logo_bmp = wx.StaticBitmap(self, -1, wx.Bitmap(img=logo))
		sizer.Add(logo_bmp, 1, wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_TOP | wx.TOP, border=20)
		
		self.welcome_message = wx.StaticText(self, -1, _('Next generation PHA starts here'),
			style=wx.ALIGN_CENTER_HORIZONTAL | wx.ALIGN_TOP)
		self.welcome_message.SetFont(wx.Font(16, wx.SWISS, wx.NORMAL, wx.NORMAL))
		self.welcome_message.Wrap(logo_bmp.GetSize()[0])
		
		sizer.Add(self.welcome_message,1, wx.ALIGN_CENTER)
		self.apply_colour_scheme(ColourScheme)
		
		self.SetSizer(sizer)
		self.SetAutoLayout(True)
		sizer.FitInside(self)
	
	
	def apply_colour_scheme(self, colour_scheme):
		"""Changes the colours used in the panel to those in the specified colour scheme.
		"""
		self.SetBackgroundColour(colour_scheme.BackMid)
		#TODO - this should get its colour from the colour_scheme
		self.welcome_message.SetForegroundColour('red')


class SelectTemplateDialogue(wx.Dialog):
	# Define the template selection dialogue box

	def __init__(self, parent, title, ColourScheme, ProjTemplates):
		# ProjTemplates: list of path names of project template files (str)
		global KeyPressHash
		wx.Dialog.__init__(self, parent, wx.ID_ANY, title, size=(600, 400))
		# set dialogue box position based on position of parent window
		self.SetPosition(parent.GetPosition() + (20,20))
		# set up sizers to contain the objects in the dialogue box
		self.sizer2=wx.BoxSizer(wx.VERTICAL)
		self.sizer1=wx.BoxSizer(wx.HORIZONTAL)

		# Set up prompt message
		panel1 = wx.Panel(self)
		panel1.SetBackgroundColour(ColourScheme.BackBright)
		PromptTextWidget = wx.StaticText(panel1, -1, _('Which template would you like for your new project?'))
		PTWSizeY = PromptTextWidget.GetSize().GetHeight()
		PromptTextWidget.SetPosition( (20, 0.5 * PTWSizeY) ) # vertically centre text in panel1 with 0.5x border
		panel1.SetMinSize( (20, 2 * PTWSizeY) )
		self.sizer2.Add(panel1, 0, wx.EXPAND) # prompt msg panel expandable, 10px border all around
#		self.sizer2.SetItemMinSize(0, (600,80))

		# Set up listbox with choice of templates (Rappin p217)
		panel2 = wx.Panel(self)
		panel2.SetBackgroundColour(ColourScheme.BackMid)

		# load the list of available templates
		# FIXME - what if the template list is empty?
		self.avail_templates = {}
		for template_path in ProjTemplates:
			self.avail_templates[os.path.basename(template_path)] = template_path 
		self.tc = wx.ListBox(panel2, -1, choices=list(self.avail_templates.keys()), pos=(20,20), size=(200,200), style=wx.LB_SINGLE)
		
		self.tc.SetSelection(0) # preselect default template
#		self.tc.Bind(wx.EVT_LISTBOX, OnChoiceBox) # eventually this will open a preview of the clicked template
		self.sizer2.Add(panel2)
		self.sizer2.SetItemMinSize(1, (600,240))

		# Set up user's response buttons
		KeyPressHash = ClearKeyPressRegister(KeyPressHash)
		panel3 = wx.Panel(self)
		panel3.SetBackgroundColour(ColourScheme.BackBright)
		# todo: pay attention to whether user is authorised to edit project $AUTH
		ButtonInfo = [(_('Make new project\nand store my work | S'), 15, 5, 180, 70, self.OnStoreButton, ord('s'), 'Store'),
					  (_('Let me try it out (I may\nstore the project later) | T'), 210, 5, 220, 70, self.OnTrialButton, ord('t'), 'Try'),
					  (_('Cancel | Esc'), 445, 5, 140, 70, self.OnCancelButton, wx.WXK_ESCAPE, 'Cancel') ]
			# info per button: (text in button, x and y location, x and y size, handling routine, keyboard shortcut, internal name)		
		for (ButtonText, x, y, SizeX, SizeY, ButtonHandler, Key, Name) in ButtonInfo:
			RegisterKey = True # whether to register the keypress
			b = wx.Button(panel3, -1, ButtonText, pos=(x, y), size=(SizeX, SizeY))
			b.Bind(wx.EVT_BUTTON, ButtonHandler)
			b.SetFont(wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL))
			b.SetForegroundColour('navy')
			if (Name == 'Recent') and not recent_proj_list: 
				b.Disable() # disable Recent projects button if none available
				RegisterKey = False
			elif (Name == 'New') and not ProjTemplates:
				b.Disable() # disable New project button if no templates available
				RegisterKey = False
			if RegisterKey: KeyPressHash = RegisterKeyPressHandler(KeyPressHash, Key, ButtonHandler)
		self.sizer2.Add(panel3)
		self.sizer2.SetItemMinSize(2, (600,80))

		# Lay out sizers
		self.SetSizer(self.sizer2) # assigns sizer2 to fill dialogue box
		self.SetAutoLayout(True)
		self.sizer2.FitInside(self)


	def DisableKeypresses(self): # temporarily suppress all keypress handlers, to avoid inadvertent behaviour
		global KeyPressHash
		self.OldKPR = KeyPressHash[:]
		KeyPressHash = ClearKeyPressRegister(KeyPressHash) # to avoid inadvertent behaviour from key presses


	def ReinstateKeypresses(self): # reinstate keyboard shortcuts
		global KeyPressHash
		KeyPressHash = self.OldKPR


	def OnTrialButton(self, event=None):
		# handle 'Let me try out template' request
		# retrieve the target template filename from the dropdown box
		self.DisableKeypresses()
		TargetTemplateStub = self.tc.GetStringSelection()
		TargetTemplateFile = self.avail_templates[TargetTemplateStub]
		if IsReadableFile(TargetTemplateFile):
			# set dialogue box's return data: TargetTemplateFile (str), ProjFilename (str), SaveOnFly (bool)
			self.ReturnData = (TargetTemplateFile, '', False)
			# close the template selection dialogue box
			self.EndModal(wx.ID_OK)
		else: # there was a problem with the template file; pop up a message
			i = wx.MessageBox(_('Vizop says sorry'), (_("Template %s can't be opened") % TargetTemplateStub), style=wx.OK)


	def OnStoreButton(self, event=None):
		# handle 'Start new file from template and store my work' request
		global KeyPressHash
		self.DisableKeypresses()
		# retrieve the target template filename from the dropdown box
		SettingsMgr = SettingsManager()
		TargetTemplateStub = self.tc.GetStringSelection()
		TargetTemplateFile = self.avail_templates[TargetTemplateStub]
		if IsReadableFile(TargetTemplateFile):
			# get a default directory in which to store the project
			try:
				DefDir = SettingsMgr.get_config('NewProjDir')
			except KeyError:
				# No default dir found in settings: store one
				DefDir = SettingsMgr.get_value('UserHomeDir')
				SettingsMgr.set_value('NewProjDir', DefDir)
			# get default extension for project files
			ProjFileExt = SettingsMgr.get_config('ProjFileExt')
			# get a filename to store the project
			(StoreLocOK, ProjFilename) = GetFilenameForSave(DialogueParentFrame=self,
				DialogueTitle=_('Vizop needs a filename for your new project'),
				DefaultDir=DefDir, DefaultFile='', Wildcard='', DefaultExtension=ProjFileExt)
			if StoreLocOK:
				# set dialogue box's return data: TargetTemplateFile (str), ProjFilename (str), SaveOnFly (bool)
				self.ReturnData = (TargetTemplateFile, ProjFilename, True)
				SettingsMgr.set_value('NewProjDir', os.path.dirname(ProjFilename))
				# close the template selection dialogue box
				self.EndModal(wx.ID_OK)
			else: # we're returning to template selection dialogue: reinstate keyboard shortcuts
				self.ReinstateKeypresses()
		else: # there was a problem with the template file; pop up a message
			i = wx.MessageBox(_('Vizop says sorry'), (_("Template %s can't be opened") % TargetTemplateStub), style=wx.OK)
		

	def OnCancelButton(self, event=None):
		# handle Cancel request in template selection dialogue
		global KeyPressHash
		KeyPressHash = ClearKeyPressRegister(KeyPressHash)
		self.EndModal(wx.ID_CANCEL)

class JoinCollaborationDialogue(wx.Dialog):
	# Define the "join collaboration" dialogue box

	def __init__(self, parent, title, ColourScheme):
		global KeyPressHash
		KeyPressHash = ClearKeyPressRegister(KeyPressHash) # prevent inadvertent activation of shortcuts on main welcome panel
		wx.Dialog.__init__(self, parent, wx.ID_ANY, title, size=(600, 400))
		# set dialogue box position based on position of parent window
		self.SetPosition(parent.GetPosition() + (20,20))
		# make a panel for the box (so that we can set background colour)
		MyPanel = wx.Panel(self)
		MyPanel.SetBackgroundColour(ColourScheme.BackBright)
		# set up sizer to contain the objects in the dialogue box
		self.MainSizer = wx.GridBagSizer(vgap=0, hgap=0)
		# make widgets to appear in dialogue
		NameLabel = wx.StaticText(self, -1, _('Please enter your name:'))
		self.NameTextCtrl = wx.TextCtrl(self, -1)
		AskLabel = wx.StaticText(self, -1, _('Ask the project editor for a collaboration code'))
		CodeLabel = wx.StaticText(self, -1, _('Enter the code here:'))
		self.CodeTextCtrl = wx.TextCtrl(self, -1)
		self.CancelButton = wx.Button(self, -1, 'Cancel')
		self.GoButton = wx.Button(self, -1, 'Go')
		self.MessageLabel = wx.StaticText(self, -1, '')
		# put widgets in sizer
		for w, Row, ColStart, ColSpan, LeftMargin in [ (NameLabel, 0, 0, 1, 10), (self.NameTextCtrl, 0, 1, 2, 0),
			(AskLabel, 1, 0, 3, 10), (CodeLabel, 2, 0, 1, 10), (self.CodeTextCtrl, 2, 1, 2, 0), (self.CancelButton, 3, 1, 1, 0),
										   (self.GoButton, 3, 2, 1, 0), (self.MessageLabel, 4, 0, 3, 10)]:
			self.MainSizer.Add(w, pos=(Row, ColStart),
				span=(1, ColSpan), flag=wx.EXPAND | wx.LEFT, border=LeftMargin)
		# make bindings
		self.CancelButton.Bind(wx.EVT_BUTTON, self.OnCancelJoinCollaborationButton)
		self.GoButton.Bind(wx.EVT_BUTTON, self.OnGoJoinCollaborationButton)
		# tell panel to use sizer
		MyPanel.SetSizer(self.MainSizer)
		MyPanel.SetAutoLayout(True)
		self.MainSizer.Layout()
		MyPanel.Fit()

	def OnCancelJoinCollaborationButton(self, Event): # handle click on "cancel" button in "join collaboration" dialogue
		self.EndModal(wx.ID_CANCEL)

	def OnGoJoinCollaborationButton(self, Event):
		# check that user has entered a name and a collaboration code
		NameSupplied = self.NameTextCtrl.GetValue().strip()
		CodeSupplied = self.CodeTextCtrl.GetValue().strip()
		if not (NameSupplied and CodeSupplied): # one of them is missing
			self.MessageLabel.SetLabel(_('Please supply a name and code, then click Go again'))
		else: # request to join collaboration %%% working here
#		self.ReturnData = (TargetTemplateFile, '', False)
#		# close the template selection dialogue box
			self.EndModal(wx.ID_OK)
