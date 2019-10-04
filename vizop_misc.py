# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright xSeriCon, 2018
import os, os.path, re, sys, wx, wx.adv, zmq
import xml.etree.ElementTree as ElementTree

# Vizop modules needed:
from settings import SettingsManager
import info, core_classes

"""
The vizop_misc module contains miscellaneous functions used throughout Vizop, including communications socket handling
"""

DATA_DIR = 'runtime'
VIZOP_ROOT = os.getcwd() # get the folder in which Vizop is executing
zmqContext = zmq.Context() # context for communications sockets. Must be only 1 instance for whole of Vizop instance

def ReverseLookup(Dic={}, TargetValue=None, NotFoundValue=None): # updated 2Mar2013
	# searches values in Dic for TargetValue, and returns corresponding key in Dic, or NotFoundValue if TargetValue not found
	# If >1 instance of TargetValue in Dic, an arbitrary one of the matching keys will be returned
	foundkey = NotFoundValue
	for k in Dic.keys():
		if (Dic[k] == TargetValue):
			foundkey = k
			break
	return foundkey

def XYadd(tup1, tup2): # returns tuple/list whose elements are the sum of respective elements in tup1, tup2
	# (which can be of any length). Returns same type as tup1
	tupsum = []
	for i in range(min(len(tup1), len(tup2))):
		tupsum.append(tup1[i] + tup2[i])
	return type(tup1)(tupsum)

def ColourFrac(Col1, Col2, Col2Frac=0.0): # returns colour (tuple) that is a fraction Col2Frac of the way from Col1 to Col2
	# e.g. ColourFrac( (0,0,0), (100,100,100), 0.75 ) returns (75,75,75)
	return tuple(map(lambda c1, c2: c1 + (c2-c1)*Col2Frac, Col1, Col2))

def RegisterKeyPressHandler(KeyPressHash, KeyCode, Handler, Args={}):
	# put the Handler for keypress KeyCode (int or list) into keypress table KeyPressHash.
	# Return updated KeyPressHash
	# KeyCode can also be a list of key codes; Handler will be invoked if all the keys are pressed simultaneously in correct order
	# If KeyCode is already in the table, the previous Handler is overwritten
	# Args is dict of arguments and values needed by Handler
	# KeyPressHash is list of tuples, rather than dict, because dict doesn't allow lists as keys
	ExistingKeyCodes = [k for (k, h, a) in KeyPressHash]
	if KeyCode in ExistingKeyCodes: # if KeyCode already registered, replace it
		KeyPressHash[ExistingKeyCodes.index(KeyCode)] = (KeyCode, Handler, Args.copy())
	else: # KeyCode not registered: add new item to KeyPressHash
		KeyPressHash.append( (KeyCode, Handler, Args.copy()) )
	return KeyPressHash

def UnregisterKeyPressHandler(KeyPressHash, KeyCode):
	# remove keypress KeyCode (int or list) from keypress table KeyPressHash, if found. Return updated KeyPressHash table
	ExistingKeyCodes = [k for (k, h, a) in KeyPressHash]
	if KeyCode in ExistingKeyCodes: # is KeyCode in keypress hash table?
		KeyPressHash.pop(ExistingKeyCodes.index(KeyCode)) # remove the entry from hash table
	return KeyPressHash

def ClearKeyPressRegister(KeyPressHash): # clear all existing keypress handler records
	return []

def IsReadableFile(filename):
	"""
	Returns True if filename (str) is an existent file and is readable
	"""
	return (os.path.isfile(filename) and
			os.access(filename, os.R_OK))
	# TODO see note on security in os.path website and revise this code to plug the hole


def IsWritableLocation(Path):
	"""
	Returns True if Path (str) is an existent folder that user has write access to
	"""
	return (os.path.isdir(Path) and os.access(Path, os.W_OK))


def get_usr_runtime_files_dir():
	"""
	Returns the complete path to the directory that Vizop uses to store
	user specific files needed at runtime. This is platform dependent,
	e.g. on MacOS and Linux it will be ${HOME}/.vizop
	"""
	if sys.platform == 'win32':
		#Windows doesn't really do hidden directories, so get rid of the dot
		return os.path.join(os.path.expanduser('~'),"%s" % info.CacheFolderTail)
	else:
		return os.path.join(os.path.expanduser('~'),".%s" % info.CacheFolderTail)


def get_sys_runtime_files_dir():
	"""
	Returns the complete path to the directory that Vizop uses to store
	user independent files needed at runtime. This is platform dependent,
	but on Linux it will probably be /usr/local/share/Vizop
	"""
	return os.path.join(VIZOP_ROOT, DATA_DIR)


def select_file_from_all(message='', default_path=None,
					  wildcard='*', allow_multi_files=False, parent_frame=None, **Args):
	"""
	Provide generic file selection dialogue. Allows user to select any file(s)
	from the filesystem.
	Returns list of full file paths selected (or [] if none were selected)
	"""
	# **Args is to soak up obsolete arg read_only (no longer recognised by wxPython)
	# First, get default directory to show in dialogue
	if default_path is None:
		sm = SettingsManager()
		try: # get saved path from config file
			default_path = sm.get_config('UserWorkingDir')
		except KeyError: # no path saved; select user's home folder
			default_path = os.path.expanduser('~')

	dialogue = wx.FileDialog(message=message, defaultDir=default_path,
							 wildcard=wildcard,
							 style=((wx.MULTIPLE * allow_multi_files) | wx.OPEN),
							 parent=parent_frame, pos=(100, 100))

	if dialogue.ShowModal() == wx.ID_OK: # dialogue box exited with OK button
		if allow_multi_files:
			return dialogue.GetPaths()
		else:
			return [dialogue.GetPath()]
	else:
		# dialogue box exited with Cancel button
		return []

def OnAboutRequest(Parent=None, event=None):
	# handle request for 'About Vizop' info: show About box
	# To consider: the keyboard shortcuts for the parent screen still work while the About box is open. This could be
	# confusing for the user. Currently haven't found any way to resolve this. This function exits while the About
	# box is still on screen, so it's not enough just to block keyboard shortcuts while this function has control.
	AboutInfo = wx.adv.AboutDialogInfo() # create an 'About' info object, and populate it
	AboutInfo.SetDescription(_('Vizop is a Fault Tree Analysis utility.\n\n' + \
		'The next generation of Vizop will add support\nfor PHA and alarm rationalization.\n\n' + \
		info.OWNER_EMAIL))
	for Developer in info.DEVELOPERS:
		AboutInfo.AddDeveloper(Developer)
	AboutInfo.SetName(info.PROG_NAME)
	AboutInfo.SetVersion(info.VERSION)
	AboutInfo.SetCopyright(_(u'Copyright \u00A9 %s %s') % (info.YEAR_LAST_RELEASED, info.OWNER)) # \u00A9 = (c) symbol
	# TODO add licensing info here: AboutInfo.SetLicense(str)
	wx.adv.AboutBox(AboutInfo) # show the About box

def GetFilenameForSave(DialogueParentFrame, DialogueTitle='', DefaultDir='', DefaultFile='', Wildcard='', DefaultExtension=''):
	""" Open 'save' dialogue; get filename from user
		Returns: (ProceedToSave, Full path name of target file)
		ProceedToSave is boolean: True if file write can proceed """
	Dialogue = wx.FileDialog(parent=DialogueParentFrame, message=DialogueTitle, defaultDir=DefaultDir,
							 defaultFile=DefaultFile, wildcard=Wildcard, style= wx.SAVE | wx.OVERWRITE_PROMPT ) # Rappin p166
	if Dialogue.ShowModal() == wx.ID_OK: # we got a filename and user didn't cancel
		ProceedToSave = True
		SaveFilename = EnsureFilenameHasExtension(Dialogue.GetPath(), DefaultExtension, Separator=os.extsep)
	else:
		ProceedToSave = False
		SaveFilename = ''
	Dialogue.Destroy()
	return (ProceedToSave, SaveFilename)

def EnsureFilenameHasExtension(Filename='', Extension='', Separator='.'):
	# check whether Filename (str) ends in Extension (str), and if it doesn't, append it with separator (usually a dot).
	# Returns final filename (str)
	TargetExtension = Separator + Extension
	if not (Filename[-len(TargetExtension):] == TargetExtension): Filename += TargetExtension
	return Filename

def SendRequest(Socket=None, Command='RQ_Null', FetchReply=False, XMLRoot=None, **Args):
	# make an XML request string and send it to datacore.
	# This is the primary means of communication between controlframe and datacore.
	# Socket (a zmq socket instance): socket to use for sending message (required)
	# Command (str): the basic command string, usually beginning with RQ_
	# FetchReply (bool): If True, SendRequest will wait for reply to command and return reply received
	# XMLRoot (XML tree): if supplied, this is sent as the body of the command. If None, take from Args
	# Args (dict): keywords are data names (str), values are data values (str, or list of str). Ignored if XMLRoot provided
	if __debug__ == 1: # skip the following checking code if running in Optimized mode
		assert Socket is not None
		assert type(Command) is str, "VM1142 SendRequest: oops: requested Command is not a string"
		# Do type checking of Args: check that keys are str, and values are either str or list of str
		for Cmd, Values in Args.items():
			if type(Cmd) is not str:
				print("VM1148: Oops: non-string data name %s sent to SendRequest" % str(Cmd))
			if type(Values) is not list:
				Values = [Values]
			for ThisValue in Values:
				if not isinstance(ThisValue, str):
					print("VM1153: Oops: non-string data value %s sent to SendRequest" % str(ThisValue))
	if XMLRoot is None:
		# create new XML structure from keys and values in Args, and set root element = Command
		RootElement = ElementTree.Element(Command)
		MyXMLTree = ElementTree.ElementTree(element=RootElement)
		# for any Args, make sub-elements and insert into the XML tree
		for Cmd, Values in Args.items():
			# force Values to be a list; if only a single str was supplied, put it in a list
			if type(Values) is not list:
				Values = [Values]
			# make multiple sub-elements, one for each item in Values; set element text to corresponding value in Values
			for ThisValue in Values:
				NewElement = ElementTree.SubElement(RootElement, Cmd)
				NewElement.text = ThisValue # Can't put this into preceding line as text= arg; it creates a separate attrib in XML tag
	else: # use XMLRoot supplied
		RootElement = XMLRoot
	# convert the XML tree to a string
	XMLString = ElementTree.tostring(RootElement, encoding='UTF-8')
	# submit the string via zmq
#	# next line is for debugging only
#	ThisSocketNo, ThisSocketLabel =  [(s.SocketNo, s.SocketLabel) for s in RegisterSocket.Register if s.Socket == Socket][0]
#	print('VM209 sending request on socket: ', ThisSocketNo, ThisSocketLabel)
	Socket.send(XMLString, copy=True)
	if FetchReply: # this path not currently used?
		ReplyReceived = None
		while ReplyReceived is None:
			ReplyReceived = ListenToSocket(Socket=Socket, Wait=True, SendReply2=False)
		return ReplyReceived
	else: return None # don't wait, exit

def SendReply(Socket=None, Reply=None):
	# send reply on Socket (a REP-type socket). Reply is an XML tree object
	assert Socket is not None
	assert Reply is not None
	Socket.send(ElementTree.tostring(Reply, encoding='UTF-8'))

def FetchReply(Socket=None):
	# get reply from socket. Needs to be called after a SendRequest message has been processed, because
	# REQ/REP sockets must be used in a send() - recv() sequence. Currently not used.
	Reply = SocketToUse.recv() # get reply message
	print("VM1247 FetchReply: received reply from DataCore: '%s'" % Reply)
	return Reply

class SocketInRegister(object):
	# items are zmq sockets with associated data needed by other modules

	def __init__(self, Socket=None, SocketNo=5555, SocketLabel='', Viewport=None, PHAObj=None, BelongsToDatacore=False):
		object.__init__(self)
		assert isinstance(SocketNo, int)
		assert isinstance(BelongsToDatacore, bool)
		self.Socket = Socket # a zmq socket object
		self.SocketNo = SocketNo # the 4 digits at the end of the socket's IP address (int)
			# attrib SocketNo is used by name in controlframe module; don't rename it
		self.SocketLabel = SocketLabel # for identifying which socket to use
		self.Viewport = Viewport # Viewport that raises and expects messages, if any
		self.PHAObj = PHAObj # PHA object to which Viewport belongs
		self.BelongsToDatacore = BelongsToDatacore # whether socket is at datacore side of the pair

# if we decide to write a routine to get the SocketInRegister corresponding to a given zmq Socket, get code from
# RunCommsThread() in datacore

def GetNewSocketNumber():
	# return next available zmq socket number as str
	FirstSocketNumber = 5555 # number to allocate to first socket created
	if hasattr(GetNewSocketNumber, 'LastSocketNumber'): # any socket numbers allocated previously?
		assert isinstance(GetNewSocketNumber.LastSocketNumber, int)
		assert GetNewSocketNumber.LastSocketNumber < 9999
		GetNewSocketNumber.LastSocketNumber += 1
	else:
		GetNewSocketNumber.LastSocketNumber = FirstSocketNumber
	return GetNewSocketNumber.LastSocketNumber

def RegisterSocket(NewSocket, SocketNo, SocketLabel, Viewport=None, PHAObj=None, BelongsToDatacore=True,
		AddToVizopRegister=True):
	# add NewSocket (a zmq socket instance) to socket register. Create and return its instance of SocketInRegister
	# BelongsToDatacore (bool): whether socket is at the datacore end of the pair
	# if AddToVizopRegister is False, don't add to the internal Vizop Register - only register it with zmq
	# (The Vizop register only contains sockets belonging to datacore)
	assert isinstance(AddToVizopRegister, bool)
	# check if the socket register exists; if not, create it
	if not hasattr(RegisterSocket, 'Register'):
		RegisterSocket.Register = []
		# set up poller to check all current sockets in turn
		RegisterSocket.Poller = zmq.Poller()
	if AddToVizopRegister:
		ThisSocketObj = SocketInRegister(NewSocket, SocketNo, SocketLabel, Viewport=Viewport, PHAObj=PHAObj,
			BelongsToDatacore=BelongsToDatacore)
		RegisterSocket.Register.append(ThisSocketObj)
	else: # find socket in existing items in Vizop register
		ThisSocketObj = [s for s in RegisterSocket.Register if s.SocketNo == SocketNo][0]
	RegisterSocket.Poller.register(ThisSocketObj.Socket, zmq.POLLIN)
	return ThisSocketObj

def SetupNewSocket(SocketType='REQ', SocketLabel='', Viewport=None, PHAObj=None, SocketNo=None,
		BelongsToDatacore=False, AddToRegister=True):
	# Make a new zmq socket of type REQ (a 'request' half of a request/reply pair) or REP (a 'reply' half)
	# SocketNo (int): the socket number of the matching other half of the pair, already created, or
	# None if we should fetch a new socket number
	# BelongsToDatacore (bool): whether the socket is the datacore end of the pair
	# AddToRegister (bool): whether to add the socket to the Vizop register
	# Return the new socket, its corresponding SocketInRegister instance, and its socket number (int)
	# PHAObj currently gets assigned in DoNewViewportCommand() in module controlframe, because it may be available only
	# after a new PHA object has been created.
	assert SocketType in ('REQ', 'REP', 'PUSH', 'PULL')
	assert isinstance(SocketLabel, str)
	assert isinstance(SocketNo, int) or (SocketNo is None)
	assert isinstance(BelongsToDatacore, bool)
	assert isinstance(AddToRegister, bool)
	global zmqContext
	# fetch socket number if required
	if SocketNo is None: ThisSocketNo = GetNewSocketNumber()
	else: ThisSocketNo = SocketNo
	# create socket and bind/connect it to the appropriate address
	NewSocket = zmqContext.socket({'REQ': zmq.REQ, 'REP': zmq.REP, 'PUSH': zmq.PUSH, 'PULL': zmq.PULL}[SocketType])
	if SocketType == 'REQ': NewSocket.connect("tcp://127.0.0.1:" + str(ThisSocketNo))
	else: NewSocket.bind("tcp://127.0.0.1:" + str(ThisSocketNo))
	# put socket in Vizop's global socket register
	NewSocketObj = RegisterSocket(NewSocket, ThisSocketNo, SocketLabel.strip(), Viewport=Viewport, PHAObj=PHAObj,
		BelongsToDatacore=BelongsToDatacore, AddToVizopRegister=AddToRegister)
	return NewSocket, NewSocketObj, ThisSocketNo

def SocketWithName(TargetName): # return socket (SocketInRegister instance) in socket register with SocketLabel == TargetName.
	# raises error if socket not found
	Hits = [s for s in RegisterSocket.Register if s.SocketLabel == TargetName]
	assert len(Hits) == 1
	return Hits[0]

def ListenToSocket(Socket, Handler=None, SendReply2=True, **Args):
	# check if any message received on Socket (a zmq socket), call Handler (a callable or None) to handle it,
	# get reply back from handler, and (if SendReply2 (bool) is True) send reply on Socket
	# Handler: callable taking arg MessageReceived (XML string)
	# return any message was received on Socket (str or None)
	assert isinstance(SendReply2, bool)
	SocketsWaiting = dict(RegisterSocket.Poller.poll(timeout=1))
	MessageReceived = None
#	if SocketsWaiting: print("VM285 a socket has a waiting message in ListenToSockets: ",\
#			[(s.SocketNo, s.SocketLabel) for s in RegisterSocket.Register if s.Socket in SocketsWaiting])
	# any incoming message from Socket?
	if Socket in SocketsWaiting:
#		print("VM264 processing socket in ListenToSockets: ", [(s.SocketNo, s.SocketLabel) for s in RegisterSocket.Register if s.Socket == Socket],
#			'Sending reply: ', SendReply2, 'Origin code:', Args.get('OriginCode', 0))
		MessageReceived = Socket.recv()
		if Args.get('Debug', False): print("VM305 message received: ", MessageReceived)
		if Handler: # any handler supplied?
			# handle the message and collect an XML tree containing the response to send back to origin
			ReplyXML = Handler(MessageReceived=MessageReceived, **Args)
			assert ReplyXML is not None, Handler.__name__
		else: ReplyXML = MakeXMLMessage('Null', 'Null')
#		if SendReply2 and (ReplyXML.tag is not 'OK'): # send reply if required; don't send 'OK' as it's just an acknowledgement
		if SendReply2: # send reply if required
			Socket.send(ElementTree.tostring(ReplyXML, encoding='UTF-8')) # use SendReply() instead?
	return MessageReceived

def MakeXMLMessage(RootName='Message', RootText='', **Args):
	# returns root element of a new XML tree with root element=RootName (str) and its content = RootText (str)
	# Args can include (optional) Elements (dict) with keys = tags, values = text
	assert type(RootName) is str, "Element tag '%s' received, string needed" % str(RootName)
	assert type(RootText) is str, "Element content '%s' received, string needed" % str(RootText)
	RootElement = ElementTree.Element(RootName)
	RootElement.text = RootText
	# add any elements specified in Args
	if 'Elements' in Args:
		assert isinstance(Args['Elements'], dict)
		for ThisTag, ThisText in Args['Elements'].items():
			NewSubElement = ElementTree.SubElement(RootElement, ThisTag)
			NewSubElement.text = ThisText
	return RootElement

def PHAModelClassWithName(TargetName):
	# returns the PHA model class with internal name = TargetName, or None if not found
	assert isinstance(TargetName, str)
	InternalNameList = [c.InternalName for c in core_classes.PHAModelMetaClass.PHAModelClasses]
	if TargetName in InternalNameList:
		return core_classes.PHAModelMetaClass.PHAModelClasses[InternalNameList.index(TargetName)]
	else: return None

def GetCategoryFromValue(Categories, ThisValue, RoundUp=True):
	# return item in Categories (list of CategoryNameItem instances) where ThisValue (NumValueItem instance) is in the
	# range between the category's MinValue and MaxValue (inclusive of endpoints).
	# If ThisValue lies on the boundary between 2 categories, the higher category is returned if RoundUp (bool) is True,
	# else the lower category is returned.
	# If no category encompasses ThisValue, None is returned.
	# Assumes the MinValue and MaxValues of categories in Categories are in ascending order.
	assert isinstance(Categories, list)
	assert isinstance(ThisValue, core_classes.NumValueItem)
	assert isinstance(RoundUp, bool)
	TargetValue = ThisValue.GetMyValue()
	TargetUnit = ThisValue.GetMyUnit() # get unit of ThisValue, for conversion of values in Categories
	Found = False
	TryRoundUp = False # if we find ThisValue is at the top of a category range and RoundUp is set, whether to check that
		# ThisValue is at the bottom of the next category range
	LastCategoryIndex = len(Categories) - 1
	ThisCategoryIndex = 0
	while ThisCategoryIndex <= LastCategoryIndex: # scan over categories supplied
		ThisCategoryMinValue = core_classes.GetMyValueInUnit(Categories[ThisCategoryIndex].MinValue, NewUnit=TargetUnit)
		ThisCategoryMaxValue = core_classes.GetMyValueInUnit(Categories[ThisCategoryIndex].MaxValue, NewUnit=TargetUnit)
		# check for TryRoundUp from preceding category
		if TryRoundUp:
			Found = True # either this category or the preceding category is the target
			if utilities.EffectivelyEqual(ThisCategoryMinValue, TargetValue): HitCategoryIndex = ThisCategoryIndex
				# this category's min value matches ThisValue; so this category is the match
		else: # not checking TryRoundUp
			InRange = (MinValue <= TargetValue <= MaxValue)
			TryRoundUp = utilities.EffectivelyEqual(ThisCategoryMaxValue, TargetValue) and RoundUp and\
				(ThisCategoryIndex == LastCategoryIndex) # don't TryRoundUp if this is the highest category
			Found = InRange and not TryRoundUp
			if InRange: HitCategoryIndex = ThisCategoryIndex # category that matches criteria
			ThisCategoryIndex += 1
	if Found: return Categories[HitCategoryIndex]
	else: return None

def HighestCategoryAmong(AllCategories=[], AscendingOrder=True, QueryCategories=[]):
	# find the item in QueryCategories (list of CategoryNameItem instances) that has the min/max index in AllCategories
	# (list of CategoryNameItem instances).
	# AscendingOrder (bool) indicates whether the categories in AllCategories are ordered from low to high.
	# If True, searches for max index; else searches for min index
	# Any item in QueryCategories that isn't in AllCategories is ignored.
	# If QueryCategories contains no items in AllCategories or is empty, returns None.
	assert isinstance(AllCategories, list)
	assert isinstance(AscendingOrder, bool)
	assert isinstance(QueryCategories, list)
	QueriesInAllCategories = [c for c in QueryCategories if c in AllCategories]
	if QueriesInAllCategories: # any matching categories found?
		return AllCategories[(max if AscendingOrder else min)([AllCategories.index(c) for c in QueriesInAllCategories])]
	else: return None

def UndefinedCategoryAmong(Categories):
	# returns the first item in Categories (list of CategoryNameItem instances) with attribute IsUndefined = True
	# If no categories in Categories have IsUndefined = True, or Categories contains no CategoryNameItem instances,
	# returns None
	UndefinedFlags = [getattr(c, 'IsUndefined', False) for c in Categories]
	if True in UndefinedFlags: return Categories[UndefinedFlags.index(True)]
	else: return None
