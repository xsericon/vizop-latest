#!/usr/bin/python
# -*- coding: utf-8 -*-
# undo module: part of Vizop, (c) 2014 Peter Clarke. Contains general code for managing undo/redo
# undo/redo handlers for each specific operation are embedded in the code for those operations

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import

def AddToUndoList(Proj, DidWhat, **args):
	# Add an entry to the Undo list for Proj.  **args contains any necessary info to identify the exact action (in the form param=value).
	# Separate undo lists are kept for each open project, so that when the Undo command comes, only actions in the current project are undone
	# args can contain a ChainCount integer value.  If a record is undone, the preceding ChainCount records also need to be undone
	# args can contain a dictionary of info, named InfoAsDic.  May need to unpack this?
	# if ChainCount arg supplied, increment it by 1 and return it, else return 1
	Proj.UndoList += [ (DidWhat, args) ] # TODO: combine with previous change if they act on identical entities (parm, etc) and don't increment ChainCount
	print("U16 Added undo: ", DidWhat)
	return args.get('ChainCount', 0) + 1

def PerformUndoOnCancel(Proj, TargetUoCValue):
	"""
	If most recent undo records are marked with "undo on Cancel" and their UndoOnCancel value >= TargetUoCValue, they are undone.
	Should be called when "Cancel" selected in an editing dialogue
	No need for VizopTalks here, as this undo should be 'transparent'. Also no need to store Redo record.
	"""
	Undoing = True
	while Undoing and Proj.UndoList: # check Undo list items starting from end of list, unless list is empty
		ThisUndoIndex = Proj.UndoList[-1][1].get('UndoOnCancel', None) # get UndoOnCancel value for final Undo record
		if (ThisUndoIndex is not None): # does the record have any UndoOnCancel value?
			if ThisUndoIndex >= TargetUoCValue: # should we undo this one?
				PerformSingleUndo(Proj, Proj.UndoList[-1])
				print("U31 Performing undo: ", Proj.UndoList[-1][0])
				Proj.UndoList = Proj.UndoList[:-1] # remove it from undo list
			else: Undoing = False # stop undoing
		else: Undoing = False

def SetUp4UndoOnCancel(Proj):
	"""
	This should be called at the start of any routine that requires Undoable tasks to be Undone when a Cancel command is issued.
	Returns UndoOnCancel value that should be stored with any Undo records. See Undo spec for details.
	"""
#	if 'UndoOnCancel' in Proj.UndoList[-1][1]: Proj.UndoOnCancelIndex = Proj.UndoList[-1][1]['UndoOnCancel'] + 1
#	else: Proj.UndoOnCancelIndex = 0 # if endmost Undo record has no UndoOnCancel, assign arbitrary value
#	return Proj.UndoOnCancelIndex
	# above is longer version of below:
	return Proj.UndoList[-1][1].get('UndoOnCancel', -1) + 1

def PerformSingleUndo(Proj, UndoRecord=(None, {})):
	"""
	Perform undo of a single record in the project's undo list
	This is done by calling UndoHandler in the UndoRecord dic, sending it args: Proj, DidWhat, {info dic as keyword args}
	Doesn't generate VizopTalks message, as there may be multiple undo's in a chain
	"""
	if UndoRecord[0]:
		UndoHandler = UndoRecord[1].pop('UndoHandler', None) # find UndoHandler, and remove it from the info dic (needn't be passed as an arg)
		for UnwantedItem in ['ChainCount']: UndoRecord[1].pop(UnwantedItem, None) # remove items that needn't be passed to handler as args
		if UndoHandler:
			try:
#				apply(UndoHandler, (Proj, UndoRecord[0]), UndoRecord[1]) # the old way. RIP apply()
				UndoHandler(Proj, UndoRecord[0], **UndoRecord[1])
			except NameError: print("Oops, Undo handler for '%s' not found (problem code U57). This is a bug; please report it" % UndoRecord[0])
		else: print("Oops, Undo handler for '%s' not specified (problem code U58). This is a bug; please report it" % UndoRecord[0])

def AddToRedoList(Proj, DidWhat, RedoChain=0, **Args): # similar to AddToUndoList()
	Proj.RedoList += [ (DidWhat, Args) ] # TODO: combine with previous change if they act on identical entities (parm, etc) and don't increment RedoChain
	print("U62 Added redo: ", DidWhat)
	return RedoChain + 1

