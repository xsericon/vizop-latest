#!/usr/bin/python
# -*- coding: utf-8 -*-
# Module text: part of Vizop, (c) 2018 Peter Clarke

from __future__ import division  # makes a/b yield exact, not truncated, result
import wx, os

# vizop modules
import utilities

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
DefaultTextLineSpacing = 1.2
MaxTextLineSpacing = 10
DefaultBIUSValue = 1 # default value of bold, italic, underlined, standout attrib of TextObjects
BIUSNoEffectValue = 1 # value of bold/(etc) attrib meaning "no effect", ie not bold/(etc)
StandoutIncrement = 0.5  # fraction by which point size of text is increased for normal degree of Standout
StandoutBoxXOverhang = 5  # amount by which L and R edges of box drawn behind standing out text exceeds size of text, in canvas coords
StandoutBoxYOverhang = 5

# embeddable text formatting commands
TextFormatCommandHash = {'B': 'Bold', 'U': 'Underlined', 'I': 'Italics', 'S': 'Standout', 'F': 'Font', 'f': 'Font-Default', 'Z': 'Scale', 'z': 'No-Scale',
	'V': 'Vert-Offset', 'v': 'No-Vert-Offset', 'X': 'All-Default', 'C': 'Colour', 'c': 'Colour-Default', 'T': 'Tag'}
TakesStringArg = 'FT' # string arg expected after these commands
TakesIntArg = 'BUISZV' # integer arg expected after these commands
TakesHexArg = 'C' # hex string expected after this command
# make reverse of above hash table
TextFormatCommandRevHash = {}
for (p, q) in TextFormatCommandHash.items(): TextFormatCommandRevHash[q] = p

def BrighterThan(OldCol, PercentBrighter=50):  # return colour that is a notional % brighter than OldCol
	return tuple([min(255, d + PercentBrighter) for d in OldCol[:3]]) + OldCol[3:]  # don't increment alpha parm, if any

class TextObject(object):
	# text contained within an element, along with its formatting attributes

	def __init__(self, Content='', **Args):
		object.__init__(self)
		assert isinstance(Content, str)
		self.Content = Content # text to display (str)
			# Can contain <CR> (chr(13)) and escape sequences consisting of <elements.text.TextEscStartChar> followed by:
			# B: bold*; U: underlined*; I: italics*; S: standout*; X: revert all formatting to default
			# (commands marked * take integer arg: 0 = default, 1 = no effect, 2 = minimum effect (eg single underline), 255 = maximum effect)
			# C rrggbbaa: change colour as specified (8 hex digits); c: revert to default colour
			# F fontname <TextEscEndChar>: change font; f: revert to default font
			# Z n <TextEscEndChar>: change point size to n% of default (n unsigned integer); z: revert to default point size
			# V n <TextEscEndChar>: offset characters by n% of character height (n +ve or -ve integer); v: revert to no offset
			# changes to the syntax need to be reflected in ParseFormatCommand() and InterpretFormatCommand()
		self.Font = DefaultElementTextFont
		self.PointSize = DefaultTextPointSize # basic (user-specified) size before adjusting for zoom, standout etc.
		self.Bold = self.Underlined = self.Italics = self.Standout = DefaultBIUSValue
		self.Colour = DefaultTextColour
		self.ParaHorizAlignment = DefaultTextHorizAlignment
		self.ParaVertAlignment = DefaultTextVertAlignment
		self.LineSpacing = DefaultTextLineSpacing
		self.ParentSizeBasis = {} # dict: {object size parm: value} used for calculating required text point size based on an object's actual size.
		self.TextSize = None
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
		if CommandChar in (TakesStringArg + TakesIntArg + TakesHexArg):  # try to get arg. If TextEscEndChar missing, read to end of line
			if not (TextEscEndChar in CmdString): CmdString += TextEscEndChar  # bug trapping
			SplitAtTerminator = CmdString.split(TextEscEndChar, 1)
			ArgString = SplitAtTerminator[0]
			CmdString = SplitAtTerminator[1]  # balance of input string after terminator
			if CommandChar in IntegerExpectedAfter:  # convert to integer if necessary. Can't use int(), may raise ValueError
				if ArgString[0] == '-':  # trap negative value
					Factor = -1
					ArgString = ArgString[1:]  # chop off the negative sign
				else: Factor = 1
				ArgInteger = utilities.str2int(ArgString, 24) * Factor  # the 24 will be returned if no meaningful integer can be found
				return (Command, ArgInteger, CmdString)
			else: return (Command, ArgString, CmdString)
		else: return (Command, None, CmdString)  # command found; no arg expected
	else: return ('', None, CmdString)  # command not found

def StripOutEscapeSequences(RichText, CommandType=[]):  # Returns RichText with formatting command sequences removed
	# If CommandType is [], all commands are removed, otherwise removes only commands listed (uses long form, eg 'Font')
	index = 0  # read along RichText, looking for command sequences
	while (index < len(RichText)):
		if RichText[index] == TextEscStartChar:  # command found; chop it out of RichText
			(Command, v, Tail) = ParseFormatCommand(RichText[index + 1:])
			if (CommandType == []) or (Command in CommandType):
				RichText = RichText[:index] + Tail  # remove this command
			else: index += len(RichText) - len(Tail)  # skip over this command
		else: index += 1  # command not found; step on to next char
	return RichText

def FindnthChar(RichStr, n):  # find the index of the n'th visible character in RichStr (counting from zero), skipping over escape sequences
	OrigRichStrLength = len(RichStr)
	while (n >= 0) and (RichStr != ''):  # chop chars and command sequences off RichStr one by one
		while ((RichStr + 'X')[0] == TextEscStartChar):  # look for commands. The +'X' is to avoid crash when end of RichStr reached
			(c, v, RichStr) = ParseFormatCommand(RichStr[1:])  # found a command sequence: chop off the whole sequence
		if (n != 0): RichStr = RichStr[1:]  # chop off a single non-command char (use the 'if' to avoid problems if RichStr is already empty)
		n -= 1
	return OrigRichStrLength - len(RichStr)

def FindFormatCommandBeforeNthChar(RichStr, n):  # find index of the first format command before Nth visible char in RichStr
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
	# FmtParm = 'Scale', 'Vert-Offset', 'Bold', 'Underlined', 'Italics', 'Standout': return parm value
	# Takes account of default format, if no relevant format commands found

	def DefaultParmState(TextObj, FmtParm):  # returns default state of FmtParm
		if FmtParm == 'Scale': return DefaultTextVertFactor
		if FmtParm == 'Vert-Offset': return 0
		if FmtParm in ['Bold', 'Italics', 'Underlined', 'Standout']: return 1
		return TextObj.__dict__[CmdHash[FmtParm]['Parm']]

	CmdHash = {'Font': {'Set': 'Font', 'Unset': 'Font-Default', 'ArgExpected': True, 'Parm': 'Font'}, \
		'Bold': {'Set': 'Bold', 'Unset': 'Bold', 'ArgExpected': True, 'Parm': 'Bold'}, \
		'Underlined': {'Set': 'Underlined', 'Unset': 'Underlined', 'ArgExpected': True, 'Parm': 'Underlined'}, \
		'Italics': {'Set': 'Italics', 'Unset': 'Italics', 'ArgExpected': True, 'Parm': 'Italics'}, \
		'Standout': {'Set': 'Standout', 'Unset': 'Standout', 'ArgExpected': True, 'Parm': 'Standout'}, \
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

def CalculateTextSizeAndSpacing(El, Text, TextIdentifier, VertAlignment, CanvZoomX, CanvZoomY):
	# calculate all required values for drawing text, including dividing the text into lines and chunks
	# returned ScaledPointSizeNoZoom does not take account of zoom

	def FindYaboveText(El, TextIdentifier, TextLines, FirstYaboveText, LineSpacing, Iterations, VertAlignment, Yhere,
			Xsofar, IsFmtCmd):
		# recursively find optimal Y position for text
		# work through each line of text, split into sublines
		BreakAfter = ' `~)-=]}\\;>/'  # chars to split line after
		MinLineFill = 0.55  # fraction of total X available that must be used up when considering where to split sublines (ie no line will be shorter than this)
		MaxTopBottomDiffCentreAligned = 1.1  # target ratio of bottomY:topY when centre aligned
		MinTopBottomDiffCentreAligned = 0.91  # reciprocal of above
		MaxTopBottomDiffBottomAligned = 0.1  # target ratio of bottomY:topY when bottom aligned
		MaxIterations = 10  # to avoid infinite loop
		Sublines = []  # rich text content of each subline
		SublineHeights = []  # list of (height above baseline, descent below baseline) for each subline
		SublineX = [ [0] ]  # list of [per subline: [x offset from start of line, at left edge of each character]]
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
				SublineX[-1] = [0, 1]
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
				SublineX.append([0])
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
					if (XafterNextChar <= Xavail) or not ThisSubline:  # 'or not' ensures >= 1 char per subline, to avoid infinite loop
						ThisSubline += Line[IndexInLine]
						SublineX[-1].append(XafterNextChar)
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
							SublineX[-1] = SublineX[-1][:SplittableIndices[-1] + 2]  # 2 because SublineX has extra 0 at the start
							SublineY[-1] = SublineY[-1][:SplittableIndices[-1] + 1]
					if EndOfSubline or (IndexInLine == len(Line)):
						# reached end of subline, or entire line; close out the subline
						EndOfSubline = False
						# remove any leading spaces from subline (but leave one space if that's the only char in subline)
						if ThisSubline:
							while (len(ThisSubline) > 1) and (ThisSubline[0] == ' '):
								ThisSubline = ThisSubline[1:]
								# chop off 2nd item (the space) in SublineX[-1], and reduce other values by the x-size of the space removed
								SublineX[-1][1:] = [SublineX[-1][i + 2] - SublineX[-1][1] for i in range(len(SublineX[-1]) - 2)]
								SublineY[-1] = SublineY[-1][1:]
							# remove any trailing spaces but leave at least one char in subline
							while (len(ThisSubline) > 1) and (ThisSubline[-1] == ' '):
								ThisSubline = ThisSubline[:-1]
								SublineX[-1] = SublineX[-1][:-1]
								SublineY[-1] = SublineY[-1][:-1]
						Sublines.append(ThisSubline)
						SublineHeights.append((MaxHeightInSubline, MaxYinSubline - MaxHeightInSubline))
						YatSublineTop += MaxYinSubline * Text.LineSpacing
						ThisSubline = ''
						XatStartofSubline = Xsofar[LineNo][IndexInLine - 1]
						ThisSublineIndexStart = IndexInLine
						LastExtraLineSpace = MaxYinSubline * (Text.LineSpacing - 1)
						MaxYinSubline = 0
						SublineX.append([0])
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
				(FinalYaboveText, Sublines, SublineHeights, SublineX, SublineY, YatTextBottom) = FindYaboveText(El, TextIdentifier, TextLines,
					max(0, FirstYaboveText - (0.5 * (FirstYaboveText - (El.MaxTextY(TextIdentifier) * CanvZoomY) + YatTextBottom))),
					LineSpacing, Iterations + 1, VertAlignment, Yhere, Xsofar, IsFmtCmd)
		elif VertAlignment == 'Bottom':
			# check ratio of top to bottom gap is in acceptable range
			Ratio = ((El.MaxTextY(TextIdentifier) * CanvZoomY) - YatTextBottom) / (max(0.01, FirstYaboveText))  # max() is to avoid div/0
			if ((Ratio > MaxTopBottomDiffBottomAligned) or (Ratio < 0)) and (Iterations < MaxIterations):
				# ratio out of range: try again, increasing top space by 90% of bottom space
				# the max(0, ) is to avoid the text spilling off the top of the element
				(FinalYaboveText, Sublines, SublineHeights, SublineX, SublineY, YatTextBottom) = FindYaboveText(El, TextIdentifier, TextLines,
					max(0, FirstYaboveText + (0.9 * ((El.MaxTextY(TextIdentifier) * CanvZoomY) - YatTextBottom))),
					LineSpacing, Iterations + 1, VertAlignment, Yhere, Xsofar, IsFmtCmd)
		return (FinalYaboveText, Sublines, SublineHeights, SublineX, SublineY, YatTextBottom)

	def InterpretFormatCommand(Command, Arg, TextInstance, Bold, Underlined, Italics, Standout, Font, Scale, VertOffset, Colour):
		# returns values of all args based on input Command and Arg
		if Command == 'Bold': Bold = Arg
		elif Command == 'Underlined': Underlined = Arg
		elif Command == 'Italics': Italics = Arg
		elif Command == 'Standout': Standout = Arg
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
			Font = TextInstance.Font
			Colour = TextInstance.Colour
		elif Command == 'Colour':
			Colour = utilities.str2HexTuple(Arg)
		elif Command == 'Colour-Default': Colour = TextInstance.Colour
		else: print("Oops, unrecognised formatting command %s (problem code TE378).  This is a bug, please report it" % Command)
		return (Bold, Underlined, Italics, Standout, Font, Scale, VertOffset, Colour)

	# Main procedure for CalculateTextSizeAndSpacing()
	# First, set initial format settings; intentionally NOT allowing for standout, as standing-out text doesn't get any extra space
	# Find target point size, allowing for change of Element size
#	Text = El.Text # fetch the text object from supplied element; now using Text supplied as arg, to allow us to use
#	# a substitute text instead
	ScaledPointSizeNoZoom = Text.RequiredTextPointSizeInCU(TextIdentifier, Text.PointSize, Text.ParentSizeBasis)
	ItalicsNow = Text.Italics
	BoldNow = Text.Bold
	UnderlinedNow = Text.Underlined
	StandoutNow = Text.Standout
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
	TextLines = Text.Content.splitlines()
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
				(BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, FontNow, ScaleNow, VertOffsetNow, ColourNow) = InterpretFormatCommand(Command, Arg,
					Text, BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, FontNow, ScaleNow, VertOffsetNow, ColourNow)  # change parms accordingly
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
			(a, b, ChunkAfterCmd) = ParseFormatCommand(Chunk, CheckForEscChar=True)  # split chunk into command and text
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
	(YaboveText, Sublines, SublineHeights, SublineX, SublineY, YatTextBottom) = FindYaboveText(
		El, TextIdentifier, TextLines, MaxYaboveText, Text.LineSpacing, 0, VertAlignment, Yhere, Xsofar, IsFmtCmd)
	return YaboveText, Sublines, SublineHeights, SublineX, SublineY, ScaledPointSizeNoZoom, YatTextBottom

def TextSize(El, Text, TextIdentifier, CanvZoomX, CanvZoomY, VertAlignment='Top'):
	# returns (Xsize, Ystart, Yend) for text in El
	(YaboveText, Sublines, SublineHeights, SublineX, SublineY, ScaledPointSizeNoZoom, YatTextBottom) =\
		CalculateTextSizeAndSpacing(El, Text, TextIdentifier, VertAlignment, CanvZoomX, CanvZoomY)
	# get Xsize from the X-coord of the end of the longest subline
	Xsize = max([ThisSubline[-1] for ThisSubline in SublineX])
	return (Xsize, YaboveText, YatTextBottom)

def DrawTextInElement(El, dc, Text, TextIdentifier, LayerOffsetX=0, LayerOffsetY=0, CanvZoomX=1.0, CanvZoomY=1.0,
  	PanX=0, PanY=0, TextSizeRatio=1.0, VertAlignment='Centre'):
	# draw Text (text object instance) inside element El, correctly positioned in available y-space.
	# TextIdentifier (int): which text object in El we are drawing; El needs this to work out which Y values to supply
	# LayerOffsetX/Y is the pixel offset to apply for the display device (compensating for offset of device drawing box within device)
	# PanX, PanY (int/float): pixel offset for the element within the display device due to panning
	# TextSizeRatio is enlargement factor for Standout; simply increases the font size
	# VertAlignment can be 'Centre', 'Top' or 'Bottom'
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

		def InitializeFont():  # set all parms to "default" for this text
			dc.SetTextForeground(Text.Colour)
			dc.SetBackgroundMode(wx.TRANSPARENT)  # no text background colour; Rappin p380
			ItalicsNow = Text.Italics
			BoldNow = Text.Bold
			UnderlinedNow = Text.Underlined
			StandoutNow = Text.Standout
			FontNow = Text.Font
			ScaleNow = DefaultTextVertFactor
			VertOffsetNow = 0
			ColourNow = Text.Colour
			return (BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, FontNow, ScaleNow, VertOffsetNow, ColourNow)

		# start of RenderText(): initialize font
		(BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, FontNow, ScaleNow, VertOffsetNow, ColourNow) = InitializeFont()
		FontInstanceNow = FontInstance(RequiredPointSize(ScaledPointSizeNoZoom, CanvZoomX=ZoomX, CanvZoomY=ZoomY, TextSizeRatio=TextSizeRatio), Text.Italics, \
									   Text.Bold, Text.Underlined, Text.Font)
		dc.SetFont(FontInstanceNow)
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
			(SublineX, SublineY, StandoutAtSublineStart) = ProcessStandout(Sublines, SublineNo, SublineX, SublineY, SublineHeight, FmtCmds, ChunkLength,
				StandoutAtSublineStart)
			# make required font changes for each chunk, then draw the chunk
			CharsSoFar = 0
			for (ChunkNo, Chunk) in enumerate(SplitSubLine):  # for each chunk, get any fmt command and its arg
				(Command, Arg, Remainder) = FmtCmds[SublineNo][ChunkNo]
				if Command:  # change parms accordingly
					(BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, FontNow, ScaleNow, VertOffsetNow, ColourNow) = InterpretFormatCommand(Command, Arg, \
						Text, BoldNow, UnderlinedNow, ItalicsNow, StandoutNow, FontNow, ScaleNow, VertOffsetNow, ColourNow)
					FontInstanceNow = FontInstance(RequiredPointSize(ScaledPointSizeNoZoom * ScaleNow * 0.01,
				 		CanvZoomX=CanvZoomX, CanvZoomY=CanvZoomY, StandOutFraction=StandoutNow * StandoutIncrement,
					 	TextSizeRatio=TextSizeRatio), ItalicsNow, BoldNow, UnderlinedNow, FontNow)
					dc.SetFont(FontInstanceNow)  # change font
					dc.SetTextForeground(ColourNow)
				VertOffset = VertOffsetNow
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

	# main procedure for DrawTextInElement()
	if Text.Content.strip(): # don't process if text content is empty or whitespace only
		(YaboveText, Sublines, SublineHeights, SublineX, SublineY, ScaledPointSizeNoZoom, YatTextBottom) =\
			CalculateTextSizeAndSpacing(El, Text, TextIdentifier, VertAlignment, CanvZoomX, CanvZoomY)
		# find the actual Y coordinate in pixels to start drawing the text. max(0, ) avoids text spilling over top of element
		DummyX, YStartInPx = utilities.ScreenCoords(0, El.MinTextY(TextIdentifier) + max(0, YaboveText),
			Zoom=CanvZoomY, PanX=PanX, PanY=PanY)
		# actually draw the text
		RenderText(YStartInPx, Sublines, SublineHeights, SublineX,
	   		SublineY, ScaledPointSizeNoZoom, El.TextStandoutBackColour(TextIdentifier), ZoomX=CanvZoomX, ZoomY=CanvZoomY)

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
