#!/usr/bin/python
# -*- coding: utf-8 -*-
# undo module: part of Vizop, (c) 2018 xSeriCon. Contains general code for managing undo/redo
# undo/redo handlers for each specific operation are adjacent to the code for those operations
# Grabbed from SILability, Chain attrib changed and updated for Python 3

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import

# SILability modules
import projects

def _(Dummy): pass # dummy definition

class UndoItem(object):
	# Item in an Undo/Redo register of a project. Contains all information needed to execute the undo/redo

	def __init__(self, UndoHandler, RedoHandler, Chain='NoChain', HumanText='', UndoOnCancel=0, WritesDatabase=None,
		ReadsDatabase=None, **Args):
		# UndoHandler (callable): routine that executes the undo. It will be sent all the Args as a dict.
		# RedoHandler (callable): routine that executes the redo. It will be sent all the Args as a dict.
		# Chain (str): 'Avalanche': do all chained undo's sequentially without pausing; 'Stepwise': do the first undo,
		# respond to handler that more undo's are waiting; 'NoChain': do one undo only
		# HumanText (str): Informative text visible to the user in undo/redo lists.
		#   Should be in English; will be translated at the time of display to user
		#   Not needed if Chain!='NoChain'. Only the last Chain=='NoChain' HumanText will be shown.
		# UndoOnCancel (int): Indicator for records to be undone when user hits Cancel.
		#   When user hits 'Cancel', all consecutive records with same UndoOnCancel value as the last one (if > 0) are undone.
		#   No redo record is stored when Undoing-on-Cancel. (However, redo is required if these records are undone later.)
#		# WritesDatabase/ReadsDatabase (projects.DatabaseItem instance or None): this action reads to or writes from a database
		# First, check UndoHandler and RedoHandler are functions. Not using callable() as it's deprecated
		assert hasattr(UndoHandler, '__call__'), "UndoHandler '%s' isn't a function" % str(UndoHandler)
		assert hasattr(RedoHandler, '__call__'), "RedoHandler '%s' isn't a function" % str(RedoHandler)
		assert Chain in ['Avalanche', 'Stepwise', 'NoChain']
		assert isinstance(HumanText, str), "UN1215 Non-string '%s' supplied as human name for undo item" % \
			str(HumanText)
		assert isinstance(UndoOnCancel, int), "Non-integer '%s' supplied as UndoOnCancel value for undo item" % str(
			UndoOnCancel)
		object.__init__(self)
		self.UndoHandler = UndoHandler
		self.RedoHandler = RedoHandler
		self.Chain = Chain
		self.HumanText = HumanText
		self.UndoOnCancel = UndoOnCancel
#		self.WritesDatabase = WritesDatabase
#		self.ReadsDatabase = ReadsDatabase
		self.EditNumber = None # project EditNumber value to restore (int). If None, don't restore
		# store any values in Args as attribs
		for (Key, Value) in Args.items():
			setattr(self, Key, Value)
		# Optional attribs set elsewhere:
		#	SandboxRevertPoint (bool): if True, when exiting sandbox, revert changes made up to but not including this record

def AddToUndoList(Proj, UndoObj=None, Redoing=False, SuppressRepeats=False,
		SRArgsToSkip=('OldValue', 'EditNumber'), IncrementEditNumber=True):
	# Add UndoObj (UndoItem instance) to the Undo list for Proj.
	# Separate undo lists are kept for each open project, so that when the Undo command comes,
	# only actions in the current project are undone
	# UndoObj needs attribs: UndoHandler, RedoHandler (callables to execute undo/redo);
	#	HumanText (str; optional; describes action to be undone); Chain (str)
	# Redoing (bool): whether we are currently redoing an action. If Redoing, don't clear the RedoList
	# SuppressRepeats: If an UndoObj comes from the same widget as the preceding one, store only its ValueForRedo attrib
	# (this is to avoid undo's on TextCtrl widgets one keypress at a time)
	# SRArgsToSkip (iterable): when doing SuppressRepeats check, all attribs of the new and old Undo records will be
	#   checked except those listed in SRArgsToSkip
	# Specifically, the check is whether all attribs except OldValue are the same
	# IncrementEditNumber: whether to increment the project's EditNumber and store in Undo record for restoring
	assert isinstance(UndoObj, UndoItem)
	assert isinstance(Redoing, bool)
	if SuppressRepeats and Proj.UndoList: # only do check if there are any items in UndoList
		# check if any attribs of UndoObj (apart from OldValue) are different from the most recently stored undo object
		SuppressThisRepeat = not (False in [Value == getattr(UndoObj, Key, None)
								for (Key, Value) in Proj.UndoList[-1].__dict__.iteritems()
								if Key not in SRArgsToSkip])
	else:
		SuppressThisRepeat = False
	if SuppressThisRepeat: # this is a repeat Undo item that should be suppressed
		if hasattr(UndoObj, 'ValueForRedo'):
			# update ValueForRedo of preceding Undo record
			Proj.UndoList[-1].ValueForRedo = UndoObj.ValueForRedo
	else: # treat as normal Undo item
		if IncrementEditNumber: # increment project's EditNumber and store in Undo record
			UndoObj.EditNumber = Proj.EditNumber
			Proj.EditNumber += 1
		Proj.UndoList.append(UndoObj)
	if not Redoing: Proj.RedoList = []

def PerformUndoOnCancel(Proj, TargetUoCValue=0):
	"""
	If most recent undo records are marked with "undo on Cancel" and their UndoOnCancel value >= TargetUoCValue, they are undone.
	Should be called when "Cancel" selected in an editing dialogue
	No need to store Redo record.
	"""
	assert isinstance(Proj, projects.ProjectItem)
	assert isinstance(TargetUoCValue, int)
	Undoing = True
	while Undoing and Proj.UndoList: # check Undo list items starting from end of list, unless list is empty
		ThisUndoIndex = Proj.UndoList[-1].UndoOnCancel # get UndoOnCancel value for final Undo record
		if ThisUndoIndex >= TargetUoCValue: # should we undo this one?
			# print("U31 Performing undo on cancel: ", Proj.UndoList[-1].HumanText)
			HandleUndoRequest(Proj, StoreRedoRecord=False)
		else: Undoing = False # stop undoing

def SetUp4UndoOnCancel(Proj):
	"""
	This should be called at the start of any routine that requires Undoable tasks to be Undone when a Cancel command is issued.
	Returns UndoOnCancel value (int) that should be stored with any Undo records. See Undo spec for details.
	"""
	assert isinstance(Proj, projects.ProjectItem)
	if Proj.UndoList: UndoOnCancelIndex = Proj.UndoList[-1].UndoOnCancel + 1
	else: UndoOnCancelIndex = 1 # if there's no Undo record, assign arbitrary value > 0
	return UndoOnCancelIndex

def EndUndoOnCancel(Proj):
	# When an operation that can generate 'undo on cancel' records is finished (eg user clicks 'OK'), call this
	# function. It converts
	# 'undo on cancel' records to normal undo records, chained together, so that the user can still undo them later.
	# Calling procedure may also need to decrement its UndoOnCancelIndex (maybe Proj.UOCIndex)
	if Proj.UndoList: # any records in Undo list?
		# Work backwards through undo list, finding records marked with the latest value of UndoOnCancel
		TargetUoCValue = Proj.UndoList[-1].UndoOnCancel
		if TargetUoCValue > 0:
			ThisIndex = len(Proj.UndoList) - 1
			while (ThisIndex >= 0) and (Proj.UndoList[ThisIndex].UndoOnCancel == TargetUoCValue):
				Proj.UndoList[ThisIndex].UndoOnCancel -= 1 # we decrement it (rather than setting to zero) so that,
				# if we are doing nested 'undo on cancel'able tasks, the outer one can still perform undo on cancel.
				ThisIndex -= 1

def AddToRedoList(Proj, RedoObj): # similar to AddToUndoList()
	Proj.RedoList.append(RedoObj)

def HandleUndoRequest(Proj, RequestingControlFrameID=None, StoreRedoRecord=True, ContinuingPausedChain=False):
	# process Undo command from user
	# undo the last record in Proj's undo list. If the last record's Chain arg == 'Avalanche', undo preceding entries up to and
	# including the last one with Chain != 'Avalanche'
	# RequestingControlFrameID: ID of control frame from which undo request was issued (so that undo handler knows
	# where to send reply messages to)
	# if StoreRedoRecord, undo information will be stored in Proj's Redo list.
	# return: Success (bool), ReturnArgs (dict) from last undo handler run, UndoMsg (str) explaining the undo just done,
	#   NextUndoMsg (str) explaining what would be undone on the next call of PerformUndo

	# start of HandleUndoRequest()
	assert type(StoreRedoRecord) is bool, "UN1319 Non-boolean '%s' value for StoreRedoRecord" % str(StoreRedoRecord)
	Success = True # default value of undo success flag
	UndoMsg = NextUndoMsg = ''
	ReturnArgs = {}
	ChainPaused = False # whether we paused the undo chain because we reached an item with Chain == 'Stepwise'
	if Proj.UndoList: # check if there are any items in the undo list
		# find where we should undo up to
		UndoUpToIndex = FindLastRecordToUndo(Proj.UndoList, StartFromIndex=len(Proj.UndoList) - 1)
		UndoHowManyMinus1 = (len(Proj.UndoList) - UndoUpToIndex) - 1
		UndoneCount = 0 # how many records actually undone
		# undo those records between the end and UndoUpToIndex
		for UndoLoopIndex, ThisRec in enumerate(
				[Proj.UndoList[i] for i in range(len(Proj.UndoList) - 1, UndoUpToIndex - 1, -1)]):
			if not ChainPaused:
				# store the chaining algorithm, if this is the first undo in the chain
				if UndoLoopIndex == 0: ChainAlgorithm = ThisRec.Chain
				if ThisRec.Chain == 'Stepwise': ChainPaused = True
				# call UndoHandler to undo a single action; chained unless this is the last one to undo
				# SkipRefresh (bool): whether the handler can skip recalc/refresh (because there are more data changes to follow)
				# (we can skip if this is not the last undo in the chain)
				# ChainWaiting (bool): whether more chained undo items are waiting due to the previous item having Chain=='Stepwise'
				ReturnArgs = ThisRec.UndoHandler(Proj, ThisRec, SkipRefresh=not (UndoLoopIndex == UndoHowManyMinus1),
					RequestingControlFrameID=RequestingControlFrameID, ChainWaiting=ChainPaused)
				if ReturnArgs is None: ReturnArgs = {}
				UndoneCount += 1
				# restore project's Edit number
				if hasattr(ThisRec, 'EditNumber'):
					Proj.EditNumber = ThisRec.EditNumber
				# update Success flag
				if 'Success' in ReturnArgs:
					if type(ReturnArgs['Success']) is bool:
						Success = Success and ReturnArgs['Success']
					else:
						print("UN1321 Oops, non-bool Success value received from Undo handler: '%s'" % ThisRec.HumanText)
				else:
					Success = True # if no Success flag returned, assume all is well
				# store redo record. It's the same as the undo record, with RedoChain attrib added
				if StoreRedoRecord: # store redo record
					# store the RedoChain value required in the next redo from this chained undo, in case there is one
					ThisRec.NextRedoChain = ThisRec.Chain
					# 1st (or only) redo should not be chained; others are chained
					ThisRec.RedoChain = 'NoChain' if (UndoLoopIndex == 0 and not ContinuingPausedChain)\
						else Proj.RedoList[0].NextRedoChain
					Proj.RedoList.append(ThisRec)
#		# did we get to the end of the undo chain? If so, set the redo items' RedoChain attribs
#		if not ChainPaused:
#			# first redo item we added is not chained
#			Proj.RedoList[-1].RedoChain = 'NoChain'
#			# all other redo items have RedoChain = the last item's Chain (inherited from the first undo record done)
#			for RecIndex in range(-UndoHowManyMinus1 - 1, -1): Proj.RedoList[RecIndex].RedoChain = Proj.RedoList[-1].Chain
		# get human-readable message confirming what action was just undone
		assert hasattr(Proj.UndoList[UndoUpToIndex], 'HumanText'),\
			"UN1342 Undo item '%s' has no 'HumanText'" % Proj.UndoList[UndoUpToIndex].InternalName
		assert isinstance(Proj.UndoList[UndoUpToIndex].HumanText, str),\
			"UN1344 HumanText attribute of Undo item '%s' isn't a string" % Proj.UndoList[UndoUpToIndex].InternalName
		ReturnArgs['UndoMsg'] = _(getattr(Proj.UndoList[UndoUpToIndex], 'HumanText', ''))
		# remove the undo records just undone
		Proj.UndoList = Proj.UndoList[:-UndoneCount]
		# find the message of the last record that would be undone on next call
		if Proj.UndoList:  # if there are still some items left in the undo list, get human message for next one
			NextUndoUpToIndex = FindLastRecordToUndo(Proj.UndoList, StartFromIndex=len(Proj.UndoList) - 1)
			assert hasattr(Proj.UndoList[NextUndoUpToIndex], 'HumanText'),\
				"UN1351 Undo item '%s' has no 'HumanText'" % Proj.UndoList[NextUndoUpToIndex].InternalName
			assert isinstance(Proj.UndoList[NextUndoUpToIndex].HumanText, str),\
				"UN1353 HumanText attribute of Undo item '%s' isn't a string" % Proj.UndoList[NextUndoUpToIndex].InternalName
			ReturnArgs['NextUndoMsg'] = _(Proj.UndoList[NextUndoUpToIndex].HumanText)
		else: ReturnArgs['NextUndoMsg'] = ''
	else: # empty Undo list
		ReturnArgs['Success'] = False
		ReturnArgs['UndoMsg'] = ''
	ReturnArgs['SkipRefresh'] = ChainPaused # tell calling procedure not to refresh menus, etc. if chaining is paused
	return ReturnArgs

def HandleRedoRequest(Proj, RedoingSandbox=False, RequestingControlFrameID=None):
	# process Redo command from user
	# redo the last record in Proj's redo list. If the last record's RedoChain arg == 'Avalanche', redo preceding entries up to and
	# including the last one with RedoChain == 'NoChain', or up to and excluding the last one with RedoChain == 'Stepwise'
	# Does not create an Undo record for the redone actions; this is the responsibility of individual Redo handlers
	# (because we can't just recycle the previous Undo record - some item instances may have changed)
	# RedoingSandbox (bool): whether we are redoing sandbox entries reverted during closing of project
	# RequestingControlFrameID: ID of control frame from which redo request was issued (so that redo handler knows
	# where to send reply messages to)
	# return: Success (bool), ReturnArgs (dict) from last redo handler run, RedoMsg (str) explaining the redo just done,
	#   NextRedoMsg (str) explaining what would be redone on the next call of PerformRedo
	assert isinstance(RedoingSandbox, bool)
	assert isinstance(RequestingControlFrameID, str)
	Success = True
	RedoMsg = NextRedoMsg = ''
	ReturnArgs = {}
	ChainPaused = False # whether we paused the redo chain because we reached an item with Chain == 'Stepwise'
	SkipRefresh = False # whether we can skip refreshing the GUI after this action, as there are chained redo's to follow
	if Proj.RedoList:  # check if there are any items in the redo list
		# find where we should redo up to
		RedoUpToIndex = FindLastRecordToUndo(Proj.RedoList, StartFromIndex=len(Proj.RedoList) - 1, Redoing=True)
		RedoHowManyMinus1 = (len(Proj.RedoList) - RedoUpToIndex) - 1
		RedoneCount = 0 # how many records actually redone
		# redo those records between the end and RedoUpToIndex
		for RedoLoopIndex, ThisRec in enumerate(
				[Proj.RedoList[i] for i in range(len(Proj.RedoList) - 1, RedoUpToIndex - 1, -1)]):
			if not ChainPaused:
				if ThisRec.RedoChain == 'Stepwise': ChainPaused = True
				RedoListLen = len(Proj.RedoList) # for debugging, see 2 lines below
				# call RedoHandler to redo a single action
				# Chained (bool): whether the handler can skip closeout actions (because there are more data changes to follow)
				# ChainWaiting (bool): whether more chained redo items are waiting due to the previous item having Chain=='Stepwise'
				# SkipRefresh (bool): whether the handler can skip recalc/refresh (because there are more data changes to follow)
				# ChainUndo (str): the Chain value that the undo record stored by the redo handler should set
				#   ('NoChain' if this is the first or only redo in the chain, otherwise 'Avalanche' or 'Stepwise')
				# Expecting Redohandler to return a dict (passed on in exit arg ReturnArgs) or None
				SkipRefresh = (RedoLoopIndex != RedoHowManyMinus1)
				ReturnArgs = ThisRec.RedoHandler(Proj, ThisRec, ChainWaiting=ChainPaused,
					SkipRefresh=SkipRefresh,
					ChainUndo=ThisRec.Chain, RequestingControlFrameID=RequestingControlFrameID)
				if ReturnArgs is None: ReturnArgs = {}
				assert isinstance(ReturnArgs, dict)
				RedoneCount += 1
				if len(Proj.RedoList) != RedoListLen:
					print("UN220 DEBUG MESSAGE: looks like 'Redoing' flag wasn't set in call to AddToUndoList in Redo handler")
				# update Success flag
				if 'Success' in ReturnArgs:
					if type(ReturnArgs['Success']) is bool:
						Success = Success and ReturnArgs['Success']
					else:
						print("UN1371 Oops, non-bool Success value received from Redo handler: '%s'" % ThisRec.HumanText)
				else:
					Success = True # if no Success flag returned, assume all is well
		# get human-readable message confirming what action was just redone
		assert hasattr(Proj.RedoList[RedoUpToIndex], 'HumanText'),\
			"UN1380 Oops, Redo item '%s' has no 'HumanText'" % Proj.RedoList[RedoUpToIndex].InternalName
		assert isinstance(Proj.RedoList[RedoUpToIndex].HumanText, str),\
			"UN1382 Oops, HumanText attribute of Redo item '%s' isn't a string" % Proj.RedoList[RedoUpToIndex].InternalName
		ReturnArgs['RedoMsg'] = _(Proj.RedoList[RedoUpToIndex].HumanText)
		# remove the redo records just redone
		Proj.RedoList = Proj.RedoList[:-RedoneCount]
		# find the message of the last record that would be redone on next call
		if Proj.RedoList:  # check there are still some items left in the redo list
			NextRedoUpToIndex = FindLastRecordToUndo(Proj.RedoList, StartFromIndex=len(Proj.RedoList) - 1, Redoing=True)
			assert hasattr(Proj.RedoList[NextRedoUpToIndex], 'HumanText'),\
				"UN1387 Oops, Redo item '%s' has no 'HumanText'" % Proj.RedoList[NextRedoUpToIndex].InternalName
			assert isinstance(Proj.RedoList[NextRedoUpToIndex].HumanText, str),\
				"UN1389 Oops, HumanText attribute of Redo item '%s' isn't a string" % Proj.RedoList[NextRedoUpToIndex].InternalName
			ReturnArgs['NextRedoMsg'] = _(Proj.RedoList[NextRedoUpToIndex].HumanText)
		else: ReturnArgs['NextRedoMsg'] = ''
	else: # empty redo list
		ReturnArgs['Success'] = False
		ReturnArgs['RedoMsg'] = ''
		ReturnArgs['NextRedoMsg'] = ''
	ReturnArgs['SkipRefresh'] = SkipRefresh
	return ReturnArgs # ReturnArgs will be dict

def FindLastRecordToUndo(RecordList, StartFromIndex=None, Redoing=False):
	# find the record immediately before the last record in RecordList with Chain or RedoChain==True,
	# starting to search backwards from StartFromIndex
	# returns the index of that record
	# If every record from StartIndex back to the start of UndoList has Chain or RedoChain==True, returns 0
	# RecordList: list of UndoItems
	# StartFromIndex: int (if None, start from end of UndoList)
	# Redoing (bool): whether we are actually redoing rather than undoing (i.e. whether to look at Chain or RedoChain)
	assert type(RecordList) is list, "UN228 FindLastRecordToUndo: RecordList isn't a list"
	if StartFromIndex is None: # start from end of UndoList
		StartFromIndex = len(RecordList) - 1
	assert type(StartFromIndex) is int, "UN229 FindLastRecordToUndo: StartFromIndex isn't an integer"
	assert (StartFromIndex >= 0) and (StartFromIndex < len(RecordList)),\
		"UN231 FindLastRecordToUndo: StartFromIndex has unacceptable value %d" % StartFromIndex
	assert isinstance(Redoing, bool)
	Undoing = True
	ThisIndex = StartFromIndex
	ChainAttribName = 'RedoChain' if Redoing else 'Chain'
	while Undoing and (ThisIndex > 0):  # any more items in record list?
		# (no need to check the 0'th one, cos we will return 0 anyway)
#		Undoing = getattr(RecordList[ThisIndex], ChainAttribName, False) # stop after this one if Chain/RedoChain==False
		Undoing = (getattr(RecordList[ThisIndex], ChainAttribName) != 'NoChain') # stop after this one if Chain/RedoChain=='NoChain'
		if Undoing: ThisIndex -= 1
	return ThisIndex

def AdjustUndoListOnCloseDatabase(Proj, DatabaseToClose):
	# make adjustments to the Undo and Redo lists when a database is closed
	# Need to delete from start of list to the last record that writes to or reads from the database
	# This is because the database is no longer available, so we can't perform any related undo or redo actions
	# Warning, not updated for Chain/RedoChain attrib as str instead of bool
	for ListToAdjust, ListAttrib in ( (Proj.UndoList, 'UndoList'), (Proj.RedoList, 'RedoList') ):
		# First, work backwards through the Undo/Redo list until the most recent record touching the database is found
		TouchDBFound = False
		Index = len(ListToAdjust) - 1
		while (Index >= 0) and not TouchDBFound:
			TouchDBFound = (ListToAdjust[Index].WritesDatabase == DatabaseToClose) or\
				(ListToAdjust[Index].ReadsDatabase == DatabaseToClose)
			Index -= 1 # this leaves Index one less than the last item touching the database
		Index += 1 # leave Index at the last item touching the database
		if TouchDBFound:
			# if the found item is in a chain, need to delete the whole chain, so move forward to the end of the chain
			ChainEndFound = False
			while (Index < len(ListToAdjust)) and not ChainEndFound:
				ChainEndFound = not ListToAdjust[Index].Chain
				Index += 1
			# delete undo/redo records from ChainIndex-1 if chain end found,
			# else delete entire undo/redo list (because all remaining items are chained to the last database-touching item)
			# and write the revised list back into the project
			if ChainEndFound: setattr(Proj, ListAttrib, ListToAdjust[Index:])
			else: setattr(Proj, ListAttrib, [])

def RemoveLastInstanceOfAttribInUndoList(Proj, AttribName):
	# search for the last item in Proj's UndoList containing attrib named AttribName (str)
	# and delete the attrib (not the whole record)
	assert isinstance(AttribName, str)
	if Proj.UndoList: # any records in the undo list?
		ThisIndex = len(Proj.UndoList) - 1
		AttribStillToRemove = True
		while AttribStillToRemove and (ThisIndex >= 0):
			if hasattr(Proj.UndoList[ThisIndex], AttribName):
				delattr(Proj.UndoList[ThisIndex], AttribName)
				AttribStillToRemove = False
			ThisIndex -= 1

# remove the dummy definition of _()
del _