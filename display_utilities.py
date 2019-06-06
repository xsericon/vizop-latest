# -*- coding: utf-8 -*-
# Module display_utilities: part of Vizop, (c) 2018 xSeriCon. Contains common class definitions and functions for all Viewports

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import wx, wx.grid, wx.lib.gridmovers, zmq, math # wx provides basic GUI functions
import wx.lib.buttons as buttons
from sys import stdout


# other vizop modules required here
import art, utilities, vizop_misc, info

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
#	__metaclass__ = ViewportMetaClass
	CanBeCreatedManually = True # whether user can be invited to create a Viewport of this class.
	IsBaseClass = True # needed by metaclass

	def __init__(self, **Args): # Args must include Proj, a ProjectItem instance
		object.__init__(self)
		self.DisplDevice = None # which wx.Window object the Viewport is displayed on (needs to take a wx.DC)
		self.ID = None # assigned in CreateViewport()
		self.Proj = Args['Proj']
		self.C2DSocketREQ    = self.D2CSocketREP = None # zmq sockets for communication; set in CreateViewport()
		self.C2DSocketREQObj = self.D2CSocketREPObj = None # SocketInRegister instances matching In/OutwardSocket;
			# set in CreateViewport()
#		self.GotoMilestoneOnUndoCreate = None # a milestone instance to revert to, if creation of this Viewport is undone

def CreateViewport(Proj, ViewportClass, DisplDevice=None, PHAObj=None, DatacoreIsLocal=True, Fonts=[]):
	# create new Viewport instance of class ViewportClass in project Proj, and attach it to DisplDevice.
	# PHAObj: PHA object to which the Viewport belongs
	# DatacoreIsLocal (bool): whether datacore is in this instance of Vizop
	# Fonts: (dict) keys are strings such as 'SmallHeadingFont'; values are wx.Font instances
	# Return the Viewport instance, and D2C and C2D socket numbers (2 x int)
	assert isinstance(DatacoreIsLocal, bool)
	NewViewport = ViewportClass(Proj=Proj, DisplDevice=DisplDevice, PHAObj=PHAObj, Fonts=Fonts)
	# append the Viewport to the project's list
	NewViewport.ID = str(utilities.NextID(Proj.ActiveViewports)) # generate unique ID; stored as str
	# ID is assigned this way (rather than with master lists per class, as for other objects) to avoid memory leaks
	# set up sockets for communication with the new Viewport:
	# D2C (Viewport to core) and C2D. Each socket has both REQ (send) and REP (reply) sides.
#	# If datacore is local (i.e. running in the same instance of Vizop), we set up datacore's side first, to get the
#	# socket numbers.
#	if DatacoreIsLocal:
#		NewViewport.D2CSocketREP, NewViewport.D2CSocketREPObj = vizop_misc.SetupNewSocket(SocketType='REP',
#			SocketLabel='D2CREP_' + NewViewport.ID,
#			PHAObj=PHAObj, Viewport=NewViewport, SocketNo=None, BelongsToDatacore=True, AddToRegister=True)
#		NewViewport.C2DSocketREQ, NewViewport.C2DSocketREQObj = vizop_misc.SetupNewSocket(SocketType='REQ',
#			SocketLabel=info.ViewportOutSocketLabel + '_' + NewViewport.ID,
#			PHAObj=PHAObj, Viewport=NewViewport, SocketNo=None, BelongsToDatacore=True, AddToRegister=True)
#		D2CSocketNo = NewViewport.D2CSocketREPObj.SocketNo
#		C2DSocketNo = NewViewport.C2DSocketREQObj.SocketNo
	D2CSocketNo = vizop_misc.GetNewSocketNumber()
	C2DSocketNo = vizop_misc.GetNewSocketNumber()
	# Then we fetch the socket numbers and make the corresponding sockets on the Viewport side.
	NewViewport.C2DSocketREQ, NewViewport.C2DSocketREQObj, C2DSocketNoReturned = vizop_misc.SetupNewSocket(SocketType='REQ',
		SocketLabel='C2DREQ_' + NewViewport.ID, PHAObj=PHAObj, Viewport=NewViewport,
		SocketNo=C2DSocketNo, BelongsToDatacore=False, AddToRegister=True)
	NewViewport.D2CSocketREP, NewViewport.D2CSocketREPObj, D2CSocketNoReturned = vizop_misc.SetupNewSocket(SocketType='REP',
		SocketLabel='D2CREP_' + NewViewport.ID, PHAObj=PHAObj, Viewport=NewViewport,
		SocketNo=D2CSocketNo, BelongsToDatacore=False, AddToRegister=True)
	return NewViewport, D2CSocketNo, C2DSocketNo

def ViewportClassWithName(TargetName):
	# returns the Viewport class with internal name = TargetName, or None if not found
	assert isinstance(TargetName, str)
	InternalNameList = [c.InternalName for c in ViewportMetaClass.ViewportClasses]
	if TargetName in InternalNameList:
		return ViewportMetaClass.ViewportClasses[InternalNameList.index(TargetName)]
	else: return None

# --- classes of iWindow widgets ---

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

class ZoomWidgetObj(object):
	# widget allowing user to control zoom of a Viewport
	AngleAtPointerMin = 4.01 # 230deg in radians; 7 o'clock
	AngleAtPointerMid = 1.57 # 90deg in radians; 12 o'clock
	AngleAtPointerMax = 5.24 # 300 deg in radians; 5 o'clock
	Mid2MinAngleRange = AngleAtPointerMid - AngleAtPointerMin
	Mid2MaxAngleRange = (6.28 + AngleAtPointerMid) - AngleAtPointerMax # 2pi added, as angle range wraps
	BestMousePointerForSelecting = 'Zoom' # should be a key of StockCursors
	PosZ = 100 # z-coordinate of FloatLayer containing the zoom widget

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
		assert 1e-5 < MinZoom < InitialZoom < MaxZoom < 1e5
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

	def HandleMouseLClickOnMe(self, HitHotspot='Whole', HostViewport=None, MouseX=0, MouseY=0):
		# handle mouse left button down inside zoom widget at coords MouseX, MouseY (2 x int) in pixels relative to panel
		# ends by calling HostViewport.RefreshZoomWidget() with bitmap containing redrawn widget as arg
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
			if (Mode == 'Select'):
				wx.SetCursor(wx.Cursor(StockCursors[ObjOver.BestMousePointerForSelecting]))
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
	# These objects contain widgets for display, with associated info needed for use in sizers

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
		self.Number = False # whether to treat as a number when displaying (if False, treated as a string)
		self.PermissibleValues = [] # list of values that can be returned by a Choice widget. These must be the internal
			# values, not the human names (because these might be translated)
		self.ReadOnly = False # whether changes to the attrib value are disallowed
		self.NeedsHighlight = False # whether widget should have background highlight next time it is drawn
		self.DataAttrib = None # (None or str) name of attrib in related PHA object whose data this widget displays
		self.Font = None
		self.Widget.Hide()
		# set values of attributes provided
		for (Attr, Value) in Attrs.items():
			setattr(self, Attr, Value)
		# copy any DataAttrib value into the wx widget, for easier access in widget handlers
		if self.DataAttrib: self.Widget.DataAttrib = self.DataAttrib

	def SetMyFont(self, DefaultFont=None): # set font used to display widget value
		if getattr(self, 'Font', None) is not None:
			assert isinstance(self.Font, wx.Font)
			self.Widget.SetFont(self.Font)
		elif DefaultFont: # use default font, if provided
			assert isinstance(DefaultFont, wx.Font)
			self.Widget.SetFont(DefaultFont)

	def StaticHeader(self, **Args): # rendering method for UIWidgets containing headers that don't need to be populated
		self.SetMyFont(DefaultFont=Args.get('Font', None))

	def StaticFromText(self, DataObj, **Args): # put string or number value directly in StaticText or TextCtrl widgets
		TargetValue = getattr(DataObj, self.DataAttrib, None)
		if TargetValue is not None: # attrib exists
			if self.Number: # treat as number
				if TargetValue.GetStatus() == 'ValueStatus_Unset': # number not defined because subsystem not included
					StringToDisplay = _('Value not defined')
				else: StringToDisplay = self.StringFromNum(TargetValue, SciThreshold=None)
			else: # convert directly to str (for attribs that aren't already strings, eg int)
				StringToDisplay = str(TargetValue)
		else: # attrib doesn't exist
			StringToDisplay = _('Attrib not defined')
		# use appropriate method to populate wxwidget
		if isinstance(self.Widget, wx.StaticText):
			self.Widget.SetLabel(StringToDisplay)
		else: self.Widget.SetValue(StringToDisplay)
		self.SetMyFont(DefaultFont=Args.get('Font', None))

def StringFromNum(InputNumber, SciThreshold=None):
	# returns correctly formatted string representation of InputNumber
	# (NumValueItem instance), taking the number object's attribs Sci and Decimals into account
	# SciThreshold (int, float or None): if the absolute value of InputNumber ≥ SciThreshold, scientific notation will be used
	# First, check if value is defined
	ValueStatus = InputNumber.GetStatus()
	assert ValueStatus in core_classes.ValueStati
	if ValueStatus == 'ValueStatus_OK': # it's defined
		return InputNumber.GetDisplayValue(SciThreshold=SciThreshold)
	elif ValueStatus == 'ValueStatus_Unset': # it's not defined
		return _('Not set')

class SIFListGridTable(wx.grid.PyGridTableBase): # object containing data table for SIF list display

	def __init__(self, Log, ColumnInternalNames=[]):
		# ColumnInternalNames: list of str, internal names (not display names) of grid table columns
		wx.grid.PyGridTableBase.__init__(self)
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
		if not (0 <= Row < self.GetNumberRows()): print("MG388 row: ", Row, type(Row)) # debugging
		assert 0 <= Row < self.GetNumberRows() + 1 # +1 needed in case user drags a SIF to the bottom of the table
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
		self.DataTable = SIFListGridTable(Log, ColumnInternalNames=ColumnInternalNames) # create a data table object
		self.SetTable(self.DataTable, True, selmode=wx.grid.Grid.SelectRows) # can select rows, but not individual cells
		# enable columns to be dragged to reorder (not currently used)
		# wx.lib.gridmovers.GridColMover(self)
		# self.Bind(wx.lib.gridmovers.EVT_GRID_COL_MOVE, self.OnColMove, self)
		# enable rows to be dragged to reorder
		wx.lib.gridmovers.GridRowMover(self)
		self.Bind(wx.lib.gridmovers.EVT_GRID_ROW_MOVE, self.OnRowMove, self)
		self.DisableCellEditControl() # disallow editing of cells
		# send events to parent window (e.g. data panel) for processing, if parent has a handler
		# (the hasattr() check is in case we use a grid in any other window in future, and don't implement handler)
		print("DU624 looking for grid click handlers")
		if hasattr(self.Viewport, 'OnGridMouseDoubleLClick'):
			self.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.Viewport.OnGridMouseDoubleLClick)
		if hasattr(self.Viewport, 'OnGridRangeSelect'):
			self.Bind(wx.grid.EVT_GRID_RANGE_SELECT, self.Viewport.OnGridRangeSelect)

	def OnColMove(self, Event): # handle dragging of table column
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
	assert isinstance(Sizer, wx.GridBagSizer)
	assert isinstance(Widgets, list)
	assert isinstance(ActiveWidgetList, list)
	Sizer.Clear(delete_windows=False) # remove all existing widgets from sizer
	RowBase = 0 # which row of widgets in Widgets we are filling
	ThisRowSpan = 1 # how many sizer rows are taken up by this row of widgets
	GapYAdded = False
	for ThisWidget in Widgets:
		# here, apply any conditions to determine if widget is shown
		ShowThisWidget = True # placeholder for conditions that might be needed in future
		if ShowThisWidget:
			if ThisWidget.NewRow or GapYAdded: # start a new row (sizer also treats y-gap as a row)
				RowBase += ThisRowSpan  # skip forward the required number of rows
				if GapYAdded:
					RowBase += 1 # leave an empty sizer row for the GapY
					GapYAdded = False # reset flag
				ThisRowSpan = 1 # reset for new row
			# put widgets in sizer
			Sizer.Add(ThisWidget.Widget, pos=(RowBase + ThisWidget.RowOffset, ThisWidget.ColLoc + ThisWidget.ColOffset),
				span=(ThisWidget.RowSpan, ThisWidget.ColSpan), flag=ThisWidget.Flags | wx.LEFT, border=ThisWidget.LeftMargin)
			# set widget minimum size, if required
			if (ThisWidget.MinSizeX is not None) and (ThisWidget.MinSizeY is not None):
				Sizer.SetItemMinSize(ThisWidget.Widget, (ThisWidget.MinSizeX, ThisWidget.MinSizeY))
			ThisRowSpan = max(ThisRowSpan, ThisWidget.RowSpan)
			# set font
			if getattr(ThisWidget, 'Font', None):
				ThisWidget.Widget.SetFont(ThisWidget.Font)
			else: # use default font
				ThisWidget.Widget.SetFont(DefaultFont)
			# set foreground and background colours
			ThisWidget.Widget.SetForegroundColour(wx.NullColour)
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
			# put widgets in "currently visible" list (to enable us to remove them from keyboard shortcut list when no longer needed)
			ActiveWidgetList.append(ThisWidget)
			# make widgets visible
			ThisWidget.Widget.Show()
#				ThisWidget.DataObj = DataObj # store DataObj in UIWidget item, so that we know where to write changes
#				# populate widgets with values
#				if ThisWidget.DataAttrib and ThisWidget.DisplayMethod and DataObj:
#					getattr(ThisWidget, ThisWidget.DisplayMethod)(DataObj) # calls method with string name w.DisplayMethod
			# binding widget event handlers is now done in ActivateWidgetsInPanel
			if getattr(ThisWidget, 'GapX', 0): # add empty space to the left of this widget
				Sizer.Add((ThisWidget.GapX, 10),
					pos=(RowBase + ThisWidget.RowOffset, ThisWidget.ColLoc + ThisWidget.ColOffset - 1))
	Sizer.Layout() # refresh sizer

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

