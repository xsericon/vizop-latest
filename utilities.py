# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright Peter Clarke, 2017

"""vizop utilities module
This module contains utility functions (not Vizop-specific) that are used throughout Vizop.
"""

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import re
from math import ceil, log10

MinDivisor = 1e-12

def Pad(InStr, FieldWidth=4, PadChar=' '):
	# return InStr (str) padded to length of FieldWidth by adding PadChar's to the left
	# If PadChar contains more than one character, it will be used as a repeating pattern
	return ((int(FieldWidth) * str(PadChar)) + str(InStr))[-max(len(str(InStr)), abs(int(FieldWidth)))]

def PadList(InList, FieldWidth=4, PadValue=None, Truncate=False):
	# return InList (list) padded to length of FieldWidth (int≥0) by adding PadValue's to the right
	# If Truncate (bool) is True and InList is longer than FieldWidth, list will be truncated to Fieldwidth
	# If PadValue is mutable, multiple references to the same object may be placed in the list
	assert isinstance(InList, list)
	assert isinstance(FieldWidth, int)
	assert 0 >= FieldWidth
	assert isinstance(Truncate, bool)
	if Truncate and len(InList) > FieldWidth: return InList[:FieldWidth]
	else: return (InList + ([PadValue] * FieldWidth))[:FieldWidth]

def CanvasCoords(ScreenX, ScreenY, Zoom, PanX, PanY): # return (CanvasX, CanvasY) corresponding to input parms
	# Zoom is in %. PanX, PanY are in screen coords.
	return ( int(round((ScreenX - PanX) * 100 / max(1, Zoom))), int(round((ScreenY - PanY) * 100 / max(1, Zoom))) )

def CanvasCoordsViewport(Viewport, ScreenX, ScreenY): # return (CanvasX, CanvasY) corresponding to input parms for Viewport,
	# taking account of zoom, pan and scale factor specific to DisplDevice
	return ( int(round((ScreenX - Viewport.PanX - Viewport.OffsetX) / (Viewport.Zoom * Viewport.DisplDevice.ScaleX))),
		int(round((ScreenY - Viewport.PanY - Viewport.OffsetY) / (Viewport.Zoom * Viewport.DisplDevice.ScaleY))) )

def ScreenCoords(CanvasX, CanvasY, Zoom, PanX, PanY): # return (ScreenX, ScreenY) (tuple of 2 int's) corresponding to input parms
	# Zoom (float) is an absolute ratio (1.0 = not zoomed). PanX, PanY (float or int) are in screen coords.
	return ( int(round(PanX + (CanvasX * Zoom))), int(round(PanY + (CanvasY * Zoom))) )

def str2int(s, MeaninglessValue=0):
	# extract a meaningful integer from s (str). Returns the integer representing the first group of digits in the string
	# e.g. '   abc-147xyz23 ' returns -147
	# if no integer can be extracted, returns MeaninglessValue
	inps = s.strip()
	FirstDigitFound = False
	Sign = 1 # positive or negative indicator
	i = -1
	# find the first digit
	while (not FirstDigitFound) and (i < len(inps)-1):
		i += 1
		FirstDigitFound = inps[i].isdigit()
		# check for leading '-'
		if (inps[i] == '-'): Sign = -1
	if not FirstDigitFound: return MeaninglessValue # string contains no digits
	firstdigit = i # now we know the index of the first digit in the string
	NonDigitFound = False
	while (not NonDigitFound) and (i < len(inps)-1):
		i += 1
		NonDigitFound = not inps[i].isdigit()
	if NonDigitFound: lastdigit = i-1
	else: lastdigit = i # now we know the index of the last digit in this group
	return Sign * int(inps[firstdigit : lastdigit+1])

def str2real(s, meaninglessvalue=0.0):
	# extract the first available real number from s (str). (This procedure from SILability 1.21)
	# if no real number can be extracted, returns meaninglessvalue
	InStr = StripSpaces(s) + 'garbage' # stuff tacked on the end, to avoid hitting indexing problems when string is empty
	# strip all chars from start of string until digit, . or - found
	while not ((InStr + '0')[0] in '0123456789-.'): InStr = InStr[1:] # the +'0' is to avoid crash if string contains no required chars
	if (InStr == ''): return meaninglessvalue # no number characters found, goodbye
	# extract the mantissa part of the real number: search until a nondigit or second '.' found
	ResultStr = ''
	DecimalsFound = 0
	if (InStr[0] == '-'): # extract leading negative sign
		ResultStr = '-'
		InStr = InStr[1:]
	ValidCharFound = True
	DigitsFound = False
	while (DecimalsFound < 2) and ValidCharFound: # extract digits and first decimal
		if (InStr[0] == '.'):
			DecimalsFound += 1
			if (DecimalsFound == 1): # first decimal, chop from InStr and put it in ResultStr
				ResultStr += '.'
				InStr = InStr[1:]
		elif (InStr[0] in '0123456789'): # extract digit
			ResultStr += InStr[0]
			InStr = InStr[1:]
			DigitsFound = True
		else: ValidCharFound = False
	if not DigitsFound: return meaninglessvalue # we found only - or . or both, but no digits
	# if first character after mantissa is 'E', extract it followed by (optional negative sign and) exponent
	if (InStr[0] in 'Ee'):
		ResultStr += InStr[0]
		InStr = InStr[1:]
		if (InStr[0] == '-'): # extract leading negative sign
			ResultStr += '-'
			InStr = InStr[1:]
		ResultStr += str(str2int(InStr, 0)) # get the remaining digits of the exponent, or zero if none found
	# finally, check whether last character is a nondigit (could be -.Ee) and, if so, append 0 to avoid problems with float()
	if not (ResultStr[-1] in '0123456789'): ResultStr += '0'
	return float(ResultStr)

def str2HexTuple(InStr): # parses InStr as series of 2-digit hex values and returns values as tuple of integers
	# eg str2HexTuple('01AB3F') returns (0x01, 0xAB, 0x3F). Not case sensitive
	OutVals = []
	for i in range(0, len(InStr), 2): # i takes values 0, 2, 4..., len(InStr)-1
		try: ThisVal = int(InStr[i:i+2], 16) # extract hex value (base 16)
		except ValueError: ThisVal = 0 # error trapping if value not readable
		OutVals.append(ThisVal)
	return tuple(OutVals)

def HexTuple2str(HexTuple): # opposite of str2HexTuple. Any hex digits a..f will be returned as lowercase
	OutStr = ''
	for InVal in HexTuple:
		try: OutStr += ('0' + hex(min(255, max(0, int(InVal))))[2:])[-2:]
			# the [2:] deletes the '0x' prefix. The '0' and [-2:] prepend extra zero if needed
		except ValueError: OutStr += '00' # traps any values in HexTuple not convertible to integers
	return OutStr

ChopFromEnd = lambda InStr,ChopHowMany : (InStr + ' ')[:(-ChopHowMany)-1] # function to remove ChopHowMany chars from end of InStr
	# Simply using InStr[:-ChopHowMany] fails when ChopHowMany = 0

def StripSpaces(instr, CharsToStrip=' '):
	""" Return instr with all spaces (or other characters in CharsToStrip) removed """
	res = ''
	for i in instr:
		if not (i in CharsToStrip): res += i
	return res

_bool_regexp = re.compile(r'''
						  ^\s* #matches whitespace at beginning of string
						  (?:(?P<true>true|yes|[yt]|1)| #matches true values
						  (?P<false>false|no|[fn]|0)) #matches false values
						  \s*$ #matches whitespace at end of string
						  ''', flags=re.IGNORECASE | re.VERBOSE)

def str_to_bool(val):
	"""
	Converts str(val) into a boolean. Raises ValueError if str(val) is not a
	valid string representation of a boolean.

	Valid strings are (case insensitive):

		True  -> 1, true, t, y, yes
		False -> 0, false, f, n, no

	Leading and trailing whitespace will be ignored.
	"""
	# define a regular expression for matching string representations of boolean values
	# this will match any upper or lower case version of y, yes, t, true, 1, n, no,
	# f, false or 0. Leading or trailing whitespace will be ignored.
	match = _bool_regexp.match(str(val))
	if match is not None:
		if match.groupdict()['true'] is None:
			return False
		else:
			return True
	else:
		raise ValueError("Invalid string \'%s\' for conversion to boolean type." % val)

def MergeDicts(*dict_args):
	'''
	Given any number of dicts, shallow copy and merge into a new dict. Return the new dict.
	If any key appears in >1 dict, it will be assigned the value in the rightmost dict.
	'''
	result = {}
	for dictionary in dict_args:
		result.update(dictionary)
	return result

def StringOfIntsToList(Instr, SplitChar=','):
	# return a list of ints converted from string. eg '1,2,  3' --> [1,2,3]
	# Not currently used. Maybe eval() might be better way?
	assert isinstance(Instr, str), "StringOfIntsToList got a non-string Instr"
	assert isinstance(SplitChar, str), "StringOfIntsToList got a non-string SplitChar"
	return [int(x) for x in Instr.split(SplitChar)]

def NextID(ObjList):
	# return the next available ID for a new object getting added to ObjList
	# ObjList: list of any kind of object that has attribute ID (any type convertible to int)
	assert hasattr(ObjList, '__iter__'), "Object list sent to NextID isn't iterable"
	return max([int(e.ID) for e in ObjList] + [0]) + 1 # generate unique ID

def ObjectWithID(Objects, TargetID): # return object instance among Objects (list/set of object instances)
	# with specified ID (str). Returns None if ID not found
	# check Objects is iterable (list, set etc)
	assert hasattr(Objects, '__iter__'), "Object list sent to ObjectWithID isn't iterable"
	for p in Objects:
		# check Objects have ID attributes
		assert hasattr(p, 'ID'), "Object item doesn't have ID attribute"
	ObjIDs = [p.ID for p in Objects]
	if TargetID in ObjIDs:
		return Objects[ObjIDs.index(TargetID.strip())]
	else:
		print("ObjectWithID: warning, requested object ID '%s' not found" % str(TargetID))
		return None

def IsEffectivelyZero(TestVal=0.0):
	# returns True if TestVal (int or float) is close to zero, ie unsuitable as a dividend
	assert isinstance(TestVal, (int, float))
	return (abs(TestVal) < MinDivisor)

def EffectivelyEqual(Val1, Val2, Precision=0.0001):
	# returns True if Val1 and Val2 (int or float) are equal to within a factor of Precision (float).
	# if Val1 and Val2 are both effectively zero, returns True.
	# Otherwise, if either Val1 or Val2 are effectively zero, returns False.
	assert isinstance(Val1, (int, float))
	assert isinstance(Val2, (int, float))
	assert isinstance(Precision, float)
	if IsEffectivelyZero(Val1):
		if IsEffectivelyZero(Val2): return True
		else: return False
	else:
		if IsEffectivelyZero(Val2): return False
		else:
			return bool( abs((Val1 - Val2)/Val2) < abs(Precision) )

def RoundToSigFigs(InputValue, SigFigs=3):
	# returns ( InputValue (int or float) rounded to SigFigs (int, >0) significant figures,
	#   Number of significant decimal places (int) )
	# From SILability 1.21
	assert type(InputValue) in [int, float]
	assert isinstance(SigFigs, int)
	if IsEffectivelyZero(float(InputValue)):
		return (0.0, 0) # to avoid crash when trying to take log10(0.0)
	else:
		SigFigs = max(1, SigFigs) # ensure SigFigs > 0
		# + 1e-15 is to ensure correct result for InputValue that's an exact power of 10
		Decimals = int(SigFigs - ceil(log10(abs(InputValue)) + 1e-15))
		return (round(InputValue, Decimals), Decimals)

def RoundValueForDisplay(InputValue, SigFigs=3, SciLowerLimit=1e-4, SciUpperLimit=1e6):
	# return InputValue (float or int) as str with specified number of significant figures.
	# if abs(InputValue) <= SciLowerLimit or >= SciUpperLimit, it will be shown in scientific notation.
	assert isinstance(InputValue, (float, int))
	assert isinstance(SigFigs, int)
	assert SigFigs > 0
	assert isinstance(SciLowerLimit, (float, int))
	assert isinstance(SciUpperLimit, (float, int))
	assert 0 < SciLowerLimit < SciUpperLimit
	AbsValue = abs(InputValue)
	# round the value, and find out how many digits to show after the decimal place
	(RoundedValue, SigDecimals) = RoundToSigFigs(AbsValue, SigFigs)
	if SciLowerLimit < AbsValue < SciUpperLimit: # show in non-scientific notation
		# format the display with the correct number of digits before and after the decimal place
		OutStr = '%*.*f' % (SigFigs, SigDecimals, RoundedValue)
	else: # show in scientific notation
		OutStr = '%*.*e' % (SigFigs, SigFigs - 1, RoundedValue)
	# add negative sign if InputValue is negative
	if InputValue < 0: OutStr = '-' + OutStr
	return OutStr

def TextAsString(XMLTag, ValueIfEmpty=''): # return text from XMLTag.
	# If empty (no text in the XML tag), or if text contains whitespace only, return ValueIfEmpty
	# (We use this function because just calling XMLTag.text will return None if text is empty)
	# This procedure is taken from SILability
	T = XMLTag.text
	if T is None: return ValueIfEmpty
	elif not T.strip(): return ValueIfEmpty
	else: return T.strip()

def SortOnValues(InList, ResultField, SortKeyField):
	"""
	InList is a list (or nested lists) of dictionaries
    returns a list of ResultField values, sorted according to the values of
    corresponding SortKeyField entries

	>>> l = [{'a':1, 'b':10},{'a':2, 'b':9}]
	>>> SortOnValues(l, 'b', 'a')
	[10, 9]
	>>> SortOnValues(l, 'a', 'b')
	[2, 1]
	>>> l = [[{'a':1, 'b':10},{'a':2, 'b':9}], [[{'a':3, 'b':8}], {'a':4, 'b':7}]]
	>>> SortOnValues(l, 'b', 'a')
	[10, 9, 8, 7]
	"""
	assert type(InList) == list

	if not InList:
		return []

	# merge nested lists into a single list
	dict_list = Flatten(InList, ltypes=(list))
	# build a list of (key, values), sorted on keys
	result_list = sorted([(d[SortKeyField], d[ResultField]) for d in dict_list], key=lambda x: x[0])
	# return list of values
	return [i[1] for i in result_list]

def Flatten(l, ltypes=(list, tuple)):
	"""
	Reduces any iterable containing other iterables into a single list
	of non-iterable items. The ltypes option allows control over what
	element types will be flattened.
	Returns iterable of the same type as l, containing all member items of l that are of types given in ltypes.
	If l is an empty iterable, returns empty iterable.
	This algorithm is taken from:
	http://rightfootin.blogspot.com/2006/09/more-on-python-flatten.html

	>>> print Flatten([range(2),range(3,6)])
	[0, 1, 3, 4, 5]
	>>> print Flatten([1,2,(3,4)])
	[1, 2, 3, 4]
	>>> print Flatten([1,[2,3,[4,5,[6,[7,8,[9,[10]]]]]]])
	[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
	>>> print Flatten([1,[2,3,[4,5,[6,[7,8,[9,[10]]]]]]], ltypes=())
	[1, [2, 3, [4, 5, [6, [7, 8, [9, [10]]]]]]]
	>>> print Flatten([1,2,(3,4)],ltypes=(list))
	[1, 2, (3, 4)]
	"""
	ltype = type(l)
	l = list(l)
	i = 0
	while i < len(l):
		while isinstance(l[i], ltypes):
			if not l[i]:
				l.pop(i)
				i -= 1
				break
			else:
				l[i:i + 1] = l[i]
		i += 1
	return ltype(l)

def CompareTuple(first, second, element=0):
	"""
	Compares two tuples based on their values at the index given by element.
	Returns int: 1 if element in first > element in second, 0 if equal, -1 if second > first.
	Currently not used. Previously this was the cmp arg in sort() functions.
	>>> print CompareTuple((1,2),(1,3))
	0
	>>> print CompareTuple((1,2),(2,1))
	-1
	>>> print CompareTuple((1,2),(2,1),element=1)
	1
	"""
	ElInFirst = first[element]
	ElInSecond = second[element]
	if ElInFirst > ElInSecond: return 1
	elif ElInFirst < ElInSecond: return -1
	else: return 0

def Bool2Str(Input, TrueStr='y', FalseStr='n'):
	# convert between boolean and string. If Input is bool, Output will be TrueStr or FalseStr.
	# If input is str, output will be bool.
	# Input str's interpreted as True: Y Yes True 1 (case insensitive). Any other str value interpreted as False.
	# Leading and trailing whitespace is ignored.
	assert isinstance(Input, (bool, str))
	if isinstance(Input, bool): return {True: TrueStr, False: FalseStr}[Input]
	else: return Input.strip().upper() in ['Y', 'YES', 'TRUE', '1']

def UnpackPairsList(Instr, IntraPairSeparator='~', InterPairSeparator=','):
	# Instr (str) contains zero or more items 'x~y' (x, y arbitrary strings not containing ~) separated by commas.
	# Returns list of tuples [ (x1, y1), (x2, y2)... ]
	assert isinstance(Instr, str)
	assert isinstance(IntraPairSeparator, str)
	assert isinstance(InterPairSeparator, str)
	if Instr:
		return [tuple(Pair.split(IntraPairSeparator)) for Pair in Instr.split(InterPairSeparator)]
	else: return [] # needed because ''.split('x') returns [''] not [] if split's arg is defined

def TextWithoutSpecialChars(InText):
	# returns string with 'special characters' in InText processed. Currently:
	# smart single/double quotes are converted to straight single/double quotes
	# This is used as a workaround to deal with behaviour of ExpandoTextCtrl, which seems to convert 'quotes' to
	# smart quotes unbidden
	assert isinstance(InText, str)
	ConversionHash = {u'\u2018': "'", u'\u2019': "'", u'\u201c': '"', u'\u201d': '"'}
	# check and process each char in InText
	# convert if the char is in ConversionHash, else keep the same char
	return ''.join([ConversionHash.get(ThisChar, ThisChar) for ThisChar in InText])
