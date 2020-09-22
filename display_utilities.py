# -*- coding: utf-8 -*-
# Module display_utilities: part of Vizop, (c) 2020 xSeriCon. Contains common class definitions and functions for all Viewports

# library modules
# from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import wx, wx.grid, wx.lib.gridmovers, zmq, math # wx provides basic GUI functions
from wx.lib.expando import ExpandoTextCtrl, EVT_ETC_LAYOUT_NEEDED
import wx.lib.buttons as buttons
from sys import stdout

# other vizop modules required here
import art, utilities, vizop_misc, info, core_classes

__author__ = 'peter'

StockCursors = {'Normal': wx.CURSOR_ARROW, 'Hide': wx.CURSOR_BLANK, 'Bullseye': wx.CURSOR_BULLSEYE, 'Crosshairs': wx.CURSOR_CROSS, \
	'Hand': wx.CURSOR_HAND, 'Caret': wx.CURSOR_IBEAM, 'MouseLeft': wx.CURSOR_LEFT_BUTTON, 'Zoom': wx.CURSOR_MAGNIFIER, \
	'MouseMiddle': wx.CURSOR_MIDDLE_BUTTON, 'Stop': wx.CURSOR_NO_ENTRY, 'Paintbrush': wx.CURSOR_PAINT_BRUSH, 'Pencil': wx.CURSOR_PENCIL, \
	'<Arrow': wx.CURSOR_POINT_LEFT, '>Arrow': wx.CURSOR_POINT_RIGHT, 'Question': wx.CURSOR_QUESTION_ARROW, 'Flip': wx.CURSOR_RIGHT_ARROW, \
	'MouseRight': wx.CURSOR_RIGHT_BUTTON, '/Arrow': wx.CURSOR_SIZENESW, '|Arrow': wx.CURSOR_SIZENS, '\Arrow': wx.CURSOR_SIZENWSE, \
	'-Arrow': wx.CURSOR_SIZEWE, '+Arrow': wx.CURSOR_SIZING, 'Spraycan': wx.CURSOR_SPRAYCAN, 'Hourglass': wx.CURSOR_WAIT, 'Watch': wx.CURSOR_WATCH}

class ViewportMetaClass(type): # a class used to build a list of Viewport classes.
	# When a class with metaclass == this class is initialized, this class's __init__ procedure is run.
	ViewportClasses = [] # for list of Viewport classes

	def __init__(self, name, bases, dic):
		type.__init__(type, name, bases, dic)
		# add new Viewport class to the list, except the base class
		if not self.IsBaseClass:
			ViewportMetaClass.ViewportClasses.append(self)

class ViewportBaseClass(object, metaclass=ViewportMetaClass): # base class for all Viewports
	CanBeCreatedManually = True # whether user can be invited to create a Viewport of this class.
	IsBaseClass = True # needed by metaclass

	def __init__(self, **Args): # Args must include Proj, a ProjectItem instance. 'ID' is optional arg
		object.__init__(self)
		self.DisplDevice = None # which wx.Window object the Viewport is displayed on (needs to take a wx.DC)
		self.ID = Args.get('ID', None) # if no ID is supplied, it's assigned in CreateViewport()
		self.Proj = Args['Proj']
		self.PHAObjID = Args.get('PHAObjID', None) # storing ID, not the actual object, in case datacore isn't local
		self.Zoom = 1.0 # ratio of canvas coords to screen coords (absolute ratio, not %)
		self.PanX = self.PanY = 0 # offset of drawing origin, in screen coords
		self.OffsetX = self.OffsetY = 0 # offset of Viewport in display panel, in screen coords;
			# referenced in utilities.CanvasCoordsViewport() but not currently used
		self.C2DSocketREQ    = self.D2CSocketREP = None # zmq sockets for communication; set in CreateViewport()
		self.C2DSocketREQObj = self.D2CSocketREPObj = None # SocketInRegister instances matching In/OutwardSocket;
			# set in CreateViewport()
		# store Viewport to restore when this one is destroyed
		self.ViewportToRevertTo = Args.get('ViewportToRevertTo', None)
#		self.GotoMilestoneOnUndoCreate = None # a milestone instance to revert to, if creation of this Viewport is undone

#	method StoreViewportCommonDataInXML() is in module projects

def CreateViewport(Proj, ViewportClass, DisplDevice=None, PHAObj=None, DatacoreIsLocal=True, Fonts=[], ID=None, **Args):
	# Client side method.
	# create new Viewport instance of class ViewportClass in project Proj, and attach it to DisplDevice.
	# PHAObj: PHA object shadow to which the Viewport belongs, if any (None if the Viewport is project-wide)
	# DatacoreIsLocal (bool): whether datacore is in this instance of Vizop
	# Fonts: (dict) keys are strings such as 'SmallHeadingFont'; values are wx.Font instances
	# ID (str or None): if None, a new ID is fetched (but see FIXME below). If str, the supplied ID is used
	# Return the Viewport instance, and D2C and C2D socket numbers (2 x int)
	# Also returns VizopTalksArgs (dict of attrib: value; these are args to controlframe.SubmitVizopTalksMessage)
	# and VizopTalksTips (list of dicts, same as VizopTalksArgs)
	assert isinstance(DatacoreIsLocal, bool)
	assert (isinstance(ID, str) and bool(ID)) or (ID is None) # ensure any ID supplied is nonblank
	# prepare dict of args to send to new Viewport
	ArgsToSupply = Args
	ArgsToSupply.update({'DateChoices': core_classes.DateChoices})
	NewViewport = ViewportClass(Proj=Proj, PHAObjID=getattr(PHAObj, 'ID', None), ParentWindow=DisplDevice,
		DisplDevice=DisplDevice, Fonts=Fonts, ID=ID, **ArgsToSupply)
	# append the Viewport to the project's list
	Proj.ClientViewports.append(NewViewport)
	if ID is None:
		NewViewport.ID = str(Proj.GetNewID()) # generate unique ID; stored as str. FIXME this is getting ID from client side Proj!
	# assign default name to Viewport
	Proj.AssignDefaultNameToViewport(Viewport=NewViewport)
	# set up sockets for communication with the new Viewport:
	# D2C (Viewport to core) and C2D. Each socket has both REQ (send) and REP (reply) sides.
	D2CSocketNo = vizop_misc.GetNewSocketNumber()
	C2DSocketNo = vizop_misc.GetNewSocketNumber()
	# Then we fetch the socket numbers and make the corresponding sockets on the Viewport side.
	NewViewport.C2DSocketREQ, NewViewport.C2DSocketREQObj, C2DSocketNoReturned = vizop_misc.SetupNewSocket(SocketType='REQ',
		SocketLabel='C2DREQ_' + NewViewport.ID, PHAObj=PHAObj, Viewport=NewViewport,
		SocketNo=C2DSocketNo, BelongsToDatacore=False, AddToRegister=True)
	NewViewport.D2CSocketREP, NewViewport.D2CSocketREPObj, D2CSocketNoReturned = vizop_misc.SetupNewSocket(SocketType='REP',
		SocketLabel='D2CREP_' + NewViewport.ID, PHAObj=PHAObj, Viewport=NewViewport,
		SocketNo=D2CSocketNo, BelongsToDatacore=False, AddToRegister=True)
	# get args to send to SubmitVizopTalksMessage from Viewport, if available
	VizopTalksArgs = getattr(NewViewport, 'NewViewportVizopTalksArgs', {'MainText': '<No info provided by Viewport>'})
	VizopTalksTips = getattr(NewViewport, 'NewViewportVizopTalksTips', [])
	return NewViewport, D2CSocketNo, C2DSocketNo, VizopTalksArgs, VizopTalksTips

def ViewportClassWithName(TargetName):
	# returns the Viewport class with internal name = TargetName, or None if not found
	assert isinstance(TargetName, str)
	InternalNameList = [c.InternalName for c in ViewportMetaClass.ViewportClasses]
	if TargetName in InternalNameList:
		return ViewportMetaClass.ViewportClasses[InternalNameList.index(TargetName)]
	else: return None

#def ArchiveDestroyedViewport(Proj, ViewportShadow, PersistentAttribs={}):
	# redundant; now we keep the Viewport shadow in the project's main list
	# store a deleted Viewport shadow in Proj's list, to enable retrieval of persistent attributes if the Viewport is
	# re-created
	# If another Viewport of the same class is already in the archive list, replace the old one in the list with the new one
	# PersistentAttribs (dict): attribs to store in the Viewport shadow, to be restored if the Viewport is resurrected
	# return: EjectedViewportShadow (the old version removed from the list, or None), TargetIndex (int: index where
	# ViewportShadow is placed in the list); for undo
	# first, store persistent attribs in the ViewportShadow in case the Viewport is resurrected later
#	ViewportShadow.PersistentAttribs = PersistentAttribs
#	# check if there's another Viewport of the same class already in the archive
#	ExistingViewportClasses = [v.MyClass for v in Proj.ArchivedViewportShadows]
#	if ViewportShadow.MyClass in ExistingViewportClasses: # replace existing archived Viewport shadow
#		TargetIndex = ExistingViewportClasses.index(ViewportShadow.MyClass)
#		EjectedViewportShadow = Proj.ArchivedViewportShadows[TargetIndex] # keep the old one for undo
#		Proj.ArchivedViewportShadows[TargetIndex] = ViewportShadow # overwrite old one with new one
#	else: # no existing Viewport of this class; add it
#		Proj.ArchivedViewportShadows.append(ViewportShadow)
#		EjectedViewportShadow = None
#		TargetIndex = len(Proj.ArchivedViewportShadows) - 1 # index of archived ViewportShadow in list
#	return EjectedViewportShadow, TargetIndex

class GUIWidget(object): # superclass of all widgets that can be shown in iWindow modes
	# when instances are created, the widgets are created, but not assigned to sizer, and no event binding is done
	# this might be a 'parallel system' with class UIWidget in module controlframe. Consider merging.

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		object.__init__(self)
		self.Widget = None # associated widget object (eg wx.Button)
		self.Handler = Handler # handler routine for events associated with the widget (eg EVT_BUTTON)
		self.Events = Events # widget events that should be bound to the handler
		self.SizerPos = SizerPos # position of widget in sizer grid within relevant group of widgets
		self.SizerSpan = SizerSpan # how many columns and rows spanned in the sizer
		self.SizerFlag = SizerFlag # sizer-related flags to apply to the widget
		self.Visible = False # whether visible and assigned to a sizer

	def MakeVisible(self, Visible=True, Sizer=None): # make widget in/visible and add to/remove from Sizer, unless Sizer is None
		# currently not used
		if Visible:
			self.Visible = True
			if Sizer: Sizer.add(self.Widget, pos=self.SizerPos, span=self.SizerSpan, flag=self.SizerFlag)
			self.Widget.Show()
		else:
			self.Visible = False
			if Sizer: Sizer.detach(self.Widget)
			self.Widget.Hide()

	def DoPostCreateTasks(self): # do any tasks required after creation of widget
		self.Widget.Hide()

class StaticTextWidget(GUIWidget): # widget showing fixed text
	# args can include:
	# Text (str) - plain text to assign to widget
	# FontArgs (dict) - args to supply to FontInstance()

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.StaticText(ParentWindow, -1, args.get('Text', ''))
		# set default formatting
		self.Widget.SetFont(utilities.FontInstance(args.get('FontArgs', {})))
		self.DoPostCreateTasks()

class TextCtrlWidget(GUIWidget): # widget showing user-editable text
	# args can include:
	# Text (str) - plain text to assign to widget
	# FontArgs (dict) - args to supply to FontInstance()
	# WidgetFlags (int) - style flags to apply to widget (default: wx.TE_LEFT)

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.TextCtrl(ParentWindow, -1, value=args.get('Text', ''), style=args.get('WidgetFlags', wx.TE_LEFT))
		# set default formatting
		self.Widget.SetFont(utilities.FontInstance(args.get('FontArgs', {})))
		self.DoPostCreateTasks()

class ChoiceWidget(GUIWidget): # widget showing drop-down choice
	# args can include:
	# Choices (list of str) - choices to assign
	# DefaultIndex (int) - index of default choice in Choices
	# FontArgs (dict) - args to supply to FontInstance()

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.Choice(ParentWindow, -1, choices=args.get('Choices', [_('<Undefined>')]))
		# set default formatting and selection
		self.Widget.SetFont(utilities.FontInstance(args.get('FontArgs', {})))
		self.Widget.SetSelection(args.get('DefaultIndex', 0))
		self.DoPostCreateTasks()

class CheckboxWidget(GUIWidget): # widget showing checkbox
	# args can include:
	# Text (str) - plain text to assign to widget
	# DefaultState (bool) - default checked/unchecked state
	# FontArgs (dict) - args to supply to FontInstance()

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.CheckBox(ParentWindow, -1, label=args.get('Text', _('<Undefined>')))
		self.Widget.SetFont(utilities.FontInstance(args.get('FontArgs', {})))
		self.Widget.SetValue(args.get('DefaultState', False))
		self.DoPostCreateTasks()

class IntSpinboxWidget(GUIWidget): # widget showing textbox limited to integers, and up/down buttons
	# args can include:
	# Text (str) - plain text to assign to widget
	# DefaultValue, MinValue, MaxValue (int)
	# FontArgs (dict) - args to supply to FontInstance()

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.SpinCtrl(ParentWindow, -1, initial=args.get('DefaultValue', args.get('MinValue', 0)), min=args.get('MinValue', 0), max=args.get('MaxValue', 999),
			label=args.get('Text', _('<Undefined>')))
		self.Widget.SetFont(utilities.FontInstance(args.get('FontArgs', {})))
		self.DoPostCreateTasks()

class NormalButtonWidget(GUIWidget): # widget showing normal momentary button with text
	# args can include:
	# Text (str) - plain text to assign to button
	# FontArgs (dict) - args to supply to FontInstance()

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.Button(ParentWindow, -1, label=args.get('Text', _('<Undefined>')))
		self.Widget.SetFont(utilities.FontInstance(args.get('FontArgs', {})))
		self.DoPostCreateTasks()

class PanelWidget(GUIWidget): # widget containing a panel for rich text
	# args can include: (TBC)

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND, **args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **args)
		self.Widget = wx.Panel(ParentWindow, -1)
		# set default formatting
		self.DoPostCreateTasks()

class BitmapButtonWidget_UsingwxButton(GUIWidget): # widget showing button with image - using wx button widget
	# redundant?
	# args can include:
	# Toggle: whether it should be a ToggleButton
	# Image (wx.Bitmap): image to assign to button
	# PosXInCU, PosYInCU, PosXInPx, PosYInPx, SizeXInPx, SizeYInPx: parms for testing for mouse hit

	def ButtonBitmap(self, ImageName): # returns bitmap for button
		return wx.BitmapFromImage(art.ArtProvider().get_image(ImageName, (48, 48), conserve_aspect_ratio=True))

	def __init__(self, ParentWindow=None, Handler=None, Events=[], SizerPos=(0,0), SizerSpan=(1,1), SizerFlag=wx.EXPAND,
			Toggle=True, **Args):
		GUIWidget.__init__(self, ParentWindow, Handler, Events, SizerPos, SizerSpan, SizerFlag, **Args)
		if Toggle: ButtonClass = buttons.GenBitmapToggleButton
		else: ButtonClass = buttons.GenBitmapButton
		for (Parm, Default) in [('PosXInCU', 0), ('PosYInCU', 0), ('PosXInPx', 0), ('PosYInPx', 0),
				('SizeXInPx', 48), ('SizeYInPx', 48), ('IsLeft', False)]:
			setattr(self, Parm, Args.get(Parm, Default))
		self.Widget = ButtonClass(ParentWindow, -1, bitmap=self.ButtonBitmap(Args['Image']),
			pos=(self.ScreenPosX, self.ScreenPosY), size=(self.ScreenSizeX, self.ScreenSizeY))
		# set up bitmaps
		self.DoPostCreateTasks()

class BitmapButtonWidget(GUIWidget):  # widget showing button with image - not using wx button widget
	# args can include:
	# Toggle: whether it should be a ToggleButton
	# Image (wx.Bitmap): image to assign to button
	# PosXInCU, PosYInCU, PosXInPx, PosYInPx, SizeXInCU, SizeYInCU, SizeXInPx, SizeYInPx: parms for testing for mouse hit
	# IsLeft (bool): if it's a connect button, whether it's connecting from an object in the left column
	# ColIndex (int): index of FT column to left of inter-column strip containing the button

	def __init__(self, ArtProvider=None, ImageName='', Toggle=True, **Args):
		# ArtProvider: an art.ArtProvider object
		object.__init__(self)
		for (Parm, Default) in [('PosXInCU', 0), ('PosYInCU', 0), ('PosXInPx', 0), ('PosYInPx', 0),
								('ScreenSizeX', 48), ('ScreenSizeY', 48), ('IsLeft', False), ('ColIndex', None)]:
			setattr(self, Parm, Args.get(Parm, Default))
		# set up bitmaps
		self.ImageNoZoom = {'Default': ArtProvider.get_image(name=ImageName, size=None)}
		self.SizeXInCU, self.SizeYInCU = self.ImageNoZoom['Default'].GetSize()
		print("DU234 button bitmap original size: ", self.SizeXInCU, self.SizeYInCU)
		self.BitmapZoomLevel = 1.0
		self.BitmapZoomed = {} # keys should match keys of self.ImageNoZoom
		self.ChangeZoom(NewZoom=1.0) # set bitmap in self.BitmapZoomed
		self.Status = 'Default' # whether the button is pressed/unpressed, etc. Matches one of keys of self.ImageNoZoom

	def ChangeZoom(self, NewZoom): # recalculate button bitmaps for new zoom level, and set self.BitmapZoomLevel
		assert isinstance(NewZoom, float)
		for Status in self.ImageNoZoom:
			self.BitmapZoomed[Status] = wx.BitmapFromImage(art.ZoomedImage(self.ImageNoZoom[Status], NewZoom))
		self.BitmapZoomLevel = NewZoom

	def Draw(self, DC, Zoom, **Args): # render the button in DC. No additional args required
		# work out whether to resize button bitmaps
		if Zoom != self.BitmapZoomLevel: self.ChangeZoom(Zoom)
		DC.DrawBitmap(self.BitmapZoomed.get(self.Status, self.BitmapZoomed['Default']), self.PosXInCU * Zoom,
			self.PosYInCU * Zoom, useMask=False)

def ActivateWidgetsInPanel(Widgets=[], Sizer=None, ActiveWidgetList=[], DefaultFont=None,
		HighlightBkgColour=None, **Args):
	# activate widgets that are about to be displayed in a panel: put them in Sizer, bind event handlers, and register
	# keyboard shortcuts
	# Args may contain TextWidgets (list of text widgets to check for loss of focus in OnIdle) (currently not used)
	assert isinstance(Widgets, list)
	assert isinstance(Sizer, wx.GridBagSizer)
	assert isinstance(ActiveWidgetList, list)
	# set up widgets in their sizer
	PopulateSizer(Sizer=Sizer, Widgets=Widgets, ActiveWidgetList=ActiveWidgetList,
		DefaultFont=DefaultFont, HighlightBkgColour=HighlightBkgColour)
	# set widget event handlers for active widgets
	global KeyPressHash
	for ThisWidget in ActiveWidgetList:
		if ThisWidget.Handler:
			for Event in ThisWidget.Events:
				ThisWidget.Widget.Bind(Event, ThisWidget.Handler)
		# set keyboard shortcuts
		# TODO rethink where KeyPressHash should be stored, maybe in RegisterKeyPressHandler; same issue in
		# DeactivateWidgetsInPanel
		if getattr(ThisWidget, 'KeyStroke', None): pass
#			KeyPressHash = vizop_misc.RegisterKeyPressHandler(
#				KeyPressHash, ThisWidget.KeyStroke, ThisWidget.Handler, getattr(ThisWidget, 'KeyPressHandlerArgs', {}))

def DeactivateWidgetsInPanel(Widgets=[], HideAllWidgets=False, **Args):
	# deactivate widgets that are ceasing to be displayed in a panel of the Control Frame
	# This method does 3 things:
	# 1. All widgets in Widgets (UIWidget instances) are unbound from their event handlers
	# 2. Disable any keyboard shortcuts registered for the widgets
	# 3. If HideAllWidgets is True, all widgets are hidden
	assert isinstance(Widgets, list)
	assert isinstance(HideAllWidgets, bool)
	# unbind widget event handlers
	assert isinstance(Widgets, list)
	global KeyPressHash
	for ThisWidget in Widgets:
		# 1. unbind event handler
		if ThisWidget.Handler:
			for Event in ThisWidget.Events:
				ThisWidget.Widget.Unbind(Event)
		# 2. disable keyboard shortcut
		if getattr(ThisWidget, 'KeyStroke', None): pass
#			KeyPressHash = vizop_misc.UnregisterKeyPressHandler(KeyPressHash, ThisWidget.KeyStroke)
		# 3. hide widget
		if HideAllWidgets: ThisWidget.Widget.Hide()

class ZoomWidgetObj(object):
	# widget allowing user to control zoom of a Viewport
	AngleAtPointerMin = 4.01 # 230deg in radians; 7 o'clock
	AngleAtPointerMid = 1.57 # 90deg in radians; 12 o'clock
	AngleAtPointerMax = 5.24 # 300 deg in radians; 5 o'clock
	Mid2MinAngleRange = AngleAtPointerMid - AngleAtPointerMin
	Mid2MaxAngleRange = (6.28 + AngleAtPointerMid) - AngleAtPointerMax # 2pi added, as angle range wraps
	BestMousePointerForSelecting = 'Zoom' # should be a key of StockCursors
	PosZ = 100 # z-coordinate of FloatLayer containing the zoom widget
	MinZoomLimit = 1e-5 # absolute limits of zoom value
	MaxZoomLimit = 1e5

	def __init__(self, Viewport=None, PosXInPx=0, PosYInPx=0, InitialZoom=1.0, MaxZoom=5.0, MidZoom=1.0, MinZoom=0.2, SizeY=50):
		# Viewport: instance of a subclass of ViewportBaseClass
		# PosXInPx, PosYInPx (2 x int): Centre position in pixels relative to panel
		# InitialZoom (float): initial zoom setting to show
		# MaxZoom, MinZoom (floats): max and min zoom values to allow; must be either side of 1.0
		# MidZoom (float): zoom value at centre point of widget
		# SizeY (int): height of widget in pixels
		assert isinstance(Viewport, ViewportBaseClass)
		assert isinstance(InitialZoom, (int, float))
		assert isinstance(MaxZoom, (int, float))
		assert isinstance(MinZoom, (int, float))
		assert ZoomWidgetObj.MinZoomLimit < MinZoom < InitialZoom < MaxZoom < ZoomWidgetObj.MaxZoomLimit
		assert MinZoom < MidZoom < MaxZoom
		assert isinstance(SizeY, int)
		object.__init__(self)
		self.Viewport = Viewport
		self.CurrentZoom = float(InitialZoom)
		self.MaxZoom = float(MaxZoom)
		self.MidZoom = float(MidZoom)
		self.MinZoom = float(MinZoom)
		self.LogMaxZoom = math.log10(self.MaxZoom)
		self.LogMidZoom = math.log10(self.MidZoom)
		self.LogMinZoom = math.log10(self.MinZoom)
		self.Mid2MinZoomRange = math.log10(MidZoom / MinZoom)
		self.Mid2MaxZoomRange = math.log10(MidZoom / MaxZoom)
		self.Status = 'Idle' # can be 'Idle', 'Zooming'
		# set positions, sizes and colours of components
		# if the widget gets repositioned, change values of self.RingCentreX/Y and self.DotPosX/Y
		self.SizeXInPx = self.SizeYInPx = SizeY
		self.HalfSizeXInPx = self.SizeXInPx / 2
		self.HalfSizeYInPx = self.SizeYInPx / 2
		self.FloatLayer = FloatLayer(Bitmap=wx.Bitmap.FromRGBA(width=self.SizeXInPx, height=self.SizeYInPx),
			PosXInPx=PosXInPx, PosYInPx=PosYInPx, PosZ=ZoomWidgetObj.PosZ)
		self.SetPos(PosXInPx, PosYInPx) # sets self.RingCentreX/Y and self.DotPosX/Y
		self.RingRadius = int(SizeY * 0.4)
		self.PointerRadius = int(SizeY * 0.5) # distance of pointer tip from centre of ring
		self.PointerBaseRadius = int(SizeY * 0.3) # distance from ring centre to pointer base
		self.PointerHalfAngle = 0.4 # half-angle of spread of base of pointer
		self.DotPosXRelative = [int(Frac * self.SizeXInPx) for Frac in (-0.2, -0.05, 0.15)] # dot centres relative to widget centre
		self.DotPosYRelative = [int(Frac * self.SizeYInPx) for Frac in (0.0, 0,0, 0,0)]
		self.DotRadii = [int(Frac * SizeY) for Frac in (0.05, 0.07, 0.11)]
		self.RingFillColour = {'Idle': (0x87, 0x18, 0x44), 'Zooming': (0xee, 0x28, 0x82)} # shades of plum.
			# keys match values of self.Status
		self.RingEdgeColour = (0xff, 0x3e, 0x8b) # coral
		self.RingEdgeThickness = 1
		self.PointerColourRight = (0xed, 0xbc, 0xcf) # blush white
		self.PointerColourLeft = (0xed, 0xd1, 0xdc) # lighter blush white
		self.DotColour = (0xbd, 0x86, 0x9c) # grey-pink

	def SetPos(self, PosXInPx, PosYInPx): # set widget position in pixels relative to panel
		self.PosXInPx = PosXInPx
		self.PosYInPx = PosYInPx
		self.LeftXInPx = PosXInPx # used to test for mouse hit
		self.RightXInPx = PosXInPx + self.SizeXInPx
		self.TopYInPx = PosYInPx
		self.BottomYInPx = PosYInPx + self.SizeYInPx
		self.RingCentreX = PosXInPx
		self.RingCentreY = PosYInPx
		self.FloatLayer.PosXInPx = PosXInPx # set layer drawing position
		self.FloatLayer.PosYInPx = PosYInPx

	def SetZoom(self, TargetZoom): # set zoom value of widget (does not redraw it)
		assert isinstance(TargetZoom, (int, float))
		assert (0.999 * self.MinZoom) < TargetZoom < (self.MaxZoom * 1.001) # allowing for rounding errors
		self.CurrentZoom = float(TargetZoom)

	def DrawInBitmap(self): # draw zoom widget in own bitmap
		# set StartX/Y, the position of the widget centre
		StartX = self.HalfSizeXInPx
		StartY = self.HalfSizeYInPx
		DC = wx.MemoryDC(self.FloatLayer.Bitmap)
		# clear bitmap to transparent
		DC.SetBackground(wx.Brush(wx.Colour(0, 0, 0, 0))) # TRANSPARENT_BRUSH and BRUSHSTYLE_TRANSPARENT not working here
		DC.Clear()
		# draw ring
		DC.SetPen(wx.Pen(self.RingEdgeColour, width=self.RingEdgeThickness))
		DC.SetBrush(wx.Brush(self.RingFillColour[self.Status]))
		DC.DrawCircle(x=StartX, y=StartY, radius=self.RingRadius)
		# draw dots in the ring
		DC.SetPen(wx.Pen(self.DotColour))
		DC.SetBrush(wx.Brush(self.DotColour))
		for ThisDotIndex in range(len(self.DotRadii)):
			DC.DrawCircle(x=StartX + self.DotPosXRelative[ThisDotIndex], y=StartY + self.DotPosYRelative[ThisDotIndex],
				radius=self.DotRadii[ThisDotIndex])
		# calculate pointer angle (anticlockwise from east)
		if self.CurrentZoom < self.MidZoom: # pointer to left of 12 o'clock
			PointerAngle = ZoomWidgetObj.AngleAtPointerMin +\
				( ((math.log10(self.CurrentZoom / self.MinZoom)) / self.Mid2MinZoomRange) * ZoomWidgetObj.Mid2MinAngleRange)
		else: # pointer to right of 12 o'clock
			PointerAngle = ZoomWidgetObj.AngleAtPointerMax +\
				( (math.log10(self.CurrentZoom / self.MaxZoom) / self.Mid2MaxZoomRange) * ZoomWidgetObj.Mid2MaxAngleRange)
		# calculate pointer tip coords
		CosPointerAngle = math.cos(PointerAngle)
		SinPointerAngle = math.sin(PointerAngle)
		PointerTipX = StartX + (self.PointerRadius * CosPointerAngle)
		PointerTipY = StartY - (self.PointerRadius * SinPointerAngle)
		# calculate pointer base coords: left, centre and right
		PointerBaseLAngle = PointerAngle + self.PointerHalfAngle
		PointerBaseRAngle = PointerAngle - self.PointerHalfAngle
		PointerBaseLX = StartX + (self.PointerBaseRadius * math.cos(PointerBaseLAngle))
		PointerBaseLY = StartY - (self.PointerBaseRadius * math.sin(PointerBaseLAngle))
		PointerBaseCX = StartX + (self.PointerBaseRadius * CosPointerAngle)
		PointerBaseCY = StartY - (self.PointerBaseRadius * SinPointerAngle)
		PointerBaseRX = StartX + (self.PointerBaseRadius * math.cos(PointerBaseRAngle))
		PointerBaseRY = StartY - (self.PointerBaseRadius * math.sin(PointerBaseRAngle))
		# draw pointer: left half
		DC.SetPen(wx.Pen(self.PointerColourLeft))
		DC.SetBrush(wx.Brush(self.PointerColourLeft))
		DC.DrawPolygon( [(PointerTipX, PointerTipY), (PointerBaseLX, PointerBaseLY), (PointerBaseCX, PointerBaseCY)] )
		# draw pointer: right half
		DC.SetPen(wx.Pen(self.PointerColourRight))
		DC.SetBrush(wx.Brush(self.PointerColourRight))
		DC.DrawPolygon( [(PointerTipX, PointerTipY), (PointerBaseRX, PointerBaseRY), (PointerBaseCX, PointerBaseCY)] )

	def GetSize(self): # returns (SizeX, SizeY) of widget in pixels
		return self.SizeXInPx, self.SizeYInPx

	def MouseHit(self, MouseXInPx, MouseYInPx, TolXInPx, TolYInPx):
		# returns (str) hotspot hit in widget instance, or None if not hit
		# Hotspots can be: "Whole" (whole object hit)
		# Currently, this is the same as in class FTBoxyObject
		assert isinstance(MouseXInPx, (float, int))
		assert isinstance(MouseYInPx, (float, int))
		assert isinstance(TolXInPx, (float, int))  # mouse hit tolerance in pixels
		assert isinstance(TolYInPx, (float, int))
		# test if hotspot "Whole" hit
		if (MouseXInPx + TolXInPx >= self.LeftXInPx) and (MouseYInPx + TolYInPx >= self.TopYInPx) and \
				(MouseXInPx - TolXInPx <= self.RightXInPx) and \
				(MouseYInPx - TolYInPx <= self.BottomYInPx):
			return "Whole"
		else:
			return None

	def HandleMouseLClickOnMe(self, HitHotspot='Whole', HostViewport=None, MouseX=0, MouseY=0, **Args):
		# handle mouse left button down inside zoom widget at coords MouseX, MouseY (2 x int) in pixels relative to panel
		# Ends by calling HostViewport.RefreshZoomWidget() with bitmap containing redrawn widget as arg
		# No args required in Args
		self.MouseLDownX = MouseX
		self.MouseLDownY = MouseY # capture coords of original mouse down position
		self.MouseLastX = MouseX # capture coords of last seen mouse position (used in HandleMouseLDrag)
		self.MouseLastY = MouseY
		self.LogMouseLDownZoom = math.log10(self.CurrentZoom)
		self.Status = 'Zooming'
		HostViewport.RefreshZoomWidget(StillZooming=True)

	def HandleMouseLDragOnMe(self, MouseX=0, MouseY=0, FullZoomRange=40000, HostViewport=None, **Args):
		# handle mouse drag with left button down to new coords MouseX, MouseY (2 x int) in pixels relative to panel
		# This procedure only sets self.CurrentZoom; it doesn't redraw the widget.
		# FullZoomRange (int): square of number of mouse pixels dragged that corresponds to zooming from MidZoom to Min or Max.
		# First, calculate square of number of pixels' distance from mouse drag start position to current position
		# Calculate positive and negative zoom contributions separately
		SqrPixelsDraggedPos = max(0, MouseX - self.MouseLDownX)**2 + max(0, MouseY - self.MouseLDownY)**2
		SqrPixelsDraggedNeg = min(0, MouseX - self.MouseLDownX)**2 + min(0, MouseY - self.MouseLDownY)**2
		ZoomFraction = max(-FullZoomRange, min(FullZoomRange, SqrPixelsDraggedPos - SqrPixelsDraggedNeg)) / FullZoomRange
		# calculate new zoom; based on initial click coords = starting zoom, stored in LogMouseLDownZoom
		if ZoomFraction > 0:
			self.CurrentZoom = 10 ** ((ZoomFraction * self.LogMaxZoom) + (self.LogMouseLDownZoom * (1.0 - ZoomFraction)))
		else:
			self.CurrentZoom = 10 ** ((-ZoomFraction * self.LogMinZoom) + (self.LogMouseLDownZoom * (1.0 + ZoomFraction)))
		# constrain zoom within min and max for HostViewport
		self.CurrentZoom = min(HostViewport.MaxZoom, max(HostViewport.MinZoom, self.CurrentZoom))
		HostViewport.RedrawDuringZoom(NewZoom=self.CurrentZoom)

	def HandleMouseLDragEndOnMe(self, MouseX=0, MouseY=0, HostViewport=None, **Args):
		# handle mouse left button up after clicking (and maybe dragging) on zoom widget
		# Args may include Dragged (bool) - whether mouse was dragged with L button down
		# returns bitmap containing redrawn widget
		self.Status = 'Idle'
		HostViewport.RefreshZoomWidget(StillZooming=False)

	def HandleMouseLDClickOnMe(self, HostViewport=None, **Args):
		# handle mouse left double click on zoom widget: reset zoom to MidZoom (usually 100%)
		self.CurrentZoom = self.MidZoom
		self.Status = 'Idle' # ensures zoom widget colour remains normal
		HostViewport.RedrawDuringZoom(NewZoom=self.CurrentZoom)

	def HandleMouseWheel(self, Event=None, HostViewport=None, **Args):
		# handle mouse wheel event to zoom. Emulates a click and Y-drag on the zoom tool
		WheelToPixelConversionFactor = 50 # sets the zoom sensitivity
		InitialMouseX, InitialMouseY = Event.GetPosition()
		self.HandleMouseLClickOnMe(HostViewport=HostViewport, MouseX=InitialMouseX, MouseY=InitialMouseY)
		VirtualNewMousePositionY = InitialMouseY + (math.copysign(1, Event.GetWheelRotation()) \
			* WheelToPixelConversionFactor * math.log10(abs(Event.GetWheelRotation())))
		self.HandleMouseLDragOnMe(MouseX=InitialMouseX, MouseY=VirtualNewMousePositionY, HostViewport=HostViewport, **Args)
		self.HandleMouseLDragEndOnMe(MouseX=InitialMouseX, MouseY=VirtualNewMousePositionY, HostViewport=HostViewport, **Args)

def SetPointer(Viewport, DisplayDevice, Event, Mode='Select'): # set required mouse pointer style
	# Event is mouse event, if called as an event handler, else None
	# Mode is 'Select' (can only de/select PHA object), (others to be added)
	if Viewport: # any Viewport exists?
		if Event:
			(ScreenX, ScreenY) = Event.GetPosition() # get mouse coords if called as event handler. See Rappin p150
		else: (ScreenX, ScreenY) = wx.GetMousePosition() # if called directly
		# find out whether we are over any object
		(ObjOver, Hotspot) = FindObjectAt(Viewport, ScreenX, ScreenY, DisplayDevice, HandleSelection='Any')
		if (ObjOver is None): # set default mouse pointer
			wx.SetCursor(wx.Cursor(StockCursors['Normal']))
		else: # set mouse pointer according to hotspot
			if (Mode in ['Select', 'Edit']):
				wx.SetCursor(wx.Cursor(StockCursors[ObjOver.BestMousePointerForSelecting]))
			elif (Mode == 'Widgets'): # set normal pointer for interaction with wx widgets
				wx.SetCursor(wx.Cursor(StockCursors['Normal']))
			elif (Mode == 'Blocked'): # user cannot interact with the Viewport
				wx.SetCursor(wx.Cursor(StockCursors['Stop']))
			else: print("Oops, invalid mouse move mode '%s' requested (problem code DU356). This is a bug; please report it" % Mode)
	else: # no Viewport; set default pointer
		wx.SetCursor(wx.Cursor(StockCursors['Normal']))

def FindObjectAt(Viewport, ScreenX, ScreenY, DisplayDevice, VisibleOnly=True, HandleSelection='Only-Selected'):
	# returns (first visible object instance hit, [hotspots hit in the object]) at screen coords ScreenX/Y in DisplayDevice given
	# If VisibleOnly, only checks visible objects
	# HandleSelection can be: 'Only-Selected' (returns only selected object at the location),
	# 'Any' (returns the object at the location, irrespective of selection),
	# 'Prefer-Selected' (returns selected object at the location, if any; otherwise, returns same as 'Any')

	def FirstHitAmong(ObjList, X, Y): # return first element in ElList that's hit at canvas coords X, Y; or None if no hits
		HotSpotHit = []
		ObjIndex = 0
		while (ObjIndex < len(ObjList)) and not HotSpotHit:
			HotSpotHit = ObjList[ObjIndex].MouseHit(CanvasX, CanvasY, DisplayDevice.TolXInPx, DisplayDevice.TolYInPx)
			ObjIndex += 1
		if HotSpotHit: return (ObjList[ObjIndex-1], HotSpotHit)
		else: return (None, []) # no hit found

	# main procedure for FindObjectAt() begins
	assert isinstance(Viewport, ViewportBaseClass)
	assert isinstance(ScreenX, (int, float))
	assert isinstance(ScreenY, (int, float))
	assert isinstance(DisplayDevice, wx.Window) # TODO should be more specific
	assert isinstance(VisibleOnly, bool)
	assert HandleSelection in ('Only-Selected', 'Prefer-Selected', 'Any')
	# get canvas coords of position under test
	CanvasX, CanvasY = utilities.CanvasCoordsViewport(Viewport, ScreenX, ScreenY)
	Hit = (None, [])
	if (HandleSelection in ['Only-Selected', 'Prefer-Selected']): # check selected objects first
		Hit = FirstHitAmong([Obj for Obj in Viewport.AllClickableObjects(SelectedOnly=True)], CanvasX, CanvasY, VisibleOnly)
	# check nonselected objects, if required
	if ((HandleSelection == 'Prefer-Selected') and (not Hit[0])) or (HandleSelection == 'Any'):
		Hit = FirstHitAmong([Obj for Obj in Viewport.AllClickableObjects(SelectedOnly=True, VisibleOnly=VisibleOnly)], CanvasX, CanvasY)
	return Hit

class FloatLayer(object):  # floating layer objects containing parts of the Viewport image

	def __init__(self, Bitmap=None, PosXInPx=0, PosYInPx=0, PosZ=1):
		# Bitmap: the bitmap that will be overlaid onto the Viewport bitmap. Already zoomed as appropriate
		# PosX/YInPx: offset of Bitmap relative to display device
		# PosZ: z-coordinate of Bitmap. Higher PosZ will be overlaid on top of lower PosZ.
		assert isinstance(Bitmap, wx.Bitmap)
		assert isinstance(PosXInPx, (int, float))
		assert isinstance(PosYInPx, (int, float))
		assert isinstance(PosZ, int)
		assert PosZ > 0
		object.__init__(self)
		self.Bitmap = Bitmap
		self.PosXInPx = int(round(PosXInPx))
		self.PosYInPx = int(round(PosYInPx))
		self.PosZ = PosZ


class UIWidgetItem(object):
	# These objects contain widgets for display, with associated info needed for use in flex grid sizers
	# Optional attributes for instances:
	#	SkipLoseFocus (bool): (for TextCtrl and ExpandoTextCtrl widgets) Ignore me when I lose focus, i.e. don't call my handler
	#	HideMethod (callable): method to hide self.Widget. Defaults to Widget.Hide
	#	ShowMethod (callable): method to show (unhide) self.Widget. Defaults to Widget.Show
	#	SetFontMethod (callable): method to set widget's font. Defaults to Widget.SetFont
	#	IsInSizer (bool): whether to add the widget to the main sizer for the panel. Defaults to True

	def __init__(self, Widget, **Attrs):
		object.__init__(self)
		self.Handler = None # procedure that handles user changes of data in the widget
		self.Events = [] # wx events to bind to Handler
		self.ColLoc = 0 # in which sizer column to insert the widget
		self.RowSpan = 1 # how many rows and columns occupied by the widget in the sizer
		self.ColSpan = 1
		self.ShiftDown = 0 # rows to shift this widget down by. Used to allow multiple widgets alongside one with RowSpan > 1
		self.NewRow = False # whether this widget should start a new row
		self.RowOffset = 0 # these offset attribs can be adjusted to make the widget insert into a different sizer cell
		self.ColOffset = 0
		self.LeftMargin = 0 # gap, in pixels, inside the sizer cell on the left
		self.MinSizeX = None # fixed X/Y size of widget in pixels. If either is None, sizer sets widget size.
		self.MinSizeY = None # Unless MinSizeX and MinSizeY are both set, they will be ignored.
			# MinSizeX/Y currently implemented in result panel but not in data entry panel
		self.GapX = self.GapY = 0 # space to insert: GapX is to the left (counts as a sizer column), GapY is below this widget
		self.Flags = wx.EXPAND # flags to apply when adding the widget to a sizer
		self.Widget = Widget # the wx widget itself
		self.Lifespan = 'Permanent' # whether the widget is created on demand and should be destroyed when removed
			# from the sizer. Can be 'Permanent', 'Destroy' (destroy when removed from sizer)
		self.DisplayMethod = None # method name for displaying the data (str)
		self.IsNumber = False # whether to treat as a number when displaying (if False, treated as a string)
		self.PermissibleValues = [] # list of values that can be returned by a Choice widget. These must be the internal
			# values, not the human names (because these might be translated)
		self.ReadOnly = False # whether changes to the attrib value are disallowed
		self.IsVisible = True # (bool) whether widget should be displayed on screen. If False, no empty placeholder is left
			# Possible gotcha: if IsVisible is False and NewRow is True, the new row won't be started (FIXME)
		self.NeedsHighlight = False # whether widget should have background highlight next time it is drawn
		self.PHAObj = None # PHA object containing DataAttrib (below)
		self.DataAttrib = None # (None or str) name of attrib in related PHA object whose data this widget displays
		self.Font = None
		self.HideMe = Attrs.get('HideMethod', getattr(self.Widget, 'Hide', None)) # get method to hide widget. Certain widgets such as
			# sizers need a method other than self.Hide(). The getattr is needed because, unfortunately,
			# get() evaluates its 2nd arg even when not required
		self.ShowMe = Attrs.get('ShowMethod', getattr(self.Widget, 'Show', None)) # get method to show widget
		self.SetFontMethod = Attrs.get('SetFontMethod', getattr(self.Widget, 'SetFont', None))
		self.HideMe()
		self.IsInSizer = Attrs.get('IsInSizer', True)
		# set values of attributes provided
		for (Attr, Value) in Attrs.items():
			setattr(self, Attr, Value)
		# copy any DataAttrib value into the wx widget, for easier access in widget handlers
		if self.DataAttrib: self.Widget.DataAttrib = self.DataAttrib

	def SetMyFont(self, DefaultFont=None): # set font used to display widget value
		if getattr(self, 'Font', None) is not None:
			assert isinstance(self.Font, wx.Font)
			self.SetFontMethod(self.Font)
		elif DefaultFont: # use default font, if provided
			assert isinstance(DefaultFont, wx.Font)
			self.SetFontMethod(DefaultFont)

	def StaticHeader(self, **Args): # rendering method for UIWidgets containing headers that don't need to be populated
		self.SetMyFont(DefaultFont=Args.get('Font', None))

	def StaticFromText(self, DataObj, **Args): # put string or number value directly in StaticText or TextCtrl widgets
		# Warning: this will break because StringFromNum() call is missing its RR arg; similar issue with GetMyStatus()
		# and values returned from GetMyStatus() are out of date (now NumProblemValue instances)
		TargetValue = getattr(DataObj, self.DataAttrib, None)
		if TargetValue is not None: # attrib exists
			if self.IsNumber: # treat as number
				if TargetValue.GetMyStatus(RR=RR) == 'ValueStatus_Unset': # number not defined
					StringToDisplay = _('Value not defined')
				else: StringToDisplay = StringFromNum(TargetValue)
			else: # convert directly to str (for attribs that aren't already strings, eg int)
				StringToDisplay = str(TargetValue)
		else: # attrib doesn't exist
			StringToDisplay = _('Attrib not defined')
		# use appropriate method to populate wxwidget
		if isinstance(self.Widget, wx.StaticText):
			self.Widget.SetLabel(StringToDisplay)
		else: self.Widget.SetValue(StringToDisplay)
		self.SetMyFont(DefaultFont=Args.get('Font', None))

class UIWidgetPlaceholderItem(object):
	# instances of this class are placeholders in a list of UIWidgetItem instances to indicate where to insert variable
	# widgets
	def __init__(self, Name='', **Attrs):
		# Name (str): identifier used by InsertVariableWidgets() to find insertion point for variable widgets
		assert isinstance(Name, str)
		assert len(Name) > 0
		object.__init__(self)
		self.Name = Name

def StringFromNum(InputNumber, RR):
	# returns correctly formatted string representation of InputNumber
	# (NumValueItem instance), taking the number object's attribs Sci and Decimals into account
	# Uses info.SciThresholdUpper/Lower (int, float or None): if the absolute value of InputNumber ≥ SciThreshold,
	# scientific notation will be used
	# First, check if value is available
	ValueStatus = InputNumber.GetMyStatus(RR=RR)
	if ValueStatus == core_classes.NumProblemValue_NoProblem: # it's available
		return InputNumber.GetDisplayValue(RR=RR, SciThresholdUpper=info.SciThresholdUpper,
			SciThresholdLower=info.SciThresholdLower)
	elif ValueStatus == core_classes.NumProblemValue_UndefNumValue: # it's not defined
		return _('Not set')
	else: # return 'cannot get value' indicator
		return info.CantDisplayValueOnScreen

class BaseGridTable(wx.grid.GridTableBase): # object containing underlying data table for a grid display of data

	def __init__(self, Log, ColumnInternalNames=[]):
		# ColumnInternalNames: list of str, internal names (not display names) of grid table columns
		wx.grid.GridTableBase.__init__(self)
		self.Log = Log
		self.identifiers = ColumnInternalNames # internal names of columns
		self.rowLabels = []
		self.colLabels = []
		self.data = []

	def GetNumberRows(self): # required method for this class
		return len(self.data)

	def GetNumberCols(self): # required method for this class
		return len(self.identifiers)

	def IsEmptyCell(self, Row, Col): # required method for this class
		assert isinstance(Row, int)
		assert isinstance(Col, int)
		assert 0 <= Row < self.GetNumberRows()
		assert 0 <= Col < self.GetNumberCols()
		return not self.data[Row][self.identifiers[Col]]

	def GetValue(self, Row, Col): # required method for this class
		assert isinstance(Row, int)
		assert isinstance(Col, int)
		if not (0 <= Row < self.GetNumberRows()): print("DU388 row: ", Row, type(Row)) # debugging
		assert 0 <= Row < self.GetNumberRows() + 1 # +1 needed in case user drags a row to the bottom of the table
		assert 0 <= Col < self.GetNumberCols()
		return self.data[Row][self.identifiers[Col]]

	def SetValue(self, Row, Col, Value): # required method for this class
		assert isinstance(Row, int)
		assert isinstance(Col, int)
		assert 0 <= Row < self.GetNumberRows()
		assert 0 <= Col < self.GetNumberCols()
		self.data[Row][self.identifiers[Col]] = Value

	def GetRowLabelValue(self, Row):
		assert isinstance(Row, int)
		assert 0 <= Row
		return self.rowLabels[Row]

	def GetColLabelValue(self, Col):
		assert isinstance(Col, int)
		assert 0 <= Col < self.GetNumberCols()
		return self.colLabels[Col]

	def MoveColumn(self, FromColNo, ToColNo):
		assert isinstance(FromColNo, int)
		assert isinstance(ToColNo, int)
		assert 0 <= FromColNo < self.GetNumberCols()
		assert 0 <= ToColNo < self.GetNumberCols()
		# move column identifier in the list
		self.identifiers.insert(ToColNo, self.identifiers.pop(FromColNo))
		# notify grid of change
		ThisGrid = self.GetView()
		ThisGrid.BeginBatch()
		ThisGrid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, FromColNo, 1))
		ThisGrid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_COLS_INSERTED, ToColNo, 1))
		ThisGrid.EndBatch()

	def MoveRow(self, FromRowNo, ToRowNo):
		assert isinstance(FromRowNo, int)
		assert isinstance(ToRowNo, int)
		assert 0 <= FromRowNo < self.GetNumberRows()
		assert 0 <= ToRowNo < self.GetNumberRows() + 1 # +1 in case the row is dragged to the bottom of the table
		# notify grid of change
		ThisGrid = self.GetView()
		ThisGrid.BeginBatch()
		ThisGrid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, FromRowNo, 1))
		ThisGrid.ProcessTableMessage(wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_INSERTED, ToRowNo, 1))
		ThisGrid.EndBatch()

class DraggableGrid(wx.grid.Grid): # wx.grid object whose rows can be reordered by dragging

	def __init__(self, Parent, Log=stdout, Viewport=None, ColumnInternalNames=[]):
		assert isinstance(Viewport, ViewportBaseClass)
		wx.grid.Grid.__init__(self, Parent, -1)
		self.Viewport = Viewport
		self.DataTable = BaseGridTable(Log, ColumnInternalNames=ColumnInternalNames) # create a data table object
		self.SetTable(self.DataTable, True, selmode=wx.grid.Grid.SelectRows) # can select rows, but not individual cells
		# enable columns to be dragged to reorder (not currently used)
		# wx.lib.gridmovers.GridColMover(self)
		# self.Bind(wx.lib.gridmovers.EVT_GRID_COL_MOVE, self.OnColMove, self)
		# enable rows to be dragged to reorder (TODO add this function later)
#		wx.lib.gridmovers.GridRowMover(self) # keep these 2 lines for later
#		self.Bind(wx.lib.gridmovers.EVT_GRID_ROW_MOVE, self.OnRowMove, self)
		self.DisableCellEditControl() # disallow direct editing of cells
		# send events to parent window (e.g. data panel) for processing, if parent has a handler
		if hasattr(self.Viewport, 'OnGridMouseDoubleLClick'):
			self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.Viewport.OnGridMouseDoubleLClick)
		if hasattr(self.Viewport, 'OnGridRangeSelect'):
			self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.Viewport.OnGridRangeSelect)

	def OnColMove(self, Event): # handle dragging of table column (not currently used?)
		self.GetTable().MoveColumn(Event.GetMoveColumn(), Event.GetBeforeColumn())

	def OnRowMove(self, Event): # handle dragging of table row
		self.GetTable().MoveRow(Event.GetMoveRow(), Event.GetBeforeRow())
		# call row move handler in the hosting panel (currently DataEntryPanel)
		if hasattr(self.Viewport, 'OnMoveGridRow'):
			self.Viewport.OnMoveGridRow(Event, FromRowIndex=Event.GetMoveRow(), ToRowIndex=Event.GetBeforeRow())

class ColourSchemeItem(object):
	# defines a colour scheme to apply to all Viewports. So far, we just assign a default set of colours
	def __init__(self):
		object.__init__(self)
		# each colour scheme needs to contain a colour for every well (imagine wells on an artist's palette)
		self.BackBright = (0xa6, 0xd6, 0xc1)
		self.BackMid = (0x76, 0xa6, 0x99)
		self.ButtonLive = (0xF0, 0xFF, 0x00) # yellow; for buttons that represent something in progress
		self.ButtonSelected = (0xD0, 0xDF, 0x00) # darker yellow; for button that is toggled to 'on' status
		self.ButtonUnselected = "gray"
		self.BackHighlight = (0xF0, 0xFF, 0x00) # yellow; for highlighting widget backgrounds

def PopulateSizer(Sizer=None, Widgets=[], ActiveWidgetList=[], DefaultFont=None, HighlightBkgColour=None):
	# lay out required Widgets (list of UIWidgetItem instances) in Sizer (GridBagSizer instance)
	# ActiveWidgetList: list to which all UIWidgetItem instances newly added to the sizer will be appended
	# DefaultFont (wx.Font instance): font to apply to widgets, if not supplied in the UIWidgetItem
	# HighlightBkgColour (rgb colour tuple): background colour to apply to widgets with NeedsHighlight == True
	# returns list of text widgets to check for loss of focus in OnIdle
	assert isinstance(Sizer, wx.GridBagSizer)
	assert isinstance(Widgets, list)
	assert isinstance(ActiveWidgetList, list)
	TextWidgetsAdded = []
	Sizer.Clear(delete_windows=False) # remove all existing widgets from sizer
	RowBase = 0 # which row of widgets in Widgets we are filling
	ThisRowSpan = 1 # how many sizer rows are taken up by this row of widgets
	GapYAdded = False
	for ThisWidget in Widgets:
		# here, apply any conditions to determine if widget is shown
		assert isinstance(ThisWidget.IsVisible, bool)
		ShowThisWidget = ThisWidget.IsVisible
		if ShowThisWidget:
			if ThisWidget.IsInSizer:
				if ThisWidget.NewRow or GapYAdded: # start a new row (sizer also treats y-gap as a row)
					RowBase += 1 # skip forward the required number of rows
					if GapYAdded:
						RowBase += 1 # leave an empty sizer row for the GapY
						GapYAdded = False # reset flag
					ThisRowSpan = 1 # reset for new row
				# put widgets in sizer. wx.LEFT flag assigns the margin space to the left side only
				Sizer.Add(ThisWidget.Widget, pos=(RowBase + ThisWidget.RowOffset, ThisWidget.ColLoc + ThisWidget.ColOffset),
					span=(ThisWidget.RowSpan, ThisWidget.ColSpan), flag=ThisWidget.Flags | wx.LEFT, border=ThisWidget.LeftMargin)
				ThisRowSpan = max(ThisRowSpan, ThisWidget.RowSpan)
				# set widget minimum size in sizer, if required
				if (ThisWidget.MinSizeX is not None) and (ThisWidget.MinSizeY is not None):
					Sizer.SetItemMinSize(ThisWidget.Widget, (ThisWidget.MinSizeX, ThisWidget.MinSizeY))
			# set font to any font specified in widget (or DefaultFont), if any set font method is available
			ThisWidget.SetMyFont(DefaultFont=DefaultFont)
#			getattr(ThisWidget.Widget, 'SetFont', lambda f: None)\
#				(DefaultFont if getattr(ThisWidget, 'Font', None) is None else ThisWidget.Font)
#			if getattr(ThisWidget, 'Font', None):
#				ThisWidget.Widget.SetFont(ThisWidget.Font)
#			else: # use default font
#				ThisWidget.Widget.SetFont(DefaultFont)
			# set foreground and background colours, if any method is available
			getattr(ThisWidget.Widget, 'SetForegroundColour', lambda c: None)(wx.NullColour)
			if hasattr(ThisWidget.Widget, 'SetBackgroundColour'):
				if ThisWidget.NeedsHighlight:
					ThisWidget.Widget.SetBackgroundColour(HighlightBkgColour)
					ThisWidget.NeedsHighlight = False # to ensure no highlight next time widget is drawn
				else:
					ThisWidget.Widget.SetBackgroundColour(wx.NullColour)
			# add y-gap in sizer, if required
			if ThisWidget.GapY > 0:
				Sizer.Add((10, ThisWidget.GapY),
					pos=(RowBase + ThisWidget.RowOffset + ThisRowSpan, ThisWidget.ColLoc + ThisWidget.ColOffset))
				GapYAdded = True # flag to ensure we start new row and skip over sizer row containing gap
			# put widget in "currently visible" list (to enable us to remove it from keyboard shortcut list when no longer needed)
			ActiveWidgetList.append(ThisWidget)
			# put widget in "check for loss of focus" list
			if isinstance(ThisWidget.Widget, (wx.TextCtrl, ExpandoTextCtrl)): TextWidgetsAdded.append(ThisWidget)
			# binding widget event handlers is now done in ActivateWidgetsInPanel, not here
			if getattr(ThisWidget, 'GapX', 0): # add empty space to the left of this widget
				Sizer.Add((ThisWidget.GapX, 10),
					pos=(RowBase + ThisWidget.RowOffset, ThisWidget.ColLoc + ThisWidget.ColOffset - 1))
		# make widgets in/visible, using widget's ShowMe/HideMe method (in UIWidgetItem class)
		if ThisWidget.IsVisible: ThisWidget.ShowMe()
		else: ThisWidget.HideMe()
#		ThisWidget.Widget.Show(ThisWidget.IsVisible)
	Sizer.Layout() # refresh sizer
	return TextWidgetsAdded

def ChangeZoomAndPanValues(Viewport=None, Zoom=None, PanX=None, PanY=None):
	# change the values of Zoom and Pan in Viewport (a Viewport object).
	# Does not actually change the display, only the stored values.
	# Zoom, PanX and PanY can be values as str or None; if None, they are ignored.
	assert isinstance(Viewport, ViewportBaseClass)
	if Zoom:
		assert isinstance(Zoom, str)
		TargetZoom = utilities.str2real(Zoom, meaninglessvalue='?')
		if TargetZoom != '?': Viewport.Zoom = TargetZoom # TODO assert or wrap to within limits
	if PanX:
		assert isinstance(PanX, str)
		TargetPanX = utilities.str2real(PanX, meaninglessvalue='?')
		if TargetPanX != '?': Viewport.PanX = TargetPanX # TODO assert or wrap to within limits
	if PanY:
		assert isinstance(PanY, str)
		TargetPanY = utilities.str2real(PanY, meaninglessvalue='?')
		if TargetPanY != '?': Viewport.PanY = TargetPanY # TODO assert or wrap to within limits

def CheckTextCtrlFocus(HostPanel):
	# check which, if any, TextCtrl or ExpandoTextCtrl in HostPanel currently has focus, and call its handler if a TextCtrl has
	# lost focus. We've tried using wx.EVT_KILL_FOCUS for this purpose, but Windows8.1 chokes
	# when wx.EVT_KILL_FOCUS is raised (no similar problem in macOS since OS X 10.10).
	# Uses HostPanel's iterable TextWidgActive containing UIWidget instances - no problem if TextWidgActive doesn't exist
	# first, find out which TextCtrl or ExpandoTextCtrl is focused
	ActiveWidgList = getattr(HostPanel, 'TextWidgActive', [])
	NowFocused = ([w for w in ActiveWidgList if w.Widget.HasFocus()] + [None])[0]
	# has a TextCtrl lost focus?
	if hasattr(HostPanel, 'LastTextCtrlFocused'):
		# get UIWidget item that had focus last time this procedure ran (only TextCtrl's)
		LastWidget = HostPanel.LastTextCtrlFocused
		if LastWidget: # a TextCtrl had focus before
#			print('DU818 LastWidget, NowFocused: ', LastWidget, NowFocused)
			if (LastWidget != NowFocused) and (LastWidget in ActiveWidgList) and (LastWidget.Handler is not None)\
					and not getattr(LastWidget, 'SkipLoseFocus', False):
				# SkipLoseFocus means "ignore me when I lose focus"
				# Focus has changed, and the previously focused widget is still onscreen: call its handler
				LastWidget.Handler(Event=None, WidgetObj=LastWidget)
	# save focused TextCtrl (if any) for next time
	setattr(HostPanel, 'LastTextCtrlFocused', NowFocused)

def CalculateZoom(PageCountMethod, PagesAcrossRequested, PagesDownRequested, PageCountMethodArgs, MaxZoom, MinZoom, **Args):
	# For an export that may occupy more than one page, calculate the maximum zoom that will fill the number of pages
	# requested. Implements algorithm 392-1.
	# PageCountMethod (callable): method that calculates the number of pages required at a given zoom level. Assumed to
	# return dict containing (at least) keys PagesAcrossCount, PagesDownCount (2 x int).
	# PagesAcross/DownRequested (2 x int): number of pages to fill
	# PageCountMethodArgs (dict): all other args to pass to PageCountMethod, apart from Zoom. PageCountMethod must not
	#	require any positional args.
	# MaxZoom, MinZoom (float): hard limits on returned zoom value
	# returns: PagesAcrossAtFinalZoom, PagesDownAtFinalZoom, FinalZoom
	assert callable(PageCountMethod)
	assert isinstance(PagesAcrossRequested, int)
	assert isinstance(PagesDownRequested, int)
	assert PagesAcrossRequested > 0
	assert PagesDownRequested > 0
	assert isinstance(PageCountMethodArgs, dict)
	assert isinstance(MaxZoom, float)
	assert isinstance(MinZoom, float)
	assert 0 < MinZoom < MaxZoom
	InitialZoom = 1.0
	# step 1: calculate page count at initial zoom
	Zoom100Results = PageCountMethod(Zoom=InitialZoom, **PageCountMethodArgs)
	PageAcross100 = Zoom100Results['PagesAcrossCount']
	PageDown100 = Zoom100Results['PagesDownCount']
	# step 2: check if the target zoom is likely underrange
	ZoomOutOfRange = False
	if (PageAcross100 / PagesAcrossRequested > InitialZoom / MinZoom) or (PageDown100 / PagesDownRequested > InitialZoom / MinZoom):
		FinalZoom = MinZoom
		ZoomOutOfRange = True
	# step 3: check if the target zoom is likely overrange
	elif (PageAcross100 / PagesAcrossRequested < InitialZoom / MaxZoom) or (PageDown100 / PagesDownRequested < InitialZoom / MaxZoom):
		FinalZoom = MaxZoom
		ZoomOutOfRange = True
	if ZoomOutOfRange: # calculate page count at min/max zoom and exit
		FinalZoomResults = PageCountMethod(Zoom=FinalZoom, **PageCountMethodArgs)
		return FinalZoomResults['PagesAcrossCount'], FinalZoomResults['PagesDownCount'], FinalZoom
	else:
		# step 4: calculate initial trial zoom
		ThisTrialZoom = max(min(InitialZoom * PagesAcrossRequested / PageAcross100,
			InitialZoom * PagesDownRequested / PageDown100, MaxZoom), MinZoom)
		LastTrialZoom = InitialZoom
		# step 5: start loop
		LoopCounter = 0
		MaxLoops = 20
		StopLooping = False
		while not StopLooping:
			# step 6: calculate page fount at ThisTrialZoom
			ThisZoomResults = PageCountMethod(Zoom=ThisTrialZoom, **PageCountMethodArgs)
			ThisPageAcross = ThisZoomResults['PagesAcrossCount']
			ThisPageDown = ThisZoomResults['PagesDownCount']
			# step 7: calculate a step change in zoom
			TrialStep = min(PagesAcrossRequested / ThisPageAcross, PagesDownRequested / ThisPageDown)
			if TrialStep == 1.0: # page target hit; increase trial zoom to find maximum acceptable zoom
				if LoopCounter == 0: ThisZoomStep = math.sqrt(max(ThisTrialZoom, 1.0 / ThisTrialZoom))
				else: ThisZoomStep = math.sqrt(max(ThisZoomStep, 1.0 / ThisZoomStep))
			else: ThisZoomStep = math.sqrt(TrialStep)
			# step 8: update trial zoom, keeping it within valid range
			LastTrialZoom = ThisTrialZoom
			ThisTrialZoom = max(min(ThisTrialZoom * ThisZoomStep, MaxZoom), MinZoom)
			# step 9: increment loop counter
			LoopCounter += 1
			# step 10: test whether to loop again; last term stops looping if zoom step is less than 2%
			StopLooping = (LoopCounter > MaxLoops) or \
				(((ThisPageAcross == PagesAcrossRequested and ThisPageDown <= PagesDownRequested) or
				(ThisPageAcross <= PagesAcrossRequested and ThisPageDown == PagesDownRequested)) and
				(abs( (ThisTrialZoom - LastTrialZoom) / ThisTrialZoom) < 0.02))
		# step 11: return final results
		return ThisPageAcross, ThisPageDown, LastTrialZoom

def EnsurePaperMarginsReasonable(Margins, PaperSize, Orientation, LastMarginChanged='Top'):
	# check paper margins are acceptable considering the paper size specified.
	# Margins: (dict with keys 'Top', 'Bottom' etc) input margin values in mm
	# PaperSize (core_classes.PaperSize instance)
	# Orientation (str): 'Portrait' or 'Landscape'
	# LastMarginChanged (str or None): 'Top', 'Bottom' etc; which margin was most recently adjusted by user.
	# 	Not currently used
	# return: Margins (dict with keys 'Top', 'Bottom' etc; values are adjusted margins in mm);
	# 	MarginsChanged (bool): whether any returned margin values are different from supplied values
	KeyList = ['Top', 'Bottom', 'Left', 'Right']
	assert isinstance(Margins, dict)
	for ThisKey in KeyList: assert ThisKey in Margins
	assert isinstance(PaperSize, core_classes.PaperSize)
	assert Orientation in ['Portrait', 'Landscape']
	assert (LastMarginChanged in KeyList) or (LastMarginChanged is None)
	MarginsChanged = False
	# check each axis
	for ThisAxis, MarginA, MarginB in [ ('Vertical', 'Top', 'Bottom'), ('Horizontal', 'Left', 'Right') ]:
		if ThisAxis == 'Vertical':
			PaperSizeThisAxis = {'Portrait': PaperSize.SizeLongAxis, 'Landscape': PaperSize.SizeShortAxis}[Orientation]
		else:
			PaperSizeThisAxis = {'Portrait': PaperSize.SizeShortAxis, 'Landscape': PaperSize.SizeLongAxis}[Orientation]
		# check if the space between the margins is too small
		if PaperSizeThisAxis - Margins[MarginA] - Margins[MarginB] < info.MinUsablePaperLength:
			# adjust larger of the 2 margins
			if Margins[MarginA] > Margins[MarginB]:
				LargerMarginKey = MarginA; SmallerMarginKey = MarginB
			else:
				LargerMarginKey = MarginB; SmallerMarginKey = MarginA
			# set the margin to the required size, unless that size is less than the minimum allowed
			Margins[LargerMarginKey] = max(info.MinMargin, PaperSizeThisAxis - info.MinUsablePaperLength \
				- Margins[SmallerMarginKey])
			MarginsChanged = True
			# if we still didn't reach the minimum paper space, adjust the smaller margin as well
			if PaperSizeThisAxis - Margins['Top'] - Margins['Bottom'] < info.MinUsablePaperLength:
				Margins[SmallerMarginKey] = PaperSizeThisAxis - info.MinUsablePaperLength \
					- Margins[LargerMarginKey]
	return Margins, MarginsChanged

class ExcelTable_Border(object):
	# defines border along one edge of a cell at the extremity of a table

	def __init__(self, Visible=True, Colour=None, Thickness=None, Dashed=None):
		assert isinstance(Visible, bool)
		assert isinstance(Colour, tuple)
		assert isinstance(Thickness, int)
		assert Thickness >= 0
		assert isinstance(Dashed, str)
		self.Visible = Visible
		self.Colour = Colour
		self.Thickness = Thickness
		self.Dashed = Dashed

class ExcelTable_Table(object):
	# defines a block of cells in an Excel export

	def __init__(self, PositionRelativeTo=None, RelPosDirection='Right', GapToRight=0,
		SkipGapToRightIfAtRightOfSheet=True, GapBelow=0, SkipGapBelowIfAtBottomOfSheet=True, TopBorder=None,
		BottomBorder=None, LeftBorder=None, RightBorder=None):
		# PositionRelativeTo: another Table or None - the table this one should be oriented relative to
		# RelPosDirection (str): which direction this table should be oriented relative to the one named above
		# GapToRight (int): if nonzero, one blank cell with this width (mm) is left blank to the right of this table
		# SkipGapToRightIfAtRightOfSheet (bool): don't leave gap if there's no table to the right
		# GapBelow (int): if nonzero, one blank cell with height = this number of lines is left blank below this table
		# SkipGapBelowIfAtBottomOfSheet (bool): don't leave gap if there's no table below
		# Borders: border object or None
		assert isinstance(PositionRelativeTo, ExcelTable_Table) or (PositionRelativeTo is None)
		assert RelPosDirection in [info.RightLabel, info.BelowLabel]
		assert isinstance(GapToRight, int)
		assert GapToRight >= 0
		assert isinstance(SkipGapToRightIfAtRightOfSheet, bool)
		assert isinstance(GapBelow, int)
		assert GapBelow >= 0
		assert isinstance(SkipGapBelowIfAtBottomOfSheet, bool)
		assert isinstance(TopBorder, ExcelTable_Border) or (TopBorder is None)
		assert isinstance(BottomBorder, ExcelTable_Border) or (BottomBorder is None)
		assert isinstance(LeftBorder, ExcelTable_Border) or (LeftBorder is None)
		assert isinstance(RightBorder, ExcelTable_Border) or (RightBorder is None)
		self.PositionRelativeTo = PositionRelativeTo
		self.RelPosDirection = RelPosDirection
		self.GapToRight = GapToRight
		self.SkipGapToRightIfAtRightOfSheet = SkipGapToRightIfAtRightOfSheet
		self.GapBelow = GapBelow
		self.SkipGapBelowIfAtBottomOfSheet = SkipGapBelowIfAtBottomOfSheet
		self.TopBorder = TopBorder
		self.BottomBorder = BottomBorder
		self.LeftBorder = LeftBorder
		self.RightBorder = RightBorder
		self.Components = [] # list of ExcelTable_Component instances

class ExcelTable_Component(object):
	# defines a single cell in a table comprising part of an Excel export

	def __init__(self, PositionRelativeTo=None, RelPosDirection='Right', TopBorder=None,
		BottomBorder=None, LeftBorder=None, RightBorder=None, Content='', VertAlignment=info.TopLabel,
		HorizAlignment=info.LeftLabel, LeftIndentInmm=0, LeftIndentInRelWidth=0, FontStyle=None,
		BackgColour=(255,255,255), RelWidth=1.0, MergeToRight=False, MergeDown=False):
		# PositionRelativeTo: another Component or None - the component this one should be oriented relative to
		# RelPosDirection (str): which direction this component should be oriented relative to the one named above
		# Borders: border object or None
		# Content: text to put in the cell
		# VertAlignment, HorizAlignment: text alignment in the cell
		# LeftIndent: text indent to apply. LeftIndentInmm takes priority.
		# RelWidth: relative width of cell relative to all other cells in the sheet
		# Merge: whether to merge with any adjacent cell in specified direction
		assert isinstance(PositionRelativeTo, ExcelTable_Component) or (PositionRelativeTo is None)
		assert RelPosDirection in [info.RightLabel, info.BelowLabel]
		assert isinstance(TopBorder, ExcelTable_Border) or (TopBorder is None)
		assert isinstance(BottomBorder, ExcelTable_Border) or (BottomBorder is None)
		assert isinstance(LeftBorder, ExcelTable_Border) or (LeftBorder is None)
		assert isinstance(RightBorder, ExcelTable_Border) or (RightBorder is None)
		assert isinstance(Content, str)
		assert VertAlignment in [info.TopLabel, info.CentreLabel, info.BottomLabel]
		assert HorizAlignment in [info.LeftLabel, info.CentreLabel, info.RightLabel]
		assert isinstance(LeftIndentInmm, (int, float))
		assert LeftIndentInmm >= 0
		assert isinstance(LeftIndentInRelWidth, (int, float))
		assert LeftIndentInRelWidth >= 0
		assert isinstance(FontStyle, wx.Font) or (FontStyle is None)
		assert isinstance(BackgColour, tuple)
		assert isinstance(RelWidth, (int, float))
		assert RelWidth > 0
		assert isinstance(MergeToRight, bool)
		assert isinstance(MergeDown, bool)
		self.PositionRelativeTo = PositionRelativeTo
		self.RelPosDirection = RelPosDirection
		self.TopBorder = TopBorder
		self.BottomBorder = BottomBorder
		self.LeftBorder = LeftBorder
		self.RightBorder = RightBorder
		self.Content = Content
		self.VertAlignment = VertAlignment
		self.HorizAlignment = HorizAlignment
		self.LeftIndentInmm = LeftIndentInmm
		self.LeftIndentInRelWidth = LeftIndentInRelWidth
		self.FontStyle = FontStyle
		self.BackgColour = BackgColour
		self.RelWidth = Width
		self.MergeToRight = MergeToRight
		self.MergeDown = MergeDown

class ExcelTable_Sheet(object):
	# defines a block of tables defining content of an exported spreadsheet

	def __init__(self, TabName, TabColour, TargetWidth):
		# TabName (str): Name to be shown on Excel worksheet tab. Can't be blank
		# TabColour (rgb tuple, 3 x int): Colour to be applied to Excel worksheet tab
		# TargetWidth (int): Total width of all cells in the Sheet, in mm
		assert isinstance(TabName, str)
		assert TabName.strip() # ensure it's not blank or whitespace only
		assert isinstance(TabColour, tuple)
		assert isinstance(TargetWidth, int)
		assert TargetWidth > 0
		object.__init__(self)
		self.TabName = TabName
		self.TabColour = TabColour
		self.TargetWidth = TargetWidth
		self.Tables = [] # ExcelTable_Table instances