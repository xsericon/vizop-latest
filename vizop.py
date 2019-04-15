# -*- coding: utf-8 -*-
# Module vizop: part of Vizop, (c) 2018 xSeriCon. Contains main program. Launch vizop by running this module.
# Main program handles launch of the Welcome screen and the Control frame

# library modules
from __future__ import division  # makes a/b yield exact, not truncated, result. Must be 1st import
import wx # provides basic GUI functions
from wx.lib.mixins.inspection import InspectableApp # InspectableApp for debugging
# import gettext  # used to translate messages to the user into the local language
import os, threading
import xml.etree.ElementTree as ElementTree  # XML handling

# other vizop modules required here
import startup_vizop, settings, projects, controlframe, core_classes, display_utilities, utilities, info, vizop_misc,\
	faulttree, alarmrat
# must import all modules containing class definitions of subclasses of ViewportBaseClass, such as faulttree,
# even though they don't appear to be referenced in this module. This is to ensure the subclasses get catalogued

# global variables for this module
sm = settings.SettingsManager()
MinDivisor = 1e-20  # smallest absolute value treated as nonzero

RiskReceptors = [core_classes.DefaultRiskReceptor]

NumConstants = []  # list of constants defined for this project (instances of ConstNumValueItem)

# --- FAULT TREE CLASSES --- 

class FTCBVisualStateItem(object):  # states of Content Button objects. Redundant?

	def __init__(self, BackgroundColour, BorderColour, TextColour):
		object.__init__(self)
		self.BackgroundColour = BackgroundColour
		self.BorderColour = BorderColour
		self.TextColour = TextColour


FTCBNormal = FTCBVisualStateItem((0x3b, 0x45, 0xa6), (0xa6, 0x9d, 0x3b),
								 (0xff, 0xff, 0xff))  # colours: deep blue, mustard, white
FTCBActivated = FTCBVisualStateItem((0x77, 0x83, 0xff), (0xa6, 0x9d, 0x3b),
									(0xff, 0xff, 0xff))  # colours: slate blue, mustard, white
FTCBPressing = FTCBVisualStateItem((0xff, 0xf4, 0x77), (0xa6, 0x9d, 0x3b),
								   (0x00, 0x00, 0x00))  # colours: lemon yellow, mustard, black

FTCBStates = [FTCBNormal, FTCBActivated, FTCBPressing]


class IPLItem(object):  # IPL object. Currently used in Fault Tree; however FT has its own class definition so this
	# may be redundant

	def __init__(self, Proj):
		object.__init__(self)
		self.Text = None  # a TextItem instance containing rich text and formatting attributes
		self.Causes = set()  # FTBaseEventItem instances associated with this IPL
		self.Value = None  # NumValueItem instance
		self.CollapseGroups = set()  # collapse groups this event belongs to
		self.Numbering = None  # NumberingItem instance
		self.ShowInSRS = True  # whether IPLItem is listed in SRS. This is to allow hiding of non-provable IPLs such as ignition probability.
		self.Kind = None  # which IPLKindItem the IPL relates to (eg relief valves)
		self.ParentList = None  # list containing this item; needed to deduce numbering of the item
		self.BackgroundColour = Proj.NextFTItemBackgroundColour
		self.Shape = None  # shape of IPL container as displayed


class CondModifierItem(object):  # Conditional Modifier object. Currently used in Fault Tree. Currently same as IPLItem.

	def __init__(self, Proj):
		object.__init__(self)
		self.Text = None  # a TextItem instance containing rich text and formatting attributes
		self.Causes = set()  # FTBaseEventItem instances associated with this IPL
		self.Value = None  # NumValueItem instance
		self.CollapseGroups = set()  # collapse groups this event belongs to
		self.Numbering = None  # NumberingItem instance
		self.ShowInSRS = True  # whether IPLItem is listed in SRS. This is to allow hiding of non-provable IPLs such as ignition probability.


def CheckRuntimeEnvironment():
	# check all required folders exist and have appropriate permissions
	# return Problems (str): description of problem(s) found, or '' if no problems
	# first, ensure user runtime directory (~/.vizop) exists
	if not os.path.isdir(vizop_misc.get_usr_runtime_files_dir()):
		os.makedirs(vizop_misc.get_usr_runtime_files_dir())
	# check the system runtime folders exists with read access
	Problems = ''
	RuntimeDirs = [os.path.join(vizop_misc.get_sys_runtime_files_dir(), info.IconFolderTail),
						os.path.join(vizop_misc.get_sys_runtime_files_dir(), 'locale')]
	for ThisFolder in RuntimeDirs:
		if not (os.path.isdir(ThisFolder) and os.access(ThisFolder, os.R_OK)):
			# this is likely a fatal error - there is something wrong with the installation
			Problems += 'Folder %s is missing or unreadable\n' % ThisFolder
			# can't translate this message - might be missing our language files
	return Problems

def PrecedingObjects(FT, TargetObj):  # returns set of objects in Fault Tree FT that are directly connected to TargetObj
	# might be redundant (not currently used) but kept as it might be useful in FT later
	MaxIterations = 100  # arbitrary upper limit on depth of recursion, to trap infinite loops

	def FoundObjs(BaseObj, TargetObj, FoundSoFar,
				  Iterations):  # recursively return BaseObj if it is connected to TargetObj
		if Iterations > MaxIterations: return FoundSoFar  # jump out if in an infinite loop
		if TargetObj in BaseObj.ConnectsTo:
			FoundSoFar.add(BaseObj)
			return FoundSoFar
		for NextLevel in BaseObj.ConnectsTo:
			return FoundObjs(NextLevel, TargetObj, FoundSoFar, Iterations + 1)

	PrecObjs = ([])  # objects found
	FoundSoFar = set([])
	for Obj in FT.BaseEvents:
		FoundSoFar = FoundObjs(Obj, TargetObj, FoundSoFar, Iterations=0)
	return FoundSoFar


class iWindowModeItem(
	object):  # defines an iWindow mode (iWindow is the panel on the right side of the main edit screen, showing information and editable parameters)

	def __init__(self):
		object.__init__(self)
		self.ClickInContentWindow = None  # defines what happens when user clicks in Content Window when this iWindowMode is active.
		# can be: None (do nothing), 'Next'/'Revert' (go to next or preceding iWindowMode), or an iWindowMode instance to switch to.
		self.DefaultInteractionMode = None  # default Content Window InteractionMode when this iWindowMode is active.
		# can be: None (leave unchanged), or an InteractionModeItem instance

def MakeColourSchemes():
	# create colour schemes. For now, just sets up a default colour scheme.
	# return current ColourScheme object
	return display_utilities.ColourSchemeItem()

def SetupObjSelectionList(self, ObjectTypeList):
	# populates 'new object' list by scanning through all available classes of <obj> (currently only Viewports)
	# ObjectTypeList is <obj>Types
	# returns ( list of screen names of <obj> that can be created manually, ditto + kbd shortcut,
	# list of <obj> types in same order as above name lists, hash (dict) with keys = shortcut keys; values: corresponding object classes )
	ObjsCanBeCreatedManually = []  # list of object type screen-names
	ObjsCanBeCreatedManuallyWithShortcuts = []  # list of object type screen-names suffixed by keyboard shortcuts
	ObjTypes = []
	ObjKbdHash = {}  # keys: shortcut keys; values: corresponding object classes
	KbdSCused = []
	KbdSCspare = list('1234567890')  # spare keyboard shortcuts to use in event of clashes
	for e in ObjectTypeList:
		if e.CanBeCreatedManually:  # this object type can be created manually, add to the list
			(HumanName, PreferredKbdShortcut) = e.HumanName(sm.get_value('SystemLanguage'))
			PreferredKbdShortcut = min(chr(126),
									   max(chr(33), PreferredKbdShortcut[0])) # restrict it to one printable character
			# check whether the preferred shortcut is already assigned; if so, provide one from list of spares (0th or 1st item)
			if PreferredKbdShortcut in KbdSCused:
				spareIndex = int((KbdSCspare + [''])[0] == PreferredKbdShortcut)
				# which item to use, 0 or 1 (use 1 if 0th already assigned)
				ksc = (KbdSCspare + ['', ''])[spareIndex]  # get a spare shortcut, or '' if all used up
				if len(KbdSCspare) > spareIndex: del KbdSCspare[
					spareIndex]  # delete the one used from the list of spares
			else:
				ksc = PreferredKbdShortcut
			# set up how shortcut will be displayed: currently after a | unless blank
			if ksc == '':
				kscDisplay = ''
			else:
				kscDisplay = ' | ' + ksc
				KbdSCused += [ksc]
				ObjKbdHash[ksc] = e
			ObjsCanBeCreatedManually += [HumanName]
			ObjsCanBeCreatedManuallyWithShortcuts += [HumanName + kscDisplay]
			ObjTypes.append(e)
	return ObjsCanBeCreatedManually, ObjsCanBeCreatedManuallyWithShortcuts, ObjTypes, ObjKbdHash

def DoNewPHAObj(Proj, ViewportID=None, NewPHAObjType=None, **NewPHAObjArgs):
	# make a new, empty PHA object (eg HAZOP, FT) in Proj (a Project instance). Redundant, now in module controlframe
	# If ViewportID (str or None) is not None, attach it to the new PHA object.
	# NewPHAModelArgs are sent to the PHA model initiator.
	# Returns PHA object.
	assert isinstance(Proj, projects.ProjectItem), "DC1453 Proj '%s' supplied isn't a project" % str(Proj)
	if NewPHAObjType is not None:
		assert issubclass(NewPHAObjType, core_classes.PHAModelBaseClass),\
			"DC1459 NewPHAObjType %s isn't a PHA object type" % str(NewPHAObjType)
	# make the PHA model
	PHAObj = NewPHAObjType(**NewPHAObjArgs)
	# attach PHA object to Viewport shadow
	if ViewportID is not None:
		assert isinstance(ViewportID, str)
		utilities.ObjectWithID(Proj.AllViewportShadows, ViewportID).PHAObject = PHAObj
	return PHAObj

def DoNewFTEventNotIPL(Root):
	# handle request from Control Frame for new non-IPL event in an FT. Redundant, now handled in FTObjInCore class
	# input data is supplied in Root, an XML ElementTree root element
	# return reply data (XML tree) to send back to Control Frame
	global EditAllowed, OpenProjects
	print("DC612 starting DoNewFTEventNotIPL")
	# check if we can proceed to edit the PHA model
	if EditAllowed:
		# find out which project and PHA model to work in
		ThisProj = utilities.ObjectWithID(OpenProjects, Root.find('Proj').text)
		ThisPHAModel = utilities.ObjectWithID(ThisProj.PHAObjs, Root.find('PHAObj').text)
		# request ThisPHAModel to add the event
		ThisPHAModel.AddNewFTEventNotIPL(ColNo=Root.find('ColNo').text, IndexInCol=Root.find('IndexInCol').text)
		Reply = MakeXMLMessage(Elements={'OK': 'NewEventAdded'})
		# get full redraw data to send back to all applicable Viewports
		MsgToViewports = ThisPHAModel.GetFullRedrawData()
		# Send redraw message to all Viewports attached to ThisPHAModel
		for ThisViewport in ThisPHAModel.Viewports:
			ThisViewport.C2DSocketREQObj.send(ElementTree.tostring(MsgToViewports, encoding='UTF-8'))
			# %%% TODO Viewport needs to receive and process the message
	else:  # couldn't update PHA model because editing is blocked
		Reply = MakeXMLMessage(Elements={'CantComply': 'EditingBlocked'})
	return Reply

def MakeXMLMessage(RootName='Message', RootText='', **Args):
	# duplicate function in vizop_misc. Should remove this copy and transfer references to vizop_misc.
	# returns root element of a new XML tree with root element=RootName (str) and its content = RootText (str)
	# Args can include (optional) Elements (dict) with keys = tags, values = text
	#	MyXMLTree = ElementTree.ElementTree() # create new XML structure; might not be necessary
	assert type(RootName) is str, "Element tag '%s' received, string needed" % str(RootName)
	assert type(RootText) is str, "Element content '%s' received, string needed" % str(RootText)
	RootElement = ElementTree.Element(RootName)
	RootElement.text = RootText
	# add any elements specified in Args
	if 'Elements' in Args:
		for ThisTag, ThisText in Args['Elements'].items():
			NewSubElement = ElementTree.SubElement(RootElement, ThisTag)
			NewSubElement.text = ThisText
	return RootElement

def HandleRequestFromControlFrame(InMsg): # redundant, moved to module controlframe
	print("VZ603: message received from ControlFrame:", InMsg)
	ParsedMsgRoot = ElementTree.XML(InMsg)
	# handlers for all possible requests from Control Frame
	Handler = {'RQ_NewViewport': DoNewViewport, 'RQ_NewFTEventNotIPL': DoNewFTEventNotIPL}[ParsedMsgRoot.tag.strip()]
	# call handler and collect reply XML tree to send back to Control Frame
	ReplyXML = Handler(ParsedMsgRoot)
	return ReplyXML

def RunCommsThread(): # redundant. Now handled by controlframe's OnIdle()
	# execute communications thread. Contains a loop for polling comms sockets, and handlers for requests received
	global CurrentProject
	# first, set up 2 sockets for communication with local ControlFrame: frame to core (F2C) and vice versa (C2F)
	ControlFrameInwardSocket, CFInSktObj, N1 = vizop_misc.SetupNewSocket(SocketType='REP',
		SocketLabel='LocalControlFrameF2CREP', BelongsToDatacore=True)
	ControlFrameOutwardSocket, CFOutSktObj, N2 = vizop_misc.SetupNewSocket(SocketType='REQ',
		SocketLabel='LocalControlFrameC2FREQ', BelongsToDatacore=True)
	# start polling loop. TODO use vizop_misc.ListenToSockets()
	KeepLooping = True
	while KeepLooping:
		SocketsWaiting = dict(vizop_misc.RegisterSocket.Poller.poll(timeout=500)) # waits indefinitely for sockets if no timeout set
#		SocketsWaiting = dict(vizop_misc.RegisterSocket.Poller.poll()) # waits indefinitely for sockets if no timeout set
		if SocketsWaiting:
			ThisSocketLabel = [s.SocketLabel for s in vizop_misc.RegisterSocket.Register
				if s.Socket in SocketsWaiting]
		else: ThisSocketLabel = 'No sockets waiting'
		print("VZ665 SocketsWaiting: ", ThisSocketLabel)
		# any incoming message from ControlFrame?
		if ControlFrameInwardSocket in SocketsWaiting:
			# handle the message and collect an XML tree containing the response to send back to Control Frame
			ReplyXML = HandleRequestFromControlFrame(ControlFrameInwardSocket.recv())
			print("VZ658 XML received from handler in datacore: ", ElementTree.tostring(ReplyXML))
			ControlFrameInwardSocket.send(ElementTree.tostring(ReplyXML, encoding='UTF-8'))
		if ControlFrameOutwardSocket in SocketsWaiting:
			# dump any incoming reply for now (may use later)
			Dump = ControlFrameOutwardSocket.recv()
		# any incoming message from Viewports? (using getattr() in case CurrentProject is not yet assigned) # %%%
		ViewportSocketsSendingMessages = [s for s in vizop_misc.RegisterSocket.Register
			if s.Socket in SocketsWaiting if s.BelongsToDatacore if s.Viewport is not None]
		print("VZ676 Viewports sending messages: ", ViewportSocketsSendingMessages)
		# send the message to the corresponding PHA model object
		for ThisSocketObj in ViewportSocketsSendingMessages:
			# pass request to PHA model associated with the Viewport (we do this via datacore, not directly,
			# so that local and remote Viewports are treated the same)
			ThisSocketObj.Viewport.PHAObj.HandleIncomingRequest(ThisSocketObj.Socket.recv())
			# send updated data to applicable Viewports
			UpdateDisplayModels()
			KeepLooping = False
		# TODO Here, we will check any sockets sending replies from Viewports

def LaunchCommsThread(): # redundant
	# set up communications sockets for communications with Viewports.
	# launch a thread for handling requests received.
	# launch thread for handling requests
	CommsThread = threading.Thread(target=RunCommsThread)
	CommsThread.setDaemon(daemonic=True)  # to prevent comms thread from blocking Vizop termination
	CommsThread.start()

# main program
CheckRuntimeEnvironment()
app = InspectableApp(0) # make the wx app. Use Ctrl + Alt + I to inspect things. Need this before InitializeVizop()
StartupProblems = startup_vizop.InitializeVizop() # do some setting up and find any fatal environment problems
if StartupProblems:
	print("Unable to run ", info.PROG_SHORT_NAME, ". The following problems were reported:\n", StartupProblems, sep='')
	exit()
#setup gettext for translating messages
# first, find the path in which vizop is running
# set up the translator. _('foo') means 'get the translation of foo into the language defined in locale'
# We don't need this here because gettext is set up in module startup_vizop
# setup_script_path = os.path.dirname(os.path.abspath(sys.argv[0]))
# t = gettext.translation('setup', os.path.join(setup_script_path, 'locale'), fallback=True)
# _ = t.gettext

ColourScheme = MakeColourSchemes()  # set up default colour scheme
OpenProjects = []  # open project objects, in order of opening
CurrentProject = None # which project is being edited in control frame
# LaunchCommsThread()  # start thread for handling communication with Viewports
# set up 2 sockets for communication with local ControlFrame: frame to core (F2C) and vice versa (C2F)
ControlFrameInwardSocket, CFInSktObj, InwardSocketNumber = vizop_misc.SetupNewSocket(SocketType='REP',
	SocketLabel=info.ControlFrameInSocketLabel + '_Local', BelongsToDatacore=True)
ControlFrameOutwardSocket, CFOutSktObj, OutwardSocketNumber = vizop_misc.SetupNewSocket(SocketType='REQ',
	SocketLabel=info.ControlFrameOutSocketLabel + '_Local', BelongsToDatacore=True)

# vizop's primary display shows either a welcome frame or a control frame, depending on whether any project is open
RequestedToQuit = False  # whether user has requested to terminate vizop
while not RequestedToQuit:
	if OpenProjects:  # any projects open? if so, display CurrentProject's control frame
		# TODO need to assign unique ID to controlframe. Maybe from its socket number?
		ControlFrame = controlframe.ControlFrame(Projects=OpenProjects, ID="1", FirstProject=CurrentProject,
			ColScheme=ColourScheme, zmqContext=vizop_misc.zmqContext, DatacoreIsLocal=True)
		app.MainLoop()  # allow ControlFrame's event handlers to control program flow until ControlFrame is destroyed
		# we assume that ControlFrame will close all projects by itself
		# get ControlFrame's exit data
		RequestedToQuit = controlframe.ControlFrameData.Data.get('RequestToQuit', False)
	else: # no projects open: launch welcome screen
		WelcomeFrame = startup_vizop.NoProjectOpenFrame(parent=None, ID=-1, title=_("Vizop: Let's get started"),
			ColourScheme=ColourScheme)
		app.MainLoop()  # allow WelcomeFrame's event handlers to control program flow until WelcomeFrame is destroyed
		# get WelcomeFrame's exit data
		ProjectFilesToOpen = startup_vizop.NoProjectOpenFrameData.Data.get('ProjectFilesToOpen', [])
		ProjectsToCreateFromTemplates = startup_vizop.NoProjectOpenFrameData.Data.get('TemplateFilesToSpawnFrom', [])
		RequestedToQuit = startup_vizop.NoProjectOpenFrameData.Data.get('RequestToQuit', True)
		SaveOnFly = startup_vizop.NoProjectOpenFrameData.Data.get('SaveOnFly', True)
		if ProjectFilesToOpen:
			# handle any project open or create requests
			if ProjectsToCreateFromTemplates:  # any new projects to create?
				NewlyOpenedProjects, SuccessReport = \
					projects.CreateProjects(ProjectsToCreateFromTemplates, SaveOnFly, ProjectFilesToOpen)
			else:  # opening existing projects
				NewlyOpenedProjects, SuccessReport = projects.OpenProjectFiles(ProjectFilesToOpen)
			# TODO: give user feedback based on SuccessReport
			OpenProjects += NewlyOpenedProjects
			# set CurrentProject
			if OpenProjects:
				CurrentProject = OpenProjects[0]
			else:
				CurrentProject = None
				# do any pre-exit tidying up here; should close xml context