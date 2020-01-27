# -*- coding: utf-8 -*-
# Module: controlframe. This file is part of Vizop. Copyright xSeriCon, 2019
# Encodes the main control and navigation frame seen by the user when a project is open.
# Code tidying done on 1 Dec 2018

"""
The controlframe module contains code for the main Vizop control and navigation screen.
"""

# standard modules needed:
import wx, wx.aui, random, copy
from wx.lib.agw import supertooltip as ToolTip
import xml.etree.ElementTree as ElementTree
from platform import system
# vizop modules needed:
import settings, text, vizop_misc, art, display_utilities, info, utilities, core_classes, projects, project_display
import undo, faulttree, ft_full_report
from display_utilities import UIWidgetItem, UIWidgetPlaceholderItem

# ColourSwatchButtonSize = (60,20) # size for 'change colour' buttons. Not applied in all cases, yet
# HeadingTextPointSize = 13 # default point size of heading font in iWindow
# LabelTextPointSize = 11 # default point size of widget label font in iWindow
KeyPressHash = [] # list of tuples: (keystroke code, handling routines when those keystrokes are detected,
# dict of args to supply to handler)
AllControlFrameShadows = [] # all shadow objects comprising datacore's representation of currently active control
	# frames, both local and remote
UndoChainWaiting = RedoChainWaiting = False # whether un/redo paused in the middle of a chain

def SetupObjSelectionList(ObjectTypeList):
	# populates 'new object' dropdown list by scanning through all available classes of <obj> (Viewport)
	# ObjectTypeList is <obj>Types
	# returns ( list of screen names of <obj> that can be created manually, ditto + kbd shortcut,
	# list of <obj> types in same order as above name lists, hash with keys = shortcut keys; values: corresponding object classes )
	ObjsCanBeCreatedManually = [] # list of object type screen-names
	ObjsCanBeCreatedManuallyWithShortcuts = [] # list of object type screen-names suffixed by keyboard shortcuts
	ObjTypes = []
	ObjKbdHash = {} # keys: shortcut keys; values: corresponding object classes
	KbdSCused = []
	KbdSCspare = list('1234567890') # spare keyboard shortcuts to use in event of clashes
	for e in ObjectTypeList:
		if e.CanBeCreatedManually: # this object type can be created manually, add to the list
			PreferredKbdShortcut = min(chr(126), max(chr(33), e.PreferredKbdShortcut)) # get printable char as kbd shortcut
			# check whether the preferred shortcut is already assigned; if so, provide one from list of spares (0th or 1st item)
			if PreferredKbdShortcut in KbdSCused:
				spareIndex = int((KbdSCspare + [''])[0] == PreferredKbdShortcut)
					# which item to use, 0 or 1 (use 1 if 0th already assigned)
				ksc = (KbdSCspare + ['', ''])[spareIndex] # get a spare shortcut, or '' if all used up
				if len(KbdSCspare) > spareIndex: del KbdSCspare[spareIndex] # delete the one used from the list of spares
			else: ksc = PreferredKbdShortcut
			# set up how shortcut will be displayed: currently after a | unless blank
			if ksc == '': kscDisplay = ''
			else:
				kscDisplay = ' | ' + ksc
				KbdSCused += [ksc]
				ObjKbdHash[ksc] = e
			ObjsCanBeCreatedManually += [e.HumanName]
			ObjsCanBeCreatedManuallyWithShortcuts += [e.HumanName + kscDisplay]
			ObjTypes.append(e)
	return (ObjsCanBeCreatedManually, ObjsCanBeCreatedManuallyWithShortcuts, ObjTypes, ObjKbdHash)

class VizopTalksPriority(object): # defines a priority level for a VizopTalks message
	PriorityList = [] # an ordered list of priorities will be built here
	ColSchemes = ['Neutral', 'Moderate', 'Intense']

	def __init__(self, MinLife=None, Timeout=None, ColScheme='Neutral', HasTipList=False):
		assert isinstance(MinLife, int) or (MinLife is None)
		if isinstance(MinLife, int): assert MinLife >= 0
		assert isinstance(Timeout, int) or (Timeout is None)
		if isinstance(Timeout, int): assert Timeout >= 0
		assert ColScheme in VizopTalksPriority.ColSchemes
		assert isinstance(HasTipList, bool)
		VizopTalksPriority.PriorityList.append(self) # add new priority to the class's list
		self.MinLife = MinLife
		self.Timeout = Timeout
		self.ColScheme = ColScheme
		self.HasTipList = HasTipList
		if self.HasTipList: self.TipList = [] # list of tips available for this priority

# create VizopTalks message priority levels. They must be defined below in priority order, lowest first
VTMinLife = 10000  # lifetime of "minimum life" messages, in ms
VTTipTimeout = 30000  # time after which tips change
LowestPriority = VizopTalksPriority()
StatusPriority = VizopTalksPriority()
Tip_GeneralPriority = VizopTalksPriority(Timeout=VTTipTimeout, HasTipList=True)
Tip_Context_GeneralPriority = VizopTalksPriority(Timeout=VTTipTimeout, HasTipList=True)
Tip_Context_SpecificPriority = VizopTalksPriority(HasTipList=True)
ConfirmationPriority = VizopTalksPriority(Timeout=VTTipTimeout)
InstructionPriority = VizopTalksPriority(Timeout=VTTipTimeout, ColScheme='Moderate')
CautionPriority = VizopTalksPriority(MinLife=VTMinLife, ColScheme='Moderate')
OptionPriority = VizopTalksPriority(MinLife=VTMinLife, ColScheme='Moderate')
WarningPriority = VizopTalksPriority(MinLife=VTMinLife, ColScheme='Intense')
QuestionPriority = VizopTalksPriority(MinLife=VTMinLife, ColScheme='Intense')
CriticalPriority = VizopTalksPriority(MinLife=VTMinLife, ColScheme='Intense')

class VizopTalksMessage(object): # defines a message that can be shown in VizopTalks

	def __init__(self, Title='', MainText='', Buttons=[], Priority=LowestPriority):
		assert isinstance(Title, str)
		assert isinstance(MainText, str)
		assert isinstance(Buttons, list)
		self.Title = Title
		self.MainText = MainText
		self.Buttons = Buttons[:]
		self.Priority = Priority
		self.Shown = False # for tips, whether the tip has been shown to the user in this Vizop instance
		self.AppliesToCurrentContext = False # For tips. False means the tip is left over from a different user context

# make function to get priority index (int) of any priority. Low index = low priority
PriorityIndex = lambda p: VizopTalksPriority.PriorityList.index[p]

class ControlFrame(wx.Frame):
	# Define the main control frame, with panels: Edit, Control View, VizopTalks

	class VTPanel(wx.Window):
		# define the VizopTalks panel
		# In BackgColourTable, keys must match ColSchemes in class VizopTalksPriority
		BackgColourTable = {'Neutral': 'white', 'Moderate': 'wheat', 'Intense': 'yellow'}

		def __init__(self, parent, ID=-1, size=(250,100), ColScheme=None):
			wx.Window.__init__(self, parent, ID, (0,0), size, wx.RAISED_BORDER)
			self.CurrentMessage = None # currently shown message; a VizopTalksMessage instance or None if no current message
			self.ColScheme = ColScheme
			self.SetBackgroundColour("white")
			self.SetMinSize(size)
			# set up timers
			self.MinLifeTimer = wx.Timer(self)
			self.TimeoutTimer = wx.Timer(self)
			self.Bind(wx.EVT_TIMER, self.OnMinLifeTimer, self.MinLifeTimer)
			self.Bind(wx.EVT_TIMER, self.OnTimeoutTimer, self.TimeoutTimer)
			self.Bind(wx.EVT_PAINT, self.OnPaintVT)

		def OnPaintVT(self, evt): # called when the system is refreshing the VizopTalks panel
			dc = wx.PaintDC(self) # this is needed even though not used; see Rappin p368
			# redraw the current message
			if self.CurrentMessage:
				self.RenderMessage(Title=self.CurrentMessage.Title,
					MainText=self.CurrentMessage.MainText, Buttons=self.CurrentMessage.Buttons,
					Priority=self.CurrentMessage.Priority)

		def RenderMessage(self, Title='', MainText='', Buttons=[], Priority=LowestPriority):
			# draw message in VizopTalks panel. Draws texts and background, but not buttons. Starts timers if required.
			# set up drawing environment
			w, h = self.GetClientSize()
			dc = wx.BufferedDC(wx.ClientDC(self))
			BackgColour = ControlFrame.VTPanel.BackgColourTable[Priority.ColScheme]
			dc.SetBackground(wx.Brush(BackgColour))
			dc.Clear()
			# draw title
			dc.SetFont(wx.Font(16, wx.SWISS, wx.NORMAL, wx.NORMAL))
			if (Title.strip() == ''):
				(titlew, titleh) = dc.GetTextExtent('M')  # dummy to leave gap if title empty
			else:
				(titlew, titleh) = dc.GetTextExtent(Title)
			dc.DrawText(Title, 0, 0)
			# draw main text
			MainTextFont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL)  # sets the font
			dc.SetFont(MainTextFont)
			dc.DrawText(text.WrappedText(MainText, MainTextFont, self.GetClientSize()[0])[0], 0, titleh)
			# start timers if required
			if Priority.MinLife:
				if self.MinLifeTimer.IsRunning(): self.MinLifeTimer.Stop()
				self.MinLifeTimer.StartOnce(Priority.MinLife)
			if Priority.Timeout:
				if self.TimeoutTimer.IsRunning(): self.TimeoutTimer.Stop()
				self.TimeoutTimer.StartOnce(Priority.Timeout)

		def SubmitVizopTalksMessage(self, Title='', MainText='', Buttons=[], Priority=CriticalPriority):
			# call this procedure to send a message or tip to VizopTalks. Implements flowscheme 1 in specification.
			# Tip_Context_General tips are assumed to be relevant to the current user context.
			assert isinstance(Title, str)
			assert isinstance(MainText, str)
			assert isinstance(Buttons, list)
			assert Priority in VizopTalksPriority.PriorityList
			self.CurrentMessage = None # currently shown message; a VizopTalksMessage instance or None if no current message
			self.MessageBuffer = None # next message to be displayed when current message times out
			# put new msg into a message object
			SuppliedMessage = VizopTalksMessage(Title=Title, MainText=MainText, Buttons=Buttons, Priority=Priority)
			DisplayNewMessage = False # whether to display supplied message now
			# step 1: if the message is a tip, store it in the relevant tip list
			if Priority.HasTipList:
				SuppliedMessage.Shown = False
				if Priority in (Tip_Context_GeneralPriority, Tip_Context_SpecificPriority):
					SuppliedMessage.AppliesToCurrentContext = True
				# store the tip if it's not already in the list
				if Title not in ([t.Title for t in Priority.TipList]) and\
					(MainText not in [t.MainText for t in Priority.TipList]):
					Priority.TipList.append(SuppliedMessage)
			# step 2: check if there is currently any message displayed
			if self.CurrentMessage:
				# step 3: is MinLife timer running? If so, store the new message and exit
				if self.MinLifeTimer.IsRunning():
					self.MessageBuffer = SuppliedMessage
					DisplayNewMessage = False
				else:
					# step 4: check if Timeout timer is running
					if self.TimeoutTimer.IsRunning():
						# step 5: check if new message priority is higher than existing message
						if PriorityIndex(Priority) > PriorityIndex(self.CurrentMessage.Priority):
							self.TimeoutTimer.Stop()
							DisplayNewMessage = True
						else:
							self.MessageBuffer = SuppliedMessage
							DisplayNewMessage = False
					else: # step 4 'no' branch
						DisplayNewMessage = True
			else: # step 2 'no' branch
				DisplayNewMessage = True
			# step 10: display the message
			if DisplayNewMessage:
				self.CurrentMessage = copy.copy(SuppliedMessage)
				self.RenderMessage(Title=Title, MainText=MainText, Buttons=Buttons, Priority=Priority)
				# mark tip as shown, if it's a tip (assumes we just appended this tip to the end of the list)
				if Priority.HasTipList: Priority.TipList[-1].Shown = True
				# old code for adding buttons required, for use as future starting point. Destroy any active buttons first
				if 'Unlock' in Buttons: # show 'Unlock recording' button
					self.UnlockButton = wx.Button(self, -1, _('Centred'), pos=(10, h - 30))
					self.UnlockButton.Bind(wx.EVT_LEFT_UP, frame1.OnUnlockButton)
					# use 'left button up' event because the button persists if normal wx.EVT_BUTTON used

		def OnMinLifeTimer(self, Event): # handle timeout of VizopTalks MinLife timer. Implements flowscheme method 2
			# in specification
			ShowBufferedMessage = False
			# step 1: any message in message buffer?
			if self.MessageBuffer:
				# step 2: is the buffered message higher priority than the existing message?
				# we use getattr() in case there's no CurrentMessage
				if PriorityIndex(self.MessageBuffer.Priority) > \
					PriorityIndex(getattr(self.CurrentMessage, Priority, LowestPriority)):
					ShowBufferedMessage = True
				else: # step 2 "No" branch
					# step 3: Is TimeoutTimer running?
					if not self.TimeoutTimer.IsRunning():
						ShowBufferedMessage = True
			else: # step 1 "no" branch
				# step 10: is TimeoutTimer running?
				if not self.TimeoutTimer.IsRunning():
					# step 11: Any context_general tips waiting?
					AvailContextGeneralTips = [t for t in Tip_Context_GeneralPriority.TipList
						if (t.AppliesToCurrentContext and not t.Shown)]
					if AvailContextGeneralTips: # tips are available; choose one at random
						TipToDisplay = random.choice(AvailContextGeneralTips)
						self.CurrentMessage = TipToDisplay
						self.RenderMessage(Title=TipToDisplay.Title, MainText=TipToDisplay.MainText,
							Buttons=TipToDisplay.Buttons, Priority=TipToDisplay.Priority)
						TipToDisplay.Shown = True
					else: # step 11 "no" branch
						# step 12: Any general tips waiting?
						AvailGeneralTips = [t for t in Tip_GeneralPriority.TipList if not t.Shown]
						if AvailGeneralTips: # tips are available; choose one at random
							TipToDisplay = random.choice(AvailGeneralTips)
							self.CurrentMessage = TipToDisplay
							self.RenderMessage(Title=TipToDisplay.Title, MainText=TipToDisplay.MainText,
								Buttons=TipToDisplay.Buttons, Priority=TipToDisplay.Priority)
							TipToDisplay.Shown = True
			# step 20: display the buffered message
			if ShowBufferedMessage:
				self.CurrentMessage = copy.copy(self.MessageBuffer)
				self.RenderMessage(Title=self.MessageBuffer.Title, MainText=self.MessageBuffer.MainText,
					Buttons=self.MessageBuffer.Buttons, Priority=self.MessageBuffer.Priority)
				self.MessageBuffer = None # clear buffer

		def OnTimeoutTimer(self, Event): # handle timeout of VizopTalks Timeout timer. Implements flowscheme method 3
			# in specification
			ShowBufferedMessage = False
			# step 1: any message in message buffer?
			if self.MessageBuffer: # show the message
				self.CurrentMessage = copy.copy(self.MessageBuffer)
				self.RenderMessage(Title=self.MessageBuffer.Title, MainText=self.MessageBuffer.MainText,
								   Buttons=self.MessageBuffer.Buttons, Priority=self.MessageBuffer.Priority)
				self.MessageBuffer = None # clear buffer
			else:
				# step 2: Any context_general tips waiting?
				AvailContextGeneralTips = [t for t in Tip_Context_GeneralPriority.TipList
										   if (t.AppliesToCurrentContext and not t.Shown)]
				if AvailContextGeneralTips: # tips are available; choose one at random
					TipToDisplay = random.choice(AvailContextGeneralTips)
					self.CurrentMessage = TipToDisplay
					self.RenderMessage(Title=TipToDisplay.Title, MainText=TipToDisplay.MainText,
									   Buttons=TipToDisplay.Buttons, Priority=TipToDisplay.Priority)
					TipToDisplay.Shown = True
				else: # step 2 "no" branch
					# step 3: Any general tips waiting?
					AvailGeneralTips = [t for t in Tip_GeneralPriority.TipList if not t.Shown]
					if AvailGeneralTips:  # tips are available; choose one at random
						TipToDisplay = random.choice(AvailGeneralTips)
						self.CurrentMessage = TipToDisplay
						self.RenderMessage(Title=TipToDisplay.Title, MainText=TipToDisplay.MainText,
										   Buttons=TipToDisplay.Buttons, Priority=TipToDisplay.Priority)
						TipToDisplay.Shown = True
					else: # step 3 "no" branch: clear currently displayed message
						self.CurrentMessage = VizopTalksMessage()
						self.RenderMessage(Title='', MainText='', Buttons=[], Priority=LowestPriority)

		def ChangeUserContext(self): # call this method when the user context changes. It sets all context tips to
			# "Not relevant" and clears any currently shown context tip. Implements flowscheme 4 in specification
			# step 1: set all context_general tips to "not relevant"
			for ThisTip in Tip_Context_GeneralPriority.TipList: ThisTip.AppliesToCurrentContext = False
			# step 2: delete all context_specific tips
			Tip_Context_SpecificPriority.TipList = []
			# step 3: are we currently showing a Tip_Context_General or Tip_Context_Specific?
			if getattr(self.CurrentMessage, Priority, LowestPriority) in [Tip_Context_GeneralPriority, Tip_Context_SpecificPriority]:
				# step 4: stop timers
				if self.TimeoutTimer.IsRunning(): self.TimeoutTimer.Stop()
				if self.MinLifeTimer.IsRunning(): self.MinLifeTimer.Stop()
				# step 5: go to Method 3
				self.OnTimeoutTimer(Event=None)

		def FinishedWithCurrentMessage(self): # call this method to clear a message with no MinLife set
			# (e.g. an InstructionPriority message) when it's no longer required. Implements flowscheme 5 in specification
			if not self.MinLifeTimer.IsRunning():
				if self.TimeoutTimer.IsRunning(): self.TimeoutTimer.Stop()
				self.OnTimeoutTimer(Event=None)

	class ControlPanel(wx.Panel):
		# Defines the Control panel, for widgets that control the project, in the Control frame
#		WidgClassesDontBindKeyHandler = [wx.TextCtrl, wx.ComboBox] # don't bind global keypress handler to these widget classes, else they break

		def OnNewPHAModelListbox(self, Event): # handle click on PHAModel type from 'new PHA model' list box
			self.TopLevelFrame.DoNewPHAModelCommand(self.CurrentProj, PHAModelClass=
				self.PHAModelTypesInNameOrder[self.PHAModelsAspect.NewPHAModelTypesList.Widget.GetSelection()])
			self.PHAModelsAspect.NewPHAModelTypesList.Widget.SetSelection(wx.NOT_FOUND) # clear selection
			# (a workaround for the problem that re-clicking on the already selected list item doesn't raise an event next time)

		def OnNavigateBackButton(self, Event=None, **Args): print("CF320 back button clicked")
		def OnNavigateForwardButton(self, Event=None, **Args): pass

#		def HandleColourSwatchClick(self, ParentFrame, OldColour, SwatchWidget):
			# handle colour change request. Returns (WhetherChanged <boolean>, (new r,g,b))
#			# ParentFrame: the wx.Frame to be used as parent of the colour picker dialogue
#			UserSelColour = wx.GetColourFromUser(ParentFrame, OldColour) # use standard colour picker dialogue
#			if UserSelColour.IsOk(): # user successfully chose a colour
#				NewColour = (UserSelColour.red, UserSelColour.green, UserSelColour.blue)
#				SwatchWidget.SetBackgroundColor(UserSelColour)
#				if NewColour != OldColour: return (True, NewColour)
#			return (False, OldColour)

#		def OnETcontentText(self, event): # handle change of text in element during editing.
#			# Copied from T-u-t-i as-is, not edited yet
#
#			def PerformUndoChangeElementText(Proj, DidWhat, **Args):
#				Args['El'].Text.Content = Args['OldContent']
#				self.PreviousLeanText = Args['PrevLeanText']
#				self.ETcontentTextSelection = Args['PrevSelection']
#				self.ETcontentText_Updated = Args['PrevUpdatedFlag']
#
#			UndoChain = 0 # how many undo items created
#			SkippingPasteEvent = False # flag used for bug workaround, see below
#			# First, identify the type of change made: insertion, deletion or replacement
#			(PrevCursorL, PrevCursorR) = self.ETcontentTextSelection # find the left and right ends of the selection before change made
#			NewContent = self.ETcontentText.GetValue() # retrieve current value of text widget
#			NowCursor = self.ETcontentText.GetInsertionPoint() # retrieve current cursor position
#			if PrevCursorL == PrevCursorR: # cursor was not extended, so it's an insertion or deletion
#				if len(NewContent) > len(self.PreviousLeanText): # text is now longer, so it's an insertion
#					Change = 'Insertion'
#					NoOfChars = len(NewContent) - len(self.PreviousLeanText) # no of chars inserted
#					ChangePos = PrevCursorL
#					ReplacementString = NewContent[PrevCursorL:][:NoOfChars] # chars to insert
#				else: # it's a deletion; work out whether done with backspace key or delete key
#					Change = 'Deletion'
#					ReplacementString = ''
#					NoOfChars = len(self.PreviousLeanText) - len(NewContent) # no of chars deleted (could be >1 if chars were highlighted)
#					if (len(self.PreviousLeanText) - PrevCursorL) == (len(NewContent) - NowCursor): # deletion was before cursor using Backspace
#						ChangePos = NowCursor
#					else: # Delete key used
#						ChangePos = PrevCursorL
#			else: # cursor extended; previously highlighted characters have been deleted or replaced
#				Change = 'Replacement'
#				NoOfChars = PrevCursorR - PrevCursorL # no of chars removed
#				ChangePos = PrevCursorL
#				ReplacementString = ChopFromEnd(NewContent[PrevCursorL:], len(self.PreviousLeanText) - PrevCursorR) # chars to insert
#				SkippingPasteEvent = (len(ReplacementString) > 0) and not self.ETcontentText.SkippedLastPasteEvent
#					# workaround bugs in GetValue(): returns wrong value 1st time after paste, and paste double-triggers EVT_TEXT
#				self.ETcontentText.SkippedLastPasteEvent = SkippingPasteEvent
#			if not SkippingPasteEvent:
#				# do the update in the selected elements
#				for el in self.CurrentProj.CurrentElements:
#					UndoChain = AddToUndoList(self.CurrentProj, 'Change-Element-Text', Element=el, OldContent=el.Text.Content, PrevLeanText=self.PreviousLeanText,
#						PrevUpdatedFlag=self.ETcontentText_Updated, PrevSelection=self.ETcontentTextSelection,
#						ChainCount=UndoChain, UndoOnCancel=self.CurrentProj.UndoOnCancelIndex, UndoHandler=PerformUndoChangeElementText)
#					elements.text.UpdateStoredElementText(el, Change, ChangePos, NoOfChars, ReplacementString)
#				self.PreviousLeanText = self.ETcontentText.GetValue() # store updated textctrl value for comparison next time
#				self.ETcontentText_Updated = False # store flag used by CursorMove test routine
#				self.ETcontentTextSelection = (NowCursor, NowCursor) # store current cursor location for comparison next time
#				# refresh display
#				rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=self.CurrentProj.CurrentElements,
#					Editing=self.CurrentProj.CurrentElements, zCoordsChanged=[])
#
#		def UpdateTextFormatNowWidgets(self, RichStr, CursorPos): # refresh values of all "now" text format widgets
#			# according to current cursor position (counting visible chars) in RichStr (which can contain embedded format commands)
#			# Copied from Vizop as-is, not edited yet
#			ThisTextObject = self.CurrentProj.CurrentElements[0].Text
#			# set font name widget
#			FontNow = elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Font')
#			self.ETcharNowFontText.Widget.SetStringSelection(FontNow)
#			# set font scale widget
#			ScaleNow = elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Scale')
#			self.ETcharNowSizeText.Widget.SetValue(str(ScaleNow))
#			# set font colour widget
#			ColourNow = elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Colour')
#			self.ETcharNowColourSwatch.Widget.SetBackgroundColour(ColourNow)
#			# set checkboxes
#			self.ETcharNowBoldCheck.Widget.SetValue(elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Bold-On'))
#			self.ETcharNowUnderlineCheck.Widget.SetValue(elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Underlining-On'))
#			self.ETcharNowItalicCheck.Widget.SetValue(elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Italics-On'))
#			self.ETcharNowStandoutCheck.Widget.SetValue(elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Standout-On'))
#			# set sub/superscript checkboxes
#			VertOffsetNow = elements.text.CurrentFormatStatus(ThisTextObject, RichStr, CursorPos, FmtParm='Vert-Offset')
#			self.ETcharNowSuperscriptCheck.Widget.SetValue(VertOffsetNow > 0)
#			self.ETcharNowSubscriptCheck.Widget.SetValue(VertOffsetNow < 0)
#
#		def OnETcontentText_CursorMove(self, event): # called when cursor is moved in ETcontentText by keyboard or mouse
#			# Copied from Tuti as-is, not edited yet
#			if not self.ETcontentText_Updated: # check whether text was changed by the keypress event; if not:
#				(Left, Right) = self.ETcontentText.Widget.GetSelection() # get selection (start, end)
#				# if selection is newly extended, check whether it has been extended forwards or backwards
#				if (Right > Left) and (self.ETcontentTextSelection[0] == self.ETcontentTextSelection[1]):
#					ExtendForward = (Right > self.ETcontentTextSelection[1])
#				else: ExtendForward = True # default for other cases
#				self.ETcontentTextSelection = (Left, Right) # store (selection start, end) tuple
#			self.ETcontentText_Updated = False # reset flag indicating whether text changed since last cursor move event
#			# change to Default or Selected Aspect of ControlPanel if required
#			CurrentAspect = getattr(self, 'EditTextModeAspect', 'Default')
#			# FIXME in the next line, Right and Left are unassigned of the if-then above is not executed
#			if (Right > Left) and (CurrentAspect != 'Selected'): # some chars are selected; switch ControlPanel to 'selected format' aspect
#				self.GotoControlPanelAspect('Edit-Element-Text', Aspect='Selected', NextMode=self.NextEditPanelMode, NextModeArgs=self.NextEditPanelModeArgs,
#										ResetCursorPos=False)
#				# focus on text entry box and set cursor pos
#				SetTextCtrlFocusAndInsertionPoint(self.ETcontentText, self.ETcontentTextSelection, ExtendForward)
#			elif (Right == Left) and (CurrentAspect != 'Default'): # no chars are selected; switch ControlPanel to 'default format' aspect
#				self.GotoControlPanelAspect('Edit-Element-Text', Aspect='Default', NextMode=self.NextEditPanelMode, NextModeArgs=self.NextEditPanelModeArgs,
#										ResetCursorPos=False)
#				SetTextCtrlFocusAndInsertionPoint(self.ETcontentText, self.ETcontentTextSelection, ExtendForward)
#
#		def CursorIsExtended(self, SelectionTuple): # returns True if TextCtrl cursor is extended
#			return (SelectionTuple[0] != SelectionTuple[1])
#
#		def OnETcharNowFontText(self, event): # handle request for change of current element text font
#			# Copied from T-u-t-i as-is, not edited yet
#			UndoChain = 0
#			if self.CursorIsExtended(self.ETcontentTextSelection): # some text is highlighted, change font within the highlighted text
#				El = self.CurrentProj.CurrentElements[0] # only work on 1st selected Element
#				NewFont = self.ETcharNowFontText.GetStringSelection()
#				OldRichStr = El.Text.Content
#				NewRichStr = elements.text.MidTextFormatChange(El.Text, OldRichStr, self.ETcontentTextSelection[0], \
#					self.ETcontentTextSelection[1], NewFont, \
#					CommandOnOff=True, StartCommand='Font', StopCommand='Font-Default', StripCommands=['Font', 'Font-Default'])
#				UndoChain = AddToUndoList(self.CurrentProj, 'Change-Element-Text-MidtextFormat', Elements=[El],
#					OldValue=OldRichStr, NewValue=NewRichStr, ChainCount=UndoChain,
#					UndoOnCancel=self.CurrentProj.UndoOnCancelIndex, UndoHandler=self.PerformUndoCETMTF)
#				El.Text.Content = NewRichStr
#				rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=[El], Editing=self.CurrentProj.CurrentElements)
#
#		def OnETcharNowSizeText(self, event): # handle request for change of font size midtext
#			# Copied from T-u-t-i as-is, not edited yet
#			UndoChain = 0
#			El = self.CurrentProj.CurrentElements[0] # only work on 1st selected Element
#			NewSize = max(elements.text.MinElementTextVertFactor, min(str2int(self.ETcharNowSizeText.GetValue(), 100), elements.text.MaxElementTextVertFactor))
#			self.ETcharNowSizeText.SetValue(str(NewSize)) # write back valid value to textbox
#			if self.CursorIsExtended(self.ETcontentTextSelection): # some text is highlighted, change font within the highlighted text
#				OldRichStr = El.Text.Content
#				NewRichStr = elements.text.MidTextFormatChange(El.Text, OldRichStr, self.ETcontentTextSelection[0], \
#					self.ETcontentTextSelection[1], NewSize, \
#					CommandOnOff=True, StartCommand='Scale', StopCommand='No-Scale', StripCommands=['Scale', 'No-Scale'])
#				UndoChain = AddToUndoList(self.CurrentProj, 'Change-Element-Text-MidtextFormat', Elements=[El],
#					OldValue=El.Text.Content, NewValue=NewRichStr, ChainCount=UndoChain,
#					UndoOnCancel=self.CurrentProj.UndoOnCancelIndex, UndoHandler=self.PerformUndoCETMTF)
#				El.Text.Content = NewRichStr
#				rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=[El], Editing=self.CurrentProj.CurrentElements)
#
#		def OnETcharNowColourSwatch(self, event): # handle request for change of text colour midtext. Untested
#			# Copied from T-u-t-i as-is, not edited yet
#			UndoChain = 0
#			if self.CursorIsExtended(self.ETcontentTextSelection): # some text is highlighted, change colour within the highlighted text
#				OldRichStr = self.CurrentProj.CurrentElements[0].Text.Content[:]
#				OldColour = elements.text.CurrentFormatStatus(self.CurrentProj.CurrentElements[0].Text, OldRichStr, self.ETcontentTextSelection[0], 'Colour')
#				UserSelColour = wx.GetColourFromUser(self.TopLevelFrame, OldColour) # use standard colour picker dialogue
#				if UserSelColour.IsOk(): # user successfully chose a colour
#					NewColour = (UserSelColour.red, UserSelColour.green, UserSelColour.blue)
#					NewRichStr = elements.text.MidTextFormatChange(self.CurrentProj.CurrentElements[0].Text, OldRichStr, self.ETcontentTextSelection[0], \
#						self.ETcontentTextSelection[1], NewColour, CommandOnOff=True, StartCommand='Colour', StopCommand='Colour-Default', \
#						StripCommands=['Colour', 'Colour-Default'])
#					for El in self.CurrentProj.CurrentElements:
#						UndoChain = AddToUndoList(self.CurrentProj, 'Change-Element-Text-MidtextFormat', Elements=[El],
#							OldValue=El.Text.Content, NewValue=NewRichStr, ChainCount=UndoChain,
#							UndoOnCancel=self.CurrentProj.UndoOnCancelIndex, UndoHandler=self.PerformUndoCETMTF)
#						El.Text.Content = NewRichStr
#					rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=self.CurrentProj.CurrentElements, Editing=self.CurrentProj.CurrentElements)
#					self.ETcharNowColourSwatch.Widget.SetBackgroundColour(UserSelColour) # set button colour
#
#		def ChangeTextBIU(self, Proj, Elements, StartCommand, StopCommand, OnOff): # block of code for bold, underlining, italics or standout on/off midtext
#			# Copied from Vizop as-is, not edited yet
#			UndoChain = 0
#			if self.CursorIsExtended(self.ETcontentTextSelection): # some text is highlighted, toggle B/I/U within the highlighted text
#				OldRichStr = Elements[0].Text.Content
#				NewRichStr = elements.text.MidTextFormatChange(Elements[0].Text, OldRichStr, self.ETcontentTextSelection[0], \
#					self.ETcontentTextSelection[1], None, CommandOnOff=OnOff, StartCommand=StartCommand, \
#					StopCommand=StopCommand, StripCommands=[StartCommand, StopCommand])
#				for El in Elements:
#					UndoChain = AddToUndoList(Proj, 'Change-Element-Text-MidtextFormat', Elements=[El],
#						OldValue=El.Text.Content, NewValue=NewRichStr, ChainCount=UndoChain,
#						UndoOnCancel=Proj.UndoOnCancelIndex, UndoHandler=self.PerformUndoCETMTF)
#					El.Text.Content = NewRichStr
#				rendering.UpdateProjectDisplay(Proj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=Elements, Editing=Elements)
#
#		def ChangeTextSuperSub(self, Proj, Elements, SuperSubStatus, WasOpposite): # block of code for super/subscript on/off midtext
#			# SuperSubStatus: 'Super', 'Sub' or 'Normal'
#			# WasOpposite: True if text was previously the opposite status (subscript/superscript)
#			# Copied from T-u-t-i as-is, not edited yet
#			SuperscriptVertOffset = 80 # % of line spacing by which superscript text is offset vertically
#			SubscriptVertOffset = -30
#			SuperscriptScaleFactor = 0.7 # fraction of normal character size for super/subscript text
#			CancelSSScaleFactor = 1.429 # 1/SuperscriptScaleFactor
#			UndoChain = 0
#			if self.CursorIsExtended(self.ETcontentTextSelection): # some text is highlighted, toggle super/sub within the highlighted text
#				OldRichStr = Elements[0].Text.Content
#				ScaleNow = elements.text.CurrentFormatStatus(Elements[0].Text, OldRichStr, self.ETcontentTextSelection[0], FmtParm='Scale')
#				if ScaleNow is None: ScaleNow = 100 # handle 'no scale defined' return from CurrentFormatStatus(); should be redundant
#				# insert Vert-Offset command
#				NewRichStr = elements.text.MidTextFormatChange(Elements[0].Text, OldRichStr, self.ETcontentTextSelection[0], \
#					self.ETcontentTextSelection[1], {'Super': SuperscriptVertOffset, 'Sub': SubscriptVertOffset, 'Normal': 0}[SuperSubStatus], \
#					CommandOnOff=(SuperSubStatus in ['Super', 'Sub']), StartCommand='Vert-Offset', \
#					StopCommand='No-Vert-Offset', StripCommands=['Vert-Offset', 'No-Vert-Offset'])
#				# insert 'change size' command
#				if WasOpposite: NewScaleFactor = 1 # don't scale down if we were already scaled down
#				elif (SuperSubStatus in ['Super', 'Sub']): NewScaleFactor = SuperscriptScaleFactor
#				else: NewScaleFactor = CancelSSScaleFactor
#				NewRichStr = elements.text.MidTextFormatChange(Elements[0].Text, NewRichStr, self.ETcontentTextSelection[0], self.ETcontentTextSelection[1],  \
#					NewScaleFactor * ScaleNow, CommandOnOff=(SuperSubStatus in ['Super', 'Sub']) or (ScaleNow != 100), StartCommand='Scale', \
#					StopCommand='No-Scale', StripCommands=['Scale', 'No-Scale'])
#				for El in Elements:
#					UndoChain = AddToUndoList(Proj, 'Change-Element-Text-MidtextFormat', Elements=[El],
#						OldValue=El.Text.Content, NewValue=NewRichStr, ChainCount=UndoChain,
#						UndoOnCancel=Proj.UndoOnCancelIndex, UndoHandler=self.PerformUndoCETMTF)
#					El.Text.Content = NewRichStr
#				rendering.UpdateProjectDisplay(Proj, [Proj.DisplayDevice[0]], ElementsChanged=Elements, Editing=Elements)
#
#		def OnETcharNowBoldCheck(self, event): # handle request for change of bold status midtext
#			self.ChangeTextBIU(self.CurrentProj, self.CurrentProj.CurrentElements, 'Bold-On', 'Bold-Off', OnOff=self.ETcharNowBoldCheck.IsChecked())
#
#		def OnETcharNowUnderlineCheck(self, event): # handle request for change of underlining status midtext
#			self.ChangeTextBIU(self.CurrentProj, self.CurrentProj.CurrentElements, 'Underlining-On', 'Underlining-Off', \
#				OnOff=self.ETcharNowUnderlineCheck.IsChecked())
#
#		def OnETcharNowItalicCheck(self, event): # handle request for change of italics status midtext
#			self.ChangeTextBIU(self.CurrentProj, self.CurrentProj.CurrentElements, 'Italics-On', 'Italics-Off', \
#				OnOff=self.ETcharNowItalicCheck.IsChecked())
#
#		def OnETcharNowSuperscriptCheck(self, event): # handle request for change of superscript status midtext
#			OnOff = self.ETcharNowSuperscriptCheck.IsChecked()
#			self.ChangeTextSuperSub(self.CurrentProj, self.CurrentProj.CurrentElements, {True: 'Super', False: 'Normal'}[OnOff], \
#				self.ETcharNowSubscriptCheck.IsChecked())
#			if OnOff: self.ETcharNowSubscriptCheck.SetValue(False) # uncheck subscript checkbox
#
#		def OnETcharNowSubscriptCheck(self, event): # handle request for change of subscript status midtext
#			OnOff = self.ETcharNowSubscriptCheck.IsChecked()
#			self.ChangeTextSuperSub(self.CurrentProj, self.CurrentProj.CurrentElements, {True: 'Sub', False: 'Normal'}[OnOff], \
#				self.ETcharNowSuperscriptCheck.IsChecked())
#			if OnOff: self.ETcharNowSuperscriptCheck.SetValue(False) # uncheck superscript checkbox
#
#		def OnETcharNowStandoutCheck(self, event): # handle request for change of standout status midtext
#			self.ChangeTextBIU(self.CurrentProj, self.CurrentProj.CurrentElements, 'Standout-On', 'Standout-Off', \
#				OnOff=self.ETcharNowStandoutCheck.IsChecked())
#
#		def OnETcharFinishedButton(self, Event=None): # handle click on 'finished editing element text' button
#			self.GotoControlPanelAspect(self.NextEditPanelMode, **self.NextEditPanelModeArgs)
#
#		def OnETlineSpacingText(self, Event=None):
#			pass
#
#		def OnETcharBaseFontText(self, event): # handle request for change of default element text font
#			NewFont = self.ETcharBaseFontText.GetStringSelection()
#			# update default font in all selected elements
#			# copied from Tuti, not edited much yet
#			Redraw = [] # elements to redraw
#			for el in self.CurrentProj.CurrentElements:
#				if (NewFont != el.Text.Font):
#					el.Text.Font = NewFont
#					Redraw.append(el)
#			rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=Redraw, Editing=self.CurrentProj.CurrentElements)
#
#		def UpdateTextSizeWidget(self, NewSize): # write current text point size value to ControlPanel widget. NewSize = integer value that should be displayed
#			self.ETcharBaseSizeText.SetValue(str(NewSize)) # write back valid value to textbox
#
#		def OnETcharBaseSizeText(self, event): # handle request for change of default element text point size
#			NewSize = max(elements.text.MinElementTextPointSize, \
#				min(str2int(self.ETcharBaseSizeText.GetValue(), elements.text.DefaultElementTextPointSize), elements.text.MaxElementTextPointSize))
#			self.UpdateTextSizeWidget(NewSize) # write back valid value to textbox
#			# update default font size in all selected elements
#			Redraw = [] # elements to redraw
#			for el in self.CurrentProj.CurrentElements:
#				if (NewSize != el.Text.PointSize):
#					el.Text.PointSize = NewSize
#					el.Text.ParentSizeBasis = el.TextSizeBasis() # store basis size of ThisEl, used to calculate actual text size when ThisEl is resized
#					Redraw.append(el)
#			rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=Redraw, Editing=self.CurrentProj.CurrentElements)
#
#		def OnETcharBaseColourSwatch(self, event): # click on 'text default colour' button
#			OldColour = self.CurrentProj.CurrentElements[0].Text.Colour
#			UserSelColour = wx.GetColourFromUser(self.TopLevelFrame, OldColour) # use standard colour picker dialogue
#			if UserSelColour.IsOk(): # user successfully chose a colour
#				NewColour = (UserSelColour.red, UserSelColour.green, UserSelColour.blue, OldColour[3]) # last arg carries the alpha value from oldcol
#				for el in self.CurrentProj.CurrentElements: el.Text.Colour = NewColour
#				rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=self.CurrentProj.CurrentElements, Editing=self.CurrentProj.CurrentElements)
#				self.ETcharBaseColourSwatch.Widget.SetBackgroundColour(UserSelColour) # set button colour
#				AddToUndoList(self.CurrentProj, 'Change-Element-Text-Default-Properties', Elements=self.CurrentProj.CurrentElements, \
#					Parm='Colour', OldValue=OldColour, NewValue=NewColour, ChainCount=0)
#
#		def OnETcharBaseBoldCheck(self, event): # click in 'text default is bold' checkbox
#			# update default formatting to bold in all selected elements
#			for el in self.CurrentProj.CurrentElements: el.Text.Bold = self.ETcharBaseBoldCheck.Widget.IsChecked()
#			rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=self.CurrentProj.CurrentElements, Editing=self.CurrentProj.CurrentElements)
#
#		def OnETcharBaseUnderlineCheck(self, event): # click in 'text default is underlined' checkbox
#			# update default formatting to underlined in all selected elements
#			for el in self.CurrentProj.CurrentElements: el.Text.Underlined = self.ETcharBaseUnderlineCheck.Widget.IsChecked()
#			rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=self.CurrentProj.CurrentElements, Editing=self.CurrentProj.CurrentElements)
#
#		def OnETcharBaseItalicCheck(self, event): # click in 'text default is italic' checkbox
#			# update default formatting to italic in all selected elements
#			for el in self.CurrentProj.CurrentElements: el.Text.Italics = self.ETcharBaseItalicCheck.Widget.IsChecked()
#			rendering.UpdateProjectDisplay(self.CurrentProj, [self.CurrentProj.DisplayDevice[0]], ElementsChanged=self.CurrentProj.CurrentElements, Editing=self.CurrentProj.CurrentElements)
#
#		def HandleTextEditRequest(self, event): # handle request for editing text in selected element(s)
#			# event: the mouse event that raised the request, or None if from keyboard
#			# copied from T-u-t-i, not edited much yet
#			if True in [El.CanHaveText for El in self.CurrentProj.CurrentElements]: # check if any text-supporting Element is selected
#				# go to edit-text screen
#				self.GotoControlPanelAspect('Edit-Element-Text', NextMode=self.EditPanelCurrentMode, NextModeArgs=self.CurrentModeArgs, ResetCursorPos=True)
#				SetTextCtrlFocusAndInsertionPoint(self.ETcontentText, self.ETcontentTextSelection)

		def OnExitVizopRequest(self, Event=None, **Args):
			self.TopLevelParent.OnExitVizopRequest(Event)

		def GotoControlPanelAspect(self, NewAspect=None, Viewport=None, **Args):
			# Display required widgets in ControlPanel according to requested NewAspect
			# NewAspect (ControlPanelAspectItem instance or name as str): aspect to switch to
			# Viewport is current Viewport (currently only needed for mode 'Edit-Centre')

			def GotoNewPHAModelAspect(PrevMode=None, PrevViewport=None):
				# set up and display ControlPanel aspect for "New PHA model".
				# PrevMode is ControlPanel mode to return to, if Cancel pressed; if None, Cancel button is not shown
				# and 'exit Vizop' button shown instead
				# PrevViewport is the *current* Viewport (to return control if Cancel pressed)
				global KeyPressHash
				print("CF691 starting GotoNewPHAModelAspect")
				self.TopLevelFrame.MyEditPanel.EditPanelMode(Viewport=PrevViewport, NewMode='Blocked')
				if self.CurrentProj.ActiveViewports: # project has some existent Viewports
					self.VTWindow.SubmitVizopTalksMessage(Title=_("New Viewport"),
						MainText=_('What kind of Viewport would you like to create?'), Buttons=[],
						Priority=QuestionPriority)
				else:
					self.VTWindow.SubmitVizopTalksMessage(Title=_("Your project has no Viewports"),
						MainText=_('Would you like to create one?'), Buttons=[], Priority=QuestionPriority)
				WidgList = [] + self.NewViewportWidgets # basic set of widgets (the [] is needed so that we make a copy)
				self.WViewportList.Widget.SetSelection(wx.NOT_FOUND) # clear previous selection
					# (this is a workaround because EVT_LISTBOX is not raised when user clicks on item that's already selected,
					# contrary to Rappin p218)
				# store row count of basic widgets
				if not hasattr(GotoNewPHAModelAspect, 'HowManyRows'): GotoNewPHAModelAspect.HowManyRows = self.HowManyWidgetRows(WidgList)
				NextRow = GotoNewPHAModelAspect.HowManyRows + 1
				# add either "Cancel" or "Exit Vizop" button
				if PrevMode: # add the Cancel button if needed, and insert correct handler
#					self.CancelButtonWidgets[0].Handler = lambda Event: self.OnNewEntityCancel(Event, NextMode=PrevMode, Viewport=PrevViewport)
					(CancelWidgets, NextRow) = self.WidgetsInPosition(self.CancelButtonWidgets, NextRow - 1)
					WidgList += CancelWidgets
#					self.CancelButton.Widget.Bind(wx.EVT_BUTTON, lambda event: self.OnNewEntityCancel(
#						event, NextMode=PrevMode, Viewport=PrevViewport))
					self.CancelButton.KeyPressHandlerArgs = {'event': None} # args to be stored in KeyPressHash. May be unnecessary
				else: # add 'exit Vizop' button
					(ExitWidget, NextRow) = self.WidgetsInPosition(self.ExitVizopWidget, NextRow - 1)
					WidgList += ExitWidget
				# set up keyboard shortcuts for selecting Viewport types
				for (KeyStroke, ViewportClass) in self.NewViewportKbdHash.items():
					KeyPressHash = vizop_misc.RegisterKeyPressHandler(KeyPressHash, KeyCode=ord(KeyStroke),
						Handler=self.TopLevelFrame.DoNewViewportCommand, Args={'ViewportClass': ViewportClass,
						'Chain': False})
				return WidgList

			# main procedure for GotoControlPanelAspect
			assert isinstance(NewAspect, (self.ControlPanelAspectItem, str))
			global KeyPressHash
			# deactivate previous aspect
			if self.ControlPanelCurrentAspect:
				self.ControlPanelCurrentAspect.Deactivate(Widgets=self.ControlPanelCurrentAspect.WidgetList)
			# get target aspect, if supplied as a string
			if isinstance(NewAspect, str):
				TargetAspect = {'CPAspect_NumValue': self.NumericalValueAspect,
					'CPAspect_FaultTree': self.FaultTreeAspect,
					'CPAspect_FTConnectorOut': self.FTConnectorOutAspect}.get(NewAspect, None)
			else: TargetAspect = NewAspect
			if TargetAspect: # any recognised aspect supplied?
				self.ControlPanelCurrentAspect = TargetAspect # store new aspect
				TargetAspect.CurrentArgs = Args # store for repeating on next call
				self.PHAObjInControlPanel = Args.get('PHAObjInControlPanel', None)
				self.ComponentInControlPanel = Args.get('ComponentInControlPanel', None)
				# fetch UndoOnCancel value to store in undo record for any tasks that should be undone when Cancel pressed
				self.UndoOnCancel = Args.get('UndoOnCancel', None)
				# prefill widgets in new aspect and activate it. TODO consider calling RedrawControlPanelAspect() instead
				TargetAspect.Prefill(**Args)
				TargetAspect.SetWidgetVisibility(**Args)
				# set up the notebook tab for the aspect
				TargetAspect.Activate()
				# switch to tab for new aspect
				if TargetAspect.IsInNotebook: # does the notebook already have a tab for this aspect?
					self.MyNotebook.ChangeSelection(self.MyNotebook.FindPage(TargetAspect.NotebookPage))
				else: # no tab yet; make one, and insert it at the end
					self.MyNotebook.InsertPage(index=self.MyNotebook.GetPageCount(), page=TargetAspect.NotebookPage,
						text=TargetAspect.TabText)
					self.MyNotebook.ChangeSelection(page=self.MyNotebook.GetPageCount() - 1)
					TargetAspect.IsInNotebook = True
			else: print('CF744 warning, unrecognised control panel aspect "%s" requested' % str(NewAspect))
			# Note: we may need to remove notebook pages not currently required; use Notebook.RemovePage(page=PageIndex)

		def RedrawControlPanelAspect(self):
			# repopulates all widgets in the current control panel aspect
			self.ControlPanelCurrentAspect.Prefill(**self.ControlPanelCurrentAspect.CurrentArgs)
			self.ControlPanelCurrentAspect.SetWidgetVisibility(**self.ControlPanelCurrentAspect.CurrentArgs)
			self.ControlPanelCurrentAspect.Activate(**self.ControlPanelCurrentAspect.CurrentArgs)

		def WidgetsInPosition(self, WidgList, StartingRow=1, ColOffset=0):
			# set up widgets in WidgList (list of UIWidgetItems) for insertion into an overall widget list at StartingRow
			# and offset by ColOffset columns to the right
			# return ( [widgets with offsets set], next available row number)
			# This procedure may be obsolete, as we don't use RowLoc any more
			NextRow = 0
			for Widget in WidgList:
				Widget.RowOffset = StartingRow - Widget.RowLoc
				Widget.ColOffset = ColOffset
				NextRow = max(NextRow, StartingRow + Widget.RowLoc + Widget.RowSpan)
			return (WidgList, NextRow)

		def HowManyWidgetRows(self, WidgList): # return no of rows occupied by widgets in WidgList
			# find the lowest and highest row numbers occupied, taking RowSpan into account
			# This procedure may be obsolete, as we don't use RowLoc any more
			MinRow = min([9999] + [W.RowLoc for W in WidgList])
			MaxRow = max([-1] + [W.RowLoc + W.RowSpan - 1 for W in WidgList])
			return max(0, MaxRow - MinRow + 1) # the 0 handles empty WidgList case

		def InsertVariableWidgets(self, TargetPlaceholderName, FixedWidgets, VariableWidgets):
			# finds TargetPlaceholderName (str) in FixedWidgets (list of UIWidgetItem instances with placeholder(s))
			# creates and returns combined widget list,
			# replacing the placeholder with the variable widgets inserted in the correct position according to their
			# RowOffset and ColOffset attribs (NB row posn doesn't consider any GapY defined in variable widgets)
			# doesn't check whether this causes position clashes with existing widgets
			# doesn't take accound of RowOffset, ColOffset attribs
			# return: CombinedWidgets
			# The overall algorithm is:
			# 1. Find the applicable placeholder in FixedWidgets. Transfer all widgets before the placeholder to
			# CombinedWidgets.
			# 2. Keep transferring FixedWidgets until the next FixedWidget is to the right of, or below, the first
			# variable widget.
			# 3. Transfer the first variable widget to CombinedWidgets.
			# 4. Repeat steps 2 and 3 with each successive variable widget until all the widgets are used up.
			assert isinstance(TargetPlaceholderName, str)
			assert hasattr(FixedWidgets, '__iter__') # confirm it's an iterable
			assert hasattr(VariableWidgets, '__iter__')
			# confirm matching placeholder found in FixedWidgets
			assert TargetPlaceholderName in [P.Name for P in FixedWidgets if isinstance(P, UIWidgetPlaceholderItem)]
			# find row and column address of placeholder
			ThisRow = NextCol = 0 # ThisRow: current row; NextCol: next available column in the row
			PlaceholderFound = False
			FixedWidgetIndex = 0
			ThisRowSpan = 1 # how many sizer rows are taken up by current row of widgets
			GapYAdded = False # whether the current row contains any widget with GapY set, i.e. leaving a gap above
			while not PlaceholderFound: # walk through FixedWidgets until placeholder is found
				ThisWidget = FixedWidgets[FixedWidgetIndex]
				if isinstance(ThisWidget, UIWidgetPlaceholderItem) and\
					(getattr(ThisWidget, 'Name', None) == TargetPlaceholderName):
					PlaceholderFound = True
				else:
					if ThisWidget.NewRow: # start new row if required
						ThisRow += ThisRowSpan # add span of preceding row
						ThisRowSpan = 1 # reset ThisRowSpan for new row
						GapYAdded = False # reset flag
					NextCol = ThisWidget.ColLoc + ThisWidget.ColSpan
					if (ThisWidget.GapY > 0) and not GapYAdded: # did the widget require a GapY above?
						ThisRow += 1 # add a row for the GapY
						GapYAdded = True # set flag to avoid repeat-adding gap if another widget has GapY in the same row
					FixedWidgetIndex += 1
			# now we have ThisRow and NextCol (start location for variable widgets) and FixedWidgetIndex (index of placeholder)
			# put widgets before the placeholder into the combined list
			CombinedWidgets = FixedWidgets[:FixedWidgetIndex]
			# assign row and column positions to variable widgets
			for ThisVarWidget in VariableWidgets:
				ThisVarWidget.ActualRow = ThisRow + ThisVarWidget.RowOffset
				ThisVarWidget.ActualCol = NextCol + ThisVarWidget.ColOffset
			# copy remaining FixedWidgets and all VariableWidgets into CombinedWidgets in the correct order
			FixedWidgetIndex += 1 # skip over the placeholder
			VarWidgetIndex = 0
			FixedWidgetsFinished = (FixedWidgetIndex >= len(FixedWidgets))
			VarWidgetsFinished = (VarWidgetIndex >= len(VariableWidgets)) # whether we have used up all widgets in the lists
			while not (FixedWidgetsFinished and VarWidgetsFinished): # loop while either list has unused widgets
				# find insertion row and column of next variable widget
				if not VarWidgetsFinished:
					NextVarWidgetRow = VariableWidgets[VarWidgetIndex].ActualRow
					NextVarWidgetCol = VariableWidgets[VarWidgetIndex].ActualCol
				# add fixed widgets until the next fixed widget is beyond the target location of the next variable widget
				StopAddingFixedWidgets = False
				while (not FixedWidgetsFinished) and (not StopAddingFixedWidgets):
					ThisFixedWidget = FixedWidgets[FixedWidgetIndex]
					# update ThisRow for ThisFixedWidget (use getattr in case it's a placeholder widget)
					if getattr(ThisFixedWidget, 'NewRow', False): ThisRow += 1
					# are there any more variable widgets?
					if VarWidgetsFinished: StopAddingFixedWidgets = False # if not, keep adding fixed widgets
					else:
						# check if ThisFixedWidget is to the right of, or below, the next variable widget
						StopAddingFixedWidgets = (ThisRow > NextVarWidgetRow) or (ThisFixedWidget.ColLoc > NextVarWidgetCol)
					# if it isn't, add it to the combined list and move to the next fixed widget
					if not StopAddingFixedWidgets:
						CombinedWidgets.append(ThisFixedWidget)
						FixedWidgetIndex += 1
						FixedWidgetsFinished = (FixedWidgetIndex >= len(FixedWidgets))
				# add a variable widget (step 3)
				if not VarWidgetsFinished:
					ThisVariableWidget = VariableWidgets[VarWidgetIndex]
					# set row and column attribs for ThisVariableWidget
					if NextVarWidgetRow > ThisRow: # moving to next row
						ThisVariableWidget.NewRow = True
						ThisRow += 1
					ThisVariableWidget.ColLoc = NextVarWidgetCol
					# add next variable widget to combined list
					CombinedWidgets.append(ThisVariableWidget)
					# move to next variable widget
					VarWidgetIndex += 1
					VarWidgetsFinished = (VarWidgetIndex >= len(VariableWidgets))
			return CombinedWidgets

		def SetInitialControlPanelAspect(self):
			# sets the initial display of control panel, when first created. Currently, this is empty.
			# It will be populated later by ControlFrame.__init__ calling SetProject()
			pass # no content required at first
#			if self.CurrentProj.ActiveViewports: # if any Viewports exist: go to Edit Centre mode
#				self.GotoControlPanelAspect('Edit-Centre', Viewport=self.CurrentViewport)
#			else: # no PHA models exist: go to PHAModel aspect to allow user to create a new PHA model
#				self.GotoControlPanelAspect(NewAspect=self.PHAModelsAspect)

#		def ButtonBitmap(self, ImageName): # returns bitmap for button. Now moved to ControlFrame
#			# ImageName can be the filename stub of an icon file in the runtime icons folder, or wx.ART_something
#			# See https://wxpython.org/Phoenix/docs/html/wx.ArtProvider.html
#			if isinstance(ImageName, str):
#				return wx.BitmapFromImage(self.TopLevelFrame.MyArtProvider.get_image(ImageName, (24, 24),
#					conserve_aspect_ratio=True))
#			else:
#				return self.TopLevelFrame.MyArtProvider.GetBitmap(id=ImageName, size=(24, 24))

		# ControlPanel main setup routine
		def __init__(self, parent, ID=-1, label="", pos=wx.DefaultPosition, size=(500,100), VTWindow=None,
					 FirstProject=None, Viewport=None, ColScheme=None):
			# FirstProject: the project (ProjectItem instance) that should be 'focused' when Edit panel is launched
			# VTWindow: the VizopTalks panel

			def SetupObjectLists(self):
				# Set up object lists (for Viewports and PHAModels)
				(self.ViewportsCanBeCreatedManually, self.ViewportsCanBeCreatedManuallyWithShortcuts, self.ViewportTypesInNameOrder,
				 self.NewViewportKbdHash) = SetupObjSelectionList(display_utilities.ViewportMetaClass.ViewportClasses)
				(self.PHAModelsCanBeCreatedManually, self.PHAModelsCanBeCreatedManuallyWithShortcuts, self.PHAModelTypesInNameOrder,
				 self.NewPHAModelKbdHash) = SetupObjSelectionList(core_classes.PHAModelMetaClass.PHAModelClasses)

			wx.Panel.__init__(self, parent, ID, pos, size, wx.RAISED_BORDER | wx.TAB_TRAVERSAL, label)
			# make lists for creation of Viewports and PHAModels
			SetupObjectLists(self)
			self.CurrentProj = FirstProject # which project is currently 'focused'
			self.ColScheme = ColScheme
			self.SetBackgroundColour(self.ColScheme.BackBright)
			self.SetMinSize(size)
			self.ControlPanelCurrentAspect = None # which aspect is currently active
			self.settings_manager = settings.SettingsManager()
			self.VTWindow = VTWindow
			self.TopLevelFrame = parent # reference to ControlFrame
			# set up a notebook control to manage tabbed panels
			self.MyNotebook = wx.Notebook(parent=self, style=wx.NB_TOP)
			self.StandardImageButtonSize = wx.Size(32, 32)

			# Make widgets for the aspects to be displayed in the tabbed panels. Add more aspects here when developed
			self.MakePHAModelsAspect()
			self.MakeNumericalValueAspect()
			self.MakeFaultTreeAspect()
			self.MakeFTConnectorOutAspect()
			# Make sizer for notebook (this is required even though there's only one item in it, the notebook itself)
			MySizer = wx.BoxSizer()
			MySizer.Add(self.MyNotebook, 1, wx.EXPAND)
			self.SetSizer(MySizer)

			# generate list of system fonts (not currently used)
#			e = wx.FontEnumerator()
#			e.EnumerateFacenames()
#			SystemFonts = e.GetFacenames()

#				# widgets for edit-text screen
#			self.ETheaderLabel = UIWidgetItem(wx.StaticText(self, -1, _('EDIT TEXT IN ELEMENT')), ColSpan=2)
#			self.ETcontentText = UIWidgetItem(wx.TextCtrl(self, -1, size=(300, 150), \
#														  style=wx.TE_PROCESS_ENTER | wx.HSCROLL | wx.TE_MULTILINE | wx.TE_RICH2), Handler=self.OnETcontentText,
#											  Events=[wx.EVT_TEXT], RowLoc=2, ColSpan=4)
#			self.ETcontentText_Updated = False # flag used by cursor move event detection routine
#			self.ETcontentText.Widget.SkippedLastPasteEvent = False # flag used for EVT_TEXT bug workaround
#			self.ETparaLabel = UIWidgetItem(wx.StaticText(self, -1, _('Alignment:')), RowLoc=4)
#			self.ETparaLeftRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Left'), style=wx.RB_GROUP),
#												Handler=lambda event: self.OnETparaHorizAlignRadio(event, Alignment='Left'), Events=[wx.EVT_RADIOBUTTON], RowLoc=4)
#			self.ETparaRightRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Right')),
#												 Handler=lambda event: self.OnETparaHorizAlignRadio(event, Alignment='Right'),
#												 Events=[wx.EVT_RADIOBUTTON], RowLoc=4, ColLoc=3)
#			self.ETparaHorizCentreRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Centred')),
#													   Handler=lambda event: self.OnETparaHorizAlignRadio(event, Alignment='Centre'),
#													   Events=[wx.EVT_RADIOBUTTON], RowLoc=4, ColLoc=2)
#			self.ETparaHorizCentreRadio.Widget.SetValue(True)
#
#			self.ETparaTopRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Top'), style=wx.RB_GROUP),
#											   Handler=lambda event: self.OnETparaVertAlignRadio(event, Alignment='Top'), Events=[wx.EVT_RADIOBUTTON], RowLoc=5)
#			self.ETparaBottomRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Bottom')),
#												  Handler=lambda event: self.OnETparaVertAlignRadio(event, Alignment='Bottom'),
#												  Events=[wx.EVT_RADIOBUTTON], RowLoc=5, ColLoc=3)
#			self.ETparaVertCentreRadio = UIWidgetItem(wx.RadioButton(self, -1, _('Centred')),
#													  Handler=lambda event: self.OnETparaVertAlignRadio(event, Alignment='Centre'), Events=[wx.EVT_RADIOBUTTON],
#													  RowLoc=5, ColLoc=2)
#			self.ETparaVertCentreRadio.Widget.SetValue(True)
#			self.ETcharNowStandoutCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Standing out')),
#													   Handler=self.OnETcharNowStandoutCheck, Events=[wx.EVT_CHECKBOX], RowLoc=4, ColLoc=3, ColSpan=2)
#
#			self.ETlineSpacingLabel1 = UIWidgetItem(wx.StaticText(self, -1, _('Gap between lines:')), RowLoc=7, ColSpan=2)
#			self.ETlineSpacingText = UIWidgetItem(wx.TextCtrl(self, -1, size=(80, 30)),
#												  Handler=self.OnETlineSpacingText, Events=[wx.EVT_KILL_FOCUS], RowLoc=7, ColLoc=2)
#			self.ETlineSpacingLabel2 = UIWidgetItem(wx.StaticText(self, -1, _('lines')), RowLoc=7, ColLoc=3) # unit label 'lines'
#			self.ETcharNowFormatLabel = UIWidgetItem(wx.StaticText(self, -1, _('STYLE OF SELECTED CHARACTERS')), ColSpan=4)
#			self.ETcharNowFontLabel = UIWidgetItem(wx.StaticText(self, -1, _('Font:')), RowLoc=1)
#			self.ETcharNowFontText = UIWidgetItem(wx.Choice(self, -1, size=(100, 30), choices=SystemFonts),
#												  Handler=self.OnETcharNowFontText, Events=[wx.EVT_CHOICE], RowLoc=1, ColLoc=1, ColSpan=2)
#			self.ETcharNowSizeLabel = UIWidgetItem(wx.StaticText(self, -1, _('Size x')), RowLoc=1, ColLoc=3)
##												  Handler=self.OnETcharNowSizeText, Events=[wx.EVT_KILL_FOCUS], RowLoc=1, ColLoc=4)
#			self.ETcharNowColourLabel = UIWidgetItem(wx.StaticText(self, -1, _('Colour:')), RowLoc=2)
#			self.ETcharNowColourSwatch = UIWidgetItem(wx.Button(self, -1, '', size=ColourSwatchButtonSize),
#													  Handler=self.OnETcharNowColourSwatch, Events=[wx.EVT_BUTTON], RowLoc=2, ColLoc=1)
#			self.ETcharNowBoldCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Bold')),
#												   Handler=self.OnETcharNowBoldCheck, Events=[wx.EVT_CHECKBOX], RowLoc=3, ColLoc=1)
#			self.ETcharNowUnderlineCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Underlined')),
#														Handler=self.OnETcharNowUnderlineCheck, Events=[wx.EVT_CHECKBOX], RowLoc=3, ColLoc=2)
#			self.ETcharNowItalicCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Italic')),
##			self.ETcharNowSuperscriptCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Superscript')),
#														  Handler=self.OnETcharNowSuperscriptCheck, Events=[wx.EVT_CHECKBOX], RowLoc=4, ColLoc=1)
#			self.ETcharNowSubscriptCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Subscript')),
#														Handler=self.OnETcharNowSubscriptCheck, Events=[wx.EVT_CHECKBOX], RowLoc=4, ColLoc=2)
#			self.ETcharBaseFormatLabel = UIWidgetItem(wx.StaticText(self, -1, _('DEFAULT CHARACTER STYLE')), ColSpan=4)
#			self.ETcharBaseFontLabel = UIWidgetItem(wx.StaticText(self, -1, _('Font:')), RowLoc=1)
#			self.ETcharBaseFontText = UIWidgetItem(wx.Choice(self, -1, size=(100, 30), choices=SystemFonts),
#												   Handler=self.OnETcharBaseFontText, Events=[wx.EVT_CHOICE], RowLoc=1, ColLoc=1, ColSpan=2)
#			self.ETcharBaseSizeLabel = UIWidgetItem(wx.StaticText(self, -1, _('Size (pt):')), RowLoc=1, ColLoc=3)
#			self.ETcharBaseSizeText = UIWidgetItem(wx.TextCtrl(self, -1, size=(60, 30)),
#												   Handler=self.OnETcharBaseSizeText, Events=[wx.EVT_KILL_FOCUS], RowLoc=1, ColLoc=4)
#			self.ETcharBaseColourLabel = UIWidgetItem(wx.StaticText(self, -1, _('Colour:')), RowLoc=2)
#			self.ETcharBaseColourSwatch = UIWidgetItem(wx.Button(self, -1, '', size=ColourSwatchButtonSize),
#													   Handler=self.OnETcharBaseColourSwatch, Events=[wx.EVT_BUTTON], RowLoc=2, ColLoc=1)
#			self.ETcharBaseBoldCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Bold')),
#													Handler=self.OnETcharBaseBoldCheck, Events=[wx.EVT_CHECKBOX], RowLoc=3, ColLoc=1)
#			self.ETcharBaseUnderlineCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Underlined')),
#														 Handler=self.OnETcharBaseUnderlineCheck, Events=[wx.EVT_CHECKBOX], RowLoc=3, ColLoc=2)
#			self.ETcharBaseItalicCheck = UIWidgetItem(wx.CheckBox(self, -1, _('Italic')),
#													  Handler=self.OnETcharBaseItalicCheck, Events=[wx.EVT_CHECKBOX], RowLoc=3, ColLoc=3)
#			self.ETcharFinishedButton = UIWidgetItem(wx.Button(self, -1, _('Finished | ' + info.CtrlKey + 'Enter')),
#													 Handler=self.OnETcharFinishedButton, Events=[wx.EVT_BUTTON], RowLoc=1, ColLoc=2, ColSpan=2,
#													 KeyStroke=[wx.WXK_CONTROL, wx.WXK_RETURN])
#
#			# widgets for Edit-Centre mode
#			self.ECHeadTitle = UIWidgetItem(wx.StaticText(self, -1, _('VIZOP EDITING CENTRE')), ColSpan=4,
#											Flags=wx.ALIGN_CENTER_VERTICAL)
#			self.ECHeadTitle.Widget.SetFont(text.FontInstance(HeadingTextPointSize, Bold=True))
#			self.ECProjTitle = UIWidgetItem(wx.StaticText(self, -1, _('PROJECTS')), RowPos=2, ColSpan=2,
#											Flags=wx.ALIGN_CENTER_VERTICAL)
#			self.ECProjTitle.Widget.SetFont(text.FontInstance(LabelTextPointSize, Bold=True))
#			self.ECNewProjButton = UIWidgetItem(wx.Button(self, -1, _('Project settings | F9')),
#												Handler=self.OnECProjSettingsButton, Events=[wx.EVT_BUTTON], RowLoc=3, ColSpan=3, KeyStroke=wx.WXK_F9)
#
#			self.ECViewportTitle = UIWidgetItem(wx.StaticText(self, -1, _('ViewportS')),
#												 RowLoc=6, ColSpan=2, Flags=wx.ALIGN_CENTER_VERTICAL)
#			self.ECViewportTitle.Widget.SetFont(text.FontInstance(LabelTextPointSize, Bold=True))
#			self.ECNewViewportButton = UIWidgetItem(wx.Button(self, -1, _('New Viewport | F11')),
#													 Handler=self.OnECNewViewportButton, Flags=[wx.EVT_BUTTON], RowLoc=7, ColSpan=3, KeyStroke=wx.WXK_F11)
#			self.ECViewportDestroyButton = UIWidgetItem(wx.Button(self, -1, _('Destroy | Del + F11')),
#														 Handler=self.OnECViewportDestroyButton, Events=[wx.EVT_BUTTON], RowLoc=8, ColLoc=3, ColSpan=3,
#														 KeyStroke=[wx.WXK_DELETE, wx.WXK_F11])
#
#			self.ECAboutButton = UIWidgetItem(wx.Button(self, -1, _('About Vizop | A')),
#											  Handler=lambda Event: vizop_misc.OnAboutRequest(Parent=self, event=Event), Events=[wx.EVT_BUTTON],
#											  RowLoc=12, ColSpan=2, KeyStroke=ord('a'))
#			self.ECExitButton = UIWidgetItem(wx.Button(self, -1, _('Exit Vizop | ' + info.CtrlKey + 'Q')),
#											 Handler=self.OnExitVizopRequest, Events=[wx.EVT_BUTTON], RowLoc=12, ColLoc=2, ColSpan=3,
#											 KeyStroke=[wx.WXK_CONTROL, ord('q')])
#
#			self.ECWidgets = [self.ECHeadTitle, self.ECProjTitle, self.ECViewportTitle, self.OnECNewViewportButton,
#				self.ECViewportDestroyButton, self.InputDocsButton, self.ECAboutButton, self.ECExitButton]
#			self.ExitVizopWidget = [self.ECExitButton]
#
			self.SetInitialControlPanelAspect() # set initial appearance of control panel, before loading project

		def UpdateNavigationButtonStatus(self, Proj):
			# update status of forward, back, undo and redo unttons in control panel
			self.PHAModelsAspect.NavigateForwardButton.Widget.Enable(bool(Proj.ForwardHistory))
			self.PHAModelsAspect.NavigateBackButton.Widget.Enable(True in [m.Displayable for m in Proj.BackwardHistory])
			self.PHAModelsAspect.UndoButton.Widget.Enable(bool(Proj.UndoList))
			self.PHAModelsAspect.RedoButton.Widget.Enable(bool(Proj.RedoList))

		def PrefillWidgetsForPHAModelsAspect(self): # set initial values for widgets in PHAModels aspect
			Proj = self.TopLevelFrame.CurrentProj
			# enable navigation buttons if there are any items in current project's history lists
			self.UpdateNavigationButtonStatus(Proj)

		def SetWidgetVisibilityForPHAModelsAspect(self, **Args): # set IsVisible attrib for widgets
			pass

		def MakeStandardWidgets(self, Scope, NotebookPage):
			# make standard set of widgets, e.g. navigation buttons and undo/redo buttons, appearing on every aspect
			# Scope (ControlPanelAspectItem instance): the aspect owning the widgets
			# NotebookPage (wx.Panel instance): panel in the wxNotebook containing the aspect's widgets
			assert isinstance(Scope, self.ControlPanelAspectItem)
			Scope.NavigateBackButton = UIWidgetItem(wx.Button(NotebookPage,
				size=self.StandardImageButtonSize), KeyStroke=[wx.WXK_CONTROL, wx.WXK_LEFT],
				ColLoc=0, ColSpan=1, Events=[wx.EVT_BUTTON], Handler=self.OnNavigateBackButton, Flags=0)
			Scope.NavigateBackButton.Widget.SetBitmap(self.TopLevelFrame.ButtonBitmap(wx.ART_GO_BACK))
			Scope.NavigateBackButton.ToolTip = ToolTip.SuperToolTip(_("Go back"))
			Scope.NavigateBackButton.ToolTip.SetTarget(self.PHAModelsAspect.NavigateBackButton.Widget)
			Scope.NavigateForwardButton = UIWidgetItem(wx.Button(NotebookPage, size=self.StandardImageButtonSize), KeyStroke=[wx.WXK_CONTROL, wx.WXK_RIGHT],
				ColLoc=1, ColSpan=1, Events=[wx.EVT_BUTTON], Handler=self.OnNavigateForwardButton, Flags=0)
			Scope.NavigateForwardButton.Widget.SetBitmap(self.TopLevelFrame.ButtonBitmap(wx.ART_GO_FORWARD))
			Scope.UndoButton = UIWidgetItem(wx.Button(NotebookPage, size=self.StandardImageButtonSize), KeyStroke=[wx.WXK_CONTROL, ord('z')],
				ColLoc=0, ColSpan=1, Events=[wx.EVT_BUTTON], Handler=self.TopLevelFrame.OnUndoRequest, NewRow=True, Flags=0) # =0 keeps button at fixed size
			Scope.UndoButton.Widget.SetBitmap(self.TopLevelFrame.ButtonBitmap(wx.ART_UNDO))
			Scope.RedoButton = UIWidgetItem(wx.Button(NotebookPage, size=self.StandardImageButtonSize), KeyStroke=[wx.WXK_CONTROL, ord('y')],
				ColLoc=1, ColSpan=1, Events=[wx.EVT_BUTTON], Handler=self.TopLevelFrame.OnRedoRequest, Flags=0)
			Scope.RedoButton.Widget.SetBitmap(self.TopLevelFrame.ButtonBitmap(wx.ART_REDO))

		def MakePHAModelsAspect(self): # make Control Panel aspect for PHAModel control
			# make basic attribs needed for the aspect
			MyNotebookPage = wx.Panel(parent=self.MyNotebook)
			MyTabText = _('PHA models') # text appearing on notebook tab
			self.PHAModelsAspect = self.ControlPanelAspectItem(InternalName='PHAModels', ParentFrame=self,
				TopLevelFrame=self.TopLevelFrame, PrefillMethod=self.PrefillWidgetsForPHAModelsAspect,
				SetWidgetVisibilityMethod=self.SetWidgetVisibilityForPHAModelsAspect, NotebookPage=MyNotebookPage,
				TabText=MyTabText)
			# make widgets
			self.MakeStandardWidgets(Scope=self.PHAModelsAspect, NotebookPage=MyNotebookPage)
			self.PHAModelsAspect.NewPHAModelTypesLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Select a type of PHA model:')),
				ColLoc=3, ColSpan=3, GapX=20)
			self.PHAModelsAspect.NewPHAModelTypesList = UIWidgetItem(wx.ListBox(MyNotebookPage, -1,
				choices=self.PHAModelsCanBeCreatedManuallyWithShortcuts,
				style=wx.LB_SINGLE), Handler=self.OnNewPHAModelListbox, Events=[wx.EVT_LISTBOX], ColLoc=3, ColSpan=4)
			# make list of widgets in this aspect
			self.PHAModelsAspect.WidgetList = [self.PHAModelsAspect.NavigateBackButton,
				self.PHAModelsAspect.NavigateForwardButton, self.PHAModelsAspect.NewPHAModelTypesLabel,
				self.PHAModelsAspect.UndoButton, self.PHAModelsAspect.RedoButton, self.PHAModelsAspect.NewPHAModelTypesList]

		def MakeNumericalValueAspect(self): # make Control Panel aspect for numerical value editing
			# make basic attribs needed for the aspect
			MyNotebookPage = wx.Panel(parent=self.MyNotebook)
			MyTabText = _('Value') # text appearing on notebook tab
			self.NumericalValueAspect = self.ControlPanelAspectItem(InternalName='NumericalValue', ParentFrame=self,
				TopLevelFrame=self.TopLevelFrame, PrefillMethod=self.PrefillWidgetsForNumericalValueAspect,
				SetWidgetVisibilityMethod=self.SetWidgetVisibilityforNumericalValueAspect, NotebookPage=MyNotebookPage,
				TabText=MyTabText)
			# make widgets
			self.MakeStandardWidgets(Scope=self.NumericalValueAspect, NotebookPage=MyNotebookPage)
			self.NumericalValueAspect.HeaderLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, ''),
				ColLoc=3, ColSpan=4, GapX=20, Font=self.TopLevelFrame.Fonts['SmallHeadingFont'])
			self.NumericalValueAspect.CommentButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Comment')),
				Handler=self.NumericalValueAspect_OnCommentButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=7, ColSpan=1,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.NumericalValueAspect.ValueLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Current value:')),
				ColLoc=3, ColSpan=1)
			self.NumericalValueAspect.ValueText = UIWidgetItem(wx.TextCtrl(MyNotebookPage, -1,
				style=wx.TE_PROCESS_ENTER), MinSizeY=25,
				Events=[wx.EVT_TEXT_ENTER], Handler=self.NumericalValueAspect_OnValueTextWidget, IsNumber=True,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=100, ColLoc=4, ColSpan=1, DisplayMethod='StaticFromText')
				# this TextCtrl raises events in 2 ways: (1) <Enter> key raises wx.EVT_TEXT_ENTER, (2) loss of focus is
				# caught by OnIdle().
			self.NumericalValueAspect.UnitChoice = UIWidgetItem(wx.Choice(MyNotebookPage, -1, size=(100, 30), choices=[]),
				  Handler=self.NumericalValueAspect_OnUnitWidget, Events=[wx.EVT_CHOICE], ColLoc=5, ColSpan=1)
			self.NumericalValueAspect.ValueKindLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Basis:') + ' '),
				ColLoc=6, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.EXPAND)
			self.NumericalValueAspect.ValueKindChoice = UIWidgetItem(wx.Choice(MyNotebookPage, -1, size=(100, 30), choices=[]),
				  Handler=self.NumericalValueAspect_OnValueKindWidget, Events=[wx.EVT_CHOICE], ColLoc=7, ColSpan=1)
			self.NumericalValueAspect.LinkedToLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, ''),
				ColLoc=3, ColSpan=2, NewRow=True)
			self.NumericalValueAspect.LinkFromButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Link from...')),
				Handler=self.NumericalValueAspect_OnLinkFromButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=7, ColSpan=1, NewRow=True,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.NumericalValueAspect.ShowMeLinkFromButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Show me')),
				Handler=self.NumericalValueAspect_OnShowMeLinkFromButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=8, ColSpan=1,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.NumericalValueAspect.CopyFromButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Copy from...')),
				Handler=self.NumericalValueAspect_OnCopyFromButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=7, ColSpan=1, NewRow=True,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.NumericalValueAspect.ShowMeCopyFromButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Show me')),
				Handler=self.NumericalValueAspect_OnShowMeCopyFromButton,
				Events=[wx.EVT_BUTTON], ColLoc=8, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.NumericalValueAspect.ConstantLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1,
				_('Constant used:') + ' '),
				ColLoc=6, ColSpan=1, NewRow=True, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_RIGHT | wx.EXPAND)
			self.NumericalValueAspect.ConstantChoice = UIWidgetItem(wx.Choice(MyNotebookPage, -1, size=(100, 30), choices=[]),
				  Handler=self.NumericalValueAspect_OnConstantWidget, Events=[wx.EVT_CHOICE], ColLoc=7, ColSpan=1)
			self.NumericalValueAspect.EditConstantsButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Edit constants')),
				Handler=self.NumericalValueAspect_OnEditConstantsButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=8, ColSpan=1,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.NumericalValueAspect.MatrixLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Matrix used:')),
				ColLoc=6, ColSpan=1, NewRow=True)
			self.NumericalValueAspect.MatrixChoice = UIWidgetItem(wx.Choice(MyNotebookPage, -1, size=(100, 30), choices=[]),
				Handler=self.NumericalValueAspect_OnMatrixWidget, Events=[wx.EVT_CHOICE], ColLoc=7, ColSpan=1)
			self.NumericalValueAspect.EditMatricesButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Edit matrices')),
				Handler=self.NumericalValueAspect_OnEditMatricesButton,
				Events=[wx.EVT_BUTTON], ColLoc=8, ColSpan=1, Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			# make list of all widgets in this aspect
			self.NumericalValueAspect.WidgetList = [self.NumericalValueAspect.NavigateBackButton,
				self.NumericalValueAspect.NavigateForwardButton, self.NumericalValueAspect.HeaderLabel,
				self.NumericalValueAspect.CommentButton,
				self.NumericalValueAspect.UndoButton, self.NumericalValueAspect.RedoButton,
				self.NumericalValueAspect.ValueLabel, self.NumericalValueAspect.ValueText,
				self.NumericalValueAspect.UnitChoice, self.NumericalValueAspect.ValueKindLabel,
				self.NumericalValueAspect.ValueKindChoice,
				self.NumericalValueAspect.LinkedToLabel,
				self.NumericalValueAspect.LinkFromButton, self.NumericalValueAspect.ShowMeLinkFromButton,
				self.NumericalValueAspect.CopyFromButton, self.NumericalValueAspect.ShowMeCopyFromButton,
				self.NumericalValueAspect.ConstantLabel, self.NumericalValueAspect.ConstantChoice,
				self.NumericalValueAspect.EditConstantsButton,
				self.NumericalValueAspect.MatrixLabel, self.NumericalValueAspect.MatrixChoice,
				self.NumericalValueAspect.EditMatricesButton]

		# specific methods for NumericalValueAspect

		def PrefillWidgetsForNumericalValueAspect(self, **Args): # set initial values for widgets in NumericalValueAspect
			Proj = self.TopLevelFrame.CurrentProj
			# capture the component containing the numerical value to display
			self.TopLevelFrame.PHAObjInControlPanel = Args['PHAObjInControlPanel']
			self.TopLevelFrame.ComponentInControlPanel = Args['ComponentInControlPanel']
			# enable navigation buttons if there are any items in current project's history lists
			self.UpdateNavigationButtonStatus(Proj)
			# set widget values
			# set up HeaderLabel
			if self.TopLevelFrame.ComponentInControlPanel: # is there a component name? (editing value in FT header)
				self.NumericalValueAspect.HeaderLabel.Widget.SetLabel(_('Value: %s') % self.TopLevelFrame.PHAObjInControlPanel.
					ComponentEnglishNames[self.TopLevelFrame.ComponentInControlPanel])
			else:
				self.NumericalValueAspect.HeaderLabel.Widget.SetLabel(_('Value: %s %s') %
					(self.TopLevelFrame.PHAObjInControlPanel.EventTypeHumanName,
					self.TopLevelFrame.PHAObjInControlPanel.Numbering))
			# set up ValueText
			self.NumericalValueAspect.ValueText.PHAObj = self.TopLevelFrame.PHAObjInControlPanel
			PHAObj = self.NumericalValueAspect.ValueText.PHAObj
			self.NumericalValueAspect.ValueText.DataAttrib = self.TopLevelFrame.ComponentInControlPanel
			# find host for attribs such as Value and UnitOptions
			DataAttrib = self.NumericalValueAspect.ValueText.DataAttrib
			DataHost = getattr(PHAObj, DataAttrib) if DataAttrib else PHAObj
			# populate ValueText with the current value
			self.NumericalValueAspect.ValueText.Widget.SetValue(DataHost.Value)
			# select all text in the value text widget - user intuitively expects this
			self.NumericalValueAspect.ValueText.Widget.SelectAll()
			# set up UnitChoice
			UnitOptions = DataHost.UnitOptions # list of ChoiceItem instances
			self.NumericalValueAspect.UnitChoice.PHAObj = self.TopLevelFrame.PHAObjInControlPanel
			self.NumericalValueAspect.UnitChoice.DataAttrib = self.TopLevelFrame.ComponentInControlPanel
			# populate UnitChoice with unit options
			self.NumericalValueAspect.UnitChoice.Widget.Set([u.HumanName for u in UnitOptions])
			# select the current unit in UnitChoice, if any
			ApplicableUnitOptionsList = [u.Applicable for u in UnitOptions]
			self.NumericalValueAspect.UnitChoice.Widget.SetSelection(
				ApplicableUnitOptionsList.index(True) if True in ApplicableUnitOptionsList else wx.NOT_FOUND)
			# set up ValueKindChoice
			ValueKindOptions = DataHost.ValueKindOptions # list of ChoiceItem instances
			self.NumericalValueAspect.ValueKindChoice.PHAObj = self.TopLevelFrame.PHAObjInControlPanel
			self.NumericalValueAspect.ValueKindChoice.DataAttrib = self.TopLevelFrame.ComponentInControlPanel
			# populate ValueKindChoice with value kind options
			self.NumericalValueAspect.ValueKindChoice.Widget.Set([u.HumanName for u in ValueKindOptions])
			# select the current value kind in ValueKindOptions
			ApplicableValueKindOptionsList = [u.Applicable for u in ValueKindOptions]
			self.NumericalValueAspect.ValueKindChoice.Widget.SetSelection(
				ApplicableValueKindOptionsList.index(True) if True in ApplicableValueKindOptionsList else wx.NOT_FOUND)

		def SetWidgetVisibilityforNumericalValueAspect(self, **Args): # set IsVisible attrib for each widget
			# set widgets that are always visible
			VisibleList = [self.NumericalValueAspect.NavigateBackButton,
				self.NumericalValueAspect.NavigateForwardButton, self.NumericalValueAspect.HeaderLabel,
				self.NumericalValueAspect.CommentButton, self.NumericalValueAspect.LinkedToLabel,
				self.NumericalValueAspect.UndoButton, self.NumericalValueAspect.RedoButton,
				self.NumericalValueAspect.ValueLabel, self.NumericalValueAspect.ValueText,
				self.NumericalValueAspect.UnitChoice, self.NumericalValueAspect.ValueKindLabel,
				self.NumericalValueAspect.ValueKindChoice]
			# find the ValueKind for this value
			ThisPHAObj = Args['PHAObjInControlPanel']
			ThisDataAttribName = Args['ComponentInControlPanel'] # contains attrib name if editing an FT header
				# component, else ''
			# find value kind options (list of ChoiceItem instances)
			ValueKindOptions = getattr(ThisPHAObj, ThisDataAttribName).ValueKindOptions if ThisDataAttribName else\
				ThisPHAObj.ValueKindOptions
			ApplicableValueKindOptionsList = [u.Applicable for u in ValueKindOptions]
			# select the current value kind in ValueKindOptions
			ThisValueKindName = ValueKindOptions[ApplicableValueKindOptionsList.index(True)].XMLName\
				if True in ApplicableValueKindOptionsList else None
			ThisValueKind = core_classes.NumValueClasses[ [c.XMLName for c in core_classes.NumValueClasses].index(
				ThisValueKindName)] if ThisValueKindName else None
			# set widgets that depend on value kind
			if ThisValueKind == core_classes.ParentNumValueItem:
				VisibleList.extend([self.NumericalValueAspect.CopyFromButton, self.NumericalValueAspect.ShowMeCopyFromButton])
			elif ThisValueKind == core_classes.UseParentValueItem:
				VisibleList.extend([self.NumericalValueAspect.LinkFromButton, self.NumericalValueAspect.ShowMeLinkFromButton])
			elif ThisValueKind == core_classes.ConstNumValueItem:
				VisibleList.extend([self.NumericalValueAspect.ConstantLabel, self.NumericalValueAspect.ConstantChoice,
					self.NumericalValueAspect.EditConstantsButton])
			elif ThisValueKind == core_classes.LookupNumValueItem:
				VisibleList.extend([self.NumericalValueAspect.MatrixLabel, self.NumericalValueAspect.MatrixChoice,
									self.NumericalValueAspect.EditMatricesButton])
			# set IsVisible attribs
			for ThisWidget in self.NumericalValueAspect.WidgetList:
				ThisWidget.IsVisible = (ThisWidget in VisibleList)

		def NumericalValueAspect_OnCommentButton(self, Event): pass

		def NumericalValueAspect_OnValueTextWidget(self, Event, WidgetObj=None):
			# handle end-of-editing (loss of focus) or Enter key press on value text widget
			# if invoked from Enter keypress, find widget object containing text widget
			if Event:
				EventWidget = Event.GetEventObject()
				ThisWidgetObj = [w for w in self.NumericalValueAspect.WidgetList if w.Widget == EventWidget][0]
				EventWidget.SelectAll() # select all text in the widget, as visual indicator to user that <Enter> worked
			else: ThisWidgetObj = WidgetObj
			# get value entered by user
			UserEntry = ThisWidgetObj.Widget.GetValue()
			if self.TopLevelFrame.CurrentViewport: # Confirm that Viewport still exists; it might have been destroyed
				# if we just did undo of viewport creation
				# get Viewport to request value change (no validation here; done in datacore)
				print('CF1238 DataAttrib:', ThisWidgetObj.DataAttrib)
				# find name of component (if any) whose value we are updating
				ValueAttribName = getattr(ThisWidgetObj.PHAObj, ThisWidgetObj.DataAttrib).InternalName if ThisWidgetObj.DataAttrib\
					else 'Value'
				self.TopLevelFrame.CurrentViewport.RequestChangeText(ElementID=ThisWidgetObj.PHAObj.ID,
					EditComponentInternalName=ValueAttribName, NewValue=UserEntry)

		def NumericalValueAspect_OnUnitWidget(self, Event):
			# handle change of selection in unit Choice widget
			# get option selected by user
			EventWidget = Event.GetEventObject()
			UserSelection = EventWidget.GetSelection()
			if UserSelection != wx.NOT_FOUND: # is any item selected?
				# find widget object
				ThisWidgetObj = [w for w in self.NumericalValueAspect.WidgetList if w.Widget == EventWidget][0]
				# find host object of UnitOptions, and matching edit component name
				if ThisWidgetObj.DataAttrib:
					HostObj = getattr(ThisWidgetObj.PHAObj, ThisWidgetObj.DataAttrib)
					EditComponentName = HostObj.InternalName
				else:
					HostObj = ThisWidgetObj.PHAObj
					# check if we're editing an FT gate (ugly; this module shouldn't care what the PHA model is)
					EditComponentName = 'GateValueUnit' if isinstance(HostObj, faulttree.FTGate) else 'EventValueUnit'
				# find XML name of unit requested
				TargetUnitName = HostObj.UnitOptions[EventWidget.GetSelection()].XMLName
				# get Viewport to request unit change (no validation here; done in datacore)
				self.TopLevelFrame.CurrentViewport.RequestChangeChoice(ElementID=ThisWidgetObj.PHAObj.ID,
					EditComponentInternalName=EditComponentName,
					AttribName='Unit', NewValue=TargetUnitName)

		def NumericalValueAspect_OnValueKindWidget(self, Event):
			# handle change of selection in number kind Choice widget
			# get option selected by user
			EventWidget = Event.GetEventObject()
			UserSelection = EventWidget.GetSelection()
			if UserSelection != wx.NOT_FOUND: # is any item selected?
				# find widget object and attrib containing value kind options
				ThisWidgetObj = [w for w in self.NumericalValueAspect.WidgetList if w.Widget == EventWidget][0]
				OptionsAttrib = getattr(ThisWidgetObj.PHAObj, ThisWidgetObj.DataAttrib) if ThisWidgetObj.DataAttrib\
					else ThisWidgetObj.PHAObj
				# find XML name of number kind requested
				TargetUnitName = OptionsAttrib.ValueKindOptions[EventWidget.GetSelection()].XMLName
				# get Viewport to request number kind change (no validation here; done in datacore)
				self.TopLevelFrame.CurrentViewport.RequestChangeChoice(ElementID=ThisWidgetObj.PHAObj.ID,
					EditComponentInternalName=OptionsAttrib.InternalName,
					AttribName='NumberKind', NewValue=TargetUnitName)

		def NumericalValueAspect_OnLinkFromButton(self, Event): pass

		def NumericalValueAspect_OnShowMeLinkFromButton(self, Event): pass

		def NumericalValueAspect_OnCopyFromButton(self, Event): pass

		def NumericalValueAspect_OnShowMeCopyFromButton(self, Event): pass

		def NumericalValueAspect_OnConstantWidget(self, Event): pass

		def NumericalValueAspect_OnEditConstantsButton(self, Event): pass

		def NumericalValueAspect_OnMatrixWidget(self, Event): pass

		def NumericalValueAspect_OnEditMatricesButton(self, Event): pass

		def MakeFaultTreeAspect(self): # make Fault Tree aspect
			# make basic attribs needed for the aspect
			MyNotebookPage = wx.Panel(parent=self.MyNotebook)
			MyTabText = _('Fault Tree') # text appearing on notebook tab
			self.FaultTreeAspect = self.ControlPanelAspectItem(InternalName='FaultTree', ParentFrame=self,
				TopLevelFrame=self.TopLevelFrame, PrefillMethod=self.PrefillWidgetsForFaultTreeAspect,
				SetWidgetVisibilityMethod=self.SetWidgetVisibilityforFaultTreeAspect, NotebookPage=MyNotebookPage,
				TabText=MyTabText)
			# make widgets
			self.MakeStandardWidgets(Scope=self.FaultTreeAspect, NotebookPage=MyNotebookPage)
			self.FaultTreeAspect.HeaderLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Fault Tree:')),
				ColLoc=3, ColSpan=1, GapX=20, Font=self.TopLevelFrame.Fonts['SmallHeadingFont'])
			self.FaultTreeAspect.FTNameText = UIWidgetItem(wx.TextCtrl(MyNotebookPage, -1,
				style=wx.TE_PROCESS_ENTER), MinSizeY=25,
				Events=[wx.EVT_TEXT_ENTER], Handler=self.FaultTreeAspect_OnFTNameTextWidget,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=4, ColSpan=1, DisplayMethod='StaticFromText')
				# this TextCtrl raises events in 2 ways: (1) <Enter> key raises wx.EVT_TEXT_ENTER, (2) loss of focus is
				# caught by OnIdle().
			self.FaultTreeAspect.FTDescriptionLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Description:')),
				ColLoc=6, ColSpan=1, GapX=20)
			self.FaultTreeAspect.FTDescriptionText = UIWidgetItem(wx.TextCtrl(MyNotebookPage, -1,
				style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE), MinSizeY=25,
				Events=[wx.EVT_TEXT_ENTER], Handler=self.FaultTreeAspect_OnFTDescriptionWidget,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=7, ColSpan=2, DisplayMethod='StaticFromText')
			self.FaultTreeAspect.ViewLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('FT view:')),
				ColLoc=9, ColSpan=1)
			self.FaultTreeAspect.ViewNameText = UIWidgetItem(wx.TextCtrl(MyNotebookPage, -1,
				style=wx.TE_PROCESS_ENTER), MinSizeY=25,
				Events=[wx.EVT_TEXT_ENTER], Handler=self.FaultTreeAspect_OnFTNameTextWidget,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=10, ColSpan=1, DisplayMethod='StaticFromText')
			self.FaultTreeAspect.GoToFTLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Go to FT:')),
				ColLoc=3, ColSpan=1)
			self.FaultTreeAspect.GoToFTChoice = UIWidgetItem(wx.Choice(MyNotebookPage, -1, size=(200, 25), choices=[]),
				  Handler=self.FaultTreeAspect_OnGoToFTChoice, Events=[wx.EVT_CHOICE], ColLoc=4, ColSpan=1)
			self.FaultTreeAspect.GoToViewLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Go to view:')),
				ColLoc=9, ColSpan=1)
			self.FaultTreeAspect.GoToViewChoice = UIWidgetItem(wx.Choice(MyNotebookPage, -1, size=(200, 25), choices=[]),
				  Handler=self.FaultTreeAspect_OnGoToViewChoice, Events=[wx.EVT_CHOICE], ColLoc=10, ColSpan=1)
			self.FaultTreeAspect.CommentButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Comment')),
				Handler=self.FaultTreeAspect_OnCommentButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=7, ColSpan=1,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.FaultTreeAspect.ActionButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Action')),
				Handler=self.FaultTreeAspect_OnActionButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=8, ColSpan=1,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			self.FaultTreeAspect.Divider1 = UIWidgetItem(wx.StaticLine(MyNotebookPage, -1, size=(500, 5),
				style=wx.LI_HORIZONTAL), NewRow=True,
				ColLoc=3, ColSpan=5, LeftMargin=10, GapY=10,
				Flags=wx.ALL | wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_CENTER)
			self.FaultTreeAspect.ProblemLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Problem:')),
				ColLoc=3, ColSpan=1, NewRow=True)
			self.FaultTreeAspect.ProblemDescription = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, ''),
				ColLoc=4, ColSpan=4)
			self.FaultTreeAspect.ProblemShowMeButton = UIWidgetItem(wx.Button(MyNotebookPage, -1, _('Show me')),
				Handler=self.FaultTreeAspect_OnProblemShowMeButton,
				Events=[wx.EVT_BUTTON],
				ColLoc=9, ColSpan=1,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND)
			# make list of all widgets in this aspect
			self.FaultTreeAspect.WidgetList = [self.FaultTreeAspect.NavigateBackButton,
				self.FaultTreeAspect.NavigateForwardButton,
				self.FaultTreeAspect.HeaderLabel, self.FaultTreeAspect.FTNameText,
				self.FaultTreeAspect.FTDescriptionLabel, self.FaultTreeAspect.FTDescriptionText,
				self.FaultTreeAspect.ViewLabel, self.FaultTreeAspect.ViewNameText,
				self.FaultTreeAspect.UndoButton, self.FaultTreeAspect.RedoButton,
				self.FaultTreeAspect.GoToFTLabel, self.FaultTreeAspect.GoToFTChoice,
				self.FaultTreeAspect.GoToViewLabel, self.FaultTreeAspect.GoToViewChoice,
				self.FaultTreeAspect.CommentButton, self.FaultTreeAspect.ActionButton,
				self.FaultTreeAspect.Divider1,
				self.FaultTreeAspect.ProblemLabel, self.FaultTreeAspect.ProblemDescription,
				self.FaultTreeAspect.ProblemShowMeButton]

		def PrefillWidgetsForFaultTreeAspect(self, **Args):
			Proj = self.TopLevelFrame.CurrentProj
			AllFTsInProj = [p for p in Proj.PHAObjShadows if type(p) is faulttree.FTObjectInCore]
			CurrentViewport = self.TopLevelFrame.CurrentViewport
			# keep a record of which FT is on display
			CurrentFT = self.TopLevelFrame.PHAObjInControlPanel = Args['PHAObjInControlPanel']
			# enable navigation buttons if there are any items in current project's history lists
			self.UpdateNavigationButtonStatus(Proj)
			# set widget values
			# set up FTNameText and FTDescriptionText
			# 	TODO limit length displayed. Smart ellipsization? Also in GoToFTChoice and ViewNameText
			self.FaultTreeAspect.FTNameText.Widget.ChangeValue(CurrentFT.HumanName)
			self.FaultTreeAspect.FTNameText.Widget.SelectAll()
			self.FaultTreeAspect.FTDescriptionText.Widget.ChangeValue(CurrentFT.Description)
			self.FaultTreeAspect.FTDescriptionText.Widget.SelectAll()
			# set up GoToFTChoice
			self.FaultTreeAspect.GoToFTChoice.Widget.Set([p.HumanName for p in AllFTsInProj])
			# preselect current FT in GoToFTChoice
			ApplicablePHAObjsList = [p.Applicable for p in Proj.PHAObjShadows]
			self.FaultTreeAspect.GoToFTChoice.Widget.SetSelection(ApplicablePHAObjsList.index(True)
				if True in ApplicablePHAObjsList else wx.NOT_FOUND)
			# set up ViewNameText
			self.FaultTreeAspect.ViewNameText.Widget.ChangeValue(CurrentViewport.HumanName)
			# set up GoToViewChoice
			ViewportsInThisPHAObj = [v for v in Proj.AllViewportShadows if v.PHAObj.ID == CurrentFT.ID]
			ViewportIDs = [v.ID for v in ViewportsInThisPHAObj]
			self.FaultTreeAspect.GoToViewChoice.Widget.Set([v.HumanName for v in ViewportsInThisPHAObj])
			# preselect current Viewport in GotoViewChoice
			self.FaultTreeAspect.GoToViewChoice.Widget.SetSelection(ViewportIDs.index(CurrentViewport.ID)
				if CurrentViewport.ID in ViewportIDs else wx.NOT_FOUND)
			# set problem-related widgets TODO use self.TopLevelFrame.CurrentValueProblem

		def SetWidgetVisibilityforFaultTreeAspect(self, **Args): # set IsVisible attrib for each widget
			# set widgets that are always visible
			VisibleList = [self.FaultTreeAspect.NavigateBackButton,
				self.FaultTreeAspect.NavigateForwardButton, self.FaultTreeAspect.HeaderLabel,
				self.FaultTreeAspect.FTNameText, self.FaultTreeAspect.FTDescriptionLabel,
				self.FaultTreeAspect.UndoButton, self.FaultTreeAspect.RedoButton,
				self.FaultTreeAspect.FTDescriptionText, self.FaultTreeAspect.GoToFTLabel,
				self.FaultTreeAspect.GoToFTChoice, self.FaultTreeAspect.CommentButton,
				self.FaultTreeAspect.ActionButton, self.FaultTreeAspect.Divider1,
				self.FaultTreeAspect.ViewLabel, self.FaultTreeAspect.ViewNameText,
				self.FaultTreeAspect.GoToViewLabel, self.FaultTreeAspect.GoToViewChoice]
			# set visibility for problem-related widgets
			ProblemVisible = bool(self.TopLevelFrame.CurrentValueProblem)
			if ProblemVisible: VisibleList.extend( [self.FaultTreeAspect.ProblemLabel,
				self.FaultTreeAspect.ProblemDescription, self.FaultTreeAspect.ProblemShowMeButton] )
			# set IsVisible attribs
			for ThisWidget in self.NumericalValueAspect.WidgetList:
				ThisWidget.IsVisible = (ThisWidget in VisibleList)

		def FaultTreeAspect_OnFTNameTextWidget(self, Event, **Args):
			print('CF1360 in handler for FT name widget; not coded yet')

		def FaultTreeAspect_OnViewNameTextWidget(self, Event, **Args): pass
		def FaultTreeAspect_OnFTDescriptionWidget(self, Event, **Args): pass

		def FaultTreeAspect_OnGoToFTChoice(self, Event, **Args):
			# handle change of option in GotoFT choice widget
			Proj = self.TopLevelFrame.CurrentProj
			# first, find out which FT was requested
			FTIndex = Event.GetEventObject().GetSelection()
			if FTIndex != wx.NOT_FOUND: # is any item selected?
				FTRequestedID = [p for p in Proj.PHAObjShadows if type(p) is faulttree.FTObjectInCore][FTIndex].ID
				# requested different FT from the one on display?
				if FTRequestedID != self.TopLevelFrame.CurrentViewport.PHAObj.ID:
					self.TopLevelFrame.SwitchToPHAObj(Proj=Proj, TargetPHAObjID=FTRequestedID)

		def FaultTreeAspect_OnGoToViewChoice(self, Event, **Args): pass
		def FaultTreeAspect_OnCommentButton(self, Event, **Args): pass
		def FaultTreeAspect_OnActionButton(self, Event, **Args): pass
		def FaultTreeAspect_OnProblemShowMeButton(self, Event, **Args): pass

		def MakeFTConnectorOutAspect(self): # make Fault Tree connector-out aspect for Control Panel
			# make basic attribs needed for the aspect
			MyNotebookPage = wx.Panel(parent=self.MyNotebook)
			MyTabText = _('Outward connector') # text appearing on notebook tab
			self.FTConnectorOutAspect = self.ControlPanelAspectItem(InternalName='FTConnectorOut', ParentFrame=self,
				TopLevelFrame=self.TopLevelFrame, PrefillMethod=self.PrefillWidgetsForFTConnectorOutAspect,
				SetWidgetVisibilityMethod=self.SetWidgetVisibilityforFTConnectorOutAspect, NotebookPage=MyNotebookPage,
				TabText=MyTabText)
			# make fixed widgets (this aspect also has variable widgets depending on the number of associated connector-ins)
			self.MakeStandardWidgets(Scope=self.FTConnectorOutAspect, NotebookPage=MyNotebookPage)
			self.FTConnectorOutAspect.HeaderLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Outward connector:')),
				ColLoc=3, ColSpan=1, GapX=20, Font=self.TopLevelFrame.Fonts['SmallHeadingFont'])
			self.FTConnectorOutAspect.ConnectorNameText = UIWidgetItem(wx.TextCtrl(MyNotebookPage, -1,
				style=wx.TE_PROCESS_ENTER), MinSizeY=25,
				Events=[wx.EVT_TEXT_ENTER], Handler=self.FTConnectorOutAspect_OnConnectorNameTextWidget,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=4, ColSpan=1, DisplayMethod='StaticFromText')
				# this TextCtrl raises events in 2 ways: (1) <Enter> key raises wx.EVT_TEXT_ENTER, (2) loss of focus is
				# caught by OnIdle().
			self.FTConnectorOutAspect.ConnectorDescriptionLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1, _('Description:')),
				ColLoc=6, ColSpan=1, GapX=20)
			self.FTConnectorOutAspect.ConnectorDescriptionText = UIWidgetItem(wx.TextCtrl(MyNotebookPage, -1,
				style=wx.TE_PROCESS_ENTER | wx.TE_MULTILINE), MinSizeY=25,
				Events=[wx.EVT_TEXT_ENTER], Handler=self.FTConnectorOutAspect_OnConnectorDescriptionWidget,
				Flags=wx.ALIGN_CENTER_VERTICAL | wx.ALIGN_LEFT | wx.EXPAND,
				MinSizeX=200, ColLoc=7, ColSpan=2, DisplayMethod='StaticFromText')
			self.FTConnectorOutAspect.ConnectToLabel = UIWidgetItem(wx.StaticText(MyNotebookPage, -1,
				_('Connected to:')), ColLoc=3, ColSpan=1)
			self.FTConnectorOutAspect.ConnectorInPlaceholder = UIWidgetPlaceholderItem(Name='ConnectorIn')
			# make list of all fixed widgets in this aspect
			self.FTConnectorOutAspect.FixedWidgetList = [self.FTConnectorOutAspect.NavigateBackButton,
				self.FTConnectorOutAspect.NavigateForwardButton,
				self.FTConnectorOutAspect.HeaderLabel, self.FTConnectorOutAspect.ConnectorNameText,
				self.FTConnectorOutAspect.ConnectorDescriptionLabel, self.FTConnectorOutAspect.ConnectorDescriptionText,
				self.FTConnectorOutAspect.UndoButton, self.FTConnectorOutAspect.RedoButton,
				self.FTConnectorOutAspect.ConnectToLabel, self.FTConnectorOutAspect.ConnectorInPlaceholder]
			self.FTConnectorOutAspect.VariableWidgetList = [] # populated in LineupVariableWidgetsForFTConnectorOutAspect()
			self.FTConnectorOutAspect.WidgetList = [] # complete widget list, populated in Lineup...()

		def LineupVariableWidgetsForFTConnectorOutAspect(self, ConnectorOut, NotebookPage):
			# adjust variable widgets in FT Connector-out aspect of Control Panel
			# depending on number of connector-in's to which this Connector-Out is connected
			# NotebookPage: parent window for the variable widgets
			# first, deactivate and destroy all existing variable widgets (to avoid memory leak)
			self.FTConnectorOutAspect.Deactivate(Widgets=self.FTConnectorOutAspect.VariableWidgetList)
			for ThisWidget in self.FTConnectorOutAspect.VariableWidgetList: ThisWidget.Widget.Destroy()
			self.FTConnectorOutAspect.VariableWidgetList = []
			# make a name widget and 'remove' button for each connector-in
			# RowOffset and ColOffset are offsets from the position of the placeholder in FixedWidgetList
			for (ThisConnectorInIndex, ThisConnectorIn) in enumerate(ConnectorOut.ConnectorIns):
				self.FTConnectorOutAspect.VariableWidgetList.append(UIWidgetItem(wx.TextCtrl(NotebookPage, -1,
					ThisConnectorIn.HumanName, style=wx.TE_READONLY), RowOffset=ThisConnectorInIndex, ColOffset=0,
					ColSpan=1, ConnectorInID=ThisConnectorIn.ID))
				DisconnectButtonWidget = UIWidgetItem(wx.Button(NotebookPage,
					size=self.StandardImageButtonSize), PHAObj=self.TopLevelFrame.PHAObjInControlPanel,
					RowOffset=ThisConnectorInIndex, ColOffset=1, ColSpan=1, Events=[wx.EVT_BUTTON],
					Handler=self.FTConnectorOutAspect_OnConnectorInDisconnectButton, ConnectorInID=ThisConnectorIn.ID)
				self.FTConnectorOutAspect.VariableWidgetList.append(DisconnectButtonWidget)
				DisconnectButtonWidget.Widget.SetBitmap(self.TopLevelFrame.ButtonBitmap(wx.ART_MINUS))
			# find out whether any connector-ins are available as possible new connections for this connector-out
			NewConnectorInsAvailable = ConnectorOut.NewConnectorInsAvailable()
			if NewConnectorInsAvailable:
#				# add 'add' button at the bottom of the list of connector-ins
#				ConnectButtonWidget = UIWidgetItem(wx.Button(NotebookPage,
#					size=self.StandardImageButtonSize),
#					RowOffset=len(ConnectorOut.ConnectorIns), ColOffset=1, ColSpan=1, Events=[wx.EVT_BUTTON],
#					Handler=self.FTConnectorOutAspect_OnConnectorInConnectButton)
#				self.FTConnectorOutAspect.VariableWidgetList.append(ConnectButtonWidget)
#				ConnectButtonWidget.Widget.SetBitmap(self.TopLevelFrame.ButtonBitmap(wx.ART_PLUS))
				# add choice widget to add connection, with label
				NewConnectLabelWidget = UIWidgetItem(wx.StaticText(NotebookPage, -1,
					_('Add connection to:')), RowOffset=len(ConnectorOut.ConnectorIns),
					ColOffset=1, ColSpan=1)
				NewConnectChoiceWidget = UIWidgetItem(wx.Choice(NotebookPage, -1, size=(200, 30),
					choices=[c.HumanName for c in NewConnectorInsAvailable]),
					PHAObj=self.TopLevelFrame.PHAObjInControlPanel,
					Handler=self.NumericalValueAspect_OnNewConnectChoiceWidget, Events=[wx.EVT_CHOICE],
					RowOffset=len(ConnectorOut.ConnectorIns), ColOffset=2, ColSpan=1)
				self.FTConnectorOutAspect.VariableWidgetList.append(NewConnectLabelWidget)
				self.FTConnectorOutAspect.VariableWidgetList.append(NewConnectChoiceWidget)
			else: # no new connector-ins available; add static text
				NoNewConnectorsMessage = UIWidgetItem(wx.StaticText(NotebookPage, -1,
					_('(No unused inward connectors available)')), RowOffset=len(ConnectorOut.ConnectorIns),
					ColOffset=1, ColSpan=1)
				self.FTConnectorOutAspect.VariableWidgetList.append(NoNewConnectorsMessage)
			# insert connector-in widgets into widget list, based on RowOffset and ColOffset
			self.FTConnectorOutAspect.WidgetList = self.InsertVariableWidgets(TargetPlaceholderName='ConnectorIn',
				FixedWidgets=self.FTConnectorOutAspect.FixedWidgetList,
				VariableWidgets=self.FTConnectorOutAspect.VariableWidgetList)

		def PrefillWidgetsForFTConnectorOutAspect(self, **Args):
			# populate widgets for FT Connector-out aspect of Control Panel
			Proj = self.TopLevelFrame.CurrentProj
			CurrentViewport = self.TopLevelFrame.CurrentViewport
			# capture which connector element is current
			self.TopLevelFrame.PHAObjInControlPanel = Args['PHAObjInControlPanel']
			self.TopLevelFrame.ComponentInControlPanel = Args['ComponentInControlPanel']
			# enable navigation buttons if there are any items in current project's history lists
			self.UpdateNavigationButtonStatus(Proj)
			# set widget values
			# set up ConnectorNameText and ConnectorDescriptionText
			# TODO limit length displayed. Smart ellipsization?
			self.FTConnectorOutAspect.ConnectorNameText.Widget.ChangeValue(
				self.TopLevelFrame.PHAObjInControlPanel.HumanName)
			self.FTConnectorOutAspect.ConnectorNameText.Widget.SelectAll()
			self.FTConnectorOutAspect.ConnectorNameText.PHAObj = self.TopLevelFrame.PHAObjInControlPanel
			self.FTConnectorOutAspect.ConnectorDescriptionText.Widget.ChangeValue(
				self.TopLevelFrame.PHAObjInControlPanel.Description)
			self.FTConnectorOutAspect.ConnectorDescriptionText.Widget.SelectAll()
			self.FTConnectorOutAspect.ConnectorDescriptionText.PHAObj = self.TopLevelFrame.PHAObjInControlPanel
			# set up lineup of variable widgets
			self.LineupVariableWidgetsForFTConnectorOutAspect(ConnectorOut=self.TopLevelFrame.PHAObjInControlPanel,
				NotebookPage=self.FTConnectorOutAspect.NotebookPage)

		def SetWidgetVisibilityforFTConnectorOutAspect(self, **Args): # set IsVisible attrib for each widget
			# set IsVisible attribs for all fixed and variable widgets
			for ThisWidget in self.FTConnectorOutAspect.WidgetList: ThisWidget.IsVisible = True

		def FTConnectorOutAspect_OnConnectorNameTextWidget(self, Event, **Args): pass
		def FTConnectorOutAspect_OnConnectorDescriptionWidget(self, Event, **Args): pass

		def FTConnectorOutAspect_OnConnectorInDisconnectButton(self, Event):
			# handle click on [-] button to disconnect a connector-in from a connector-out
			# find which connector-in to disconnect
			EventWidget = Event.GetEventObject()
			ThisWidgetObj = [w for w in self.FTConnectorOutAspect.WidgetList if w.Widget == EventWidget][0]
			ConnectorInToDisconnect = ThisWidgetObj.ConnectorInID
			# get Viewport to request disconnection
			self.TopLevelFrame.CurrentViewport.RequestDisconnectConnectorIn(ElementID=ThisWidgetObj.PHAObj.ID,
				ConnectorInToDisconnectID=ConnectorInToDisconnect)

		def FTConnectorOutAspect_OnConnectorInConnectButton(self, Event, ConnectorIn): pass

		def NumericalValueAspect_OnNewConnectChoiceWidget(self, Event, **Args):
			# handle user selection of Connector-In to connect to
			# get option selected by user
			EventWidget = Event.GetEventObject()
			UserSelection = EventWidget.GetSelection()
			if UserSelection != wx.NOT_FOUND: # is any item selected?
				# find widget object and attrib containing value kind options
				ThisWidgetObj = [w for w in self.FTConnectorOutAspect.WidgetList if w.Widget == EventWidget][0]
				OptionsAttrib = getattr(ThisWidgetObj.PHAObj, ThisWidgetObj.DataAttrib) if ThisWidgetObj.DataAttrib\
					else ThisWidgetObj.PHAObj
				# find XML name (= ID) of Connector-In requested
				TargetConnectorID = OptionsAttrib.ConnectorInsAvailable[EventWidget.GetSelection()].ID
				# get Viewport to request new connection
				self.TopLevelFrame.CurrentViewport.RequestNewConnectionToConnectorIn(ElementID=ThisWidgetObj.PHAObj.ID,
					TargetConnectorID=TargetConnectorID)

		class ControlPanelAspectItem(object): # class whose instances are aspects of the Control panel
			# attribs:
			# WidgetList (list): UIWidgetItem instances - widgets visible in the aspect
			# InternalName (str): name for debugging
			# ParentFrame (wx.Frame): reference to Control panel
			# TopLevelFrame (wx.Frame): reference to ControlFrame (needed for access to top level methods)
			# PrefillMethod (callable): method that prefills widget values for an instance
			# SetWidgetVisibilityMethod (callable): method that sets IsVisible flag for each widget
			# NotebookPage (wx.Panel): page in a wx.Notebook containing this aspect
			# TabText (str): human-readable name of the aspect, shown in aspect's notebook tab

			def __init__(self, WidgetList=[], InternalName='', ParentFrame=None, TopLevelFrame=None, PrefillMethod=None,
					SetWidgetVisibilityMethod=None, NotebookPage=None, TabText=''):
				assert isinstance(WidgetList, list) # can be empty at this stage
				assert isinstance(InternalName, str)
				assert isinstance(ParentFrame, wx.Panel)
				assert isinstance(TopLevelFrame, wx.Frame)
				assert callable(PrefillMethod)
				assert callable(SetWidgetVisibilityMethod)
				assert isinstance(NotebookPage, wx.Panel)
				assert isinstance(TabText, str)
				object.__init__(self)
				self.WidgetList = WidgetList[:]
				self.InternalName = InternalName
				self.ParentFrame = ParentFrame
				self.TopLevelFrame = TopLevelFrame
				self.PrefillMethod = PrefillMethod
				self.SetWidgetVisibilityMethod = SetWidgetVisibilityMethod
				self.NotebookPage = NotebookPage
				self.TabText = TabText
				self.IsInNotebook = False # whether the notebook currently has a tab for this aspect
				# make a sizer for the widgets (to be populated later)
				self.MySizer = wx.GridBagSizer(vgap=0, hgap=0) # make sizer for widgets
				self.NotebookPage.SetSizer(self.MySizer)

			def Activate(self, **Args): # activate widgets for this aspect
				print('CF1636 in Activate: received WidgetsToActivate: ', hasattr(Args, 'WidgetsToActivate'))
				Proj = self.ParentFrame.CurrentProj
				self.TopLevelFrame.ActivateWidgetsInPanel(Widgets=self.WidgetList, Sizer=self.MySizer,
					ActiveWidgetList=[w for w in self.WidgetList if w.IsVisible], **Args)

			def Deactivate(self, Widgets=[], **Args): # deactivate widgets for this aspect
				self.TopLevelFrame.DeactivateWidgetsInPanel(Widgets=Widgets, **Args)

			def Prefill(self, **Args): # initialise value of each appropriate widget in self.WidgetList
				self.PrefillMethod(**Args)

			def SetWidgetVisibility(self, **Args): # set IsVisible attrib of each widget in self.WidgetList
				self.SetWidgetVisibilityMethod(**Args)


	def ActivateWidgetsInPanel(self, Widgets=[], Sizer=None, ActiveWidgetList=[], **Args):
		# activate widgets that are about to be displayed in a panel of the Control Frame
		# Args may contain TextWidgets (list of text widgets to check for loss of focus in OnIdle)
		assert isinstance(Widgets, list)
		assert isinstance(Sizer, wx.GridBagSizer)
		assert isinstance(ActiveWidgetList, list)
		# set up widgets in their sizer
		display_utilities.PopulateSizer(Sizer=Sizer, Widgets=Widgets, ActiveWidgetList=ActiveWidgetList,
			DefaultFont=self.Fonts['NormalWidgetFont'], HighlightBkgColour=self.ColScheme.BackHighlight)
		# set widget event handlers for active widgets
		global KeyPressHash
		for ThisWidget in ActiveWidgetList:
			if ThisWidget.Handler:
				for Event in ThisWidget.Events:
					ThisWidget.Widget.Bind(Event, ThisWidget.Handler)
			# set keyboard shortcuts
			if getattr(ThisWidget, 'KeyStroke', None):
				KeyPressHash = vizop_misc.RegisterKeyPressHandler(
					KeyPressHash, ThisWidget.KeyStroke, ThisWidget.Handler, getattr(ThisWidget, 'KeyPressHandlerArgs', {}))

	def DeactivateWidgetsInPanel(self, Widgets=[], **Args):
		# deactivate widgets that are ceasing to be displayed in a panel of the Control Frame
		# TODO: do we need to delete any variable widgets?
		# unbind widget event handlers
		assert isinstance(Widgets, list)
		global KeyPressHash
		for ThisWidget in Widgets:
			if ThisWidget.Handler:
				for Event in ThisWidget.Events:
					ThisWidget.Widget.Unbind(Event)
			# disable keyboard shortcuts
			if getattr(ThisWidget, 'KeyStroke', None):
				KeyPressHash = vizop_misc.UnregisterKeyPressHandler(KeyPressHash, ThisWidget.KeyStroke)

	class ViewPanel(wx.Panel): # define the View panel in the control frame, used to provide selectors for current Viewports

		# main Viewpanel setup routine
		def __init__(self, wxParent, size, VTPanel, ColScheme):
			# VTPanel is the parent's VizopTalks panel
			wx.Panel.__init__(self, wxParent, -1, (0,0), size, wx.RAISED_BORDER)
			self.TopLevelFrame = wxParent
			self.ScaleX = self.ScaleY = 1.0 # scale factors depending on resolution of the physical device, to make
				# all panels look similarly scaled
			self.TolXInPx = self.TolYInPx = 2 # precision of clicking on objects & hotspots, in pixels
			self.ColScheme = ColScheme
			self.BackgColour = self.ColScheme.BackMid # set background colour
			self.Bind(wx.EVT_PAINT, self.OnPaint)
			self.LDragStatus = 'NotDragging' # whether we are dragging with left mouse button held down.
				# can be 'NotDragging', 'ReadyToDrag' (L button held down, but not enough motion yet),
				# 'NotAllowed' (L button held down, but can't drag this object), 'Dragging' (dragging in progress)
			self.ActiveWidgets = [] # instances of UIWidgetItem

		def RefreshViewPanel(self, Proj): # update view panel to reflect current display status
			print("CF1141 starting RefreshViewPanel, coding here")
#			self.DestroyActiveWidgets() # remove all active widgets

		def OnPaint(self, Event): pass

	class EditPanel(wx.Panel): # define the Edit panel in the control frame, used to display a Viewport

		# main EditPanel handling routine
		def __init__(self, wxParent, size, ViewportOwner=None, ColScheme=None):
			# ViewportOwner is the entity with attribute CurrentViewport
			wx.Panel.__init__(self, wxParent, -1, (0,0), size, wx.RAISED_BORDER)
			self.TopLevelFrame = wxParent
			self.ScaleX = self.ScaleY = 1.0 # scale factors depending on resolution of the physical device, to make
				# Viewports look similarly scaled on each device
			self.TolXInPx = self.TolYInPx = 2 # precision of clicking on objects & hotspots, in pixels
			self.ColScheme = ColScheme
			self.BackgColour = self.ColScheme.BackMid # set background colour
			self.ViewportOwner = ViewportOwner
			self.LatestViewport = {}
				# keys: PHAObj shadows; values: the latest Viewport for the respective PHAObj shown in this panel
			self.AllViewportsShown = [] # all Viewports shown in this display device in this Vizop instance
			self.Bind(wx.EVT_PAINT, self.OnPaint)
			self.LDragStatus = 'NotDragging' # whether we are dragging with left mouse button held down.
				# can be 'NotDragging', 'ReadyToDrag' (L button held down, but not enough motion yet),
				# 'NotAllowed' (L button held down, but can't drag this object), 'Dragging' (dragging in progress)

			# set up dialogue aspects
#			ft_full_report.MakeFTFullExportAspect(MyEditPanel=self, Fonts=self.TopLevelFrame.Fonts,
#				SystemFontNames=self.TopLevelFrame.SystemFontNames, DateChoices=core_classes.DateChoices)
#			self.EditPanelCurrentAspect = None # which dialogue aspect is currently active, if any

		def Redraw(self, FullRefresh=True):
			# full redraw of Viewport. FullRefresh (bool): whether to request redraw from scratch
			assert isinstance(FullRefresh, bool)
			if self.ViewportOwner.CurrentViewport:
				DC = wx.BufferedDC(wx.ClientDC(self))
				self.DoRedraw(DC, FullRefresh=FullRefresh)

		def DoRedraw(self, DC, FullRefresh=True): # redraw Viewport in DC provided
			# FullRefresh (bool): whether to request redraw from scratch
			assert isinstance(FullRefresh, bool)
			DC.SetBackground(wx.Brush(self.BackgColour))
			DC.Clear()
			self.ViewportOwner.CurrentViewport.RenderInDC(DC, FullRefresh=FullRefresh)
			# may need self.Refresh() here to invoke OnPaint()

		def ShowEmptyPanel(self): # clear edit panel display to background colour
			DC = wx.BufferedDC(wx.ClientDC(self))
			DC.SetBackground(wx.Brush(self.BackgColour))
			DC.Clear()

		def ReleaseViewportFromDisplDevice(self):
			# execute actions needed when display device is changing from one Viewport to another
			print('CF1755 clearing Viewport from display device')
			# first, do wrap-up actions in the Viewport
			self.ViewportOwner.CurrentViewport.ReleaseDisplayDevice(DisplDevice=self)
			self.TopLevelFrame.CurrentViewport = None # this probably isn't used, redundant
			# clear graphics
			self.ShowEmptyPanel()
			self.EditPanelMode(Viewport=None, NewMode='Blocked') # block user interaction with display device

		def EditPanelMode(self, Viewport=None, NewMode='Edit'):
			# set up mode for user interaction with Viewport panel. NewMode can be:
			# 'Edit', 'Select'
			# 'Blocked' (user cannot interact with Viewport contents)
			# 'Widgets' (Viewport contains only wx widgets, no clickable graphical objects)
			# If NewMode == 'Blocked', Viewport arg isn't required

			def OnMouseEntersViewportPanel(Event, Mode):
				assert Mode in info.EditPanelModes
				# define initial cursor type for each EditPanelMode. Values are keys in StockCursors
				CursorHash = {'Edit': 'Normal', 'Select': 'Normal', 'Blocked': 'Stop', 'Widgets': 'Normal'}
				wx.SetCursor(wx.Cursor(display_utilities.StockCursors[CursorHash[Mode]]))

			def OnMouseLeavesViewportPanel(event):
				wx.SetCursor(wx.Cursor(display_utilities.StockCursors['Normal']))
				# normal mouse pointer when outside content window

			def SetUp4EditText(): # set up handlers for request to edit object text
				global KeyPressHash
				self.Bind(wx.EVT_LEFT_DCLICK, self.OnMouseDoubleLClick)
				KeyPressHash = vizop_misc.RegisterKeyPressHandler(KeyPressHash, wx.WXK_F2, self.OnMouseDoubleLClick)

			# main procedure for EditPanelMode()
			assert NewMode in info.EditPanelModes
			self.Bind(wx.EVT_LEAVE_WINDOW, OnMouseLeavesViewportPanel) # change pointer when leaving display mode panel
			if (NewMode == 'Select'):
				self.Bind(wx.EVT_MOTION, lambda Event: self.OnMouseMoveEdit(Event, NewMode))
				self.Bind(wx.EVT_LEFT_DOWN, lambda Event: self.OnMouseLClickEdit(Event, Viewport=Viewport,
					CanStartDrag=True, CanSelect=True, Mode=NewMode))
				self.Bind(wx.EVT_LEFT_UP, lambda Event: self.OnMouseLUpEdit(Event, NewMode))
				SetUp4EditText()
				wx.SetCursor(wx.Cursor(display_utilities.StockCursors['Normal'])) # normal mouse pointer
				self.Unbind(wx.EVT_ENTER_WINDOW)
			elif (NewMode in ['Blocked', 'Widgets']):
				self.Unbind(wx.EVT_MOTION)
				self.Unbind(wx.EVT_LEFT_DOWN)
				self.Unbind(wx.EVT_LEFT_DCLICK)
				self.Bind(wx.EVT_ENTER_WINDOW, lambda Event: OnMouseEntersViewportPanel(Event=Event, Mode=NewMode))
					# bind method that changes mouse pointer when mouse enters display mode panel
			# set required mouse pointer style for current screen position
			display_utilities.SetPointer(Viewport, self, Event=None, Mode=NewMode)

		def OnPaint(self, event=None):
			if self.ViewportOwner.CurrentViewport:
				# redraw, if needed
				# TODO set PaintNeeded to False during text editing (seems like the blinking cursor in the TextCtrl triggers paint events)
				if getattr(self.ViewportOwner.CurrentViewport, 'PaintNeeded', True):
					MyPaintDC = wx.PaintDC(self)
					self.DoRedraw(MyPaintDC, FullRefresh=True)

		def OnMouseLClickEdit(self, event, Viewport, CanStartDrag=True, CanSelect=True, **Args):
			# handle mouse left button click inside EditPanel
			# if CanStartDrag, this click can be treated as start of dragging gesture
			# if CanSelect, click can change which Elements are selected
			# get mouse coords relative to EditPanel. Rappin p150
			if hasattr(Viewport, 'HandleMouseLClick'):
				MouseCoordX, MouseCoordY = event.GetPosition() # seems to be relative to panel position
				Viewport.HandleMouseLClick(MouseCoordX, MouseCoordY,
					Viewport.DisplDevice.TolXInPx, Viewport.DisplDevice.TolYInPx,
					CanStartDrag=CanStartDrag, CanSelect=CanSelect)
			if CanStartDrag: self.LDragStatus = 'ReadyToDrag'
			else: self.LDragStatus = 'NotAllowed'

		def OnMouseMoveEdit(self, Event, Mode): # handle mouse motion, with mouse button up or down
			display_utilities.SetPointer(self.ViewportOwner.CurrentViewport, self, Event, Mode=Mode)
			# check if we are dragging an object
			if Event.LeftIsDown() and (self.LDragStatus in ['ReadyToDrag', 'Dragging']): self.OnDragElement(Event)

		def OnMouseLUpEdit(self, Event, Mode): # handle mouse left button up, whether dragged or not
			(ScreenX, ScreenY) = Event.GetPosition() # get mouse coords. See Rappin p150
			self.LDragStatus = 'NotDragging' # unset DragInProgress flag
			# get Viewport to tidy up
			Viewport = self.ViewportOwner.CurrentViewport
			if hasattr(Viewport, 'HandleMouseLDragEnd'):
				Viewport.HandleMouseLDragEnd(ScreenX, ScreenY, Dragged=(self.LDragStatus == 'Dragging'))
			display_utilities.SetPointer(Viewport, self, Event, Mode=Mode)

		def OnDragElement(self, event): # handle mouse dragging of selected element(s).
			Viewport = self.ViewportOwner.CurrentViewport
			if hasattr(Viewport, 'HandleMouseLDrag'):
				(ScreenX, ScreenY) = event.GetPosition() # get mouse coords. See Rappin p150
				self.LDragStatus = 'Dragging'
				Viewport.HandleMouseLDrag(ScreenX, ScreenY)

		def OnMouseDoubleLClick(self, event=None, CanStartDrag=False, CanSelect=False, **Args):
			# handle left double click, or equivalent keypress: may invoke text edit mode
			Viewport = self.ViewportOwner.CurrentViewport
			if hasattr(Viewport, 'HandleMouseLDClick'):
				(MouseCoordX, MouseCoordY) = event.GetPosition()
				Viewport.HandleMouseLDClick(MouseCoordX, MouseCoordY,
					Viewport.DisplDevice.TolXInPx,
					Viewport.DisplDevice.TolYInPx,
					CanStartDrag=CanStartDrag, CanSelect=CanSelect, **Args)

		def OnMouseMClickEdit(self, event, Viewport, CanStartDrag=True, CanSelect=True):
			# handle mouse middle button click inside EditPanel
			# if CanStartDrag, this click can be treated as start of dragging gesture
			# if CanSelect, click can change which Elements are selected
			Viewport = self.ViewportOwner.CurrentViewport
			if hasattr(Viewport, 'HandleMouseMClick'):
				# get mouse coords relative to EditPanel. Rappin p150
				(ScreenX, ScreenY) = event.GetPosition()
				Viewport.HandleMouseMClick(ScreenX, ScreenY, CanStartDrag=CanStartDrag, CanSelect=CanSelect)

		def OnMouseRClickEdit(self, event, Viewport, CanStartDrag=True, CanSelect=True):
			# handle mouse right button click inside EditPanel
			# if CanStartDrag, this click can be treated as start of dragging gesture
			# if CanSelect, click can change which Elements are selected
			Viewport = self.ViewportOwner.CurrentViewport
			if hasattr(Viewport, 'HandleMouseRClick'):
				# get mouse coords relative to EditPanel. Rappin p150
				(ScreenX, ScreenY) = event.GetPosition()
				Viewport.HandleMouseRClick(ScreenX, ScreenY, CanStartDrag=CanStartDrag, CanSelect=CanSelect)

		def SetKeystrokeHandlerOnOff(self, On=True):
			# switch on or off keystroke handling
			assert isinstance(On, bool)
			self.Parent.KeyPressEnabled = On

		def GotoControlPanelAspect(self, AspectName, PHAObjInControlPanel, ComponentInControlPanel):
			# handle request from Viewport to change the aspect in the Control Panel
			self.TopLevelFrame.MyControlPanel.GotoControlPanelAspect(NewAspect=AspectName,
				PHAObjInControlPanel=PHAObjInControlPanel, ComponentInControlPanel=ComponentInControlPanel)

		# allow this display device to return DatacoreIsLocal value from parent frame
		DatacoreIsLocal = property(fget=lambda self: self.TopLevelFrame.DatacoreIsLocal)

	def OnExitVizopRequest(self, event): # Handle 'Exit Vizop' request from File menu, button press or keyboard shortcut
		ControlFrameData.Data['RequestToQuit'] = True # set return data for use by heart
		self.Destroy() # kills Control frame, raises EVT_CLOSE which calls self.OnClose()

	def SetupMenus(self): # initialize menus at the top of the screen
		# Any menu item which should be enabled/disabled depending on the current state of the Viewport should have
		# attributes "HostMenu" (wx.Menu instance) and  "InternalName" (str). Used in UpdateMenuStatus()
		# Set up the "File" menu
		FileMenu = wx.Menu()
		Openmitem = FileMenu.Append(-1, _('&Open Vizop project...'), '')
#		self.Bind(wx.EVT_MENU, self.OnProjectOpenRequest, Openmitem)
		Savemitem = FileMenu.Append(-1, _('&Save Vizop project'), '')
		self.Bind(wx.EVT_MENU, projects.SaveEntireProjectRequest, Savemitem)
		FileMenu.AppendSeparator() # add a separating line in the menu
		self.FTFullReportmitem = FileMenu.Append(-1, _('Export full Fault Tree...'), '')
		self.Bind(wx.EVT_MENU, self.OnExportFullFTRequest, self.FTFullReportmitem)
		self.FTFullReportmitem.HostMenu = FileMenu
		self.FTFullReportmitem.InternalName = 'FTFullExport'
		self.FileMenuSeparatorAfterViewportCommands = FileMenu.AppendSeparator()
		# InsertBeforeMe: list of  menu items to insert above this location
		self.FileMenuSeparatorAfterViewportCommands.InsertBeforeMe = [self.FTFullReportmitem]
		Aboutmitem = FileMenu.Append(-1, _('About &Vizop...'), '')
		self.Bind(wx.EVT_MENU, vizop_misc.OnAboutRequest, Aboutmitem) # OnAboutRequest is shared with welcome frame
		Quitmitem = FileMenu.Append(-1, _('E&xit Vizop'), '')
		self.Bind(wx.EVT_MENU, self.OnExitVizopRequest, Quitmitem)

		# Set up the "Edit" menu
		EditMenu = wx.Menu()
		self.UndoMenuItemID = wx.NewId()
		self.UndoMenuItem = EditMenu.Append(self.UndoMenuItemID, _('&Undo'), '')
		self.Bind(wx.EVT_MENU, self.OnUndoRequest, self.UndoMenuItem)
		self.RedoMenuItemID = wx.NewId()
		self.RedoMenuItem = EditMenu.Append(self.RedoMenuItemID, _('&Redo'), '')
		self.Bind(wx.EVT_MENU, self.OnRedoRequest, self.RedoMenuItem)

		# Create the menubar
		self.MenuBar = wx.MenuBar()
		# add menus to MenuBar
		self.MenuBar.Append(FileMenu, _('&File'))
		self.MenuBar.Append(EditMenu, _('&Edit'))
		self.SetMenuBar(self.MenuBar) # Add MenuBar to ControlFrame
		self.ViewportMenuItems = [self.FTFullReportmitem] #  menu items relating to Viewports that may need to be inserted/removed

	def UpdateMenuStatus(self): # update texts and stati of menu items in control frame
		Proj = self.CurrentProj
		# Undo menu item
		if Proj.UndoList:
			# find record that will be undone 'up to' (skipping over any chained records)
			LastRecordToUndo = Proj.UndoList[undo.FindLastRecordToUndo(Proj.UndoList)]
			UndoText = _(LastRecordToUndo.HumanText)
			self.UndoMenuItem.SetText((_('&Undo %s')) % UndoText)
			self.MenuBar.Enable(self.UndoMenuItemID, True)
		else: # nothing to undo
			self.UndoMenuItem.SetText(_('(Nothing to undo)'))
			self.MenuBar.Enable(self.UndoMenuItemID, False)
		# Redo menu item
		if Proj.RedoList:
			# find record that will be undone 'up to' (skipping over any chained records)
			LastRecordToRedo = Proj.RedoList[undo.FindLastRecordToUndo(Proj.RedoList)]
			RedoText = _(LastRecordToRedo.HumanText)
			self.RedoMenuItem.SetText((_('&Redo %s')) % RedoText)
			self.MenuBar.Enable(self.RedoMenuItemID, True)
		else: # nothing to redo
			self.RedoMenuItem.SetText(_('(Nothing to redo)'))
			self.MenuBar.Enable(self.RedoMenuItemID, False)
		# remove any unnecessary menu commands depending on Viewport state
		for (ThisMenu, ThisMenuLabel) in self.MenuBar.GetMenus():
			for ThisMenuItem in ThisMenu.GetMenuItems():
				# if the menu item has an InternalName, check if the InternalName is required by the current Viewporrt
				if hasattr(ThisMenuItem, 'InternalName'):
					if not (ThisMenuItem.InternalName in getattr(self.CurrentViewport, 'MenuCommandsAvailable', [])):
						ThisMenuItem.HostMenu.Remove(ThisMenuItem)
		# attach any necessary menu commands depending on Viewport state
		for ThisMenuItem in self.ViewportMenuItems:
			if (ThisMenuItem.InternalName in getattr(self.CurrentViewport, 'MenuCommandsAvailable', [])):
				# attach the menu item if it's not already in its host menu
				TargetMenu = ThisMenuItem.HostMenu
				if not (ThisMenuItem in TargetMenu.GetMenuItems()):
					# find the location to attach the menu item
					TargetIndex = [ThisMenuItem in getattr(i, 'InsertBeforeMe', [])
						for i in TargetMenu.GetMenuItems()].index(True)
					TargetMenu.Insert(pos=TargetIndex, menuItem=ThisMenuItem)

	def OnUndoRequest(self, Event): # handle Undo request from user
		# first, clear UndoChainWaiting flag possibly left over from last undo action
		global UndoChainWaiting
		ContinuePausedChain = UndoChainWaiting # store this; it means whether we are continuing an undo chain started before
		UndoChainWaiting = False
		ReturnArgs = undo.HandleUndoRequest(self.CurrentProj, SocketFromDatacoreName=self.SocketFromDatacoreName,
			ContinuingPausedChain=ContinuePausedChain)
		if not ReturnArgs['SkipRefresh']:
			pass # we don't refresh the GUI here (it's too early) - do it in SwitchToViewport() instead

	def OnRedoRequest(self, Event): # handle Redo request from user
		# first, clear RedoChainWaiting flag possibly left over from last redo action
		global RedoChainWaiting
		RedoChainWaiting = False
		ReturnArgs = undo.HandleRedoRequest(self.CurrentProj, RequestingControlFrameID=self.ID,
			SocketFromDatacoreName=self.SocketFromDatacoreName)
		if not ReturnArgs['SkipRefresh']: # update GUI
			self.UpdateMenuStatus() # update menu status to show next un/redoable action
			self.MyControlPanel.UpdateNavigationButtonStatus(Proj=self.CurrentProj)

	def OnClose(self, event):
		# do cleanup tasks when Control frame is closed. Called when EVT_CLOSE is raised
#		sm = settings.SettingsManager()
#		sm.set_value('main_frame_layout', self.layout_manager.SavePerspective())
#		# deinitialize the frame manager
#		self.layout_manager.UnInit()
		# delete the frame, returns control to main program in module heart for cleaning up
		self.Destroy()

	def OnIdle(self, Event): # during idle time, handle keystrokes for shortcuts, and listen to sockets.
		# Part of this procedure is repeated in module startup_vizop
		global KeyPressHash, UndoChainWaiting, RedoChainWaiting
		# initialise storage object used to remember keys pressed last time, for chord detection in correct order
		if not hasattr(self, 'PrevChordKeys'): self.PrevChordKeys = []
		KeysDownThisTime = [] # prepare list of key codes that are 'hit' and match any keys in KeyPressHash
		KeyPressIndexHit = None # which item (index in KeyPressHash) is to be invoked
		if self.KeyPressEnabled: # are we detecting keypresses?
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
			# add current project to Args, if not already there; then remove it again afterwards, so that it gets refreshed next time
			AddProjArg = ('Proj' not in Args)
			if AddProjArg: Args['Proj'] = self.CurrentProj
			Handler(**Args) # invoke handler
			if AddProjArg: del Args['Proj']
		# check for incoming messages
		MessageReceived = self.CheckForIncomingMessages()
		if not MessageReceived: # don't do the following if a message was received; leave 1 cycle to let it get processed
			# check if any undo/redo records are waiting
			if UndoChainWaiting: self.OnUndoRequest(Event=None)
			if RedoChainWaiting: self.OnRedoRequest(Event=None)
			# call CheckTextCtrlFocus routine for Edit Panel and Control Panel, to handle loss of focus of TextCtrl's
#			Viewport = self.MyEditPanel.ViewportOwner.CurrentViewport
#			if hasattr(Viewport, 'CheckTextCtrlFocus'): Viewport.CheckTextCtrlFocus()
			display_utilities.CheckTextCtrlFocus(HostPanel=self.MyEditPanel)
			display_utilities.CheckTextCtrlFocus(HostPanel=self.MyControlPanel)

	def ButtonBitmap(self, ImageName): # returns bitmap for button
		# ImageName can be the filename stub of an icon file in the runtime icons folder, or wx.ART_something
		# See https://wxpython.org/Phoenix/docs/html/wx.ArtProvider.html
		if isinstance(ImageName, str):
			return wx.BitmapFromImage(self.MyArtProvider.get_image(ImageName, (24, 24),
				conserve_aspect_ratio=True))
		else:
			return self.MyArtProvider.GetBitmap(id=ImageName, size=(24, 24))

	def NavigateToMilestone(self, Proj, MilestoneID=None, StoreForwardHistory=True):
		# display the milestone in Proj's backward history
		# MilestoneID (str containing integer): milestone to navigate to
		# StoreForwardHistory (bool): whether to store the existing state of the display as a milestone in forward history
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(MilestoneID, str)
		MilestoneIDs = [m.ID for m in Proj.BackwardHistory]
		assert MilestoneID in MilestoneIDs
		assert isinstance(StoreForwardHistory, bool)
		if StoreForwardHistory: self.StoreMilestone(Backward=False)
		# find the milestone in backward history, and its index in the history list
		MilestoneIndex = MilestoneIDs.index(MilestoneID)
		MilestoneToDisplay = Proj.BackwardHistory[MilestoneIndex]
		# clear backward history up to and including the milestone just displayed (do this before displaying the
		# milestone, so that the navigation button status gets updated)
		Proj.BackwardHistory = Proj.BackwardHistory[:MilestoneIndex]
		# display the Viewport in the milestone, if any
		if MilestoneToDisplay.Viewport: pass # TODO; include call to MyEditPanel.ReleaseViewportFromDisplDevice
		else: self.DisplayBlankViewport(Proj)

	def DisplayBlankViewport(self, Proj): # show empty edit panel (i.e. no Viewport) and update other panels appropriately
		# release current viewport from edit panel and blank the edit panel
		self.MyEditPanel.ReleaseViewportFromDisplDevice()
		# set control panel to PHA models aspect (expecting there to be no existing PHA models at this point)
		self.MyControlPanel.GotoControlPanelAspect(NewAspect=self.MyControlPanel.PHAModelsAspect)
		# refresh view panel
		self.MyViewPanel.RefreshViewPanel(Proj)
		# if there are no PHA models in the project, queue a VizopTalks prompt to create one
		self.InviteUserToCreatePHAModel(Proj)

	def StoreMilestone(self, Proj, Backward=True):
		# store current state of display in a milestone.
		# Backward (bool): if True, store the milestone in Proj's backward history list. If False, stor in forward history.
		print("CF1391 Starting StoreMilestone, not coded yet")

	def CheckForIncomingMessages(self):
		# check datacore and control frame sockets for incoming messages, and send to appropriate processing routines
		# return MessageReceived (bool); whether any message was received
		MessageReceived = False
		# 1. check sockets belonging to datacore: first, sockets bringing messages from control frames
		# find incoming sockets from control frames
		IncomingCFSocketObjs = [s for s in vizop_misc.RegisterSocket.Register
			if s.SocketLabel.startswith(info.ControlFrameInSocketLabel)]
		# check corresponding inward and outward sockets; Outward Socket is the socket whose label has the same suffix as Inward Socket
		for ThisSocketObj in IncomingCFSocketObjs:
			MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=ThisSocketObj.Socket, Handler=self.DatacoreHandleRequestFromControlFrame))
			MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=[s.Socket for s in vizop_misc.RegisterSocket.Register
				if s.SocketLabel == info.ControlFrameOutSocketLabel + '_' + ThisSocketObj.SocketLabel.split('_')[1]][0],
				Handler=None, SendReply2=False))
		# 2. check datacore sockets bringing messages from Viewports
		IncomingViewportSocketObjs = [s for s in vizop_misc.RegisterSocket.Register
			if s.BelongsToDatacore if s.Viewport is not None if 'REP' in s.SocketLabel]
		# check which Viewports sent messages, and send the message to the corresponding PHA model object
		ViewportMessageReceived = False
		for ThisSocketObj in IncomingViewportSocketObjs:
			# pass request to PHA model associated with the Viewport (we do this via datacore, not directly,
			# so that local and remote Viewports are treated the same)
			if ThisSocketObj.Viewport.PHAObj: # proceed only if Viewport has been assigned to a PHA object
				# (will not have happened yet if Viewport is newly created)
				ViewportMessageReceivedThisTime = vizop_misc.ListenToSocket(Proj=self.CurrentProj, Socket=ThisSocketObj.Socket,
					Handler=ThisSocketObj.Viewport.PHAObj.HandleIncomingRequest)
#				if ViewportMessageReceivedThisTime: print('CF1459 incoming viewport message received')
				ViewportMessageReceived |= bool(ViewportMessageReceivedThisTime)
				MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=[s.Socket for s in vizop_misc.RegisterSocket.Register
						if s.SocketLabel == info.ViewportOutSocketLabel + '_' + ThisSocketObj.SocketLabel.split('_')[1]][0],
						Handler=None, SendReply2=False))
		MessageReceived |= ViewportMessageReceived
		# update applicable Viewports, if any messages were received
		if ViewportMessageReceived:
			self.UpdateAllViewports(Proj=self.CurrentProj, Message=ViewportMessageReceivedThisTime)
		# 3. check sockets for any messages coming into the control frame, and process
		MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=self.zmqInwardSocket, Handler=self.HandleIncomingMessageToControlFrame))
		MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=self.zmqOutwardSocket, Handler=self.HandleIncomingReplyToControlFrame,
			SendReply2=False))
		# 4. likewise for control frame's current Viewport, if any
		if self.CurrentViewport:
			MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=self.CurrentViewport.C2DSocketREQ,
				Handler=self.HandleMessageToLocalViewport, SendReply2=False, OriginCode=11))
			# check messages from datacore's Viewport shadow to our local Viewports
			MessageReceived |= bool(vizop_misc.ListenToSocket(Socket=self.CurrentViewport.D2CSocketREP,
				Handler=self.HandleMessageToLocalViewport, SendReply2=True, OriginCode=12))
		# TODO should we discard incoming REQ messages to other Viewports that aren't currently on display?
		return MessageReceived

	def HandleIncomingMessageToControlFrame(self, MessageReceived=''):
		# handle incoming messages from datacore to control frame. Called from ListenToSockets() in module vizop_misc
		# parse incoming message to XML tree
		XMLRoot = ElementTree.fromstring(MessageReceived)
		# handlers for all possible notifications to Control Frame. Handler must send a reply
		Handler = {
			'NO_NewPHAModel_Undo': self.PostProcessNewPHAModel_Undo,
			'NO_NewPHAModel_Redo': self.PostProcessNewPHAModel_Redo,
			'NO_NewViewport_Undo': self.PostProcessNewViewport_Undo,
			'NO_NewViewport_Redo': self.PostProcessNewViewport_Redo,
			'NO_FT_ChangeText_Undo': self.UpdateAllViewportsAfterUndo,
			info.NO_ShowViewport: self.ProcessSwitchToViewport
			}[XMLRoot.tag.strip()]
		# call handler, and return its reply
		Reply = Handler(XMLRoot=XMLRoot)
		assert Reply is not None, Handler.__name__ + ' sent no reply'
		return Reply

	def HandleIncomingReplyToControlFrame(self, MessageReceived='', **Args):
		# handle incoming reply messages from datacore to control frame. Called from ListenToSockets() in module vizop_misc
		# parse incoming message to XML tree
		XMLRoot = ElementTree.fromstring(MessageReceived)
		# handlers for all possible replies to Control Frame
		Handler = {'RP_NewViewport': self.PostProcessNewViewport,
			'RP_SwitchToViewport': self.PostProcessSwitchToViewport,
			'RP_NewPHAModel': self.PostProcessNewPHAModel,
			'RP_StopDisplayingViewport': self.PostProcessNoActionRequired
			}[XMLRoot.tag.strip()]
		# call handler, and return its reply
		Reply = Handler(XMLRoot)
		assert Reply is not None, Handler.__name__
		return Reply

	def DatacoreHandleRequestFromControlFrame(self, MessageReceived, **Args):
		# process a message from Control Frame to Datacore, e.g. to create a new Viewport
		# MessageReceived (bytes): XML message from control frame
		assert isinstance(MessageReceived, bytes)
		ParsedMsgRoot = ElementTree.XML(MessageReceived)
		# get project ID from message received
		ProjIDTagInXML = ParsedMsgRoot.find(info.ProjIDTag)
		# find the project with the ID provided
		Proj = self.Projects[ [p.ID for p in self.Projects].index(ProjIDTagInXML.text) ]
		# handlers for all possible requests from Control Frame. Handlers must return an XML reply message
		Handler = {'RQ_NewViewport': self.DatacoreDoNewViewport,
			'RQ_SwitchToViewport': self.DatacoreSwitchToViewport,
			'RQ_NewFTEventNotIPL': self.DatacoreDoNewFTEventNotIPL,
			'RQ_NewPHAObject': DatacoreDoNewPHAObj,
			'RQ_StopDisplayingViewport': DatacoreStopDisplayingViewport}[
			ParsedMsgRoot.tag.strip()]
		# call handler and collect reply XML tree to send back to Control Frame
		ReplyXML = Handler(Proj=Proj, XMLRoot=ParsedMsgRoot)
		return ReplyXML

	def DoNewViewportCommand(self, Proj, Redoing=False, **Args):
		# handle request for new Viewport in project Proj
		# Redoing (bool): whether we are redoing an undone "new Viewport" operation (currently not used)
		# Expected Args: ViewportClass (class of new Viewport); not needed if Redoing
		#	PHAModel (instance) to attach the Viewport to,
		#	Chain (bool): whether this new Viewport creation call is chained from another event (e.g. new PHA model)
		#	ViewportInRedoRecord (Viewport instance) if Redoing
		# Optional Args:
		#	ViewportToRevertTo (Viewport instance): Viewport to redisplay when this Viewport is destroyed
		assert isinstance(Redoing, bool)
		assert 'PHAModel' in Args
		assert isinstance(Args['Chain'], bool)
		if Redoing:
			assert isinstance(Args['ViewportInRedoRecord'], display_utilities.ViewportBaseClass)
		else:
			assert Args['ViewportClass'] in display_utilities.ViewportMetaClass.ViewportClasses
		# store a navigation milestone to go back to, in case the user undoes creating a new PHA model
		NewMilestone = core_classes.MilestoneItem(Proj=Proj, DisplDevice=self.MyEditPanel, Displayable=False)
		Proj.BackwardHistory.append(NewMilestone)
		# create new Viewport object, with communication sockets, or retrieve previously made Viewport if redoing
		if Redoing:
			NewViewport = Args['ViewportInRedoRecord']
			RequestToDatacore = 'RQ_NewViewport_Redo'
		else:
			# prepare dict of additional args for Viewport creation
			ArgsToSend = {}
			if Args.get('ViewportToRevertTo', None) is not None:
				ArgsToSend['ViewportToRevertTo'] = Args['ViewportToRevertTo']
			# create the Viewport
			NewViewport, D2CSocketNo, C2DSocketNo, VizopTalksArgs = display_utilities.CreateViewport(Proj,
				Args['ViewportClass'], DisplDevice=self.MyEditPanel, PHAObj=Args['PHAModel'], Fonts=self.Fonts,
				SystemFontNames=self.SystemFontNames, **ArgsToSend)
			RequestToDatacore = 'RQ_NewViewport'
		self.Viewports.append(NewViewport) # add it to the register for Control Frame
		self.TrialViewport = NewViewport # set as temporary current viewport, confirmed after successful creation
		# request datacore to create new viewport shadow
		NewViewportAttribs = {'ControlFrame': self.ID, info.SkipRefreshTag: utilities.Bool2Str(Args['Chain']),
			'ViewportClass': Args['ViewportClass'].InternalName, info.ProjIDTag: Proj.ID, 'Viewport': NewViewport.ID,
			info.PHAModelIDTag: Args['PHAModel'].ID, info.PHAModelTypeTag: Args['PHAModel'].InternalName,
			info.MilestoneIDTag: NewMilestone.ID, info.D2CSocketNoTag: str(D2CSocketNo),
			info.C2DSocketNoTag: str(C2DSocketNo), info.HumanNameTag: NewViewport.HumanName}
		vizop_misc.SendRequest(self.zmqOutwardSocket, Command=RequestToDatacore, **NewViewportAttribs)
		# show VizopTalks confirmation message
		if not Redoing:
			VizopTalksArgs.update( {'Priority': ConfirmationPriority} ) # set message priority
			self.MyVTPanel.SubmitVizopTalksMessage(**VizopTalksArgs)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def DoNewPHAModelCommand(self, Proj, PHAModelClass, **Args):
		# handle request for new PHA model in project Proj
		# Expected Args: PHAModelClass (class of new PHAModel)
		assert PHAModelClass in core_classes.PHAModelMetaClass.PHAModelClasses
		# make dictionary of command attribs (we make dict instead of putting attribs directly in the SendRequest() call
		# so that we can use standardized XML tag names from info module)
		AttribDict = {'ControlFrame': self.ID, info.PHAModelTypeTag: PHAModelClass.InternalName,
			info.ProjIDTag: Proj.ID}
		# request datacore to create new PHA object
		ReplyReceived = vizop_misc.SendRequest(self.zmqOutwardSocket, Command='RQ_NewPHAObject', FetchReply=False,
			**AttribDict)

	def PostProcessNewPHAModel(self, XMLRoot):
		# finish setting up new PHA model
		# find the project in which the PHA model was just created
		Proj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		# find the PHA model class just created
		NewPHAObjType = core_classes.PHAModelMetaClass.PHAModelClasses[
			[c.InternalName for c in core_classes.PHAModelMetaClass.PHAModelClasses].index(
				XMLRoot.find(info.PHAModelTypeTag).text)]
		# make initial Viewport for the PHA model
		ViewportType = NewPHAObjType.DefaultViewportType
		self.DoNewViewportCommand(Proj, ViewportClass=ViewportType, Chain=True,
			PHAModel=utilities.ObjectWithID(Proj.PHAObjShadows,
				TargetID=utilities.TextAsString(XMLRoot.find(info.PHAModelIDTag))))
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def PostProcessNewPHAModel_Undo(self, XMLRoot=None):
		# finish handling undo of "new PHA model"
		# we get the type of PHA model sent in, rather than trying to deduce it from the PHA model's ID number, because
		# the PHA model has now been destroyed (so exists only in the redo record, which we shouldn't rely on)
		global UndoChainWaiting
		Proj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Undone'), MainText=_("New PHA model: %s") %
			vizop_misc.PHAModelClassWithName(XMLRoot.find(info.PHAModelTypeTag).text).HumanName,
			Priority=ConfirmationPriority)
		# is this undo chained? If not, update display
		if not utilities.Bool2Str(XMLRoot.find(info.SkipRefreshTag).text):
			pass
			# any other back navigation to do here? Below is already done in PostProcessNewViewport_Undo
#			self.NavigateToMilestone(Proj=Proj, MilestoneID=XMLRoot.find(info.MilestoneIDTag).text, StoreForwardHistory=False)
#		self.UpdateMenuStatus() # duplicate; will be done in OnUndoRequest()
#		self.MyControlPanel.UpdateNavigationButtonStatus(Proj=self.CurrentProj)
		# set UndoChainWaiting flag to trigger any further undo items
		UndoChainWaiting = utilities.Bool2Str(XMLRoot.find(info.ChainWaitingTag).text)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def PostProcessNewPHAModel_Redo(self, XMLRoot=None):
		# finish handling redo of "new PHA model"
		Proj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Redone'), MainText=_("New PHA model: %s") %
			vizop_misc.PHAModelClassWithName(XMLRoot.find(info.PHAModelTypeTag).text).HumanName,
			Priority=ConfirmationPriority)
		# create a new Viewport from scratch. We don't attempt to retain and reinstate the old one, because it didn't
		# exist when the Undo record was created.
#		self.DoNewViewportCommand(Proj,
#			ViewportInRedoRecord=utilities.ObjectWithID(Proj.ActiveViewports, XMLRoot.find(info.ViewportTag).text),
#			Redoing=True, Chain=True,
#			PHAModel=utilities.ObjectWithID(core_classes.PHAModelBaseClass.AllPHAModelObjects,
#			utilities.TextAsString(XMLRoot.find(info.PHAModelIDTag))))
		ViewportType = vizop_misc.PHAModelClassWithName(XMLRoot.find(info.PHAModelTypeTag).text).DefaultViewportType
		self.DoNewViewportCommand(Proj, ViewportClass=ViewportType, Chain=True,
			PHAModel=utilities.ObjectWithID(core_classes.PHAModelBaseClass.AllPHAModelObjects,
			utilities.TextAsString(XMLRoot.find(info.PHAModelIDTag))))
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def PostProcessNoActionRequired(self, XMLRoot=None):
		# handle incoming RP_ message to Control Frame where no action is required
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def DoSwitchToViewportCommand(self, Proj, PHAObj, Viewport, Redoing=False, Chain=False, **Args):
		# handle request to switch to existing Viewport in project Proj
		# Redoing (bool): whether we are redoing an undone "switch to Viewport" operation (currently not used, can be removed)
		# Chain (bool): whether this new Viewport creation call is chained from another event (e.g. switch PHA model)
		# Possible Args:
		#	ViewportInRedoRecord (Viewport instance) if Redoing
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(PHAObj, core_classes.PHAModelBaseClass)
		assert isinstance(Viewport, display_utilities.ViewportBaseClass)
		assert isinstance(Redoing, bool)
		assert isinstance(Chain, bool)
		if Redoing:
			assert isinstance(Args['ViewportInRedoRecord'], display_utilities.ViewportBaseClass)
		# store a navigation milestone to go back to
		NewMilestone = core_classes.MilestoneItem(Proj=Proj, DisplDevice=self.MyEditPanel, Displayable=True)
		Proj.BackwardHistory.append(NewMilestone)
#		# create new Viewport object, with communication sockets, or retrieve previously made Viewport if redoing
#		if Redoing:
#			NewViewport = Args['ViewportInRedoRecord']
#			RequestToDatacore = 'RQ_NewViewport_Redo'
#		else:
#			NewViewport, D2CSocketNo, C2DSocketNo, VizopTalksArgs = display_utilities.CreateViewport(Proj,
#				Args['ViewportClass'], DisplDevice=self.MyEditPanel, PHAObj=Args['PHAModel'], Fonts=self.Fonts)
		RequestToDatacore = 'RQ_SwitchToViewport'
#		self.Viewports.append(NewViewport) # add it to the register for Control Frame
#		self.TrialViewport = NewViewport # set as temporary current viewport, confirmed after successful creation
#		# request datacore to create new viewport shadow
		# The attribs in the dict below are used in DatacoreSwitchToViewport(). Many of them are not currently used;
		# TODO remove unneeded attribs for bug resilience
		TargetViewportAttribs = {'ControlFrame': self.ID, info.SkipRefreshTag: utilities.Bool2Str(Chain),
			info.ProjIDTag: Proj.ID, info.ViewportTag: Viewport.ID,
			info.PHAModelIDTag: PHAObj.ID,
#			info.PHAModelIDTag: PHAObj.ID, info.PHAModelTypeTag: PHAObj.InternalName,
			info.MilestoneIDTag: NewMilestone.ID}
		vizop_misc.SendRequest(self.zmqOutwardSocket, Command=RequestToDatacore, **TargetViewportAttribs)
		# show VizopTalks confirmation message
		if not Redoing:
			self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Now showing %s:') % type(PHAObj).HumanName,
				MainText=PHAObj.HumanName + '\n\n' + _('Use back button to go back'), Priority=ConfirmationPriority)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def SwitchToPHAObj(self, Proj, TargetPHAObjID):
		# display most recently viewed Viewport of PHA object with ID == TargetPHAObj
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(TargetPHAObjID, str)
		assert TargetPHAObjID in [p.ID for p in Proj.PHAObjShadows]
		TargetPHAObj = Proj.PHAObjShadows[ [p.ID for p in Proj.PHAObjShadows].index(TargetPHAObjID) ]
		TargetViewport = self.MyEditPanel.LatestViewport[TargetPHAObj]
		self.DoSwitchToViewportCommand(Proj=Proj, PHAObj=TargetPHAObj, Viewport=TargetViewport)

	def PostProcessSwitchToViewport(self, XMLRoot):
		# get info on an existing Viewport from datacore in XMLRoot, and display the Viewport
		assert isinstance(XMLRoot, ElementTree.Element)
		Proj = self.CurrentProj
		# find the associated PHA object from the ID returned from datacore
		PHAObjIDTag = XMLRoot.find(info.IDTag)
		PHAObj = utilities.ObjectWithID(Proj.PHAObjShadows, utilities.TextAsString(PHAObjIDTag))
		# find the target Viewport from the ID returned from datacore (it's the text of the root tag)
		TargetViewport = utilities.ObjectWithID(self.MyEditPanel.AllViewportsShown, TargetID=XMLRoot.text)
		# set target Viewport as the current Viewport and release any existing Viewport from display device
		self.SwitchToViewport(TargetViewport=TargetViewport, XMLRoot=XMLRoot)
		# send acknowledgment message back (ListenToSockets does the actual sending)
		return vizop_misc.MakeXMLMessage('CP_SwitchToViewport', RootText='OK')

	def PostProcessNewViewport(self, XMLRoot):
		# get info on newly created Viewport from datacore in XMLRoot, and use it to finish
		# setting up new Viewport
		# TODO need to handle 'CantComply' sub-element in XMLRoot, indicating that Viewport can't be created.
		# (also in redo?)
		# In this instance, also need to delete the navigation history milestone that was added in DoNewViewportCommand()
		assert isinstance(XMLRoot, ElementTree.Element)
		# find the new PHA object from the ID returned from datacore
		PHAObjIDTag = XMLRoot.find(info.IDTag)
		PHAObj = utilities.ObjectWithID(core_classes.PHAModelBaseClass.AllPHAModelObjects,
			utilities.TextAsString(PHAObjIDTag))
		# find the new Viewport from the ID returned from datacore (it's the text of the root tag) for checking
		assert self.TrialViewport.ID == XMLRoot.text
		# attach Viewport to PHA object, and label its sockets
		self.TrialViewport.PHAObj = PHAObj
		self.TrialViewport.C2DSocketREQObj.PHAObj = self.TrialViewport.D2CSocketREPObj.PHAObj = PHAObj
		# set Viewport as the current Viewport and release any existing Viewport from display device
		self.SwitchToViewport(TargetViewport=self.TrialViewport, XMLRoot=XMLRoot)
		# send acknowledgment message back (ListenToSockets does the actual sending)
		return vizop_misc.MakeXMLMessage('CP_NewViewport', RootText='OK')

	def PostProcessNewViewport_Undo(self, XMLRoot=None):
		# finish handling undo of "new Viewport"
		global UndoChainWaiting
		Proj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Undone'), MainText=_("New Viewport: %s") %
			display_utilities.ViewportClassWithName(XMLRoot.find(info.ViewportTypeTag).text).HumanName,
			Priority=ConfirmationPriority)
		# update display, regardless of SkipRefresh tag in XMLRoot (we have to refresh now, because we have the
		# milestone to revert to)
#		if not utilities.Bool2Str(XMLRoot.find(info.SkipRefreshTag).text):
		self.NavigateToMilestone(Proj=Proj, MilestoneID=XMLRoot.find(info.MilestoneIDTag).text,
			StoreForwardHistory=False)
		# set UndoChainWaiting flag to trigger any further undo items
		UndoChainWaiting = utilities.Bool2Str(XMLRoot.find(info.ChainWaitingTag).text)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def PostProcessNewViewport_Redo(self, XMLRoot=None):
		# finish handling redo of "new Viewport"
		global UndoChainWaiting, RedoChainWaiting
		Proj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		# set trial Viewport (created in PostProcessNewPHAModel_Redo) as the current Viewport
		self.SwitchToViewport(TargetViewport=self.TrialViewport, XMLRoot=XMLRoot)
		# attach Viewport to PHA object, and label its sockets
		self.CurrentViewport.PHAObj = PHAObj
		self.CurrentViewport.C2DSocketREQObj.PHAObj = self.CurrentViewport.D2CSocketREPObj.PHAObj = PHAObj
		# set up the display in the PHA panel; now done in SwitchToViewport(), above
#		self.ShowViewport(MessageAsXMLTree=XMLRoot)
		# is this redo chained after another redo? If not, post a message in VizopTalks
		if not utilities.Bool2Str(XMLRoot.find(info.ChainedTag).text):
			self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Redone'), MainText=_("New Viewport: %s") %
				display_utilities.ViewportClassWithName(XMLRoot.find(info.ViewportTypeTag).text).HumanName,
				Priority=ConfirmationPriority)
#		# is there another redo chained after this redo? If not, update display
#		if not utilities.Bool2Str(XMLRoot.find(info.SkipRefreshTag).text):
#			self.NavigateToMilestone(Proj=Proj, MilestoneID=XMLRoot.find(info.MilestoneIDTag).text,
#				StoreForwardHistory=False)
		# set RedoChainWaiting flag to trigger any further redo items
		RedoChainWaiting = utilities.Bool2Str(XMLRoot.find(info.ChainWaitingTag).text)
		# send acknowledgment message back (ListenToSockets does the actual sending)
		return vizop_misc.MakeXMLMessage('Null', 'Null')
#		return {'Success': True, 'Notification': vizop_misc.MakeXMLMessage('Null', 'Null')}

	def ReleaseCurrentViewport(self, Proj):
		# release any Viewport currently showing in edit panel
		if self.CurrentViewport:
			# remove old Viewport from local ActiveViewports list
			Proj.ActiveViewports.remove(self.CurrentViewport)
			# tell datacore the Viewport is no longer on display
			AttribDict = {info.ProjIDTag: Proj.ID, 'ControlFrame': self.ID, info.ViewportTag: self.CurrentViewport.ID}
			self.MyEditPanel.ReleaseViewportFromDisplDevice()
			ReplyReceived = vizop_misc.SendRequest(self.zmqOutwardSocket, Command='RQ_StopDisplayingViewport',
				FetchReply=False, **AttribDict)
			self.CurrentViewport = None

	def SwitchToViewport(self, TargetViewport=None, XMLRoot=None):
		# switch edit panel display (in local ControlFrame) to show TargetViewport
		# TargetViewport is supplied directly as an arg, or (if it's None) via ViewportTag in XMLRoot
		# first, find which Viewport to show
		Proj = self.CurrentProj
		if TargetViewport is None: # don't use this route - requested viewport may not exist in Proj.ActiveViewports
			ViewportToShow = utilities.ObjectWithID(Objects=Proj.ActiveViewports,
				TargetID=XMLRoot.find(info.ViewportTag).text)
		else: ViewportToShow = TargetViewport
		assert isinstance(ViewportToShow, (ViewportShadow, display_utilities.ViewportBaseClass))
		if isinstance(ViewportToShow, display_utilities.ViewportBaseClass):
			print('CF2406 Warning: Viewport shadow is Viewport class, should be ViewportShadow class')
		# release any existing Viewport from PHA panel
		self.ReleaseCurrentViewport(Proj=Proj)
		# add target Viewport
		Proj.ActiveViewports.append(ViewportToShow)
		# set Viewport as current in Control Frame
		self.CurrentViewport = ViewportToShow
		# set current display device in Viewport
		ViewportToShow.DisplDevice = self.MyEditPanel
		# store Viewport as shown in edit panel
		if not (self.CurrentViewport in self.MyEditPanel.AllViewportsShown):
			self.MyEditPanel.AllViewportsShown.append(self.CurrentViewport)
		# set Viewport as the latest shown for this shadow PHAObj in this display device
		self.MyEditPanel.LatestViewport[ViewportToShow.PHAObj] = ViewportToShow
		# restore zoom and pan, if provided in XMLRoot
		if XMLRoot is not None:
			ThisZoomTag = XMLRoot.find(info.ZoomTag)
			TargetZoom = ThisZoomTag.text if ThisZoomTag else None
			ThisPanXTag = XMLRoot.find(info.PanXTag)
			TargetPanX = ThisXMLTag.text if ThisPanXTag else None
			ThisPanYTag = XMLRoot.find(info.PanYTag)
			TargetPanY = ThisPanYTag.text if ThisPanYTag else None
			display_utilities.ChangeZoomAndPanValues(Viewport=self.CurrentViewport, Zoom=TargetZoom, PanX=TargetPanX,
				PanY=TargetPanY)
		# store history for backward navigation
		self.StoreMilestone(Proj, Backward=True)
		# draw the Viewport
		self.ShowViewport(MessageAsXMLTree=XMLRoot)
		# update other GUI elements
		self.RefreshGUIAfterDataChange(Proj=Proj)
		# show appropriate aspect in Control Panel
		self.MyControlPanel.GotoControlPanelAspect(NewAspect=self.CurrentViewport.PreferredControlPanelAspect,
			PHAObjInControlPanel=self.CurrentViewport.PHAObj, ComponentInControlPanel=None)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def DatacoreDoNewViewport_Undo(self, Proj, UndoRecord, **Args): # undo creation of new Viewport
		global UndoChainWaiting
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(UndoRecord, undo.UndoItem)
#		# find out which Control Frame sent the undo request (so that we know which one to reply to)
#		RequestingControlFrameID = Args['RequestingControlFrameID']
		# find out which datacore socket to send messages on
		SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
		# find and remove the new Viewport object
		ViewportToRemove = UndoRecord.ViewportShadow
		Proj.AllViewportShadows.remove(ViewportToRemove)
		# tell Control Frame what we did
		Notification = vizop_misc.MakeXMLMessage(RootName='NO_NewViewport_Undo', RootText=ViewportToRemove.ID,
			Elements={info.MilestoneIDTag: UndoRecord.MilestoneID, info.SkipRefreshTag: UndoRecord.Chain,
			info.ViewportTypeTag: ViewportToRemove.MyClass.InternalName,
			info.ChainWaitingTag: utilities.Bool2Str(Args['ChainWaiting']),
			info.ProjIDTag: Proj.ID})
		vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket,
			Command='NO_NewViewport_Undo', XMLRoot=Notification)
#		vizop_misc.SendRequest(Socket=ControlFrameWithID(RequestingControlFrameID).C2FREQSocket.Socket,
#			Command='NO_NewViewport_Undo', XMLRoot=Notification)
		projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.ViewportTag,
			Elements={info.IDTag: ViewportToRemove.ID, info.DeleteTag: ''}))
		UndoChainWaiting = Args.get('ChainWaiting', False)
		return {'Success': True}

	def DatacoreDoNewViewport_Redo(self, Proj, RedoRecord, **Args): # redo creation of new Viewport
		# fetch the previously created Viewport shadow from the Redo record
		RecoveredViewport = RedoRecord.ViewportShadow
		# find the PHA object owning the Viewport
		ThisPHAObj = RecoveredViewport.PHAObj
		ThisPHAObj.Viewports.append(RecoveredViewport) # add Viewport to list in the PHA object
		# fetch full redraw data of Viewport
		RedrawXMLData = ThisPHAObj.GetFullRedrawData(Viewport=RecoveredViewport, ViewportClass=RecoveredViewport.MyClass)
		# send ID of PHA model, followed by full redraw data, as reply to ControlFrame
		Notification = vizop_misc.MakeXMLMessage(RootName='NO_NewViewport_Redo', RootText=RecoveredViewport.ID,
			Elements={info.ProjIDTag: ThisPHAObj.ID, info.ViewportTypeTag: RecoveredViewport.MyClass.InternalName,
			info.ChainWaitingTag: utilities.Bool2Str(Args['ChainWaiting']),
			info.ChainedTag: utilities.Bool2Str(Args['ChainUndo']) })
		Notification.append(RedrawXMLData)
		# store undo record
		undo.AddToUndoList(Proj, Redoing=True, UndoObj=undo.UndoItem(UndoHandler=self.DatacoreDoNewViewport_Undo,
			RedoHandler=self.DatacoreDoNewViewport_Redo, ViewportShadow=RecoveredViewport, Chain=Args['ChainUndo'],
			MilestoneID=RedoRecord.MilestoneID,
			HumanText=_('new Viewport: %s' % RecoveredViewport.MyClass.HumanName)))
		# send the info to control frame as a notification
		vizop_misc.SendRequest(Socket=ControlFrameWithID(Args['RequestingControlFrameID']).C2FREQSocket.Socket,
			Command='NO_NewViewport_Redo', XMLRoot=Notification)
		return {'Success': True, 'Notification': Notification}

	def DatacoreDoNewViewport(self, XMLRoot=None, Proj=None, ViewportClass=None, ViewportID=None, HumanName='',
		PHAModel=None, Chain='NoChain'):
		# datacore function to handle request for new Viewport from any Control Frame (local or remote)
		# It creates a Viewport shadow, i.e. an object that allows the datacore to know that a Viewport exists in
		# one of the Control Frames (local or remote).
		# input data is supplied in XMLRoot, an XML ElementTree root element, or as separate attribs
		# including Chain (str: 'NoChain' or 'Stepwise'): whether this call is chained from another event, e.g. new PHA model
		# return reply data (XML tree) to send back to respective Control Frame
		# This function might be better placed outside Control Frame class, but currently we can't because it needs
		# access to ControlFrame's self.Projects
		# First, get the attribs needed to make the Viewport in the datacore
		if XMLRoot is None: # this branch is not currently used
			ThisProj = Proj
			NewViewportClass = ViewportClass
			NewViewportID = ViewportID
			NewViewportHumanName = HumanName
			ExistingPHAObj = PHAModel
		else:
			ThisProj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
			ClassList = display_utilities.ViewportMetaClass.ViewportClasses # list of all user-requestable Viewports
			NewViewportClass = ClassList[[Cls.InternalName for Cls in ClassList].index(XMLRoot.find('ViewportClass').text)]
			NewViewportID = XMLRoot.find('Viewport').text
			NewViewportHumanName = XMLRoot.find(info.HumanNameTag).text
			ExistingPHAObj = utilities.ObjectWithID(ThisProj.PHAObjs, XMLRoot.find(info.PHAModelIDTag).text)
			Chain = 'Stepwise' # TODO need 'NoChain' if we are adding new Viewport to existing PHA model
		# check if we can proceed to create the Viewport; we may need editing rights (TODO remove this requirement)
		if Proj.EditAllowed:
			# make the Viewport shadow
			NewViewport = ViewportShadow(ThisProj, NewViewportID, MyClass=NewViewportClass,
				HumanName=NewViewportHumanName,
				D2CSocketNumber=int(XMLRoot.find(info.D2CSocketNoTag).text),
				C2DSocketNumber=int(XMLRoot.find(info.C2DSocketNoTag).text), PHAModel=ExistingPHAObj)
			# attach existing PHA object to the Viewport
			NewViewport.PHAObj = ExistingPHAObj
			NewViewport.IsOnDisplay = True # set flag that ensures NewViewport will get redrawn
			ExistingPHAObj.Viewports.append(NewViewport) # add Viewport to list in the PHA object
			# fetch full redraw data of new PHA object, and include in reply message to send to control frame
			Reply = self.MakeXMLMessageForDrawViewport(MessageHead='RP_NewViewport', PHAObj=ExistingPHAObj,
				Viewport=NewViewport, ViewportID=NewViewportID)
			undo.AddToUndoList(Proj, UndoObj=undo.UndoItem(UndoHandler=self.DatacoreDoNewViewport_Undo,
				RedoHandler=self.DatacoreDoNewViewport_Redo, ViewportShadow=NewViewport, Chain=Chain,
				MilestoneID=XMLRoot.find(info.MilestoneIDTag).text,
				HumanText=_('new Viewport: %s') % NewViewportClass.HumanName))
		else: # couldn't make Viewport because it needs a new PHA model and editing is blocked. Redundant
			Reply = vizop_misc.MakeXMLMessage(RootName='RP_NewViewport', RootText="Null",
				Elements={'CantComply': 'EditingBlocked'})
		# send the info back to control frame as a reply message (via ListenToSocket)
		return Reply

	def MakeXMLMessageForDrawViewport(self, MessageHead, PHAObj, Viewport, ViewportID):
		# make and return XML element containing message required for SwitchToViewport, with all required redraw data
		# MessageHead: command string required as XML root, e.g. 'RP_NewViewport'
		assert isinstance(MessageHead, str)
		assert isinstance(PHAObj, core_classes.PHAModelBaseClass)
		assert isinstance(Viewport, ViewportShadow)
		assert isinstance(ViewportID, str)
		# fetch full redraw data of new PHA object
		RedrawXMLData = PHAObj.GetFullRedrawData(Viewport=Viewport, ViewportClass=Viewport.MyClass)
		# put ID of PHA object, followed by full redraw data, into XML element
		Reply = vizop_misc.MakeXMLMessage(RootName=MessageHead, RootText=ViewportID, Elements={info.IDTag: PHAObj.ID})
		Reply.append(RedrawXMLData)
		return Reply

	def DatacoreSwitchToViewport(self, XMLRoot=None, Proj=None, ViewportClass=None, ViewportID=None, HumanName='',
			PHAObj=None, Chain='NoChain'):
		# datacore function to handle request to switch to an existing Viewport from any Control Frame (local or remote)
		# It assumes a Viewport shadow, i.e. an object that allows the datacore to know that a Viewport exists in
		# one of the Control Frames (local or remote), already exists for this Viewport.
		# Input data is supplied in XMLRoot, an XML ElementTree root element, or as separate attribs
		# including Chain (str: 'NoChain' or 'Stepwise'): whether this call is chained from another event, e.g. new PHA model
		# return reply data (XML tree) to send back to respective Control Frame
		# This function might be better placed outside Control Frame class, but currently we can't because it needs
		# access to ControlFrame's self.Projects
		# First, get the attribs needed to find the Viewport in the datacore
		if XMLRoot is None: # this branch is not currently used
			ThisProj = Proj
			TargetViewportClass = ViewportClass
			TargetViewportID = ViewportID
			TargetViewportHumanName = HumanName
			ExistingPHAObj = PHAObj
		else:
			ThisProj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
			ClassList = display_utilities.ViewportMetaClass.ViewportClasses # list of all user-requestable Viewport classes
			TargetViewportID = XMLRoot.find(info.ViewportTag).text
			TargetViewport = utilities.ObjectWithID(ThisProj.AllViewportShadows, TargetID=TargetViewportID)
			ExistingPHAObj = utilities.ObjectWithID(ThisProj.PHAObjs, TargetID=XMLRoot.find(info.PHAModelIDTag).text)
#				TargetViewportClass = ClassList[
#					[Cls.InternalName for Cls in ClassList].index(XMLRoot.find('ViewportClass').text)]
#				TargetViewportID = XMLRoot.find('Viewport').text
#				TargetViewportHumanName = XMLRoot.find(info.HumanNameTag).text
#				ExistingPHAObj = utilities.ObjectWithID(ThisProj.PHAObjs, XMLRoot.find(info.PHAModelIDTag).text)
#				Chain = 'Stepwise' # TODO need 'NoChain' if we are adding new Viewport to existing PHA model
#			# check if we can proceed to create the Viewport; we may need editing rights
#			if Proj.EditAllowed:
#				# make the Viewport shadow
#				NewViewport = ViewportShadow(ThisProj, TargetViewportID, MyClass=TargetViewportClass,
#											 HumanName=TargetViewportHumanName,
#											 D2CSocketNumber=int(XMLRoot.find(info.D2CSocketNoTag).text),
#											 C2DSocketNumber=int(XMLRoot.find(info.C2DSocketNoTag).text),
#											 PHAModel=ExistingPHAObj)
#				# attach existing PHA object to the Viewport
#				NewViewport.PHAObj = ExistingPHAObj
#				ExistingPHAObj.Viewports.append(NewViewport)  # add Viewport to list in the PHA object
		# make reply message to send to control frame
		TargetViewport.IsOnDisplay = True
		Reply = self.MakeXMLMessageForDrawViewport(MessageHead='RP_SwitchToViewport', PHAObj=ExistingPHAObj,
			Viewport=TargetViewport, ViewportID=TargetViewportID)
		# send the info back to control frame as a reply message (via ListenToSocket)
		return Reply

	def UpdateAllViewportsAfterUndo(self, XMLRoot=None):
		# handle request to update all Viewports after undo of a data change
		global UndoChainWaiting
		Proj = utilities.ObjectWithID(self.Projects, XMLRoot.find(info.ProjIDTag).text)
		# write undo confirmation message in Vizop Talks panel
		self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Undone'), MainText=XMLRoot.find(info.UserMessageTag).text,
			Priority=ConfirmationPriority)
		# update display in local Control Frame, if SkipRefresh tag in XMLRoot is False
		if not utilities.Bool2Str(XMLRoot.find(info.SkipRefreshTag).text):
			# request redraw of Viewport, with changed element visible TODO make RenderInDC force element to be visible
			ThisViewport.RenderInDC(TargetDC, FullRefresh=True)
		# set UndoChainWaiting flag to trigger any further undo items
		UndoChainWaiting = utilities.Bool2Str(XMLRoot.find(info.ChainWaitingTag).text)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def ProcessSwitchToViewport(self, XMLRoot=None):
		# handle request in incoming message to switch to a Viewport
		self.SwitchToViewport(TargetViewport=utilities.ObjectWithID(Objects=self.Viewports,
			TargetID=XMLRoot.findtext(info.ViewportTag)), XMLRoot=XMLRoot)
		return vizop_misc.MakeXMLMessage('Null', 'Null')

	def DatacoreDoNewFTEventNotIPL(self, Root): # handle request to datacore for new FT event that's not an IPL
		# probably not currently used; redundant?
		# find out which project to work in
		ThisProj = utilities.ObjectWithID(OpenProjects, Root.find('Proj').text)
		if ThisProj.EditAllowed:
			# find out which PHA model to work in
			ThisPHAObj = utilities.ObjectWithID(ThisProj.PHAObjs, Root.find('PHAObj').text)
			# find applicable PHA object
			ThisPHAObj = WithID(Root.find('PHAObj').text)
			# ask PHA object to add new event
			Reply = ThisPHAObj.HandleIncomingRequest(self, Proj=self.CurrentProj, MessageAsXMLTree=Root)
		else: # couldn't make new event because editing is blocked
			Reply = vizop_misc.MakeXMLMessage(RootName='RP_NewFTEventNotIPL', RootText="Null",
				Elements={'CantComply': 'EditingBlocked'})
		# send the info back to control frame as a reply message (via ListenToSockets)
		return Reply

		# send reply for routing back to control frame
		Reply = vizop_misc.MakeXMLMessage(RootName='RP_NewFTEventNotIPL', RootText=NewViewportID,
			Elements={info.IDTag: ThisPHAObj.ID})
		return Reply

	def HandleMessageToLocalViewport(self, MessageReceived=None, MessageAsXMLTree=None, **Args):
		# process message received on socket requiring attention by local Viewport
		# returns acknowledgement message as XML string
		if MessageReceived is None:
			assert isinstance(MessageAsXMLTree, ElementTree.Element)
			XMLTreeToSend = MessageAsXMLTree
		else:
			assert isinstance(MessageReceived, bytes)
			XMLTreeToSend = ElementTree.fromstring(MessageReceived)
		# get message root
		MessageRoot = XMLTreeToSend.tag
		# if message is 'OK', it's just an acknowledgement with no action required
#		if MessageRoot == 'OK': return None # no reply message needed to CheckForIncoming Messages()
		if MessageRoot == 'OK':
			# check whether the incoming message includes information requiring a VizopTalks message
			if XMLTreeToSend.text == info.ValueOutOfRangeMsg:
				self.MyVTPanel.SubmitVizopTalksMessage(Title=_('Sorry'), MainText=_('That value is out of range'),
					Buttons=[], Priority=InstructionPriority)
			else: # clear any existing VizopTalks message
				self.MyVTPanel.FinishedWithCurrentMessage()
			return vizop_misc.MakeXMLMessage(RootName='OK', RootText='OK')
		else:
			# draw complete Viewport
			ReplyXML = self.ShowViewport(MessageReceived=MessageReceived, MessageAsXMLTree=XMLTreeToSend, **Args)
			self.RefreshGUIAfterDataChange(Proj=self.CurrentProj)
			return ReplyXML

	def RefreshGUIAfterDataChange(self, Proj):
		# perform specific refreshes (e.g. control panel, control frame menus) after a change to the data on display
		# refresh control frame GUI
		self.UpdateMenuStatus()
		# refresh control panel
		self.MyControlPanel.RedrawControlPanelAspect()
		self.MyControlPanel.UpdateNavigationButtonStatus(Proj=Proj)

	def ShowViewport(self, MessageReceived=None, MessageAsXMLTree=None, **Args):
		# show Viewport ViewportToShow in PHA panel, using data in MessageReceived (XML string) or, if None, in
		# MessageAsXMLTree (XML root element)
		if MessageReceived is None:
			assert isinstance(MessageAsXMLTree, ElementTree.Element)
			XMLTree = MessageAsXMLTree
		else:
			assert isinstance(MessageReceived, bytes)
			XMLTree = ElementTree.fromstring(MessageReceived)
		# First, tell Viewport to prepare for display, with data from PHA model
		self.CurrentViewport.PrepareFullDisplay(XMLTree)
		self.MyEditPanel.EditPanelMode(self.CurrentViewport, NewMode=self.CurrentViewport.InitialEditPanelMode)
			# set up initial mouse pointer and mouse bindings
		self.Refresh() # trigger OnPaint() so that the panel rendering is refreshed
		return vizop_misc.MakeXMLMessage(RootName='RP_ShowViewport', RootText='Null')

	def SetupFonts(self):
		Fonts = {}
		Fonts['BigHeadingFont'] = core_classes.FontInstance(Size=18, Bold=True)
		if system() == 'Darwin': # slightly larger font size on macOS than Windows
			Fonts['NormalFont'] = core_classes.FontInstance(Size=12, Bold=False)
			Fonts['BoldFont'] = core_classes.FontInstance(Size=12, Bold=True)
			Fonts['SmallHeadingFont'] = core_classes.FontInstance(Size=14, Bold=True)
			Fonts['NormalWidgetFont'] = core_classes.FontInstance(Size=12, Bold=False)
			Fonts['BoldWidgetFont'] = core_classes.FontInstance(Size=12, Bold=True)
		else:
			Fonts['NormalFont'] = core_classes.FontInstance(Size=11, Bold=False)
			Fonts['BoldFont'] = core_classes.FontInstance(Size=11, Bold=True)
			Fonts['SmallHeadingFont'] = core_classes.FontInstance(Size=13, Bold=True)
			Fonts['NormalWidgetFont'] = core_classes.FontInstance(Size=11, Bold=False)
			Fonts['BoldWidgetFont'] = core_classes.FontInstance(Size=11, Bold=True)
		return Fonts

	def OnExportFullFTRequest(self, Event): # handle menu request to produce FT export
		# first, detach any Viewport from the edit panel
#		ViewportToRevertTo = self.CurrentViewport
#		self.ReleaseCurrentViewport(Proj=self.CurrentProj)
#		# invoke "FT export" aspect for dialogue with user
#		self.GotoEditPanelAspect(NewAspect='EPAspect_ExportFullFT', ViewportToRevertTo=ViewportToRevertTo,
#			SystemFontNames=self.SystemFontNames, FT=self.CurrentViewport)
		# make a FTFullExport Viewport. DoNewViewportCommand() provides the new Viewport as self.TrialViewport
		self.DoNewViewportCommand(Proj=self.CurrentProj, ViewportClass=ft_full_report.FTFullExportViewport,
			Chain=True, PHAModel=self.CurrentViewport.PHAObj, ViewportToRevertTo=self.CurrentViewport)

	def GotoEditPanelAspect(self, NewAspect, **Args):
		# switch to a dialogue aspect in edit panel.
		# Assumes any Viewport has already been cleared from edit panel by calling ReleaseCurrentViewport()

		# main procedure for GotoEditPanelAspect
		assert isinstance(NewAspect, (project_display.EditPanelAspectItem, str))
		global KeyPressHash
		Proj = self.CurrentProj
		# deactivate previous aspect, if any %%% working here
		if self.MyEditPanel.EditPanelCurrentAspect:
			self.MyEditPanel.EditPanelCurrentAspect.Deactivate(Widgets=self.MyEditPanel.EditPanelCurrentAspect.WidgetList)
		# get target aspect, if supplied as a string
		if isinstance(NewAspect, str):
			TargetAspect = {'EPAspect_ExportFullFT': self.MyEditPanel.FTFullExportAspect}.get(NewAspect, None)
		else:
			TargetAspect = NewAspect
		if TargetAspect: # any recognised aspect supplied?
			self.MyEditPanel.EditPanelCurrentAspect = TargetAspect  # store new aspect
			TargetAspect.CurrentArgs = Args  # store for repeating on next call
#			self.PHAObjInControlPanel = Args.get('PHAObjInControlPanel', None)
			# fetch UndoOnCancel value to store in undo record for any tasks that should be undone when Cancel pressed
			self.UndoOnCancel = Args.get('UndoOnCancel', None)
			# prefill widgets in new aspect and activate it
			TargetAspect.Prefill(Proj, **Args)
			TargetAspect.SetWidgetVisibility(**Args)
			TargetAspect.Activate(**Args)
			# display aspect's sizer (containing all the visible widgets) in the edit panel
			self.MyEditPanel.SetSizer(TargetAspect.MySizer)
		else:
			print('CF2771 warning, unrecognised edit panel aspect "%s" requested' % str(NewAspect))

	# ControlFrame main body
	def __init__(self, parent=None, ID=None, title='', Projects=[], FirstProject=None, Viewport=None,
				 ColScheme=None, zmqContext=None, DatacoreIsLocal=True):
		# ID (str): ID of this control frame (for datacore's addressing purposes; not the wx ID of the window)
		# FirstProject (ProjectItem instance): the project (among those listed in Projects) that should be focused first
		# zmqContext: context for communications sockets (not used)
		# DatacoreIsLocal (bool): whether this control frame instance is running in the same Vizop instance as the datacore
		assert isinstance(ID, str)
		assert isinstance(FirstProject, projects.ProjectItem)
		assert FirstProject in Projects
		assert isinstance(ColScheme, display_utilities.ColourSchemeItem)
		assert isinstance(DatacoreIsLocal, bool)
		global KeyPressHash, ControlFrameData, AllControlFrameShadows, NormalWidgetFont, BoldWidgetFont
		sm = settings.SettingsManager()
		self.MyArtProvider = art.ArtProvider() # system for providing button images
		ControlFrameData.Data = {} # clear return data, to avoid accidentally sending obsolete data back to datacore
		self.ColScheme = ColScheme # store colour scheme (a ColourSchemeItem instance)
		self.ID = ID
		self.KeyPressEnabled = True # whether we are detecting keypresses for shortcuts
		self.DatacoreIsLocal = DatacoreIsLocal
		self.EditAllowed = DatacoreIsLocal
		self.Projects = Projects
		self.DisplayDevices = [] # wx.Panel instances; devices that can show Viewports
		self.TryHandshake = False # flag to OnIdle to try handshake with remote datacore
		self.CurrentValueProblem = None # info about any value problem currently displayed in the Control Panel

		# set up fonts. NormalWidgetFont and BoldWidgetFont are global, so that they can be accessed by UIWidget class
		# other fonts are set up in SetupFonts()
		self.BigHeadingFont = core_classes.FontInstance(Size=18, Bold=True)
		if system() == 'Darwin': # slightly larger font size on MacOS
			NormalWidgetFont = core_classes.FontInstance(Size=12, Bold=False)
			BoldWidgetFont = core_classes.FontInstance(Size=12, Bold=True)
			self.SmallHeadingFont = core_classes.FontInstance(Size=14, Bold=True)
		else: # Windows, Linux
			NormalWidgetFont = core_classes.FontInstance(Size=11, Bold=False)
			BoldWidgetFont = core_classes.FontInstance(Size=11, Bold=True)
			self.SmallHeadingFont = core_classes.FontInstance(Size=13, Bold=True)
		self.Fonts = self.SetupFonts() # must call before making MyControlPanel
		# generate list of system fonts
		e = wx.FontEnumerator()
		e.EnumerateFacenames()
		self.SystemFontNames = e.GetFacenames()

		# set up list of existing Viewports in this instance of Vizop
		if Viewport:
			assert Viewport in display_utilities.ViewportMetaClass.ViewportClasses
			self.Viewports = [Viewport]
			self.CurrentViewport = Viewport # which Viewport is now displayed
		else:
			self.Viewports = []
			self.CurrentViewport = None
		self.TrialViewport = None # used during creation of Viewports
		KeyPressHash = vizop_misc.ClearKeyPressRegister(KeyPressHash)
		# set up sockets for communication with datacore (no matter whether datacore is local or remote)
		F2CREPSocket, C2FREQSocket = self.SetupSockets(vizop_misc.RegisterSocket.Register)
		# if datacore is local (i.e. on the same machine as control frame), register this control frame with the datacore
		# (for remote control frames, the datacore has to do this by itself)
		if DatacoreIsLocal:
			ThisControlFrameShadow = ControlFrameShadow(ID=self.ID)
			ThisControlFrameShadow.C2FREQSocket = C2FREQSocket
			ThisControlFrameShadow.F2CREPSocket = F2CREPSocket
			AllControlFrameShadows.append(ThisControlFrameShadow)
			# get name of datacore socket to send messages to this control frame
			self.SocketFromDatacoreName = info.ControlFrameOutSocketLabel + info.LocalSuffix
		else: # remote datacore
			self.TryHandshake = True # inform OnIdle() to handshake with remote datacore
			print('CF1978 need to set up self.SocketFromDatacoreName')
		screenx1, screeny1, screenx2, screeny2 = wx.Display().GetGeometry() # get max size of primary display device
		TaskBarYAllowance = 0 # allows for window manager taskbar, assumed y axis only
		# set Control Frame size on first run.
		# On subsequent runs, layout_manager resets frame to its previous size (obsolete - no longer using layout_manager)
		ControlFrameSize = wx.Size(screenx2 - screenx1, screeny2 - screeny1 - TaskBarYAllowance)
		# set first-run sizes for the panels inside control frame
		MenuBarAllowance = 50 # y-allowance needed for menu bar at top of control frame
		VTPanelDefaultSizeX = 280
		ControlPanelDefaultSizeY = 150
		ViewPanelDefaultSizeY = 50
		EditPanelSize = wx.Size(screenx2 - screenx1,
			screeny2 - screeny1 - TaskBarYAllowance - ControlPanelDefaultSizeY - ViewPanelDefaultSizeY - MenuBarAllowance)
		ControlPanelSize = wx.Size(screenx2 - screenx1 - VTPanelDefaultSizeX, ControlPanelDefaultSizeY)
		ViewPanelSize = wx.Size(screenx2 - screenx1 - VTPanelDefaultSizeX, ViewPanelDefaultSizeY)
		VTPanelSize = wx.Size(VTPanelDefaultSizeX, ControlPanelDefaultSizeY + ViewPanelDefaultSizeY)
		wx.Frame.__init__(self, parent, wx.ID_ANY, title, size=ControlFrameSize, pos=(screenx1, screeny1))
#		self.layout_manager = wx.aui.AuiManager(self)
		# set up layout for panels
#		EditPanelLayout = wx.aui.AuiPaneInfo()
#		EditPanelLayout.Dockable(True).Floatable(False).CloseButton(False)
#		EditPanelLayout.CaptionVisible(False).Top().Name("EditPanel")
#		EditPanelLayout.dock_proportion = 10
#		EditPanelLayout.MinSize(EditPanelSize)

#		ControlPanelLayout = wx.aui.AuiPaneInfo()
#		ControlPanelLayout.Dockable(True).Floatable(False).CloseButton(False)
#		ControlPanelLayout.CaptionVisible(False).Centre().Left()
#		ControlPanelLayout.MinSize(ControlPanelSize).Name("ControlPanel")
#		ControlPanelLayout.dock_proportion = 3

#		ViewPanelLayout = wx.aui.AuiPaneInfo()
#		ViewPanelLayout.Dockable(True).Floatable(False).CloseButton(False)
#		ViewPanelLayout.CaptionVisible(False).Bottom().Left()
#		ViewPanelLayout.MinSize(ViewPanelSize).Name("ViewPanel")
#		ViewPanelLayout.dock_proportion = 1

#		VizopTalksPanelLayout = wx.aui.AuiPaneInfo()
#		VizopTalksPanelLayout.MinSize(VTPanelSize)
#		VizopTalksPanelLayout.Dockable(True).Floatable(False).CloseButton(False)
#		VizopTalksPanelLayout.CaptionVisible(False).Bottom().Right().Name("VizopTalks")
#		VizopTalksPanelLayout.dock_proportion = 4
		# create the panels to go into the main window
#		SizeX = ControlFrameSize[0] - ControlPanelSize[0]
#		SizeY = ControlFrameSize[1] - MenuBarAllowance
		self.MyEditPanel = self.EditPanel(wxParent=self, size=EditPanelSize, ViewportOwner=self,
			ColScheme=self.ColScheme)
#		self.MyEditPanel.SetMinSize( (SizeX, SizeY) )
		self.MyEditPanel.EditPanelMode(self.CurrentViewport, 'Select') # set up mouse pointer and bindings (needs OffsetX/Y)
		self.MyVTPanel = self.VTPanel(self, size=VTPanelSize)
		self.MyControlPanel = self.ControlPanel(self, size=ControlPanelSize, VTWindow=self.MyVTPanel,
			FirstProject=FirstProject, ColScheme=ColScheme)
		self.MyViewPanel = self.ViewPanel(self, size=ViewPanelSize, VTPanel=self.MyVTPanel, ColScheme=ColScheme)

		# make and populate master sizer for panels
		self.TopLevelSizer = wx.GridBagSizer()
		self.TopLevelSizer.Add(self.MyEditPanel, pos=(0,0), span=(1,2), flag=wx.FIXED_MINSIZE)
		self.TopLevelSizer.Add(self.MyControlPanel, pos=(1,0), span=(1,1))
		self.TopLevelSizer.Add(self.MyViewPanel, pos=(2,0), span=(1,1))
		self.TopLevelSizer.Add(self.MyVTPanel, pos=(1,1), span=(2,1))
		self.SetSizer(self.TopLevelSizer)
		self.TopLevelSizer.Layout()

		self.AddDisplayDevice(NewDisplayDevice=self.MyViewPanel)
		# put panels under layout management. Order of AddPane calls is important
#		self.layout_manager.AddPane(self.MyViewPanel, ViewPanelLayout)
#		self.layout_manager.AddPane(self.MyEditPanel, EditPanelLayout)
#		self.layout_manager.AddPane(self.MyControlPanel, ControlPanelLayout)
#		self.layout_manager.AddPane(self.MyVTPanel, VizopTalksPanelLayout)

#		try:
#			# load the previous layout of the panels
#			print("CF1402 reloading of screen layout from cache is commented out") # %%%
#			layout = sm.get_value('main_frame_layout')
#			self.layout_manager.LoadPerspective(layout, True)
#		except KeyError:
#			# tell the manager to 'commit' all the changes just made
#			self.layout_manager.Update()
		self.MyControlPanel.SetFocus() # enable ControlPanel to handle Tab, Space, Enter keys
		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.Bind(wx.EVT_IDLE, self.OnIdle)

		self.SetupMenus()
		self.Show(True)
		self.SetProject(FirstProject) # also sets self.CurrentProj

	def SetupSockets(self, SktRegister, DatacoreIsLocal=True, F2CSocketNumber=None, C2FSocketNumber=None):
		# set up zmq sockets for communication between control frame and datacore.
		# SktRegister is list of Vizop's socket instances
		# DatacoreIsLocal (bool): whether datacore is running in same instance of Vizop
		# F2CSocketNumber (int): if not DatacoreIsLocal, the controlframe-to-datacore socket number provided by remote
		# datacore; else ignored
		# C2FSocketNumber (int): similar for opposite direction
		# returns datacore-side socket instances, or (None, None) if not DatacoreIsLocal
		assert isinstance(DatacoreIsLocal, bool)
		# if datacore is local, find the socket numbers already created by datacore
		if DatacoreIsLocal:
			F2CSkts = [SktObj for SktObj in SktRegister
				if getattr(SktObj, 'SocketLabel', '') == info.ControlFrameInSocketLabel + info.LocalSuffix]
			C2FSkts = [SktObj for SktObj in SktRegister
				if getattr(SktObj, 'SocketLabel', '') == info.ControlFrameOutSocketLabel + info.LocalSuffix]
			assert len(F2CSkts) == 1 # must be exactly 1 socket in each direction
			assert len(C2FSkts) == 1
			F2CREPSocket = F2CSkts[0]
			C2FREQSocket = C2FSkts[0]
			F2CSocketNoToUse = F2CREPSocket.SocketNo
			C2FSocketNoToUse = C2FREQSocket.SocketNo
		else: # remote datacore: need to get socket numbers via handshake code entered by user
			assert isinstance(F2CSocketNoToUse, int)
			assert isinstance(C2FSocketNoToUse, int)
			F2CREPSocket = C2FREQSocket = None # cannot identify datacore's sockets
			F2CSocketNoToUse = F2CSocketNumber
			C2FSocketNoToUse = C2FSocketNumber
		# create and connect to sockets on control frame side
		self.zmqOutwardSocket, self.zmqOutwardSocketObj, OutwardSocketNumber = vizop_misc.SetupNewSocket(SocketType='REQ',
			SocketLabel='F2CREQ', SocketNo=F2CSocketNoToUse, BelongsToDatacore=False, AddToRegister=True)
		self.zmqInwardSocket, self.zmqInwardSocketObj, InwardSocketNumber = vizop_misc.SetupNewSocket(SocketType='REP',
			SocketLabel='C2FREP', SocketNo=C2FSocketNoToUse, BelongsToDatacore=False, AddToRegister=True)
		return F2CREPSocket, C2FREQSocket

	def SetProject(self, ThisProj):
		# handle change of project displayed
		# set control frame title
		if ThisProj.ShortTitle:
			ProjTitleToShow = ThisProj.ShortTitle
		else:
			ProjTitleToShow = _('<Untitled project>')
		self.SetTitle(info.PROG_SHORT_NAME + ' | ' + ProjTitleToShow)
		self.CurrentProj = ThisProj
		# go to appropriate initial view of project
		if ThisProj.PHAObjs: # does the project have any PHA models?
			pass # TODO call self.MyControlPanel.GotoControlPanelAspect, although this is now done in SwitchToViewport()
		else: # no existing PHA models
			# no need to store a navigation milestone here - done in DoNewViewport
			# get the user to create a PHA model
			self.InviteUserToCreatePHAModel(Proj=ThisProj)
			# set control panel to PHAModels aspect
			self.MyControlPanel.GotoControlPanelAspect(NewAspect=self.MyControlPanel.PHAModelsAspect)
			self.RefreshGUIAfterDataChange(Proj=ThisProj) # set menu status, and other GUI updates

	def InviteUserToCreatePHAModel(self, Proj):
		# invite user to create a new PHA model instance within project Proj (ProjectItem instance).
		assert isinstance(Proj, projects.ProjectItem)
		# set appropriate VizopTalks message
		if Proj.PHAObjs:
			VTHeader = _('Add new PHA model')
			VTText = _('Click on the model type you require')
		else:
			VTHeader = _('Your project has no PHA models yet')
			VTText = _('Click on the model type you require')
		self.MyVTPanel.SubmitVizopTalksMessage(Title=VTHeader, MainText=VTText, Buttons=[], Priority=InstructionPriority)

	def AddDisplayDevice(self, NewDisplayDevice=None): # add new display device to control panel's register
		assert isinstance(NewDisplayDevice, wx.Panel)
		self.DisplayDevices.append(NewDisplayDevice)

	def UpdateAllViewports(self, Proj=None, Message=None):
		# this is a Datacore function.
		# refresh Viewports after change to data in datacore. For now, we just redraw all Viewports currently shown
		# in a display device.
		# Message (str): XML message received requesting update to Viewports (currently not used)
		# Check with all Viewports that datacore knows about
		for ThisViewportShadow in Proj.AllViewportShadows:
			# check if ThisViewportShadow is displayed in any display device, local or remote
			if ThisViewportShadow.IsOnDisplay:
				# find Viewport shadow corresponding to
				# get refresh data from corresponding PHA object
				RedrawXMLData = ThisViewportShadow.PHAObj.GetFullRedrawData(Viewport=ThisViewportShadow,
					ViewportClass=ThisViewportShadow.MyClass)
				# make XML message with ID of PHA object, followed by full redraw data
				FullXMLData = vizop_misc.MakeXMLMessage(RootName='RQ_RedrawViewport', RootText=ThisViewportShadow.ID,
					Elements={info.IDTag: ThisViewportShadow.PHAObj.ID})
				FullXMLData.append(RedrawXMLData)
				# send it to Viewport
				vizop_misc.SendRequest(Socket=ThisViewportShadow.D2CSocketREQObj.Socket, Command='RQ_RedrawViewport',
					XMLRoot=FullXMLData)

class ControlFramePersistent(object):
	# a persistent object used for returning data from control frame after it is Destroy()ed.

	def __init__(self):
		object.__init__(self)
		self.Data = {}

ControlFrameData = ControlFramePersistent() # make an instance of the data return object

def DatacoreDoNewPHAObj_Undo(Proj, UndoRecord, **Args): # undo creation of new PHA object
	assert isinstance(Proj, projects.ProjectItem)
	assert isinstance(UndoRecord, undo.UndoItem)
#	# find out which Control Frame sent the undo request (so that we know which one to reply to)
#	RequestingControlFrameID = Args['RequestingControlFrameID']
	# find out which datacore socket to send messages on
	SocketFromDatacore = vizop_misc.SocketWithName(TargetName=Args['SocketFromDatacoreName'])
	# find and remove the new PHA object from Proj
	PHAObjToRemove = UndoRecord.PHAObj
	Proj.PHAObjs.remove(PHAObjToRemove)
	# tell Control Frame what we did
	Reply = vizop_misc.MakeXMLMessage(RootName='NO_NewPHAModel_Undo', RootText=PHAObjToRemove.ID,
		Elements={info.PHAModelTypeTag: type(PHAObjToRemove).InternalName,
		info.ChainWaitingTag: utilities.Bool2Str(Args['ChainWaiting']),
		info.ProjIDTag: Proj.ID, info.SkipRefreshTag: utilities.Bool2Str(Args['SkipRefresh'])})
#	vizop_misc.SendRequest(Socket=ControlFrameWithID(RequestingControlFrameID).C2FREQSocket.Socket,
#		Command='NO_NewPHAModel_Undo', XMLRoot=Reply)
	vizop_misc.SendRequest(Socket=SocketFromDatacore.Socket,
		Command='NO_NewPHAModel_Undo', XMLRoot=Reply)
	projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.PHAModelTag,
		Elements={info.IDTag: PHAObjToRemove.ID, info.DeleteTag: ''}))
	return {'Success': True}

def DatacoreDoNewPHAObj_Redo(Proj, RedoRecord, **Args): # redo creation of new PHA object
	global UndoChainWaiting, RedoChainWaiting
	# get PHA model instance previously created and stored in redo record
	PHAObj = RedoRecord.PHAObj
	# attach PHA model to the project
	Proj.PHAObjs.append(PHAObj)
	undo.AddToUndoList(Proj, Redoing=True, UndoObj=undo.UndoItem(UndoHandler=DatacoreDoNewPHAObj_Undo,
		RedoHandler=DatacoreDoNewPHAObj_Redo, Chain=Args['ChainUndo'],
		PHAObj=PHAObj,
		HumanText=_('new PHA model: %s' % type(PHAObj).HumanName)))
	projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.PHAModelTag,
		Elements={info.IDTag: PHAObj.ID, info.PHAModelTypeTag: type(PHAObj).InternalName}))
	# make return message containing new PHA model's ID
	Notification = vizop_misc.MakeXMLMessage(RootName='NO_NewPHAModel_Redo', RootText=PHAObj.ID,
		Elements={info.ProjIDTag: Proj.ID, info.PHAModelIDTag: PHAObj.ID,
		info.PHAModelTypeTag: type(PHAObj).InternalName})
	# set RedoChainWaiting flag to trigger any further redo items
	RedoChainWaiting = Args.get('ChainWaiting', False)
	# send message to ControlFrame to initiate post-processing actions
	vizop_misc.SendRequest(Socket=ControlFrameWithID(Args['RequestingControlFrameID']).C2FREQSocket.Socket,
		Command='NO_NewPHAModel_Redo', XMLRoot=Notification)
	return {'Success': True, 'Notification': Notification}
	# no need to refresh display, as New Viewport must follow

def DatacoreDoNewPHAObj(Proj, XMLRoot=None, ViewportID=None, **NewPHAObjArgs):
	# make a new, empty PHA object (eg HAZOP, FT) in Proj (a Project instance).
	# XMLRoot (XML tag object); contains tags with information needed to set up new PHA object
	# including: info.PHAModelTypeTag = InternalName of PHA model class required
	# If ViewportID (str or None) is not None, attach it to the new PHA object.
	# NewPHAModelArgs are sent to the PHA model initiator.
	# Returns PHA object.
	assert isinstance(Proj, projects.ProjectItem), "CF1453 Proj '%s' supplied isn't a project" % str(Proj)
	# get type of PHA model required
	NewPHAObjType = vizop_misc.PHAModelClassWithName(XMLRoot.find(info.PHAModelTypeTag).text)
	if not NewPHAObjType: print("CF1933 oops, unknown PHA object type requested")
		# TODO properly handle case of PHA model unknown (e.g. we're running old version of Vizop)
	# make the PHA model and attach it to the project
	NewPHAObj = NewPHAObjType(Proj, **NewPHAObjArgs)
	Proj.PHAObjs.append(NewPHAObj)
	Proj.PHAObjShadows.append(NewPHAObj) # put the same object in the shadows list, for local display devices to access
	Proj.AssignDefaultNameToPHAObj(PHAObj=NewPHAObj)
	undo.AddToUndoList(Proj, UndoObj=undo.UndoItem(UndoHandler=DatacoreDoNewPHAObj_Undo, Chain='NoChain',
		RedoHandler=DatacoreDoNewPHAObj_Redo, ViewportID=ViewportID,
		PHAObj=NewPHAObj, HumanText=_('new PHA model: %s' % NewPHAObjType.HumanName)))
	projects.SaveOnFly(Proj, UpdateData=vizop_misc.MakeXMLMessage(RootName=info.PHAModelTag,
		Elements={info.IDTag: NewPHAObj.ID, info.PHAModelTypeTag: NewPHAObjType.InternalName}))
	# make return message containing new PHA model's ID
	Reply = vizop_misc.MakeXMLMessage(RootName='RP_NewPHAModel', RootText=NewPHAObj.ID,
		Elements={info.ProjIDTag: Proj.ID, info.IDTag: ViewportID, info.PHAModelIDTag: NewPHAObj.ID,
		info.PHAModelTypeTag: NewPHAObjType.InternalName})
	return Reply

def DatacoreStopDisplayingViewport(Proj, XMLRoot=None):
	# handle request to datacore informing that a Viewport is no longer on display in any display device
	# first, find the corresponding Viewport shadow - if it's just been deleted, it won't exist
	TargetViewportID = XMLRoot.findtext(info.ViewportTag)
	if TargetViewportID in [v.ID for v in Proj.AllViewportShadows]: # it still exists
		TargetViewport = utilities.ObjectWithID(Proj.AllViewportShadows, TargetViewportID)
		TargetViewport.IsOnDisplay = False
	return vizop_misc.MakeXMLMessage(RootName='RP_StopDisplayingViewport', RootText=TargetViewportID,
		Elements={})

class ViewportShadow(object): # defines objects that represent Viewports in the datacore.
	# These are not the actual (visible) Viewports - those live in the controlframe (local or remote) and aren't
	# directly accessible by the datacore.

	def __init__(self, Proj, ID, MyClass=None, D2CSocketNumber=None, C2DSocketNumber=None, PHAModel=None,
			HumanName=''):
		# ID (str) is the same as the ID of the corresponding "real" Viewport
		# MyClass (ViewportClasses instance): class of actual Viewport shadowed by this one
		# D2CSocketNumber and C2DSocketNumber (2 x int): socket numbers assigned in display_utilities.CreateViewport
		# PHAModel: PHA model owning the real Viewport
		# HumanName: HumanName assigned to the real Viewport
		assert isinstance(Proj, projects.ProjectItem)
		assert isinstance(ID, str)
		assert MyClass in display_utilities.ViewportMetaClass.ViewportClasses
		assert isinstance(D2CSocketNumber, int)
		assert isinstance(C2DSocketNumber, int)
		assert isinstance(HumanName, str)
		object.__init__(self)
		self.ID = ID
		self.MyClass = MyClass
		self.HumanName = HumanName
		self.IsOnDisplay = False # whether the Viewport shadow is currently displayed on any display device
		# set up sockets using socket numbers provided
		self.C2DSocketREP, self.C2DSocketREPObj, C2DSocketNumberReturned = vizop_misc.SetupNewSocket(SocketType='REP',
			SocketLabel='C2DREP_' + self.ID,
			PHAObj=PHAModel, Viewport=self, SocketNo=C2DSocketNumber, BelongsToDatacore=True, AddToRegister=True)
		self.D2CSocketREQ, self.D2CSocketREQObj, D2CSocketNumberReturned = vizop_misc.SetupNewSocket(SocketType='REQ',
			SocketLabel=info.ViewportOutSocketLabel + '_' + self.ID,
			PHAObj=PHAModel, Viewport=self, SocketNo=D2CSocketNumber, BelongsToDatacore=True, AddToRegister=True)
		# put the new viewport shadow into the project's list
		Proj.AllViewportShadows.append(self)

class ControlFrameShadow(object): # defines objects that represent control frames in the datacore.
	# These are not the actual (visible) control frames - those live in the controlframe (local or remote)

	def __init__(self, ID): # ID (str) is the same as the ID of the corresponding "real" control frame
		global AllControlFrameShadows
		object.__init__(self)
		self.ID = ID
		self.F2CREPSocket = None # datacore's end of the control frame-to-core communications channel (socket object)
		self.C2FREQSocket = None # datacore's end of the core-to-control frame communications channel (socket object)
		AllControlFrameShadows.append(self)

def ControlFrameWithID(IDToFind): # return datacore's ControlFrameShadow object with ID = IDToFind (str)
	assert IDToFind in [cf.ID for cf in AllControlFrameShadows]
	return [cf for cf in AllControlFrameShadows if cf.ID == IDToFind][0]

