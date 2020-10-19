#!/usr/bin/python
# -*- coding: utf-8 -*-
# Module text: part of Vizop, (c) 2020 Peter Clarke

from __future__ import division  # makes a/b yield exact, not truncated, result
import wx, os

# vizop modules
import utilities, info

TextEscStartChar = chr(1) # character used to initiate formatting command in text strings
TextEscEndChar = chr(2) # character used to terminate formatting command in text strings
TextEscEndArg = chr(3) # terminates argument to formatting command
DefaultElementTextFont = 'Flange-Light'  # default properties for text inside elements
MinTextPointSize = 4
DefaultTextPointSize = 11
MaxTextPointSize = 99
DefaultTextVertFactor = 100  # scale value that means normal scale
MinTextVertFactor = 5  # min and max allowable % of base font size for midtext size changes
MaxTextVertFactor = 999
DefaultTextColour = (0xE6, 0xE6, 0xFA)  # grey-blue
DefaultTextHorizAlignment = 'Centre'
DefaultTextVertAlignment = 'Centre'
MinTextLineSpacing = 0.1
DefaultTextLineSpacing = 1.0
MaxTextLineSpacing = 10
DefaultBIUSValue = 1 # default value of bold, italic, underlined, standout attrib of TextObjects
BIUSNoEffectValue = 1 # value of bold/(etc) attrib meaning "no effect", ie not bold/(etc)
StandoutIncrement = 0.5  # fraction by which point size of text is increased for normal degree of Standout
StandoutBoxXOverhang = 5  # amount by which L and R edges of box drawn behind standing out text exceeds size of text, in canvas coords
StandoutBoxYOverhang = 5
WordBreakCharsToRight = ' `~)-=]}\\;>/\n' + info.NewlineSymbol
WordBreakCharsToLeft = ' `~(-=[{\\;</\n' + info.NewlineSymbol

# embeddable text formatting commands
TextFormatCommandHash = {'B': 'Bold', 'U': 'Underlined', 'I': 'Italics', 'S': 'Standout', 'H': 'Highlight',
	'F': 'Font', 'f': 'Font-Default', 'Z': 'Scale', 'z': 'No-Scale',
	'V': 'Vert-Offset', 'v': 'No-Vert-Offset', 'X': 'All-Default', 'C': 'Colour', 'c': 'Colour-Default', 'T': 'Tag'}
TakesStringArg = 'FT' # string arg expected after these commands
TakesIntArg = 'BUISZVH' # integer arg expected after these commands
TakesHexArg = 'C' # hex string expected after this command
# make reverse of above hash table
TextFormatCommandRevHash = {}
for (p, q) in TextFormatCommandHash.items(): TextFormatCommandRevHash[q] = p

def BrighterThan(OldCol, PercentBrighter=50):  # return colour that is a notional % brighter than OldCol
	return tuple([min(255, d + PercentBrighter) for d in OldCol[:3]]) + OldCol[3:]  # don't increment alpha parm, if any

def ReverseColour(OldCol): # return colour that shows up clearly in reverse-video against OldCol; used for highlighting
	if False in [100 < OldCol[c] < 160 for c in range(3)]: # it's not mid-grey; flip each colour channel to 255-c
		return tuple([255 - OldCol[c] for c in range(3)])
	else: # special case: mid-grey colours are converted to light blue
		return (0xAF, 0xDE, 0xF3)

class TextObject(object):
	# text contained within an element, along with its formatting attributes

	def __init__(self, Content='', **Args):
		object.__init__(self)
		assert isinstance(Content, str)
		self.Content = Content # text to display (str)
			# Can contain <CR> (chr(13)) and escape sequences consisting of <elements.text.TextEscStartChar> followed by:
			# B: bold*; U: underlined*; I: italics*; S: standout*; H: highlight*; X: revert all formatting to default
			# (commands marked * take integer arg: 0 = default, 1 = no effect, 2 = minimum effect (eg single underline), 255 = maximum effect)
			# C rrggbbaa: change colour as specified (8 hex digits); c: revert to default colour
			# F fontname <TextEscEndChar>: change font; f: revert to default font
			# Z n <TextEscEndChar>: change point size to n% of default (n unsigned integer); z: revert to default point size
			# V n <TextEscEndChar>: offset characters by n% of character height (n +ve or -ve integer); v: revert to no offset
			# changes to the syntax need to be reflected in ParseFormatCommand() and InterpretFormatCommand()
		self.Font = DefaultElementTextFont
		self.PointSize = DefaultTextPointSize # basic (user-specified) size before adjusting for zoom, standout etc.
		self.Bold = self.Underlined = self.Italics = self.Standout = self.Highlight = DefaultBIUSValue
		self.Colour = DefaultTextColour
		self.ParaHorizAlignment = DefaultTextHorizAlignment
		self.ParaVertAlignment = DefaultTextVertAlignment
		self.LineSpacing = DefaultTextLineSpacing
		self.ParentSizeBasis = {} # dict: {object size parm: value} used for calculating required text point size based on an object's actual size.
		self.TextSize = None
		# attribs used internally during text rendering
		self.SublineXStart = [] # per subline, the starting X coord relative to frame
		# soak up any attribs provided in Args (dangerous, no value checks done)
		self.__dict__.update(Args)

	def RequiredTextPointSizeInCU(self, TextIdentifier, PointSize, ParentSizeBasis=None):
		# return text point size adjusted to take account of animations, but not zoom. Placeholder, for future
		return PointSize

def SplitWithEscChars(line):
	# return line split into substrings at TextEscStartChar instances, retaining all the chars from the original string
	if TextEscStartChar in line:
		return [t for t in [line[:line.index(TextEscStartChar)]] + \
		   [TextEscStartChar + s for s in line[line.index(TextEscStartChar) + 1:].split(TextEscStartChar)] if len(t) > 0]
	return [line]  # unsplit if no TextEscStartChar in line


def ParseFormatCommand(CmdString, CheckForEscChar=False):  # parse format command from start of CmdString
	# if CheckForEscChar is True: check whether CmdString begins with "I'm a command" signal character, and return 'command not found' result if not
	# return: (Command (long name), ArgValue, Remainder of CmdString)
	# where Command is any value in TextFormatCommandHash and ArgValue is a string or integer argument (or None if N/A)
	global TextFormatCommandHash
	if (CmdString == ''): return ('', None, '')
	if CheckForEscChar:
		if (CmdString[0] == TextEscStartChar): CmdString = CmdString[1:]  # chop off the signal character
		else: return ('', None, CmdString)  # no "I'm a command" signal found; return CmdString intact
	# Get command char first
	CommandChar = CmdString[0]
	if CommandChar in TextFormatCommandHash:
		Command = TextFormatCommandHash[CommandChar]
		CmdString = CmdString[1:]  # chop off the command char
		if CommandChar in (TakesStringArg + TakesIntArg + TakesHexArg): # try to get arg. If TextEscEndChar missing, read to end of line
			if not (TextEscEndChar in CmdString): CmdString += TextEscEndChar # bug trapping
			SplitAtTerminator = CmdString.split(TextEscEndChar, 1)
			ArgString = SplitAtTerminator[0]
			CmdString = SplitAtTerminator[1]  # balance of input string after terminator
			if CommandChar in TakesIntArg: # convert to integer if necessary. Can't use int(), may raise ValueError
				if ArgString[0] == '-': # trap negative value
					Factor = -1
					ArgString = ArgString[1:]  # chop off the negative sign
				else: Factor = 1
				ArgInteger = utilities.str2int(ArgString, 24) * Factor  # the 24 will be returned if no meaningful integer can be found
				return (Command, ArgInteger, CmdString)
			else: return (Command, ArgString, CmdString)
		else: return (Command, None, CmdString)  # command found; no arg expected
	else: return ('', None, CmdString)  # command not found

def StripOutEscapeSequences(RichText, CommandType=[]): # Returns RichText with formatting command sequences removed
	# If CommandType is [], all commands are removed, otherwise removes only commands listed (uses long form, eg 'Font')
	assert isinstance(RichText, str)
	index = 0  # read along RichText, looking for command sequences
	while (index < len(RichText)):
		if RichText[index] == TextEscStartChar: # command found; chop it out of RichText
			(Command, v, Tail) = ParseFormatCommand(RichText[index + 1:])
			if (CommandType == []) or (Command in CommandType):
				RichText = RichText[:index] + Tail  # remove this command
			else: index += len(RichText) - len(Tail)  # skip over this command
		else: index += 1  # command not found; step on to next char
	return RichText

def RemoveHighlightCommands(RichText):
	# remove any highlight commands from RichText. Provided as a convenience function for calling from other modules
	# TODO optimization: could run faster if we just search for the index of highlight commands specifically
	return StripOutEscapeSequences(RichText, CommandType='Highlight')

def FindnthChar(RichStr, n, IgnoreNewlines=False):
	# find the index of the n'th visible character in RichStr (counting from zero), skipping over escape sequences
	# IgnoreNewlines (bool): whether to skip \n characters
	assert isinstance(IgnoreNewlines, bool)
	ExtendedRichStr = RichStr + 'X' # The +'X' is to avoid crash when end of RichStr reached
	OrigRichStrLength = len(ExtendedRichStr)
#	ChoppedChar = ''
	while (n >= 0) and (ExtendedRichStr != 'X'): # chop chars and command sequences off ExtendedRichStr one by one
		# look for commands and newlines
		while (ExtendedRichStr[0] == TextEscStartChar) or (IgnoreNewlines and ExtendedRichStr[0] == '\n'):
			# did we find a command sequence? If so, remove it
			if ExtendedRichStr[0] == TextEscStartChar:
				(c, v, ExtendedRichStr) = ParseFormatCommand(ExtendedRichStr[1:])
			# did we find a newline? If so, remove it
			else:
				ExtendedRichStr = ExtendedRichStr[1:]
#		while IgnoreNewlines and (RichStr + 'X')[0] == '\n': # skip over newline characters, if required
#			RichStr = RichStr[1:]
#		# chop off a single non-command char
#		ChoppedChar = (RichStr + ' ')[0] # the + ' ' is in case RichStr is empty
		if n != 0: ExtendedRichStr = ExtendedRichStr[1:] # chop off a single non-command if we haven't reached the target count
#		# decrement char counter unless we found a newline and we're supposed to ignore newlines
#		if not (IgnoreNewlines and ChoppedChar == '\n'):
		# decrement char counter
		n -= 1
	return OrigRichStrLength - len(ExtendedRichStr)

def FindFormatCommandBeforeNthChar(RichStr, n):
	# find index of the first format command before Nth visible char in RichStr
	# if Nth char is not preceded by a format command, returns same as FindnthChar()
	if (n == 0): return 0
	return FindnthChar(RichStr, n - 1) + 1

def MakeFormatCommand(CommandChar, *args):  # return string containing escape character, CommandChar, and any necessary args and terminator
	OutStr = TextEscStartChar + CommandChar
	if CommandChar in TakesStringArg: OutStr += str(args[0]) + TextEscEndChar
	elif CommandChar in TakesIntArg: OutStr += str(args[0]) + TextEscEndChar
	elif CommandChar in TakesHexArg: OutStr += utilities.HexTuple2str(args[0]) + TextEscEndChar  # colour change as string of hex digits
	return OutStr

def InsertFormatCommand(RichStr, Pos, CommandType, *args):
	# insert a formatting command into the rich string RichStr, at char pos Pos. args are necessary arguments to the command, eg font name
	# If there's already a formatting command of the same CommandType at this location, replace it; otherwise insert it
	CommandChar = TextFormatCommandRevHash[CommandType]  # get the required command character to insert
	CommandLoc = FindFormatCommandBeforeNthChar(RichStr, Pos)  # get the location to insert the command
	# check through all commands at the location, to see if any match the required command
	StringHead = RichStr[:CommandLoc]  # chunk of string before insertion point
	StringTail = RichStr[CommandLoc:]  # chunk of string after insertion point
	CommandHere = 'X'  # dummy to initiate loop
	CommandFound = False
	while (not CommandFound) and (CommandHere != ''):
		StringBeforeParsing = StringTail
		(CommandHere, Arg, StringTail) = ParseFormatCommand(StringTail, CheckForEscChar=True)  # parse format command from start of StringTail
		if (CommandHere == CommandType):  # found command that matches the one we need to insert
			if not CommandFound: StringHead += MakeFormatCommand(CommandChar, args[0])  # replace it (first time only)
			CommandFound = True
		else: StringHead += utilities.ChopFromEnd(StringBeforeParsing, len(StringTail))  # splice the command found back into the string
	if not CommandFound: StringHead += MakeFormatCommand(CommandChar, args[0])  # add the required command, if not already inserted
	return StringHead + StringTail

def CurrentFormatStatus(TextObj, RichStr, Pos, FmtParm='Font'):  # return state of formatting parm supplied at Pos'th visible char in RichStr. Returns:
	# FmtParm = 'Font', 'Colour': return name of font/colour value
	# FmtParm = 'Scale', 'Vert-Offset', 'Bold', 'Underlined', 'Italics', 'Standout', 'Highlight': return parm value
	# Takes account of default format, if no relevant format commands found

	def DefaultParmState(TextObj, FmtParm):  # returns default state of FmtParm
		if FmtParm == 'Scale': return DefaultTextVertFactor
		if FmtParm == 'Vert-Offset': return 0
		if FmtParm in ['Bold', 'Italics', 'Underlined', 'Standout', 'Highlight']: return 1
		return TextObj.__dict__[CmdHash[FmtParm]['Parm']]

	CmdHash = {'Font': {'Set': 'Font', 'Unset': 'Font-Default', 'ArgExpected': True, 'Parm': 'Font'}, \
		'Bold': {'Set': 'Bold', 'Unset': 'Bold', 'ArgExpected': True, 'Parm': 'Bold'}, \
		'Underlined': {'Set': 'Underlined', 'Unset': 'Underlined', 'ArgExpected': True, 'Parm': 'Underlined'}, \
		'Italics': {'Set': 'Italics', 'Unset': 'Italics', 'ArgExpected': True, 'Parm': 'Italics'}, \
		'Standout': {'Set': 'Standout', 'Unset': 'Standout', 'ArgExpected': True, 'Parm': 'Standout'}, \
		'Highlight': {'Set': 'Highlight', 'Unset': 'Highlight', 'ArgExpected': True, 'Parm': 'Highlight'}, \
		'Scale': {'Set': 'Scale', 'Unset': 'No-Scale', 'ArgExpected': True, 'Parm': None}, \
		'Vert-Offset': {'Set': 'Vert-Offset', 'Unset': 'No-Vert-Offset', 'ArgExpected': True, 'Parm': None}, \
		'Colour': {'Set': 'Colour', 'Unset': 'Colour-Default', 'ArgExpected': True, 'Parm': 'Colour'} }
	AllDefaultCmd = 'All-Default'  # format command to set all parms to default
	ParmState = DefaultParmState(TextObj, FmtParm)  # this will be the returned state
	RichStr = RichStr[:FindnthChar(RichStr, Pos)]  # truncate RichStr at Pos (or could count visible chars in 'while' loop below, quicker)
	while (RichStr != ''):  # work along input string
		(CommandHere, Arg, RichStr) = ParseFormatCommand(RichStr, CheckForEscChar=True)  # parse format command from start of RichStr
		if (CommandHere == ''): RichStr = RichStr[1:]  # no command found: chop a character and continue
		else:  # command found; see if it matches the one we're looking for
			if (CommandHere == CmdHash[FmtParm]['Set']):
				if CmdHash[FmtParm]['ArgExpected']:  # store current value of parm's arg
					if (FmtParm == 'Colour'): ParmState = utilities.str2HexTuple(Arg)
					else: ParmState = Arg
				else: ParmState = True  # parm is currently set (e.g. bold)
			elif (CommandHere == CmdHash[FmtParm]['Unset']):  # return 'unset' value of parm
				if CmdHash[FmtParm]['ArgExpected']: ParmState = DefaultParmState(TextObj, FmtParm)  # store default value of parm's arg
				else: ParmState = False  # parm is currently unset (e.g. bold)
			elif (CommandHere == AllDefaultCmd):  # return default value of parm
				ParmState = DefaultParmState(TextObj, FmtParm)
	return ParmState


def MidTextFormatChange(TextObj, RichStr, StartIndex, EndIndex, Parm='', CommandOnOff=True, StartCommand='Font', StopCommand='Font-Default', \
	StripCommands=['Font', 'Font-Default']):
	# Updates RichStr to handle change of format request in segment from StartIndex to EndIndex (indices of visible chars)
	# CommandOnOff: boolean, whether function (font/bold/etc) is activated
	# returns RichStr with StartCommand and Parm (eg font name) inserted, 'put it back how it was' command at end of segment.
	# any format commands of type StripCommands removed midsegment
	# First, strip out existing format commands of type StartCommand within the highlighted text
	StartPos = FindFormatCommandBeforeNthChar(RichStr, StartIndex)
	EndPos = FindnthChar(RichStr, EndIndex)
	RevertTo = CurrentFormatStatus(TextObj, RichStr, EndIndex, StartCommand)  # format to restore after change
	if RevertTo: RevertCmd = StartCommand  # format was positively defined, or boolean == True
	else: RevertCmd = StopCommand
	NewRichStr = RichStr[:StartPos] + StripOutEscapeSequences(RichStr[StartPos:EndPos], CommandType=StripCommands) \
		+ RichStr[EndPos:]
	NewRichStr = InsertFormatCommand(NewRichStr, StartIndex, {True: StartCommand, False: StopCommand}[CommandOnOff], Parm)
		# insert "change format" command
	NewRichStr = InsertFormatCommand(NewRichStr, EndIndex, RevertCmd, RevertTo)  # insert "restore prev format" cmd
	return NewRichStr

def FontInstance(Size=12, Italics=BIUSNoEffectValue, Bold=BIUSNoEffectValue, Underlined=BIUSNoEffectValue, Font=''):
	# return wx.Font instance matching supplied args
	# Size is absolute; zooming, standout etc need to be handled by the calling procedure
	return wx.Font(Size, family=wx.DEFAULT, style={False: wx.NORMAL, True: wx.ITALIC}[(Italics != BIUSNoEffectValue)],
		weight={False: wx.NORMAL, True: wx.BOLD}[(Bold != BIUSNoEffectValue)], underline=(Underlined != BIUSNoEffectValue), faceName=Font)

def RequiredPointSize(BasicPointSize, CanvZoomX=1.0, CanvZoomY=1.0, StandOutFraction=1.0, StandoutIncrement=0.0,
	TextSizeRatio=1.0):
	# return (int) physical point size of text, taking zoom and other args into account
	return int(round(BasicPointSize * 0.5 * (CanvZoomX + CanvZoomY) * (1 + StandOutFraction * StandoutIncrement)
		* TextSizeRatio))

def InterpretFormatCommand(Command, Arg, TextInstance, Bold, Underlined, Italics, Standout, Highlight,
	Font, Scale, VertOffset, Colour):
	# returns values of all args based on input Command and Arg
	if Command == 'Bold': Bold = Arg
	elif Command == 'Underlined': Underlined = Arg
	elif Command == 'Italics': Italics = Arg
	elif Command == 'Standout': Standout = Arg
	elif Command == 'Highlight': Highlight = Arg
	elif Command == 'Font': Font = Arg
	elif Command == 'Font-Default': Font = TextInstance.Font
	elif Command == 'Scale': Scale = Arg
	elif Command == 'No-Scale': Scale = DefaultTextVertFactor
	elif Command == 'Vert-Offset': VertOffset = Arg
	elif Command == 'No-Vert-Offset': VertOffset = 0
	elif Command == 'All-Default':
		Bold = TextInstance.Bold
		Underlined = TextInstance.Underlined
		Italics = TextInstance.Italics
		Highlight = TextInstance.Highlight
		Font = TextInstance.Font
		Colour = TextInstance.Colour
	elif Command == 'Colour':
		Colour = utilities.str2HexTuple(Arg)
	elif Command == 'Colour-Default': Colour = TextInstance.Colour
	else: print("Oops, unrecognised formatting command %s (problem code TE378).  This is a bug, please report it" % Command)
	return (Bold, Underlined, Italics, Standout, Highlight, Font, Scale, VertOffset, Colour)

def CalculateTextSizeAndSpacing(El, Text, TextIdentifier, VertAlignment, CanvZoomX, CanvZoomY):
	# calculate all required values for drawing text, including dividing the text into lines and chunks
	# returned ScaledPointSizeNoZoom does not take account of zoom
	# return:
	#	Sublines (list of str; chars in each subline, rich text)

	def FindYaboveText(El, TextIdentifier, TextLines, FirstYaboveText, LineSpacing, Iterations, VertAlignment, Yhere,
			Xsofar, IsFmtCmd):
		# recursively find optimal Y position for text
		# work through each line of text, split into sublines
		BreakAfter = ' `~)-=]}\\;>/' # chars to split line after. TODO use WordBreakChars global variable
		MinLineFill = 0.55  # fraction of total X available that must be used up when considering where to split sublines (ie no line will be shorter than this)
		MaxTopBottomDiffCentreAligned = 1.1  # target ratio of bottomY:topY when centre aligned
		MinTopBottomDiffCentreAligned = 0.91  # reciprocal of above
		MaxTopBottomDiffBottomAligned = 0.1  # target ratio of bottomY:topY when bottom aligned
		MaxIterations = 10  # to avoid infinite loop
		Sublines = [] # rich text content of each subline
		SublineHeights = [] # list of (height above baseline, descent below baseline) for each subline
		Text.SublineYMid = [] # list of Y coord of middle of the subline for each subline
		Text.SublineX = [ [0] ]  # list of [per subline: [x offset from start of line, at left edge of each character]]
		SublineY = [ [] ]  # list of [per subline: [ (height above baseline, descent below baseline) per character]]
		FinalYaboveText = FirstYaboveText  # starting position for 1st line
		# work through each line
		LastExtraLineSpace = 0  # extra space to delete at bottom of entire text
		YatSublineTop = (El.TextYOffsetInElementInCU(TextIdentifier) * CanvZoomY) + FirstYaboveText
		for (LineNo, Line) in enumerate(TextLines):
			IndexInLine = 0
			MaxHeightInSubline = 0  # total Y, and height above baseline
			MaxYinSubline = -1  # not zero, to ensure fmt cmd at start of line will trigger calc of Xavail
			ThisSubline = ''
			ThisSublineIndexStart = 0  # which index of Line this Subline starts at
			EndOfSubline = False
			XatStartofSubline = 0
			if StripOutEscapeSequences(Line) == '':  # handle empty line
				Text.SublineX[-1] = [0, 1]
				# set height = preceding subline, or = height of first actual char in text if it's the first subline
				# the (10, 5) is a notional value in case no actual chars are found in text
				if (LineNo == 0): SublineY[-1] = [ (sum(Yhere, []) + [ (10, 5) ])[0] ]
				else: SublineY[-1] = SublineY[-2]
				MaxYinSubline = SublineY[-1][0][0] + SublineY[-1][0][1]
				MaxHeightInSubline = SublineY[-1][0][0]
				Yhere[LineNo] = SublineY[-1]
				Sublines.append(' ')
				SublineHeights.append((MaxHeightInSubline, MaxYinSubline - MaxHeightInSubline))
				YatSublineTop += MaxYinSubline * Text.LineSpacing
				ThisSubline = ''
				ThisSublineIndexStart = IndexInLine
				LastExtraLineSpace = MaxYinSubline * (Text.LineSpacing - 1)
				MaxYinSubline = 0
				Text.SublineX.append([0])
				SublineY.append([])
			else:  # non-empty line: find last char that will fit in subline by adding in successive chars
				while (IndexInLine < len(Line)):
					# check if next char increases the height of line; if so, recalculate available X
					FontHeightHere = Yhere[LineNo][IndexInLine][0]  # height above baseline
					FontDescentHere = Yhere[LineNo][IndexInLine][1]
					FontYHere = FontHeightHere + FontDescentHere  # total height, above and below baseline
					if (FontYHere > MaxYinSubline):
						MaxYinSubline = FontYHere
						MaxHeightInSubline = FontHeightHere
						Xavail = max(0, (El.MaxComponentXat(TextIdentifier, YatSublineTop, YatSublineTop + MaxYinSubline) -
							El.MinTextXat(TextIdentifier, YatSublineTop, YatSublineTop + MaxYinSubline)) * CanvZoomX)
						# MaxYInSubline is initialized to -1 to ensure Xavail is set on 1st iteration
					# check if there's enough space to add next char. If so, add it, else start another subline
					XafterNextChar = (Xsofar[LineNo][IndexInLine] - XatStartofSubline)
#					if getattr(Text, 'debug', False): print('TE338 XafterNextChar: ', XafterNextChar,XatStartofSubline)
					if (XafterNextChar <= Xavail) or not ThisSubline:  # 'or not' ensures >= 1 char per subline, to avoid infinite loop
						ThisSubline += Line[IndexInLine]
						Text.SublineX[-1].append(XafterNextChar)
						SublineY[-1].append((FontHeightHere, FontDescentHere))
						IndexInLine += 1
					else: # reached end of subline. Work out suitable place to split it
						EndOfSubline = True
						SplittableIndices = [ ChIndex for ChIndex in range(len(ThisSubline))
							if ThisSubline[ChIndex] in BreakAfter
							if (Xsofar[LineNo][ChIndex + ThisSublineIndexStart - 1] - XatStartofSubline) >= (Xavail * MinLineFill)
							if (Xsofar[LineNo][ChIndex + ThisSublineIndexStart - 1] - XatStartofSubline) <= Xavail
							if not IsFmtCmd[LineNo][ChIndex + ThisSublineIndexStart] ]
						# if any place found, pick the last one; chop off the end of the subline from that point
						if SplittableIndices:
							IndexInLine -= (len(ThisSubline) - SplittableIndices[-1] - 1)
							ThisSubline = ThisSubline[:SplittableIndices[-1] + 1]
							Text.SublineX[-1] = Text.SublineX[-1][:SplittableIndices[-1] + 2]  # 2 because SublineX has extra 0 at the start
							SublineY[-1] = SublineY[-1][:SplittableIndices[-1] + 1]
					if EndOfSubline or (IndexInLine == len(Line)):
						# reached end of subline, or entire line; close out the subline
						EndOfSubline = False
						# remove any leading spaces from subline (but leave one space if that's the only char in subline)
						if ThisSubline:
							while (len(ThisSubline) > 1) and (ThisSubline[0] == ' '):
								ThisSubline = ThisSubline[1:]
								# chop off 2nd item (the space) in SublineX[-1], and reduce other values by the x-size of the space removed
								Text.SublineX[-1][1:] = [Text.SublineX[-1][i + 2] - Text.SublineX[-1][1] for i in range(len(Text.SublineX[-1]) - 2)]
								SublineY[-1] = SublineY[-1][1:]
							# remove any trailing spaces but leave at least one char in subline
							while (len(ThisSubline) > 1) and (ThisSubline[-1] == ' '):
								ThisSubline = ThisSubline[:-1]
								Text.SublineX[-1] = Text.SublineX[-1][:-1]
								SublineY[-1] = SublineY[-1][:-1]
						Sublines.append(ThisSubline)
						SublineHeights.append((MaxHeightInSubline, MaxYinSubline - MaxHeightInSubline))
						Text.SublineYMid.append(YatSublineTop + (0.5 *  MaxYinSubline))
						# prepare for next subline
						YatSublineTop += MaxYinSubline * Text.LineSpacing
						ThisSubline = ''
						XatStartofSubline = Xsofar[LineNo][IndexInLine - 1]
						ThisSublineIndexStart = IndexInLine
						LastExtraLineSpace = MaxYinSubline * (Text.LineSpacing - 1)
						MaxYinSubline = 0
						Text.SublineX.append([0])
						SublineY.append([])
		# after final line, remove the extra gap
		YatTextBottom = YatSublineTop - LastExtraLineSpace
		# check whether text is now in the required position; if not, recurse. No need to do this for Top or Bottom alignment
		if VertAlignment == 'Centre':
			# check ratio of bottom to top gap is in acceptable range
			Ratio = ((El.MaxTextY(TextIdentifier) * CanvZoomY) - YatTextBottom) / (max(0.01, FirstYaboveText))  # max() is to avoid div/0
			if ((Ratio > MaxTopBottomDiffCentreAligned) or (Ratio < MinTopBottomDiffCentreAligned)) and (Iterations < MaxIterations):
				# ratio out of range: try again, adjusting top space by half the difference between top and bottom space
				# the max(0, ) is to avoid the text spilling off the top of the element
				(FinalYaboveText, Sublines, SublineHeights, Text.SublineX, SublineY, YatTextBottom) = FindYaboveText(El, TextIdentifier, TextLines,
					max(0, FirstYaboveText - (0.5 * (FirstYaboveText - (El.MaxTextY(TextIdentifier) * CanvZoomY) + YatTextBottom))),
					LineSpacing, Iterations + 1, VertAlignment, Yhere, Xsofar, IsFmtCmd)
		elif VertAlignment == 'Bottom':
			# check ratio of top to bottom gap is in acceptable range
			Ratio = ((El.MaxTextY(TextIdentifier) * CanvZoomY) - YatTextBottom) / (max(0.01, FirstYaboveText))  # max() is to avoid div/0
			if ((Ratio > MaxTopBottomDiffBottomAligned) or (Ratio < 0)) and (Iterations < MaxIterations):
				# ratio out of range: try again, increasing top space by 90% of bottom space
				# the max(0, ) is to avoid the text spilling off the top of the element
				(FinalYaboveText, Sublines, SublineHeights, Text.SublineX, SublineY, YatTextBottom) = FindYaboveText(El, TextIdentifier, TextLines,
					max(0, FirstYaboveText + (0.9 * ((El.MaxTextY(TextIdentifier) * CanvZoomY) - YatTextBottom))),
					LineSpacing, Iterations + 1, VertAlignment, Yhere, Xsofar, IsFmtCmd)
		return (FinalYaboveText, Sublines, SublineHeights, Text.SublineX, SublineY, YatTextBottom)

	# Main procedure for CalculateTextSizeAndSpacing()
	# First, set initial format settings; intentionally NOT allowing for standout, as standing-out text doesn't get any extra space
	# Find target point size, allowing for change of Element size
	ScaledPointSizeNoZoom = Text.RequiredTextPointSizeInCU(TextIdentifier, Text.PointSize, Text.ParentSizeBasis)
	ItalicsNow = Text.Italics
	BoldNow = Text.Bold
	UnderlinedNow = Text.Underlined
	StandoutNow = Text.Standout
	HighlightNow = Text.Highlight
	FontNow = Text.Font
	ScaleNow = DefaultTextVertFactor
	VertOffsetNow = 0
	ColourNow = Text.Colour
	# make a dummy device context for finding text size
	dc = wx.MemoryDC()
	dc.SetFont(FontInstance(RequiredPointSize(ScaledPointSizeNoZoom, CanvZoomX=CanvZoomX, CanvZoomY=CanvZoomY,
  		StandOutFraction=0.0, TextSizeRatio=1.0), Text.Italics, Text.Bold, Text.Underlined, Text.Font))
	# terminology: line = user defined line, sep by <CR>; subline = split-up line to fit avail x-space; chunk = block of chars with same formatting
	# split text into lines
	TextLines = Text.Content.split('\n') # not using splitlines() because of different behaviour if Content ends with \n
#	if getattr(Text, 'debug', False):
#		print('TE456 Content is now: ', [ord(c) for c in Text.Content])
#		print('TE456 TextLines in CalculateTextSizeAndSpacing:', [c for c in TextLines])
	CharX = []  # nested lists: [ lines: [ chunks: [canvas x after each char in chunk, excluding format commands] ] ]
	ChunkText = []  # nested lists: [ lines: [ string contents of each chunk, including format commands with Esc char] ]
	ChunkY = []  # nested lists: [ lines: [ canvas y (above baseline, below baseline) for each chunk] ]
	# collect x, y info for text in each line
	for line in TextLines:
		CharX.append([])
		ChunkText.append([])
		ChunkY.append([])
		# split line into chunks delimited by formatting command characters, retaining esc chars
		SplitLine = SplitWithEscChars(line)
		for Chunk in SplitLine:
			# change font, if chunk begins with fmt cmd
			(Command, Arg, ChunkRaw) = ParseFormatCommand(Chunk, CheckForEscChar=True)
			if Command:
				(BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, HighlightNow, FontNow, ScaleNow, VertOffsetNow, ColourNow) = InterpretFormatCommand(Command, Arg,
					Text, BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, HighlightNow, FontNow, ScaleNow, VertOffsetNow, ColourNow)  # change parms accordingly
				dc.SetFont(FontInstance(RequiredPointSize(ScaledPointSizeNoZoom * ScaleNow * 0.01, CanvZoomX=CanvZoomX,
			  		CanvZoomY=CanvZoomY, TextSizeRatio=1.0),
					ItalicsNow, BoldNow, UnderlinedNow, FontNow))  # change font, taking no account of Standout (as no extra space is allowed for standout)
			if Chunk: ChunkText[-1].append(Chunk)  # add Chunk to ChunkText unless it's empty (ie blank line)
			# get x, y info for this chunk
			CharX[-1].append(dc.GetPartialTextExtents(ChunkRaw))  # list of x for each char in this chunk
			(w, h, d, l) = dc.GetFullTextExtent(ChunkRaw)  # get y info about chunk
			ChunkY[-1].append(((h - d), d))  # store height info for this chunk
	# build lists: Xsofar, Yhere, IsFmtCmd for each char in lines; used by FindYaboveText()
	Xsofar = []
	Yhere = [] # list of [for each line: [for each char: (font height, font descent)]]
	IsFmtCmd = []
	for (LineNo, Line) in enumerate(TextLines):
		Xsofar.append([])
		Yhere.append([])
		IsFmtCmd.append([])
		Xlast = 0  # X loc of last char added to Xsofar
		for (ChunkNo, Chunk) in enumerate(ChunkText[LineNo]):
			(a, b, ChunkAfterCmd) = ParseFormatCommand(Chunk, CheckForEscChar=True) # split chunk into command and text
			# insert values into lists for the fmt cmd chars, if any
			HowManyFmtChars = len(Chunk) - len(ChunkAfterCmd)
			Xsofar[-1] += [Xlast] * HowManyFmtChars
			Yhere[-1] += [ChunkY[LineNo][ChunkNo]] * HowManyFmtChars
			IsFmtCmd[-1] += [True] * HowManyFmtChars
			# insert values into lists for the raw text chars
			for RawCh in range(len(ChunkAfterCmd)): Xsofar[-1].append(CharX[LineNo][ChunkNo][RawCh] + Xlast)
			Yhere[-1] += [ChunkY[LineNo][ChunkNo]] * len(ChunkAfterCmd)
			IsFmtCmd[-1] += [False] * len(ChunkAfterCmd)
			Xlast = Xsofar[-1][-1]  # store value for start of next chunk
	# recursively find optimal y offset for top of text
	FirstValInYhere = (sum(Yhere, []) + [ (10, 5) ])[0]  # (10, 5) is notional value in case there are no actual chars
	if VertAlignment == 'Centre':  # Start by putting 1st actual char in middle of available y range, offset upwards by half the height of 1st char
		MaxYaboveText = 0.5 * (((El.MaxTextY(TextIdentifier) - El.TextYOffsetInElementInCU(TextIdentifier)) * CanvZoomY)
			- (FirstValInYhere[0] + FirstValInYhere[1]))
	elif VertAlignment == 'Bottom':  # put 1st char at bottom, offset upwards by height of 1st char
		MaxYaboveText = (El.MaxTextY(TextIdentifier) * CanvZoomY) - (FirstValInYhere[0] + FirstValInYhere[1])
	else:  # assume Top alignment
		MaxYaboveText = 0
	(YaboveText, Sublines, SublineHeights, Text.SublineX, SublineY, YatTextBottom) = FindYaboveText(
		El, TextIdentifier, TextLines, MaxYaboveText, Text.LineSpacing, 0, VertAlignment, Yhere, Xsofar, IsFmtCmd)
	return YaboveText, Sublines, SublineHeights, Text.SublineX, SublineY, ScaledPointSizeNoZoom, YatTextBottom

def TextSize(El, Text, TextIdentifier, CanvZoomX, CanvZoomY, VertAlignment='Top'):
	# returns (Xsize, Ystart, Yend) for text in El
	(YaboveText, Sublines, SublineHeights, Text.SublineX, SublineY, ScaledPointSizeNoZoom, YatTextBottom) =\
		CalculateTextSizeAndSpacing(El, Text, TextIdentifier, VertAlignment, CanvZoomX, CanvZoomY)
	# get Xsize from the X-coord of the end of the longest subline
	Xsize = max([ThisSubline[-1] for ThisSubline in Text.SublineX])
	return (Xsize, YaboveText, YatTextBottom)

def DrawTextInElement(El, dc, Text, TextIdentifier, LayerOffsetX=0, LayerOffsetY=0, CanvZoomX=1.0, CanvZoomY=1.0,
  	PanX=0, PanY=0, TextSizeRatio=1.0, VertAlignment='Centre', DrawCursor=False, CursorIndex=0,
			CursorColour=(0,0,0), debug=False):
	# draw Text (text object instance) inside element El, correctly positioned in available y-space.
	# TextIdentifier (int): which text object in El we are drawing; El needs this to work out which Y values to supply
	# LayerOffsetX/Y is the pixel offset to apply for the display device (compensating for offset of device drawing box within device)
	# PanX, PanY (int/float): pixel offset for the element within the display device due to panning
	# TextSizeRatio is enlargement factor for Standout; simply increases the font size
	# VertAlignment can be 'Centre', 'Top' or 'Bottom'
	# DrawCursor (bool): whether to draw caret
	# CursorIndex (int): position in raw text at which to draw caret
	# CursorColour (3-tuple of int)
	# Overall strategy:
	# 1. set up data needed to determine best Y to draw text and where to split lines
	# 2. recursively select best Y using FindYaboveText() (only needed if VertAlignment is 'Centre')
	# 3. do the drawing using RenderText()

	def RenderText(Ytop, Sublines, SublineHeights, SublineX, SublineY, ScaledPointSizeNoZoom, StandoutBoxColour, ZoomX,
				   ZoomY):
		# do the actual drawing, starting at Ytop

		def ProcessStandout(Sublines, SublineNo, SublineX, SublineY, SublineHeight, FmtCmds, ChunkLength, StandoutNow):
			# work through subline, adjust SublineX for any character that is standing out
			# StandoutNow is True if standout is active at the start of the subline
			# return adjusted SublineX and whether Standout is True at end of subline (ready for next subline)
			# TODO for future: assumes only one value of standout intensity (ie only on or off)
			ChunkNo = 0
			CharsSoFar = 0
			SOStartChar = 0
			SOEndChar = len(Sublines[SublineNo]) - 1  # default if standout continues to end of subline
			while ChunkNo < len(FmtCmds[SublineNo]) - 1:  # work through each chunk
				while (ChunkNo < len(FmtCmds[SublineNo]) - 1) and not StandoutNow:  # scan until standing-out chunk found
					# the chunk has Standout if there's a Standout command with arg != BIUSNoEffectValue
					StandoutNow = (FmtCmds[SublineNo][ChunkNo][0] == 'Standout') and (FmtCmds[SublineNo][ChunkNo][1] != BIUSNoEffectValue)
					if StandoutNow: SOStartChar = CharsSoFar  # index of char in subline where standout starts
					CharsSoFar += ChunkLength[SublineNo][ChunkNo]
					ChunkNo += 1
				if StandoutNow:  # standout start found; scan until end of standout or end of line
					while (ChunkNo < len(FmtCmds[SublineNo])) and StandoutNow:  # scan until not-standing-out chunk found
						StandoutNow = not ((FmtCmds[SublineNo][ChunkNo][0] == 'Standout') and (FmtCmds[SublineNo][ChunkNo][1] != BIUSNoEffectValue))
						if not StandoutNow: SOEndChar = CharsSoFar  # capture end of standout. FIXME SOEndChar value wrong
						CharsSoFar += ChunkLength[SublineNo][ChunkNo]
						ChunkNo += 1
					# find upwards y-adjustment of standing-out chars, in canvas coords. FIXME assumes whole standout has same point size, and same vert-offset
					VertAdjust = SublineHeight * StandoutIncrement * 0.5  # 0.5 is a fudge factor to make vert pos look right
					# adjust x, y of chars in standing-out range
					NSOStartX = SublineX[SublineNo][SOStartChar]  # start of unexpanded x range
					NSOEndX = SublineX[SublineNo][SOEndChar]  # end of unexpanded x range
					SOEndX = 0.5 * ((1 + StandoutIncrement) * (NSOEndX - NSOStartX) + NSOStartX + NSOEndX)  # end of expanded x range
# 					SOStartX = NSOStartX + NSOEndX - SOEndX # start of expanded x range. This line may be equivalent to next one, TODO check and use simpler one
					SOStartX = 0.5 * (NSOStartX + NSOEndX - (1 + StandoutIncrement) * (NSOEndX - NSOStartX))  # start of expanded x range
					for i in range(SOStartChar, SOEndChar - 1):  # adjust x pos of each char
						SublineX[SublineNo][i] = ((0.5 * SublineX[SublineNo][i] * (SOEndX - SOStartX) - 0.25 * (SOEndX * SOEndX - SOStartX * SOStartX)) /
							(0.5 * (0.1 + NSOEndX - NSOStartX))) + (0.5 * (NSOStartX + NSOEndX))  # 0.1+ to avoid div/0
						SublineY[SublineNo][i] = (SublineY[SublineNo][i][0] + VertAdjust, SublineY[SublineNo][i][1])
			return (SublineX, SublineY, StandoutNow)

		def InitializeFont(): # set all parms to "default" for this text
			dc.SetTextForeground(Text.Colour if Text.Highlight == BIUSNoEffectValue else ReverseColour(Text.Colour))
			dc.SetBackgroundMode(wx.TRANSPARENT) # no text background colour; Rappin p380
			ItalicsNow = Text.Italics
			BoldNow = Text.Bold
			UnderlinedNow = Text.Underlined
			StandoutNow = Text.Standout
			HighlightNow = Text.Highlight
			FontNow = Text.Font
			ScaleNow = DefaultTextVertFactor
			VertOffsetNow = 0
			ColourNow = Text.Colour
			return (BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, HighlightNow, FontNow, ScaleNow, VertOffsetNow,
				ColourNow)

		# start of RenderText(): initialize font
		(BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, HighlightNow, FontNow, ScaleNow, VertOffsetNow,
			ColourNow) = InitializeFont()
		FontInstanceNow = FontInstance(RequiredPointSize(ScaledPointSizeNoZoom, CanvZoomX=ZoomX, CanvZoomY=ZoomY, TextSizeRatio=TextSizeRatio), Text.Italics, \
									   Text.Bold, Text.Underlined, Text.Font)
		dc.SetFont(FontInstanceNow)
		Text.SublineXStart = [] # per subline, the starting X coord relative to frame
		FmtCmds = []  # [ per subline, [(format command, arg, remainder) per chunk] ]
		ChunkLength = []  # [ per subline, [total length of each chunk including fmt cmds] ]
		# draw the text, one subline at a time
		YStart = Ytop
		StandoutAtSublineStart = StandoutNow  # whether first char in subline is standing out
		for (SublineNo, Subline) in enumerate(Sublines):
			FmtCmds.append([])
			ChunkLength.append([])
			# analyse subline first: split subline into chunks delimited by formatting command characters
			SplitSubLine = SplitWithEscChars(Subline)
			for (ChunkNo, Chunk) in enumerate(SplitSubLine):  # for each chunk, get any fmt command and its arg
				FmtCmds[-1].append(ParseFormatCommand(Chunk, CheckForEscChar=True))
				ChunkLength[-1].append(len(Chunk))
			# find line height and X limits within element
			SublineHeight = SublineHeights[SublineNo][0]  # Y distance from subline top to baseline
			SublineTHeight = SublineHeight + SublineHeights[SublineNo][1]  # Y distance from subline top to descender
			# leftmost available position for text within El, relative to layer, in pixels
			# TODO consider using FindTextXYStart() to replace the following lines
			MinXavail, DummyY = utilities.ScreenCoords(El.MinTextXat(TextIdentifier,
				YStart, YStart + SublineTHeight), 0, Zoom=ZoomX, PanX=0, PanY=0)
			MaxXavail, DummyY = utilities.ScreenCoords(El.MaxTextXat(TextIdentifier,
				YStart, YStart + SublineTHeight), 0, Zoom=ZoomX, PanX=0, PanY=0)
			# calculate starting X, depending on alignment
			if Text.ParaHorizAlignment == 'Left': XStartAbs = LayerOffsetX + PanX + MinXavail
			elif Text.ParaHorizAlignment == 'Right': XStartAbs = LayerOffsetX + PanX + MaxXavail - SublineX[SublineNo][-1]
			elif Text.ParaHorizAlignment == 'Centre': XStartAbs = LayerOffsetX + PanX + (0.5 * (MinXavail + MaxXavail - SublineX[SublineNo][-1]))
			else:  # bug trapping
				XStartAbs = LayerOffsetX + PanX + MinXavail
				print("Oops, unrecognised text alignment '%s' (problem code TE309). This is a bug, please report it" % Text.ParaHorizAlignment)
			# process Standout: adjust SublineX for any standing-out chars
			# TODO optimization: set a flag HasStandout elsewhere, and don't call ProcessStandout() if the flag is False
			# FIXME ProcessStandout() call commented out because it messes up SublineX when there's highlight
#			(SublineX, SublineY, StandoutAtSublineStart) = ProcessStandout(Sublines, SublineNo, SublineX, SublineY, SublineHeight, FmtCmds, ChunkLength,
#				StandoutAtSublineStart)
			Text.SublineXStart.append(XStartAbs)
			# make required font changes for each chunk, then draw the chunk
			CharsSoFar = 0
			for (ChunkNo, Chunk) in enumerate(SplitSubLine):  # for each chunk, get any fmt command and its arg
				(Command, Arg, Remainder) = FmtCmds[SublineNo][ChunkNo]
				if Command: # change parms accordingly
					(BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, HighlightNow, FontNow, ScaleNow, VertOffsetNow,
						ColourNow) = InterpretFormatCommand(Command, Arg, Text, BoldNow, UnderlinedNow, ItalicsNow,
						StandoutNow, HighlightNow, FontNow, ScaleNow, VertOffsetNow, ColourNow)
					FontInstanceNow = FontInstance(RequiredPointSize(ScaledPointSizeNoZoom * ScaleNow * 0.01,
				 		CanvZoomX=CanvZoomX, CanvZoomY=CanvZoomY, StandOutFraction=StandoutNow * StandoutIncrement,
					 	TextSizeRatio=TextSizeRatio), ItalicsNow, BoldNow, UnderlinedNow, FontNow)
					dc.SetFont(FontInstanceNow) # change font
					dc.SetTextForeground(Text.Colour if HighlightNow == BIUSNoEffectValue else ReverseColour(Text.Colour))
				VertOffset = VertOffsetNow
				# if text is highlighted, draw background box in original text colour
				if HighlightNow != BIUSNoEffectValue:
					dc.SetPen(wx.Pen( wx.Colour(ColourNow) ))
					dc.SetBrush(wx.Brush( wx.Colour(ColourNow), style=wx.SOLID ))
					xL = XStartAbs + SublineX[SublineNo][CharsSoFar]
					yT = max(El.TextYOffsetInElementInCU(TextIdentifier) * CanvZoomY + LayerOffsetY + PanY,
						 YStart + (1 - 0.01 * VertOffset) *
						 (SublineHeight - SublineY[SublineNo][CharsSoFar][0]) + LayerOffsetY + PanY)
					xR = XStartAbs + SublineX[SublineNo][CharsSoFar + len(Chunk)]
					yB = min(El.MaxTextY(TextIdentifier) * CanvZoomY + LayerOffsetY + PanY, yT + SublineTHeight)
					dc.DrawRectangle(x=xL, y=yT, width=xR - xL, height=yB - yT)
				if StandoutNow != BIUSNoEffectValue: # is the text currently standing out?
					# draw bkgnd-coloured box behind standing-out text, keeping it within El.TextYOffsetInElementInCU .. El.MaxTextY
					dc.SetPen(wx.Pen('white', 1, wx.TRANSPARENT))
					dc.SetBrush(wx.Brush(StandoutBoxColour, style=wx.SOLID))
					xL = XStartAbs + SublineX[SublineNo][CharsSoFar] - StandoutBoxXOverhang * CanvZoomX
					yT = max(El.TextYOffsetInElementInCU(TextIdentifier) * CanvZoomY + LayerOffsetY + PanY, YStart + (1 - 0.01 * VertOffset) *
						(SublineHeight - SublineY[SublineNo][CharsSoFar][0]) - StandoutBoxYOverhang * CanvZoomY + LayerOffsetY + PanY)
					xR = XStartAbs + SublineX[SublineNo][CharsSoFar + len(Chunk)] + StandoutBoxXOverhang * CanvZoomX
					BoxHeight = SublineTHeight + 2 * StandoutBoxYOverhang * CanvZoomY
					yB = min(El.MaxTextY(TextIdentifier) * CanvZoomY + LayerOffsetY + PanY, yT + BoxHeight)
					dc.DrawRectangle(x=xL, y=yT, width=xR - xL, height=yB - yT)
					# draw "standout" lines on two sides of the box
					dc.SetPen(wx.Pen(BrighterThan(StandoutBoxColour, 30), 2))
					dc.DrawLine(xL, yT, xL, yB + 1)
					dc.SetPen(wx.Pen(BrighterThan(StandoutBoxColour, 50), 2))
					dc.DrawLine(xL, yB + 1, xR, yB + 1)
				# draw the text in this chunk
				dc.DrawText(Remainder, XStartAbs + SublineX[SublineNo][CharsSoFar],
					LayerOffsetY + PanY + (YStart + (1 - 0.01 * VertOffset) * (SublineHeight - SublineY[SublineNo][CharsSoFar][0])))
				CharsSoFar += len(Chunk)
			YStart += (SublineHeight + SublineHeights[SublineNo][1]) * Text.LineSpacing  # set up for next subline

	def FindTextXYStart(TextIdentifier, YStartInPx, Zoom, SublineNo):
		# find and return absolute X and Y position to start the specified subline
		SublineHeight = SublineHeights[SublineNo][0]  # Y distance from subline top to baseline
		SublineTHeight = SublineHeight + SublineHeights[SublineNo][1]  # Y distance from subline top to descender
		# find starting Y coord for the specified subline
		YStartThisSubline = YStartInPx
		for ThisSublineIndex in range(1, SublineNo + 1):
			YStartThisSubline += (SublineHeight + SublineHeights[ThisSublineIndex][1]) * Text.LineSpacing
		# find leftmost available position for text within El, relative to layer, in pixels
		MinXavail, DummyY = utilities.ScreenCoords(El.MinTextXat(TextIdentifier,
			YStartThisSubline, YStartThisSubline + SublineTHeight), 0, Zoom=Zoom,
												   PanX=0, PanY=0)
		MaxXavail, DummyY = utilities.ScreenCoords(El.MaxTextXat(TextIdentifier,
			YStartThisSubline, YStartThisSubline + SublineTHeight), 0, Zoom=Zoom,
												   PanX=0, PanY=0)
		# calculate starting X, depending on alignment
		if Text.ParaHorizAlignment == 'Left':
			XStartAbs = LayerOffsetX + PanX + MinXavail
		elif Text.ParaHorizAlignment == 'Right':
			XStartAbs = LayerOffsetX + PanX + MaxXavail - Text.SublineX[SublineNo][-1]
		elif Text.ParaHorizAlignment == 'Centre':
			XStartAbs = LayerOffsetX + PanX + (0.5 * (MinXavail + MaxXavail - Text.SublineX[SublineNo][-1]))
		else:  # bug trapping
			XStartAbs = LayerOffsetX + PanX + MinXavail
			print(
				"Oops, unrecognised text alignment '%s' (problem code TE638). This is a bug, please report it" % Text.ParaHorizAlignment)
		return XStartAbs, YStartThisSubline

	def DrawTheCursor(TextIdentifier, CursorIndex, CursorColour, YStartInPx, Zoom):
		assert isinstance(CursorIndex, int)
		# find the target index of the character at which to draw the cursor, ignoring escape sequences and newlines
		TargetIndex = FindnthChar(RichStr=Text.Content, n=CursorIndex, IgnoreNewlines=False)
		# first, find which subline contains the cursor
		ThisSublineIndex = 0
		CumulativeCharCount = 0
		SublineCount = len(Text.Sublines) # total number of sublines in the text
		# step to next subline if the cursor is beyond the end of the current subline
		while (ThisSublineIndex < SublineCount) and (TargetIndex > CumulativeCharCount + len(Text.Sublines[ThisSublineIndex])):
			CumulativeCharCount += len(Text.Sublines[ThisSublineIndex]) + 1 # +1 to skip over the \n
			# step to next line if not yet reached target character, and if there's another line
			if (CumulativeCharCount <= TargetIndex) and (ThisSublineIndex < SublineCount - 1): ThisSublineIndex += 1
		# find the starting X, Y position of the subline
		XStartAbs, YStartAbs = FindTextXYStart(TextIdentifier, YStartInPx, Zoom, ThisSublineIndex)
		# find the absolute x-coordinate to draw the top left of the cursor
		# is the cursor beyond the end of the subline?
		if TargetIndex - CumulativeCharCount >= len(Text.Sublines[ThisSublineIndex]):
			CursorX = XStartAbs + Text.SublineX[ThisSublineIndex][-1]
		# is the cursor at the start of a subline? if so, offset CursorX slightly to the right, to avoid clash with box
		elif TargetIndex == CumulativeCharCount:
			CursorX = XStartAbs + Text.SublineX[ThisSublineIndex][0] + info.EditCursorXOffsetAtLeftEdge
		else: # cursor is in the middle of a subline
			CursorX = XStartAbs + Text.SublineX[ThisSublineIndex][TargetIndex - CumulativeCharCount]
		CursorY = LayerOffsetY + PanY + YStartAbs
		print('TE759 CursorY position: LayerOffsetY + PanY + YStartAbs:', LayerOffsetY, PanY, YStartAbs)
#		CursorY = LayerOffsetY + PanY + YStartAbs + SublineHeight - SublineY[SublineNo][CursorIndex - CumulativeCharCount][0]
		# draw the cursor
		dc.SetPen(wx.Pen(CursorColour, width=max(1, int(round(2 * Zoom)))))
		dc.DrawLine(CursorX, CursorY, CursorX, CursorY + SublineHeights[ThisSublineIndex][0] +
			SublineHeights[ThisSublineIndex][1])

	# main procedure for DrawTextInElement()

#	print('TE748 in DrawTextInElement with debug: ', debug)
	# if text is empty (or whitespace only) and we need to draw cursor, add dummy content so that we can calculate
	# correct position for cursor
	if DrawCursor and not Text.Content.strip():
		UsingDummyText = True
		OldText = Text.Content
		Text.Content = 'y'
	else: UsingDummyText = False
#	if Text.Content.strip(): # don't process if text content is empty or whitespace only
	# calculate text position, size and spacing
	(YaboveText, Text.Sublines, SublineHeights, Text.SublineX, SublineY, ScaledPointSizeNoZoom, YatTextBottom) =\
		CalculateTextSizeAndSpacing(El, Text, TextIdentifier, VertAlignment, CanvZoomX, CanvZoomY)
	# find the actual Y coordinate in pixels to start drawing the text. max(0, ) avoids text spilling over top of element
	DummyX, YStartInPx = utilities.ScreenCoords(0, El.MinTextY(TextIdentifier) + max(0, YaboveText),
		Zoom=CanvZoomY, PanX=PanX, PanY=PanY)
	# actually draw the text (unless we are using dummy content)
	if not UsingDummyText:
		RenderText(YStartInPx, Text.Sublines, SublineHeights, Text.SublineX,
			SublineY, ScaledPointSizeNoZoom, El.TextStandoutBackColour(TextIdentifier), ZoomX=CanvZoomX, ZoomY=CanvZoomY)
	if DrawCursor:
#		dc.SetPen(wx.Pen((255, 0, 0)))
#		dc.DrawRectangle(0, 0, 100, 20)
		print('TE726 drawing cursor at index: ', CursorIndex)
		DrawTheCursor(TextIdentifier, CursorIndex, CursorColour, YStartInPx, Zoom=CanvZoomY)
	# restore original text if we substituted dummy text
	if UsingDummyText: Text.Content = OldText

def UpdateStoredText(TextObj, Change, ChangePoint, NoOfChars, String):
	# change the text stored in TextObj. Change is 'Insertion', 'Deletion' or 'Replacement'.
	# ChangePoint is the index of the visible char where change occurs. NoOfChars is no of chars to remove if deleting or replacing.
	# String is chars to insert for Insertion or Replacement

	def DeleteFirstNChars(RichStr, n):  # remove the first n visible chars from RichStr, but leave the formatting commands in place
		# Returns (Cut-down RichStr, index of 1st char that isn't a formatting command)
		index = 0
		FirstNonFormatChar = 999999
		while (n > 0) and (index < len(RichStr)):
			while (RichStr[index] == TextEscStartChar):  # look at the remainder of RichStr: does it begin with a command?
				(c, v, RemainderStr) = ParseFormatCommand(RichStr[index + 1:])
				index = len(RichStr) - len(RemainderStr)
			else:  # no command was found; it's a visible character
				RichStr = RichStr[:index] + RichStr[index + 1:]  # delete the char from RichStr
				n -= 1
				FirstNonFormatChar = min(FirstNonFormatChar, index)
		return (RichStr, min(FirstNonFormatChar, len(RichStr)))

	# main procedure for UpdateStoredElementText()
	RichText = TextObj.Content
	if (Change == 'Insertion'):
		InsertionPoint = FindnthChar(RichText, ChangePoint)  # find the insertion point
		RichText = RichText[:InsertionPoint] + String + RichText[InsertionPoint:]
	elif (Change == 'Deletion'):
		DeletionPoint = FindnthChar(RichText, ChangePoint)  # find the point to start deleting from
		(Tail, n) = DeleteFirstNChars(RichText[DeletionPoint:], NoOfChars)
		RichText = RichText[:DeletionPoint] + Tail
	elif (Change == 'Replacement'):
		DeletionPoint = FindnthChar(RichText, ChangePoint)  # find the point to start deleting from
		(Tail, InsertionPoint) = DeleteFirstNChars(RichText[DeletionPoint:], NoOfChars)
		RichText = RichText[:DeletionPoint] + Tail[:InsertionPoint] + String + Tail[InsertionPoint:]
			# delete the removed chars from RichText, and insert any formatting commands, then the new chars, then the remainder of the string
	TextObj.Content = RichText  # update element text

def SetHighlightRange(Text, StartIndex, EndIndex):
	# set the content of TextObj to be highlighted from StartIndex to EndIndex (stripped text indices, ignoring
	# embedded format commands)
	assert isinstance(Text, str)
	assert isinstance(StartIndex, int)
	assert isinstance(EndIndex, int)
	# first, remove all existing highlight commands
	FinalText = StripOutEscapeSequences(RichText=Text, CommandType=['Highlight'])
	# set highlight only if requested range is longer than zero
	if EndIndex > StartIndex:
		StartIndexRich = FindnthChar(RichStr=FinalText, n=StartIndex, IgnoreNewlines=True)
		# insert 'start highlight' command
		FinalText = FinalText[:StartIndexRich] + TextEscStartChar + 'H2' + TextEscEndChar + FinalText[StartIndexRich:]
		EndIndexRich = FindnthChar(RichStr=FinalText, n=EndIndex, IgnoreNewlines=True)
		# insert 'end highlight' command
		FinalText = FinalText[:EndIndexRich] + TextEscStartChar + 'H1' + TextEscEndChar + FinalText[EndIndexRich:]
	return FinalText

def WrappedText(InText, Font, PixelsAvail, BreakAfter=' `~!)-=]}\\;>/?', MinLengthPercent=30, StripLeadingSpaces=True):
	# Splits InText (str) into lines to wrap within PixelsAvail space
	# Font is a wx.Font instance (can use FontInstance() )
	# BreakAfter is a string of chars at which line can be broken.
	# If BreakAfter is '', line will break only at max possible length
	# '.' and ',' are excluded from default BreakAfter because breaking at . or , is undesirable
	#	 unless they are followed by ' ', which will trigger the break anyway
	# Returns string with os.linesep (system dependent newline string) inserted at each line break, but not at the end
	# Each line (apart from the last one) shall not be shorter than MinLengthPercent% of PixelsAvail
	# If StripLeadingSpaces is True, any whitespace at the start of each line is deleted
	# Bugs: (1) messes up Unicode (if linebreak occurs in the middle of a multi-byte character)
	# (2) space deleted from start of line was taken into account in line length calc,
	# so line may appear too short
	# Return tuple is: (wrapped text (str), number of lines in wrapped text; returns 1 if wrapped text is empty (int))
	if len(InText) < 2: return (InText, 1) # zero or one characters returned unchanged
	MinLengthPercent = max(min(MinLengthPercent, 100), 10) # error trapping; limit it to 10-100%
	OutText = ''
	# First, find out the size of each character in the InText
	# make a buffer of arbitrary size to hold text in a single line. Possible gotcha if text is huge
	#	Buffer = wx.EmptyBitmap(2048, 256) # deprecated
	Buffer = wx.Bitmap(width=2048, height=256, depth=wx.BITMAP_SCREEN_DEPTH)
	dc = wx.MemoryDC(Buffer) # temporary DC used to work out actual text size
	dc.SetFont(Font)
	CumulativeSizes = dc.GetPartialTextExtents(InText)
	pos = 0 # pointer to which character in InText is being considered
	LineLength = 0 # cumulative length, in pixels, of current line
	BreakPoint = 0 # last possible break point in current line
	BreakLength = 0 # line length up to candidate break point
	LineStart = 0 # first character position (in InText) of current line
	LineCount = 1 # number of lines in wrapped text
	# count along InText, one character at a time, looking for end of line
	while (pos < len(InText)):
		# add this character to the candidate line
		LineLength = CumulativeSizes[pos] - CumulativeSizes[LineStart]
		# reached maximum line length?
		if (LineLength > PixelsAvail):
			# can line be broken at the last breakpoint found?
			if ((100 * BreakLength / PixelsAvail) < MinLengthPercent):
				# no, line would be too short: break at end instead
				BreakPoint = pos - 1
			# break line at the BreakPoint
			LineCount += 1
			pos = BreakPoint
			if StripLeadingSpaces:
				OutText += os.linesep + InText[LineStart:pos+1].lstrip()
			else:   OutText += os.linesep + InText[LineStart:pos+1]
			LineStart = pos + 1 # this will be start position of the next line
			BreakLength = 0
			LineLength = 0
		# record position of possible breakpoint
		if (InText[pos] in BreakAfter):
			BreakPoint = pos
			BreakLength = LineLength
		pos += 1
	# any residual characters left over? (do this test to avoid unnecessary blank line at end)
	if (LineStart+1 < len(InText)):
		# append them to the OutText
		LineCount += 1
		if StripLeadingSpaces:
			OutText += os.linesep + InText[LineStart:].lstrip()
		else:   OutText += os.linesep + InText[LineStart:]
	return (OutText[len(os.linesep):], LineCount) # the [x:] removes the unwanted newline at the start

def FindWordBreakInLeanText(LeanText, StartIndex, ToRight):
	# find and return index of next word start in LeanText (str, text with no command sequences).
	# StartIndex (int): index in LeanText to start from.
	# ToRight (bool): if True, search to right, else to left

	def AtTextLimit(Text, Index, ToRight):
		# return bool: whether Index at the end of Text (if ToRight) or at 0 (if not ToRight)
		assert isinstance(Text, str)
		assert isinstance(Index, int)
		assert isinstance(ToRight, bool)
		return (ToRight and (ThisIndex == len(Text))) or ((not ToRight) and (ThisIndex == 0))

	# start of FindWordBreakInLeanText
	xor = lambda a, b: bool(int(a) ^ int(b)) # make a boolean xor function
	assert isinstance(LeanText, str)
	assert isinstance(StartIndex, int)
	assert isinstance(ToRight, bool)
	WordBreakChars = WordBreakCharsToRight if ToRight else WordBreakCharsToLeft
	# check if we're already at the end of the text. If so, then if moving to the right, we're already at the word limit;
	# otherwise, skip one character to the left so we can start searching on an actual character
	ThisIndex = StartIndex
	if StartIndex >= len(LeanText):
		if ToRight: return len(LeanText)
		else: ThisIndex = StartIndex - 1
	else:
		if (not ToRight) and (StartIndex <= 0): return 0
	Increment = 1 if ToRight else -1 # distance to step per iteration
	WordBreakFound = False
	# do 3 searches: 1. step over word breaks (in case we started on a word break);
	# 	2. step over non-word breaks (to reach the limit of the current word);
	# 	3. step over word breaks (to reach next word)
	for SearchingForWordBreak, SecondWordBreak in [(True, False), (False, False), (True, True)]:
		# step over unwanted characters
		CheckingForUnwantedChars = not AtTextLimit(LeanText, ThisIndex, ToRight)
		while CheckingForUnwantedChars:
			if not xor(SearchingForWordBreak, LeanText[ThisIndex] in WordBreakChars):
				if SecondWordBreak: WordBreakFound = True # flag indicating we reached and found a new word break
				ThisIndex += Increment
			else: CheckingForUnwantedChars = False # stop stepping if a non-wordbreak character found
			CheckingForUnwantedChars &= not AtTextLimit(LeanText, ThisIndex, ToRight) # stop if text limit reached
	# special case: if moving to the left and we reached a word break,
	# move 1 char to the right (so that we are sitting at the end of the preceding word)
	if (not ToRight) and WordBreakFound: ThisIndex += 1
	return ThisIndex

def FindCharAtPosXInLine(TextObj, PosX, TargetLineIndex):
	# find the rich-text index of the character in subline number TargetLineIndex (int) in content of TextObj
	# that starts nearest to PosX (int; x coord)
	# return: rich-text character index (int)
	# TODO possible gotcha: may only work for left-aligned text
	assert isinstance(TextObj, TextObject)
	assert isinstance(PosX, int)
	assert isinstance(TargetLineIndex, int)
	assert 0 <= TargetLineIndex < len(TextObj.SublineX)
	# get x-coords of each character in target subline
	TargetSublineX = TextObj.SublineX[TargetLineIndex]
	# make a list indicating, for each character in this subline, whether it's to the right of PosX
	PosXToUse = PosX - TextObj.SublineXStart[TargetLineIndex] # take account of X gap to left of subline
	CharIsToRight = [ThisCharX >= PosXToUse for ThisCharX in TargetSublineX]
	# is the 0th character to the right of PosX? If so, pick the 0th character
	if CharIsToRight[0]: TargetCharIndexInSubline = 0
	# is the last char to the left of PosX? If so, pick the last character
	elif not CharIsToRight[-1]: TargetCharIndexInSubline = len(CharIsToRight) - 1
	else:
		# find X of the first char to the right of PosX, and X of the char to the left of this
		FirstCharToRightIndex = CharIsToRight.index(True)
		FirstCharToRightX = TargetSublineX[FirstCharToRightIndex]
		FirstCharToLeftX = TargetSublineX[FirstCharToRightIndex - 1]
		# find out which one is closer to PosX
		if (PosXToUse - FirstCharToLeftX) < (FirstCharToRightX - PosXToUse):
			TargetCharIndexInSubline = FirstCharToRightIndex - 1
		else: TargetCharIndexInSubline = FirstCharToRightIndex
	# find how many chars (in rich text) occur before the target subline
	CharsInPrecedingSublines = 0
	for ThisSubline in TextObj.SublineX[:TargetLineIndex]: CharsInPrecedingSublines += len(ThisSubline)
	return CharsInPrecedingSublines + TargetCharIndexInSubline

def XCoordOfChar(TextObj, CharIndexLean):
	# return the x coordinate of the character with index CharIndexLean (int) in lean text (ignoring command sequences)
	# if CharIndexLean is out of range, returns X coord of 0th or last char as appropriate
	# TODO: possible gotcha: may only work for left-aligned text
	# first, find the rich char index in the whole text
	CharIndexRich = FindnthChar(RichStr=TextObj.Content, n=CharIndexLean)
	# the short way: make a list of all char X-coords in the text
	AllCharX = utilities.Flatten(TextObj.SublineX)
	TargetX = AllCharX[CharIndexRich]
	# or, the long way: work through sublines and chunks (not tested yet)
#	# find which subline contains the index
#	SublineLengthsBefore = [0] # make a list of cumulative subline lengths
#	for ThisLine in TextObj.Sublines[1:]: SublineLengthsBefore.append(SublineLengthsBefore[-1] + len(ThisLine))
#	AfterTargetChar = [(SublineLengthsBefore[i] > CharIndexRich) for i in range(len(SublineLengthsBefore))]
#	if True in AfterTargetChar: # target char is in one of the sublines; find which subline
#		TargetSubline = AfterTargetChar.index(True) - 1
#		# find which chunk of the subline the char is in
#		ChunkLengthsBefore = [0]
#		for ThisChunk in TextObj.SublineX[TargetSubline]: ChunkLengthsBefore.append(ChunkLengthsBefore[-1] + len(ThisChunk))
#		ChunkAfterTargetChar = [(ChunkLengthsBefore[i] > (CharIndexRich - SublineLengthsBefore[TargetSubline]))
#			for i in range(len(ChunkLengthsBefore))]
#		if True in ChunkAfterTargetChar: # target char is in one of the chunks
#			TargetChunk = ChunkAfterTargetChar.index(True) - 1
#			TargetCharIndexInChunk = CharIndexRich - SublineLengthsBefore[TargetSubline] - ChunkLengthsBefore[TargetChunk]
#			TargetX = TextObj.SublineX[TargetSubline][TargetChunk][TargetCharIndexInChunk]
#		else: # target char is at the beginning of the 0th chunk
#			TargetCharIndexInChunk = CharIndexRich - SublineLengthsBefore[TargetSubline]
#			TargetX = TextObj.SublineX[TargetSubline][0][0]
#	else: # target char is at the beginning of the 0th subline, 0th chunk
#		TargetX = TextObj.SublineX[0][0][0]
	return TargetX

def SublineIndexContainingChar(TextObj, CharIndexLean):
	# return the number of the subline containing the char at CharIndexLean (int) in lean text

#	def Sum(MyList): # return sum of integer values in MyList (iterable)
#		Total = 0
#		for i in MyList: Total += i
#		return Total

	CharIndexRich = FindnthChar(RichStr=TextObj.Content, n=CharIndexLean)
	# count along sublines until target index is reached
	CharsSoFar = 0
	ThisSublineIndex = 0
	print('TE995 SublineX: ', TextObj.SublineX)
	while CharsSoFar < CharIndexRich and ThisSublineIndex < len(TextObj.SublineX):
#		CharsSoFar += Sum([len(ThisChunk) for ThisChunk in TextObj.SublineX[ThisSublineIndex]])
		CharsSoFar += len(TextObj.SublineX[ThisSublineIndex])
		if CharsSoFar < CharIndexRich: ThisSublineIndex += 1
	return min(ThisSublineIndex, len(TextObj.SublineX) - 1)

def FindnthCharLean(TextObj, CharIndexRich):
	# find the corresponding lean char index in TextObj's content corresponding to rich text index CharIndexRich (int)
	assert isinstance(TextObj, TextObject)
	assert isinstance(CharIndexRich, int)
	assert 0 <= CharIndexRich <= len(TextObj.Content)
	return len(StripOutEscapeSequences(TextObj.Content[:CharIndexRich]))

def HowManyLinesInText(TextObj):
	# return the number of sublines (i.e. lines as displayed) in TextObj's content
	assert isinstance(TextObj, TextObject)
	return len(TextObj.SublineX) - 1

def NearestCharIndexLeanAtXY(TextObj, TargetX, TargetY):
	# return lean char index (int) closest to coordinate TargetX, TargetY ( 2 x int)
	assert isinstance(TextObj, TextObject)
	assert isinstance(TargetX, (int, float))
	assert isinstance(TargetY, (int, float))
	# find the nearest subline: make list of Y-distance of TargetY from each subline's Y midpoint
	DistanceYFromSublines = [abs(int(TargetY - ThisSublineYMid)) for ThisSublineYMid in TextObj.SublineYMid]
	TargetSubline = DistanceYFromSublines.index(min(DistanceYFromSublines))
	# find the subline's nearest character in the X direction
	CharIndexRich = FindCharAtPosXInLine(TextObj=TextObj, PosX=TargetX, TargetLineIndex=TargetSubline)
	return FindnthCharLean(TextObj=TextObj, CharIndexRich=CharIndexRich)