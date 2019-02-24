#!/usr/bin/python
# -*- coding: utf-8 -*-
# This is part of Vizop, (c) 2014 Peter Clarke. Main section of code is in this module

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import wx # provides basic GUI functions
# import wx.aui
from wx import lib
from wx.lib import scrolledpanel # used for milestone display
# import cPickle # used for saving and loading files. If data structure problems are hit, try pickle instead
# from copy import deepcopy # used to create deep copies of data structures. See Beazley p30
from os import path
from os.path import expanduser
from os import remove # OS command for deleting files; see Beazley p316
from os import rename # OS command for renaming files/directories; see Beazley p316
from os import sep, extsep
	# sep = file path element separator (eg /); extsep = separates filename from extension (eg .)
import os # to start a new line, use os.linesep
# from getpass import getuser # gets currently logged in username (Unix, Windows only)
from locale import getdefaultlocale # used to obtain current locale, hence language settings. Beazley p286
import tempfile # For handling temporary files; see Beazley p342
# from math import cos, sin, degrees, radians # Beazley p190
import wx.lib.mixins.inspection as wit # provides InspectableApp for debugging
# import timeit, time # for timing of execution only; Beazley p512, 348

# other vizop modules required here
import vizop
from vizop import undo

# global variables for this module
# TimeMultiplier = 1000 # factor to multiply displayed times (in s) to get internal times (currently in ms)
PickleProtocol = 2 # which pickling protocol to use for loading and saving. See Beazley p163

sm = settings.SettingsManager()
sm.set_value('SystemLanguage', getdefaultlocale()[0]) # returns e.g. 'en_US'
ProjectDisplays = {} # dictionary of displays (panels in which projects can be displayed), referenced by ID
DisplaysAwaited = {} # dictionary of project instances (values) which are waiting for displays (keys) to become available
sm.set_value('EditDisplayIndex', 1) # which wx.Display is the main edit/control display, if >1 display is available
ProjList = {} # dictionary of currently open projects. Keys are project IDs, values are instances of ProjectClass
TemplateSelectedFrom = '' # when "Select template" dialogue is opened, where it was opened from (welcome screen or main screen)
FirstVizopTalks = ('', '') # (title, message) to show in VizopTalks when main window first built
CurrentProject = None # Project the user is currently working on
KeyPressHash = [] # list of tuple: (keystroke code, handling routines when those keystrokes are detected, dict of args to supply to handler)
	# keystroke code can be list of codes, in required order, or list of lists of codes (if multiple keystrokes should be recognised for one handler)

# utility functions

def KeyPressHandler(KeyPressEvent, KeyShortcutTable):
	# interprets key presses and returns the name of the appropriate handling routine, or None. Uses raw codes, so not case sensitive
	# KeyPressEvent is event as picked up by handler bound to wx.EVT_KEY_DOWN
	# KeyShortcutTable is dictionary: keys are keypresses, values are names of handling routines (or anything you like; will be returned as-is)
	# For keypresses: Use any of Alt+, Ctrl+, Shift+ in that order; then keytop name (upper case for alpha)
	# For details, refer to http://www.wxpython.org/docs/api/wx.KeyEvent-class.html
	KeyNameTable = {27: 'Esc', 340: 'F1', 341: 'F2', 342: 'F3', 343: 'F4', 344: 'F5', 345: 'F6', 346: 'F7', \
		347: 'F8', 348: 'F9', 349: 'F10', 350: 'F11', 351: 'F12', 364: 'Numlock', 322: 'Ins', 127: 'Del', \
		310: 'Pause', 8: 'Backspace', 9: 'Tab', 311: 'Capslock', 13: 'Enter', 306: 'Shift', 308: 'Ctrl', \
		307: 'Alt', 309: 'Menu', 366: 'PgUp', 367: 'PgDn', 315: 'Up', 317: 'Down', 314: 'Left', 316: 'Right', 32: 'Space' }
	Modifiers = 'Alt+'*KeyPressEvent.AltDown() + 'Ctrl+'*KeyPressEvent.CmdDown() + 'Shift+'*KeyPressEvent.ShiftDown()
	ShortcutString = str(Modifiers)
	KeyCode = KeyPressEvent.GetUnicodeKey() # find out which key was pressed
	if (KeyCode in range(33, 126)):
		ShortcutString += chr(KeyCode) # if it's an alphanum key, add the keytop label (for readability)
	elif (KeyCode in KeyNameTable): ShortcutString += KeyNameTable[KeyCode] # for named keys
	else: ShortcutString += str(KeyCode) # any other keycode not listed in KeyNameTable
	if (ShortcutString in KeyShortcutTable): return KeyShortcutTable[ShortcutString]
	else: return None

signum = lambda x: (x > 0) - (x < 0) # returns 1 if x>0, -1 if x<0, 0 if x==0. Undefined for non-number inputs


# global functions

def OnAboutRequest(event=None):
	# handle request for 'About Vizop' info: show About box. Redundant, not used
	# FIXME On some platforms, wx.AboutBox() is not modal - so we can't block return to other panels, meaning that we can't suppress their keyboard
	# shortcuts. May have to change this to a custom modal dialogue box.
	about_info = wx.AboutDialogInfo() # create an 'About' info object, and populate it
	about_info.SetDescription(_('Vizop is a Process Hazards Analysis tool, designed to be visual, intuitive and easy to exchange data between PHA ' +
		'models. At present, only the Fault Tree model is available.'))
	about_info.AddDeveloper(_('Peter Clarke (info@VizopSoftware.com)'))
	about_info.SetName(info.PROG_NAME)
	about_info.SetVersion(info.VERSION)
	about_info.SetCopyright(_(u'Copyright \u00A9 %s %s') % (info.YEAR_LAST_RELEASED, info.AUTHOR)) # \u00A9 produces (c) symbol
	wx.AboutBox(about_info) # show the About box


def CreateProject():
	# Make a Project object and return (project instance, project ID)
	global ProjList
	NewProjKey = 1 + max([0] + ProjList.keys()) # find highest project key of already-open projects, add 1 to get key for new project
	Proj = projects.ProjectClass() # create the project as an instance of ProjectClass
	ProjList[NewProjKey] = Proj # list the project in ProjList
	return (Proj, NewProjKey)


