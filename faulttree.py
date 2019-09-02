# -*- coding: utf-8 -*-
# Module faulttree: part of Vizop, (c) 2017 xSeriCon

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import wx # provides basic GUI functions
import zmq, copy
import xml.etree.ElementTree as ElementTree # XML handling

# other vizop modules required here
import text, utilities, core_classes, info, vizop_misc, projects, art, display_utilities, undo

# constants applicable to fault tree
TextElementTopBufferInCU = 2 # y-gap in canvas units between top of a text element and top of its contained text
DefaultFontFamily = wx.FONTFAMILY_SWISS
ConnectingLineColour = (0xf6, 0xff, 0x2a) # golden yellow, for lines connecting FT elements
ButtonBaseColour = (0x64, 0x64, 0x80) # mid grey, background colour for graphical buttons
ButtonBorderColour = (0x20, 0x20, 0x30) # deep grey, border colour for graphical buttons
ButtonGraphicColour = (0xd0, 0xd0, 0xff) # blue-white, graphics colour for graphical buttons
GateBorderColour = ButtonBorderColour
GateBaseColourStr = '0x64, 0x64, 0xa0'
GateBaseColour = (0x64, 0x64, 0xa0)
GateLabelBkgColour = ButtonBorderColour
GateLabelFgColour = ButtonGraphicColour
GateTextBkgColour = (0xb0, 0xb0, 0xff) # light grey
GateTextFgColour = (0x00, 0x00, 0x00) # black
HighlightColour = (0xfd, 0xf8, 0x47) # yellow
HighlightColourStr = '253,248,71' # yellow
ConnectingLineThicknessInCU = 4 # in canvas coords

def SILTarget(Mode='', RiskRed=1.0):
	# returns SIL target (str) corresponding to RiskRed (PFH or RRF depending on Mode)
	assert Mode in core_classes.OpModes
	assert isinstance(RiskRed, float)
	if Mode in [core_classes.HighDemandMode, core_classes.ContinuousMode]:
		assert 1.1 > RiskRed > 0.0 # check PFH is in acceptable range, allowing for rounding error
		SILTable = [(1e-4, '0'), (1e-5, 'a'), (1e-6, '1'), (1e-7, '2'), (1e-8, '3'), (1e-9, '4'), (-0.1, 'b')]
		for MinRiskRed, ThisSILTarget in SILTable: # step through SILTable until we find a PFH value <= RiskRed
			if MinRiskRed <= RiskRed: break
	else: # Low-Demand mode
		assert RiskRed >= 0 # check RRF is in acceptable range
		SILTable = [(1.1, '0'), (10.0, 'a'), (100.0, '1'), (1000.0, '2'), (10000.0, '3'), (100000.0, '4')]
		for MinRiskRed, ThisSILTarget in SILTable: # step through SILTable until we find a RRF value >= RiskRed
			if MinRiskRed >= RiskRed: break
		else: # Python 'else' statement executes if 'for' loop runs without being 'break'd
			ThisSILTarget = 'b' # RRF is beyond SIL 4 range
	return ThisSILTarget

class ButtonElement(object): # object containing a button and attributes and methods needed to render it
	# class ButtonObjectNotInElement is a subclass of this

	def __init__(self, FT, Row=0, RowBase=0, ColStart=0, ColSpan=1, StartX=0, EndX=200, PosYInCU=0, InternalName='',
				 HostObject=None):
		# FT (FTForDisplay instance): FT containing this button element
		# InternalName (str): label indicating the kind of function the button has
		assert isinstance(FT, FTForDisplay)
		assert InternalName in ['EventLinkedButton', 'EventGroupedButton', 'EventCommentButton',
			'EventActionItemButton', 'ValueCommentButton', 'ValueProblemButton', 'ConnectButton', 'GateLinkedButton',
			'GateLinkedButton', 'GateCommentButton', 'GateActionItemButton', 'ValueProblemButton',
			'GateStyleButton', 'GateGroupedButton']
		assert isinstance(HostObject, (FTEvent, FTGate, FTCollapseGroup, FTConnector)) or (HostObject is None)
		object.__init__(self)
		self.FT = FT
		self.HostObject = HostObject # which object (e.g. FTEvent instance) contains the ButtonElement instance
		self.Row = Row # row of grid in which button is located
		self.RowBase = RowBase # relative row of grid within a subgroup of elements
		self.ColStart = ColStart # column of grid in which button starts
		self.ColSpan = ColSpan # how many columns of grid are spanned by the button
		self.StartX = StartX # X-coord (canvas coords) of button left end, relative to DC (obsolescent)
		self.EndX = EndX # similar for right end of button
		# StartX, EndX were intended to facilitate checking for mouse hits but probably better to make new attribs StartXScreen etc
		self.PosYInCU = PosYInCU
		self.PosZ = 0 # z-coordinate
		self.FillXSpace = False # whether button should expand to fill available space in X direction
		if InternalName == 'ConnectButton': self.Status = 'Unconnected'
		else: self.Status = 'Out'
		# Status can be 'Out', 'In', 'Pressed' (user currently clicking it), or 'Alert' (flashing a warning)
		# For Connect buttons, status is 'Unconnected', 'Connected', 'Connecting' (making a connection)
		self.BitmapZoomed = {'Default': None} # bitmaps containing button images scaled to current zoom level.
			# Keys must include 'Default', other keys optional
		self.BitmapZoomLevel = 1.0 # zoom level of current bitmaps in self.BitmapZoomed (float) (not used?)
		self.InternalName = InternalName # name used to identify specific elements
		self.ArtProviderName = {'EventLinkedButton': 'FT_LinkButton', 'EventGroupedButton': 'FT_GroupButton',
			'EventCommentButton': 'FT_CommentButton', 'ConnectButton': 'FT_ConnectButton',
			'EventActionItemButton': 'FT_ActionButton', 'ValueCommentButton': 'FT_CommentButton',
			'ValueProblemButton': 'FT_ProblemButton', 'GateLinkedButton': 'FT_LinkButton',
			'GateLinkedButton': 'FT_LinkButton', 'GateCommentButton': 'FT_CommentButton',
			'GateActionItemButton': 'FT_ActionButton', 'ValueProblemButton': 'FT_ProblemButton',
			'GateGroupedButton': 'FT_GroupButton', 'GateStyleButton': 'FT_GateStyleButton'}[InternalName]
			# ArtProviderName is name to pass to ArtProvider + _ + key of BitmapZoomed
		self.SizeXInCU = self.SizeYInCU = 30 # no-zoom size in pixels
		self.SetupImages()
		self.Visible = True
		self.Selected = False # whether highlighted as part of user selection
		self.IsClickable = True

	def SetupImages(self): # populate self.BitmapZoomed with images for the button
		self.ChangeZoom(NewZoom=self.BitmapZoomLevel) # make initial bitmaps

	def ChangeZoom(self, NewZoom): # recalculate button bitmaps for new zoom level
		assert isinstance(NewZoom, float)
		for Status in self.BitmapZoomed:
			self.BitmapZoomed[Status] = wx.BitmapFromImage(self.FT.ArtProvider.get_image(
				name=self.ArtProviderName + '_' + Status, conserve_aspect_ratio=True,
				size=(int(self.SizeXInCU * NewZoom), int(self.SizeYInCU * NewZoom))))
		self.BitmapZoomLevel = NewZoom

	def Draw(self, DC, Zoom, **Args): # render the button in DC. No additional args required
		if self.InternalName == 'ConnectButton': # draw graphically instead of using bitmap
			self.DrawConnectButton(DC, Zoom)
		else: # draw bitmap
			# work out whether to resize button bitmaps
			if Zoom != self.BitmapZoomLevel: self.ChangeZoom(Zoom)
			DC.DrawBitmap(self.BitmapZoomed.get(self.Status, self.BitmapZoomed['Default']), self.PosXInCU * Zoom,
				self.PosYInCU * Zoom, useMask=False)

	def DrawConnectButton(self, DC, Zoom, InFloatLayer=False, DesignatedX=None, DesignatedY=None): # draw a connect button
		# InFloatLayer (bool): whether we are drawing in a dedicated layer buffer, rather than in the inter-column strip buffer
		# DesignatedX/Y: specific position (in pixels) to draw the button, or None to use default position
		# (DesignatedX/Y used during dragging)
		assert isinstance(InFloatLayer, bool)
		LineColour = {'Unconnected': (0xf6, 0xff, 0x2a), 'Connected': (0xf6, 0xff, 0x2a),
			'Connecting': (0xff, 0xcb, 0x29)}[self.Status] # golden yellow / orange
		FillColour = (0xff, 0xff, 0xff) # white
		DC.SetPen(wx.Pen(LineColour, width=max(1, int(round(2 * Zoom)))))
		DC.SetBrush(wx.Brush(FillColour))
		self.SizeXInPx = self.SizeYInPx = int(round(self.SizeXInCU * Zoom))
		Radius = int(round(0.5 * self.SizeXInPx))
		if (DesignatedX is not None) and (DesignatedY is not None): PosX = DesignatedX; PosY = DesignatedY
		elif InFloatLayer: # offset as the buffer is made 5 pixels too large on each edge
			PosX = self.FT.ConnectButtonBufferBorderX
			PosY = self.FT.ConnectButtonBufferBorderY
		else: PosX = int(round(self.PosXInCU * Zoom)); PosY = int(round(self.PosYInCU * Zoom)) # use button's real position in display device
		DC.DrawCircle(PosX + Radius, PosY + Radius, Radius)

	def GetMinSizeInCU(self): # calculate property MinSize - in canvas units
		return self.SizeXInCU, self.SizeYInCU

	def MouseHit(self, MouseXInPx, MouseYInPx, TolXInPx, TolYInPx, debug=False):
		# returns (str) hotspot hit in FTBoxyObject instance, or None if not hit
		# Hotspots can be: "Whole" (whole object hit)
		# This procedure currently same as class BoxyObject. Consider making this class a subclass of BoxyObject?
		assert isinstance(MouseXInPx, (float, int))
		assert isinstance(MouseYInPx, (float, int))
		assert isinstance(TolXInPx, (float, int)) # mouse hit tolerance in pixels
		assert isinstance(TolYInPx, (float, int))
		if debug:
			print("FT131 MouseHit: MouseXInPx, MouseYInPx, self.PosXInPx, self.PosYInPx, self.SizeXInPx, self.SizeYInPx: ", \
				MouseXInPx, MouseYInPx, self.PosXInPx, self.PosYInPx, self.SizeXInPx, self.SizeYInPx)
		# test if hotspot "Whole" hit
		if (MouseXInPx - TolXInPx >= self.PosXInPx) and (MouseYInPx - TolYInPx >= self.PosYInPx) and \
			(MouseXInPx + TolXInPx <= self.PosXInPx + self.SizeXInPx) and \
			(MouseYInPx + TolYInPx <= self.PosYInPx + self.SizeYInPx):
			return "Whole"
		else: return None

	def HandleMouseLClickOnMe(self, **Args): # handle mouse left button single click on ButtonElement instance
		if self.InternalName == 'EventCommentButton':
			self.HandleMouseLClickOnCommentButton(CommentKind='Description')
		elif self.InternalName == 'ValueCommentButton': self.HandleMouseLClickOnCommentButton(CommentKind='Value')
		elif self.InternalName == 'EventActionItemButton': self.HandleMouseLClickOnActionItemButton()
		elif self.InternalName == 'ConnectButton': self.HandleMouseLClickOnConnectButton()
		elif self.InternalName == 'GateStyleButton': self.HandleMouseLClickOnGateStyleButton()

	def HandleMouseLClickOnCommentButton(self, CommentKind):
		# handle mouse left button single click on a comment button
		assert CommentKind in ['Description', 'Value']
		if CommentKind == 'Description':
			Show = not self.HostObject.ShowDescriptionComments # toggle whether comments are visible
			Command = 'RQ_FT_DescriptionCommentsVisible'
		elif CommentKind == 'Value':
			Show = not self.HostObject.ValueComments # toggle whether comments are visible
			Command = 'RQ_FT_ValueCommentsVisible'
		vizop_misc.SendRequest(Socket=self.FT.C2DSocketREQ, Command=Command,
			ProjID=self.FT.Proj.ID, PHAObj=self.FT.PHAObj.ID, Viewport=self.FT.ID, Element=self.HostObject.ID,
			Visible=utilities.Bool2Str(Show))

	def HandleMouseLClickOnActionItemButton(self):
		# handle mouse left button single click on action item button
		Show = not self.HostObject.ShowActionItems # toggle whether action items are visible
		Command = 'RQ_FT_ActionItemsVisible'
		vizop_misc.SendRequest(Socket=self.FT.C2DSocketREQ, Command=Command,
			ProjID=self.FT.Proj.ID, PHAObj=self.FT.PHAObj.ID, Viewport=self.FT.ID, Element=self.HostObject.ID,
			Visible=utilities.Bool2Str(Show))

	def HandleMouseLClickOnConnectButton(self):
		# handle mouse left button single click on a connect button
		self.FT.EditingConnection = True # set flags
		self.Status = 'Connecting'
		self.FT.EditingConnectionStartButton = self # get info needed to process drag (this and following lines)
		# during the drag, rubber bands will be drawn to connect button(s). Work out which connect buttons.
		# Refer to case numbers in table in FT Spec.
		if self.IsLeft: # starting at output?
			if self.HostObject.ConnectTo: # already connected to anything? Case 2
				# find the buttons associated with elements connected to the start output
				self.FT.RubberBandTo = [b for ThisEl in self.HostObject.ConnectTo for b in self.FT.ConnectButtons
					if b.HostObject is ThisEl]
			else: # not connected to anything. Case 1
				self.FT.RubberBandTo = [self]
		else: # starting at output
			StartButtonJoinedFrom = JoinedFrom(self.FT, FTObj=self.HostObject, FirstOnly=False)
			if StartButtonJoinedFrom: # already connected to anything? Case 4
				# find the buttons associated with elements connected to the start input
				self.FT.RubberBandTo = [b for ThisEl in StartButtonJoinedFrom for b in self.FT.ConnectButtons
					if b.HostObject is ThisEl]
			else: # not connected to anything. Case 3
				self.FT.RubberBandTo = [self]

		# find size constraints of drag area: the size of the inter-column strip
		self.FT.StripCentreXInPx, self.FT.StripMinXInPx, self.FT.StripMinYInPx, self.FT.StripMaxXInPx, self.FT.StripMaxYInPx =\
			self.FT.GetConnectButtonDragInfo(self)
		# find all other buttons this connect button could connect to (for possible future 'snap' to button effect)
		self.FT.EditingConnectionCanConnectTo = self.FT.ConnectButtonsCanConnectTo(self)
		# draw the connect button in a dedicated bitmap, with overhang on each edge
		ConnectButtonBitmap = wx.Bitmap(width=self.SizeXInPx + 2 * self.FT.ConnectButtonBufferBorderX,
			height=self.SizeYInPx + 2 * self.FT.ConnectButtonBufferBorderY, depth=wx.BITMAP_SCREEN_DEPTH)
		DrawDC = wx.MemoryDC(ConnectButtonBitmap)
		self.DrawConnectButton(DrawDC, self.FT.Zoom, InFloatLayer=True)
		# make a floating layer for the connect button bitmap
		self.FloatLayer = display_utilities.FloatLayer(Bitmap=ConnectButtonBitmap,
				PosXInPx=self.PosXInPx - self.FT.ConnectButtonBufferBorderX,
			PosYInPx=self.PosYInPx - self.FT.ConnectButtonBufferBorderY, PosZ=7)
		self.FT.FloatingLayers.append(self.FloatLayer)
		self.FT.DisplDevice.Redraw(FullRefresh=False) # refresh the display to show the changed comment button

	def HandleMouseLClickOnGateStyleButton(self):
		# handle mouse left button single click on a gate style button
		# TODO send message to datacore to update the initial gate style; also in click handler of FTGate
		# change gate style flag
		self.HostObject.DetailedView = False
		self.FT.DisplDevice.Redraw(FullRefresh=True) # refresh the display to show the gate style

	MinSizeInCU = property(fget=GetMinSizeInCU)

class ButtonObjectNotInElement(ButtonElement):
	# class of buttons that behave similar to ButtonElements inside a TextElement, but aren't contained in a TextElement
	# such as connect buttons

	def __init__(self, FT, InternalName='', PosYInCU=0, HostObject=None, **Args):
		ButtonElement.__init__(self, FT=FT, Row=0, RowBase=0, ColStart=0, ColSpan=1, StartX=0, EndX=200, PosYInCU=PosYInCU,
			InternalName=InternalName, HostObject=HostObject)
		# capture attribs provided in Args
		for (AttribName, AttribValue) in Args.items(): setattr(self, AttribName, AttribValue)
		self.BestMousePointerForSelecting = 'Pencil'

class FTHeader(object): # FT header object. Rendered by drawing text into bitmap (doesn't use native widgets or sizer)
	# This class is used by FTForDisplay but not by FTObjectInCore (keeps header data in itself, not in sub-object)
	# ComponentEnglishNames: used for display in Control Panel
	ComponentEnglishNames = {'SIFName': 'SIF name', 'Rev': 'Revision', 'OpMode': 'Operating mode',
		'TolFreq': 'Tolerable frequency', 'SILTargetValue': 'SIL target'}

	def __init__(self, FT):
		assert isinstance(FT, FTForDisplay)
		object.__init__(self)
		self.FT = FT
		self.ID = 'Header' # needed when calling datacore to request data changes; e.g. in RequestChangeText()
		self.InitializeData()
		# create Elements needed for drawing each text in the header
		self.Elements = self.CreateTextElements()

	def InitializeData(self):
		self.SIFName = ''
		self.OpMode = _('<undefined>')
		self.Rev = ''
		self.RR = _('<undefined>') # risk receptors
		self.Severity = ''
		self.TolFreq = core_classes.NumValueItemForDisplay() # tolerable frequency, object including value, unit, possible units etc.
		self.TolFreq.InternalName = 'TolFreq' # for cross-reference to datacore attrib during editing
		self.TolFreq.AcceptableUnits = [] # populated in PopulateUnitOptions()
		# TolFreq.ValueKindOptions is set in PopulateHeaderData() from values set in SetTolFreq()
		self.UEL = '' # unmitigated event likelihood (outcome frequency) of FT
		self.OutcomeUnit = '' # ? not used ? assumed same as unit of TolFreq ?
		self.TargetUnit = '' # 'RRF' or 'PFD' or 'PFH'
		self.RRF = '' # required value of RRF, PFD or PFH to meet tol freq (str)
		self.SIL = '' # calculated SIL target (str)
		# make list of names of numerical values that need lists of unit options, ValueKind options etc.
		self.NumericalValues = ['TolFreq']
		self.BackgColour = '0,0,0'
		self.TextColour = '0,0,0'
		self.SizeXInCU = self.SizeYInCU = self.SizeXInPx = self.SizeYInPx = 10
		self.PosXInCU = self.PosYInCU = 0 # position relative to canvas origin, in canvas coords
		self.PosXInPx = self.PosYInPx = 0 # absolute position on display device in pixels, taking zoom and pan into account
			# (needed for testing mouse hits)
		self.Bitmap = wx.Bitmap(width=10, height=10, depth=wx.BITMAP_SCREEN_DEPTH)

	def CreateTextElements(self):
		# create elements for text items in FT header. Return list of elements
		ColourLabelBkg = (0x80, 0x3E, 0x51) # plum
		ColourLabelFg = (0xFF, 0xFF, 0xFF) # white
		ColourContentBkg = (0x6A, 0xDA, 0xBD) # mint green
		ColourContentFg = (0x00, 0x00, 0x00) # black
		Col1XStartInCU = 200 # x-coord of left edge of column 1 in canvas coords (redundant, X sizes get overridden later)

		# internal names must match attrib names in FTObjectInCore instance
		SIFNameLabel = TextElement(self.FT, Row=0, ColStart=0, ColSpan=1, StartX=0, EndX=Col1XStartInCU-1,
			HostObject=self, InternalName='SIFNameLabel')
		SIFName = TextElement(self.FT, Row=0, ColStart=1, ColSpan=3, StartX=Col1XStartInCU, EndX=999,
			HostObject=self, InternalName='SIFName', EditBehaviour='Text', MaxWidthInCU=600)
		RevLabel = TextElement(self.FT, Row=1, ColStart=0, ColSpan=1, StartX=0, EndX=Col1XStartInCU-1,
			HostObject=self, InternalName='RevLabel')
		Rev = TextElement(self.FT, Row=1, ColStart=1, ColSpan=1, StartX=Col1XStartInCU, EndX=499,
			HostObject=self, InternalName='Rev', EditBehaviour='Text', MaxWidthInCU=200)
		ModeLabel = TextElement(self.FT, Row=1, ColStart=2, ColSpan=1, StartX=500, EndX=749,
			HostObject=self, InternalName='ModeLabel')
		self.OpModeComponent = TextElement(self.FT, Row=1, ColStart=3, ColSpan=1, StartX=750, EndX=999,
			HostObject=self, InternalName='OpMode', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName')
		self.RRLabel = TextElement(self.FT, Row=2, ColStart=0, ColSpan=1, StartX=0, EndX=Col1XStartInCU-1,
			HostObject=self, InternalName='RRLabel', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName')
		self.RRComponent = TextElement(self.FT, Row=2, ColStart=1, ColSpan=3, StartX=Col1XStartInCU, EndX=749,
			HostObject=self, InternalName='RR', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName')
		SeverityLabel = TextElement(self.FT, Row=3, ColStart=0, ColSpan=1, StartX=0, EndX=Col1XStartInCU-1,
			HostObject=self, InternalName='SeverityLabel')
		self.SeverityComponent = TextElement(self.FT, Row=3, ColStart=1, ColSpan=1, StartX=Col1XStartInCU, EndX=499,
			HostObject=self, InternalName='Severity', EditBehaviour='Choice', ObjectChoices=[], DisplAttrib='HumanName')
		TolFreqLabel = TextElement(self.FT, Row=4, ColStart=0, ColSpan=1, StartX=0, EndX=Col1XStartInCU-1,
			HostObject=self, InternalName='TolFreqLabel')
		TolFreq = TextElement(self.FT, Row=4, ColStart=1, ColSpan=1, StartX=Col1XStartInCU, EndX=499,
			HostObject=self, InternalName='TolFreq', EditBehaviour='EditInControlPanel',
			ControlPanelAspect='CPAspect_NumValue')
		UELLabel = TextElement(self.FT, Row=4, ColStart=2, ColSpan=1, StartX=500, EndX=749,
			HostObject=self, InternalName='UELLabel')
		UEL = TextElement(self.FT, Row=4, ColStart=3, ColSpan=1, StartX=750, EndX=999,
			HostObject=self, InternalName='UEL')
		RRFLabel = TextElement(self.FT, Row=5, ColStart=0, ColSpan=1, StartX=0, EndX=Col1XStartInCU-1,
			HostObject=self, InternalName='RRFLabel')
		RRF = TextElement(self.FT, Row=5, ColStart=1, ColSpan=1, StartX=Col1XStartInCU, EndX=499,
			HostObject=self, InternalName='RRF')
		SILLabel = TextElement(self.FT, Row=5, ColStart=2, ColSpan=1, StartX=500, EndX=749,
			HostObject=self, InternalName='SILLabel')
		SIL = TextElement(self.FT, Row=5, ColStart=3, ColSpan=1, StartX=750, EndX=999,
			HostObject=self, InternalName='SIL')
		# make lists of label and content elements (used for setting colours, below)
		LabelEls = [SIFNameLabel, RevLabel, ModeLabel, self.RRLabel, SeverityLabel, TolFreqLabel, UELLabel, RRFLabel, SILLabel]
		self.ContentEls = [SIFName, Rev, self.OpModeComponent, self.RRComponent, RRF, self.SeverityComponent, TolFreq,
			UEL, RRF, SIL]

		# populate labels (content elements get populated in PopulateHeaderData() )
		SIFNameLabel.Text.Content = _('SIF name')
		RevLabel.Text.Content = _('Revision')
		ModeLabel.Text.Content = _('Operating mode')
		self.RRLabel.Text.Content = _('Risk receptors')
		SeverityLabel.Text.Content = _('Severity')
		TolFreqLabel.Text.Content = _('Tolerable freq')
		UELLabel.Text.Content = _('UEL')
		RRFLabel.Text.Content = _('RRF target')
		SILLabel.Text.Content = _('SIL target')

		# set element colours
		for El in LabelEls:
			El.Text.Colour = ColourLabelFg
			El.BkgColour = ColourLabelBkg
		for El in self.ContentEls:
			El.Text.Colour = ColourContentFg
			El.BkgColour = ColourContentBkg

		# return all the elements in a list
		return [SIFNameLabel, SIFName, RevLabel, Rev, ModeLabel, self.OpModeComponent, self.RRLabel, self.RRComponent,
				SeverityLabel, self.SeverityComponent, TolFreqLabel, TolFreq, UELLabel, UEL, RRFLabel, RRF, SILLabel, SIL]

	def CalculateSize(self, Zoom, PanX, PanY):
		# populate text elements, calculate overall size of header, set pos and size attributes of header and its components
		# PanX, PanY args not used

		def PopulateTextElements(Elements):
			# put required values into all text elements apart from labels
			# The following list contains (attribs of header, element's InternalName)
			AttribInfo = [('SIFName', 'SIFName'), ('Rev', 'Rev'), ('OpMode', 'OpMode'), ('RR', 'RR'),
						  ('RRF', 'RRF'), ('SIL', 'SIL')]
			# put the content into the elements
			for (Attrib, Name) in AttribInfo:
				ElementNamed(Elements, Name).Text.Content = self.__dict__[Attrib]
			# populate tolerable frequency, with value and unit
			ElementNamed(Elements, 'TolFreq').Text.Content = self.TolFreq.Value + ' ' + self.TolFreq.Unit.HumanName
			# populate other values that have units. The list contains (value attrib, unit attrib, element's InternalName)
#			AttribInfoWithUnits = [('TolFreq', 'TolFreqUnit', 'TolFreq'), ('UEL', 'OutcomeUnit', 'UEL')]
			AttribInfoWithUnits = [('UEL', 'OutcomeUnit', 'UEL')]
			for (ValueAttrib, UnitAttrib, Name) in AttribInfoWithUnits:
				ElementNamed(Elements, Name).Text.Content = self.__dict__[ValueAttrib] + ' ' + self.__dict__[UnitAttrib]

		# start of main procedure for FTHeader's CalculateSize()
		HeaderBorderX = HeaderBorderY = 20  # outer border in canvas coords
		GapBetweenCols = GapBetweenRows = 5  # in canvas coords
		MinColWidth = 40 # in canvas coords
		PopulateTextElements(self.Elements)  # put required text values in the elements
		# calculate height of each "sizer" row in canvas coords
		ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs = CalculateRowAndColumnDimensions(
			self.Elements, GapBetweenCols, GapBetweenRows, MinColWidth, HeaderBorderX, HeaderBorderY)
		# set element X and Y positions and sizes according to row heights. Positions are relative to the header bitmap,
		# so no need to take Pan into account
		for El in self.Elements:
			El.StartX = El.PosXInCU = ColStartXs[El.ColStart] # gradually getting rid of StartX/Y
			El.EndX = El.EndXInCU = ColEndXs[El.ColStart + El.ColSpan - 1]
			El.SizeXInCU = El.EndXInCU - El.PosXInCU
			El.StartY = El.PosYInCU = RowStartYs[El.Row]
			El.EndY = El.EndYInCU = RowEndYs[El.Row]
			El.SizeYInCU = El.EndYInCU - El.PosYInCU
			El.PosXInPx, El.PosYInPx = utilities.ScreenCoords(El.PosXInCU, El.PosYInCU, Zoom, PanX=self.FT.PanX, PanY=self.FT.PanY)
			EndXInPx, EndYInPx = utilities.ScreenCoords(El.EndXInCU, El.EndYInCU,
				Zoom, PanX=self.FT.PanX, PanY=self.FT.PanY)
			El.SizeXInPx = EndXInPx - El.PosXInPx + 1
			El.SizeYInPx = EndYInPx - El.PosYInPx + 1
		# calculate size (canvas and screen units) of FTHeader
		self.SizeXInCU = max([El.EndXInCU for El in self.Elements]) - GapBetweenRows + HeaderBorderX
		self.SizeYInCU = RowEndYs[-1] - GapBetweenRows + HeaderBorderY  # remove bottom "gap", add bottom border
		self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
		self.SizeYInPx = int(round(self.SizeYInCU * Zoom))

	def RenderIntoBitmap(self, Zoom): # draw header in self.Bitmap. Should be called after CalculateSize()

		def DrawElements(DC, Elements, Zoom, ComponentNameToHighlight=''): # render header's elements in DC
			BackBoxRoundedness = 5 # for text elements, how rounded the background boxes' corners are
			for El in Elements:
				# render element, including any background box with highlight, in DC
				El.Draw(DC, Zoom, BackBoxRoundedness=BackBoxRoundedness,
					Highlight=(El.InternalName == ComponentNameToHighlight))

		# start of main procedure for RenderIntoBitmap()
		# make bitmap
		self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		# make a DC for drawing
		DC = wx.MemoryDC(self.Bitmap)
		# draw elements into the bitmap
		DrawElements(DC, self.Elements, Zoom, self.ComponentNameToHighlight)

	def AllClickableObjects(self, SelectedOnly=False, VisibleOnly=True):
		# return list of all elements in header that should respond to mouse clicks
		# If SelectedOnly (bool), only return elements that are currently selected; similarly for VisibleOnly (bool)
		assert isinstance(SelectedOnly, bool)
		assert isinstance(VisibleOnly, bool)
		return [ThisEl for ThisEl in self.Elements
			if ((ThisEl.Selected or not SelectedOnly) and (ThisEl.Visible or not VisibleOnly))]

class FTBoxyObject(object): # superclass of vaguely box-like FT components for use in FTForDisplay. Used to avoid duplicate
	# definitions of some attributes and methods

	def __init__(self, **Args):
		object.__init__(self)
		self.HostFT = Args.get('HostFT', None)
		self.ConnectTo = [] # object instances connected horizontally to the right of this instance
		self.Clickable = True # bool; whether instance is intended to respond to user clicks
		self.Visible = True # bool; whether instance would be visible if currently panned onto the display device
		self.Connectable = True # whether instances of this class can be connected
		self.Selected = False # bool; whether currently user-selected i.e. highlighted
		self.ColNo = Args.get('ColNo') # (int) column number (index in HostFT.Columns) in which this instance lives

	def MouseHit(self, MouseXInPx, MouseYInPx, TolXInPx, TolYInPx):
		# returns (str) hotspot hit in FTBoxyObject instance, or None if not hit
		# Hotspots can be: "Whole" (whole object hit)
		assert isinstance(MouseXInPx, (float, int))
		assert isinstance(MouseYInPx, (float, int))
		assert isinstance(TolXInPx, (float, int)) # mouse hit tolerance in pixels
		assert isinstance(TolYInPx, (float, int))
		# test if hotspot "Whole" hit
		if (MouseXInPx - TolXInPx >= self.PosXInPx) and (MouseYInPx - TolYInPx >= self.PosYInPx) and \
			(MouseXInPx + TolXInPx <= self.PosXInPx + self.SizeXInPx) and \
			(MouseYInPx + TolYInPx <= self.PosYInPx + self.SizeYInPx):
			return "Whole"
		else: return None

	def HorizontalLineYInCU(self):  # return y coord of horizontal part of connecting line to/from this object
		return int(round(self.PosYInCU + 0.5 * self.SizeYInCU))

	def AllClickableObjects(self, SelectedOnly=False, VisibleOnly=True):
		# return list of all elements in FT element object that should respond to mouse clicks
		# If SelectedOnly (bool), only return elements that are currently selected; similarly for VisibleOnly (bool)
		# currently this procedure is the same as the version in class FTEvent
		assert isinstance(SelectedOnly, bool)
		assert isinstance(VisibleOnly, bool)
		return [El for El in self.AllElements if El.IsClickable
			if (El.Selected or not SelectedOnly) if (El.Visible or not VisibleOnly)]


class TextElement(FTBoxyObject): # object containing a text object and other attributes and methods needed to render it
	# Consists of a single text inside a coloured box. It's a component of an FTHeader or FTEvent.

	def __init__(self, FT, Row=0, RowBase=0, ColStart=0, ColSpan=1, EndX=200, MinHeight=10, InternalName='',
				 HostObject=None, **Args):
		# HostObject: the FTHeader or FTEvent instance containing this TextElement instance
		# Args can include:
		# 	HorizAlignment ('Left', 'Centre' or 'Right') (defaults to Centre if not specified)
		#	MaxWidthInCU (int) max width of component containing the text (defaults to 999)
		#	ControlPanelAspect (str) name of aspect to show in Control Panel when this element has focus
		#	EditBehaviour (str): indicates required behaviour for edit-in-place. Can be:
		#		'Text': provide textbox prefilled with the component's display value
		#		'Choice': provide choice widget
		#		'EditInControlPanel': don't allow edit-in-place; editing allowed only in a control panel aspect
		FTBoxyObject.__init__(self, **Args)
		assert isinstance(FT, FTForDisplay)
		assert isinstance(HostObject, (FTHeader, FTEvent, FTGate, FTConnector))
		assert Args.get('HorizAlignment', 'Centre') in ['Left', 'Centre', 'Right']
		self.FT = FT
		self.HostObject = HostObject
		self.Row = Row # row of grid in which text is located
		self.RowBase = RowBase # relative row of grid within a subgroup of elements
		self.ColStart = ColStart # column of grid in which text starts (int counting from 0)
		self.ColSpan = ColSpan # how many columns of grid are spanned by the text (int)
		self.PosXInCU = 0 # X-coord (canvas coords) of text container left end
		self.StartY = 0 # Y-coord (canvas coords) of text container top edge, relative to whole of header.
		self.EndX = self.EndXInCU = EndX # similar for right end of container (not the actual text in the container)
		self.MinSizeXInCU = 100 # minimum width in canvas coords
		self.MinSizeYInCU = MinHeight # minimum height (canvas coords) for elements that can stretch
		self.PosZ = 0 # z-coordinate
		self.FillXSpace = True # whether element should expand to fill available space in X direction
		self.Text = text.TextObject()
		self.Text.PointSize = 20 # default size before zoom
		self.Text.Font = wx.Font(pointSize=12, style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL,
			family=DefaultFontFamily).GetFaceName() # system name for actual font used (str)
		self.Text.ParaHorizAlignment = Args.get('HorizAlignment', 'Centre') # centre aligned horizontally by default
		self.InternalName = InternalName # name used to identify specific elements
		self.BkgColour = (0x40, 0x40, 0x40)
		self.Visible = True
		self.Selected = False # whether highlighted as part of user selection
		self.IsClickable = True
		self.MaxWidthInCU = 999
		# fetch any remaining attribs supplied in Args
		for (Attrib, Value) in Args.items(): setattr(self, Attrib, Value)

	def MinTextXat(self, TextIdentifier=0, StartY=0, EndY=10):
		# returns minimum X coord (canvas coords) available for text within element in the Y-range StartY to EndY
		return self.PosXInCU

	def MaxComponentXat(self, TextIdentifier=0, StartY=0, EndY=10):
		# returns maximum X coord (canvas coords) permitted for component containing text,
		# in the Y-range StartY to EndY
		# This is used for line break calculation in module text
		return self.PosXInCU + self.MaxWidthInCU

	def MaxTextXat(self, TextIdentifier=0, StartY=0, EndY=10):
		# returns maximum X coord (canvas coords) that text can occupy within component, assuming component size is
		# already fixed, in the Y-range StartY to EndY
		# This is used for text centring or right alignment in module text
		return self.EndXInCU - 1

	def MinTextY(self, TextIdentifier=0): # returns min Y coord (canvas coords) at which text will be drawn in the element
		# (relative to canvas, not relative to element)
		# this is used by text drawing routines in text module
		return self.StartY + TextElementTopBufferInCU

	def MaxTextY(self, TextIdentifier=0): # returns max Y coord (canvas coords) at which text can be drawn in the element
		return self.StartY + 999 # effectively unlimited Y-space for text

	def TextYOffsetInElementInCU(self, TextIdentifier=0):
		# returns number of canvas units by which text is offset from the top of the element
		return TextElementTopBufferInCU

	def TextStandoutBackColour(self, TextIdentifier=0): # return colour of "standing out" text background box
		return (0xc0, 0xc0, 0xc0) # fudge for now

	def RequiredTextPointSize(self, TextIdentifier, OrigPointSize, ParentSizeBasis):
		# return required point size (integer) of text in Element, based on change between Element's current size and parms in SizeBasis
		# refer to corresponding procedure in Tuti module 'shapes'
		# may never be needed (it's intended for animations)
		return OrigPointSize

	def GetMinSizeInCU(self): # calculate property MinSize - in canvas coords
		SizeX, TopY, BottomY = text.TextSize(self, TextIdentifier=0, CanvZoomX=1.05, CanvZoomY=1.05)
			# zoom args set to 1 so that we get canvas units, with a buffer to allow for rounding errors
			# (buffer needed to avoid sudden line breaks during zoom)
		return max(self.MinSizeXInCU, SizeX), max(self.MinSizeYInCU, BottomY - TopY)

	MinSizeInCU = property(fget=GetMinSizeInCU)

	def Draw(self, DC, Zoom, **Args): # render text element, including background box, in DC
		# Optional arg BackBoxRoundedness: radius of background box corner curvature, in canvas coords
		# Optional arg Highlight (bool): whether to highlight the background box
		DefaultRound = 3 # default value of BackBoxRoundedness if not supplied
		# set background colour according to whether to highlight
		BkgColour = HighlightColour if Args.get('Highlight', False) else self.BkgColour
		DC.SetPen(wx.Pen(BkgColour))
		DC.SetBrush(wx.Brush(BkgColour))
		# find starting coords in pixels relative to the header/column bitmap (need not take Pan into account)
		ThisStartX, ThisStartY = utilities.ScreenCoords(self.PosXInCU, self.PosYInCU, Zoom=Zoom, PanX=0, PanY=0)
		DC.DrawRoundedRectangle(ThisStartX, ThisStartY, (self.EndXInCU - self.PosXInCU) * Zoom,
			(self.EndYInCU - self.PosYInCU) * Zoom, radius=Args.get('BackBoxRoundedness', DefaultRound) * Zoom)
		# draw the text on top of the box
		text.DrawTextInElement(self, DC, self.Text, TextIdentifier=0, CanvZoomX=Zoom,
			CanvZoomY=Zoom, PanX=0, PanY=0, VertAlignment='Top')

	def HandleMouseLClickOnMe(self, **Args): # handle mouse left button single click on TextElement instance
		# first, request control frame to show appropriate aspect in control panel
#		# find out which object contains the parameter to be edited, if any
#		DataHostObj = self.FT if isinstance(self.HostObject, FTHeader) else self.HostObject
		if getattr(self, 'ControlPanelAspect', None):
#			if isinstance(self.CurrentEditElement.HostObject, FTHeader):
#				ElementID = 'Header'
#				DatacoreHostObj = self.FT
#			else:
#				ElementID = self.CurrentEditElement.HostObject.ID
#				DatacoreHostObj = self.HostObject.FT
#			EditComponentInternalName = self.CurrentEditElement.InternalName
			self.FT.DisplDevice.GotoControlPanelAspect(AspectName=self.ControlPanelAspect,
				PHAObjInControlPanel=self.HostObject, ComponentInControlPanel=self.InternalName)
		if self.FT.PHAObj.EditAllowed: # proceed with editing only if allowed to edit in this instance of vizop
			# get absolute position of textbox for editing: position within element + column + FT, then apply zoom and pan
			Zoom = self.FT.Zoom
			# check if HostObject of this element is in a column; if so, get PosX/Y within the column
			if getattr(self.HostObject, 'Column', None):
				PosXInCol = self.HostObject.Column.PosXInCU
				PosYInCol = self.HostObject.Column.PosYInCU
			else:
				PosXInCol = PosYInCol = 0
			self.TextCtrlPosXInPxWithinDisplDevice, self.TextCtrlPosYInPxWithinDisplDevice = utilities.ScreenCoords(
				self.PosXInCU + self.HostObject.PosXInCU + PosXInCol,
				self.PosYInCU + self.HostObject.PosYInCU + PosYInCol, Zoom=Zoom,
				PanX=self.FT.PanX, PanY=self.FT.PanY)
			# provide appropriate widget for editing, depending on EditBehaviour and OpMode
			MyEditBehaviour = getattr(self, 'EditBehaviour', None)
			# disallow editing if not allowed in this OpMode
			if self.FT.OpMode not in getattr(self, 'EditInOpModes', core_classes.OpModes): MyEditBehaviour = None
			# check if this object can be edited depending on specific conditions
			ThisEventType = getattr(self.HostObject, 'EventType', None)
			if self.InternalName == 'EventValue' and ThisEventType == 'SIFFailureEvent': MyEditBehaviour = None
			elif self.InternalName == 'EventValueUnit' and ThisEventType == 'SIFFailureEvent': MyEditBehaviour = None
			elif self.InternalName == 'EventValueKind' and ThisEventType == 'SIFFailureEvent': MyEditBehaviour = None
			if MyEditBehaviour == 'Text':
				# make and populate a TextCtrl for editing
				self.EditTextCtrl = wx.TextCtrl(parent=self.FT.DisplDevice, value=self.Text.Content,
					pos=(self.TextCtrlPosXInPxWithinDisplDevice, self.TextCtrlPosYInPxWithinDisplDevice),
					size=(self.SizeXInCU * Zoom, (self.SizeYInCU + 5) * Zoom),
					style=wx.TE_PROCESS_ENTER | wx.HSCROLL | wx.TE_BESTWRAP) # + 5 for better visual effect
				self.EditTextCtrl.SetFocus()
				self.EditTextCtrl.SetInsertionPointEnd() # set cursor to end of existing text
				self.EditTextCtrl.SetFont(wx.Font(pointSize=int(round(self.Text.PointSize * Zoom)), family=DefaultFontFamily,
					style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL, faceName=self.Text.Font))
				self.EditTextCtrl.SetForegroundColour(self.Text.Colour)
				self.EditTextCtrl.SetBackgroundColour(self.BkgColour)
				self.EditTextCtrl.Bind(wx.EVT_TEXT_ENTER, self.FT.EndEditingOperation)
				self.EditTextCtrl.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown) # for detection of Esc keypresses
				# store info required to close out editing when finished
				self.FT.CurrentEditTextCtrl = self.EditTextCtrl
				self.FT.CurrentEditElement = self
				self.FT.DisplDevice.SetKeystrokeHandlerOnOff(On=False) # turn off keypress shortcut detection in control frame
			elif MyEditBehaviour == 'Choice':
				# make and populate a Choice widget
				self.EditChoice = wx.Choice(parent=self.FT.DisplDevice,
					pos=(self.TextCtrlPosXInPxWithinDisplDevice, self.TextCtrlPosYInPxWithinDisplDevice - 2),
					size=((self.SizeXInCU + 20) * Zoom, (self.SizeYInCU + 3) * Zoom),
					choices=[getattr(c, self.DisplAttrib) for c in self.ObjectChoices])
				self.EditChoice.SetFocus()
#				self.EditChoice.SetFont(wx.Font(pointSize=int(round(self.Text.PointSize * Zoom)), family=DefaultFontFamily,
#					style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL, faceName=self.Text.Font))
				self.EditChoice.SetFont(wx.Font(wx.FontInfo(pointSize=int(round(self.Text.PointSize * Zoom))).Family(wx.FONTFAMILY_SWISS)))
				self.EditChoice.SetForegroundColour(self.Text.Colour)
				self.EditChoice.SetBackgroundColour(self.BkgColour)
				# pre-select the current selection in the choice box
				self.EditChoice.SetSelection([c.Applicable for c in self.ObjectChoices].index(True))
				self.FT.CurrentEditChoice = self.EditChoice
				self.FT.CurrentEditElement = self
				self.FT.DisplDevice.SetKeystrokeHandlerOnOff(On=False) # turn off keypress shortcut detection in control frame
				self.EditChoice.Bind(wx.EVT_CHOICE, self.OnEditChoice) # bind handler for click in choice box
			elif MyEditBehaviour == 'EditInControlPanel': # can't edit in place, editing in control panel only
				pass

	def OnEditChoice(self, Event): # handle click in choice box during editing
		self.FT.EndEditingOperation()

	def OnKeyDown(self, Event): # handle key press during editing; used for catching Esc key
		if Event.KeyCode == wx.WXK_ESCAPE: self.FT.EndEditingOperation(AcceptEdits=False)
		else: Event.Skip() # allow editing widget to handle keypress normally

class FTEvent(FTBoxyObject): # FT event object. Rendered by drawing text into bitmap (doesn't use native widgets or sizer)
	# Used for causes, IPLs, intermediate events, final events
	NeedsConnectButton = True # whether to provide connect buttons
	# Attribs are used by ParseFTData() to populate object's attributes from data transferred from datacore (may be redundant)
	Attribs = [(info.IDTag, int, False), ('EventTypeHumanName', str, False), ('Numbering', str, False), ('Description', str, False), ('Value', str, False),
		('ValueUnit', str, False), ('Status', int, False), ('CanEditValue', bool, False), ('ShowActionItems', bool, False), ('BackgColour', 'rgb', False),
		('DescriptionComment', str, True), ('ValueComment', str, True), ('ValueUnitComment', str, True),
		('ValueKindComment', str, True), ('ActionItems', str, True), ('ConnectTo', int, True)]

	def __init__(self, Column, **Args):
		# Args must include FT (the FTForDisplay instance containing this element)
		assert isinstance(Column, FTColumn)
		assert 'FT' in Args
		FTBoxyObject.__init__(self, **Args)
		self.Column = Column # the FTColumn instance hosting the FTEvent instance
		self.FT = Args['FT']
		self.InitializeData()
		(self.TopFixedEls, self.ValueFixedEls) = self.CreateFixedTextElements()
		self.BorderColour = (0x35, 0x6d, 0x5f) # darker green
		self.BackgroundColour = (0x54, 0xae, 0x97) # slightly darker than text entry boxes
		self.MaxElementsConnectedToThis = FTEventInCore.MaxElementsConnectedToThis

	def InitializeData(self):
		# attribs transferred from datacore
		self.ID = 0
		self.IsIPL = False # Marker for IPLs. We may want to make them look different (indent? colour?)
		self.EventTypeHumanName = ''
		self.Numbering = '' # numbering string representation used by Viewport
		self.EventDescription = ''
		self.Value = ''
		self.ValueUnit = ''
		self.ValueKind = ''
		self.CanEditValue = False
		self.ShowActionItems = False
		self.BackgColour = '0,0,0' # rgb colour as str
		self.EventDescriptionComments = [] # str values
		self.ValueComments = [] # str values
		self.ShowDescriptionComments = True # whether description comments are visible
		self.ShowValueComments = True # whether value comments are visible
		self.ActionItems = [] # str values
		self.ShowActionItems = True
		self.EventCommentWidgets = []
		self.ValueCommentWidgets = []
		# attribs determined locally, not transferred from datacore
		self.Status = '' # button status
		self.SizeXInPx = self.SizeXInCU = 10 # width in screen pixels and canvas units
		self.SizeYInPx = self.SizeYInCU = 10
		self.PosXInCU = self.PosYInCU = 0 # position relative to the origin of the column it belongs to, in canvas units
		self.PosXInPx = self.PosYInPx = 0  # absolute position on display device in pixels, taking zoom and pan into account
			# (needed for testing mouse hits)
		self.PosZ = 0 # z-coordinate
		self.Buffer = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		self.Linked = False # whether event is linked to others; info provided by DataCore
		self.CollapseGroups = [] # FTCollapseGroup objects this object belongs to
		self.ValueProblemID = '' # ID of NumValueProblem instance, or '' if no problem (not used yet)
		self.ValueProblemObjectID = '' # ID of an FT object that is causing a value problem in this object. '' = no problem
		self.ShowProblemIndicator = False # whether problem indicator button is visible
		self.Bitmap = wx.Bitmap(width=10, height=10, depth=wx.BITMAP_SCREEN_DEPTH)

	# colours for text and background are defined for individual text Elements, not for whole FTEvent

	def CreateFixedTextElements(self):
		# create elements for fixed text items in FTEvent. Return (list of elements at top of FTEvent, list of elements relating to FTEvent's value)
		HeaderLabelBkg = (0xdb, 0xf7, 0xf0) # pale green
		ColourLabelBkg = (0x80, 0x3E, 0x51) # plum
		ColourLabelFg = (0xFF, 0xFF, 0xFF) # white
		ColourContentBkg = (0x6A, 0xDA, 0xBD) # mint green
		ColourContentFg = (0x00, 0x00, 0x00) # black

		# column widths: 100, 100, 100, 50, 50
		# any element with MinHeight parm set is growable in the y axis to fit the text.
		# it should be assigned to the Row that it can force to grow
		# Elements in variable row number (after Comments row) have RowBase parm, which defines the row number if there
		# are no comments visible
		# InternalNames must match XML tags stored in TextComponentHash's in FT object in datacore
		# EditInOpModes attrib: which OpModes the component can be user-edited in (if omitted, allowed in all OpModes)
		self.EventTypeComponent = TextElement(self.FT, Row=0, ColStart=0, ColSpan=7, EndX=399,
			HostObject=self, InternalName='EventType', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName') # DisplAttrib is the attrib of the ChoiceItem instance to display in the choice box
		self.EventNumberingComponent = TextElement(self.FT, Row=1, ColStart=0, ColSpan=1, EndX=399,
			HostObject=self, InternalName=info.NumberingTag)
		self.EventDescriptionComponent = TextElement(self.FT, Row=1, ColStart=1, ColSpan=5, EndX=299, MinHeight=25,
			HostObject=self, InternalName='EventDescription', EditBehaviour='Text', HorizAlignment='Left',
			MaxWidthInCU=400)
		EventLinkedButton = ButtonElement(self.FT, Row=2, ColStart=1, ColSpan=1, StartX=300, EndX=349,
			HostObject=self, InternalName='EventLinkedButton')
			# button elements have Status attribute that can be 'Out', 'In', 'Pressed' (user currently clicking it), or 'Alert' (flashing a warning)
		EventGroupedButton = ButtonElement(self.FT, Row=2, ColStart=2, ColSpan=1, StartX=350, EndX=399,
			HostObject=self, InternalName='EventGroupedButton')
		EventCommentButton = ButtonElement(self.FT, Row=1, ColStart=6, ColSpan=1, StartX=300, EndX=349,
			HostObject=self, InternalName='EventCommentButton')
		EventActionItemButton = ButtonElement(self.FT, Row=2, ColStart=3, ColSpan=1, StartX=350, EndX=399,
			HostObject=self, InternalName='EventActionItemButton')
		EventValue = TextElement(self.FT, RowBase=0, ColStart=0, ColSpan=1, EndX=99, EditBehaviour='Text',
			HostObject=self, InternalName='Value') # internal name = 'Value' to match attrib name in Core object
		self.EventValueUnitComponent = TextElement(self.FT, RowBase=0, ColStart=1, ColSpan=2, EndX=199,
			HostObject=self, InternalName='EventValueUnit', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName')
		self.EventValueKindComponent = TextElement(self.FT, RowBase=0, ColStart=3, ColSpan=2, EndX=299,
			HostObject=self, InternalName='EventValueKind', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName')
		ValueCommentButton = ButtonElement(self.FT, RowBase=0, ColStart=6, ColSpan=1, StartX=300, EndX=349,
			HostObject=self, InternalName='ValueCommentButton')
		self.ValueProblemButton = ButtonElement(self.FT, RowBase=0, ColStart=5, ColSpan=1, StartX=350, EndX=399,
			HostObject=self, InternalName='ValueProblemButton')

		# make lists of elements: TopEls at top of event, ValueEls relating to event value
		TopEls = [self.EventTypeComponent, self.EventNumberingComponent, self.EventDescriptionComponent,
			EventLinkedButton, EventGroupedButton, EventCommentButton,
			EventActionItemButton]
		ValueEls = [EventValue, self.EventValueUnitComponent, self.EventValueKindComponent, ValueCommentButton,
			self.ValueProblemButton]
		# set text element colours
		for El in TopEls + ValueEls:
			if type(El) is TextElement:
				El.Text.Colour = ColourContentFg
				El.BkgColour = ColourContentBkg
		self.EventTypeComponent.BkgColour = HeaderLabelBkg
		return TopEls, ValueEls

	def CreateVariableTextElements(self):
		# create elements that vary depending on display settings - currently comments and action items
		# return list of elements for each of description comments, action items, and value comments
		ColourLabelBkg = (0x80, 0x3E, 0x51) # plum
		ColourLabelFg = (0xFF, 0xFF, 0xFF) # white
		ColourContentBkg = (0x6A, 0xDA, 0xBD) # mint green
		ColourContentFg = (0x00, 0x00, 0x00) # black

		# Make description comments, value comments and action items
		DescrComments = []
		ValueComments = []
		ActionItems = []
		for (CommentElementList, CommentList, ShowFlag, CommentLabel) in \
			[(DescrComments, self.EventDescriptionComments, self.ShowDescriptionComments, _('Comment')),
			 (ValueComments, self.ValueComments, self.ShowValueComments, _('Comment')),
			 (ActionItems, self.ActionItems, self.ShowActionItems, _('Action items'))]:
			if ShowFlag: # check whether this set of items is required to be displayed
				for (CommentIndex, Comment) in enumerate(CommentList):
					CommentElementList.append(TextElement(self.FT, RowBase=CommentIndex, ColStart=1, ColSpan=5,
						EndX=399, MinHeight=25, HostObject=self))
					CommentElementList[-1].Text.Content = Comment
					CommentElementList[-1].Text.Colour = ColourContentFg
					CommentElementList[-1].BkgColour = ColourContentBkg
					CommentElementList[-1].Text.ParaHorizAlignment = 'Left'
				# add item label (e.g. 'Comment') at left side of first row of items
				CommentElementList.append(TextElement(self.FT, RowBase=0, ColStart=0, ColSpan=1, EndX=99,
					HostObject=self))
				CommentElementList[-1].Text.Content = CommentLabel
				CommentElementList[-1].Text.Colour = ColourLabelFg
				CommentElementList[-1].BkgColour = ColourLabelBkg
				CommentElementList[-1].Text.ParaHorizAlignment = 'Centre'
		return (DescrComments, ValueComments, ActionItems)

	def RenderIntoBitmap(self, Zoom): # draw FTEvent in self.Bitmap. Also calculates FTEvent size attributes

		def PopulateTextElements(Elements):
			# put required values into all fixed text components of this element
			# (variable elements are populated in CreateVariableTextElements() )
			# The following list contains (attribs of FTEvent, element's InternalName)
			# It's a combined list for both DescriptionElements and ValueElements, hence the "if" below
#			AttribInfo = [ ('EventTypeHumanName', 'EventType'), ('Value', 'EventValue'),
			AttribInfo = [ ('EventTypeHumanName', 'EventType'), ('Value', 'Value'),
				('ValueUnit', 'EventValueUnit'), ('ValueKind', 'EventValueKind') ]
			# put the content into the elements
			for (Attrib, Name) in AttribInfo:
				MatchingEl = ElementNamed(Elements, Name)
				if MatchingEl:
					MatchingEl.Text.Content = self.__dict__[Attrib]
			# put event numbering and description into respective fields
			DescriptionEl = ElementNamed(Elements, 'EventDescription')
			if DescriptionEl: DescriptionEl.Text.Content = self.EventDescription
			NumberingEl = ElementNamed(Elements, info.NumberingTag)
			if NumberingEl: NumberingEl.Text.Content = self.Numbering

		def SetElementSizesInCU():  # set sizes in canvas units of all elements in the FTEvent instance
			for ThisEl in self.AllElements:
				ThisEl.SizeXInCU, ThisEl.SizeYInCU = ThisEl.MinSizeInCU

		def SetButtonStati(Elements):
			# set 'Status' attributes of buttons in Elements. Need to call with Elements = TopEls + ValueEls
			for (ButtonName, Flag) in [('EventLinkedButton', self.Linked), ('EventGroupedButton', bool(self.CollapseGroups)),
									   ('EventCommentButton', bool(self.EventDescriptionComments)),
									   ('EventActionItemButton', bool(self.ActionItems)),
									   ('ValueCommentButton', bool(self.ValueComments))]:
				FoundButtonElement = ElementNamed(Elements, ButtonName)
				if FoundButtonElement:
					FoundButtonElement.Status = {True: 'In', False: 'Out'}[Flag]
			ValueProblemElement = ElementNamed(Elements, 'ValueProblemButton')
			if ValueProblemElement:
				ValueProblemElement.Status = {True: 'Alert', False: 'Out'}[(self.ValueProblemObjectID is None)]

		def DrawBackgroundBox(DC, Zoom): # draw FTEvent's background box in DC
			DC.SetPen(wx.Pen(self.BorderColour, width=1)) # for now, a 1 pixel border around the event. TODO make nicer and apply zoom
			DC.SetBrush(wx.Brush(self.BackgroundColour))
			# box is drawn in FTElement's own bitmap, so coords are relative to element (not using PosX/YInPx, which are relative to column)
			DC.DrawRectangle(0, 0, self.SizeXInPx, self.SizeYInPx)

		def DrawElements(DC, Elements, Zoom): # render FTEvent's elements in DC
			BackBoxRoundedness = 3 # for text elements, how rounded the background boxes' corners are
			for El in Elements:
				# render element, including any background box, in DC
				if getattr(El, 'Visible', True):
					El.Draw(DC, Zoom, BackBoxRoundedness=BackBoxRoundedness)

		# start of main procedure for RenderIntoBitmap()
		BorderX = BorderY = 10 # outer border in canvas coords
		GapBetweenRows = GapBetweenCols = 5 # in canvas coords
		MinColWidth = 40
		# create variable elements and build combined element list comprising fixed and variable elements
		(self.DescriptionCommentEls, self.ValueCommentEls, self.ActionItemEls) = self.CreateVariableTextElements()
		self.AllElements = BuildFullElementList(
			self.TopFixedEls, self.DescriptionCommentEls, self.ValueFixedEls, self.ValueCommentEls, self.ActionItemEls)

		PopulateTextElements(self.AllElements) # put required text values in the elements
		SetElementSizesInCU()
		SetButtonStati(self.AllElements) # set button elements to required status
		# calculate height of each "sizer" row in canvas coords
		ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs = CalculateRowAndColumnDimensions(
			self.AllElements, GapBetweenCols, GapBetweenRows, MinColWidth, BorderX, BorderY)
		# set element X, Y positions according to column positions and row heights
		for El in self.AllElements:
			El.PosXInCU = ColStartXs[El.ColStart]
			El.EndXInCU = El.PosXInCU + sum([ColWidths[c] for c in range(El.ColStart, El.ColStart + El.ColSpan)]) - GapBetweenCols
			# if element should fill available X-space, adjust its X size to match available space
			if El.FillXSpace: El.SizeXInCU = El.EndXInCU - El.PosXInCU
			El.SizeXInPx = int(round(El.SizeXInCU * Zoom))
			El.PosXInPx = int(round(El.PosXInCU * Zoom))
			El.StartY = El.PosYInCU = RowStartYs[El.Row] # transitioning from StartY to PosYInCU; eventually should kill StartY
			El.EndYInCU = RowEndYs[El.Row]
			El.SizeYInCU = El.EndYInCU - El.PosYInCU
			El.SizeYInPx = int(round(El.SizeYInCU * Zoom))
		# calculate FTEvent size; removing gap after final row/col and adding borders at both edges
		self.SizeXInCU = max([El.EndXInCU for El in self.AllElements]) - GapBetweenCols + 2 * BorderX
		self.SizeYInCU = RowEndYs[-1] - GapBetweenRows + 2 * BorderY
		self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
		self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
		# make the bitmap
		self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		# make a DC for drawing
		DC = wx.MemoryDC(self.Bitmap)
		# draw background box, then elements, into the bitmap
		DrawBackgroundBox(DC, Zoom)
		DrawElements(DC, self.AllElements, Zoom)

class FTGate(FTBoxyObject): # object containing FT gates for display. These belong to FTColumn's.
	# Rendered by drawing into bitmap (doesn't use native widgets or sizer)
	NeedsConnectButton = True # whether to provide connect buttons
	# Attribs are used by ParseFTData() to populate object's attributes from data transferred from datacore (may be redundant)
	Attribs = [(info.IDTag, int, False), ('Algorithm', str, False), ('BackgColour', 'rgb', False), ('Style', str, False), ('Numbering', str, False),
		('Description', str, False), ('Value', str, False), ('ValueUnit', str, False), ('Status', int, False), ('CanEdit', bool, False),
		('DescriptionComment', str, True), ('ValueComment', str, True), ('ValueUnitComment', str, True), ('ConnectTo', int, True)]
	GateKindHash = {'AND': _('AND gate'), 'OR': _('OR gate'), 'MutExcOR': _('Mutually exclusive'),
		'NAND': _('NAND gate'), 'NOR': _('NOR gate'), '2ooN': _(u'≥2 out of N'), '3ooN': _(u'≥3 out of N')} # human readable names per algorithm

	def __init__(self, **Args): # attribs marked * below are named in quotes elsewhere: be careful if names changed
		FTBoxyObject.__init__(self, **Args)
		self.ID = None # must be defined by routine that creates new FTGate instance
		self.Column = Args['Column']
		self.FT = Args['FT']
		self.Algorithm = '' # *
		self.BackgColour = '0,0,0'
		self.Style = ''
		self.DetailedView = True # whether we are showing the detailed gate, or just a gate symbol
		self.Numbering = ''
		self.GateDescription = ''
		self.Value = ''
		self.ValueUnit = '' # *
		self.Status = 0
		self.ShowComments = False # whether comments are visible
		self.MadeBySystem = False # needed to determine whether gate can be deleted
		self.GateDescriptionComments = [] # str values
		self.ActionItems = [] # str values
		self.ShowActionItems = True
#		self.ConnectTo = [] # str values, ID's of connected items in next column (already defined in superclass)
		self.SizeXInCU = self.SizeXInPx = self.SizeYInCU = self.SizeYInPx = 10 # size in canvas units and screen pixels
		self.PosZ = 0 # z-coordinate
		self.Buffer = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		self.Linked = False # whether gate is linked to others; info provided by DataCore
		self.CollapseGroups = [] # FTCollapseGroup objects this gate belongs to
		self.ValueProblemObjectID = '' # ID of an FT object that is causing a value problem in this gate. '' = no problem
		self.ValueProblemID = '' # ID of NumProblemValue instance. '' = no problem
		(self.TopFixedEls, self.ValueFixedEls) = self.CreateFixedTextElements()
		self.Clickable = True # bool; whether instance is intended to respond to user clicks
		self.Visible = True # bool; whether it would be visible if currently panned onto the display device
		self.Selected = False # bool; whether currently user-selected i.e. highlighted
		self.MaxElementsConnectedToThis = FTGateItemInCore.MaxElementsConnectedToThis

	def CreateFixedTextElements(self):
		# create elements for fixed text items and buttons in FTGate. Return (list of elements at top of FTGate,
		# list of elements relating to FTGate's value)
		# column widths: 100, 100, 50, 50
		# any element with MinHeight parm set is growable in the y axis to fit the text.
		# it should be assigned to the Row that it can force to grow
		# Elements in variable row number (after Comments) have RowBase parm, which defines the row number if there
		# are no comments visible
		self.GateKind = TextElement(self.FT, Row=0, ColStart=0, ColSpan=4, EndX=299, HostObject=self,
			InternalName='GateKind', EditBehaviour='Choice', ObjectChoices=[], DisplAttrib='HumanName')
		self.GateStyleButton = ButtonElement(self.FT, Row=0, ColStart=4, ColSpan=1, StartX=200, EndX=249,
			HostObject=self, InternalName='GateStyleButton')
		self.GateDescription = TextElement(self.FT, Row=2, ColStart=0, ColSpan=2, EndX=199, MinHeight=50,
			HostObject=self, InternalName='GateDescription', EditBehaviour='Text')
		self.GateLinkedButton = ButtonElement(self.FT, Row=1, ColStart=3, ColSpan=1, StartX=200, EndX=249, HostObject=self, InternalName='GateLinkedButton')
		self.GateGroupedButton = ButtonElement(self.FT, Row=1, ColStart=4, ColSpan=1, StartX=250, EndX=299, HostObject=self, InternalName='GateGroupedButton')
		self.GateCommentButton = ButtonElement(self.FT, Row=2, ColStart=3, ColSpan=1, StartX=200, EndX=249, HostObject=self, InternalName='GateCommentButton')
		self.GateActionItemButton = ButtonElement(self.FT, Row=2, ColStart=4, ColSpan=1, StartX=250, EndX=299, HostObject=self, InternalName='GateActionItemButton')
		self.GateValue = TextElement(self.FT, RowBase=0, ColStart=0, ColSpan=1, EndX=99, HostObject=self, InternalName='GateValue')
		self.GateValueUnit = TextElement(self.FT, RowBase=0, ColStart=1, ColSpan=1, EndX=199, HostObject=self,
			InternalName='GateValueUnit', EditBehaviour='Choice', ObjectChoices=[],
			DisplAttrib='HumanName')
		self.ValueProblemButton = ButtonElement(self.FT, RowBase=0, ColStart=4, ColSpan=1, StartX=250, EndX=299,
			HostObject=self, InternalName='ValueProblemButton')
		# Gates don't have "value types" (it's always calculated) or "value comments"

		# make lists of elements: TopEls at top of event, ValueEls relating to event value
		TopEls = [self.GateKind, self.GateStyleButton, self.GateDescription, self.GateLinkedButton, self.GateGroupedButton,
			self.GateCommentButton, self.GateActionItemButton]
		ValueEls = [self.GateValue, self.GateValueUnit, self.ValueProblemButton]

		# set text element colours
		for El in TopEls + ValueEls:
			if type(El) is TextElement:
				El.Text.Colour = GateTextFgColour
				El.BkgColour = GateTextBkgColour

		return TopEls, ValueEls

	def CreateVariableTextElements(self):
		# create elements that vary depending on display settings - currently comments and action items
		# return list of elements for each of description comments and action items
		# Make description comments, value comments and action items
		DescrComments = []
		ActionItems = []
		for (CommentElementList, CommentList, ShowFlag, CommentLabel) in \
			[(DescrComments, self.GateDescriptionComments, self.ShowComments, _('Comment')),
			 (ActionItems, self.ActionItems, self.ShowActionItems, _('Action items'))]:
			if ShowFlag: # check whether this set of items is required to be displayed
				for (CommentIndex, Comment) in enumerate(CommentList):
					CommentElementList.append(TextElement(self.FT, RowBase=CommentIndex, ColStart=1, ColSpan=5,
						EndX=399, MinHeight=25, HostObject=self))
					CommentElementList[-1].Text.Content = Comment
					CommentElementList[-1].Text.Colour = GateTextFgColour
					CommentElementList[-1].BkgColour = GateTextBkgColour
					CommentElementList[-1].Text.ParaHorizAlignment = 'Left'
				# add item label (e.g. 'Comment') at left side of first row of items
				CommentElementList.append(TextElement(self.FT, RowBase=0, ColStart=0, ColSpan=1, EndX=99,
					HostObject=self))
				CommentElementList[-1].Text.Content = CommentLabel
				CommentElementList[-1].Text.Colour = GateLabelFgColour
				CommentElementList[-1].BkgColour = GateLabelBkgColour
				CommentElementList[-1].Text.ParaHorizAlignment = 'Centre'
		return (DescrComments, ActionItems)

	def RenderIntoBitmap_old(self, Zoom): # draw FTGate in its own self.Bitmap. Also calculates FTGate's size attributes
		# old version - superseded by new one developed from equivalent procedure in FTEvent class

		def PopulateTextElements(Elements):
			# put required values into all fixed text elements
			# (variable elements are populated in CreateVariableTextElements() )
			# The following list contains (attribs of FTGate, element's InternalName)
			AttribInfo = [ ('Description', 'GateDescription'), ('Value', 'GateValue'), ('ValueUnit', 'GateValueUnit') ]
			# put the content into the elements
			for (Attrib, Name) in AttribInfo:
				MatchingEl = ElementNamed(Elements, Name)
				if MatchingEl:
					MatchingEl.Text.Content = self.__dict__[Attrib]
			# put the gate kind into the respective element
				self.GateKind.Text.Content = FTGate.GateKindHash.get(self.Algorithm,
					_('<Undefined gate type>'))

		def SetButtonStati(Elements):
			# set 'Status' attributes of buttons in Elements. Old version, obsolete
			for (ButtonName, Flag) in [('GateLinkedButton', self.Linked), ('GateGroupedButton', bool(self.CollapseGroups)),
					('GateCommentButton', bool(self.GateDescriptionComments)), ('GateStyleButton', False),
					('GateActionItemButton', bool(self.ActionItems))]:
				FoundButtonElement = ElementNamed(Elements, ButtonName)
				if FoundButtonElement:
					FoundButtonElement.Status = {True: 'In', False: 'Out'}[Flag]
			ValueProblemElement = ElementNamed(Elements, 'ValueProblemButton')
			if ValueProblemElement:
				ValueProblemElement.Status = {True: 'Alert', False: 'Out'}[(self.ValueProblemObjectID is None)]

		def DrawElements(DC, Elements, Zoom): # render gate's elements in DC
			BackBoxRoundedness = 5 # for text elements, how rounded the background boxes' corners are
			for El in Elements:
				El.Draw(DC, Zoom, BackBoxRoundedness=BackBoxRoundedness) # render element, including any background box, in DC

		# start of main procedure for RenderIntoBitmap() for class FTGate
		BorderX = BorderY = 20 # outer border in canvas coords
		GapBetweenRows = GapBetweenCols = 10 # in canvas coords
		MinColWidth = 40
		# create variable elements and build combined element list comprising fixed and variable elements
		self.DescriptionCommentEls = self.CreateVariableTextElements()
		self.AllElements = BuildFullElementList(self.TopFixedEls, self.DescriptionCommentEls, self.ValueFixedEls)

		PopulateTextElements(self.AllElements) # put required text values in the elements
		SetButtonStati(self.AllElements) # set button elements to required status
		# calculate height of each "sizer" row in canvas coords
		ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs = CalculateRowAndColumnDimensions(self.AllElements, GapBetweenCols,
			GapBetweenRows, MinColWidth, BorderX, BorderY)
		# set element Y positions and sizes according to row heights TODO update based on changes in FTElement
		for El in self.AllElements:
			El.StartY = RowStartYs[El.Row]
			El.EndY = RowEndYs[El.Row]
		# calculate FTGate size
		self.SizeXInCU = max([El.EndX for El in self.AllElements]) + BorderX # the + BorderX adds right border space
		self.SizeYInCU = RowEndYs[-1] - GapBetweenRows + BorderY # remove bottom "gap", add bottom border
		self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
		self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
		# make the bitmap
		self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		# make a DC for drawing
		DC = wx.MemoryDC(self.Bitmap)
		# draw elements into the bitmap
		DrawElements(DC, self.AllElements, Zoom)

	def RenderIntoBitmap(self, Zoom): # draw FTGate in self.Bitmap. Also calculates FTGate size attributes
		# based on equivalent method in FTEvent class

		def PopulateTextElements(Elements):
			# put required values into all fixed text components of this element
			# (variable elements are populated in CreateVariableTextElements() )
			# The following list contains (attribs of FTGate, element's InternalName)
			# It's a combined list for both DescriptionElements and ValueElements, hence the "if" below
			AttribInfo = [ ('Description', 'GateDescription'), ('Value', 'GateValue'), ('ValueUnit', 'GateValueUnit'),
						   ('Numbering', info.NumberingTag)]
			# put the content into the elements
			for (Attrib, TagName) in AttribInfo:
				MatchingEl = ElementNamed(Elements, TagName)
				if MatchingEl:
					MatchingEl.Text.Content = self.__dict__[Attrib]
			# put the gate kind into the respective element
			self.GateKind.Text.Content = self.GateKindHash.get(self.Algorithm,
				_('<Undefined gate type>'))

		def SetElementSizesInCU():  # set sizes in canvas units of all elements in the FTGate instance
			for ThisEl in self.AllElements:
				ThisEl.SizeXInCU, ThisEl.SizeYInCU = ThisEl.MinSizeInCU

		def SetButtonStati(Elements):
			# set 'Status' attributes of buttons in gate's Elements
			for (ButtonName, Flag) in [('GateLinkedButton', self.Linked), ('GateGroupedButton', bool(self.CollapseGroups)),
					('GateCommentButton', bool(self.GateDescriptionComments)), ('GateStyleButton', False),
					('GateActionItemButton', bool(self.ActionItems))]:
				FoundButtonElement = ElementNamed(Elements, ButtonName)
				if FoundButtonElement:
					FoundButtonElement.Status = {True: 'In', False: 'Out'}[Flag]
			ValueProblemElement = ElementNamed(Elements, 'ValueProblemButton')
			if ValueProblemElement:
				ValueProblemElement.Status = {True: 'Alert', False: 'Out'}[(self.ValueProblemObjectID is None)]

		def DrawBackgroundBox(DC, Zoom): # draw FTGate's background box in DC
			DC.SetPen(wx.Pen(GateBorderColour, width=max(1, int(round(Zoom)))))
			DC.SetBrush(wx.Brush(GateBaseColour))
			# box is drawn in FTGate's own bitmap, so coords are relative to gate (not using PosX/YInPx, which are relative to column)
			DC.DrawRectangle(0, 0, self.SizeXInPx, self.SizeYInPx)

		def DrawElements(DC, Elements, Zoom): # render FTGate's elements in DC
			BackBoxRoundedness = int(round(3 * Zoom)) # for text elements, how rounded the background boxes' corners are
			for El in Elements:
				# render element, including any background box, in DC
				if getattr(El, 'Visible', True):
					El.Draw(DC, Zoom, BackBoxRoundedness=BackBoxRoundedness)

		def DrawGateSymbol(Zoom): # draw gate in self.Bitmap as a symbol

			def SetupDC(PenWidth): # set up self.Bitmap and DC for drawing. Return DC
				self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
				# make a DC for drawing
				DC = wx.MemoryDC(self.Bitmap)
				DC.SetPen(wx.Pen(GateBorderColour, width=PenWidth))
				DC.SetBrush(wx.Brush(GateBaseColour))
				return DC

			def FillSymbol(Bitmap, BitmapX, BitmapY, StartX, StartY, FillColour, BoundaryRed):
				# fill symbol in Bitmap (of dimensions (BitmapX, BitmapY)
				# StartX, StartY: a point inside the symbol
				# FillColour: an RGB tuple (R, G, B)
				# BoundaryRed (int): the red value of the boundary of the symbol (currently ignored, just looks for non-zero red value)
				# Add alpha channel to FillColour
				FillColour = tuple(list(FillColour) + [0xff])
				# First, get the bitmap data and split into a list of lists (per row) of tuples (RGB per point)
				AllData = 'x' * BitmapX * BitmapY * 4 # string to put bitmap data into
				Bitmap.CopyToBuffer(data=AllData, format=wx.BitmapBufferFormat_RGBA)
				# split into rows
				AllDataPerRow = [AllData[ThisRowStart:ThisRowStart + (4 * BitmapX)]
					for ThisRowStart in range(0, len(AllData), 4 * BitmapX)]
				# split each row into RGB sublists
				AllDataRGB = []
				for ThisRow in AllDataPerRow:
					AllDataRGB.append( [tuple([ord(x) for x in ThisRow[ThisPixelStart:ThisPixelStart + 4]])
						for ThisPixelStart in range(0, 4 * BitmapX, 4)])
				for RowIncrement in [-1, 1]: # work upwards (increment -1) then downwards (+1)
					FillingY = StartY # row currently being filled; start from starting row
					ThisRowLStart = ThisRowRStart = StartX # pixels in this row that we have to fill at L and R ends and maybe beyond
					MoreToFill = True
					while MoreToFill:
						# fill row FillingX, from LStart leftwards
						ThisRowData = AllDataRGB[FillingY]
						# find additional pixels to fill to the left of LStart
						ThisRowInProgress = True
						while ThisRowLStart > 0 and ThisRowInProgress:
							ThisRowLStart -= 1
							ThisRowInProgress = (ThisRowData[ThisRowLStart][0] == 0)
						# find additional pixels to fill to the right of RStart
						ThisRowInProgress = True
						while ThisRowRStart < BitmapX - 1 and ThisRowInProgress:
							ThisRowRStart += 1
							ThisRowInProgress = (ThisRowData[ThisRowRStart][0] == 0)
						# fill the section between LStart and RStart
						for ThisX in range(ThisRowLStart, ThisRowRStart):
							ThisRowData[ThisX] = FillColour
						if 0 < FillingY < BitmapY - 1: # find starting point for next row
							NextRowData = AllDataRGB[FillingY + RowIncrement]
							NextRowLStart = None # starting point to fill in next row (above)
							CheckingX = ThisRowLStart # search rightwards until a pixel is found to fill
							while (CheckingX < ThisRowRStart) and (NextRowLStart is None):
								if (NextRowData[CheckingX][0] == 0): NextRowLStart = CheckingX
								CheckingX += 1
							MoreToFill = (NextRowLStart is not None) # whether we found any pixels in the row above
							FillingY += RowIncrement # ready for next row
							ThisRowLStart = ThisRowRStart = NextRowLStart
						else: MoreToFill = False # reached edge of bitmap
				# return all data as a bitmap. First way is old way using reduce()
				# Bitmap.CopyFromBuffer(data=reduce(lambda a, b: a+b, [chr(c) for r in AllDataRGB for p in r for c in p]),
				#	format=wx.BitmapBufferFormat_RGBA)
				Bitmap.CopyFromBuffer(data=''.join([chr(c) for r in AllDataRGB for p in r for c in p]),
					format=wx.BitmapBufferFormat_RGBA)
				return Bitmap

			AlgorithmsWithBubble = ['NOR', 'NAND']  # which algorithms need a bubble (little circle) on the output
			BubbleRadiusInCU = 5
			BubbleRadiusInPx = int(round(BubbleRadiusInCU * Zoom))
			TextPointSizeNoZoom = 30
			PenWidth = max(1, int(round(Zoom)))  # width of pen for drawing border
			if self.Style == 'IEC 60617-12': # boxes with annotations inside
				BoxSizeXInCU = 60
				self.SizeYInCU = 100
				if self.Algorithm in AlgorithmsWithBubble: self.SizeXInCU = BoxSizeXInCU + 2 * BubbleRadiusInCU
				else: self.SizeXInCU = BoxSizeXInCU
				self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
				self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
				# make the bitmap and DC and set up pen and brush for drawing symbol
				DC = SetupDC(PenWidth)
				# draw a rectangle
				DC.DrawRectangle(0, 0, int(round((BoxSizeXInCU - 2) * Zoom)), self.SizeYInPx)
				# for NAND and NOR gates, draw a bubble on the output
				if self.Algorithm in AlgorithmsWithBubble:
					DC.DrawCircle(int(round((BoxSizeXInCU + BubbleRadiusInCU - 1) * Zoom)),
						int(round(0.5 * self.SizeYInPx)), radius=BubbleRadiusInPx)
				# write annotation
				DC.SetFont(wx.Font(pointSize=int(round(TextPointSizeNoZoom * Zoom)), family=DefaultFontFamily,
					style=wx.FONTSTYLE_NORMAL, weight=wx.FONTWEIGHT_NORMAL))
				DC.SetTextForeground(ButtonGraphicColour)
				MyText = {'OR': '≥1', 'MutExcOR': '=1', 'AND': '&', 'NOR': '≥1', 'NAND': '&', '2ooN': '2ooN',
					'3ooN': '3ooN'}[self.Algorithm]
				# work out text size, so we can position it in the shape
				TextXSizeInPx, TextYSizeInPx = DC.GetTextExtent(MyText)
				DC.DrawText(MyText, int(round(0.5 * (BoxSizeXInCU * Zoom - TextXSizeInPx))),
					int(round(0.2 * (self.SizeYInPx - TextYSizeInPx))))
			elif self.Style == 'IEEE 91': # traditional distinctive shapes
				if self.Algorithm in ['AND', 'NAND']: SymbolSizeXInCU = 60
				else: SymbolSizeXInCU = 100 # target size of symbol without bubble or 'XOR' line on left
				self.SizeYInCU = 60
				XORLineAllowanceXInCU = 10 # extra X allowance on left side for XOR line
				if self.Algorithm in AlgorithmsWithBubble: self.SizeXInCU = SymbolSizeXInCU + 2 * BubbleRadiusInCU
				else: self.SizeXInCU = SymbolSizeXInCU
				if self.Algorithm == 'MutExcOR':
					self.SizeXInCU += XORLineAllowanceXInCU
					XStartInPx = int(round(XORLineAllowanceXInCU * Zoom)) # starting position of symbol, not counting the XOR line
				else: XStartInPx = 0
				self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
				self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
				SymbolEndXInPx = XStartInPx + int(round(SymbolSizeXInCU * Zoom))
				HalfHeightInPx = int(round(0.5 * self.SizeYInPx))
				DC = SetupDC(PenWidth)
				DC.SetBrush(wx.Brush(colour='black', style=wx.TRANSPARENT)) # no shape fill
				if self.Algorithm == 'MutExcOR': # draw extra curve on left for XOR gate
					DC.DrawArc(0, self.SizeYInPx, 0, 0, -int(round(0.5 * SymbolSizeXInCU * Zoom)), 0.5 * self.SizeYInPx)
				# draw left part of symbol: curve for OR/XOR/NOR, straight for AND/NAND, arrowhead for 2ooN/3ooN)
				if self.Algorithm in ['OR', 'MutExcOR', 'NOR']:
					DC.DrawArc(XStartInPx, self.SizeYInPx, XStartInPx, 0,
						XStartInPx - int(round(0.5 * SymbolSizeXInCU * Zoom)), 0.5 * self.SizeYInPx)
				elif self.Algorithm in ['AND', 'NAND']:
					DC.DrawLine(XStartInPx, self.SizeYInPx, XStartInPx, 0)
				elif self.Algorithm in ['2ooN', '3ooN']:
					ArrowheadEndXInPx = XStartInPx + int(round(0.2 * SymbolSizeXInCU * Zoom))
					DC.DrawLine(XStartInPx, self.SizeYInPx, ArrowheadEndXInPx, HalfHeightInPx)
					DC.DrawLine(ArrowheadEndXInPx, HalfHeightInPx, XStartInPx, 0)
				# draw right part of symbol
				HalfwayAlongSymbolInPx = XStartInPx + int(round(0.5 * SymbolSizeXInCU * Zoom))
				if self.Algorithm in ['OR', 'MutExcOR', 'NOR']: # 2 circular arcs
					# y coord of arc centre calculated as x + d = y*y/x + x/4 where x, y are shape length and height
					X2OverY = ((SymbolSizeXInCU * Zoom)**2) / self.SizeYInPx
					DC.DrawArc(SymbolEndXInPx, HalfHeightInPx, XStartInPx, 2, XStartInPx,
						X2OverY + int(round(0.25 * self.SizeYInPx)))
					DC.DrawArc(XStartInPx, self.SizeYInPx - 1, SymbolEndXInPx, HalfHeightInPx, XStartInPx,
						int(round(0.75 * self.SizeYInPx)) - X2OverY)
				else: # 1 circular arc and 2 horizontal lines
					DC.DrawArc(HalfwayAlongSymbolInPx, self.SizeYInPx - 1, HalfwayAlongSymbolInPx, 1,
						HalfwayAlongSymbolInPx, HalfHeightInPx)
					DC.DrawLine(XStartInPx, 0, HalfwayAlongSymbolInPx, 0)
					DC.DrawLine(XStartInPx, self.SizeYInPx, HalfwayAlongSymbolInPx, self.SizeYInPx)
				# for NAND and NOR gates, draw a bubble on the output
				if self.Algorithm in AlgorithmsWithBubble:
					DC.SetBrush(wx.Brush(GateBaseColour)) # bubble fill colour
					DC.DrawCircle(SymbolEndXInPx + BubbleRadiusInPx, HalfHeightInPx, radius=BubbleRadiusInPx)
				if not (self.FT.Panning or self.FT.Zooming): # skip fill if panning or zooming, as it gets slow
					# Flood fill the symbol; using manual implementation, as MacOS doesn't support FloodFill
					DC.Destroy() # so that FillSymbol() has exclusive access to self.Bitmap
					self.Bitmap = FillSymbol(self.Bitmap, self.SizeXInPx, self.SizeYInPx, HalfwayAlongSymbolInPx, HalfHeightInPx,
						GateBaseColour, GateBorderColour[0])
			elif self.Style == 'DIN 40700': pass

		# start of main procedure for RenderIntoBitmap()
		if self.DetailedView: # show detailed version of gate
			BorderX = BorderY = 10 # outer border in canvas coords
			GapBetweenRows = GapBetweenCols = 5 # in canvas coords
			MinColWidth = 40
			# create variable elements and build combined element list comprising fixed and variable elements
			(self.DescriptionCommentEls, self.ActionItemEls) = self.CreateVariableTextElements()
			self.AllElements = BuildFullElementList(
				self.TopFixedEls, self.ValueFixedEls, self.DescriptionCommentEls, self.ActionItemEls)

			PopulateTextElements(self.AllElements) # put required text values in the components
			SetElementSizesInCU()
			SetButtonStati(self.AllElements) # set button elements to required status
			# calculate height of each "sizer" row in canvas coords
			ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs = CalculateRowAndColumnDimensions(
				self.AllElements, GapBetweenCols, GapBetweenRows, MinColWidth, BorderX, BorderY)
			# set element X, Y positions according to column positions and row heights
			for El in self.AllElements:
				El.PosXInCU = ColStartXs[El.ColStart]
				El.EndXInCU = El.PosXInCU + sum([ColWidths[c] for c in range(El.ColStart, El.ColStart + El.ColSpan)]) - GapBetweenCols
				# if element should fill available X-space, adjust its X size to match available space
				if El.FillXSpace: El.SizeXInCU = El.EndXInCU - El.PosXInCU
				El.SizeXInPx = int(round(El.SizeXInCU * Zoom))
				El.PosXInPx = int(round(El.PosXInCU * Zoom))
				El.StartY = El.PosYInCU = RowStartYs[El.Row] # transitioning from StartY to PosYInCU; eventually should kill StartY
				El.EndYInCU = RowEndYs[El.Row]
				El.SizeYInCU = El.EndYInCU - El.PosYInCU
				El.SizeYInPx = int(round(El.SizeYInCU * Zoom))
			# calculate FTGate size; removing gap after final row/col and adding borders at both edges
			self.SizeXInCU = max([El.EndXInCU for El in self.AllElements]) - GapBetweenCols + 2 * BorderX
			self.SizeYInCU = RowEndYs[-1] - GapBetweenRows + 2 * BorderY
			self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
			self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
			# make the bitmap
			self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
			# make a DC for drawing
			DC = wx.MemoryDC(self.Bitmap)
			# draw background box, then elements, into the bitmap
			DrawBackgroundBox(DC, Zoom)
			DrawElements(DC, self.AllElements, Zoom)
		else: # non-detailed view
			DrawGateSymbol(Zoom=Zoom)

	def AllClickableObjects(self, SelectedOnly=False, VisibleOnly=True):
		# return list of all elements in FTGate object that should respond to mouse clicks
		# If SelectedOnly (bool), only return elements that are currently selected; similarly for VisibleOnly (bool)
		assert isinstance(SelectedOnly, bool)
		assert isinstance(VisibleOnly, bool)
		assert isinstance(self.DetailedView, bool)
		if self.DetailedView: # use method in the superclass (FTBoxyObject)
			return super(FTGate, self).AllClickableObjects(SelectedOnly=SelectedOnly, VisibleOnly=VisibleOnly)
		else: return self # in gate symbol view, only the symbol itself is clickable

	def HandleMouseLClickOnMe(self, **Args): # handle mouse click on gate when in symbol (not detailed) style
		# change gate style flag
		self.DetailedView = True
		self.FT.DisplDevice.Redraw(FullRefresh=True) # refresh the display to show detailed gate style

class FTConnector(FTBoxyObject): # object defining Connectors-In and -Out for display. These belong to FTColumn's.
	# Is the superclass of FTConnectorIn and FTConnectorOut
	# Rendered by drawing into bitmap (doesn't use native widgets or sizer)
	ConnectorStyles = ['Default'] # future, will define various connector appearances (squares, arrows, circles etc)
	NeedsConnectButton = True # whether to provide connect buttons
	# Attribs are used by ParseFTData() to populate object's attributes from data transferred from datacore (may be redundant)
	Attribs = [(info.IDTag, int, False), ('BackgColour', 'rgb', False), ('Style', str, False), ('Numbering', str, False),
		('Description', str, False), ('Value', str, False), ('ValueUnit', str, False), ('ConnectTo', int, True)]

	def __init__(self, **Args): # attribs marked * below are named in quotes elsewhere: be careful if names changed
		FTBoxyObject.__init__(self, **Args)
		self.ID = None
		self.BackgColour = '0,0,0'
		self.Style = FTConnector.ConnectorStyles[0]
		self.Numbering = ''
		self.ConnectorDescription = ''
		self.Value = ''
		self.ValueUnit = '' # *
#		self.ConnectTo = [] # str values, ID's of connected items in next column (already defined in superclass)
		self.SizeXInCU = self.SizeXInPx = self.SizeYInCU = self.SizeYInPx = 10 # size in canvas units and screen pixels
		self.PosZ = 0 # z-coordinate
		self.Buffer = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		self.CollapseGroups = [] # FTCollapseGroup objects this Connector belongs to
		self.ValueProblemID = '' # ID of NumValueProblem instance, or '' if no problem (not used yet)
		self.ValueProblemObjectID = '' # ID of an FT object that is causing a value problem in this object. '' = no problem
		self.FixedEls = self.CreateFixedTextElements()
		self.Clickable = True # bool; whether instance is intended to respond to user clicks
		self.Visible = True # bool; whether it would be visible if currently panned onto the display device
		self.Selected = False # bool; whether currently user-selected i.e. highlighted
		self.MaxElementsConnectedToThis = FTConnectorItemInCore.MaxElementsConnectedToThis

	def CreateFixedTextElements(self):
		# create elements for fixed text items in FTConnector. Return list of elements
		ColourLabelBkg = (0x80, 0x3E, 0x51) # plum; however not used in FTConnector
		ColourLabelFg = (0xFF, 0xFF, 0xFF) # white; however not used in FTConnector
		ColourContentBkg = (0x6A, 0xDA, 0xBD) # mint green
		ColourContentFg = (0x00, 0x00, 0x00) # black

		# column widths: 100, 100, 50, 50
		# any element with MinHeight parm set is growable in the y axis to fit the text.
		# it should be assigned to the Row that it can force to grow
		ConnDescription = TextElement(self.FT, Row=0, ColStart=0, ColSpan=2, EndX=199, MinHeight=50, HostObject=self,
			InternalName='ConnDescription')
		ConnGroupedButton = ButtonElement(self.FT, Row=0, ColStart=4, ColSpan=1, StartX=250, EndX=299,
			HostObject=self, InternalName='ConnGroupedButton')
		ConnValue = TextElement(self.FT, Row=1, ColStart=0, ColSpan=1, EndX=99, HostObject=self,
			InternalName='ConnValue')
		ConnValueUnit = TextElement(self.FT, Row=1, ColStart=1, ColSpan=1, EndX=199, HostObject=self,
			InternalName='ConnValueUnit')
		self.ConnValueProblemButton = ButtonElement(self.FT, Row=1, ColStart=4, ColSpan=1, StartX=250, EndX=299,
			HostObject=self, InternalName='ConnValueProblemButton')
		# Connectors don't have "value types" (it's always calculated), "comments" or "action items"

		# make list of elements
		TopEls = [ConnDescription, ConnGroupedButton, ConnValue, ConnValueUnit, self.ConnValueProblemButton]

		# set text element colours
		for El in TopEls:
			if type(El) is TextElement:
				El.Text.Colour = ColourContentFg
				El.BkgColour = ColourContentBkg

		return TopEls

	def RenderIntoBitmap(self, Zoom): # draw FTConnector in its own self.Bitmap. Also calculates FTConnector's size attributes

		def PopulateTextElements(Elements):
			# put required values into all fixed text elements
			# The following list contains (attribs of FTConnector, element's InternalName)
			AttribInfo = [ ('Description', 'ConnDescription'), ('Value', 'ConnValue'), ('ValueUnit', 'ConnValueUnit') ]
			# put the content into the elements
			for (Attrib, Name) in AttribInfo:
				MatchingEl = ElementNamed(Elements, Name)
				if MatchingEl:
					MatchingEl.Text.Content = self.__dict__[Attrib]

		def SetButtonStati(Elements):
			# set 'Status' attributes of buttons in Elements
			ValueProblemElement = ElementNamed(Elements, 'ConnValueProblemButton')
			if ValueProblemElement:
				ValueProblemElement.Status = {True: 'Alert', False: 'Out'}[(self.ValueProblemObjectID is None)]

		def DrawElements(DC, Elements, Zoom): # render FTConnector's elements in DC
			BackBoxRoundedness = 5 # for text elements, how rounded the background boxes' corners are
			for El in Elements:
				El.Draw(DC, Zoom, BackBoxRoundedness=BackBoxRoundedness) # render element, including any background box, in DC

		# start of main procedure for RenderIntoBitmap() for class FTConnector
		BorderX = BorderY = 20 # outer border in canvas coords
		GapBetweenRows = GapBetweenCols = 10 # in canvas coords
		MinColWidth = 40
		# build combined element list (even though there's only one group of elements, left this way for consistency)
		self.AllElements = BuildFullElementList(self.FixedEls)

		PopulateTextElements(self.AllElements) # put required text values in the elements
		SetButtonStati(self.AllElements) # set button elements to required status
		# calculate height of each "sizer" row in canvas coords
		ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs = CalculateRowAndColumnDimensions(self.AllElements, GapBetweenCols,
			GapBetweenRows, MinColWidth, BorderX, BorderY)
		# set element Y positions and sizes according to row heights TODO update based on changes in FTElement
		for El in self.AllElements:
			El.StartY = RowStartYs[El.Row]
			El.EndY = RowEndYs[El.Row]
		# calculate FTConnector size
		self.SizeXInCU = max([El.EndX for El in self.AllElements]) + BorderX # the + BorderX adds right border space
		self.SizeYInCU = RowEndYs[-1] - GapBetweenRows + BorderY # remove bottom "gap", add bottom border
		self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
		self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
		# make the bitmap
		self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		# make a DC for drawing
		DC = wx.MemoryDC(self.Bitmap)
		# draw elements into the bitmap
		DrawElements(DC, self.AllElements, Zoom)

class FTConnectorIn(FTConnector):

	def __init__(self):
		FTConnector.__init__(self)

class FTConnectorOut(FTConnector):

	def __init__(self):
		FTConnector.__init__(self)

class FTCollapseGroup(object): # depiction of a group of FT objects that have been collapsed to a single display object
	# The CollapseGroup is not actually an FT object in itself, and is not stored in any column.

	def __init__(self, ID): # ID (int): the ID in the data from DataCore. Used (only?) for grabbing attribs from DataCore
		object.__init__(self)
		self.ID = ID
		self.Collapsed = False # whether group is currently displayed as collapsed
		self.PosZ = 0

class FTBuilder(FTBoxyObject): # 'add' button object within an FTColumn.
	# Created and managed within Viewport, so no data <--> DataCore.
	Hotspots = ['Whole'] # hotspot names for mouse hits

	def __init__(self, **Args): # Args must include: HostFT (handled by superclass), ObjTypeRequested, OffsetXInCU
		assert 'HostFT' in Args
		assert Args['ObjTypeRequested'] in [FTEventInCore, FTGateItemInCore]
		assert isinstance(Args['OffsetXInCU'], int) # X offset relative to column
		# ObjTypeRequested: which type of FT object will be created when user selects this FTBuilder - must be an element class
		# belonging to FTObj (not FTForDisplay)
		FTBoxyObject.__init__(self, **Args)
		self.ID = 0
		self.BackgColour = (0,0,0)
		self.Description = '' # the text in the button
		self.Visible = True
		self.Connectable = False # whether instances of this class can be connected
		self.Selected = False # whether button is currently "highlighted" (may not be used for any practical purpose)
		self.SizeXInCU = self.SizeXInPx = 50
		self.SizeYInCU = self.SizeYInPx = 20 # size in canvas units and screen pixels
		self.PosXInCU = Args['OffsetXInCU'] # position relative to column, in canvas units
		self.PosYInCU = 0
		self.PosXInPx = self.PosYInPx = 0 # absolute position on display device in pixels, taking zoom and pan into account
			# (needed for testing mouse hits)
		self.PosZ = 0 # z-coordinate
		self.Bitmap = None # wx.Bitmap instance. Created in self.RenderIntoBitmap()
		self.ObjTypeRequested = Args['ObjTypeRequested']

	def RenderIntoBitmap(self, Zoom): # draw FTBuilder in self.Bitmap. Also sets FTBuilder size attributes
		# set FTBuilder size
		self.SizeXInPx = int(round(self.SizeXInCU * Zoom))
		self.SizeYInPx = int(round(self.SizeYInCU * Zoom))
		# make the bitmap
		self.Bitmap = wx.Bitmap(width=self.SizeXInPx, height=self.SizeYInPx, depth=wx.BITMAP_SCREEN_DEPTH)
		# make a DC for drawing
		DC = wx.MemoryDC(self.Bitmap)
		# draw a large box
		DC.SetPen(wx.Pen(ButtonGraphicColour, width=1))
		DC.SetBrush(wx.Brush(ButtonBaseColour))
		DC.DrawRoundedRectangle(0, 0, self.SizeXInPx, self.SizeYInPx, radius=min(1, int(round(6 * Zoom))))
		# draw a + inside
		PlusLineThickness = 3
		DC.SetPen(wx.Pen(ButtonGraphicColour, width=max(1, int(round(PlusLineThickness * Zoom)))))
		DC.DrawLine(self.SizeXInPx * 0.2, self.SizeYInPx * 0.15, self.SizeXInPx * 0.2, self.SizeYInPx * 0.45)
		DC.DrawLine(self.SizeXInPx * 0.14, self.SizeYInPx * 0.3, self.SizeXInPx * 0.26, self.SizeYInPx * 0.3)
		# draw graphic for type of object button will create
		if self.ObjTypeRequested == FTEventInCore: # draw box
			DC.DrawRoundedRectangle(self.SizeXInPx * 0.4, self.SizeYInPx * 0.2, self.SizeXInPx * 0.4,
				self.SizeYInPx * 0.6, radius=min(1, int(round(4 * Zoom))))
		elif self.ObjTypeRequested == FTGateItemInCore: # draw gate: arc, vertical line, and 3 connecting stubs
			DC.DrawArc(self.SizeXInPx * 0.6, self.SizeYInPx * 0.8, self.SizeXInPx * 0.6, self.SizeYInPx * 0.2,
				self.SizeXInPx * 0.6, self.SizeYInPx * 0.5)
			DC.DrawLine(self.SizeXInPx * 0.6, self.SizeYInPx * 0.2, self.SizeXInPx * 0.6, self.SizeYInPx * 0.8)
			DC.DrawLine(self.SizeXInPx * 0.5, self.SizeYInPx * 0.3, self.SizeXInPx * 0.6, self.SizeYInPx * 0.3)
			DC.DrawLine(self.SizeXInPx * 0.5, self.SizeYInPx * 0.7, self.SizeXInPx * 0.6, self.SizeYInPx * 0.7)
			DC.DrawLine(self.SizeXInPx * 0.75, self.SizeYInPx * 0.5, self.SizeXInPx * 0.85, self.SizeYInPx * 0.5)

	def HandleMouseLClickOnMe(self, HitHotspot, **Args): # process mouse left click on HitHotspot (str)
		# request DataCore to create new FT object, and get back confirmation
		# If user has clicked on a builder button, IndexInCol is the index at which the new item is to be inserted,
		# not counting builder buttons. This is found by counting the number of non-builder items above the builder button
		AllElsInColumn = self.HostFT.Columns[self.ColNo].FTElements
		IndexInCol = len([El for El in AllElsInColumn[:AllElsInColumn.index(self)] if not isinstance(El, FTBuilder)])
		# request PHA object to add new element by sending message through zmq
#		print('FT1494 FT sending request on socket: ',  [(s.SocketNo, s.SocketLabel) for s in vizop_misc.RegisterSocket.Register if s.Socket == self.HostFT.C2DSocketREQ])
		vizop_misc.SendRequest(Socket=self.HostFT.C2DSocketREQ, Command='RQ_FT_NewElement',
			Proj=self.HostFT.Proj.ID, PHAObj=self.HostFT.PHAObj.ID, Viewport=self.HostFT.ID,
			ObjKindRequested=self.ObjTypeRequested.InternalName, ColNo=str(self.ColNo), IndexInCol=str(IndexInCol))

	def AllClickableObjects(self, SelectedOnly=False, VisibleOnly=True):
		# return list of all elements in FTBuilder object that should respond to mouse clicks
		# (currently, only the button itself)
		# If SelectedOnly (bool), only return elements that are currently selected; similarly for VisibleOnly (bool)
		assert isinstance(SelectedOnly, bool)
		assert isinstance(VisibleOnly, bool)
		if (self.Selected or not SelectedOnly) and (self.Visible or not VisibleOnly): return [self]
		else: return []

class FTColumn(object): # object containing a column of FT objects for display, including:
	# FTEvent (including IPL), FTGate, FTConnectorIn/Out, collapse groups, and builder buttons
	# Used to populate Columns[] in FTForDisplay instance
	# This class declaration has to be below those named in SuitableObjects
	# SuitableObjects: keys are tags of recognised objects, values are corresponding object classes
	SuitableObjects = {'event': FTEvent, 'gate': FTGate, 'connector-in': FTConnectorIn,
		'connector-out': FTConnectorOut, 'FTAddButton': None}

	def __init__(self, FT, ColNo): # ColNo: column number, counting from zero (int)
		object.__init__(self)
		assert isinstance(ColNo, int)
		assert ColNo >= 0
		self.ColNo = ColNo
		self.FT = FT
		self.PosXInPx = 0 # X coord of left edge in pixels, relative to display device origin, including zoom and pan
		self.SizeXInPx = 10 # width in pixels
			# PosXInPx and SizeXInPx needed to determine x-coord of inter-column strip to the right
		self.FTElements = []

	def RenderElementsInOwnBitmaps(self, Zoom):
		# Get each element to calculate its own contents and draw itself in own individual bitmap
		for ThisFTObject in self.FTElements:
			ThisFTObject.RenderIntoBitmap(Zoom)

	def RenderInDC(self, FT, DC, ColOffsetX, ColOffsetY):
		# Copy all elements of the FTColumn from their own bitmaps into the DC.
		# ColOffsetX/Y (int): offset (in pixels) of column relative to whole FT
		# Assumes bitmaps already rendered in self.RenderElementsInOwnBitmaps()
		# Calculates and returns NextOffsetX (int), the first available X coord (pixels) after the FTColumn is drawn
		NextOffsetX = ColOffsetX # NextOffsetX no longer used
		for ThisFTElement in self.FTElements:
			# Blit each object's bitmap into DC
			DC.DrawBitmap(ThisFTElement.Bitmap, ThisFTElement.PosXInPx, ThisFTElement.PosYInPx, useMask=False)
			self.DrawConnectingLine(ThisFTElement, DC) # if necessary, draw horizontal from right edge of element to end of column
		return int(round(NextOffsetX))

	def DrawConnectingLine(self, FTElement, DC):
		# if FTElement is narrower than the column, draw right connecting line to join up with the inter-column strip
		if (FTElement.SizeXInPx < self.SizeXInPx) and FTElement.Connectable:
			Zoom = self.FT.Zoom
			LineYInCU = FTElement.HorizontalLineYInCU()
			MyPen = wx.Pen(ConnectingLineColour, width=max(1, int(round(ConnectingLineThicknessInCU * Zoom))))
			MyPen.SetCap(wx.CAP_BUTT) # set square end for line, to prevent line encroaching on elements
			DC.SetPen(MyPen)
			LineStartXInPx, LineStartYInPx = utilities.ScreenCoords(self.PosXInCU + FTElement.PosXInCU + FTElement.SizeXInCU + 1,
				LineYInCU, Zoom, PanX=self.FT.PanX, PanY=self.FT.PanY)
			LineEndXInPx, LineEndYInPx = utilities.ScreenCoords(self.PosXInCU + self.SizeXInCU, LineYInCU, Zoom, PanX=self.FT.PanX,
				PanY=self.FT.PanY)
			DC.DrawLine(LineStartXInPx, LineStartYInPx, LineEndXInPx, LineEndYInPx)

	def AllClickableObjects(self, SelectedOnly=False, VisibleOnly=True):
		# return list of all elements in column that should respond to mouse clicks, including connect buttons
		# If SelectedOnly (bool), only return elements that are currently selected; similarly for VisibleOnly (bool)
		assert isinstance(SelectedOnly, bool)
		assert isinstance(VisibleOnly, bool)
		return utilities.Flatten([ThisEl.AllClickableObjects(SelectedOnly=SelectedOnly, VisibleOnly=VisibleOnly)
								  for ThisEl in self.FTElements
								  if ((ThisEl.Selected or not SelectedOnly) and (ThisEl.Visible or not VisibleOnly))])

def CalculateRowAndColumnDimensions(Elements, GapBetweenCols, GapBetweenRows, MinColWidth, BorderX, BorderY):
	# for any kind of FT elements, calculate and return column and row sizes in canvas coords (lists), including GapBetweenRows
	# BorderX and BorderY is left and right / top and bottom border to allow
	# returns lists: ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs
	# make lists to write into, containing same number of items as the number of columns/rows required
	ColWidths = [MinColWidth] * (1 + max([El.ColStart + El.ColSpan - 1 for El in Elements]))
	RowHeights = [0] * (1 + max([El.Row for El in Elements]))
	# put the required max heights in each element in the row heights list
	for El in Elements:
		El.MinSizeX, MinSizeY = El.MinSizeInCU
		# first pass: assign column widths for elements spanning only 1 column
		if El.ColSpan == 1: ColWidths[El.ColStart] = max(ColWidths[El.ColStart], El.MinSizeX)
		RowHeights[El.Row] = max(RowHeights[El.Row], MinSizeY)
	for El in Elements:
		# second pass: assign any additional space needed in last column of element spanning >1 column.
		# The 'sum' function calculates the space already assigned in columns prior to the last column
		if El.ColSpan > 1:
			ColWidths[El.ColStart + El.ColSpan - 1] = max(ColWidths[El.ColStart + El.ColSpan - 1],
				El.MinSizeX - sum(ColWidths[El.ColStart:El.ColStart+El.ColSpan-1]))
	# add GapBetweenCols to each column width
	ColWidths = [w + GapBetweenCols for w in ColWidths]
	# add GapBetweenRows to each row height
	RowHeights = [h + GapBetweenRows for h in RowHeights]
	# calculate StartX and EndX for each column
	ColStartXs = []
	ColEndXs = []
	ColStartXSoFar = BorderX
	for ThisColWidth in ColWidths:
		ColStartXs.append(ColStartXSoFar)
		ColStartXSoFar += ThisColWidth
		ColEndXs.append(ColStartXSoFar - GapBetweenCols)
	# calculate StartY and EndY for elements in each row
	RowStartYs = []
	RowEndYs = []
	RowStartYSoFar = BorderY
	for ThisRowHeight in RowHeights:
		RowStartYs.append(RowStartYSoFar)
		RowStartYSoFar += ThisRowHeight
		RowEndYs.append(RowStartYSoFar - GapBetweenRows)
	return ColWidths, ColStartXs, ColEndXs, RowHeights, RowStartYs, RowEndYs

def ElementNamed(ElList, ElName): # returns first element in ElList whose InternalName attribute is ElName
	# If no match found, returns None
	MatchList = [El for El in ElList if El.InternalName == ElName]
	if MatchList: return MatchList[0]
	else: return None

class FTPanelClass(wx.Panel):
	# large panel on left side of vizop frame, for displaying entire FT. Redundant (now we blit into ControlFrame)
	# $$$ we still need to make an instance of this class in the frame

	def __init__(self, ParentFrame):
		wx.Panel.__init__(ParentFrame)
		self.FT = None # the FT object currently shown in the panel
		self.Bind(wx.EVT_PAINT, self.OnPaint)

	def OnPaint(self, event=None):

		# main code for OnPaint()
		MyPaintDC = wx.PaintDC(self) # ultimate destination for all layers
		TransDC = wx.GCDC(MyPaintDC) # DC for transparent drawing
		# blit first layer (background) opaque, much faster than transparent
		MyPaintDC.DrawBitmap(self.FT.Buffer, 0, 0, useMask=False)
		# the following code, from Tuti, will be needed when we want to layer rubber bands over the FT
		# for layer in LayersToPaint: # draw all normal layers transparent, then SelectLayer on top if required
		#     layer.Buffer.SetMaskColour(sm.get_config('MaskColour'))
		#     TransDC.DrawBitmap(layer.Buffer, layer.OffsetX + CurrentProject.PanOffsetX[DisplIndex] + self.OffsetX,
		#         layer.OffsetY + CurrentProject.PanOffsetY[DisplIndex] + self.OffsetY, useMask=True) # Rappin p378

class FTColumnInCore(object): # FT column object used in DataCore by FTObjectInCore

	def __init__(self, FT, ColNo=0):  # FT: which FTObjectInCore instance this object belongs to; ColNo (int): column number
		assert isinstance(FT, FTObjectInCore)
		object.__init__(self)
#		self.ID = str(utilities.NextID(FTEventInCore.AllFTEventsInCore))  # generate unique ID; stored as str
#		FTEventInCore.AllFTEventsInCore.append(self)  # add self to register; must do after assigning self.ID
		FT.MaxElementID += 1 # find next available ID
		self.ID = str(FT.MaxElementID)
		assert isinstance(ColNo, int)
		assert ColNo >= 0
		self.ColNo = ColNo
		self.FT = FT
		self.FTElements = []

class FTEventInCore(object): # FT event object used in DataCore by FTObjectInCore
	# Used for causes, SIF failure events (a single bottom level event used in high demand and continuous modes),
	# IPLs, intermediate events, final events, connectors in/out but not gates
	EventTypes = ['InitiatingEvent', 'SIFFailureEvent', 'IntermediateEvent', 'IPL', 'TopEvent',
		'ConnectorIn', 'ConnectorOut', 'EnablingCondition', 'ConditionalModifier']
	# event types whose value is a frequency
	EventTypesWithFreqValue = ['InitiatingEvent', 'SIFFailureEvent', 'IntermediateEvent', 'TopEvent',
		'ConnectorIn', 'ConnectorOut']
	# event types whose value is a probability
	EventTypesWithProbValue = ['IPL', 'EnablingCondition', 'ConditionalModifier']
	# event types for which the user must supply a value
	EventTypesWithUserValues = ['InitiatingEvent', 'IPL', 'EnablingCondition', 'ConditionalModifier']
	# event types for which user can supply a value, or it can be derived from elsewhere
	EventTypesUserOrDerivedValues = ['ConnectorIn']
	# event types for which value is derived, not user supplied
	EventTypesWithDerivedValues = ['SIFFailureEvent', 'IntermediateEvent', 'TopEvent', 'ConnectorOut']
	UserSuppliedNumberKinds = [core_classes.UserNumValueItem, core_classes.ConstNumValueItem,
		core_classes.LookupNumValueItem, core_classes.ParentNumValueItem, core_classes.UseParentValueItem]
	DerivedNumberKinds = [core_classes.AutoNumValueItem]
	# set default value kinds per event type
	DefaultValueKind = {}
	for (ThisValueKind, ThisEventTypeList) in [
			(core_classes.UserNumValueItem, EventTypesWithUserValues + EventTypesUserOrDerivedValues),
			(core_classes.AutoNumValueItem, EventTypesWithDerivedValues)]:
		for ThisEventType in ThisEventTypeList:
			DefaultValueKind[ThisEventType] = ThisValueKind
#	AllFTEventsInCore = [] # register of all events currently active in Vizop; used to generate unique IDs
#		# Potential gotcha: Events in this list are not guaranteed to exist in PHA models. When they are deleted from
#		# PHA models, currently no attempt is made to remove them from this list. (Potential memory leak?)
	InternalName = 'FTEventInCore'
	DefaultLikelihood = 0.0 # initial numerical value of likelihood
	DefaultProbability = 1.0 # initial numerical value of probability
	DefaultFreqUnit = core_classes.PerYearUnit
	DefaultProbUnit = core_classes.ProbabilityUnit
	DefaultTimeUnit = core_classes.YearUnit
	DefaultRatioUnit = core_classes.DimensionlessUnit
	MaxElementsConnectedToThis = 1
	# hash for component names as they appear in Undo menu texts
	ComponentEnglishNames = {'Value': 'event value'}

	def __init__(self, Proj, FT, Column, **Args): # FT: which FTObjectInCore instance this object belongs to
		# Column: the FTColumnInCore hosting this object
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(FT, FTObjectInCore)
		assert isinstance(Column, FTColumnInCore)
		object.__init__(self)
#		self.ID = str(utilities.NextID(FTEventInCore.AllFTEventsInCore)) # generate unique ID; stored as str
#		FTEventInCore.AllFTEventsInCore.append(self) # add self to register; must do after assigning self.ID
		FT.MaxElementID += 1 # find next available ID
		self.ID = str(FT.MaxElementID)
		self.Proj = Proj
		self.FT = FT
		self.Column = Column
		# set which type of event this is allowed to be; also sets DefaultEventType (str)
		self.AvailEventTypes, self.DefaultEventType = self.SetAvailableEventTypes()
		self.IsIPL = False # Marker for IPLs
		self.EventType = self.DefaultEventType # str
		self.SetupNumbering()
		self.EventDescription = '' # rich text string
		# set up 'user defined' number kind, for event types that support it,
		# or in case user switches to an event type that supports it
		self.Value = core_classes.UserNumValueItem(HostObj=self) # gets reassigned in self.SetAsSIFFailureEvent()
		# TODO replace above with call to ChangeValueKind()
		self.OldFreqValue = core_classes.UserNumValueItem(HostObj=self) # for restoring after switching btw freq/prob
		self.OldProbValue = core_classes.UserNumValueItem(HostObj=self)
		# store the initial (and most recently user-selected) unit for each quantity kind. Values are UnitKind instances
		self.LastSelectedUnitPerQtyKind = {'Probability': FTEventInCore.DefaultProbUnit,
			'Frequency': FTEventInCore.DefaultFreqUnit, 'Time': FTEventInCore.DefaultTimeUnit,
			'Ratio': FTEventInCore.DefaultRatioUnit}
		for ThisRR in FT.MyTolRiskModel.RiskReceptors:
			self.Value.SetMyValue(FTEventInCore.DefaultLikelihood, RR=ThisRR)
			self.OldFreqValue.SetMyValue(FTEventInCore.DefaultLikelihood, RR=ThisRR)
			self.OldProbValue.SetMyValue(FTEventInCore.DefaultProbability, RR=ThisRR)
			self.Value.SetMyStatus(NewStatus='ValueStatus_Unset', RR=ThisRR)
			self.OldFreqValue.SetMyStatus(NewStatus='ValueStatus_Unset', RR=ThisRR)
			self.OldProbValue.SetMyStatus(NewStatus='ValueStatus_Unset', RR=ThisRR)
		self.Value.SetMyUnit(FTEventInCore.DefaultFreqUnit)
		self.OldFreqValue.SetMyUnit(FTEventInCore.DefaultFreqUnit)
		self.OldProbValue.SetMyUnit(FTEventInCore.DefaultProbUnit)
		# change value kind if user defined kind isn't supported
		if FTEventInCore.DefaultValueKind[self.EventType] != core_classes.UserNumValueItem:
			self.ChangeValueKind(FTEventInCore.DefaultValueKind[self.EventType])
		self.IsSIFFailureEventInRelevantOpMode = False # whether this event was the SIF failure event when we were in
			# relevant opmodes (used to restore SIF failure event if we change back to those modes)
		self.CanEditValue = True # False if the value should only be calculated and not overridden by user
		self.ApplicableRiskReceptors = FT.MyTolRiskModel.RiskReceptors[:] # set which risk receptors apply to this event
		self.ShowActionItems = False
		self.BackgColour = '0,0,0'
		self.EventDescriptionComments = [] # list of AssociatedTextItem instances
		self.ValueComments = [] # list of AssociatedTextItem instances
		self.ShowDescriptionComments = True # whether description comments are visible
		self.ShowValueComments = True # whether value comments are visible
		self.ActionItems = [] # list of AssociatedTextItem instances
		self.ShowActionItems = True
		self.MakeTestComments()
		self.ConnectTo = [] # FT object instances in next column to the right, to which this element is connected
#		self.LinkedTo = [] # list of LinkItem instances of which this item is a LinkMaster
		self.LinkedFrom = [] # list of LinkItem instances for linking individual attribs to a master element elsewhere in the project
		self.CollapseGroups = [] # CollapseGroup objects this object belongs to

	def MakeTestComments(self):
		# make test comments for the FTEvent. Temporary
		DC = core_classes.AssociatedTextItem(Proj=self.Proj, PHAObjClass=type(self), Host=self)
		DC.Content = 'Test comment on description'
		DC.Numbering = core_classes.NumberingItem()
		# put a serial number into the numbering object
		SerialObj = core_classes.SerialNumberChunkItem()
		DC.Numbering.NumberStructure = [SerialObj]
		self.EventDescriptionComments.append(DC)
		VC = core_classes.AssociatedTextItem(Proj=self.Proj, PHAObjClass=type(self), Host=self)
		VC.Content = 'Test comment on value'
		VC.Numbering = core_classes.NumberingItem()
		# put a serial number into the numbering object
		SerialObj = core_classes.SerialNumberChunkItem()
		VC.Numbering.NumberStructure = [SerialObj]
		self.ValueComments.append(VC)
		AI = core_classes.AssociatedTextItem(Proj=self.Proj, PHAObjClass=type(self), Host=self)
		AI.Content = 'Test action item'
		self.ActionItems.append(AI)
		AI.Numbering = core_classes.NumberingItem()
		# put a serial number into the numbering object
		SerialObj = core_classes.SerialNumberChunkItem()
		AI.Numbering.NumberStructure = [SerialObj]

	def SetupNumbering(self): # set up default numbering scheme for FTEventInCore instance
		self.Numbering = core_classes.NumberingItem()
		# put a serial number into the numbering object
		SerialObj = core_classes.SerialNumberChunkItem()
		self.Numbering.NumberStructure = [SerialObj]

	def SetAvailableEventTypes(self):
		# work out what types of event this FTObjectInCore instance can be.
		# Return list of event types (list of str), default event type (str)
		AvailEventTypes = ['IPL', 'EnablingCondition', 'ConditionalModifier', 'ConnectorIn'] # these are always allowed
		if self.Column.ColNo == 0: # these are only allowed in 1st column
			AvailEventTypes.append('InitiatingEvent')
			if self.FT.OpMode in [core_classes.HighDemandMode, core_classes.ContinuousMode]:
				AvailEventTypes.append('SIFFailureEvent') # only allowed in these OpModes
		else:
			AvailEventTypes.extend(['TopEvent', 'IntermediateEvent', 'ConnectorOut'])
		# sort into the same order as EventTypes, for nice display
		AvailEventTypesForDisplay = [t for t in self.EventTypes if t in AvailEventTypes]
		return AvailEventTypesForDisplay, AvailEventTypesForDisplay[0]

	def ChangeEventType(self, NewEventType=None, ChangingOpMode=False): # change this FTEvent's type to NewEventType
		# NewEventType (str): new event type to apply. Ignored if ChangingOpMode is True (will use DefaultEventType)
		# ChangingOpMode (bool): whether we're changing event type due to a change of operating mode
		assert isinstance(ChangingOpMode, bool)
		assert (NewEventType in self.AvailEventTypes) or (ChangingOpMode and (NewEventType is None))
		if ChangingOpMode: NewEventTypeToApply = self.DefaultEventType
		else: NewEventTypeToApply = NewEventType
		# are we changing from SIFFailureEvent? If so, don't store the old value (it was calculated, not manual)
		ChangingFromSIFFailureEvent = (self.EventType == 'SIFFailureEvent') and (NewEventTypeToApply != 'SIFFailureEvent')
		ChangingToProbEvent = (NewEventTypeToApply in self.EventTypesWithProbValue)
		ChangingToFreqEvent = (NewEventTypeToApply in self.EventTypesWithFreqValue)
		# are we changing from a probability based event to a frequency based one, or vice versa?
		ChangingFromFreqToProbEvent = (self.EventType in self.EventTypesWithFreqValue) and ChangingToProbEvent
		ChangingFromProbToFreqEvent = (self.EventType in self.EventTypesWithProbValue) and ChangingToFreqEvent
		# decide if we need to change value kind
		ChangeToUserValueKind = (NewEventType in FTEventInCore.EventTypesWithUserValues) and\
			(type(self.Value) not in FTEventInCore.UserSuppliedNumberKinds)
		ChangeToDerivedValueKind = (NewEventType in FTEventInCore.EventTypesWithDerivedValues) and\
			(type(self.Value) not in FTEventInCore.DerivedNumberKinds)
		# is the existing value kind 'user defined'? If so, store the value for later use
		if isinstance(self.Value, core_classes.UserNumValueItem):
			# keep old probability value to restore
			if ChangingFromProbToFreqEvent: self.OldProbValue = copy.copy(self.Value)
			# keep old frequency value to restore
			if ChangingFromFreqToProbEvent: self.OldFreqValue = copy.copy(self.Value)
		# restore old frequency value
		if ChangingFromFreqToProbEvent or ((ChangingFromSIFFailureEvent or ChangeToUserValueKind) and ChangingToProbEvent):
			self.Value = copy.copy(self.OldProbValue)
		# restore old probability value
		if ChangingFromProbToFreqEvent or ((ChangingFromSIFFailureEvent or ChangeToUserValueKind) and ChangingToFreqEvent):
			self.Value = copy.copy(self.OldFreqValue)
		# change to derived value kind if necessary
		if ChangeToDerivedValueKind:
			self.ChangeValueKind(NewValueKind=FTEventInCore.DefaultValueKind[NewEventType])
		if NewEventTypeToApply == 'SIFFailureEvent': self.SetAsSIFFailureEvent() # set this event as the SIF failure event
		else: self.EventType = NewEventTypeToApply

	def ChangeValueKind(self, NewValueKind=None):
		# change this FTEvent's value kind to NewValueKind (a NumValueItem subclass).
		# TODO fully implement [VRM] - currently only sets up an Auto value
		assert NewValueKind in core_classes.NumValueClasses
		# make a new instance of the target subclass of NumValueItem
		NewValueObj = NewValueKind()
		# copy any persistent attribs from the old to the new number object
		for ThisAttrib in core_classes.NumValueClasses.PersistentAttribs:
			if hasattr(self.Value, ThisAttrib): setattr(NewValueObj, ThisAttrib, getattr(self.Value, ThisAttrib))
		if NewValueKind == core_classes.AutoNumValueItem: # set up for 'derived value'
			NewValueObj.Calculator = self.GetEventValue  # provide method to get derived value (overridden by SetAsSIFFailureEvent())
			NewValueObj.StatusGetter = self.GetEventValueStatus  # provide method to get status
			NewValueObj.UnitGetter = NewValueObj.GetMyUserDefinedUnit # return current unit when requested
			# we could set an initial unit here, but we don't know what the user wants. So we set it the first time
			# the value is successfully calculated
		# overwrite the old Value with the new number object
		self.Value = NewValueObj

	def SetAsSIFFailureEvent(self): # this function should be called when we want to mark this FT event as the
		# "SIF failure" initiating event; only for High Demand and Continuous OpModes.
		# Returns: the FT event in this FT that was previously the SIF failure event; that will now be changed to an
		# "InitiatingEvent"
		# or None if there wasn't any
		# First, find any existing SIF failure event
		AlreadySetEvents = [e for e in WalkOverAllFTObjs(self.FT) if getattr(e, 'EventType', None) == 'SIFFailureEvent']
		assert len(AlreadySetEvents) < 2 # should be no more than 1 object previously flagged; if >1, it's a bug
		if AlreadySetEvents: # if any object was previously flagged, unflag it
			AlreadySetEvents[0].Value = copy.copy(AlreadySetEvents[0].ValueInLowDemandMode)
			AlreadySetEvents[0].EventType = 'InitiatingEvent'
			AlreadySetEvents[0].IsSIFFailureEventInRelevantOpMode = False
			ReturnValue = AlreadySetEvents[0]
		else:
			ReturnValue = None
		# set this event as the SIF failure event
		self.EventType = 'SIFFailureEvent'
		# Store ValueInLowDemandMode
		self.ValueInLowDemandMode = copy.copy(self.Value)
		self.IsSIFFailureEventInRelevantOpMode = True
		# Make and set up AutoNumValueItem for self.Value
		self.ChangeValueKind(NewValueKind=core_classes.AutoNumValueItem)
		self.Value.Calculator = self.CalcSIFFailureFreq
		self.Value.UnitGetter = None # %%% TODO: point to the getter for the unit of the tolerable frequency
		return ReturnValue

	def CalcSIFFailureFreq(self, RR, FormulaAntecedents, **args):
		# Calculate frequency of SIF failure (in High Demand or Continuous mode) that causes the FT top event to meet
		# tol risk target. Return result as a float if valid, else a NumProblemValue instance.
		assert isinstance(RR, core_classes.RiskReceptorItem)
		assert isinstance(self.FT, FTObjectInCore)
		assert self.EventType == 'SIFFailureEvent' # should only call this procedure if it's a SIF failure event
		# find FT event that's marked as top event
		TopEvents = [e for e in WalkOverAllFTObjs(self.FT) if getattr(e, 'EventType', None) == 'TopEvent']
		assert len(TopEvents) < 2 # should be no more than 1 object set as top event; if >1, it's a bug
		if TopEvents:
			# try to get tolerable frequency value and unit
			TolFreqValue, TolFreqUnit, TolFreqProblem, X = self.FT.TolFreq.Value(RR, FormulaAntecedents)
			if TolFreqProblem: # unable to get tol freq; can't calculate
				return core_classes.NumProblemValue_TolRiskNoSelFreq
			# validate tol freq parms
			assert isinstance(TolFreqValue, float)
			assert isinstance(TolFreqUnit, core_classes.UnitItem)
			if utilities.IsEffectivelyZero(TolFreqValue): # tolerable risk is set to zero; can't calculate
				return core_classes.NumProblemValue_DivisionByZero
			else:
				# set trial value and try to calculate FT outcome
				AutoValueObject = copy.copy(self.Value) # so that we can restore if afterwards TODO use ChangeValueKind()
				self.Value = core_classes.UserNumValueItem(HostObj=self)
				TrialValue = 1.0
				self.Value.SetMyValue(NewValue=TrialValue, RR=core_classes.DefaultRiskReceptor)
				self.Value.SetMyUnit(TolFreqUnit)
				OutcomeProblem = TopEvents[0].GetMyStatus(RR, FormulaAntecedents)
				assert isinstance(OutcomeProblem, core_classes.NumProblemValue)
				assert isinstance(OutcomeUnit, core_classes.UnitItem)
				if OutcomeProblem != 'ValueStatus_OK': # unable to calculate FT outcome
#					OutcomeProblem.ProblemEvent = ProblemEvent
					return OutcomeProblem
				else: # result is available, no problems reported by GetMyStatus
					# check the outcome unit matches the tolerable frequency unit
					OutcomeValue = TopEvents[0].GetMyValue(RR=RR, FormulaAntecedents=FormulaAntecedents)
					OutcomeUnit = TopEvents[0].GetMyUnit()
					assert isinstance(OutcomeValue, float)
					if OutcomeUnit == TolFreqUnit:
						# now we can calculate SIF failure freq. restore value object, then calculate and return
						self.Value = AutoValueObject
						return TrialValue * TolFreqValue / OutcomeValue
					else: # unit mismatch, can't calculate
						return core_classes.NumProblemValue_TolRiskUnitMismatch
		else:
			# if no event is marked as top event, we can't calculate; return problem indicator
			return core_classes.NumProblemValue_FTOutcomeUndef

	def CheckValue(self, NumValueInstance=None):
		# check whether value in NumValueInstance (a UserNumValueItem instance) is acceptable in the FTEvent
		# return a NumProblemValue instance
		assert isinstance(NumValueInstance, core_classes.NumValueItem) or (NumValueInstance is None)
		if isinstance(NumValueInstance, core_classes.NumValueClassesToCheckValid): # check numerical value supplied by user
			# check FTIE1: value >= 0; check FTIE2: value <= 1/day if frequency; check FTIE3: value <= 1.0 if probability
			ValueNow = NumValueInstance.GetMyValue(RR=self.FT.RiskReceptorGroupOnDisplay[0])
			IsFrequency = (self.EventType in self.EventTypesWithFreqValue) # whether this event is frequency-based
			if IsFrequency:
				MinValueAllowedPerDay = 0.0
				MaxValueAllowedPerDay = 1.0
				MinValueAllowedInMyUnit = MinValueAllowedPerDay * core_classes.PerDayUnit.Conversion.get(
					NumValueInstance.GetMyUnit(), -1e20)
				MaxValueAllowedInMyUnit = MaxValueAllowedPerDay * core_classes.PerDayUnit.Conversion.get(
					NumValueInstance.GetMyUnit(), 1e20)
			else: # it's a probability
				MinProbabilityAllowed = 0.0
				MaxProbabilityAllowed = 1.0
				MinValueAllowedInMyUnit = MinProbabilityAllowed * core_classes.ProbabilityUnit.Conversion.get(
					NumValueInstance.GetMyUnit(), -1e20)
				MaxValueAllowedInMyUnit = MaxProbabilityAllowed * core_classes.ProbabilityUnit.Conversion.get(
					NumValueInstance.GetMyUnit(), 1e20)
			# check value is in allowed range, allowing for rounding errors
			if (0.999 * MinValueAllowedInMyUnit) <= ValueNow < (1.001 * MaxValueAllowedInMyUnit):
				return core_classes.NumProblemValue_NoProblem
			else: return core_classes.NumProblemValue(InternalName='OutOfRange',
				HumanHelp=_('Outside acceptable range %s to %s') % \
					(str(utilities.RoundToSigFigs(MinValueAllowedInMyUnit, SigFigs=2)[0]),
					 str(utilities.RoundToSigFigs(MaxValueAllowedInMyUnit, SigFigs=2)[0])))
		else: # not an attrib that needs checking
			return core_classes.NumProblemValue_NoProblem

	def GetValueOriginObject(self, RR, **Args): # return element that yields value for this element
		assert isinstance(self.Value, core_classes.AutoNumValueItem)
		# find event connected to this one (should be only one; we find them all for bug trapping)
		ConnectFrom = JoinedFrom(self.FT, self, FirstOnly=False)
		assert len(ConnectFrom) == 1
		assert isinstance(ConnectFrom[0], (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
		return ConnectFrom[0].Value # where to get the value from

	def GetEventValue(self, RR, **Args): # return event value (float) if value kind is Auto
		# this gets called by the NumValue instance's Calculate() call
		assert isinstance(self.Value, core_classes.AutoNumValueItem)
		# find event connected to this one (should be only one; we find them all for bug trapping)
		ValueOriginObject = self.GetValueOriginObject(RR, **Args)
		if ValueOriginObject.Status(RR=RR) == core_classes.NumProblemValue_NoProblem:
			# fetch value from connected object
			ConnectedObjectValue = ValueOriginObject.GetMyValue(RR=RR)
			# check if this element's unit has ever been set; if not, set to the same as the connected object
			if self.Value.GetMyUnit() == core_classes.NullUnit:
				self.SetEventUnit(TargetUnit=ValueOriginObject.GetMyUnit())
			# convert value according to event's unit
			return ValueOriginObject.GetMyValue(RR=RR) * ValueOriginObject.GetMyUnit().Conversion[self.Value.GetMyUnit()]
		else: return None # can't get value

	def SetEventUnit(self, TargetUnit): # set unit of event
		assert isinstance(TargetUnit, core_classes.UnitItem)
		self.Value.SetMyUnit(TargetUnit)

#	def GetEventUnit(self, RR, **Args): # return event unit if value kind is Auto
#		# this is intended as a UnitGetter method for the number kind class. Not currently used
#		assert isinstance(self.Value, core_classes.AutoNumValueItem)
#		# find event connected to this one (should be only one; we find them all for bug trapping)
#		ValueOriginObject = self.GetValueOriginObject(RR, **Args)
#		if ValueOriginObject.Status(RR=RR) == core_classes.NumProblemValue_NoProblem:
#			# fetch value from connected object, and convert to required unit
#			return ValueOriginObject.GetMyUnit()
#		else: return None # can't get value

	def GetEventValueStatus(self, RR): # return event value status as a NumProblemValue instance, if value kind is Auto
		# this gets called by the NumValue instance's StatusGetter() call
		assert isinstance(self.Value, core_classes.AutoNumValueItem)
		ConnectFrom = JoinedFrom(self.FT, self, FirstOnly=False)
		if ConnectFrom: # is any event connected to this one? get status from the connected one
			assert len(ConnectFrom) == 1
			assert isinstance(ConnectFrom[0], (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
			print("FT1596 status of connected value: ", ConnectFrom[0].Value.Status(RR=RR).InternalName)
			return ConnectFrom[0].Value.Status(RR=RR)
		else: # not connected
			return core_classes.NumProblemValue_FTNotConnected

	def AcceptableUnits(self): # return list of units (UnitItem instances) this event can offer
		if self.EventType in self.EventTypesWithFreqValue:
			AcceptableUnits = core_classes.FrequencyUnits
		elif self.EventType in self.EventTypesWithProbValue:
			AcceptableUnits = core_classes.ProbabilityUnits
		else:
			raise ValueError("FT1383 don't know value type for event type '%s'" % self.EventType)
		return AcceptableUnits

	def ShowCommentsOnOff(self, CommentKind, Show): # show or hide comments in FTEvent
		# return XML confirmation message
		assert CommentKind in ['Description', 'Value']
		assert isinstance(Show, bool)
		if CommentKind == 'Description': self.ShowDescriptionComments = Show
		elif CommentKind == 'Value': self.ShowValueComments = Show
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def ShowActionItemsOnOff(self, Show):  # show or hide action items in FTEvent
		# return XML confirmation message
		assert isinstance(Show, bool)
		self.ShowActionItems = Show
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def ConnectToElement(self, DestinationEl): # make connection from this element to DestinationEl
		# redundant
		assert isinstance(DestinationEl, (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
		print("FT1975 connecting to: ", DestinationEl)
		self.ConnectTo.append(DestinationEl)
		# set DestinationEl's value unit appropriate to the value kind of the connected event
		DestinationEl.Value.SetMyUnit(DestinationEl.LastSelectedUnitPerQtyKind[self.Value.GetMyUnit().QtyKind])
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

class FTGateItemInCore(object): # logic gate in a Fault Tree, used in DataCore
#	AllFTGatesInCore = [] # register of all FTGates created; used to generate IDs
	InternalName = 'FTGateInCore'
	GateStyles = ['IEC 60617-12', 'IEEE 91', 'DIN 40700']
	Algorithms = ['OR', 'MutExcOR', 'AND', 'NOR', 'NAND', '2ooN', '3ooN']
	DefaultGateStyle = 'IEEE 91'
	MaxElementsConnectedToThis = 100 # arbitrary limit on number of inputs

	def __init__(self, Proj=None, FT=None, Column=None, ModelGate=None):
		# ModelGate is another FTGateItemInCore to derive formatting attributes from
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(FT, FTObjectInCore)
		assert isinstance(Column, FTColumnInCore)
		object.__init__(self)
#		self.ID = str(utilities.NextID(FTGateItemInCore.AllFTGatesInCore)) # generate unique ID; stored as str
#		FTGateItemInCore.AllFTGatesInCore.append(self) # add self to register. Must do after assigning self.ID
		FT.MaxElementID += 1 # find next available ID
		self.ID = str(FT.MaxElementID)
		print("FT1996 created FTGate in core with ID: ", self.ID, type(self.ID))
		self.Proj = Proj
		self.FT = FT
		self.Column = Column
		self.GateDescription = ''
		self.Value = core_classes.AutoNumValueItem(HostObj=self)
		self.Value.Calculator = self.GetMyValue
		self.Value.UnitGetter = self.GetMyUnit
		self.Value.StatusGetter = self.GetMyStatus
		# store the initial (and most recently user-selected) unit for each quantity kind
		self.LastSelectedUnitPerQtyKind = {'Probability': FTEventInCore.DefaultProbUnit,
			'Frequency': FTEventInCore.DefaultFreqUnit, 'Time': FTEventInCore.DefaultTimeUnit,
			'Ratio': FTEventInCore.DefaultRatioUnit}
		self.CollapseGroups = [] # CollapseGroup objects this object belongs to
		self.ConnectTo = [] # FT object instances in next column to the right
		self.Algorithm = FTGateItemInCore.Algorithms[0]  # must be in Algorithms
		self.MadeBySystem = False # True if the gate was made automatically and can't be edited by user
		self.GateDescriptionComments = [] # list of AssociatedTextItem instances
		self.ShowDescriptionComments = False # whether description comments are visible
		self.ActionItems = [] # list of AssociatedTextItem instances
		self.ShowActionItems = False
#		self.LinkedTo = [] # list of LinkItem instances of which this item is a LinkMaster
		self.LinkedFrom = [] # list of LinkItem instances for linking individual attribs to a master element elsewhere in the project
		# set up gate formatting based on ModelGate
		if ModelGate:
			assert isinstance(ModelGate, FTGateItemInCore)
			assert isinstance(ModelGate.BackgColour, str)
			self.BackgColour = ModelGate.BackgColour
			assert ModelGate.Style in FTGateItemInCore.GateStyles
			self.Style = ModelGate.Style
			assert isinstance(ModelGate.Numbering, core_classes.NumberingItem)
			self.Numbering = ModelGate.Numbering
		else:
			self.BackgColour = GateBaseColourStr
			self.Style = FTGateItemInCore.DefaultGateStyle # must be in GateStyles
			self.Numbering = core_classes.NumberingItem()

	def GetMyStatus(self, RiskReceptor=core_classes.DefaultRiskReceptor):
		# return NumProblemValue instance for specified risk receptor, indicating whether gate can be calculated
		# If there's a problem, populates return object with the problem-causing object.
		assert isinstance(self.FT, FTObjectInCore)
		# make list of input NumValueItem objects
		InputNumObjs = [Input.Value for Input in JoinedFrom(self.FT, self, FirstOnly=False)]
		# first, check if all input values are available
		InputProblems = [(Input, Input.Status(RiskReceptor)) for Input in InputNumObjs
			if Input.Status(RiskReceptor) is not core_classes.NumProblemValue_NoProblem]
		if InputProblems:
			ReportObj = copy.copy(InputProblems[0][1]) # make a problem report object to return
			ReportObj.ProblemObj = InputProblems[0][0] # store the FT object causing the problem
			return ReportObj
		else: # continue checks: get input values
			InputValues = [Input.GetMyValue(RR=RiskReceptor) for Input in InputNumObjs]
			# count how many probabilities and frequencies are in the input values
			ProbCount = len([InputItem for InputItem in InputNumObjs if InputItem.GetMyUnit().QtyKind == 'Probability'])
			FreqInputs = [InputItem for InputItem in InputNumObjs if InputItem.GetMyUnit().QtyKind == 'Frequency']
			FreqCount = len(FreqInputs)

			# OR/MutExcOR gate: make sure we aren't mixing probabilities and frequencies
			if self.Algorithm in ['OR', 'MutExcOR']:
				if (ProbCount > 0) and (FreqCount > 0):
					ReportObj = copy.copy(core_classes.NumProblemValue_BadOROperands) # make a problem report object to return
					ReportObj.ProblemObj = self # store the FT object causing the problem
					return ReportObj
			# AND gate: can't accept >1 frequency as input
			elif self.Algorithm == 'AND':
				# if exactly 1 input is a frequency, calculate the total frequency (product of input values)
				if FreqCount > 1:
					ReportObj = copy.copy(core_classes.NumProblemValue_BadANDOperands) # make a problem report object to return
					ReportObj.ProblemObj = self # store the FT object causing the problem
					return ReportObj
			# NOR/NAND gate: can't accept frequencies
			elif self.Algorithm in ['NOR', 'NAND']:
				if FreqCount > 0: # make a problem report object to return
					if self.Algorithm == 'NOR': ReportObj = copy.copy(core_classes.NumProblemValue_BadNOROperands)
					else: ReportObj = copy.copy(core_classes.NumProblemValue_BadNANDOperands)
					ReportObj.ProblemObj = self # store the FT object causing the problem
					return ReportObj
			# if we got here, all is well (assuming the algorithm is recognised)
			return core_classes.NumProblemValue_NoProblem

	def GetMyValue(self, RiskReceptor=core_classes.DefaultRiskReceptor, **Args):
		# calculate and return output value of the gate for specified risk receptor
		# assumes we have already run GetMyStatus() to confirm value is valid
		# returns value as float
		# 1st PHAObject yielding a problem value (or None)).
		assert isinstance(self.FT, FTObjectInCore)
		# make list of input NumValueItem objects, and of numerical values with units
		InputNumObjs = [Input.Value for Input in JoinedFrom(self.FT, self, FirstOnly=False)]
		InputValuesAndUnits = [(Input.GetMyValue(RR=RiskReceptor, **Args), Input.GetMyUnit()) for Input in InputNumObjs]
		# count how many probabilities and frequencies are in the input values
		ProbCount = len([InputItem for InputItem in InputNumObjs if InputItem.GetMyUnit().QtyKind == 'Probability'])
		FreqInputs = [InputItem for InputItem in InputNumObjs if InputItem.GetMyUnit().QtyKind == 'Frequency']
		FreqCount = len(FreqInputs)
		# get the unit to use for return value
		TargetFreqUnit = self.LastSelectedUnitPerQtyKind['Frequency']
		TargetProbUnit = self.LastSelectedUnitPerQtyKind['Probability']

		# OR gate: return 1 - product(1 - inputs)
		if self.Algorithm == 'OR':
			# if all inputs are frequencies, calculate the total frequency, converting units as required
			if ProbCount == 0:
				return sum([v * u.Conversion[TargetFreqUnit] for v, u in InputValuesAndUnits], 0.0)
			# (FIXME this doesn't account for "overlaps" where 2 events occur simultaneously)
			# if all inputs are probabilities, calculate the combined non-mutually-exclusive probability
			else:
				Result = 1.0
				# multiply 1-prob(event) for each input event. Convert values to probability (not %) for calculation
				for ThisValue, ThisUnit in InputValuesAndUnits:
					Result *= (1.0 - (ThisValue * ThisUnit.Conversion[core_classes.ProbabilityUnit]))
				# convert units back if necessary
				return Result * core_classes.ProbabilityUnit.Conversion[TargetProbUnit]

		# MutExcOR gate: return sum(inputs)
		elif self.Algorithm == 'MutExcOR':
			# if all inputs are frequencies, calculate the total frequency (sum of input frequencies)
			if ProbCount == 0:
				return sum([v * u.Conversion[TargetFreqUnit] for v, u in InputValuesAndUnits], 0.0)
			# if all inputs are probabilities, calculate the combined mutually-exclusive probability, limited to 1.0
			else:
				# convert values to probability (not %) for calculation, then convert back if necessary
				return core_classes.ProbabilityUnit.Conversion[TargetProbUnit] *\
					min(1.0, sum([v * u.Conversion[core_classes.ProbabilityUnit]
					for v, u in InputValuesAndUnits], 0.0))

		# AND gate: return product(inputs) (assumes input events are independent)
		elif self.Algorithm == 'AND':
			# if exactly 1 input is a frequency, calculate the total frequency by multiplying the one frequency input
			# by the other inputs (converted to probability units)
			if FreqCount == 1:
				Result = 1.0
				for v, u in InputValuesAndUnits:
					if u.QtyKind == 'Frequency': Result *= v * u.Conversion[TargetFreqUnit]
					else: Result *= v * u.Conversion[core_classes.ProbabilityUnit]
				return Result
			# if all inputs are probabilities, calculate the combined probability (product of input values converted to probability)
			else:
				Result = 1.0
				for ThisValue, ThisUnit in InputValuesAndUnits:
					Result *= ThisValue * ThisUnit.Conversion[core_classes.ProbabilityUnit]
				# convert result to required unit
				return core_classes.ProbabilityUnit.Conversion[TargetProbUnit] * Result

		# NOR gate: return 1 - combined non-mutually-exclusive probability. Has no meaning for frequency inputs
		elif self.Algorithm == 'NOR':
			Result = 1.0
			for ThisValue, ThisUnit in InputValuesAndUnits:
				Result *= (1.0 - (ThisValue * ThisUnit.Conversion[core_classes.ProbabilityUnit]))
			# convert to final required unit
			return core_classes.ProbabilityUnit.Conversion[TargetProbUnit] * Result

		# NAND gate: return 1 - combined probability. Has no meaning for frequency inputs
		elif self.Algorithm == 'NAND':
			Result = 1.0
			for ThisValue, ThisUnit in InputValuesAndUnits:
				# convert values to probability (not %) for calculation, then convert back if necessary
				Result *= (1.0 - (ThisValue * ThisUnit.Conversion[core_classes.ProbabilityUnit]))
			# convert to final required unit
			return core_classes.ProbabilityUnit.Conversion[TargetProbUnit] * Result

		elif self.Algorithm in ['2ooN', '3ooN']:
			# convert input values to probability
			InputsAsProb = [(1.0 - (v * u.Conversion[core_classes.ProbabilityUnit])) for v, u in InputValuesAndUnits]
			NoOfInputs = len(InputValuesAndUnits)
			# get how many inputs required True as a minimum
			MinTrueInputs = {'2ooN': 2, '3ooN': 3}[self.Algorithm]
			# add up the probabilities of all combinations of inputs with >= MinTrueInputs True
			ProbResult = 0
			for NoOfTrueInputs in range(MinTrueInputs, NoOfInputs + 1):
				ThisCombinationGenerator = NextCombination(Length=NoOfInputs, PassMark=NoOfTrueInputs)
				for ThisCombination in ThisCombinationGenerator: # go through combinations with NoOfTrueInputs True
					ThisProb = 1.0
					for InputIndex, ThisValue in enumerate(InputsAsProb):
						if ThisCombination(InputIndex): ThisProb *= ThisValue
					ProbResult += ThisProb
			# convert to user requested unit
			return core_classes.ProbabilityUnit.Conversion[TargetProbUnit] * ProbResult

	def GetMyUnit(self): # return currently applicable unit
		# make list of input NumValueItem objects, and of numerical values with units
		InputNumObjs = [Input.Value for Input in JoinedFrom(self.FT, self, FirstOnly=False)]
		# count how many probabilities and frequencies are in the input values
		ProbCount = len([InputItem for InputItem in InputNumObjs if InputItem.GetMyUnit().QtyKind == 'Probability'])
		FreqInputs = [InputItem for InputItem in InputNumObjs if InputItem.GetMyUnit().QtyKind == 'Frequency']
		FreqCount = len(FreqInputs)
		# get the unit to use if gate's output value is either frequency or probability
		TargetFreqUnit = self.LastSelectedUnitPerQtyKind['Frequency']
		TargetProbUnit = self.LastSelectedUnitPerQtyKind['Probability']

		# OR gate: return 1 - product(1 - inputs)
		if self.Algorithm in ['OR', 'MutExcOR']:
			# if all inputs are frequencies, return frequency unit
			if ProbCount == 0: return TargetFreqUnit
			# if all inputs are probabilities, return probability unit
			else: return TargetProbUnit

		# AND gate: return product(inputs) (assumes input events are independent)
		elif self.Algorithm == 'AND':
			# if exactly 1 input is a frequency, return frequency unit
			# by the other inputs (converted to probability units)
			if FreqCount == 1: return TargetFreqUnit
			# if all inputs are probabilities, return probability unit
			else: return TargetProbUnit

		# NOR/NAND/MooN gate: return probability unit. Has no meaning for frequency inputs
		elif self.Algorithm in ['NOR', 'NAND', '2ooN', '3ooN']: return TargetProbUnit

	def ChangeGateKind(self, NewGateKind=None): # change this FTGate's algorithm to NewGateKind
		# NewGateKind (str): new algorithm to apply
		assert NewGateKind in self.Algorithms
		self.Algorithm = NewGateKind

	def AcceptableUnits(self): # return list of units (UnitItem instances) this gate can offer.
		# Currently, it offers all available units as defined in core_classes module.
		# find out what kind of unit is currently selected
		CurrentUnitKind = self.GetMyUnit().QtyKind
		if CurrentUnitKind == 'Probability': return core_classes.ProbabilityUnits[:]
		elif CurrentUnitKind == 'Frequency': return core_classes.FrequencyUnits[:]
		elif CurrentUnitKind == 'Time': return core_classes.TimeUnits[:]
		elif CurrentUnitKind == 'Ratio': return core_classes.RatioUnits[:]
		else: raise TypeError("FT2196 don't know unit type '%s' for gate" % CurrentUnitKind)

	def SetLastSelectedUnit(self, NewUnit): # set gate's "last selected unit" attrib. Call this after changing units
		if NewUnit.QtyKind == 'Probability': self.LastSelectedUnitPerQtyKind['Probability'] = NewUnit
		elif NewUnit.QtyKind == 'Frequency': self.LastSelectedUnitPerQtyKind['Frequency'] = NewUnit
		else: print("CC2203 warning, unexpected QtyKind for gate value: ", NewUnit.QtyKind)

def NextCombination(Length, PassMark):
	# generator function returning the next combination (list) in a sequence of combinations.
	# Each combination is a Length-long (int) list of True's and False's, of which exactly PassMark (int) items are True
	# Warning: as this generator returns a mutable object, we must retrieve copies of the yielded values.
	assert isinstance(Length, int)
	assert isinstance(PassMark, int)
	assert Length >= PassMark > 0
	LastList = [True] * PassMark + [False] * (Length - PassMark) # starting combination
	print("FT2086 yielding: ", LastList)
	yield LastList # return starting combination
	NotFinished = True # whether there are more combinations remaining
	while NotFinished:
		# find next combination: if last item is False, move last True one place to right
		if not LastList[-1]:
			LastTrueIndex = [i for i in range(Length) if LastList[i]][-1]
			LastList[LastTrueIndex] = False
			LastList[LastTrueIndex + 1] = True
			print("FT2289 yielding: ", LastList)
			yield LastList
		else: # find the rightmost [True, False] sequence in LastList, if any (if none found, all combinations exhausted)
			LastTFIndexList = [i for i in range(Length - 2) if LastList[i] if not LastList[i + 1]]
			NotFinished = bool(LastTFIndexList)
			if NotFinished:
				LastTFIndex = LastTFIndexList[-1]
				# move the True in the T, F sequence one place to the right, fill up the required number of Trues to its
				# right, and fill up remaining positions with False
				LastList[LastTFIndex] = False
				LastList = LastList[:LastTFIndex + 1] + [True] * (PassMark - LastList[:LastTFIndex].count(True))
				LastList = LastList + [False] * (Length - len(LastList))
				print("FT2301 yielding: ", LastList)
				yield LastList
	return # finished

class FTConnectorItemInCore(object):  # in- and out-connectors (CX's) to allow data transfer between multiple FTs
	AllFTCXInCore = [] # register of all FTConnectors currently active in Vizop; used to generate unique IDs
	ConnectorStyles = ['Default'] # future, will define various connector appearances (squares, arrows, circles etc)
	MaxElementsConnectedToThis = 1

	def __init__(self, FT): # FT is the FaultTree object this connector belongs to
		object.__init__(self)
#		self.ID = str(utilities.NextID(FTConnectorItemInCore.AllFTCXInCore)) # generate unique ID; stored as str
#		FTConnectorItemInCore.AllFTCXInCore.append(self) # add self to register. Must do after assigning self.ID
		assert isinstance(FT, FTObjectInCore)
		FT.MaxElementID += 1 # find next available ID
		self.ID = str(FT.MaxElementID)
		self.FT = FT
		self.Out = True # True if this is an out-CX (else, it is an in-CX)
		self.ConnectorDescription = '' # text shown in the CX, if it's an out-CX. Also shown in in-CX if RelatedCX is None.
		# If it's an in-CX, this is ignored and the displayed text is derived from the connected out-CX
		self.ConnectorDescriptionComments = [] # list of AssociatedTextItem instances
		self.ShowDescriptionComments = False # whether description comments are visible
		self.RelatedCX = None # an FTConnectorItemInCore instance:
			# If this is in-CX, defines which out-CX it's connected to. If out-CX, should be None
		self.BackgColour = '0,0,255' # blue
		self.ConnectTo = [] # FT object instances in next column to the right
		self.CollapseGroups = [] # CollapseGroup objects this event belongs to
		self.Numbering = core_classes.NumberingItem() # NumberingItem instance TODO use SetupNumbering() from FTEventInCore
			# NB, in-CX should use numbering from any related out-CX; but if RelatedCX is None, it still needs its own Numbering
		self.Style = FTConnector.ConnectorStyles[0]
		self.ApplicableRiskReceptors = FT.MyTolRiskModel.RiskReceptors[:] # set which risk receptors apply to this connector
			# NB, in-CX should use RR's from any related out-CX; but if RelatedCX is None, it still needs its own RR list

	def GetMyValue(self, RiskReceptor=core_classes.DefaultRiskReceptor):
		# calculate and return output value of the connector for specified risk receptor
		# returns (float, UnitItem instance, 1st NumProblemValue in calculation chain (or None),
		# 1st PHAObject yielding a problem value (or None).
		assert isinstance(RiskReceptor, core_classes.RiskReceptorItem)
		if self.Out: # if this is an out-CX, its value is obtained from joined-from object
			JoinedFromObj = JoinedFrom(self.FT, self, FirstOnly=True)[0]
			if not JoinedFromObj: # not connected; return problem indicator
				return 0, core_classes.NullUnit, core_classes.NumProblemValue_BrokenLink, self
			return JoinedFromObj.Value # return tuple received from .Value method
		else: # it's an in-CX: get value from the out-CX it's related to
			if self.RelatedCX is None: # not connected; return problem indicator
				return 0, core_classes.NullUnit, core_classes.NumProblemValue_BrokenLink, self
			assert isinstance(self.RelatedCX, FTConnectorItemInCore)
			return self.RelatedCX.Value

	Value = property(fget=GetMyValue) # returns (value, UnitItem, any NumProblemValue, ID of object yielding NumProb)

class FTCollapseGroupInCore(object): # collapse group containing one or more FT elements that can be shown collapsed
	# into a single object for more compact display

	def __init__(self, FT): # FT is the FaultTree object this connector belongs to
		object.__init__(self)
		assert isinstance(FT, FTObjectInCore)
		FT.MaxElementID += 1  # find next available ID
		self.ID = str(FT.MaxElementID)
		self.FT = FT
		self.CollapseGroupDescription = '' # text shown in the collapse group, if collapsed
		self.CollapsedInitially = False # whether the collapse group is shown collapsed when the FT is first displayed.
			# Users can collapse/expand collapse groups in the Viewports without changing this attribute, so it doesn't
			# necessarily reflect the current status of collapse groups - only the status when loaded from file.
		self.BackgColour = '0,0,255' # blue

class FTForDisplay(display_utilities.ViewportBaseClass): # forward definition to allow use in FTObjectInCore
	InternalName = 'Forward'

class FTObjectInCore(core_classes.PHAModelBaseClass):
	# defines Fault Tree object as stored in DataCore. This represents an entire fault tree.
	# It's handled and accessed only by DataCore, not by Viewports.
	IsBaseClass = False # must do this for every PHAModelBaseClass subclass
	PreferredKbdShortcut = 'f'
	HumanName = _('Fault Tree')
	InternalName = 'FT'
	AllFTObjects = [] # register of all instances defined
	RiskRedMeasures = ['RRF', 'PFD', 'PFH'] # permitted values of self.TargetRiskRedMeasure
	RRGroupingOptions = ['Grouped', 'Singly'] # whether risk receptors are shown grouped or separately
	DefaultRRGroupingOption = RRGroupingOptions[0]
	DefaultViewportType = FTForDisplay
	# names of attribs referring to header, whose value is the same as the text in the XML tag
	TextComponentNames = ['SIFName', 'Rev', 'SILTargetValue', 'TargetRiskRedMeasure', 'BackgColour',
							   'TextColour']
	# English names for components; keys are attrib names in this class. Values are translated at point of display
	ComponentEnglishNames = {'SIFName': 'SIF name', 'Rev': 'Revision', 'OpMode': 'Operating mode',
		'TolFreq': 'Tolerable frequency', 'SILTargetValue': 'SIL target'}
	# element classes that have a number system, i.e. have a Numbering attrib. Must be tuple, not list
	ElementsWithNumberSystem = (FTConnectorItemInCore, FTGateItemInCore, FTEventInCore)

	def __init__(self, Proj, **Args):
		core_classes.PHAModelBaseClass.__init__(self, Proj, **Args)
		# ID is already assigned in PHAModelBaseClass.__init__
		# self.EditAllowed attrib is inherited from base class
		FTObjectInCore.AllFTObjects.append(self) # add self to register; must do after assigning self.ID
		self.MaxElementID = 0 # Highest ID (int) of all elements in this FT. Used only to determine next available ID
		# set up numbering for the FT itself - to appear in a high-level list of all FTs in the project
		self.Numbering = core_classes.NumberingItem()
		# put a serial number into the numbering object
		SerialObj = core_classes.SerialNumberChunkItem()
		self.Numbering.NumberStructure = [SerialObj]
		# define object-wide attributes. Many of these are displayed in the FT header
		self.SIFName = ''
		self.OpMode = core_classes.DefaultOpMode # instance of OpModeType
		self.Rev = ''
		self.TargetRiskRedMeasure = 'RRF' # can take values in RiskRedMeasures
		self.SILTargetValue = '' # set by self.TargetRiskRed()
		self.BackgColour = '0,0,0' # string of rgb values (no point in using wx.Colour or tuple as we have to convert it)
		self.TextColour = '255,255,255'
		# data content of FTObjectInCore
		self.Columns = [FTColumnInCore(self)] # contains FTColumnInCore instances. Start with one empty column
		# AttribTypeHash (dict): keys are attrib names in FTObjectInCore (str), values are acceptable values for the attrib (list)
		# Need a key for each attrib that presents to the user as a choice widget
		self.MyTolRiskModel = Proj.CurrentTolRiskModel
		# set initial severity per risk receptor = maximum severity. Severity is dict: {RR: Severity category object}
		SeverityObjs = self.MyTolRiskModel.TolFreqTable.Keys[self.MyTolRiskModel.TolFreqTable.SeverityDimensionIndex]
		self.Severity = dict([(RR, SeverityObjs[-1]) for RR in self.MyTolRiskModel.RiskReceptors])
		# get initial tolerable frequency value (value object containing all RRs), based on defaults in tolerable risk model
		self.TolFreq = core_classes.UserNumValueItem(MaxValue=1e3, MinValue=1e-20, MaxMinUnit=core_classes.PerYearUnit)
		self.SetTolFreq()
		self.RRGroupingOption = FTObjectInCore.DefaultRRGroupingOption # whether risk receptors are shown grouped
		self.RefreshRiskReceptorGrouping(GroupingOption=self.RRGroupingOption, FirstTime=True)
		self.AttribValueHash = {'OpMode': core_classes.OpModes, 'RR': self.RiskReceptorGroupOnDisplay,
			'Severity': SeverityObjs}
		self.ModelGate = None # (None or FTGateItemInCore instance in this FT) gate to use as model when creating a new gate
		self.CollapseGroups = [] # list of instances of FTCollapseGroupInCore

	def SetTolFreq(self): # set tolerable frequency for all risk receptors, by lookup in risk model according to severity
		for RR in self.MyTolRiskModel.RiskReceptors:
			TolFreqValueObj = self.MyTolRiskModel.TolFreqTable.Lookup(Categories=[self.Severity[RR]])
			# copy value and unit from tol freq table (to avoid creating link between TolFreq and an item in the table)
			self.TolFreq.SetMyValue(TolFreqValueObj.GetMyValue(RR=RR), RR=RR)
			self.TolFreq.SetMyUnit(TolFreqValueObj.GetMyUnit()) # setting the same unit several times, never mind
		# set lists of permissible units and ValueKinds; used elsewhere to offer options to user
		self.TolFreq.AcceptableUnits = core_classes.FrequencyUnits
		self.TolFreq.ValueKindOptions = [core_classes.UserNumValueItem, core_classes.ConstNumValueItem,
			core_classes.LookupNumValueItem, core_classes.UseParentValueItem, core_classes.ParentNumValueItem]

	def AcceptableUnits(self): # return list of units (UnitItem instances) for FT's TolFreq
		return core_classes.FrequencyUnits

	def AcceptableValueKinds(self): # return list of value kinds (subclasses of NumValueItem) for FT's TolFreq
		return [core_classes.UserNumValueItem, core_classes.ConstNumValueItem, core_classes.LookupNumValueItem,
			core_classes.ParentNumValueItem, core_classes.UseParentValueItem]

	def RefreshRiskReceptorGrouping(self, GroupingOption, FirstTime=False):
		# re-group risk receptors and select appropriate group to be displayed
		# FirstTime (bool): whether this is the first grouping of RR's (for newly created FTObjectInCore instance)
		assert isinstance(FirstTime, bool)
		if FirstTime: Old1stRROnDisplay = None
		else: Old1stRROnDisplay = self.RiskReceptorGroupOnDisplay[0] # which RR the user can currently see
		self.RiskReceptorGroups = self.WorkOutRiskReceptorGrouping(GroupingOption=GroupingOption)
		# select RR group so that user can still see the same RR that was on display before
		self.RiskReceptorGroupOnDisplay = [g for g in self.RiskReceptorGroups
			if (FirstTime or (Old1stRROnDisplay in g))][0]

	def GetAllObjsWithNumberSystems(self):
		# a generator yielding FT components from FT that contain numbering systems
		# This is a required method for all PHA object classes
		# first, return the FT itself
		yield self
		# then, iterate over all elements in all columns
		for Col in self.Columns:
			assert isinstance(Col, FTColumnInCore)
			for ThisElement in Col.FTElements:
				if isinstance(ThisElement, self.ElementsWithNumberSystem):
					yield ThisElement
		return

	def GetOutcome(self):
		# Get FT outcome value. In Low Demand mode, this is the value of the top event; else, value of SIFFailureEvent object
		# Returns ValueInfoItem instance
		assert self.OpMode in core_classes.OpModes
		# find event(s) flagged as top event or SIF Failure event depending on OpMode
		if self.OpMode == core_classes.LowDemandMode:
			OutcomeEvents = [e for e in WalkOverAllFTObjs(self) if getattr(e, 'EventType', None) == 'TopEvent']
		else:
			OutcomeEvents = [e for e in WalkOverAllFTObjs(self) if getattr(e, 'EventType', None) == 'SIFFailureEvent']
		assert len(OutcomeEvents) <= 1 # should be only one such event; if not, it's a bug
		if OutcomeEvents: return OutcomeEvents[0].Value
		else: # no event flagged; return problem indicator
			return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
				Problem=core_classes.NumProblemValue_FTOutcomeUndef, ProblemObj=None)

	Outcome = property(fget=GetOutcome)

	def TargetRiskRed(self, RR):
		# return target risk reduction requirement value (ValueInfoItem instance) from the SIF analysed in the FT.
		# Also sets self.SILTargetValue (str), which can be retrieved immediately after calling Outcome().
		# If Outcome() reports a problem, the same problem should be considered to apply to SILTargetValue, and
		# SILTargetValue will be set to ''.
		# RR is risk receptor instance
		assert self.OpMode in core_classes.OpModes
		assert self.TargetRiskRedMeasure in FTObjectInCore.RiskRedMeasures
		assert isinstance(RR, core_classes.RiskReceptorItem)
		self.SILTargetValue = '' # default value if SIL target can't be assessed
		if self.OpMode in [core_classes.HighDemandMode, core_classes.ContinuousMode]:
			# get PFH from FT event flagged as SIF Failure event
			SIFFailureEvents = [e for e in WalkOverAllFTObjs(self) if getattr(e, 'EventType', None) == 'SIFFailureEvent']
			assert len(SIFFailureEvents) <= 1 # should be no more than 1 object flagged; if >1, it's a bug
			if SIFFailureEvents: # a SIFFailure event is flagged; get its status to see if the frequency value is available
				ProblemValue = SIFFailureEvents[0].Value.Status(RR=RR)
				if ProblemValue is core_classes.NumProblemValue_NoProblem: # value available, fetch it
					SFEValue = SIFFailureEvents[0].Value.GetMyValue(RR=RR)
					SFEUnit = SIFFailureEvents[0].Value.GetMyUnit()
					assert isinstance(SFEValue, float)
					assert isinstance(SFEUnit, core_classes.UnitItem)
					# return PFH, converted to hr^-1
					assert SFEUnit.QtyKind == 'Frequency'
					assert core_classes.PerHourUnit in SFEUnit.Conversion
					PFHTarget = SFEValue * SFEUnit.Conversion[core_classes.PerHourUnit]
					self.SILTargetValue = SILTarget(Mode=self.OpMode, RiskRed=PFHTarget)
					assert isinstance(self.SILTargetValue, str)
					return core_classes.ValueInfoItem(Value=PFHTarget, Unit=core_classes.PerHourUnit,
						Problem=core_classes.NumProblemValue_NoProblem, ProblemObj=None)
				else: # value can't be calculated for some reason
					return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit, Problem=ProblemValue,
						ProblemObj=ProblemValue.ProblemEvent)
			else: # no SIFFailureEvent flagged; can't return value
				return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
					Problem=core_classes.NumProblemValue_FTSFEUndef, ProblemObj=None)
		else: # Low Demand mode: get the value of the FT Event flagged as top event
			OutcomeEvents = [e for e in WalkOverAllFTObjs(self) if getattr(e, 'EventType', None) == 'TopEvent']
			assert len(OutcomeEvents) <= 1 # should be no more than 1 object flagged; if >1, it's a bug
			if OutcomeEvents: # an OutcomeEvent is flagged; get its status to see if the frequency value is available
				ProblemValue = OutcomeEvents[0].Value.Status(RR=RR)
				if ProblemValue is core_classes.NumProblemValue_NoProblem: # value available, fetch it
					OutcomeValue = OutcomeEvents[0].Value.GetMyValue(RR=RR)
					OutcomeUnit = OutcomeEvents[0].Value.GetMyUnit()
					assert isinstance(OutcomeValue, float)
					assert isinstance(OutcomeUnit, core_classes.UnitItem)
					# try to get FT's tolerable frequency
					assert isinstance(self.TolFreq, core_classes.NumValueItem)
					ProblemValue = self.TolFreq.Status(RR)
					if ProblemValue is core_classes.NumProblemValue_NoProblem:
						TolFreqValue = self.TolFreq.GetMyValue(RR=RR)
						TolFreqUnit = self.TolFreq.GetMyUnit()
						# check the tol freq is usable
						assert isinstance(TolFreqValue, float)
						assert isinstance(TolFreqUnit, core_classes.UnitItem)
						assert TolFreqUnit in OutcomeUnit.Conversion # ensure unit conversion factor defined
						assert self.TargetRiskRedMeasure in ['RRF', 'PFD']
						if utilities.IsEffectivelyZero(TolFreqUnit): # tol freq is zero, can't calculate
							return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
								Problem=core_classes.NumProblemValue_DivisionByZero, ProblemObj=None)
						elif TolFreqUnit.QtyKind != 'Frequency': # tol freq isn't a frequency, can't calculate
							return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
								Problem=core_classes.NumProblemValue_TolRiskUnitMismatch, ProblemObj=None)
						elif OutcomeUnit.QtyKind != 'Frequency': # outcome event isn't a frequency, can't calculate
							return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
								Problem=core_classes.NumProblemValue_TolRiskUnitMismatch,
								ProblemObj=OutcomeEvents[0])
						else: # all good, calculate RRF target
							RRFTarget = max(1.0, OutcomeValue * OutcomeUnit.Conversion(TolFreqUnit) / TolFreqValue)
							self.SILTargetValue = SILTarget(Mode=self.OpMode, RiskRed=RRFTarget)
							assert isinstance(self.SILTargetValue, str)
							if self.TargetRiskRedMeasure == 'RRF':
								return core_classes.ValueInfoItem(Value=RRFTarget, Unit=core_classes.DimensionlessUnit,
									Problem=core_classes.NumProblemValue_NoProblem, ProblemObj=None)
							else: # return PFDavg target
								return core_classes.ValueInfoItem(Value=1.0 / RRFTarget,
									Unit=core_classes.ProbabilityUnit, Problem=core_classes.NumProblemValue_NoProblem,
									ProblemObj=None)
					else: # tol freq can't be obtained for some reason
						return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit, Problem=ProblemValue,
							ProblemObj=ProblemValue.ProblemEvent)
				else:  # outcome value can't be calculated for some reason
					return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
						Problem=ProblemValue, ProblemObj=ProblemValue.ProblemEvent)
			else: # no OutcomeEvent flagged
				return core_classes.ValueInfoItem(Value=0.0, Unit=core_classes.NullUnit,
					Problem=core_classes.NumProblemValue_FTOutcomeUndef, ProblemObj=None)

	def WorkOutRiskReceptorGrouping(self, GroupingOption='Grouped'):
		# if GroupingOption  == 'Grouped',
		# work out what risk receptors can be grouped together for display, based on RR's having different calculations
		# in the FT. Otherwise, return separate groups for each risk receptor.
		# returns list of lists: inner lists are RiskReceptorItem instances that can be grouped together
		if GroupingOption == 'Grouped':
			RemainingRiskReceptors = self.MyTolRiskModel.RiskReceptors[:] # RR's to consider
			OutputList = [] # list of lists of grouped RR's
			while RemainingRiskReceptors:
				ThisRR = RemainingRiskReceptors.pop(0) # get RR to compare against, popped from start of the list
				if len(RemainingRiskReceptors) > 0: # are there any other RR's to compare against?
					MatchList = [ThisRR] # build list of RR's that can be grouped together
					for ComparingRR in RemainingRiskReceptors: # check all other RR's remaining against ThisRR
						# first, check severity and tolerable frequency
						Matched = (self.Severity[ThisRR] == self.Severity[ComparingRR]) and\
							(self.TolFreq.GetMyValue(RR=ThisRR) == self.TolFreq.GetMyValue(RR=ComparingRR))
						# check RR's apply to all the same events (including IPLs) and connectors
						for ThisObj in WalkOverAllFTObjs(self):
							if isinstance(ThisObj, (FTEventInCore, FTConnectorItemInCore)):
								if ThisRR in ThisObj.ApplicableRiskReceptors:
									Matched = Matched and (ComparingRR in ThisObj.ApplicableRiskReceptors)
						if Matched: # if RR's match, put ComparingRR into MatchList and proceed to next RR
							MatchList.append(ComparingRR)
							RemainingRiskReceptors.remove(ComparingRR)
					OutputList.append(MatchList) # put the list of matched RR's into the output list
				else: # no remaining RR's to compare against; just put the one remaining RR in the output list
					OutputList.append([ThisRR])
					RemainingRiskReceptors = [] # remove it from the 'remaining' list
			return OutputList
		elif GroupingOption == 'Singly':
			return [ [r] for r in self.MyTolRiskModel.RiskReceptors] # return RR's in individual groups
		else: raise ValueError("Unknown GroupingOption '%s'" % GroupingOption)

	def GetFullRedrawData(self, Viewport=None, ViewportClass=None, **Args):
		# return all data in FTObjectInCore as an XML tree, for sending to Viewport to fully draw the FT
		# Viewport (instance of ViewportShadow): the Viewport to be displayed (not currently used)
		# ViewportClass (subclass of ViewportBaseClass): the class of the displayable Viewport
		# Args: can include ExtraXMLTagsAsDict (dict; keys: tags to be included in output XML data; values: tag texts)
		# Args: can include ExtraXMLTagsAsTags (ElementTree XML element to append directly to XML tree)

		def PopulateOverallData(El): # put data relating to FT as a whole into XML element El
			# add FT object's ID as text of El, then OpMode as a tag
			El.text = self.ID
			OpModeEl = ElementTree.SubElement(El, info.OpModeTag)
			OpModeEl.text = self.OpMode.XMLName
			# add HumanNames of risk receptors, appropriately grouped together
			for (ThisRRGroupIndex, ThisRRGroup) in enumerate(self.RiskReceptorGroups):
				RREl = ElementTree.SubElement(El, info.RiskReceptorTag)
				# set human name for RR group to list of RR names separated by commas
				RREl.text = info.ListSeparator.join([RR.HumanName for RR in ThisRRGroup])
				RREl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisRRGroup == self.RiskReceptorGroupOnDisplay))
				RREl.set(info.SerialTag, str(ThisRRGroupIndex)) # add risk receptor group serial number
			# add HumanNames of severity categories
			ThisTolFreqTable = self.MyTolRiskModel.TolFreqTable
			for (ThisSeverityCatIndex, ThisSeverityCategory) in \
					enumerate(ThisTolFreqTable.Keys[ThisTolFreqTable.SeverityDimensionIndex]):
				SeverityCatEl = ElementTree.SubElement(El, info.SeverityCatTag)
				# set human name for severity category
				SeverityCatEl.text = ThisSeverityCategory.HumanName
				# set 'we are showing this category' flag to True if the severity is the same as the first RR on display
				SeverityCatEl.set(info.ApplicableAttribName,
					utilities.Bool2Str(ThisSeverityCategory == self.Severity[self.RiskReceptorGroupOnDisplay[0]]))
				SeverityCatEl.set(info.SerialTag, str(ThisSeverityCatIndex)) # add severity category serial number
			# add options for risk receptor grouping
			for (ThisGroupingOptionIndex, ThisGroupingOption) in enumerate(self.RRGroupingOptions):
				RRGroupingEl = ElementTree.SubElement(El, info.RiskReceptorGroupingOptionTag)
				# set human name for grouping option to internal name of option
				RRGroupingEl.text = str(ThisGroupingOption)
				RRGroupingEl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisGroupingOption == self.RRGroupingOption))
				RRGroupingEl.set(info.SerialTag, str(ThisGroupingOptionIndex)) # add grouping option serial number

		def PopulateHeaderData(El):
			# put FT header data into XML element El
			if __debug__ == 1: # do type checks
				assert isinstance(El, ElementTree.Element), "FT1658 El is not an XML element"
				assert isinstance(self.SIFName, str), "FT1659 Fault Tree's SIFName is not a string"
				assert self.OpMode in core_classes.OpModes
				assert isinstance(self.Rev, str), "FT1653 Fault Tree's Rev is not a string"
				assert isinstance(self.RiskReceptorGroupOnDisplay, list), "FT1664 Fault Tree's RiskReceptorGroupOnDisplay is not a list"
				for RR in self.RiskReceptorGroupOnDisplay:
					assert isinstance(RR, core_classes.RiskReceptorItem), "FT1667 Invalid item '%s' in RiskReceptorItem" % str(RR)
				assert len(self.RiskReceptorGroupOnDisplay) > 0, "FT1669 Fault Tree has empty list of RiskReceptorGroupOnDisplay"
				assert isinstance(list(self.Severity.values())[0], core_classes.CategoryNameItem)
				assert isinstance(self.TolFreq, core_classes.NumValueItem),\
					"FT1668 Fault Tree's TolFreq is not a NumValueItem"
				assert isinstance(self.TargetRiskRedMeasure, str), "FT1671 Fault Tree's TargetRiskRedMeasure is not a string"
				assert self.TargetRiskRedMeasure in FTObjectInCore.RiskRedMeasures,\
					"FT1672 Fault Tree's TargetRiskRedMeasure value '%s' is invalid" % str(self.TargetRiskRedMeasure)
				assert isinstance(self.BackgColour, str), "FT1673 Fault Tree's BackgColour is not a string"
				assert isinstance(self.TextColour, str), "FT1674 Fault Tree's TextColour is not a string"
			# determine which risk receptor to use for calculation
			RRForCalc = self.RiskReceptorGroupOnDisplay[0]
			# First, make an element to contain all the data
			HeaderEl = ElementTree.SubElement(El, info.FTHeaderTag)
			# make sub-elements for all the required attribs
			# elements where the text is the HumanName of the FT attribute
			DataInfo = [ ('OpMode', self.OpMode), ('Severity', self.Severity[RRForCalc]) ]
			for Tag, Attrib in DataInfo:
				El = ElementTree.SubElement(HeaderEl, Tag)
				El.text = Attrib.HumanName
			# elements where the FT attribute is a ValueInfoItem instance
			DataInfo = [ ('UEL', self.Outcome), ('TargetRiskRed', self.TargetRiskRed(RRForCalc)) ]
			for Tag, Attrib in DataInfo:
				El = ElementTree.SubElement(HeaderEl, Tag)
				El.text = str(Attrib.Value)
			# elements where the FT attribute is a NumValueItem (or subclass) instance
			DataInfo = [ ('TolFreq', self.TolFreq) ]
			for Tag, Attrib in DataInfo:
				AttribEl = ElementTree.SubElement(HeaderEl, Tag)
#				AttribEl.text = str(Attrib.GetMyValue(RR=RRForCalc))
#				AttribEl.text = Attrib.GetDisplayValue(RR=RRForCalc, InvalidResult='- - -')
				# get correctly formatted string representation of numerical value
				AttribEl.text = display_utilities.StringFromNum(InputNumber=Attrib, RR=RRForCalc)
				V = display_utilities.StringFromNum(InputNumber=Attrib, RR=RRForCalc)
				# add unit, unit options, ValueKind options and Constant options
				UnitEl = ElementTree.SubElement(AttribEl, info.UnitTag)
				UnitEl.text = str(Attrib.GetMyUnit().XMLName)
				PopulateValueOptionField(CurrentOption=Attrib.GetMyUnit(), AcceptableOptions=Attrib.AcceptableUnits,
					EventEl=AttribEl, OptionXMLTagName=info.UnitOptionTag, OfferConvertOptions=True)
				PopulateValueOptionField(CurrentOption=type(Attrib), AcceptableOptions=Attrib.ValueKindOptions,
					EventEl=AttribEl, OptionXMLTagName=info.ValueKindOptionTag, OfferConvertOptions=False)
#				for ThisValueKindOption in Attrib.ValueKindOptions:
#					ValueKindOptionEl = ElementTree.SubElement(AttribEl, info.ValueKindOptionTag)
#					ValueKindOptionEl.text = str(ThisValueKindOption.XMLName)
				for ThisConstantOption in self.Proj.Constants:
					ConstantOptionEl = ElementTree.SubElement(AttribEl, info.ConstantOptionTag)
					ConstantOptionEl.text = str(ThisConstantOption.HumanName)
					IDEl = ElementTree.SubElement(ConstantOptionEl, info.IDTag)
					IDEl.text = ThisConstantOption.ID
				for ThisMatrixOption in self.Proj.TolRiskModels: # %%% working here
					MatrixOptionEl = ElementTree.SubElement(AttribEl, info.MatrixOptionTag)
					MatrixOptionEl.text = str(ThisMatrixOption.HumanName)
					MatrixOptionIDEl = ElementTree.SubElement(MatrixOptionEl, info.IDTag)
					MatrixOptionIDEl.text = ThisMatrixOption.ID

			# elements where the text is the same as the FT attribute
			# Note, SILTargetValue must be interrogated AFTER TargetRiskRed() call, above
			for Tag in self.TextComponentNames:
				El = ElementTree.SubElement(HeaderEl, Tag)
				El.text = getattr(self, Tag)
			# elements where the text is the HumanName of the Unit of the FT attribute
#			DataInfo = [ ('TolFreqUnit', self.TolFreq), ('OutcomeUnit', self.Outcome) ]
			DataInfo = [ ('OutcomeUnit', self.Outcome) ]
			for Tag, Attrib in DataInfo:
				El = ElementTree.SubElement(HeaderEl, Tag)
				El.text = str(Attrib.Unit.HumanName)
			return HeaderEl

		def PopulateFTEventData(FT, El, FTEvent, EventListForNumbering):
			# put FT event data into XML element El
			# EventListForNumbering: list containing all FTEvents to consider when numbering this one
			# FT: FTObjectInCore containing FT event
			if __debug__ == 1: # do type checks
				assert isinstance(FT, FTObjectInCore)
				TypeChecks = [ (El, ElementTree.Element), (FTEvent.ID, str), (FTEvent.IsIPL, bool),
					(FTEvent.Numbering, core_classes.NumberingItem), (FTEvent.EventDescription, str),
					(FTEvent.CanEditValue, bool), (FTEvent.ShowActionItems, bool),
					(FTEvent.BackgColour, str), (FTEvent.EventDescriptionComments, list),
					(FTEvent.ValueComments, list), (FTEvent.ShowDescriptionComments, bool),
					(FTEvent.ShowValueComments, bool), (FTEvent.ActionItems, list),
					(FTEvent.ConnectTo, list), (FTEvent.CollapseGroups, list)]
#					(FTEvent.ConnectTo, list), (FTEvent.LinkedTo, list), (FTEvent.CollapseGroups, list)]
#				IterableChecks = [(FTEvent.LinkedTo, core_classes.LinkItem), (FTEvent.LinkedFrom, core_classes.LinkItem),
				IterableChecks = [(FTEvent.LinkedFrom, core_classes.LinkItem),
					(FTEvent.CollapseGroups, FTCollapseGroup), (FTEvent.EventDescriptionComments, core_classes.AssociatedTextItem),
					(FTEvent.ValueComments, core_classes.AssociatedTextItem),
					(FTEvent.ActionItems, core_classes.AssociatedTextItem)]
				MemberChecks = [ (FTEvent.EventType, FTEventInCore.EventTypes) ]
				# didn't do IterableCheck on ConnectTo, as several types are possible
				core_classes.DoTypeChecks(TypeChecks, IterableChecks, MemberChecks)
			# make FTEvent element to contain all the other elements
			EventEl = ElementTree.SubElement(El, info.FTEventTag)
			# get value and unit for display
			RRToDisplay = FT.RiskReceptorGroupOnDisplay[0]
			ValueStatus = FTEvent.Value.Status(RR=RRToDisplay)
			if ValueStatus == core_classes.NumProblemValue_NoProblem:
				# get the likelihood value of the FTEvent, and format for display
				EventValue = utilities.RoundValueForDisplay(InputValue=FTEvent.Value.GetMyValue(RR=RRToDisplay),
					SigFigs=info.EventValueSigFigs)
				# run value checks
				ValueStatus = FTEvent.CheckValue(NumValueInstance=FTEvent.Value)
				# decide whether a problem indicator is needed
				if (ValueStatus == core_classes.NumProblemValue_NoProblem): ProblemLevel = None
				else: ProblemLevel = 'Level10'
			else: # can't display value; make tag for problem indicator
				if ValueStatus == core_classes.NumProblemValue_UndefNumValue: EventValue = _('not set')
				else: EventValue = '- - -' # signifying value unobtainable
				ProblemLevel = 'Level10'
			if ProblemLevel: # do we need to display value problem indicator?
				ProblemTag = ElementTree.SubElement(EventEl, info.ProblemIndicatorTag)
				ProblemTag.text = ValueStatus.HumanHelp
				ProblemTag.set(info.ProblemLevelAttribName, ProblemLevel) # indicating the seriousness of the problem
			EventUnit = FTEvent.Value.GetMyUnit()
			ProblemValue = FTEvent.Value.Status(RR=FT.RiskReceptorGroupOnDisplay[0])
			ProblemObj = None # TODO work out how to fetch this from the NumValueItem instance
			# make sub-elements for all the required attribs:
			# elements where the text is the same as the FTEvent attribute in str form
			FTEvent.TextComponentHash = {info.IDTag: FTEvent.ID, 'IsIPL': FTEvent.IsIPL, 'EventType': FTEvent.EventType,
				info.NumberingTag: FTEvent.Numbering.HumanValue(FTEvent, EventListForNumbering)[0],
				'EventDescription': FTEvent.EventDescription,
				'CanEditValue': FTEvent.CanEditValue, 'ValueProblemID': getattr(ProblemValue, 'ID', ''),
				'Value': EventValue, info.ShowActionItemTag: FTEvent.ShowActionItems, 'BackgColour': FTEvent.BackgColour,
				info.ShowDescriptionCommentTag: FTEvent.ShowDescriptionComments,
				info.ShowValueCommentTag: FTEvent.ShowValueComments,
				'Unit': EventUnit.HumanName, 'ValueProblemObjectID': getattr(ProblemObj, 'ID', ''),
				'FTEventLinked': bool(FTEvent.LinkedFrom)}
#				'FTEventLinked': bool(FTEvent.LinkedTo) or bool(FTEvent.LinkedFrom)}
			for Tag, Attrib in FTEvent.TextComponentHash.items():
				El = ElementTree.SubElement(EventEl, Tag)
				El.text = str(Attrib)
			# elements for lists of AssociatedTextItems: comments and action items
			DataInfo = [ (info.DescriptionCommentTag, FTEvent.EventDescriptionComments, FTEvent.ShowDescriptionComments),
				(info.ValueCommentTag, FTEvent.ValueComments, FTEvent.ShowValueComments),
				(info.ActionItemTag, FTEvent.ActionItems, FTEvent.ShowActionItems)]
			for Tag, ListName, Show in DataInfo:
				if bool(ListName) and Show:
					for ThisItem in ListName:
						ItemEl = ElementTree.SubElement(EventEl, Tag)
						# comment content is XML tag text; numbering is in 'Numbering' attrib
						ItemEl.text = ThisItem.Content
						ItemEl.set(info.NumberingTag, ThisItem.Numbering.HumanValue(PHAItem=ThisItem, Host=ListName)[0])
						# TODO to change numbering scope (e.g. per FT rather than per event), change ListName in the above [YBO]
			# elements for lists of items with IDs
			for Tag, ListName in [ ('ConnectTo', FTEvent.ConnectTo), ('CollapseGroups', FTEvent.CollapseGroups) ]:
				for Item in ListName:
					El = ElementTree.SubElement(EventEl, Tag)
					El.text = Item.ID
			# add options for object type
			for (ThisObjTypeIndex, ThisObjType) in enumerate(FTEvent.AvailEventTypes):
				ObjTypeEl = ElementTree.SubElement(EventEl, info.EventTypeOptionTag)
				# set human name for type option to internal name of option
				ObjTypeEl.text = ThisObjType
				ObjTypeEl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisObjType == FTEvent.EventType))
				ObjTypeEl.set(info.SerialTag, str(ThisObjTypeIndex)) # add type option serial number
			# add options for value unit: first, plain units, then options to convert value to new units TODO use PopulateValueOptionField()
			CurrentUnit = FTEvent.Value.GetMyUnit()
			AcceptableUnits = FTEvent.AcceptableUnits() # keep this line when switching to PopulateValueOptionField()
			AcceptableValueKinds = FTEvent.AcceptableValueKinds() # keep this line when switching to PopulateValueOptionField()
			HowManyAcceptableUnits = len(AcceptableUnits)
			for (ThisUnitIndex, ThisUnit) in enumerate(AcceptableUnits):
				UnitEl = ElementTree.SubElement(EventEl, info.UnitOptionTag)
				UnitEl.text = ThisUnit.XMLName
				UnitEl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisUnit == CurrentUnit))
				UnitEl.set(info.SerialTag, str(ThisUnitIndex))  # add unit option serial number
			for (ThisUnitIndex, ThisUnit) in enumerate(AcceptableUnits):
				if ThisUnit != CurrentUnit: # don't offer option to convert to existing unit
					UnitEl = ElementTree.SubElement(EventEl, info.UnitOptionTag)
					UnitEl.text = ThisUnit.XMLName + info.ConvertValueMarker
					UnitEl.set(info.ApplicableAttribName, utilities.Bool2Str(False)) # each item in this list isn't current
					# add unit option serial number, noting that we already have options from the 1st list
					UnitEl.set(info.SerialTag, str(HowManyAcceptableUnits + ThisUnitIndex))
			# add options for value kind - unless this is SIF failure event, then just send 'auto' value kind
#			if FTEvent.EventType == 'SIFFailureEvent': NumValueClassesToShow = [core_classes.AutoNumValueItem]
#			else: NumValueClassesToShow = [c for c in core_classes.NumValueClasses if c.UserSelectable]
			if FTEvent.EventType in FTEvent.EventTypesWithUserValues:
				NumValueClassesToShow = FTEvent.UserSuppliedNumberKinds
			elif FTEvent.EventType in FTEvent.EventTypesWithDerivedValues:
				NumValueClassesToShow = FTEvent.DerivedNumberKinds
			elif FTEvent.EventType in FTEvent.EventTypesUserOrDerivedValues:
				NumValueClassesToShow = FTEvent.UserSuppliedNumberKinds + FTEvent.DerivedNumberKinds
			for (ThisValueKindIndex, ThisValueKind) in enumerate(NumValueClassesToShow):
				ValueKindEl = ElementTree.SubElement(EventEl, info.NumberKindTag)
				# set human name for number kind option to internal name of option
				ValueKindEl.text = ThisValueKind.XMLName
				ValueKindEl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisValueKind == type(FTEvent.Value)))
				ValueKindEl.set(info.SerialTag, str(ThisValueKindIndex)) # add number kind option serial number
			return EventEl

		def PopulateFTConnectorData(El, FTConnector):
			# put FT connector-in/out data into XML element El
			if __debug__ == 1: # do type checks
				TypeChecks = [(El, ElementTree.Element), (FTConnector, FTConnectorItemInCore),
							  (FTConnector.ID, str), (FTConnector.FT, FTObjectInCore), (FTConnector.Out, bool),
							  (FTConnector.ConnectorDescription, str), (FTConnector.BackgColour, str),
							  (FTConnector.ConnectTo, list), (FTConnector.CollapseGroups, list),
							  (FTConnector.Numbering, core_classes.NumberingItem), (FTConnector.Style, str)]
				IterableChecks = [(FTConnector.CollapseGroups, FTCollapseGroup)]
				# didn't do iterableCheck on ConnectTo, as several types are possible
				core_classes.DoTypeChecks(TypeChecks, IterableChecks)
			# make FTConnector element to contain all the other elements
			ConnEl = ElementTree.SubElement(El, 'FTConnector')
			EventValue, EventUnit, ProblemValue, ProblemObj = FTConnector.Value # get the current value of the FTConnector
			# make sub-elements for all the required attribs:
			# elements where the text is the same as the FTConnector attribute
			DataInfo = [ (info.IDTag, FTConnector.ID), ('Connectivity', {True: 'Out', False: 'In'}[FTConnector.Out]),
				('Description', FTConnector.ConnectorDescription), ('BackgColour', FTConnector.BackgColour),
				('Numbering', FTConnector.Numbering.HumanValue(FTGate)[0]), ('Style', FTConnector.Style),
				('ShowDescriptionComments', str(FTConnector.ShowDescriptionComments)), ('Value', str(EventValue)),
				('Unit', EventUnit.HumanName), ('ValueProblemID', getattr(ProblemValue, 'ID', '')),
				('ValueProblemObjectID', getattr(ProblemObj, 'ID', '')) ]
			for Tag, Attrib in DataInfo:
				El = ElementTree.SubElement(ConnEl, Tag)
				El.text = str(Attrib)
			# elements for lists of AssociatedTextItems
			DataInfo = [ ('DescriptionComments', FTConnector.ConnectorDescriptionComments) ]
			for Tag, ListName in DataInfo:
				for Item in ListName:
					El = ElementTree.SubElement(ConnEl, Tag)
					El.text = Item.Content # rich text
			# elements for lists of items with IDs
			for Tag, ListName in [('ConnectTo', FTConnector.ConnectTo), ('CollapseGroups', FTConnector.CollapseGroups)]:
				for Item in ListName:
					El = ElementTree.SubElement(ConnEl, Tag)
					El.text = Item.ID
			# elements with special handling: RelatedCX
			El = ElementTree.SubElement(ConnEl, 'RelatedConnector')
			if FTConnector.RelatedCX is None:
				El.Text = '-1'
			else:
				assert isinstance(FTConnector.RelatedCX, FTConnectorItemInCore)
				assert isinstance(FTConnector.RelatedCX.ID, str)
				El.Text = FTConnector.RelatedCX.ID
			return ConnEl

#		def PopulateValueOptionField(FTEvent, EventEl, OfferConvertOptions=True):
		def PopulateValueOptionField(CurrentOption, AcceptableOptions, EventEl, OptionXMLTagName, OfferConvertOptions=True):
			# put options for value attrib (e.g. unit, value kind) into element EventEl in FTEvent's XML representation
			# OptionXMLTagName (str): XML tag for option (e.g. info.UnitOptionTag)
			# If OfferConvertOptions is True, append options to convert value to new units (special for units)
#			assert CurrentOption in core_classes.AllSelectableUnits
			assert CurrentOption in AcceptableOptions
			assert isinstance(OfferConvertOptions, bool)
			HowManyAcceptableOptions = len(AcceptableOptions)
			for (ThisOptionIndex, ThisOption) in enumerate(AcceptableOptions):
				OptionEl = ElementTree.SubElement(EventEl, OptionXMLTagName)
				OptionEl.text = ThisOption.XMLName
				OptionEl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisOption == CurrentOption))
				OptionEl.set(info.SerialTag, str(ThisOptionIndex)) # add option serial number
			# add 'convert unit' options
			if OfferConvertOptions:
				for (ThisOptionIndex, ThisOption) in enumerate(AcceptableOptions):
					if ThisOption != CurrentOption: # don't offer option to convert to existing unit
						OptionEl = ElementTree.SubElement(EventEl, OptionXMLTagName)
						OptionEl.text = ThisOption.XMLName + info.ConvertValueMarker
						OptionEl.set(info.ApplicableAttribName, utilities.Bool2Str(False))
						# above line: False because each item in this list isn't the current unit
						# add unit option serial number, noting that we already have options from the 1st list
						OptionEl.set(info.SerialTag, str(HowManyAcceptableOptions + ThisOptionIndex))

		def PopulateFTGateData(El, FTGate):
			# put FT gate data into XML element El
			if __debug__ == 1: # do type checks
				TypeChecks = [ (El, ElementTree.Element), (FTGate.ID, str), (FTGate.Algorithm, str),
					(FTGate.Numbering, core_classes.NumberingItem), (FTGate.MadeBySystem, bool),
					(FTGate.GateDescription, str), (FTGate.ShowActionItems, bool),
					(FTGate.BackgColour, str), (FTGate.GateDescriptionComments, list), (FTGate.Style, str),
					(FTGate.ShowDescriptionComments, bool), (FTGate.ActionItems, list), (FTGate.LinkedFrom, list),
					(FTGate.ConnectTo, list), (FTGate.CollapseGroups, list) ]
#					(FTGate.ConnectTo, list), (FTGate.LinkedTo, list), (FTGate.CollapseGroups, list) ]
#				IterableChecks = [(FTGate.LinkedTo, core_classes.LinkItem), (FTGate.LinkedFrom, core_classes.LinkItem),
				IterableChecks = [(FTGate.LinkedFrom, core_classes.LinkItem),
					(FTGate.CollapseGroups, FTCollapseGroup), (FTGate.GateDescriptionComments, core_classes.AssociatedTextItem),
					(FTGate.ActionItems, core_classes.AssociatedTextItem)]
				MemberChecks = [ (FTGate.Algorithm, FTGateItemInCore.Algorithms) ]
				core_classes.DoTypeChecks(TypeChecks, IterableChecks, MemberChecks)
			# make FTGate element to contain all the other elements
			GateEl = ElementTree.SubElement(El, 'FTGate')
			# get value and unit for display
			RRToDisplay = self.RiskReceptorGroupOnDisplay[0]
			ValueStatus = FTGate.Value.Status(RR=RRToDisplay)
			if ValueStatus == core_classes.NumProblemValue_NoProblem:
				# get the output value of the FTGate, and format for display
				OutputValue = utilities.RoundValueForDisplay(InputValue=FTGate.Value.GetMyValue(RR=RRToDisplay),
					SigFigs=info.EventValueSigFigs)
				# decide whether a problem indicator is needed
				if (ValueStatus == core_classes.NumProblemValue_NoProblem): ProblemLevel = None
				else: ProblemLevel = 'Level10'
			else: # can't display value; make tag for problem indicator
				OutputValue = '- - -' # signifying value unobtainable
				ProblemLevel = 'Level10'
			if ProblemLevel: # do we need to display value problem indicator?
				ProblemTag = ElementTree.SubElement(GateEl, info.ProblemIndicatorTag)
				ProblemTag.text = ValueStatus.HumanHelp
				ProblemTag.set(info.ProblemLevelAttribName, ProblemLevel) # indicating the seriousness of the problem
			GateUnit = FTGate.Value.GetMyUnit()
			ProblemValue = FTGate.Value.Status(RR=self.RiskReceptorGroupOnDisplay[0])
			ProblemObj = None # TODO work out how to fetch this from the NumValueItem instance
			# make sub-elements for all the required attribs:
			# elements where the text is the same as the gate attribute
			DataInfo = [ (info.IDTag, FTGate.ID), ('Description', FTGate.GateDescription), ('Algorithm', FTGate.Algorithm),
				('MadeBySystem', FTGate.MadeBySystem), ('Style', FTGate.Style), ('Unit', GateUnit.HumanName),
				('Value', OutputValue), ('ShowActionItems', FTGate.ShowActionItems),  ('BackgColour', FTGate.BackgColour),
				(info.ShowDescriptionCommentTag, str(FTGate.ShowDescriptionComments)), ('Algorithm', FTGate.Algorithm),
				('ValueProblem', ProblemValue.InternalName),
				('ValueProblemID', getattr(ProblemValue, 'ID', '')),
				('ValueProblemObjectID', getattr(ProblemObj, 'ID', '')),
				('FTGateLinked', bool(FTGate.LinkedFrom)),
#				('FTGateLinked', bool(FTGate.LinkedTo) or bool(FTGate.LinkedFrom)),
				('Numbering', FTGate.Numbering.HumanValue(FTGate, FTGate.Column.FTElements)[0]) ]
			for Tag, Attrib in DataInfo:
				El = ElementTree.SubElement(GateEl, Tag)
				El.text = str(Attrib)
			# elements for lists of AssociatedTextItems
			DataInfo = [ ('DescriptionComments', FTGate.GateDescriptionComments), ('ActionItems', FTGate.ActionItems)]
			for Tag, ListName in DataInfo:
					for Item in ListName:
						El = ElementTree.SubElement(GateEl, Tag)
						El.text = Item.Content # rich text
			# elements for lists of items with IDs
			for Tag, ListName in [ ('ConnectTo', FTGate.ConnectTo), ('CollapseGroups', FTGate.CollapseGroups) ]:
				for Item in ListName:
					El = ElementTree.SubElement(GateEl, Tag)
					El.text = Item.ID
			# add options for gate type
			for (ThisGateTypeIndex, ThisGateType) in enumerate(FTGate.Algorithms):
				GateTypeEl = ElementTree.SubElement(GateEl, info.FTGateTypeOptionTag)
				# set human name for type option to internal name of option
				GateTypeEl.text = ThisGateType
				GateTypeEl.set(info.ApplicableAttribName, utilities.Bool2Str(ThisGateType == FTGate.Algorithm))
				GateTypeEl.set(info.SerialTag, str(ThisGateTypeIndex)) # add type option serial number
			# add options for gate unit
			PopulateValueOptionField(CurrentOption=FTGate.Value.GetMyUnit(), AcceptableOptions=FTGate.AcceptableUnits(),
				EventEl=GateEl, OptionXMLTagName=info.UnitOptionTag, OfferConvertOptions=False)
			return GateEl

		def PopulateColumnData(FT, El, Col):
			# put column data for Col (FTColumn instance) into XML element El
			# FT (FTObjectInCore): FT containing Col
			assert isinstance(FT, FTObjectInCore)
			ColumnEl = ElementTree.SubElement(El, info.FTColumnTag)
			for Obj in Col.FTElements: # work through all objects in Col
				if isinstance(Obj, FTEventInCore):
					assert isinstance(Obj.ID, str)
					assert isinstance(Obj.IsIPL, bool)
					assert Obj.EventType in FTEventInCore.EventTypes
					assert isinstance(Obj.Numbering, core_classes.NumberingItem)
					PopulateFTEventData(FT, ColumnEl, Obj, EventListForNumbering=Col.FTElements)
				elif isinstance(Obj, FTGateItemInCore):
					PopulateFTGateData(ColumnEl, Obj)
				elif isinstance(Obj, FTConnectorItemInCore):
					PopulateFTConnectorData(ColumnEl, Obj)
				else: raise TypeError("No routine provided to put object data in column XML")

		# GetFullRedrawData main procedure
		# First, make the root element
		RootElement = ElementTree.Element(ViewportClass.InternalName)
		# populate with overall FT-related data
		PopulateOverallData(RootElement)
		# populate with header data
		HeaderEl = PopulateHeaderData(RootElement)
		# populate with data for each column
		for Col in self.Columns:
			ColEl = PopulateColumnData(FT=self, El=RootElement, Col=Col)
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
		return RootElement

	def AddNewElement(self, Proj, ColNo=None, IndexInCol=None, ObjKindRequested=None):
		# insert a new non-IPL event of type ObjKindRequested (str; InternalName of an element type in FTObjectInCore for datacore)
		# into column with index ColNo (str) at index IndexInCol (str)
		# returns XML tree with information about the update
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(ColNo, str)
		assert isinstance(IndexInCol, str)
		assert isinstance(ObjKindRequested, str)
		ThisColIndex = int(ColNo); ThisIndexInCol = int(IndexInCol)
		assert 0 <= ThisColIndex <= len(self.Columns) # allows for ThisColIndex to be 1+no of columns
		if ThisColIndex < len(self.Columns): assert 0 <= ThisIndexInCol <= len(self.Columns[ThisColIndex].FTElements)
		# First, decide what kind of event to insert
		NewEventClass = {'FTEventInCore': FTEventInCore, 'FTGateInCore': FTGateItemInCore}[ObjKindRequested]
		# insert new column if needed
		if ThisColIndex == len(self.Columns): self.CreateColumn(NewColIndex=len(self.Columns))
		# insert new event
		NewEvent = NewEventClass(Proj=Proj, FT=self, Column=self.Columns[ThisColIndex], ModelGate=self.ModelGate)
		self.Columns[ThisColIndex].FTElements.insert(ThisIndexInCol, NewEvent)
		return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')

	def ConnectElements(self, FromEl, ToEl):
		# make a connection from FromEl to ToEl (instances of FTxxxInCore). Return Problem (str) reporting any problem
		assert isinstance(FromEl, (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
		assert isinstance(ToEl, (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
		# check they're not already connected
		if not (ToEl in FromEl.ConnectTo):
			# check the connection wouldn't lead to a dual path or circularity
			if self.HasPathBetween(FromEl, ToEl): Problem = _('connection would cause a dual pathway')
			elif self.HasPathBetween(ToEl, FromEl): Problem = _('connection would create a circular pathway')
			else:
				FromEl.ConnectTo.append(ToEl)
				Problem = ''
		return Problem
		# TODO undo, redo

	def DisconnectElements(self, FromEl, ToEl):
		# break a connection from FromEl to ToEl (instances of FTxxxInCore)
		assert isinstance(FromEl, (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
		assert isinstance(ToEl, (FTEventInCore, FTGateItemInCore, FTConnectorItemInCore))
		# check they're already connected
		if (ToEl in FromEl.ConnectTo):
			FromEl.ConnectTo.remove(ToEl)
		# TODO undo, redo

	def HasPathBetween(self, FromEl, ToEl): # return bool: True if FromEl and ToEl are connected through any number of
		# intermediate links
		LinkFound = (ToEl in FromEl.ConnectTo)
		if not LinkFound:
			# recursively check for link from any element linked to FromEl, to ToEl
			for ThisEl in FromEl.ConnectTo:
				LinkFound = self.HasPathBetween(ThisEl, ToEl)
				if LinkFound: break # stop searching as soon as a link is found
		return LinkFound
		# TODO confirm this will work with Connectors

	def CreateColumn(self, NewColIndex=0):
		# insert new FT column at NewColIndex
		assert isinstance(NewColIndex, int)
		assert 0 <= NewColIndex <= len(self.Columns)
		self.Columns.insert(NewColIndex, FTColumnInCore(FT=self, ColNo=NewColIndex))

	def ValidateValue(self, TargetComponent, ProposedValue, Unit):
		# check ProposedValue (int or float) in Unit (a UnitItem instance) is valid for TargetComponent (a
		# NumValueItem subclass instance containing the value of an FT element)
		# Assumes that if the component has either a MaxValue or a MinValue attrib, it also has a MaxMinUnit attrib
		# return ValueIsValid (bool)
		assert isinstance(ProposedValue, (int, float))
		assert isinstance(TargetComponent, core_classes.NumValueItem)
		assert isinstance(Unit, core_classes.UnitItem)
#		# first, find component containing the value
#		TargetComponent = getattr(ComponentHost, ComponentName)
		ValueIsValid = True
		# check Unit is compatible with component's MaxMinUnit, if any
		if hasattr(TargetComponent, 'MaxMinUnit'):
			ValueIsValid = (TargetComponent.MaxMinUnit.QtyKind == Unit.QtyKind)
			# convert the proposed value to MaxMinUnit for comparison
			ConvertedProposedValue = ProposedValue * Unit.Conversion[TargetComponent.MaxMinUnit]
		if ValueIsValid:
			# check max value, converting to match Unit with MaxMinUnit
			if hasattr(TargetComponent, 'MaxValue'):
				ValueIsValid = (ConvertedProposedValue <= TargetComponent.MaxValue)
		if ValueIsValid:
			# check min value, converting to match Unit with MaxMinUnit
			if hasattr(TargetComponent, 'MinValue'):
				ValueIsValid = (ConvertedProposedValue >= TargetComponent.MinValue)
		return ValueIsValid

	def ChangeText(self, Proj, ElementID, TextComponentName, NewValue, Viewport):
		# change content of text component in ElementID (int as str, or 'Header') identified by
		# InternalName=TextComponentName (str) to NewValue (str)
		# Viewport is the Viewport object that sent the change text request
		# Returns XML tree with information about the update
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(ElementID, str)
		assert isinstance(TextComponentName, str)
		assert isinstance(NewValue, str)
		assert isinstance(Viewport, FTForDisplay)
		ChangeAccepted = True
		# find relevant element containing the component
		if ElementID == 'Header':
			ComponentToUpdate = TextComponentName
			ComponentHost = self
		else:
			HostElement = [El for c in self.Columns for El in c.FTElements if El.ID == ElementID][0]
			ComponentToUpdate = TextComponentName
			ComponentHost = HostElement
		# update component's text
		if ComponentToUpdate in ['EventValue', 'TolFreq', 'Value']: # updating Value attrib; try to extract number from user's input
			ValueReceived = utilities.str2real(NewValue, 'junk')
			if ValueReceived != 'junk': # we got a recognisable number; update value in all applicable risk receptors
				ChangeAccepted = self.DoChangeTextInValueField(Proj, ComponentToUpdate=ComponentToUpdate, ComponentHost=ComponentHost,
					TargetValue=ValueReceived, ViewportID=Viewport.ID,
					ViewportClass=type(Viewport), Zoom=Viewport.Zoom, PanX=Viewport.PanX, PanY=Viewport.PanY,
					HostElementID=ElementID, Redoing=False, RRGroup=self.RiskReceptorGroupOnDisplay)
		else: # updating another field
			self.DoChangeTextInTextField(Proj=Proj, ComponentToUpdate=ComponentToUpdate, ComponentHost=ComponentHost,
				TargetValue=NewValue, ViewportID=Viewport.ID, ViewportClass=type(Viewport), Zoom=Viewport.Zoom,
				PanX=Viewport.PanX, PanY=Viewport.PanY, HostElementID=ElementID, Redoing=False)
#			OldValue = getattr(ComponentHost, ComponentToUpdate) # get old value for saving in Undo record
#			setattr(ComponentHost, ComponentToUpdate, NewValue) # write new value to component
#			# store undo record
#			undo.AddToUndoList(Proj, Redoing=False, UndoObj=undo.UndoItem(UndoHandler=self.ChangeTextInTextField_Undo,
#				RedoHandler=self.ChangeTextInTextField_Redo, Chain='NoChain', ComponentHost=ComponentHost, ViewportID=Viewport.ID,
#				ViewportClass=type(Viewport),
#				ElementID=ElementID, ComponentName=ComponentToUpdate, OldValue=OldValue, NewValue=NewValue,
#				HumanText=_('change %s' % self.ComponentEnglishNames[TextComponentName]),
#				Zoom=Viewport.Zoom, PanX=Viewport.PanX, PanY=Viewport.PanY))
		# prepare appropriate XML message to return
		if ChangeAccepted:
			RootName = 'OK'; RootText = 'OK'
		else:
			RootName = 'OK'; RootText = info.ValueOutOfRangeMsg
		return vizop_misc.MakeXMLMessage(RootName=RootName, RootText=RootText)

	def DoChangeTextInTextField(self, Proj, ComponentToUpdate, ComponentHost, TargetValue, ViewportID,
			ViewportClass, Zoom, PanX, PanY, HostElementID, Redoing):
		# execute change of text in a text (not number) field
		# Redoing (bool): whether this is a redo action
		assert isinstance(Redoing, bool)
		OldValue = getattr(ComponentHost, ComponentToUpdate) # get old value for saving in Undo record
		setattr(ComponentHost, ComponentToUpdate, TargetValue) # write new value to component
		# store undo record
		undo.AddToUndoList(Proj, Redoing=Redoing, UndoObj=undo.UndoItem(UndoHandler=self.ChangeTextInTextField_Undo,
			  RedoHandler=self.ChangeTextInTextField_Redo,
			  Chain='NoChain', ComponentHost=ComponentHost,
			  ViewportID=ViewportID,
			  ViewportClass=ViewportClass,
			  ElementID=HostElementID,
			  ComponentName=ComponentToUpdate,
			  OldValue=OldValue, NewValue=TargetValue,
			  HumanText=_('change %s' % self.ComponentEnglishNames[ComponentToUpdate]),
			  Zoom=Zoom, PanX=PanX, PanY=PanY))

	def DoChangeTextInValueField(self, Proj, ComponentToUpdate, ComponentHost, TargetValue, ViewportID,
			ViewportClass, Zoom, PanX, PanY, HostElementID, Redoing, RRGroup):
		# execute change of text in a number field. New number value is in TargetValue (float)
		# Redoing (bool): whether this is a redo action
		# RRGroup (list): RR's currently displayed
		assert isinstance(Redoing, bool)
		assert isinstance(TargetValue, float)
		# find component to update (a NumValueItem subclass instance)
		TargetComponent = getattr(ComponentHost, ComponentToUpdate)
		# check new value is acceptable
		TargetValueIsValid = self.ValidateValue(TargetComponent, ProposedValue=TargetValue,
			Unit=TargetComponent.GetMyUnit())
		if TargetValueIsValid:
			# get old value for saving in Undo record
			OldValue = TargetComponent.GetMyValue(RR=RRGroup[0])
			# write new value to component
			for ThisRR in RRGroup:
				TargetComponent.SetMyValue(NewValue=TargetValue, RR=ThisRR)
			# store undo record
			undo.AddToUndoList(Proj, Redoing=Redoing, UndoObj=undo.UndoItem(UndoHandler=self.ChangeTextInValueField_Undo,
				  RedoHandler=self.ChangeTextInValueField_Redo,
				  Chain='NoChain', ComponentHost=ComponentHost, RR=RRGroup,
				  ViewportID=ViewportID,
				  ViewportClass=ViewportClass,
				  ElementID=HostElementID,
				  ComponentName=ComponentToUpdate,
				  OldValue=OldValue, NewValue=TargetValue,
				  HumanText=_('change %s' % ComponentHost.ComponentEnglishNames[ComponentToUpdate]),
				  Zoom=Zoom, PanX=PanX, PanY=PanY))
		return TargetValueIsValid

	def FetchDisplayAttribsFromUndoRecord(self, UndoRecord):
		# extract data about zoom, pan, highlight etc. from UndoRecord, build it into an XML tag FTDisplayAttribTag
		# and return the tag
		DisplaySpecificData = ElementTree.Element(info.FTDisplayAttribTag)
		for (UndoRecordAttribName, TagName) in [ ('ElementID', info.FTElementContainingComponentToHighlight),
			  ('ComponentName', info.FTComponentToHighlight),
			  ('Zoom', info.ZoomTag), ('PanX', info.PanXTag), ('PanY', info.PanYTag)]:
			if hasattr(UndoRecord, UndoRecordAttribName):
				ThisAttribTag = ElementTree.SubElement(DisplaySpecificData, TagName)
				ThisAttribTag.text = str(getattr(UndoRecord, UndoRecordAttribName))
		return DisplaySpecificData

	def ChangeTextInTextField_Undo(self, Proj, UndoRecord, **Args): # handle undo for ChangeTextInTextField
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(UndoRecord, undo.UndoItem)
		# find out which datacore socket to send messages on
		SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
		# undo the change to the text value
		setattr(UndoRecord.ComponentHost, UndoRecord.ComponentName, UndoRecord.OldValue)
		# request Control Frame to switch to the Viewport that was visible when the original edit was made
		self.RedrawAfterUndoOrRedo(UndoRecord, SocketFromDatacore)
		#		# instruct Control Frame to switch the requesting control frame to the Viewport that was visible when the original
		#		# text change was made, with the original zoom and pan restored (so that the text field is on screen)
		#		# and the changed component highlighted (so that the undo is visible to the user)
		#		# prepare data about zoom, pan, highlight etc.
		#		DisplayAttribTag = self.FetchDisplayAttribsFromUndoRecord(UndoRecord)
		#		RedrawDataXML = self.GetFullRedrawData(ViewportClass=UndoRecord.ViewportClass,
		#			ExtraXMLTagsAsTags=DisplayAttribTag)
		#		MsgToControlFrame = ElementTree.Element(info.NO_ShowViewport)
		#		# add a ViewportID tag to the message, so that Control Frame knows which Viewport to redraw
		#		ViewportTag = ElementTree.Element(info.ViewportTag)
		#		ViewportTag.text = UndoRecord.ViewportID
		#		MsgToControlFrame.append(ViewportTag)
		#		MsgToControlFrame.append(RedrawDataXML)
		#		vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket, Command=info.NO_ShowViewport, XMLRoot=MsgToControlFrame)
		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.FTTag,
			Elements={info.IDTag: self.ID, info.ComponentHostIDTag: UndoRecord.ComponentHost.ID}))
		# TODO add data for the changed component to the Save On Fly data
		return {'Success': True}

	def ChangeTextInValueField_Undo(self, Proj, UndoRecord, **Args): # handle undo for ChangeTextInValueField
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(UndoRecord, undo.UndoItem)
		# find out which datacore socket to send messages on
		SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
		# undo the change to the value in all applicable RR's
		for ThisRR in UndoRecord.RR:
			getattr(UndoRecord.ComponentHost, UndoRecord.ComponentName).SetMyValue(NewValue=UndoRecord.OldValue, RR=ThisRR)
#			getattr(UndoRecord.ComponentHost, UndoRecord.ComponentToUpdate).SetMyValue(NewValue=UndoRecord.OldValue, RR=ThisRR)
		# request Control Frame to switch to the Viewport that was visible when the original edit was made
		self.RedrawAfterUndoOrRedo(UndoRecord, SocketFromDatacore)
		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.FTTag,
			Elements={info.IDTag: self.ID, info.ComponentHostIDTag: UndoRecord.ComponentHost.ID}))
			# TODO add data for the changed component to the Save On Fly data, including RR's
		return {'Success': True}

	def ChangeTextInTextField_Redo(self, Proj, RedoRecord, **Args):
		self.DoChangeTextInTextField(Proj=Proj, ComponentToUpdate=RedoRecord.ComponentName,
			ComponentHost=RedoRecord.ComponentHost,
			TargetValue=RedoRecord.NewValue, ViewportID=RedoRecord.ViewportID,
			ViewportClass=RedoRecord.ViewportClass, Zoom=RedoRecord.Zoom, PanX=RedoRecord.PanX, PanY=RedoRecord.PanY,
			HostElementID=RedoRecord.ElementID, Redoing=True)
		self.RedrawAfterUndoOrRedo(RedoRecord, SocketFromDatacore=vizop_misc.SocketWithName(
			TargetName=Args['SocketFromDatacoreName']))
		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.FTTag,
			Elements={info.IDTag: self.ID, info.ComponentHostIDTag: RedoRecord.ComponentHost.ID}))
			# TODO add data for the changed component to the Save On Fly data
		return {'Success': True}

	def ChangeTextInValueField_Redo(self, Proj, RedoRecord, **Args):
		self.DoChangeTextInValueField(Proj=Proj, ComponentToUpdate=RedoRecord.ComponentName,
			ComponentHost=RedoRecord.ComponentHost,
			TargetValue=RedoRecord.NewValue, ViewportID=RedoRecord.ViewportID,
			ViewportClass=RedoRecord.ViewportClass, Zoom=RedoRecord.Zoom, PanX=RedoRecord.PanX, PanY=RedoRecord.PanY,
			HostElementID=RedoRecord.ElementID, Redoing=True, RRGroup=RedoRecord.RR)
		self.RedrawAfterUndoOrRedo(RedoRecord, SocketFromDatacore=vizop_misc.SocketWithName(
			TargetName=Args['SocketFromDatacoreName']))
		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.FTTag,
			Elements={info.IDTag: self.ID, info.ComponentHostIDTag: RedoRecord.ComponentHost.ID}))
			# TODO add data for the changed component to the Save On Fly data, including RR's
		return {'Success': True}

	def RedrawAfterUndoOrRedo(self, UndoRecord, SocketFromDatacore):
		# instruct Control Frame to switch the requesting control frame to the Viewport that was visible when the original
		# text change was made, with the original zoom and pan restored (so that the text field is on screen)
		# and the changed component highlighted (so that the undo is visible to the user)
		# SocketFromDatacore (socket object): socket to send redraw message from datacore to Control Frame
		# prepare data about zoom, pan, highlight etc.
		DisplayAttribTag = self.FetchDisplayAttribsFromUndoRecord(UndoRecord)
		RedrawDataXML = self.GetFullRedrawData(ViewportClass=UndoRecord.ViewportClass,
			ExtraXMLTagsAsTags=DisplayAttribTag)
		MsgToControlFrame = ElementTree.Element(info.NO_ShowViewport)
		# add a ViewportID tag to the message, so that Control Frame knows which Viewport to redraw
		ViewportTag = ElementTree.Element(info.ViewportTag)
		ViewportTag.text = UndoRecord.ViewportID
		MsgToControlFrame.append(ViewportTag)
		MsgToControlFrame.append(RedrawDataXML)
		vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket, Command=info.NO_ShowViewport, XMLRoot=MsgToControlFrame)

	def ChangeChoice(self, Proj, ElementID, TextComponentName, NewValue, **Args):
		# change content of choice component in ElementID (int as str, or 'Header')
		# identified by InternalName=TextComponentName (str)
		# to the value whose XMLName attrib is NewValue (str)
		# Args contains all tags:texts supplied in the change request
		# returns XML tree with information about the update
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(ElementID, str)
		assert isinstance(TextComponentName, str)
		assert isinstance(NewValue, str)
		ValueAcceptable = True # if a value would be updated as a result of unit change, whether the unit change
			# would lead to an acceptable value
		# find relevant element containing the component
		if ElementID == 'Header':
			ComponentToUpdate = TextComponentName
			ComponentHost = self
		else:
			HostElement = [El for c in self.Columns for El in c.FTElements if El.ID == ElementID][0]
			ComponentToUpdate = TextComponentName
			ComponentHost = HostElement
		print('FT3307 in ChangeChoice: ComponentToUpdate: ', ComponentToUpdate, type(ComponentToUpdate))
		# update component's value (TODO add undo)
		if ComponentToUpdate == 'Severity': # update severity in all currently displayed risk receptors
			NewSeverityObj = [s for s in self.MyTolRiskModel.TolFreqTable.Keys[
				self.MyTolRiskModel.TolFreqTable.SeverityDimensionIndex] if s.XMLName == NewValue][0]
			for ThisRR in self.RiskReceptorGroupOnDisplay: # update severity and tol freq for applicable risk receptors
				self.Severity[ThisRR] = NewSeverityObj
			self.SetTolFreq() # update tolerable frequency
			self.RefreshRiskReceptorGrouping(GroupingOption=self.RRGroupingOption) # update RR grouping
		elif ComponentToUpdate == 'RR':  # update which risk receptor group is applicable
			self.RiskReceptorGroupOnDisplay = self.RiskReceptorGroups[int(NewValue)]
		elif ComponentToUpdate == 'RRLabel': # update grouping of risk receptors
			self.RRGroupingOption = self.RRGroupingOptions[int(NewValue)]
			self.RefreshRiskReceptorGrouping(GroupingOption=self.RRGroupingOption)
		elif ComponentToUpdate == 'OpMode':  # update SIF operating mode
			self.OpMode = [v for v in core_classes.OpModes if v.XMLName == NewValue][0]
			# update event type and available event types for existing events
			for ThisEvent in WalkOverAllFTObjs(self):
				if isinstance(ThisEvent, FTEventInCore):
					ThisEvent.AvailEventTypes, ThisEvent.DefaultEventType = ThisEvent.SetAvailableEventTypes()
					if ThisEvent.EventType not in ThisEvent.AvailEventTypes:
						ThisEvent.ChangeEventType(ChangingOpMode=True)
		elif ComponentToUpdate == 'EventType': # update FTEvent type
			# find the FTEvent to update
			ThisFTEvent = [e for e in WalkOverAllFTObjs(self) if e.ID == ElementID][0]
			ThisFTEvent.ChangeEventType(NewEventType=NewValue) # update the event type
		elif ComponentToUpdate in ('EventValueUnit', 'GateValueUnit'):
			# update value unit of FTEvent or FTGate
			# find the FTEvent/FTGate to update
			ThisFTEvent = [e for e in WalkOverAllFTObjs(self) if e.ID == ElementID][0]
			UnitChanged, NewUnit, ValueAcceptable = self.ChangeUnit(FTElement=ThisFTEvent, NewUnitXMLName=NewValue, ValueAttribName='Value')
			# if this is an FTGate, set its "last selected unit" attribute
			if UnitChanged and (ComponentToUpdate == 'GateValueUnit'): ThisFTEvent.SetLastSelectedUnit(NewUnit)
		elif ComponentToUpdate == 'TolFreq':
			# update unit of TolFreq in FT header
			UnitChanged, NewUnit, ValueAcceptable = self.ChangeUnit(FTElement=self, NewUnitXMLName=NewValue, ValueAttribName='TolFreq')
		elif ComponentToUpdate == 'EventValueKind':  # update value kind
			# find the FTEvent to update
			ThisFTEvent = [e for e in WalkOverAllFTObjs(self) if e.ID == ElementID][0]
			ThisFTEvent.ChangeValueKind(NewValueKind=NewValue)  # update the value kind
		elif ComponentToUpdate == 'GateKind': # update FTGate kind
			# find the FTGate to update
			ThisFTGate = [e for e in WalkOverAllFTObjs(self) if e.ID == ElementID][0]
			ThisFTGate.ChangeGateKind(NewGateKind=NewValue) # update the gate kind
		else: # choice attribs other than those above; currently used only for header
			# find the corresponding value object (e.g. LowDemandMode) from the list of values in AttribValueHash
			NewValueObj = [v for v in self.AttribValueHash[ComponentToUpdate] if v.XMLName == NewValue][0]
			setattr(ComponentHost, ComponentToUpdate, NewValueObj)
		# prepare appropriate XML message to return
		if ValueAcceptable:
			RootName = 'OK'; RootText = 'OK'
		else:
			RootName = 'OK'; RootText = info.ValueOutOfRangeMsg
		return vizop_misc.MakeXMLMessage(RootName=RootName, RootText=RootText)

	def ChangeUnit(self, FTElement, NewUnitXMLName, ValueAttribName): # change unit of numerical value
		# FTElement: FT itself (for updating TolFreq value), or an FTEvent or FTGate instance (for updating value unit)
		# NewUnitXMLName: (str) XML name of unit to change to, optionally with ConvertValueMarker suffix
		# ValueAttribName: (str) Name of value attrib in FTElement to change; 'TolFreq' or 'Value'
		# return:
			# UnitChanged (bool): whether the unit was actually changed
			# NewUnit (UnitItem or None): the unit changed to, or None if unit wasn't changed
			# ValueAcceptable (bool): if the unit was suitable, but the value would be out of range, this is False; else True
		AcceptableUnits = FTElement.AcceptableUnits()
		ValueAttrib = getattr(FTElement, ValueAttribName) # find the applicable attrib in FTElement
		# check whether user requested to convert the value - signified by ConvertValueMarker suffix
		if NewUnitXMLName.endswith(info.ConvertValueMarker):
			Convert = True
			NewUnitXMLName = NewUnitXMLName[:-len(info.ConvertValueMarker)] # remove marker
		else:
			Convert = False
		if NewUnitXMLName in [u.XMLName for u in AcceptableUnits]: # it's recognised
			NewUnit = [u for u in AcceptableUnits if u.XMLName == NewUnitXMLName][0]
			# decide whether to convert the value
			if Convert:
				# check whether the value is in acceptable range in the old unit, for all risk receptors
				# (in principle, this check is redundant, as the value
				# in MaxMinUnit isn't changing, but we check anyway in case the value got messed up somehow)%%%
				ValueAcceptable = True
				for ThisRR in ValueAttrib.ValueFamily.keys():
					# check value for each RR, if the value is defined for that RR
					if ValueAttrib.GetMyStatus(RR=ThisRR) == core_classes.NumProblemValue_NoProblem:
						ValueAcceptable &= self.ValidateValue(ValueAttrib, ProposedValue=ValueAttrib.GetMyValue(RR=ThisRR),
							Unit=ValueAttrib.GetMyUnit())
				UnitChanged = ValueAcceptable
				if ValueAcceptable:
					ValueAttrib.ConvertToUnit(NewUnit) # convert value and change unit
			else:
				# change the unit without changing the value
				# check whether the value is in acceptable range in the new unit, for all risk receptors
				ValueAcceptable = True
				for ThisRR in ValueAttrib.ValueFamily.keys():
					# check value for each RR, if the value is defined for that RR
					if ValueAttrib.GetMyStatus(RR=ThisRR) == core_classes.NumProblemValue_NoProblem:
						ValueAcceptable &= self.ValidateValue(ValueAttrib, ProposedValue=ValueAttrib.GetMyValue(RR=ThisRR),
							Unit=NewUnit)
					print('FT3463 RR, ValueAcceptable:', ThisRR.HumanName, ValueAcceptable)
				UnitChanged = ValueAcceptable
				if ValueAcceptable:
					ValueAttrib.SetMyUnit(NewUnit)
		else: # new unit not valid for this element
			UnitChanged = False
			ValueAcceptable = True
			NewUnit = None
		return UnitChanged, NewUnit, ValueAcceptable

	def HandleIncomingRequest(self, MessageReceived=None, MessageAsXMLTree=None, **Args):
		# handle request received by FT model in datacore from a Viewport. Request can be to edit data (eg add new element)
		# Incoming message can be supplied as either an XML string or XML tree root element
		# MessageReceived (str or None): XML message containing request info
		# MessageAsXMLTree (XML element or None): root of XML tree
		# return Reply (Root object of XML tree)
		# First, convert MessageReceived to an XML tree for parsing
		assert isinstance(MessageReceived, bytes) or (MessageReceived is None)
		assert isinstance(Args, dict)
		if MessageReceived is None:
			assert isinstance(MessageAsXMLTree, ElementTree.Element)
			XMLRoot = MessageAsXMLTree
		else: XMLRoot = ElementTree.fromstring(MessageReceived)
		Proj = Args['Proj'] # get ProjectItem object to which the current FT belongs
		# get the command - it's the tag of the root element
		Command = XMLRoot.tag
#		print('FT3088 FT handling incoming request with command: ', Command)
		# get the Viewport from which the command was issued
		SourceViewport = utilities.ObjectWithID(Objects=Proj.ActiveViewports, TargetID=XMLRoot.findtext('Viewport'))
		# prepare default reply if command unknown
		Reply = vizop_misc.MakeXMLMessage(RootName='Fail', RootText='CommandNotRecognised')
		# process the command
		if Command == 'RQ_FT_NewElement':
			Reply = self.AddNewElement(Proj=Proj, ColNo=XMLRoot.findtext('ColNo'),
				IndexInCol=XMLRoot.findtext('IndexInCol'), ObjKindRequested=XMLRoot.findtext('ObjKindRequested'))
		elif Command == 'RQ_FT_ChangeText':
			Reply = self.ChangeText(Proj=Proj, ElementID=XMLRoot.findtext('Element'),
				TextComponentName=XMLRoot.findtext('TextComponent'),
				NewValue=XMLRoot.findtext('NewValue'), Viewport=SourceViewport)
#		elif Command == 'RQ_FT_ChangeUnit':
#			Reply = self.ChangeUnit(Proj=Proj, ElementID=XMLRoot.findtext('Element'),
#				NumericalComponentName=XMLRoot.findtext('NumericalComponent'),
#				NewValue=XMLRoot.findtext('NewUnit'), Viewport=SourceViewport)
		elif Command == 'RQ_FT_ChangeChoice':
			Reply = self.ChangeChoice(Proj=Proj, ElementID=XMLRoot.findtext('Element'),
				TextComponentName=XMLRoot.findtext('TextComponent'),
				**dict([(ThisTag.tag, ThisTag.text) for ThisTag in XMLRoot.iter()]))
			# The ** arg sends a dict of all tags and their texts, allowing ChangeChoice to pick up case-specific tags
			# Attrib NewValue is already in the ** arg, so no need to include it explicitly
		elif Command == 'RQ_FT_DescriptionCommentsVisible':  # make description comments in/visible in an FT element
			ThisElementID = XMLRoot.findtext('Element')
			ThisFTElement = [e for e in WalkOverAllFTObjs(self) if e.ID == ThisElementID][0]
			Reply = ThisFTElement.ShowCommentsOnOff(CommentKind='Description',
													Show=utilities.Bool2Str(XMLRoot.findtext('Visible')))
		elif Command == 'RQ_FT_ValueCommentsVisible': # make value comments in/visible in an FT element
			ThisElementID = XMLRoot.findtext('Element')
			ThisFTElement = [e for e in WalkOverAllFTObjs(self) if e.ID == ThisElementID][0]
			Reply = ThisFTElement.ShowCommentsOnOff(CommentKind='Value', Show=utilities.Bool2Str(XMLRoot.findtext('Visible')))
		elif Command == 'RQ_FT_ActionItemsVisible': # make action items in/visible in an FT element
			ThisElementID = XMLRoot.findtext('Element')
			ThisFTElement = [e for e in WalkOverAllFTObjs(self) if e.ID == ThisElementID][0]
			Reply = ThisFTElement.ShowActionItemsOnOff(Show=utilities.Bool2Str(XMLRoot.findtext('Visible')))
		elif Command == 'RQ_FT_ChangeConnection': # change connections between elements
			AllElementsInFT = [e for e in WalkOverAllFTObjs(self)] # get list of all elements in FT
			# do requested disconnections
			DisconnectIDList = utilities.UnpackPairsList(XMLRoot.findtext('Disconnect'))
			for (From, To) in DisconnectIDList:
				self.DisconnectElements(utilities.ObjectWithID(AllElementsInFT, From),
					utilities.ObjectWithID(AllElementsInFT, To))
			# do requested connections
			ConnectIDList = utilities.UnpackPairsList(XMLRoot.findtext('Connect'))
			ProblemFound = '' # descriptor of any problem encountered during connection
			for (From, To) in ConnectIDList:
				ThisProblem = self.ConnectElements(utilities.ObjectWithID(AllElementsInFT, From),
					utilities.ObjectWithID(AllElementsInFT, To))
				if ThisProblem and not ProblemFound: # keep problem message, if this is the first problem encountered
					ProblemFound = ThisProblem
			if ProblemFound:
				Reply = vizop_misc.MakeXMLMessage(RootName='Problem', RootText=ProblemFound)
			else: Reply = vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')
		elif Command == 'OK': # dummy for 'OK' responses - received only to clear the sockets
			Reply = vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')
		return Reply

class ChoiceItem(object): # represents an item in a group of items the user can select from, in an instance of
	# FTForDisplay (such as a risk receptor) or in instance of an FT element
	def __init__(self, XMLName='', HumanName='', Applicable=True):
		# XMLName (str): stores the 'Serial' tag value received from FTObjectInCore
		# Applicable (bool): whether the item applies to this FT instance
		assert isinstance(HumanName, str)
		assert isinstance(XMLName, str)
		assert len(XMLName) > 0
		assert isinstance(Applicable, bool)
		object.__init__(self)
		self.HumanName = HumanName
		self.XMLName = XMLName
		self.Applicable = Applicable

class FTForDisplay(display_utilities.ViewportBaseClass): # object containing all data needed to display FT
	# Each separate sub-object (header, cause etc) has attributes whose names are assumed to be same as in the data message from DataCore
	# NB this class has a forward definition earlier in this module.
	IsBaseClass = False # should be done for every subclass of ViewportBaseClass
	CanBeCreatedManually = True # whether the user should be able to create a Viewport of this class from scratch
	InternalName = 'FTTreeView' # unique per class, used in messaging
	HumanName = _('Fault Tree')
	PreferredKbdShortcut = 'F'
	NewPHAObjRequired = FTObjectInCore # which datacore PHA object class this Viewport spawns on creation.
		# Should be None if the model shouldn't create a PHA object
	# VizopTalks message when a new FT is created. NB don't set Priority here, as it is overridden in DoNewViewportCommand()
	NewViewportVizopTalksArgs = {'Title': 'New Fault Tree created',
		'MainText': 'Click on grey builder button to add first FT element'}
	MinColumnLength = 100 # in canvas coords
	MarginXInCU = 20 # margin between left edge of screen and left edge of first column, in canvas coords
	ImageSizeNoZoom = (20, 20) # initial no-zoom size of all button images
	# HumanNames for risk receptor grouping options. Keys must match those in FTObjectInCore (see assert, below)
	RRGroupingNameHash = {'Grouped': _('Show grouped'), 'Singly': _('Show separately')}
	assert set(RRGroupingNameHash.keys()) == set(FTObjectInCore.RRGroupingOptions)
	EventTypeNameHash = {'InitiatingEvent': _('Initiating event'), 'SIFFailureEvent': _('SIF failure event'),
		'IntermediateEvent': _('Intermediate event'), 'IPL': _('Independent protection layer'), 'TopEvent': _('Top event'),
		'ConnectorIn': _('Inward connector'), 'ConnectorOut': _('Outward connector'),
		'EnablingCondition': _('Enabling condition'), 'ConditionalModifier': _('Conditional modifier')}
	ConnectButtonBufferBorderX = ConnectButtonBufferBorderY = 5 # pixel allowance on each edge of connect button buffer

	class SeverityCatInFT(object): # represents a severity category in FTForDisplay instance
		# (so far, it's identical to ChoiceItem class)
		def __init__(self, XMLName='', HumanName='', Applicable=True):
			# XMLName (str): stores the 'Serial' tag value received from FTObjectInCore
			# Applicable (bool): whether the category applies to this FT instance
			assert isinstance(HumanName, str)
			assert isinstance(XMLName, str)
			assert len(XMLName) > 0
			assert isinstance(Applicable, bool)
			object.__init__(self)
			self.HumanName = HumanName
			self.XMLName = XMLName
			self.Applicable = Applicable

	def __init__(self, **Args): # FT object initiation. Args must include Proj and can include DisplDevice and ParentWindow
		display_utilities.ViewportBaseClass.__init__(self, **Args)
		self.Proj = Args['Proj']
		self.PHAObj = None # instance of FTObjectInCore shown in this Viewport (set in datacore.DoNewViewport())
		self.ID = None # assigned in display_utilities.CreateViewport()
		self.DisplDevice = Args.get('DisplDevice', None)
		self.RiskReceptorObjs = [] # ChoiceItem instances, in the order RR groups should be displayed
		self.RRGroupingOptionObjs = [] # ChoiceItem instances, options for whether RR's should be grouped
		self.SeverityCatObjs = [] # SeverityCatInFT instances, in the order severity categories should be displayed
		self.Header = FTHeader(FT=self)
		self.Columns = [] # this will be FTColumn objects
		self.InterColumnStripWidth = 100  # in canvas coords
		self.Zoom = 1.0 # ratio of canvas coords to screen coords (absolute ratio, not %)
		self.PanX = self.PanY = 0 # offset of drawing origin, in screen coords
		self.OffsetX = self.OffsetY = 0 # offset of Viewport in display panel, in screen coords;
			# referenced in utilities.CanvasCoordsViewport() but not currently used
		self.ElementIDContainingComponentToHighlight = None # ID of element containing a highlighted component;
			# if highlighted component is in FT header, value is same as self.ID
		self.ComponentNameToHighlight = '' # Name of component to highlight in specified element
		self.ParentWindow = Args.get('DisplDevice', None)
		self.BaseLayerBitmap = None # a wx.Bitmap for holding the base layer of the FT, apart from floating objects such as the zoom widget
		self.FloatingLayers = [] # a list of FloatLayer objects, for overlay onto the bitmap in self.Buffer, in arbitrary order
		# set up images used in FT
		self.ImagesNoZoom = {}
		self.ArtProvider = art.ArtProvider() # initialise art provider object
		for ThisImageName in self.ArtProvider.ImageCatalogue(OnlyWithPrefix=info.FTImagePrefix):
			# get the bitmap of each image, using image name as key including the prefix
			self.ImagesNoZoom[ThisImageName] = self.ArtProvider.get_image(name=ThisImageName,
				size=FTForDisplay.ImageSizeNoZoom, conserve_aspect_ratio=True)
		# initialize zoom widget
		self.MyZoomWidget = display_utilities.ZoomWidgetObj(Viewport=self, InitialZoom=self.Zoom)
		self.LastElLClicked = self.LastElMClicked = self.LastElRClicked = None
		self.CurrentEditElement = None # which text component is currently being edited with a TextCtrl
		self.PaintNeeded = True # whether to execute DoRedraw() in display device's OnPaint() handler (bool)
		self.OpMode = core_classes.DefaultOpMode
		self.EditingConnection = False # whether user is currently editing a connection between elements
		self.Panning = self.Zooming = False # whether user is currently changing display zoom or pan, for redraw efficiency
		self.ConnectButtons = [] # ButtonElement instances for connect buttons in inter-column strips

	def Wipe(self): # wipe all data in the FT and re-initialize
		self.Header.InitializeData()
		self.Columns = []
		self.ConnectButtons = []

	def YGapBetweenItemsInCU(self, ItemAbove, ItemBelow):
		# returns min Y-gap in canvas coords between 2 items in a column. This can vary depending on the types of items.
		# bigger gap between FTEvent (non-IPL) and IPL
		GapAroundIPLBlock = 30
		DefaultGap = 20
		if isinstance(ItemAbove, FTEvent) and isinstance(ItemBelow, FTEvent):
			if ItemAbove.IsIPL and not ItemBelow.IsIPL: return GapAroundIPLBlock
		return DefaultGap

	def AllClickableObjects(self, SelectedOnly=False, VisibleOnly=True):
		# return list of all elements in FT that should respond to mouse clicks
		# If SelectedOnly (bool), only return elements that are currently selected; similarly for VisibleOnly (bool)
		assert isinstance(SelectedOnly, bool)
		assert isinstance(VisibleOnly, bool)
		return self.Header.AllClickableObjects(SelectedOnly, VisibleOnly) +\
			[y for ThisEl in self.Columns for y in ThisEl.AllClickableObjects(SelectedOnly, VisibleOnly)] +\
			[self.MyZoomWidget] + self.ConnectButtons

	def PrepareFullDisplay(self, XMLData): # instruct FTForDisplay object to fetch and set up all data needed to display the FT
		# extract all data from XML tree and use to build up FT data structure

		def PopulateValueOptions(XMLRoot, HostEl, ComponentName, ListAttrib, OptionTagName, MasterOptionsList):
			# populate choice list for attribs of a numerical value.
			# Used for unit choice, value kind choice etc.
			# These choices are offered to the user in a choice widget
			# HostEl: element containing the numerical value
			# ComponentName (str): the numerical component name in HostEl
			# ListAttrib (str): name of the list in Component to populate
			# OptionTagName (str): the XML tag containing an option
			# MasterOptionsList (list): list of subclasses with XMLName attribs to match against options in XMLRoot
			Options = []
			for ThisTag in XMLRoot.findall(OptionTagName):
				# find human name for this option (use startswith() to ignore convert unit marker suffix)
				ThisOptionHumanName = [u.HumanName for u in MasterOptionsList
					if ThisTag.text.startswith(u.XMLName)][0]
				# set human name according to whether this is a value conversion option (special case for unit options)
				if ThisTag.text.endswith(info.ConvertValueMarker): ThisHumanName = _('Convert value to %s') % ThisOptionHumanName
				else: ThisHumanName = ThisOptionHumanName
				Options.append(ChoiceItem(XMLName=ThisTag.text,
					HumanName=ThisHumanName,
					Applicable=utilities.Bool2Str(ThisTag.get(info.ApplicableAttribName))))
			# set options list in the FT component
			setattr(getattr(HostEl, ComponentName), ListAttrib, Options)

		def PopulateOverallData(XMLRoot, HeaderEl):
			# extract data about the overall FT from XMLRoot
			# get risk receptor names and whether they are applicable to this FT
			self.RiskReceptorObjs = []
			for ThisRRTag in XMLRoot.findall(info.RiskReceptorTag):
				Applicable = utilities.Bool2Str(ThisRRTag.get(info.ApplicableAttribName)) # whether ThisRRTag is current one
				self.RiskReceptorObjs.append(ChoiceItem(XMLName=ThisRRTag.get(info.SerialTag),
					HumanName=utilities.TextAsString(ThisRRTag), Applicable=Applicable))
				if Applicable: HeaderEl.RR = ThisRRTag.text # set human name of current RR group in header
			# get severity category names and whether they are applicable to this FT
			self.SeverityCatObjs = []
			for ThisRRTag in XMLRoot.findall(info.SeverityCatTag):
				self.SeverityCatObjs.append(FTForDisplay.SeverityCatInFT(
					XMLName=ThisRRTag.get(info.SerialTag),
					HumanName=utilities.TextAsString(ThisRRTag),
					Applicable=utilities.Bool2Str(ThisRRTag.get(info.ApplicableAttribName))))
			# get risk receptor grouping options and whether they are applicable to this FT
			self.RRGroupingOptionObjs = []
			for ThisRRGroupingTag in XMLRoot.findall(info.RiskReceptorGroupingOptionTag):
				self.RRGroupingOptionObjs.append(ChoiceItem(
					XMLName=ThisRRGroupingTag.get(info.SerialTag),
					HumanName=self.RRGroupingNameHash[ThisRRGroupingTag.text],
					Applicable=utilities.Bool2Str(ThisRRGroupingTag.get(info.ApplicableAttribName))))

		def PopulateHeaderData(FT, HeaderEl, HeaderXMLRoot, ComponentNameToHighlight=''):
			# put header data from HeaderXMLRoot into attribs of HeaderEl (a FTHeader instance)
			# ComponentNameToHighlight (str): apply highlight to specified component
			# In DataInfo, each pair of items is: (FTHeader attrib name, XML tag)
			assert isinstance(HeaderEl, FTHeader)
			# set all header attribs except risk receptor (set in PopulateOverallData() )
			DataInfo = [ ('SIFName', 'SIFName'), ('OpMode', 'OpMode'), ('Rev', 'Rev'),
				('TargetRiskRedMeasure', 'TargetUnit'), ('BackgColour', 'BackgColour'),
				('TextColour', 'TextColour'), ('Severity', 'Severity'),
#				('TolFreq', 'TolFreq'), ('TolFreqUnit', 'TolFreqUnit'),
				('UEL', 'UEL'), ('TargetRiskRed', 'RRF'),
				('SIL', 'SIL'), ('OutcomeUnit', 'OutcomeUnit') ]
			assert ComponentNameToHighlight in [a for (a, b) in DataInfo] + ['TolFreq'] or (ComponentNameToHighlight == '')
			for Attrib, XMLTag in DataInfo:
				setattr(HeaderEl, Attrib, HeaderXMLRoot.findtext(XMLTag, default=''))
			# populate choice boxes for OpMode, risk receptor, severity and RR grouping
			self.Header.OpModeComponent.ObjectChoices = core_classes.OpModes[:]
			self.Header.RRComponent.ObjectChoices = self.RiskReceptorObjs[:]
			self.Header.SeverityComponent.ObjectChoices = self.SeverityCatObjs[:]
			self.Header.RRLabel.ObjectChoices = self.RRGroupingOptionObjs[:]
			# set which OpMode is applicable (i.e. currently used)
			for ThisOpModeIndex, ThisOpMode in enumerate(core_classes.OpModes): # check original OpMode list (not the local copy)
				UsingThisOpMode = (ThisOpMode == self.PHAObj.OpMode)
				self.Header.OpModeComponent.ObjectChoices[ThisOpModeIndex].Applicable = UsingThisOpMode
				if UsingThisOpMode: FT.OpMode = ThisOpMode # set OpMode attrib of FT
			# populate TolFreq value and unit
			TolFreqTag = HeaderXMLRoot.find(info.TolFreqTag)
			HeaderEl.TolFreq.Value = TolFreqTag.text
			HeaderEl.TolFreq.Unit = core_classes.UnitWithName(TolFreqTag.findtext(info.UnitTag,
				default=info.NullUnitInternalName))
			# populate lists of options relating to numerical values
			for ThisNumValue, ThisNumTag in [ ('TolFreq', TolFreqTag) ]:
				PopulateValueOptions(XMLRoot=ThisNumTag, HostEl=HeaderEl, ComponentName=ThisNumValue,
					ListAttrib='AcceptableUnits', OptionTagName=info.UnitOptionTag,
					MasterOptionsList=core_classes.UnitItem.UserSelectableUnits)
				ThisNumAttrib = getattr(HeaderEl, ThisNumValue)
				for (ThisOptionTag, ThisOption) in [
#						(info.ValueKindOptionTag, 'ValueKindOptions'), (info.ConstantOptionTag, 'ConstantOptions'),
						(info.ConstantOptionTag, 'ConstantOptions'),
						(info.MatrixOptionTag, 'MatrixOptions')]:
					# create and populate each option list in turn%%% working here; get specific data from each option tag, esp. constants
					setattr(ThisNumAttrib, ThisOption, [])
					ThisOptionList = getattr(ThisNumAttrib, ThisOption)
					for ThisOptionTagFound in HeaderXMLRoot.findall(ThisOptionTag):
						ThisOptionList.append(ThisOptionTagFound.text)
				# populate value kind options
				PopulateValueOptions(XMLRoot=ThisNumTag, HostEl=HeaderEl, ComponentName=ThisNumValue,
						ListAttrib='ValueKindOptions', OptionTagName=info.ValueKindOptionTag,
						MasterOptionsList=core_classes.NumValueClasses)
			print('FT3764 set TolFreq.ValueKindOptions to: ', HeaderEl.TolFreq.ValueKindOptions)
			# populate content elements
			for ThisEl in HeaderEl.ContentEls: ThisEl.Text.Content = getattr(HeaderEl, ThisEl.InternalName)
			# store component name to highlight
			self.Header.ComponentNameToHighlight = ComponentNameToHighlight

		def PopulateColumnData(ColumnEl, Column):
			# get data from ColumnEl (an XML FTColumnTag tree element) and populate into new objects in Column (a FTColumn instance).
			# ObjPopulator: keys are XML tags for objects, values are procedures to extract data from XML
			ObjPopulator = {info.FTEventTag: PopulateFTEvent, info.FTConnectorTag: PopulateFTConnector,
				info.FTGateTag: PopulateFTGate}
			for ObjElement in list(ColumnEl): # step through objects in column (list() iterates over children of ColumnEl)
				NewObj = ObjPopulator[ObjElement.tag](XMLObj=ObjElement, Column=Column) # extract data for each object
				Column.FTElements.append(NewObj) # put object in column

		def PopulateFTEvent(XMLObj, Column):
			# create an FTEvent, get data for FTEvent from XMLObj (XML element). Return the FTEvent
			assert isinstance(Column, FTColumn)
#			print("FT2236 received event data: ", ElementTree.tostring(XMLObj))
			NewEvent = FTEvent(FT=self, Column=Column)
#			print("FT3213 making new FTEvent: ", NewEvent)
			# get event data. In DataInfo, each pair of items is: (XML tag, FTEvent attrib name)
			DataInfoAsStr = [ (info.IDTag, 'ID'), ('Numbering', 'Numbering'),
				('EventDescription', 'EventDescription'), ('Value', 'Value'), ('ValueProblemObjectID', 'ValueProblemObjectID'),
				('Unit', 'ValueUnit'), ('ValueProblemID', 'ValueProblemID'), ('BackgColour', 'BackgColour') ]
			for Tag, Attrib in DataInfoAsStr:
				setattr(NewEvent, Attrib, XMLObj.findtext(Tag, default=''))
			DataInfoAsBool = [ ('CanEditValue', 'CanEditValue'), (info.ShowActionItemTag, 'ShowActionItems'),
				('IsIPL', 'IsIPL'),  ('FTEventLinked', 'Linked'),
				(info.ShowDescriptionCommentTag, 'ShowDescriptionComments'), (info.ShowValueCommentTag, 'ShowValueComments') ]
			for Tag, Attrib in DataInfoAsBool:
				setattr(NewEvent, Attrib, utilities.Bool2Str(XMLObj.findtext(Tag, default='False')))
			# DataInfoAsList: (Tag of each item in a list, name of the list to put the tag's text into,
			# whether to fetch numbering)
			DataInfoAsList = [ (info.DescriptionCommentTag, 'EventDescriptionComments', True),
				(info.ValueCommentTag, 'ValueComments', True),
				(info.ActionItemTag, 'ActionItems', True),
				('ConnectTo', 'ConnectToIDs', False), ('CollapseGroups', 'CollapseGroupIDs', False) ]
			for Tag, Attrib, FetchNumbering in DataInfoAsList:
				if FetchNumbering: # prefix text with numbering
					setattr(NewEvent, Attrib, [El.get(info.NumberingTag, '') + ' ' + El.text for El in XMLObj.findall(Tag)])
				else: # just get text, don't look for numbering
					setattr(NewEvent, Attrib, [El.text for El in XMLObj.findall(Tag)])
			# populate event type name: internal name and human name
			NewEvent.EventType = XMLObj.find('EventType').text
			NewEvent.EventTypeHumanName = self.EventTypeNameHash[NewEvent.EventType]
			# populate event type choice
			NewEvent.EventTypeComponent.ObjectChoices = [ChoiceItem(XMLName=ThisTag.text,
				HumanName=self.EventTypeNameHash[ThisTag.text],
				Applicable=utilities.Bool2Str(ThisTag.get(info.ApplicableAttribName)))
				for ThisTag in XMLObj.findall(info.EventTypeOptionTag)]
			# populate event value unit choice; TODO use PopulateValueOptions()
			NewEvent.EventValueUnitComponent.ObjectChoices = []
			for ThisTag in XMLObj.findall(info.UnitOptionTag):
				# find human name for this unit option (use startswith() to ignore convert marker suffix)
				ThisUnitHumanName = [u.HumanName for u in core_classes.UnitItem.UserSelectableUnits
					if ThisTag.text.startswith(u.XMLName)][0]
				# set human name according to whether this is a value conversion option
				if ThisTag.text.endswith(info.ConvertValueMarker): ThisHumanName = _('Convert value to %s') % ThisUnitHumanName
				else: ThisHumanName = ThisUnitHumanName
				NewEvent.EventValueUnitComponent.ObjectChoices.append(ChoiceItem(XMLName=ThisTag.text,
					HumanName=ThisHumanName,
					Applicable=utilities.Bool2Str(ThisTag.get(info.ApplicableAttribName))))
#			# populate value kind with HumanName of number kind class specified in incoming NumberKind tag
#			NewEvent.ValueKind = ([c.HumanName for c in core_classes.NumValueClasses
#				if c.XMLName == XMLObj.findtext(info.NumberKindTag, default='')] + ['???'])[0]
			# populate value kind choice
			NewEvent.EventValueKindComponent.ObjectChoices = [ChoiceItem(XMLName=ThisTag.text,
				HumanName=[c.HumanName for c in core_classes.NumValueClasses if c.XMLName == ThisTag.text][0],
				Applicable=utilities.Bool2Str(ThisTag.get(info.ApplicableAttribName)))
				for ThisTag in XMLObj.findall(info.NumberKindTag)]
			# populate value kind with HumanName of number kind marked as applicable
			NewEvent.ValueKind = [c.HumanName for c in NewEvent.EventValueKindComponent.ObjectChoices
				if c.Applicable][0]
			# retrieve data from ProblemIndicatorTag: decide whether to show problem button
			ProblemTag = XMLObj.find(info.ProblemIndicatorTag)
			if ProblemTag is None:
				NewEvent.ValueProblemButton.Visible = False  # if no problem info received, don't show problem button
			else:
				NewEvent.ProblemHumanHelp = ProblemTag.text
				NewEvent.ValueProblemButton.Visible = (ProblemTag.get(info.ProblemLevelAttribName, '') in
					['Level7', 'Level10'])
			return NewEvent

		def PopulateFTConnector(ConnectorEl):
			# create an FTConnector, get data for FTConnector from EventEl (XML element). Return the FTConnector
			# First, find out if it's in- or out-connector and create appropriate object
			NewConnector = {'In': FTConnectorIn, 'Out': FTConnectorOut}[ConnectorEl.findtext('Connectivity')]()
			# get connector data. In DataInfoAsXXX, each pair of items is: (XML tag, FTConnector attrib name)
			DataInfoAsStr = [ (info.IDTag, 'ID'), ('Description', 'Description'), ('BackgColour', 'BackgColour'),
				('Numbering', 'Numbering'), ('Style', 'Style'), ('RelatedConnector', 'RelatedConnector'),
				('Value', 'Value'), ('ValueProblemObjectID', 'ValueProblemObjectID'),
				('Unit', 'ValueUnit'), ('ValueProblemID', 'ValueProblemID') ]
			for Tag, Attrib in DataInfoAsStr:
				setattr(NewConnector, Attrib, ConnectorEl.findtext(Tag, default=''))
			DataInfoAsBool = [ ('ShowDescriptionComments', 'ShowDescriptionComments') ]
			for Tag, Attrib in DataInfoAsBool:
				setattr(NewConnector, Attrib, bool(ConnectorEl.findtext(Tag, default='False')))
			# DataInfoAsList: (Tag of each item in a list, name of the list to put the tag's text into)
			DataInfoAsList = [ ('DescriptionComments', 'DescriptionComments'), ('ConnectTo', 'ConnectTo'),
				('CollapseGroups', 'CollapseGroups') ]
			for Tag, Attrib in DataInfoAsList:
				setattr(NewConnector, Attrib, [El.text for El in ConnectorEl.findall(Tag)])
			return NewConnector

		def PopulateFTGate(XMLObj, Column):
			# create an FTGate, get data for FTGate from XMLObj (XML element). Return the FTGate
			print("FT3299 creating new FTGate")
			NewGate = FTGate(FT=self, Column=Column)
			# get gate data. In DataInfoAsXXX, each pair of items is: (XML tag, FTGate attrib name)
			DataInfoAsStr = [ (info.IDTag, 'ID'), ('Algorithm', ''), ('BackgColour', 'BackgColour'),
				('Numbering', 'Numbering'), ('Style', 'Style'), ('Algorithm', 'Algorithm'),
				('Value', 'Value'), ('ValueProblemObjectID', 'ValueProblemObjectID'), ('Description', 'Description'),
				('Unit', 'ValueUnit'), ('ValueProblemID', 'ValueProblemID') ]
			for Tag, Attrib in DataInfoAsStr:
				setattr(NewGate, Attrib, XMLObj.findtext(Tag, default=''))
			DataInfoAsBool = [ ('MadeBySystem', 'MadeBySystem'),
				('ShowDescriptionComments', 'ShowComments'), ('FTGateLinked', 'Linked') ]
			for Tag, Attrib in DataInfoAsBool:
				setattr(NewGate, Attrib, bool(XMLObj.findtext(Tag, default='False')))
			# DataInfoAsList: (Tag of each item in a list, name of the list to put the tag's text into)
			DataInfoAsList = [ ('DescriptionComments', 'DescriptionComments'), ('ConnectTo', 'ConnectTo'),
				('CollapseGroups', 'CollapseGroups') ]
			for Tag, Attrib in DataInfoAsList:
				setattr(NewGate, Attrib, [El.text for El in XMLObj.findall(Tag)])
			# populate gate kind choice
			NewGate.GateKind.ObjectChoices = [ChoiceItem(XMLName=ThisTag.text,
				HumanName=NewGate.GateKindHash[ThisTag.text],
				Applicable=utilities.Bool2Str(ThisTag.get(info.ApplicableAttribName)))
				for ThisTag in XMLObj.findall(info.FTGateTypeOptionTag)]
			# populate gate value unit choice
			NewGate.GateValueUnit.ObjectChoices = []
			for ThisTag in XMLObj.findall(info.UnitOptionTag):
				# find human name for this unit option
				ThisUnitHumanName = [u.HumanName for u in core_classes.UnitItem.UserSelectableUnits
					if ThisTag.text == u.XMLName][0]
				NewGate.GateValueUnit.ObjectChoices.append(ChoiceItem(XMLName=ThisTag.text,
					HumanName=ThisUnitHumanName,
					Applicable=utilities.Bool2Str(ThisTag.get(info.ApplicableAttribName))))
			# retrieve data from ProblemIndicatorTag: decide whether to show problem button
			ProblemTag = XMLObj.find(info.ProblemIndicatorTag)
			if ProblemTag is None:
				NewGate.ValueProblemButton.Visible = False  # if no problem info received, don't show problem button
			else:
				NewGate.ProblemHumanHelp = ProblemTag.text
				NewGate.ValueProblemButton.Visible = (ProblemTag.get(info.ProblemLevelAttribName, '') in
					['Level7', 'Level10'])
			return NewGate

		def PopulateDisplayAttribs(FT, DisplayAttribData):
			# extract display-related attribs from DisplayAttribData (XML tag or None) and populate them into FT
			# attribs can include zoom, pan, selection, collapse groups, and highlights
			# Clears highlight-related attribs if not found in DisplayAttribData, to remove highlight when no longer required
			# the lambda below converts 'Header' to FT's ID, for cases where the component to highlight is in the header
			# In the tuple, ClearIfAbsent (bool) means whether to clear the attrib if not found in DisplayAttribData;
			# ClearValue is the value to clear to
			for (AttribName, TagName, AttribType, ClearIfAbsent, ClearValue) in [
				('ElementIDContainingComponentToHighlight', info.FTElementContainingComponentToHighlight,
					lambda x: self.ID if x == 'Header' else x, True, None),
				('ComponentNameToHighlight', info.FTComponentToHighlight, str, True, ''),
				('Zoom', info.ZoomTag, float, False, None), ('PanX', info.PanXTag, int, False, None),
				('PanY', info.PanYTag, int, False, None)]:
				# try to get TagName from DisplayAttribData XML - which might have no root tag
				ThisElement = None if DisplayAttribData is None else DisplayAttribData.find(TagName)
				if ThisElement is None:
					if ClearIfAbsent: setattr(FT, AttribName, ClearValue) # clear attrib if not found in DisplayAttribData
				else: # value found; set the attrib value
					setattr(FT, AttribName, AttribType(ThisElement.text))

		# main procedure for PrepareFullDisplay()
#		print('FT3441 starting PrepareFullDisplay using the following XML data:')
#		ElementTree.dump(XMLData)
		self.Wipe() # start with a blank FT
		# find the outer tag containing the FT data
		FTData = [t for t in XMLData.iter(self.InternalName)][0]
		# populate display-related attributes specific to this Viewport, such as zoom, pan, selection, collapse groups,
		# and highlights
		DisplayAttribData = FTData.find(info.FTDisplayAttribTag)
		PopulateDisplayAttribs(self, DisplayAttribData)
		# extract data about the overall FT
		PopulateOverallData(FTData, HeaderEl=self.Header)
		# if header data was provided, use it to populate FT header
		XMLHeaderData = FTData.find(info.FTHeaderTag)
		if XMLHeaderData is not None:
			# should we highlight a component in the header?
			ComponentNameToHighlight = self.ComponentNameToHighlight if\
				self.ElementIDContainingComponentToHighlight == self.ID else ''
			PopulateHeaderData(self, self.Header, XMLHeaderData, ComponentNameToHighlight=ComponentNameToHighlight)
		# get column data
		ColumnElements = FTData.findall(info.FTColumnTag)
		for ColNo, ColumnEl in enumerate(ColumnElements):
			NewColumn = FTColumn(FT=self, ColNo=ColNo)
			self.Columns.append(NewColumn)
			PopulateColumnData(ColumnEl, NewColumn)
		# put builder button objects in all columns, and add a final column with just a builder button
		self.AddBuilderButtons()
		# populate elements' ConnectTo attribs (must be done AFTER populating all elements)
		self.PopulateConnectTo()

	def RenderInDC(self, TargetDC, FullRefresh=True, **Args):
		# render all FT components into TargetDC provided by ControlFrame
		# FullRefresh (bool): whether to redraw from scratch

		def DrawHeader(self, DC): # render the FT header in its own bitmap, then copy it to BaseLayerDC
			self.Header.RenderIntoBitmap(self.Zoom)
			DC.DrawBitmap(self.Header.Bitmap, self.Header.PosXInPx, self.Header.PosYInPx, useMask=False)

		def SetConnectButtonPos():
			# set PosX/Y attribs of all connect buttons in the fault tree, in pixels (needed to detect mouse clicks)
			for ThisButton in self.ConnectButtons:
				ThisColumn = self.Columns[ThisButton.ColIndex] # get column to left of button
				ThisButton.PosXInPx, ThisButton.PosYInPx = utilities.ScreenCoords(
					CanvasX=ThisColumn.PosXInCU + ThisColumn.SizeXInCU + ThisButton.PosXInCU,
					CanvasY=ThisColumn.PosYInCU + ThisButton.PosYInCU, Zoom=self.Zoom, PanX=self.PanX, PanY=self.PanY)
				ThisButton.SizeXInPx = ThisButton.SizeXInCU * self.Zoom
				ThisButton.SizeYInPx = ThisButton.SizeYInCU * self.Zoom

		def BlitIntoDC(BaseLayerBitmap, TargetDC): # transfer bitmaps into TargetDC provided by display device
			# copy BaseLayerBitmap into a buffer, to avoid overwriting it with floating layers
			BaseLayerSizeX, BaseLayerSizeY = BaseLayerBitmap.GetSize()
			Buffer = wx.Bitmap(width=BaseLayerSizeX, height=BaseLayerSizeY, depth=wx.BITMAP_SCREEN_DEPTH)
			BaseLayerCopyDC = wx.MemoryDC(BaseLayerBitmap)
			BufferDC = wx.MemoryDC(Buffer)
			BufferDC.Blit(xdest=0, ydest=0, width=BaseLayerSizeX, height=BaseLayerSizeY, source=BaseLayerCopyDC,
								 xsrc=0, ysrc=0)
			# sort overlay layers by z-coord, lowest first
			LayersToOverlayInZOrder = utilities.SortOnValues(
				[{'Layer': l, 'Z': l.PosZ} for l in self.FloatingLayers + [self.MyZoomWidget.FloatLayer]],
				ResultField='Layer', SortKeyField='Z')
			# overlay floating layers onto buffer
			OverlayDC = wx.GCDC(BufferDC)
			for ThisLayer in LayersToOverlayInZOrder:
				OverlayDC.DrawBitmap(ThisLayer.Bitmap, ThisLayer.PosXInPx, ThisLayer.PosYInPx)
			# copy entire FT into TargetDC in physical display device
			TargetDC.Blit(xdest=0, ydest=0, width=BaseLayerBitmap.GetWidth(), height=BaseLayerBitmap.GetHeight(),
				source=BufferDC, xsrc=0, ysrc=0)

		# main procedure for RenderInDC()
		assert isinstance(FullRefresh, bool)
		HostPanelSizeX, HostPanelSizeY = self.DisplDevice.GetSize()
		if FullRefresh:
			# get each element in the FT to calculate and draw itself in own bitmap: header, columns and strips
			self.Header.CalculateSize(self.Zoom, self.PanX, self.PanY)
			for ThisColumn in self.Columns:
				ThisColumn.RenderElementsInOwnBitmaps(self.Zoom)
			self.MarkObjectsWithPos() # set Pos attribs of all FT objects (must be done after rendering them, so we can get their size)
			# set column positions (needed for making inter-column strips)
			for ThisColumn in self.Columns:
				# get pixel coordinates of the top right corner of the column
				ThisColumn.EndXInPx, ThisColumn.PosYInPx = utilities.ScreenCoords(ThisColumn.PosXInCU + ThisColumn.SizeXInCU, 0,
					Zoom=self.Zoom, PanX=self.PanX, PanY=self.PanY)
			self.SetupInterColumnStrips() # set up and draw strips containing connecting lines between columns
			# make an overall bitmap, ready to blit constituent bitmaps into
			MinBufferSizeXInPx, MinBufferSizeYInPx = self.CalculateFTScreenSize(self.InterColumnStripWidth)
			# make sure buffer is big enough to reach the bottom of the screen, to accommodate the zoom tool
			# (potential optimisation: draw zoom widget in separate bitmap and blit transparently into its place in the host panel)
			ActualBufferSizeX = max(HostPanelSizeX, MinBufferSizeXInPx)
			ActualBufferSizeY = max(HostPanelSizeY, MinBufferSizeYInPx)
			self.BaseLayerBitmap = wx.Bitmap(width=ActualBufferSizeX, height=ActualBufferSizeY, depth=wx.BITMAP_SCREEN_DEPTH)
			BaseLayerDC = wx.MemoryDC(self.BaseLayerBitmap)
			# draw header in its own bitmap, then copy into BaseLayerDC
			DrawHeader(self, BaseLayerDC)
			# draw columns and inter-column strips in BaseLayerDC
			for ColIndex, Column in enumerate(self.Columns):
				# draw column
				Column.RenderInDC(self, BaseLayerDC, 0, 0)
				# draw inter-column strip, to the right of the column
				BaseLayerDC.DrawBitmap(self.InterColumnStripBuffers[ColIndex], Column.PosXInPx + Column.SizeXInPx, Column.PosYInPx, useMask=False)
			# set PosX/Y attribs of connect buttons in pixels (needed to detect mouse clicks)
			SetConnectButtonPos()
		# draw zoom widget. First, set its position: 50% across the panel, and slightly above the bottom of the panel
		self.MyZoomWidget.SetPos(HostPanelSizeX * 0.5, HostPanelSizeY - self.MyZoomWidget.GetSize()[1] - 10)
		self.MyZoomWidget.SetZoom(self.Zoom) # update zoom setting of zoom widget
		self.MyZoomWidget.DrawInBitmap() # draw zoom widget in its own bitmap
		BlitIntoDC(BaseLayerBitmap=self.BaseLayerBitmap, TargetDC=TargetDC)

	def AddBuilderButtons(self): # add builder buttons between objects in each column, and in a "new" column to the right
		BuilderButtonOffsetInCU = 70 # X offset between builder button left edges
		for ColNo, Col in enumerate(self.Columns):
			# work out which builders are needed: event builders, gate builders or both
			BuildersNeeded = [FTEventInCore]
			if ColNo > 0: BuildersNeeded.append(FTGateItemInCore)
			ColContent = [] # build list of builders and objects, with extra builder button set on the end (hence [None])
			for Obj in Col.FTElements + [None]:
				for ThisBuilderIndex, ThisBuilderKind in enumerate(BuildersNeeded): # add builder button family
					ColContent.append(FTBuilder(HostFT=self, ColNo=ColNo, ObjTypeRequested=ThisBuilderKind,
						OffsetXInCU=BuilderButtonOffsetInCU * ThisBuilderIndex))
				if Obj: ColContent.append(Obj) # add the object to the list, ignoring the final None
			Col.FTElements = ColContent[:] # put copy of new list in column
		# add an extra column containing only a builder button, if there are no columns in the FT, or if the last column isn't empty
		if self.Columns:
			ExtraColNeeded = (len(self.Columns[-1].FTElements) > 1) # True if last column doesn't contain only a builder button
			ExtraColNumber = self.Columns[-1].ColNo + 1
		else: # no columns in FT; make an initial column for the builder button
			ExtraColNeeded = True
			ExtraColNumber = 0
		if ExtraColNeeded:
			ThisCol = FTColumn(FT=self, ColNo=ExtraColNumber) # make column object
			self.Columns.append(ThisCol) # store the column in the FT
			# work out which builders are needed: event builders, gate builders or both
			BuildersNeeded = [FTEventInCore]
			if ExtraColNumber > 0: BuildersNeeded.append(FTGateItemInCore)
			# make builder buttons in the column
			for ThisBuilderIndex, ThisBuilderKind in enumerate(BuildersNeeded): # add builder button family
				ThisCol.FTElements.append(FTBuilder(HostFT=self, ColNo=ExtraColNumber, ObjTypeRequested=ThisBuilderKind,
					OffsetXInCU = BuilderButtonOffsetInCU * ThisBuilderIndex))

	def PopulateConnectTo(self):
		# populate ConnectTo attrib of all elements, using IDs from ConnectToIDs attrib
		AllEls = [El for El in WalkOverAllFTObjs(self)] # get list of all IDs using Walk... generator
		for ThisEl in AllEls:
			if hasattr(ThisEl, 'ConnectToIDs'):
				ThisEl.ConnectTo = [utilities.ObjectWithID(AllEls, TargetID=ElID) for ElID in ThisEl.ConnectToIDs]

	def MarkObjectsWithPos(self): # set PosXInCU, PosYInCU, PosXInPx, PosYInPx attributes of all FT objects
		# (object position in canvas coords relative to column, and in pixels relative to display device)
		# This routine will crudely bunch everything at the top of each column. Optimise later
		YGapBelowHeader = 30 # in canvas units
		self.Header.PosXInCU = self.Header.PosYInCU = 0 # put header at top left of canvas
		self.Header.PosXInPx, self.Header.PosYInPx = utilities.ScreenCoords(self.Header.PosXInCU,
			self.Header.PosYInCU, self.Zoom, PanX=self.PanX, PanY=self.PanY)
		ThisColOffsetXInCU = self.MarginXInCU # X offset from canvas origin; initialize for 1st column
		for ColNo, Col in enumerate(self.Columns):
			ColWidthInCU = 0  # width of each column will be calculated as we go along
			Col.PosXInPx = 1000000; Col.SizeXInPx = 0 # initialise
			LastPosY = self.Header.SizeYInCU + YGapBelowHeader # column Y starts just below header
			for ElIndex, ThisElement in enumerate(Col.FTElements):
				# each element starts at left edge of column (except builder button, already set in own __init__)
				if not isinstance(ThisElement, FTBuilder): ThisElement.PosXInCU = 0
				ThisElement.PosYInCU = LastPosY
				ThisElement.PosXInPx, ThisElement.PosYInPx = utilities.ScreenCoords(ThisColOffsetXInCU + ThisElement.PosXInCU,
					LastPosY, self.Zoom, PanX=self.PanX, PanY=self.PanY)
				# set PosX/Y of components within elements
				if hasattr(ThisElement, 'AllElements'):
					for ThisComponent in ThisElement.AllElements:
						ThisComponent.PosXInPx = ThisElement.PosXInPx + (ThisComponent.PosXInCU * self.Zoom)
						ThisComponent.PosYInPx = ThisElement.PosYInPx + (ThisComponent.PosYInCU * self.Zoom)
				# set overall column width
				ColWidthInCU = max(ColWidthInCU, ThisElement.PosXInCU + ThisElement.SizeXInCU)
				# get Y-coord of next item, if any
				if ElIndex + 1 < len(Col.FTElements):
					NextItem = Col.FTElements[ElIndex + 1]
					# increment Y unless this and next items are builder buttons (so that they appear on the same row)
					if not (isinstance(NextItem, FTBuilder) and isinstance(ThisElement, FTBuilder)):
						LastPosY += ThisElement.SizeYInCU +\
							self.YGapBetweenItemsInCU(ThisElement, Col.FTElements[ElIndex + 1])
			# store finalised column PosX and width
			Col.PosXInCU = ThisColOffsetXInCU
			Col.PosYInCU = 0 # relative to display device, columns start at the top
			Col.PosXInPx, Col.PosYInPx = utilities.ScreenCoords(Col.PosXInCU, Col.PosYInCU, self.Zoom, self.PanX, self.PanY)
			Col.SizeXInCU = ColWidthInCU
			Col.SizeXInPx = ColWidthInCU * self.Zoom
			Col.SizeYInCU = self.GetColumnLengthInCU(Col)
			Col.SizeYInPx = Col.SizeYInCU * self.Zoom
			# set OffsetX for next column
			ThisColOffsetXInCU += ColWidthInCU + self.InterColumnStripWidth

	def SetupInterColumnStrips(self):
		# draw inter-column strips with connection lines

		def ConstructInterColumnStrip(LeftColIndex, ParentWindow):
			# prepare and draw one strip between columns with index LeftColIndex and ditto+1. Strip contains:
			# - connecting lines between objects in left and right columns
			# - "connect" buttons on unused outputs of objects in left column
			# - "connect" buttons on unused inputs in right column
			# Returns buffer containing the strip image, list containing connect button objects

			def DrawConnectingHorizontals(FTColumn, DrawDC, IsLeftCol=True, ConnectedEls=set()):
				# in DrawDC, draw horizontal parts of connecting lines attached to FTColumn on left or right (depending on IsLeftCol)
				# If it's a right column, we need ConnectedEls, a list or set of objects in this column that are connected
				# to items in the next column to the left
				if IsLeftCol:
					LineStartXInCU = 0
					# end the line just inside strip for unconnected objs
					LineEndXStubInCU = int(round(self.ConnectingHorizStubFraction * self.InterColumnStripWidth))
				else:
					LineStartXInCU = int(round(self.InterColumnStripWidth)) # start line at right edge of strip
					LineEndXStubInCU = int(round((1 - self.ConnectingHorizStubFraction) * self.InterColumnStripWidth))
				LineEndXFullInCU = int(round(0.5 * self.InterColumnStripWidth)) # end at centre of strip for connected objs
				DrawDC.SetPen(wx.Pen(ConnectingLineColour, width=max(1, int(round(ConnectingLineThicknessInCU * self.Zoom)))))
				# draw the lines for each connectable item in the column.
				for ThisElement in FTColumn.FTElements:
					if ThisElement.Connectable:
						LineYInCU = ThisElement.HorizontalLineYInCU()
						# decide whether the item is connected
						if IsLeftCol: IsConnected = bool(ThisElement.ConnectTo)
						else: IsConnected = (ThisElement in ConnectedEls)
						LineStartXInPx, LineStartYInPx = utilities.ScreenCoords(LineStartXInCU, LineYInCU, self.Zoom, PanX=0, PanY=0)
						# Pan needn't be considered, as it is applied when copying bitmaps to display device
						if IsConnected:
							LineEndXInPx, LineEndYInPx = utilities.ScreenCoords(LineEndXFullInCU, LineYInCU, self.Zoom, PanX=0, PanY=0)
						else:
							LineEndXInPx, LineEndYInPx = utilities.ScreenCoords(LineEndXStubInCU, LineYInCU, self.Zoom, PanX=0, PanY=0)
						DrawDC.DrawLine(LineStartXInPx, LineStartYInPx, LineEndXInPx, LineEndYInPx)

			def DrawConnectingVerticals(LeftColumn, RightColumn, DrawDC, ConnectedOnRightEls):
				# In DrawDC, draw vertical parts of connecting lines between horizontals of connected items in Left and Right columns
				# ConnectedOnRightEls is a list or set of object IDs in the right column that are connected
				LineThickness = 4 # in canvas coords
				LineXInCU = int(round(0.5 * self.InterColumnStripWidth)) # line will be drawn in centre of strip
				LineColour = (0xf6, 0xff, 0x2a) # golden yellow
				DrawDC.SetPen(wx.Pen(LineColour, width=max(1, int(round(LineThickness * self.Zoom)))))
				# convert ConnectedOnRightEls into indices in RightColumn
				ConnectedOnRightIndices = [RightColumn.FTElements.index(El) for El in ConnectedOnRightEls]
				# draw a vertical line for each connected item in right column
				for RightIndex in ConnectedOnRightIndices:
					RightObj = RightColumn.FTElements[RightIndex] # get the right column item
					# find y-coords of horizontal lines of items in left column connected to this item in right column
					LeftItemYCoords = [Obj.HorizontalLineYInCU() for Obj in
						[LeftObj for LeftObj in LeftColumn.FTElements if RightObj in LeftObj.ConnectTo]]
					# find the min and max y coord for vertical line, based on coords of connected items in left and right columns
					# Pan needn't be considered, as it is applied when copying bitmaps to display device
					MinY = min(LeftItemYCoords + [RightObj.HorizontalLineYInCU()])
					MaxY = max(LeftItemYCoords + [RightObj.HorizontalLineYInCU()])
					LineStartXInPx, LineStartYInPx = utilities.ScreenCoords(LineXInCU, MinY, self.Zoom, PanX=0, PanY=0)
					LineEndXInPx, LineEndYInPx = utilities.ScreenCoords(LineXInCU, MaxY, self.Zoom, PanX=0, PanY=0)
					DrawDC.DrawLine(LineStartXInPx, LineStartYInPx, LineEndXInPx, LineEndYInPx)

			def DrawLeftOrRightConnectButtons(ThisColumn, DrawDC, ColIndex, IsLeft=True):
				# draw 'connect' button on the horizontal stub for each connectable object in ThisColumn (FTColumn instance)
				# ThisColumn is the column containing the elements to make connect buttons for
				# IsLeft (bool): whether we are drawing connect buttons coming from the left column
				# ColIndex is the column number in the FT to the left of the connecting strip containing the buttons,
				# even if the buttons are associated with objects in the next column.
				# side, and therefore don't need connect buttons
				# returns list of new button widget objects
				ConnectButtonWidgets = []
				for ThisElement in ThisColumn.FTElements:
					# check max connectivity not yet reached (for right elements)
					if (IsLeft or (len(JoinedFrom(self, ThisElement)) < getattr(ThisElement,
							'MaxElementsConnectedToThis', 0))) and ThisElement.Connectable:
						# old version - bitmap button (keep in case we revert to bitmap)
#						NewButtonWidget = ButtonObjectNotInElement(FT=ThisColumn.FT, InternalName='ConnectButton',
#							PosYInCU=0, Toggle=False, HostObject=ThisElement,
#							ArtProvider=self.ArtProvider, ColIndex=ColIndex, ObjID=ThisElement.ID, IsLeft=True)
						NewButtonWidget = ButtonObjectNotInElement(FT=ThisColumn.FT, InternalName='ConnectButton',
							PosYInCU=0, Toggle=False, HostObject=ThisElement,
							ArtProvider=None, ColIndex=ColIndex, ObjID=ThisElement.ID, IsLeft=True)
						ConnectButtonWidgets.append(NewButtonWidget)
						# set PosXInCU. For right connect buttons, this needs to know the button size
						if IsLeft:
							NewButtonWidget.PosXInCU = int(round(self.ConnectingHorizStubFraction * self.InterColumnStripWidth))
						else:
							NewButtonWidget.PosXInCU = int(round((1 - self.ConnectingHorizStubFraction) *\
								self.InterColumnStripWidth)) - NewButtonWidget.SizeXInCU
							NewButtonWidget.IsLeft = False
						# in y-axis, align button with connect line, and offset upwards by half the button's height
						NewButtonWidget.PosYInCU = ThisElement.HorizontalLineYInCU() - 0.5 * NewButtonWidget.SizeYInCU
						# draw button in the inter-column strip
						NewButtonWidget.Draw(DC=DrawDC, Zoom=self.Zoom)
				return ConnectButtonWidgets

			# main procedure for ConstructInterColumnStrip()
			self.ConnectingHorizStubFraction = 0.1 # fraction of strip width = length of horiz stub lines for unconnected objects
			ConnectButtons = [] # connect button widgets created
			# calculate the required length
			# Does the right column exist? If so, get the greater of the left and right column lengths
			RightColExists = (LeftColIndex < len(self.Columns) - 1)
			if RightColExists:
				StripLength = max(self.GetColumnLengthInCU(self.Columns[LeftColIndex]), self.GetColumnLengthInCU(self.Columns[LeftColIndex + 1]))
				# make a set of elements in right column that are connected to the left column
				ConnectedOnRightEls = set(utilities.Flatten([Obj.ConnectTo for Obj in
					self.Columns[LeftColIndex].FTElements]))
#				print("FT3674 ConnectedOnRightEls: ", ConnectedOnRightEls)
				# check if right col has any connectable objects
				RightColConnectable = True in [getattr(El, 'NeedsConnectButton', False)
					for El in self.Columns[LeftColIndex + 1].FTElements]
			else:
				StripLength = self.GetColumnLengthInCU(self.Columns[LeftColIndex])
				RightColConnectable = False
			# make a bitmap to draw into
			Buffer = wx.Bitmap(width=int(round(self.InterColumnStripWidth * self.Zoom)),
				height=int(round(StripLength * self.Zoom)), depth=wx.BITMAP_SCREEN_DEPTH)
			DrawDC = wx.MemoryDC(Buffer)
			# draw connecting lines between left and right columns
			DrawConnectingHorizontals(self.Columns[LeftColIndex], DrawDC, IsLeftCol=True)
			if RightColConnectable:
				# draw connect buttons for any unconnected elements in the left side column
				ConnectButtons.extend(DrawLeftOrRightConnectButtons(self.Columns[LeftColIndex], DrawDC, LeftColIndex,
					IsLeft=True))
				DrawConnectingHorizontals(self.Columns[LeftColIndex + 1], DrawDC, IsLeftCol=False,
					ConnectedEls=ConnectedOnRightEls)
				DrawConnectingVerticals(self.Columns[LeftColIndex], self.Columns[LeftColIndex + 1], DrawDC, ConnectedOnRightEls)
				ConnectButtons.extend(DrawLeftOrRightConnectButtons(self.Columns[LeftColIndex + 1], DrawDC,
					LeftColIndex, IsLeft=False))
			return (Buffer, ConnectButtons)

		# main procedure for SetupInterColumnStrips()
		# draw inter-column strips
		self.InterColumnStripBuffers = []
		for ColIndex in range(len(self.Columns)):
			(ThisBuffer, ThisConnectButtons) = ConstructInterColumnStrip(ColIndex, self.ParentWindow)
			self.InterColumnStripBuffers.append(ThisBuffer)
			self.ConnectButtons.extend(ThisConnectButtons)

	def GetColumnLengthInCU(self, Column): # return the length of the column in canvas units, including the header and post-header gap
		# Column is a FTColumn instance
		if Column.FTElements: # are there any objects in the column? get the PosX + SizeX of the last object
			return Column.FTElements[-1].PosYInCU + Column.FTElements[-1].SizeYInCU
		else: return self.MinColumnLength

	def CalculateFTScreenSize(self, InterColumnStripWidth):
		# calculate total size of FT in screen pixels. This is needed to make buffer for drawing entire FT.
		# InterColumnStripWidth is in canvas units
		# First, calculate X size in pixels
		# Calculate width of each column in canvas units
		ColumnWidths = []
		for ThisCol in self.Columns:
			ColumnWidths.append(max([0] + [ThisEl.SizeXInCU for ThisEl in ThisCol.FTElements]))
		# TotalSizeX is left margin plus (all column widths plus inter-column strips), or header width, if bigger
		TotalSizeX = (self.MarginXInCU + max(self.Header.SizeXInCU, sum(ColumnWidths, 0) +
			InterColumnStripWidth * max(len(self.Columns) - 1, 0))) * self.Zoom
		# TotalSizeY is the longest column, including header and space below header
		TotalSizeY = int(round(max([self.GetColumnLengthInCU(Col) for Col in self.Columns]) * self.Zoom))
		return (TotalSizeX, TotalSizeY)

	def HandleMouseAnyClick(self, ClickXInPx, ClickYInPx, TolXInPx, TolYInPx, ClickKind, **Args):
		# handle any kind of mouse click inside the display device displaying the FT
		# ClickX/YInPx (int): coord of mouse click in pixels relative to display device, i.e. directly comparable with
		# PosX/YInPx of FT elements
		# ClickKind (str): 'XY' where X is Left, Centre or Right; Y is Single, Long, Double, Triple
		# Args can include: CanStartDrag, CanSelect
		# Find out which element(s), if any, are clicked
		assert ClickKind in [X + Y for X in ['Left', 'Centre', 'Right'] for Y in ['Single', 'Long', 'Double', 'Triple']]
		Hits = [] # list of dict of elements/hotspots clicked
		for ThisEl in self.AllClickableObjects():
			HitHotspot = ThisEl.MouseHit(ClickXInPx, ClickYInPx, TolXInPx=TolXInPx, TolYInPx=TolYInPx)
			if HitHotspot: Hits.append({'Element': ThisEl, 'Hotspot': HitHotspot})
		if Hits: # any elements hit? Find the hit element with highest PosZ (z-coordinate)
			HighestZ = max(ThisHit['Element'].PosZ for ThisHit in Hits)
			HitWithHighestZ = [ThisHit for ThisHit in Hits if ThisHit['Element'].PosZ == HighestZ][0]
			# capture which element and hotspot were clicked; needed for drag handler
			if ClickKind.startswith('Left'):
				ElToHandleLClick = HitWithHighestZ['Element']
				ElHotspotToHandle = HitWithHighestZ['Hotspot']
			# check if the topmost clicked element is already doing an editing operation - if so, ignore the click
			if ElToHandleLClick != self.CurrentEditElement:
				self.EndEditingOperation() # close out any operation in progress
				self.LastElLClicked = ElToHandleLClick # needed for drag handler
				self.LastElLClickedHotspot = ElHotspotToHandle
				# identify appropriate handler for click
				if ClickKind == 'LeftSingle': Handler = 'HandleMouseLClickOnMe'
				elif ClickKind == 'LeftDouble': Handler = 'HandleMouseLDClickOnMe'
				# invoke handler, if clicked element has implemented it
				if hasattr(ElToHandleLClick, Handler):
					getattr(ElToHandleLClick, Handler)(HitHotspot=HitHotspot, HostViewport=self, MouseX=ClickXInPx, MouseY=ClickYInPx)
				else: print("FT2105 %s handler not implemented" % ClickKind)
		else: # click on empty space within FT
			self.EndEditingOperation() # close out any operation in progress
			if ClickKind.startswith('Left'): self.HandleMouseLClickOnEmptySpace(ClickX=ClickXInPx, ClickY=ClickYInPx, ClickKind=ClickKind)

	def HandleMouseLClick(self, ClickXInPx, ClickYInPx, TolXInPx, TolYInPx, **Args):
		self.HandleMouseAnyClick(ClickXInPx, ClickYInPx, TolXInPx, TolYInPx, ClickKind='LeftSingle', **Args)

	def HandleMouseLDrag(self, MouseX, MouseY):
		# handle mouse drag with left button pressed
		if self.EditingConnection: # dragging from a connect button
			self.HandleMouseLDragEditingConnection(MouseX, MouseY)
		elif self.LastElLClicked: # did we click on an element?
			if hasattr(self.LastElLClicked, 'HandleMouseLDragOnMe'):
				self.LastElLClicked.HandleMouseLDragOnMe(Hotspot=self.LastElLClickedHotspot, HostViewport=self,
					MouseX=MouseX, MouseY=MouseY)
		else: # dragging in empty space: pan PHA model display
			# set mouse pointer
			wx.SetCursor(wx.Cursor(display_utilities.StockCursors['+Arrow']))
			self.PanX = self.PanStartX + MouseX - self.MouseLClickPosX
			self.PanY = self.PanStartY + MouseY - self.MouseLClickPosY
			self.Panning = True # flag to indicate panning is in progress
			self.DisplDevice.Redraw(FullRefresh=True)

	def HandleMouseLDragEnd(self, MouseX, MouseY, **Args):
		# handle mouse left button release at the end of dragging
		if self.EditingConnection: # we dragged after clicking on a connect button
			self.HandleMouseLDragEndEditingConnection(MouseX, MouseY)
		elif self.Panning: # we were panning - need to redraw at the end of the pan, so that gates get filled in
			self.Panning = False
			self.DisplDevice.Redraw(FullRefresh=True)
		elif hasattr(self.LastElLClicked, 'HandleMouseLDragEndOnMe'):
			self.LastElLClicked.HandleMouseLDragEndOnMe(Hotspot=self.LastElLClickedHotspot, HostViewport=self,
				MouseX=MouseX, MouseY=MouseY, **Args)

	def HandleMouseLDClick(self, ClickXInPx, ClickYInPx, TolXInPx, TolYInPx, **Args):
		# handle mouse left double click
		self.HandleMouseAnyClick(ClickXInPx, ClickYInPx, TolXInPx, TolYInPx, ClickKind='LeftDouble', **Args)

	def HandleMouseLClickOnEmptySpace(self, ClickX, ClickY, ClickKind):
		# handle mouse left button down at screen coords ClickX/Y within FT Viewport, but not on any clickable object's hotspot
		assert isinstance(ClickX, int)
		assert isinstance(ClickY, int)
		assert ClickKind in ['Left' + Y for Y in ['Single', 'Long', 'Double', 'Triple']]
		# handle single click: get ready for possible drag to pan FT display
		if ClickKind.endswith('Single'):
			self.LastElLClicked = None
			self.MouseLClickPosX = ClickX
			self.MouseLClickPosY = ClickY
			self.PanStartX = self.PanX # capture current Pan settings; used during drag
			self.PanStartY = self.PanY
			# set mouse pointer
			wx.SetCursor(wx.Cursor(display_utilities.StockCursors['+Arrow']))
		# handle double click: return Pan to 'home' position
		elif ClickKind.endswith('Double'):
			self.PanX = self.PanY = 0
			self.DisplDevice.Redraw(FullRefresh=True)

	def HandleMouseLDragEditingConnection(self, MouseX, MouseY): # handle drag after mouse left click on a connect button
		HalfButtonSizeXInPx = int(round(0.5 * self.EditingConnectionStartButton.SizeXInPx))
		HalfButtonSizeYInPx = int(round(0.5 * self.EditingConnectionStartButton.SizeYInPx))
		# we need to draw rubber band(s) leading to button(s) listed in self.RubberBandTo
		# find the position(s) of these button(s)
		RubberBandToXInPx = [ThisButton.PosXInPx + HalfButtonSizeXInPx for ThisButton in self.RubberBandTo]
		RubberBandToYInPx = [ThisButton.PosYInPx + HalfButtonSizeYInPx for ThisButton in self.RubberBandTo]
#		# get start drag position based on centre position of button first clicked
#		UseStartXInPx = self.EditingConnectionStartButton.PosXInPx + HalfButtonSizeXInPx
#		UseStartYInPx = self.EditingConnectionStartButton.PosYInPx + HalfButtonSizeYInPx
		# work out the end drag position to show (constrained within inter-column strip), which will be used as
		# centre position of ending button at current drag position
		UseEndXInPx = max(self.StripMinXInPx + HalfButtonSizeXInPx +
			(self.ConnectingHorizStubFraction * self.InterColumnStripWidth * self.Zoom),
			min(self.StripMaxXInPx - (self.ConnectingHorizStubFraction *
			self.InterColumnStripWidth * self.Zoom) - HalfButtonSizeXInPx, MouseX))
		UseEndYInPx = max(self.StripMinYInPx + self.Header.SizeYInPx + HalfButtonSizeYInPx,
			min(self.StripMaxYInPx - HalfButtonSizeYInPx, MouseY))
		# work out the buffer starting and ending coords relative to display device
		BufferStartX = min(RubberBandToXInPx + [UseEndXInPx]) - self.ConnectButtonBufferBorderX - HalfButtonSizeXInPx
		BufferStartY = min(RubberBandToYInPx + [UseEndYInPx]) - self.ConnectButtonBufferBorderY - HalfButtonSizeYInPx
		BufferEndX = max(RubberBandToXInPx + [UseEndXInPx]) + self.ConnectButtonBufferBorderX + HalfButtonSizeXInPx
		BufferEndY = max(RubberBandToYInPx + [UseEndYInPx]) + self.ConnectButtonBufferBorderY + HalfButtonSizeYInPx
		# make buffer to draw connecting line
		ConnectButtonBitmap = wx.Bitmap(
			width=(BufferEndX - BufferStartX) + 2 * (HalfButtonSizeXInPx + self.ConnectButtonBufferBorderX),
			height=(BufferEndY - BufferStartY) + 2 * (HalfButtonSizeYInPx + self.ConnectButtonBufferBorderY),
			depth=wx.BITMAP_SCREEN_DEPTH)
		DrawDC = wx.MemoryDC(ConnectButtonBitmap)
		# draw lines from rubber band button centres to ending button centre
		DrawDC.SetPen(wx.Pen(wx.Colour(0xff, 0xcb, 0x29), width=max(1, int(round(2 * self.Zoom))))) # orange
		for RubberBandToIndex in range(len(self.RubberBandTo)):
			DrawDC.DrawLine(RubberBandToXInPx[RubberBandToIndex] - BufferStartX,
				RubberBandToYInPx[RubberBandToIndex] - BufferStartY,
				UseEndXInPx - BufferStartX,
				UseEndYInPx - BufferStartY)
		# draw rubber band buttons
		for ThisButtonIndex, ThisRubberBandButton in enumerate(self.RubberBandTo):
			ThisRubberBandButton.DrawConnectButton(DC=DrawDC, Zoom=self.Zoom,
				DesignatedX=RubberBandToXInPx[ThisButtonIndex] - BufferStartX - HalfButtonSizeXInPx,
				DesignatedY=RubberBandToYInPx[ThisButtonIndex] - BufferStartY - HalfButtonSizeYInPx)
		# draw end button at current drag position
			self.EditingConnectionStartButton.DrawConnectButton(DC=DrawDC, Zoom=self.Zoom,
			DesignatedX=UseEndXInPx - BufferStartX - HalfButtonSizeXInPx,
			DesignatedY=UseEndYInPx - BufferStartY - HalfButtonSizeYInPx)
		# put draw buffer into start button's floatlayer
		FloatLayerToUse = self.EditingConnectionStartButton.FloatLayer
		FloatLayerToUse.Bitmap = ConnectButtonBitmap
		FloatLayerToUse.PosXInPx = BufferStartX
		FloatLayerToUse.PosYInPx = BufferStartY
		self.DisplDevice.Redraw(FullRefresh=False) # refresh the display to show the draw buffer

	def HandleMouseLDragEndEditingConnection(self, MouseX, MouseY):
		# handle mouse left button up after dragging on a connect button

		def SendRequest(DisconnectList=[], ConnectList=[]): # send request to core to execute command that changes
			# connections between elements
			# DisconnectList: list of 2-tuples (from, to) - elements to be disconnected from each other
			# ConnectList: list of 2-tuples (from, to) - elements to be connected to each other
			assert isinstance(DisconnectList, list)
			assert isinstance(ConnectList, list)
			assert len(DisconnectList) + len(ConnectList) > 0
			print("FT3870 Disconnect, Connect: ", ','.join([str(i.ID) + '~' + str(j.ID) for i, j in DisconnectList]), '|', ','.join([str(i.ID) + '~' + str(j.ID) for i, j in ConnectList]))
			vizop_misc.SendRequest(Socket=self.C2DSocketREQ, Command='RQ_FT_ChangeConnection',
				Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
				Disconnect=','.join([str(i.ID) + '~' + str(j.ID) for i, j in DisconnectList]),
				Connect=','.join([str(i.ID) + '~' + str(j.ID) for i, j in ConnectList]))

		def NoChangeToConnections(): # actions required to tidy up if no connection changes will be made
			# tidy up display
			self.DisplDevice.Redraw(FullRefresh=False)

		StartClickObj = self.EditingConnectionStartButton.HostObject # the object associated with the connect button dragged from
		self.EditingConnection = False
		# remove floating layer containing the drag buttons and line
		self.FloatingLayers.remove(self.EditingConnectionStartButton.FloatLayer)
		# we consider the 12 possible cases listed in FT specification.
		# Did we hit a connect button (apart from the starting button)? (filters out "drag to itself" in cases 2, 8)
		EndButtonCandidates = [b for b in self.ConnectButtons if b.MouseHit(MouseX, MouseY,
			TolXInPx=self.DisplDevice.TolXInPx, TolYInPx=self.DisplDevice.TolYInPx)
			if b is not self.EditingConnectionStartButton]
		# did we hit a connect button that we can connect to?
#		EndButtonCandidates = [b for b in self.EditingConnectionCanConnectTo if b.MouseHit(MouseX, MouseY,
#			TolXInPx=self.DisplDevice.TolXInPx, TolYInPx=self.DisplDevice.TolYInPx)]
		if EndButtonCandidates:
			EndClickObj = EndButtonCandidates[0].HostObject # destination FT object for the connection
			# did we start at a left button (output)?
			if self.EditingConnectionStartButton.IsLeft:
				# is the starting output already connected to any input?
				if StartClickObj.ConnectTo:
					# did we end at another output?
					if EndButtonCandidates[0].IsLeft:
						# move all the connections from the old output to the new one, case 4
						SendRequest(DisconnectList=[(StartClickObj, To) for To in StartClickObj.ConnectTo],
							ConnectList=[(EndClickObj, To) for To in StartClickObj.ConnectTo])
					else: # ended at an input: add connection from output to input if not already connected, cases 5 and 6
						SendRequest(ConnectList=[(StartClickObj, EndClickObj)])
				else: # starting output not connected to anything
					if EndButtonCandidates[0].IsLeft: # did we drag to another output? do nothing, case 2b
						NoChangeToConnections()
					else: # dragged to an input: make new connection, case 1
						print("FT3908 case 1: from, to: ",  StartClickObj.ID, EndClickObj.ID)
						SendRequest(ConnectList=[(StartClickObj, EndClickObj)])
			else: # started at a right button (input)
				StartObjConnectedFrom = JoinedFrom(FT=self, FTObj=StartClickObj, FirstOnly=False) # get connected outputs
				if StartObjConnectedFrom: # is the starting input already connected?
					if EndButtonCandidates[0].IsLeft: # did we end at an output?
						# connect if not already connected, cases 11 and 12
						SendRequest(ConnectList=[(EndClickObj, StartClickObj)])
					else: # ended at an input: move connections from old to new input, case 10
						print("FT3915 case 10")
						SendRequest(DisconnectList=[(From, StartClickObj) for From in StartObjConnectedFrom],
							ConnectList=[(From, EndClickObj) for From in StartObjConnectedFrom])
				else: # starting input not connected to anything
					if EndButtonCandidates[0].IsLeft: # did we end at an output? connect output to input, case 7
						SendRequest(ConnectList=[(EndClickObj, StartClickObj)])
					else: # dragged from unconnected input to another input: do nothing, case 8b
						NoChangeToConnections()
		else: # no valid end button hit
			if self.EditingConnectionStartButton.IsLeft: # started at a left (output) button?
				if StartClickObj.ConnectTo:
					# already connected to something(s)? Disconnect all of them, case 3
					SendRequest(DisconnectList=[(StartClickObj, To) for To in StartClickObj.ConnectTo])
				else: # not connected to anything; do nothing, case 2a
					NoChangeToConnections()
			else: # started at a right (input) button
				# get list of outputs this input is connected to
				JoinedFromObjs = JoinedFrom(FT=self, FTObj=StartClickObj, FirstOnly=False)
				if JoinedFromObjs:
					# already connected to something(s)? Disconnect all of them, case 9
					SendRequest(DisconnectList=[(From, StartClickObj) for From in JoinedFromObjs])
				else: # not connected to anything; do nothing, case 8
					NoChangeToConnections()

	def RefreshZoomWidget(self, StillZooming=True, **Args):
		# get FT to refresh the zoom widget. Sends request to re-blit the FT, but no need to render from scratch.
		# StillZooming (bool): whether the user is continuing to change the zoom
		assert isinstance(StillZooming, bool)
		self.Zooming = StillZooming
		self.DisplDevice.Redraw(FullRefresh=not StillZooming)

	def RedrawDuringZoom(self, NewZoom=1.0):
		# redraw FT during zoom change. For now, redraw the entire FT from scratch
		# NewZoom (float): new zoom level requested by the zoom command
		assert isinstance(NewZoom, (int, float))
		self.Zoom = NewZoom
		self.Zooming = True # simplified drawing during zoom
		self.DisplDevice.Redraw(FullRefresh=True)

	def EndEditingOperation(self, Event=None, AcceptEdits=None):
		# tidy up after user has selected from a choice or typed in a TextElement, then clicked out
		# Event: placeholder for Event arg supplied from events that bind to this procedure.
		# AcceptEdits (bool or None): whether to retain the edits made, or discard them. If None, use global project setting.
		# Currently handles plain text only with no embedded format commands
		assert isinstance(AcceptEdits, bool) or (AcceptEdits is None)
		# check if any editing operation was in progress
		if self.CurrentEditElement:
			if isinstance(AcceptEdits, bool): AcceptEditsThisTime = AcceptEdits
			else: AcceptEditsThisTime = self.DisplDevice.Parent.EditAllowed
			CurrentEditBehaviour = getattr(self.CurrentEditElement,'EditBehaviour', None)
			# check if it was a text editing operation
			if CurrentEditBehaviour == 'Text':
				# get the text typed by the user
				TextEntered = self.CurrentEditTextCtrl.GetValue().strip()
				# check if any changes made%%%
				if AcceptEditsThisTime and (TextEntered != self.CurrentEditElement.Text.Content):
					if isinstance(self.CurrentEditElement.HostObject, FTHeader): ElementID = 'Header'
					else: ElementID = self.CurrentEditElement.HostObject.ID
					EditComponentInternalName = self.CurrentEditElement.InternalName
					# destroy the TextCtrl (to avoid memory leak) (do this before SendRequest() so that the FT gets fully
					# refreshed by ControlFrame's OnPaint() afterwards)
					self.CurrentEditTextCtrl.Destroy()
					self.CurrentEditElement = self.CurrentEditTextCtrl = None
					# request PHA object in datacore to update text attribute
					self.RequestChangeText(ElementID, EditComponentInternalName, NewValue=TextEntered)
#					vizop_misc.SendRequest(Socket=self.C2DSocketREQ, Command='RQ_FT_ChangeText',
#						Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
#						Element=ElementID, TextComponent=EditComponentInternalName, NewValue=TextEntered)
				else: # no change made, or change rejected; destroy the textctrl widget
					self.CurrentEditTextCtrl.Destroy()
					self.CurrentEditElement = self.CurrentEditTextCtrl = None
			elif CurrentEditBehaviour == 'Choice': # it was a choice editing operation
				# get the option selected by the user
				TextSelected = self.CurrentEditChoice.GetStringSelection()
				# check if any changes made
				if AcceptEditsThisTime and (TextSelected != self.CurrentEditElement.Text.Content):
					if isinstance(self.CurrentEditElement.HostObject, FTHeader):
						ElementID = 'Header'
					else:
						ElementID = self.CurrentEditElement.HostObject.ID
					EditComponentInternalName = self.CurrentEditElement.InternalName
					# get matching XMLName of user's selection
					ChosenXMLName = [i.XMLName for i in self.CurrentEditElement.ObjectChoices if i.HumanName == TextSelected][0]
					# destroy the Choice widget (to avoid memory leak) (do this before SendRequest() so that the FT gets fully
					# refreshed by ControlFrame's OnPaint() afterwards)
					self.CurrentEditChoice.Destroy()
					self.CurrentEditElement = self.CurrentEditChoice = None
					# request PHA object to update choice attribute by sending message through zmq
					vizop_misc.SendRequest(Socket=self.C2DSocketREQ, Command='RQ_FT_ChangeChoice',
						ProjID=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
						Element=ElementID, TextComponent=EditComponentInternalName,
						NewValue=ChosenXMLName)
				else: # no change made, or change rejected; destroy the choice widget
					self.CurrentEditChoice.Destroy()
					self.CurrentEditElement = self.CurrentEditChoice = None
				self.DisplDevice.SetKeystrokeHandlerOnOff(On=True) # turn on keypress shortcut detection in control frame

	def RequestChangeText(self, ElementID, EditComponentInternalName, NewValue):
		# send request to Datacore to update text attribute. Also used for updating value fields
		# at this stage, NewValue has not been validated - could be unacceptable
		vizop_misc.SendRequest(Socket=self.C2DSocketREQ, Command='RQ_FT_ChangeText',
							   Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
							   Element=ElementID, TextComponent=EditComponentInternalName, NewValue=NewValue)

	def RequestChangeChoice(self, ElementID, EditComponentInternalName, NewValue):
		# send request to Datacore to change value in a Choice widget
		# at this stage, NewValue has not been validated - could be unacceptable
		vizop_misc.SendRequest(Socket=self.C2DSocketREQ, Command='RQ_FT_ChangeChoice',
#							   Proj=self.Proj.ID, PHAObj=self.PHAObj.ID, Viewport=self.ID,
							   PHAObj=self.PHAObj.ID, Viewport=self.ID,
							   Element=ElementID, TextComponent=EditComponentInternalName, NewValue=NewValue)


	def ConnectButtonsCanConnectTo(self, StartButton):
		# find and return list of connect buttons that StartButton (a connect button object) can connect to.
		# Include any button it's already connected to
		# First, find which column StartButton belongs to
		StartCol = self.Columns[StartButton.ColIndex]
		# if it's a left button, find all right buttons in the same inter-column strip that haven't met the max no of connections
		if StartButton.IsLeft:
			CanConnectTo = [b for b in self.ConnectButtons if b.ColIndex == StartButton.ColIndex if not b.IsLeft
				if len(JoinedFrom(FT=self, FTObj=b.HostObject, FirstOnly=False)) < b.HostObject.MaxElementsConnectedToThis]
		else: # for a right button, find left buttons in the same column that aren't connected
			CanConnectTo = [b for b in self.ConnectButtons if b.ColIndex == StartButton.ColIndex if b.IsLeft
				if not b.HostObject.ConnectTo]
		return CanConnectTo

	def GetConnectButtonDragInfo(self, StartButton):
		# get and return info needed to process dragging after click on a connect button (StartButton):
		# centre X-coord of the inter-column strip containing StartButton in pixels
		# min X, min Y, max X, max Y of inter-column strip containing StartButton, in pixels
		# First, find which column StartButton belongs to
		StartCol = self.Columns[StartButton.ColIndex]
		# Find the centre X-coord of the inter-column strip containing StartButton
		StripMinXInPx = StartCol.EndXInPx
		StripMinYInPx = min(StartCol.PosYInPx, self.Columns[StartButton.ColIndex + 1].PosYInPx)
		StripMaxXInPx = self.Columns[StartButton.ColIndex + 1].PosXInPx - 1
		NextColumn = self.Columns[StartButton.ColIndex + 1]
		StripMaxYInPx = max(StartCol.PosYInPx + StartCol.SizeYInPx, NextColumn.PosYInPx + NextColumn.SizeYInPx)
		StripCentreXInPx = 0.5 * (StripMinXInPx + StripMaxXInPx)
		return StripCentreXInPx, StripMinXInPx, StripMinYInPx, StripMaxXInPx, StripMaxYInPx


	def ReleaseDisplayDevice(self, DisplDevice, **Args):  # wrap-up actions needed when display device is no longer showing FT
		pass # no specific actions needed (later, might need to store any unstored user inputs, and kill any active widgets)

FTObjectInCore.DefaultViewportType = FTForDisplay # set here (not in FTForDisplay class) due to the order of the
	# class definitions

def JoinedFrom(FT, FTObj, FirstOnly=True): # return list of object(s) connected to the left of FTObj belonging to FT
	# For datacore or display version of FT
	# if FirstOnly, return a list containing only the first object found
	# else, return all objects found as a list
	assert isinstance(FT, (FTObjectInCore, FTForDisplay))
	assert isinstance(FirstOnly, bool)
	# walk over all objects in the FT until we hit one that's connected to FTObj
	FoundObjs = [] # the FT objects connected to FTObj
	for ThisObj in WalkOverAllFTObjs(FT):
#		print("FT3940 JoinedFrom: matching: ", FTObj, ThisObj.ConnectTo)
		if FTObj in ThisObj.ConnectTo:
			FoundObjs.append(ThisObj)
			if FirstOnly:
				break # don't search any more
	return FoundObjs

def WalkOverAllFTObjs(FT):
	# a generator yielding FT objects from FT (Beazley p86). For datacore or display version of FT
	assert isinstance(FT, (FTObjectInCore, FTForDisplay))
	for Col in FT.Columns:
		assert isinstance(Col, (FTColumnInCore, FTColumn))
		for Obj in Col.FTElements:
			yield Obj
	return

def BuildFullElementList(TopEls, *ElLists):
	# Make and return element list comprising fixed and variable elements, starting with TopEls (list of elements)
	# ElLists is zero or more lists of elements, in order required after TopEls
	# Example call: ElList = BuildFullElementList(TopEls, DescriptionCommentEls, ValueEls, ValueCommentEls, ActionItemEls)
	FullElList = TopEls[:] # start with copy of TopEls
	# get starting row number for element lists
	FirstRowInThisList = max([El.Row for El in TopEls]) + 1
	# append elements in each list in ElLists
	for ElList in ElLists:
		MaxRowInThisList = FirstRowInThisList # track the max row index in each element list
		for El in ElList: # append each element in turn, setting correct row number
			El.Row = El.RowBase + FirstRowInThisList
			FullElList.append(El)
			MaxRowInThisList = max(MaxRowInThisList, El.Row)
		FirstRowInThisList = MaxRowInThisList + 1 # update starting row number ready for next element list
	return FullElList

def GetObjFromID(FT, ThisID): # return object in FT with ID=ThisID, or None if no matching object found
	# For datacore or display version of FT
	# redundant, use utilities.ObjectWithID() combined with WalkOverAllFTObjs() instead
	assert isinstance(FT, (FTObjectInCore, FTForDisplay))
	assert isinstance(ThisID, int)
	MatchingObj = None
	for ThisObj in WalkOverAllFTObjs(FT):
		if ThisObj.ID == ThisID:
			MatchingObj = ThisObj
			break # stop searching when match found
	return MatchingObj

