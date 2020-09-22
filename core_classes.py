# -*- coding: utf-8 -*-
# Module core_classes: part of Vizop, (c) 2020 xSeriCon
# contains class definitions of basic objects used throughout Vizop

# library modules
# from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import. No longer needed
import wx # provides basic GUI functions
import copy, math
import xml.etree.ElementTree as ElementTree # XML handling

# other vizop modules required here
import text, utilities, info

def _(DummyArg): return DummyArg # dummy definition of _(); the real definition is elsewhere

class RiskReceptorItem(object): # class of risk receptors
#	RRs = [] # list of all risk receptor instances defined in the open projects

	def __init__(self, ID='', XMLName='', HumanName='<undefined>'):
		assert isinstance(ID, str)
		assert ID # ensure it's nonblank
		object.__init__(self)
		self.XMLName = XMLName
		self.HumanName = HumanName
		self.ID = ID
#		self.ID = str(utilities.NextID(RiskReceptorItem.RRs)) # generate unique ID; stored as str
#		RiskReceptorItem.RRs.append(self) # add this RiskReceptorItem to register (must be after NextID() call)

DefaultRiskReceptor = RiskReceptorItem(ID=info.GenericRRID, XMLName='Default', HumanName=_('Default'))

# --- arithmetic operators ---

class OperatorItem(object): # superclass of operators used to calculate numeric values in formulae
	# The operators are subclasses, not instances, so no __init__ method needed
	MinOperands = 2
	MaxOperands = 99  # arbitrary upper limit on the number of operands per operation

	@staticmethod
	def GetHumanName():
		return "Dummy name - you shouldn't see this"

	HumanName = property(fget=GetHumanName)

	@staticmethod
	def Unit(OperandUnits): # return unit that results from calculation
		# Used by operators for which all operands should have the same unit, and all units defined.
		# Returns NullUnit if any operand has no unit defined, or if operands don't all have the same unit
		assert hasattr(OperandUnits, '__iter__'), "OperandUnits '%s' isn't an iterable" % str(OperandUnits)
		DoTypeChecks([], IterableChecks=[OperandUnits, UnitItem])
		if NullUnit in OperandUnits:
			return NullUnit # problem, at least one operand has undefined or invalid unit
		if len(set(OperandUnits)) != 1: # zero or >1 different unit provided
			return NullUnit
		return OperandUnits[0] # there's only one type of unit provided; return it


class Operator_Add(OperatorItem): # class to implement 'add' operator
	# Uses Unit() method from superclass

	@staticmethod
	def GetHumanName():
		return _('add')

	@staticmethod
	def Result(Operands): # return result of calculation (float or NumProblemValue instance)
		# Operands: list of floats
		if (len(Operands) < MinOperands) or (len(Operands) > MaxOperands): return NumProblemValue_WrongNoOperands
		return float(sum(Operands))


class Operator_Subtract(OperatorItem):  # class to implement 'subtract' operator
	# Uses Unit() method from superclass

	@staticmethod
	def GetHumanName():
		return _('subtract')

	@staticmethod
	def Result(Operands): # return result of calculation (float or NumProblemValue instance)
		# Operands: list of floats
		if (len(Operands) < MinOperands) or (len(Operands) > MaxOperands): return NumProblemValue_WrongNoOperands
		# return a - b - c - ... where a, b... are in Operands; also cope if Operands is empty list
		return float((Operands + [0])[0] - sum(Operands[1:]))


class Operator_Multiply(OperatorItem): # class to implement 'multiply' operator

	@staticmethod
	def GetHumanName():
		return _('multiply')

	@staticmethod
	def Result(Operands):  # return result of calculation (float or NumProblemValue instance)
		# Operands: list of floats
		if (len(Operands) < MinOperands) or (len(Operands) > MaxOperands): return NumProblemValue_WrongNoOperands
		Result = 1.0
		for ThisOperand in Operands: Result *= ThisOperand # can't use reduce() any more, boo
		return Result

	@staticmethod
	def Unit(OperandUnits): # return unit that results from calculation
		# Basis: one unit should be defined (this unit will be returned), others should be DimensionlessUnit
		# Returns NullUnit if the basis isn't met
		assert hasattr(OperandUnits, '__iter__'), "OperandUnits '%s' isn't an iterable" % str(OperandUnits)
		DoTypeChecks([], IterableChecks=[OperandUnits, UnitItem])
		if (NullUnit in OperandUnits) or not OperandUnits:
			return NullUnit # problem, at least one operand has undefined or invalid unit, or no units provided
		UnitsWithDimension = [u for u in OperandUnits if u is not DimensionlessUnit]
		if len(UnitsWithDimension) > 1: # >1 different unit provided
			print("CC104 warning, Multiply operator supplied with >1 unit")
			return NullUnit
		return UnitsWithDimension[0] # there's only one type of unit provided; return it


class Operator_Divide(OperatorItem):  # class to implement 'divide' operator
	MaxOperands = 2

	@staticmethod
	def GetHumanName():
		return _('divide')

	@staticmethod
	def Result(Operands):  # return result of calculation (float or NumProblemValue instance)
		# Operands: list of floats
		if (len(Operands) < MinOperands) or (len(Operands) > MaxOperands): return NumProblemValue_WrongNoOperands
		# check if any divisor is near zero
		if True in [(abs(Op) < info.ZeroThreshold) for Op in Operands[1:]]: return NumProblemValue_DivisionByZero
		Result = (Operands + [1.0])[0] # start with first operand
		for ThisOperand in Operands[1:]: Result /= ThisOperand # can't use reduce() any more, boo
		return Result

	@staticmethod
	def Unit(OperandUnits): # return unit that results from calculation
		# Basis: either numerator and denominator have same unit (defined), (return DimensionlessUnit in this case)
		# or numerator unit is defined (and will be returned) and denominator is dimensionless
		# Returns NullUnit if the basis isn't met
		assert hasattr(OperandUnits, '__iter__'), "OperandUnits '%s' isn't an iterable" % str(OperandUnits)
		assert len(OperandUnits) <= MaxOperands, "%d units supplied, max is %d" % (len(OperandUnits), MaxOperands)
		DoTypeChecks([], IterableChecks=[OperandUnits, UnitItem])
		if (NullUnit in OperandUnits) or not OperandUnits:
			return NullUnit # problem, at least one operand has undefined or invalid unit, or no units provided
		# check if num and denom units are the same
		if OperandUnits[0] == OperandUnits[1]:
			return DimensionlessUnit
		# check if denom unit is DimensionlessUnit
		if OperandUnits[1] is DimensionlessUnit:
			return OperandUnits[0]
		# any other situation, indicate a problem
		return NullUnit


class Operator_RaiseToPower(OperatorItem):  # class to implement 'raise to power' operator
	MaxOperands = 2

	@staticmethod
	def GetHumanName():
		return _('raise to power')

	@staticmethod
	def Result(Operands):  # return result of calculation (float or NumProblemValue instance)
		# Operands: list of floats
		if (len(Operands) < MinOperands) or (len(Operands) > MaxOperands): return NumProblemValue_WrongNoOperands
		Result = (Operands + [1.0])[0] # start with first operand
		for ThisOperand in Operands[1:]: Result **= ThisOperand # can't use reduce() any more, boo
		return Result

	@staticmethod
	def Unit(OperandUnits): # return unit that results from calculation
		# Basis: base and exponent should be DimensionlessUnit
		# Returns NullUnit if the basis isn't met
		assert hasattr(OperandUnits, '__iter__'), "OperandUnits '%s' isn't an iterable" % str(OperandUnits)
		assert len(OperandUnits) <= MaxOperands, "%d units supplied, max is %d" % (len(OperandUnits), MaxOperands)
		DoTypeChecks([], IterableChecks=[OperandUnits, UnitItem])
		if (NullUnit in OperandUnits) or not OperandUnits:
			return NullUnit # problem, at least one operand has undefined or invalid unit, or no units provided
		# check if num and denom units are both DimensionlessUnit
		if OperandUnits[0] == OperandUnits[1] == DimensionlessUnit:
			return DimensionlessUnit
		# any other situation, indicate a problem
		print("CC170 warning, exponent operator with non-dimensionless operand(s)")
		return NullUnit

OperatorClasses = [Operator_Add, Operator_Subtract, Operator_Multiply, Operator_Divide, Operator_RaiseToPower]


class FormulaItem(object):  # class of formulae used to calculate the value of a CalcNumValueItem
	# Each FormulaItem contains a list of operands (NumValueItems, FormulaItems or floats) and an OperatorItem.
	# Complex formulae can be built up by "nesting" FormulaItems.

	def __init__(self):
		object.__init(self)
		self.Operands = [0.0, 0.0]
		self.Operator = Operator_Multiply

	def Value(self, RR=DefaultRiskReceptor,
			  FormulaAntecedents=[]):  # returns calculated value (float) or NumProblemValue
		# FormulaAntecedents is a list of all FormulaItems and CalcNumValueItems already used in this recursive calculation;
		# used for circular reference checking
		# Get numerical value of each operand; build them up in OperandValues
		OperandValues = []
		for ThisOperand in self.Operands:
			if type(ThisOperand) is FormulaItem:
				# check for circular reference, which would cause infinite recursion
				if self in FormulaAntecedents:
					Value = NumProblemValue_Circular
				else:
					Value = ThisOperand.Value(RR, FormulaAntecedents + [self]) # recursively get value of nested formula
			elif type(ThisOperand) in NumValueClasses:
				Value = ThisOperand.Value(RR, FormulaAntecedents=FormulaAntecedents + [self])
			else:
				Value = float(ThisOperand)  # assumed to be a float; take the value directly
			OperandValues.append(Value)
		# did we get numerical values for all operands? To check, find any non-float values in OperandValues
		NonFloat = [Op for Op in OperandValues if type(Op) is not float]
		if NonFloat:
			return NonFloat[0]  # return the first non-float value in OperandValues, if any
		else:
			return self.Operator.Result(OperandValues)  # return the calculated numerical value

	def Unit(self, RR=DefaultRiskReceptor, FormulaAntecedents=[]):
		# returns calculated unit (UnitItem instance) or NullUnit if the formula can't be evaluated
		# FormulaAntecedents is a list of all FormulaItems and CalcNumValueItems already used in this recursive calculation;
		# used for circular reference checking
		# Get unit of each operand; build them up in OperandUnits
		OperandUnits = []
		for ThisOperand in self.Operands:
			if type(ThisOperand) is FormulaItem:
				# check for circular reference, which would cause infinite recursion
				if self in FormulaAntecedents:
					Unit = NullUnit
				else:
					Unit = ThisOperand.Unit(RR, FormulaAntecedents + [self]) # recursively get value of nested formula
			elif type(ThisOperand) in NumValueClasses:
				Unit = ThisOperand.Unit(RR, FormulaAntecedents=FormulaAntecedents + [self])
			else:
				Unit = DimensionlessUnit  # assumed to be a float; assume dimensionless
			OperandUnits.append(Unit)
		# did we get units for all operands?
		if NullUnit in OperandUnits:
			return NullUnit  # return problem indicator
		else:
			return self.Operator.Unit(OperandUnits)  # return the calculated unit

class UnitItem(object):
	# defines an engineering unit such as a time unit
	# taken from SILability
	QtyKinds = ['Probability', 'Frequency', 'Time', 'ShortTime', 'Ratio']
	UserSelectableUnits = [] # list of all units that user can select from (excludes NullUnit)
	UnitNameHash = {} # dict with keys = XMLNames, values = UnitItem instances with that XMLName

	def __init__(self, HumanName='', XMLName='', QtyKind='', UserSelectable=True, SuppressInOutput=False):
		# QtyKind must be in UnitItem.QtyKinds
		# HumanName: name shown on screen; translatable
		# XMLName: name used in XML input/output; fixed
		# SuppressInOutput (bool): whether to hide unit's HumanName in final output
		object.__init__(self)
		assert isinstance(HumanName, str), "CC150 Non-string value for HumanName in UnitItem initialization"
		assert isinstance(XMLName, str)
		assert isinstance(QtyKind, str)
		assert QtyKind in UnitItem.QtyKinds
		assert isinstance(UserSelectable, bool)
		assert isinstance(SuppressInOutput, bool)
		self.HumanName = HumanName
		self.XMLName = XMLName
		self.QtyKind = QtyKind
		if UserSelectable:
			UnitItem.UserSelectableUnits.append(self) # add to register of units
		UnitItem.UnitNameHash[XMLName] = self # add to name hash
		self.SuppressInOutput = SuppressInOutput
		self.Conversion = {self: 1.0} # keys: UnitItem instances;
			# values: coefficient to convert from this unit to unit in key (float). The only compulsory key is self.

# acceptable engineering units
NullUnit = UnitItem('', info.NullUnitInternalName, 'Ratio', UserSelectable=False, SuppressInOutput=True) # used as problem indicator
DimensionlessUnit = UnitItem(_('no unit'), 'None', 'Ratio', SuppressInOutput=True)
ProbabilityUnit = UnitItem(_('probability'), 'Prob', 'Probability', SuppressInOutput=True)
PercentageUnit = UnitItem(_('%'), '%', 'Probability')
PerYearUnit = UnitItem(_('/yr'), '/yr', 'Frequency')
PerMonthUnit = UnitItem(_('/mo'), '/mo', 'Frequency')
PerWeekUnit = UnitItem(_('/wk'), '/wk', 'Frequency')
PerDayUnit = UnitItem(_('/day'), '/day', 'Frequency')
PerHourUnit = UnitItem(_('/hr'), '/hr', 'Frequency')
FITUnit = UnitItem(_('FIT'), 'FIT', 'Frequency')
SecondUnit = UnitItem(_('seconds'), 's', 'ShortTime')
MinuteUnit = UnitItem(_('minutes'), 'min', 'ShortTime')
HourUnit = UnitItem(_('hours'), 'hr', 'Time')
DayUnit = UnitItem(_('days'), 'day', 'Time')
WeekUnit = UnitItem(_('weeks'), 'wk', 'Time')
MonthUnit = UnitItem(_('months'), 'month', 'Time')
YearUnit = UnitItem(_('years'), 'yr', 'Time')
PerYearUnit.Conversion[PerMonthUnit] = 0.083333 # = 1/12, no of years in 1 month
PerYearUnit.Conversion[PerWeekUnit] = 0.019165 # = 7/365.25, no of years in 1 week, allowing for leap years
PerYearUnit.Conversion[PerDayUnit] = 0.0027378 # = 1/365.25, no of years in 1 hour, allowing for leap years
PerYearUnit.Conversion[PerHourUnit] = 0.000114077 # no of years in 1 hour, allowing for leap years
PerYearUnit.Conversion[FITUnit] = 114077 # no of years in 10^9 hours, allowing for leap years
PerMonthUnit.Conversion[PerYearUnit] = 12
PerMonthUnit.Conversion[PerWeekUnit] = 0.22998 # = 7 x 12/365.25, no of months in 1 week, allowing for leap years
PerMonthUnit.Conversion[PerDayUnit] = 0.032854 # = 12/365.25, inverse of average no of days per month
PerMonthUnit.Conversion[PerHourUnit] = 0.0013689 # = 1/24 x 12/365.25 assuming equal month lengths
PerMonthUnit.Conversion[FITUnit] = 1368924 # no of months in 10^9 hours, allowing for leap years
PerWeekUnit.Conversion[PerYearUnit] = 52.179 # = 365.25/7
PerWeekUnit.Conversion[PerMonthUnit] = 4.3482 # = 365.25/(7*12)
PerWeekUnit.Conversion[PerDayUnit] = 0.14286 # = 1/7
PerWeekUnit.Conversion[PerHourUnit] = 0.0059524 # = 1/24 x 1/7
PerWeekUnit.Conversion[FITUnit] = 5952400 # no of weeks in 10^9 hours, allowing for leap years
PerDayUnit.Conversion[PerYearUnit] = 365.25
PerDayUnit.Conversion[PerMonthUnit] = 30.438 # = 365.25/12
PerDayUnit.Conversion[PerWeekUnit] = 7
PerDayUnit.Conversion[PerHourUnit] = 0.041667 # = 1/24
PerDayUnit.Conversion[FITUnit] = 41666800 # no of days in 10^9 hours, allowing for leap years
PerHourUnit.Conversion[PerYearUnit] = 8766 # no of hours in 1 year, allowing for leap years
PerHourUnit.Conversion[FITUnit] = 1e9 # by definition
FITUnit.Conversion[PerYearUnit] = 8.76601e-6 # inverse of PerYear -> FIT conversion
FITUnit.Conversion[PerMonthUnit] = 7.305007e-7
FITUnit.Conversion[PerWeekUnit] = 1.679995e-7
FITUnit.Conversion[PerDayUnit] = 2.4e-8
FITUnit.Conversion[PerHourUnit] = 1e-9 # by definition
PercentageUnit.Conversion[DimensionlessUnit] = 0.01
PercentageUnit.Conversion[ProbabilityUnit] = 0.01
DimensionlessUnit.Conversion[PercentageUnit] = 100.0
ProbabilityUnit.Conversion[PercentageUnit] = 100.0
HourUnit.Conversion[DayUnit] = 0.041667 # = 1/24
HourUnit.Conversion[WeekUnit] = 0.0059524 # = 1/24 x 1/7
HourUnit.Conversion[MonthUnit] = 0.0013689 # = 1/24 x 12/365.25 assuming equal month lengths
HourUnit.Conversion[YearUnit] = 0.00011408 # = 1/24 x 1/365.25 allowing for leap years
DayUnit.Conversion[HourUnit] = 24
DayUnit.Conversion[WeekUnit] = 0.14286 # = 1/7
DayUnit.Conversion[MonthUnit] = 0.032854 # = 12/365.25 assuming equal month lengths
DayUnit.Conversion[YearUnit] = 0.0027378 # = 1/365.25 allowing for leap years
WeekUnit.Conversion[HourUnit] = 168 # 24 x 7
WeekUnit.Conversion[DayUnit] = 7
WeekUnit.Conversion[MonthUnit] = 0.22998 # = 7 x 12/365.25
WeekUnit.Conversion[YearUnit] = 0.019165 # = 7/365.25
MonthUnit.Conversion[HourUnit] = 730.5 # = 24 x 365.25/12
MonthUnit.Conversion[DayUnit] = 30.438 # = 365.25/12
MonthUnit.Conversion[WeekUnit] = 4.3482 # = 365.25/(7*12)
MonthUnit.Conversion[YearUnit] = 0.083333 # = 1/12
YearUnit.Conversion[HourUnit] = 8766 # = 24 x 365.25
YearUnit.Conversion[DayUnit] = 365.25
YearUnit.Conversion[WeekUnit] = 52.179 # = 365.25/7
YearUnit.Conversion[MonthUnit] = 12
ProbabilityUnits = [u for u in UnitItem.UserSelectableUnits if u.QtyKind == 'Probability']
FrequencyUnits = [u for u in UnitItem.UserSelectableUnits if u.QtyKind == 'Frequency']
TimeUnits = [u for u in UnitItem.UserSelectableUnits if u.QtyKind == 'Time']
RatioUnits = [u for u in UnitItem.UserSelectableUnits if u.QtyKind == 'Ratio']
AllSelectableUnits = ProbabilityUnits + FrequencyUnits + TimeUnits + RatioUnits
DefaultBetaUnit = PercentageUnit

def UnitWithName(TargetXMLName):
	# find and return UnitItem instance with XMLName==TargetXMLName, or None if not found.
	assert isinstance(TargetXMLName, str)
	return UnitItem.UnitNameHash.get(TargetXMLName, None)

class OpModeType(object): # class of SIF operating modes; consistent with implementation in SILability
	DisplayName = _('Operating mode') # for display in comment header and Undo/Redo menu items

	def __init__(self, HumanName, XMLName, PermissibleTargetKinds):
		object.__init__(self)
		self.HumanName = HumanName # visible to user
		self.XMLName = XMLName # name used in XML input/output
		self.PermissibleTargetKinds = PermissibleTargetKinds # list of str of TargetKinds such as 'PFDavg'

UndefinedMode = OpModeType(_('<Undefined>'), 'Undefined', ['PFDavg', 'RRF', 'PFH'])
LowDemandMode = OpModeType(_('Low demand'), 'LowDemand', ['PFDavg', 'RRF'])
HighDemandMode = OpModeType(_('High demand'), 'HighDemand', ['PFH'])
ContinuousMode = OpModeType(_('Continuous'), 'Continuous', ['PFH'])
OpModes = [UndefinedMode, LowDemandMode, HighDemandMode, ContinuousMode]
DefaultOpMode = LowDemandMode

ValueStati = ['ValueStatus_OK', 'ValueStatus_Unset'] # value status indicators for NumValueItem instances

class NumValueItemForDisplay(object): # class of numerical values with associated attributes, used for display
	# This class just acts as a wrapper to keep all the attributes together

	def __init__(self):
		object.__init__(self)
		self.Value = '' # (str) value as currently displayed
		self.Unit = NullUnit # (UnitItem instance) unit as currently displayed
		self.UnitOptions = [] # list of UnitItem instances that can be offered to the user for this value
		self.ValueKindOptions = [] # list of subclasses of NumValueItem that can be offered to the user for this value
		self.ConstantOptions = [] # list of ConstantItem human names (str) that can be offered to the user for this value

class NumValueItem(object): # superclass of objects in Datacore having a numerical value with units
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object
	# special attribs that may exist in an instance, and which should be preserved if the instance is converted to
	# another subclass (e.g. in faulttree.ChangeNumberKind()). Caution:
	# 1. abs(MinValue) should not be < info.ZeroThreshold,
	# otherwise small valid values may be displayed as zero
	# 2. If an instance has a MaxValue and/or a MinValue, it must also have a MaxMinUnit
	# UserValue (dict): value family defined when this item was a UserNumValueItem; keys are RR's
	# UserUnit (UnitItem instance): unit defined when this item was a UserNumValueItem
	# UserIsSet (dict): flag family defined when this item was a UserNumValueItem; keys are RR's
	# ConstConst (ConstantItem instance): a constant this item was previously assigned to
	# LookupX: attribs belonging to LookupItem
	# ParentX: attribs belonging to ParentNumValueItem
	# UseParentX: attribs belonging to UseParentNumValueItem
	PersistentAttribs = ['MaxValue', 'MinValue', 'MaxMinUnit', 'UserValue', 'UserUnit', 'UserIsSet', 'ConstConst',
		'LookupLookupTable', 'LookupInputValue', 'ParentValue', 'ParentParentPHAObj', 'UseParentParentPHAObj']
	# AttribsWithRRKeys: list of (Attrib name, default value) for attribs that are dicts with keys = RRs.
	# This list is used to create keys in new number instances when changing number kinds.
	AttribsWithRRKeys = [ ('ValueFamily', None), ('UserValueFamily', None), ('IsSetFlagFamily', None),
		('InfinityFlagFamily', False), ('SigFigs', info.DefaultSigFigs), ('Sci', False) ]

	def __init__(self, HostObj=None, **Args):
		# HostObj: None, or the object containing this NumValueItem instance,
		# which can optionally provide a CheckValue(v=NumValueItem instance) method
		object.__init__(self)
		self.HumanName = _('<undefined>')
		# set numerical values per risk receptor. Must include DefaultRiskReceptor key. None means value not defined
		self.ValueFamily = {DefaultRiskReceptor: None} # current numerical values of instance per risk receptor
		self.UserValueFamily = {DefaultRiskReceptor: None} # values provided by user.
			# Kept for reversion if we switch to another type (eg constant), then back again
			# TODO superseded by PersistentAttribs?
		self.IsSetFlagFamily = {DefaultRiskReceptor: None} # ValueStatus (member of ValueStati) per risk receptor
		self.InfinityFlagFamily = {DefaultRiskReceptor: False} # bool per risk receptor; whether value is infinite
		self.SigFigs = {DefaultRiskReceptor: info.DefaultSigFigs} # int per risk receptor; how many sig figs for display
		self.Sci = {DefaultRiskReceptor: False} # bool per risk receptor; whether to always use scientific notation
			# TODO: consider whether SigFigs and Sci should be common for all RR's
		self.MyUnit = NullUnit
		self.HostObj = HostObj

	def AddRiskReceptor(self, RR):
		# add a new risk receptor RR (RiskReceptorItem instance) to the number
		assert isinstance(RR, RiskReceptorItem)
		assert not (RR in self.ValueFamily.keys()) # to avoid overwriting existing RR
		self.ValueFamily[RR] = None
		self.UserValueFamily[RR] = None
		self.IsSetFlagFamily[RR] = 'ValueStatus_Unset'
		self.InfinityFlagFamily[RR] = False
		self.SigFigs[RR] = info.DefaultSigFigs
		self.Sci[RR] = False

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], InvalidResult=0.0, **Args):
		# return numerical value of object, appropriate to risk receptor RR
		# This GetMyValue is used by classes that directly return a numerical value. Other classes override it
		# FormulaAntecedents is a list of nested FormulaItems and CalcNumValueItems used in calculating a FormulaItem
		# value. Only relevant to CalcNumValueItems
		# InvalidResult (float): value to return if a valid value can't be returned
		# return value is always float. InvalidResult returned if there's any problem with getting the value
		# first, check that RR is defined
		if not (RR in self.ValueFamily):  # requested risk receptor not defined for this value object
			print("Warning, missing '%s' key in NumValueItem risk receptors (problem code: D26)" % RR)
			if DefaultRiskReceptor in self.ValueFamily:
				RR = DefaultRiskReceptor
			else: # DefaultRiskReceptor key is missing
				print("Oops, missing DefaultRiskReceptor key in NumValueItem risk receptors (problem code: D28). This is a bug; please report it")
				return InvalidResult
		# get the actual value
		MyStatus = self.Status(RR)
		if MyStatus == NumProblemValue_NoProblem:
			assert isinstance(self.ValueFamily[RR], float), "Numerical value '%s' is not float" % str(
				self.ValueFamily[RR])
			return float(self.ValueFamily[RR])
		else: return InvalidResult

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # set numerical value of object per risk receptor
		# error checking first
		assert isinstance(NewValue, int) or isinstance(NewValue, float),\
			"NewValue '%s' isn't a valid number" % str(NewValue)
		self.ValueFamily[RR] = float(NewValue)
		self.UserValueFamily[RR] = float(NewValue) # store manually-entered value for restoration
		self.IsSetFlagFamily[RR] = True
		self.InfinityFlagFamily[RR] = False
		self.SetMyStatus(NewStatus='ValueStatus_OK', RR=RR)

	def SetToInfinite(self, RR=DefaultRiskReceptor): # set value as infinite for this risk receptor
		assert RR in self.ValueFamily.keys()
		self.InfinityFlagFamily[RR] = True
		self.SetMyStatus(NewStatus='ValueStatus_OK', RR=RR)

	def GetMyUnit(self): # returns unit (instance of UnitItem)
		assert isinstance(self.MyUnit, UnitItem)
		return self.MyUnit

	def SetMyUnit(self, NewUnit): # set engineering unit to instance of UnitItem
		assert isinstance(NewUnit, UnitItem)
		self.MyUnit = NewUnit

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

	def GetMyValueInUnit(self, NewUnit, RR=DefaultRiskReceptor):
		# returns value (for risk receptor RR) of the NumValueItem instance, converted to NewUnit if possible
		# Return numerical value (int or float) if conversion successful;
		# otherwise returns str: 'ValueNotSet' or 'NoConversionFactor'
		assert isinstance(NewUnit, UnitItem)
		assert isinstance(self.Unit, UnitItem)
		Success = False # whether conversion was successful
		ProblemMessage = ''
		# check if required conversion factor is defined
		if NewUnit in self.GetMyUnit().Conversion:
			if RR in self.ValueFamily:
				if (self.IsSetFlagFamily[RR] == 'ValueStatus_OK') and not self.InfinityFlagFamily[RR]:
					Success = True
					ConvertedValue = self.GetMyValue(RR, InvalidResult=0) * self.GetMyUnit().Conversion[NewUnit]
				else:
					ProblemMessage = 'ValueNotSet'
			else: ProblemMessage = 'NoConversionFactor'
		if Success: return ConvertedValue
		else: return ProblemMessage

	def GetDisplayValue(self, RR=DefaultRiskReceptor, InvalidResult=_('<Undefined>'), InfiniteResult=info.InfinitySymbol,
			**Args):
		# returns value of this NumValueItem instance as formatted string, or InvalidResult if value can't be obtained
		# Args can include SciThresholdUpper and SciThresholdLower (int, float or None). If it is int or float, and
		# the absolute numerical value ≥ SciThresholdUpper or ≤ SciThresholdLower, scientific notation is forced.
		assert isinstance(self.SigFigs, dict)
		assert DefaultRiskReceptor in self.SigFigs
		assert not [s for s in self.SigFigs.values() if not isinstance(s, int)] # confirm all SigFig values are int
		assert isinstance(self.Sci, dict)
		assert DefaultRiskReceptor in self.Sci
		assert not [s for s in self.Sci.values() if not isinstance(s, bool)] # confirm all Sci values are bool
		assert isinstance(self.InfinityFlagFamily, dict)
		assert DefaultRiskReceptor in self.InfinityFlagFamily
		assert not [s for s in self.InfinityFlagFamily.values() if not isinstance(s, bool)]
			# confirm all InfinityFlagFamily values are bool
		if self.Status(RR) == 'ValueStatus_Unset': return InvalidResult
		elif self.InfinityFlagFamily[RR]: return InfiniteResult # check if infinity flag is set
		else:
			MyValue = self.GetMyValue(RR=RR, InvalidResult=InvalidResult, **Args)
			if MyValue == InvalidResult:
				return InvalidResult
			else: # result is valid; proceed to apply rounding, formatting etc.
				# the line below allows us to define number of sig figs per unit; not used anywhere in Vizop yet
				SigFigs = self.SigFigs.get(self.GetMyUnit(), self.SigFigs[DefaultRiskReceptor])
				# round MyValue to required number of sig figs
				(TruncatedValue, Decimals) = utilities.RoundToSigFigs(MyValue, SigFigs)
				# determine whether to force scientific notation; algorithm 344.1 in spec
				if Args.get('SciThresholdUpper', None) is None:
					if Args.get('SciThresholdLower', None) is None:
						ForceSci = False # neither Upper nor Lower is set; don't use sci notation
					else:
						assert isinstance(Args['SciThresholdLower'], (int, float))
						ForceSci = (abs(MyValue) <= Args['SciThresholdLower'])
				else: # upper threshold is set
					assert isinstance(Args['SciThresholdUpper'], (int, float))
					if (abs(MyValue) >= Args['SciThresholdUpper']):
						ForceSci = True
					else:
						if Args.get('SciThresholdLower', None) is None:
							ForceSci = False # Lower is not set; don't use sci notation
						else:
							assert isinstance(Args['SciThresholdLower'], (int, float))
							ForceSci = (abs(MyValue) <= Args['SciThresholdLower'])
				# apply string formatting to get scientific notation if required, and required number of decimal places
				if self.Sci.get(self.GetMyUnit(), self.Sci[DefaultRiskReceptor]) or ForceSci: # scientific notation required for this unit?
					return '%0.*e' % (SigFigs - 1, TruncatedValue) # change 'e' to 'E' if want 1.2E6 instead of 1.2e6
				else: # non-scientific notation
					return '%0.*f' % (Decimals, TruncatedValue)

	def Status(self, RR=DefaultRiskReceptor): # return NumProblemValue item indicating status of value
		# This method doesn't check the value is within valid range. For that, call CheckValue() in module FaultTree
		if not (RR in self.ValueFamily):  # requested risk receptor not defined for this value object
			print("Warning, missing '%s' key in NumValueItem risk receptors (problem code: CC390)" % RR.HumanName)
			if DefaultRiskReceptor in self.ValueFamily:
				RR = DefaultRiskReceptor
			else:  # DefaultRiskReceptor key is missing
				print("Oops, missing DefaultRiskReceptor key in NumValueItem risk receptors (problem code: CC394). ",
					"This is a bug; please report it")
				return NumProblemValue_Bug
		# check if value is set
		if (self.ValueFamily[RR] is None) or (self.IsSetFlagFamily[RR] != 'ValueStatus_OK'):
			# value not defined, returned 'undefined' NumProblemValue
			return NumProblemValue_UndefNumValue
		else: # value set (skipping the value check below - this is not the purpose of Status())
#		else: # value set; check if it is valid by trying to call self.HostObj.CheckValue(self)
#			# (the lambda function is invoked if HostObj is None or CheckValue isn't defined
#			return getattr(self.HostObj, 'CheckValue', lambda v: NumProblemValue_NoProblem)(self)
			return NumProblemValue_NoProblem

	def GetMyStatus(self, RR=DefaultRiskReceptor, **Args): # get status of value (NumProblemValue item)
		return self.Status(RR=RR)

	def SetMyStatus(self, NewStatus, RR=DefaultRiskReceptor, **Args): # set status indicator (in IsSetFlagFamily)
		assert NewStatus in ValueStati
		assert RR in self.ValueFamily.keys()
		self.IsSetFlagFamily[RR] = NewStatus
		return True # indicates successful

	def GetMyAcceptableUnits(self): # return list of UnitItems permitted for display of this value.
		# Each subclass should override this method. Needed here due to property() below.
		return [NullUnit]

	def SetMyAcceptableUnits(self, NewAcceptableUnits, **Args): # set acceptable units for display of this value.
		# Subclasses can optionally override this method. Needed here due to property() below.
		return False # nothing to do in the superclass

	AcceptableUnits = property(fget=lambda self: self.GetMyAcceptableUnits(), fset=lambda self, x: self.SetMyAcceptableUnits(x))
	# we use lambda in the property() args so that it will call the overridden methods in subclasses

	def MakeNewNumberKind(self, NewNumberKind, AttribsToPreserve=[],
			AutoCalculator=None, AutoStatusGetter=None, AutoUnitGetter=None, LinkedFromElement=None):
		# create an instance of NewNumberKind (a subclass of NumValueKind) and copy across all required attribs.
		# return the new instance
		# assumes caller has already checked that NewNumberKind is valid for the value
		# AttribsToPreserve (list of str): any existing attribs of self listed here will be copied to the new instance
		# AutoCalculator (etc): (3 x callable or None) if NewNumberKind is AutoNumValueItem,
		# these 3 methods will be assigned to its methods, if they are not None
		# LinkedFromElement (element in any PHA object): element to link from, if NewNumberKind is UseParentValueItem;
		#	if None, we attempt to restore a previous LinkedFromElement (but without checking it still exists, FIXME)
		assert issubclass(NewNumberKind, NumValueItem)
		# First, find the existing number kind
		OldNumberKind = type(self)
		# store persistent attribs for the old number kind, to allow previous number kind to be restored nicely later
		if OldNumberKind == UserNumValueItem:
			self.UserValue = copy.copy(self.ValueFamily)
			self.UserIsSet = copy.copy(self.IsSetFlagFamily)
			self.UserUnit = self.GetMyUnit()
		elif OldNumberKind == ConstNumValueItem:
			self.ConstConst = self.Constant
		elif OldNumberKind == LookupNumValueItem:
			self.LookupLookupTable = self.LookupTable
			self.LookupInputValue = self.InputValue
		elif OldNumberKind == ParentNumValueItem:
			self.ParentValue = copy.copy(self.ValueFamily)
			self.ParentParentPHAObj = self.ParentPHAObj
		elif OldNumberKind == UseParentValueItem:
			self.UseParentParentPHAObj = self.ParentPHAObj
		# create new number object in the new kind
		NewValueObj = NewNumberKind()
		# make risk receptor keys in lists in the new number object
		for (ThisListAttribName, DefaultValue) in NumValueItem.AttribsWithRRKeys:
			getattr(NewValueObj, ThisListAttribName).update(dict(
				[(ThisRR, DefaultValue) for ThisRR in self.ValueFamily.keys()]))
		# preserve attribs as requested by caller
		for ThisAttrib in [a for a in AttribsToPreserve if hasattr(self, a)]:
			setattr(NewValueObj, ThisAttrib, copy.copy(getattr(self, ThisAttrib)))
		# copy any other persistent attribs from the old to the new number object
		# set up methods for AutoNumValueItem
		if NewNumberKind == AutoNumValueItem:
			if AutoCalculator is not None:
				assert callable(AutoCalculator)
				NewValueObj.Calculator = AutoCalculator
			if AutoStatusGetter is not None:
				assert callable(AutoStatusGetter)
				NewValueObj.StatusGetter = AutoStatusGetter
			if AutoUnitGetter is not None:
				assert callable(AutoUnitGetter)
				NewValueObj.UnitGetter = AutoUnitGetter
		elif NewNumberKind == UserNumValueItem:  # set up for 'user defined value'
			# restore any previous values
			for (RestoreAttrib, OriginalAttrib) in [('UserValue', 'ValueFamily'), ('UserIsSet', 'IsSetFlagFamily')]:
				if hasattr(self, RestoreAttrib): setattr(NewValueObj, OriginalAttrib,
					copy.copy(getattr(self, RestoreAttrib)))
			if hasattr(self, 'UserUnit'): NewValueObj.SetMyUnit(self.UserUnit)
		elif NewNumberKind == ConstNumValueItem:
			if hasattr(self, 'ConstConst'): NewValueObj.Constant = self.ConstConst
		elif NewNumberKind == LookupNumValueItem:
			for (RestoreAttrib, OriginalAttrib) in [('LookupLookupTable', 'LookupTable'),
													('LookupInputValue', 'InputValue')]:
				if hasattr(self, RestoreAttrib): setattr(NewValueObj, OriginalAttrib,
					getattr(self, RestoreAttrib))
		elif NewNumberKind == ParentNumValueItem:
			if hasattr(self, 'ParentParentValue'):
				NewValueObj.ParentValue = copy.copy(self.ParentParentValue)
			for (RestoreAttrib, OriginalAttrib) in [('ParentParentPHAObj', 'ParentPHAObj')]:
				if hasattr(self, RestoreAttrib):
					setattr(NewValueObj, OriginalAttrib, getattr(self, RestoreAttrib))
		elif NewNumberKind == UseParentValueItem:
			if LinkedFromElement is None: # try to restore previously linked element
				for (RestoreAttrib, OriginalAttrib) in [('UseParentParentPHAObj', 'ParentPHAObj')]:
					if hasattr(self, RestoreAttrib):
						setattr(NewValueObj, OriginalAttrib, getattr(self, RestoreAttrib))
			else: # make link to supplied element
				NewValueObj.ParentPHAObj = LinkedFromElement
		return NewValueObj

class UserNumValueItem(NumValueItem): # class of NumValues for which user supplies a numeric value
	# Uses GetMyValue and GetMyUnit method from superclass
	HumanName = _('User defined')
	XMLName = 'User'

	def __init__(self, HostObj=None, **Args): # Args can contain any special attribs with initial values. These will be preserved on
		# save only if listed in NumValueItem.PersistentAttribs
		NumValueItem.__init__(self, HostObj, **Args)
		self.MyAcceptableUnits = []
		self.__dict__.update(Args)

	def ConvertToUnit(self, NewUnit):
		# set engineering unit of the NumValueItem instance, and try to convert the value.
		# Return str: 'OK', 'ValueNotSet', 'SetValueFailed' or 'NoConversionFactor'
		assert isinstance(NewUnit, UnitItem)
		assert isinstance(self.Unit, UnitItem)
		Success = False # whether conversion was successful
		# check if required conversion factor is defined
		if NewUnit in self.Unit.Conversion:
			# attempt to convert value for each risk receptor - only if the value has been set and is not infinity
			SetValueOK = True # whether all RRs' values were set successfully
			AllValuesDefined = True
			for RR in self.ValueFamily:
				if (self.IsSetFlagFamily[RR] == 'ValueStatus_OK') and not self.InfinityFlagFamily[RR]:
					Success = self.SetMyValue(self.GetMyValue(RR, InvalidResult=0) * self.Unit.Conversion[NewUnit], RR=RR)
					SetValueOK = SetValueOK and Success
				else:
					AllValuesDefined = False
			# determine which message string to return
			if not AllValuesDefined: Message = 'SomeValuesNotSetOrInfinite'
			elif SetValueOK: Message = 'OK'
			else: Message = 'SetValueFailed'
		else:
			Message = 'NoConversionFactor'
		self.Unit = NewUnit # set new unit (regardless of whether conversion factor found and new values set)
		return Message

	def GetMyAcceptableUnits(self): # return list of UnitItems permitted for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		return self.MyAcceptableUnits

	def SetMyAcceptableUnits(self, NewAcceptableUnits, **Args): # set acceptable units for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		assert isinstance(NewAcceptableUnits, list)
		assert False not in [isinstance(u, UnitItem) for u in NewAcceptableUnits] # confirm it's a list of UnitItem's
		self.MyAcceptableUnits = NewAcceptableUnits
		return True

class ConstantItem(object): # user-defined constants that can be attached to any number of ConstNumValueItems
	# A ConstantItem is the actual constant definition, e.g. "Explosion probability". The ConstNumValueItem instances
	# are the specific places where that value is used in the PHA objects.
	# Each constant has values per RR, and a Unit; these are wrapped in a NumValueItem instance
	def __init__(self, HumanName='', ID='', **Args):
		assert isinstance(HumanName, str)
		assert isinstance(ID, str)
		assert ID # ensure ID is not blank
		object.__init__(self)
		self.HumanName = HumanName
		self.ID = ID
		self.Value = UserNumValueItem(HostObj=self, **Args)

class ConstNumValueItem(NumValueItem): # class of constant NumValues. Refers to a ConstantItem instance
	HumanName = _('Constant')
	XMLName = 'Constant'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, ConstantToReferTo=None, **Args):
		NumValueItem.__init__(self)
		self.Constant = ConstantToReferTo # instance of ConstantItem, or None

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[]):
		assert isinstance(self.Constant, ConstantItem)
		return self.Constant.GetMyValue(RR=RR, FormulaAntecedents=FormulaAntecedents)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		raise TypeError("Not allowed to set value of a ConstNumValueItem directly")

	def GetMyUnit(self): # returns current unit of constant (instance of UnitItem) if self.Constant is defined,
		# else returns NullUnit
		if self.Constant is None: return NullUnit
		else:
			assert isinstance(self.Constant.Unit, UnitItem)
			return self.Constant.Unit

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a ConstNumValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

	def GetMyAcceptableUnits(self): # return list of UnitItems permitted for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		if self.Constant is None: return []
		else: return self.Constant.MyUnitKind.AcceptableUnits

	def SetMyAcceptableUnits(self, NewAcceptableUnits, **Args): # set acceptable units for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		raise TypeError('CC659 Not allowed to set units of ConstantItem')
		return False

class CalcNumValueItem(NumValueItem): # class of NumValues that are calculated from a formula
	HumanName = _('Calculated value')
	XMLName = 'Calc'
	UserSelectable = True # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self)
		self.Formula = None  # formula used to calculate the instance's value (instance of FormulaItem or a NumValueItem)

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[]):
		# return numerical value of object, appropriate to risk receptor RR
		# FormulaAntecedents is a list of nested FormulaItems and CalcNumValueItems used in calculating a FormulaItem value.
		# Used for circular reference checking
		# return value is a float or a NumProblemValue instance
		if self.Formula is None: # formula not defined
			return NumProblemValue_UndefNumValue
		# First, check for circular reference to self
		if self in FormulaAntecedents:
			return NumProblemValue_Circular
		elif type(self.Formula) in NumValueClasses:
			return self.Formula.Value(RR, FormulaAntecedents + ['self'])
		elif type(self.Formula) is FormulaItem:
			return self.Formula.Value(RR, FormulaAntecedents + ['self'])
		else:
			print("Oops, unrecognised type %s assigned to calculated numerical value item (problem code: D97). " + \
				  "This is a bug; please report it" % str(type(self.Formula))[6:-1])
		return NumProblemValue_Bug

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		raise TypeError("Not allowed to set value of a CalcNumValueItem directly")

	def GetMyUnit(self):  # returns human-readable unit name (rich str)
		if self.Formula is None: # formula not defined
			return NullUnit
		assert isinstance(self.Formula.Unit, UnitItem)
		return self.Formula.Unit.HumanName

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a CalcNumValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)


class NumProblemValue(NumValueItem):  # class of 'values' that prevent completion of a calculation
	# Has several instances representing different kinds of problem
	# PHA models can also define their own instances, e.g. Fault Tree uses one with InternalName = 'OutOfRange'
	HumanName = _('Problem message')
	XMLName = 'Problem'
	AllNumProblemValues = [] # register of all instances
	UserSelectable = False  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, InternalName='NumProblem', **Args):
		NumValueItem.__init__(self)
		self.ID = str(utilities.NextID(NumProblemValue.AllNumProblemValues)) # generate unique ID; stored as str
		NumProblemValue.AllNumProblemValues.append(self) # add this NumProblemValue to register (must be after NextID() call)
		self.InternalName = InternalName # used for messaging
		self.Unit = NullUnit # if asked for unit, it will return problem indicator
		self.ProblemEvent = None # which event in the PHA model caused the problem; used to give user diagnostic messages
		# assign Args to attribs
		for (ThisArg, ThisValue) in Args.items(): setattr(self, ThisArg, ThisValue)

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[]):  # return value of object
		return None

	Value = property(fget=GetMyValue)

NumProblemValue_NoProblem = NumProblemValue('NoProblem')
NumProblemValue_NoProblem.HumanHelp = _('no problem identified')
NumProblemValue_UndefNumValue = NumProblemValue('UndefValue')
NumProblemValue_UndefNumValue.HumanHelp = _('a value in the calculation is not yet defined')
NumProblemValue_BrokenLink = NumProblemValue('BrokenLink')
NumProblemValue_BrokenLink.HumanHelp = _('the source of a link is deleted')
NumProblemValue_Bug = NumProblemValue('Bug')
NumProblemValue_Bug.HumanHelp = _('a bug was encountered in Vizop')
NumProblemValue_Circular = NumProblemValue('Circular')
NumProblemValue_Circular.HumanHelp = _("there's a circular reference in a formula")
NumProblemValue_WrongNoOperands = NumProblemValue('WrongNoOperands')
NumProblemValue_WrongNoOperands.HumanHelp = _('an operator received the wrong number of operands')
NumProblemValue_BadOROperands = NumProblemValue('BadOROperands')
NumProblemValue_BadOROperands.HumanHelp = _("an OR gate can't handle both frequencies and probabilities as inputs")
NumProblemValue_BadANDOperands = NumProblemValue('BadANDOperands')
NumProblemValue_BadANDOperands.HumanHelp = _("an AND gate can't handle more than one frequency input")
NumProblemValue_BadNOROperands = NumProblemValue('BadNOROperands')
NumProblemValue_BadNOROperands.HumanHelp = _("a NOR gate can't accept frequencies as inputs")
NumProblemValue_BadNANDOperands = NumProblemValue('BadNANDOperands')
NumProblemValue_BadNANDOperands.HumanHelp = _("a NAND gate can't accept frequencies as inputs")
NumProblemValue_RRMissingInTolRiskModel = NumProblemValue('RRMissing')
NumProblemValue_RRMissingInTolRiskModel.HumanHelp = _("the risk receptor is not defined in the tolerable risk model")
NumProblemValue_TolRiskNoMatchSevCat = NumProblemValue('NoMatchSeverity')
NumProblemValue_TolRiskNoMatchSevCat.HumanHelp = _("the selected severity is not mentioned in the tolerable risk model")
NumProblemValue_TolRiskNoSelFreq = NumProblemValue('NoMatchFreq')
NumProblemValue_TolRiskNoSelFreq.HumanHelp = _("the tolerable risk model couldn't yield a frequency value")
NumProblemValue_FTSFEUndef = NumProblemValue('FTSFEUndef')
NumProblemValue_FTSFEUndef.HumanHelp = _("no FT event is defined as the SIF failure event")
NumProblemValue_FTOutcomeUndef = NumProblemValue('FTOutcomeUndef')
NumProblemValue_FTOutcomeUndef.HumanHelp = _("no FT event is defined as the outcome")
NumProblemValue_FTNotConnected = NumProblemValue('FTNotConnected')
NumProblemValue_FTNotConnected.HumanHelp = _('the event is not connected to a lower-level event')
NumProblemValue_DivisionByZero = NumProblemValue('DivByZero')
NumProblemValue_DivisionByZero.HumanHelp = _("it would require division by zero")
NumProblemValue_TolRiskUnitMismatch = NumProblemValue('TFUnitMismatch')
NumProblemValue_TolRiskUnitMismatch.HumanHelp = _("units of event frequency and tolerable frequency don't match")

class ValueInfoItem(object): # defines an object used as a wrapper to pass values and associated info resulting from a
	# calculation

	def __init__(self, Value=0.0, Unit=NullUnit, Problem=NumProblemValue_NoProblem, ProblemObj=None):
		object.__init__(self)
		assert isinstance(Value, (str, float)) # str is used when the value is meant for display
		assert isinstance(Unit, UnitItem)
		assert isinstance(Problem, NumProblemValue)
		self.Value = Value
		self.Unit = Unit
		self.Problem = Problem
		self.ProblemObj = ProblemObj

# class SwitchNumValueItem(NumValueItem): # class of values that are determined by checking against a series of yes/no conditions
# deferred until later version of Vizop
#	HumanName = _('Switch')
#	XMLName = 'Switch'
#	UserSelectable = True # whether user can manually select this class when assigning a value to a PHA object
#
#	def __init__(self, **Args):
#		object.__init__(self)
#		self.DefaultValue = None # value returned if all the Routes return False
#		self.Routes = [] # list of tuples: (SwitchItem, NumValueItem). Each SwitchItem is tested in turn; if True, returns respective NumValueItem

class LookupNumValueItem(NumValueItem): # class of values found by reference to a lookup table
	HumanName = _('Matrix lookup')
	XMLName = 'Lookup'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self)
		self.LookupTable = None # instance of LookupTableItem
		self.InputValue = None # instance of NumValueItem subclass; the value to look up in the table
		# TODO: need to develop for multidimensional lookup (currently only 1-D)

	def GetMyValue(self, RR=DefaultRiskReceptor, **args):  # return value from lookup table
		if (not self.LookupTable) or (self.InputValue is None): return NumProblemValue_UndefNumValue
		assert isinstance(self.InputValue, NumValueItem)
		assert not isinstance(self.InputValue.Value, NumProblemValue)
		return self.LookupTable.Value(RR, self.InputValue.Value, **args)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		raise TypeError("Not allowed to set value of a LookupNumValueItem directly")

	def GetMyUnit(self): # returns unit (instance of UnitItem) looked up from LookupTable,
		# or NullUnit if LookupTable isn't defined%%%
		if self.LookupTable:
			assert isinstance(self.LookupTable, LookupTableItem)
			print("CC661 LookupValueItem GetMyUnit needs to look up the unit of the output value, not coded")
	#		Unit = self.LookupTable.OutputUnit
			assert isinstance(Unit, UnitItem)
			return Unit.HumanName
		else: return NullUnit

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a LookupNumValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

	def GetMyAcceptableUnits(self): # return list of UnitItems permitted for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		if self.LookupTable is None: return []
		else: return self.LookupTable.MyUnitKind.AcceptableUnits

	def SetMyAcceptableUnits(self, NewAcceptableUnits, **Args): # set acceptable units for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		raise TypeError('CC912 Not allowed to set units of LookupNumValueItem')
		return False

class CategoryNameItem(NumValueItem): # class of objects defining one of a list of categories
	# Used for lookup in a matrix. Example: a severity value
	HumanName = _('Categories')
	XMLName = 'Category'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object
	InvalidIndicator = '!' # string passed to Viewport to indicate category is invalid

	def __init__(self, XMLName='', HumanName='', HumanDescription='', **Attribs):
		NumValueItem.__init__(self)
		self.XMLName = XMLName # identifier for this category used in an XML string
		self.HumanName = HumanName # human-readable identifier for this category
		self.HumanDescription = HumanDescription # human-readable detailed definition of this category
		self.LookupTable = None # instance of LookupTableItem
		self.DimensionName = None # name of dimension to use in LookupTable
		self.IsUndefined = False # whether this category is the "undefined" category in its hosting list of categories
		self.MyValue = {DefaultRiskReceptor: None} # value currently selected from dimension in LookupTable
		self.MinValue = {DefaultRiskReceptor: UserNumValueItem()} # min and max numerical values of the parameter to
			# which this category refers, e.g. alarm available response time
		self.MaxValue = {DefaultRiskReceptor: UserNumValueItem()}
		for ThisAttrib in Attribs: setattr(self, ThisAttrib, Attribs[ThisAttrib])

#	def GetMyValue(self, RR=DefaultRiskReceptor, **args):  # return value from lookup table
#		# check status; if value not valid, return an indicator
#		print "CC613 checking status. self.ValueFamily: ", self.ValueFamily
#		if self.Status(RR) != NumProblemValue_NoProblem: return CategoryNameItem.InvalidIndicator
#		assert isinstance(RR, RiskReceptorItem)
#		assert isinstance(self.LookupTable, LookupTableItem)
#		assert isinstance(self.DimensionName, str)
#		assert self.DimensionName in self.LookupTable.DimensionHumanNames
#		# check that MyValue is in the list of values in the lookup table
#		assert self.MyValue[RR] in self.LookupTable[RR][self.LookupTable.DimensionHumanNames.index(self.DimensionName)]
#		return self.MyValue[RR]

#	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor):
#		assert isinstance(RR, RiskReceptorItem)
#		assert isinstance(self.LookupTable, LookupTableItem)
#		assert isinstance(self.DimensionName, str)
#		assert self.DimensionName in self.LookupTable.DimensionHumanNames
#		# check that NewValue is in the list of values in the lookup table
#		assert self.MyValue[RR] in self.LookupTable.Keys[RR][self.LookupTable.DimensionHumanNames.index(self.DimensionName)]
#		self.MyValue[RR] = NewValue

#	def GetMyUnit(self):  # returns human-readable unit name (rich str)
#		assert isinstance(self.LookupTable, LookupTableItem)
#		assert isinstance(self.DimensionName, str)
#		assert self.DimensionName in self.LookupTable.DimensionHumanNames
#		return self.LookupTable.DimensionUnits[self.LookupTable.DimensionHumanNames.index(self.DimensionName)].HumanName

#	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
#		raise TypeError("Not allowed to set unit of a CategoryNameItem directly")

#	def Status(self, RR=DefaultRiskReceptor): # return NumProblemValue instance indicating status of Value
#		if (not self.LookupTable) or (self.DimensionName is None) or (self.MyValue is None):
#			return NumProblemValue_UndefNumValue
#		else: return NumProblemValue_NoProblem

#	Value = property(fget=GetMyValue, fset=SetMyValue)
#	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

class AutoNumValueItem(NumValueItem): # class of values that are calculated by a method in some other class
	HumanName = _('Calculated')
	XMLName = 'Calculated'
	UserSelectable = False  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self, **Args)
		self.Calculator = None # method used to return value
		self.UnitGetter = None # method used to return unit. When setting it, remember to set StatusGetter as well
		self.StatusGetter = None # method used to return status
		self.DefaultValue = None

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], **Args):  # return value of object
		if self.Calculator is None:
			if self.DefaultValue is None: # we hit a bug, the calculator and default value haven't been defined
				return NumProblemValue_Bug
			return self.DefaultValue
		# pack FormulaAntecedents into Args, so that Calculator doesn't have to explicitly name it as an arg
		Args['FormulaAntecedents'] = FormulaAntecedents
		return self.Calculator(RR, **Args)

	def GetMyUnit(self, **Args): # return unit obtained from object
		if self.UnitGetter is None: return NullUnit
		else: return self.UnitGetter(**Args)

	def GetMyUserDefinedUnit(self, **Args): # return unit defined by user. This is intended as a "UnitGetter" method
		# for AutoNumValueItem instances where the user is allowed to control the unit
		return super(AutoNumValueItem, self).GetMyUnit(**Args)

	def Status(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], **args):
		# return NumProblemValue item indicating status of value
		if RR.HumanName == 'Default': print('CC1013 warning, checking AutoNumValue status with default RR') # for debugging
		return self.StatusGetter(RR, **args)

class ParentNumValueItem(NumValueItem): # a NumValueItem whose value was copied from a parent, but is not linked to it
	HumanName = _('Copied from another value')
	XMLName = 'Copied'
	UserSelectable = True # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self)
		# numerical values per risk receptor. Must include DefaultRiskReceptor key
		self.ValueFamily = {DefaultRiskReceptor: 0.0}
		# parent object (eg a PHA cause) containing the NumValueItem that this item was originally copied from
		self.ParentPHAObj = None

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], **args): # return value of object
		if self.ParentPHAObj is None:
			return NumProblemValue_BrokenLink # parent object not defined, can't follow link
		return self.ParentPHAObj.Value.Value(RR, FormulaAntecedents, **args)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		# (it should be replaced with another NumValueItem class instance instead)
		raise TypeError("Not allowed to set value of a ParentNumValueItem directly")

	def GetMyUnit(self):  # returns human-readable unit name (rich str)
		if self.ParentPHAObj is None: # parent object not defined, can't follow link
			return NullUnit
		return self.ParentPHAObj.Value.Unit.HumanName

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a ParentNumValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

	def GetMyAcceptableUnits(self): # return list of UnitItems permitted for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		if self.ParentPHAObj is None: return []
		else: return self.ParentPHAObj.MyUnitKind.AcceptableUnits

	def SetMyAcceptableUnits(self, NewAcceptableUnits, **Args): # set acceptable units for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		raise TypeError('CC1050 Not allowed to set units of ParentNumValueItem')
#		return False

	def Status(self, RR=DefaultRiskReceptor, **Args): # return NumProblemValue item indicating status of value
		# status is derived from the parent number object
		if self.ParentPHAObj is None: return NumProblemValue_BrokenLink
		else: return self.ParentPHAObj.Value.Status(RR=RR, **Args)

class UseParentValueItem(NumValueItem):
	# class indicating values are to be linked from a parent PHA object, such as a cause or a calculated value
	HumanName = _('Linked from another value')
	XMLName = 'LinkedFrom'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self)
		self.ParentPHAObj = None  # parent object (eg a PHA cause) containing the NumValueItem that this item is linked to

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], **Args): # return value of object
		if self.ParentPHAObj is None:
			return NumProblemValue_BrokenLink # parent object not defined, can't follow link
		return self.ParentPHAObj.Value.GetMyValue(RR, FormulaAntecedents, **Args)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		# (it should be replaced with another NumValueItem class instance instead)
		raise TypeError("Not allowed to set value of a UseParentValueItem directly")

	def GetMyUnit(self):  # returns unit (UnitItem instance) of parent PHA object, if defined, else NullUnit
		if self.ParentPHAObj is None: # parent object not defined, can't follow link
			return NullUnit
		return self.ParentPHAObj.Value.Unit

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a UseParentValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

	def GetMyAcceptableUnits(self): # return list of UnitItems permitted for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		if self.ParentPHAObj is None: return []
		else: return self.ParentPHAObj.MyUnitKind.AcceptableUnits

	def SetMyAcceptableUnits(self, NewAcceptableUnits, **Args): # set acceptable units for display of this value.
		# Access this function through self.AcceptableUnits, via the property() statement in the superclass.
		raise TypeError('CC1090 Not allowed to set units of UseParentNumValueItem')
#		return False

	def Status(self, RR=DefaultRiskReceptor, **Args): # return NumProblemValue item indicating status of value
		# status is derived from the parent number object
		if self.ParentPHAObj is None: return NumProblemValue_BrokenLink
		else: return self.ParentPHAObj.Value.Status(RR=RR, **Args)

NumValueClasses = [UserNumValueItem, ConstNumValueItem, CalcNumValueItem, NumProblemValue, LookupNumValueItem,
	AutoNumValueItem, ParentNumValueItem, UseParentValueItem]
NumValueClassesToCheckValid = (UserNumValueItem, ConstNumValueItem, LookupNumValueItem,
	ParentNumValueItem, UseParentValueItem) # only these classes are checked in CheckValue() methods
	# this is a tuple, not a list, so it can be used directly in isinstance()
NumValueClassHumanNames = [c.HumanName for c in NumValueClasses] # list of names used in choice box
NumValueKindHash = dict( (c.XMLName, c) for c in NumValueClasses )

class LookupTableItem(object):
	# class of tables containing values that can be looked up by reference to a key value
	# The values are assumed to support all risk receptors, so there's no explicit handling of RR's here

	def __init__(self, ID):
		assert isinstance(ID, str)
		assert ID # ensure it's not blank
		object.__init__(self)
		self.ID = ID
		self.HumanName = ''
		self.HowManyDimensions = 1
		self.DimensionHumanNames = [] # list of str, one per dimension
		self.DimensionUnits = [] # list of UnitItem, one per dimension. Redundant, as units are stored in Values
		# Keys: list of lists of key value objects (CategoryNameItem instances) - one inner list per dimension
		# Example: [ [SlightItem, ModerateItem, SevereItem], [RareItem, ...etc] ]
		self.Keys = [ [] ]
		# Values: nested lists of value objects (subclasses of NumItem). Nesting depth = no of dimensions.
		# Top level list is for categories in 1st dimension; next level for 2nd dimension, etc.
		# Number of lists at each depth = number of categories in that dimension (eg. number of top level lists =
		# number of categories in 1st dimension)
		# e.g. for 3 dimensions: [ [ [D1C1;D2C1;D3C1 , D1C1;D2C1;D3C2 ... ], [D1C1;D2C2;D3C1 , D1C1;D2C2;D3C2 ... ] ],
		# and more lists for D1C2, D1C3 etc ]
		self.Values = []
		self.DefaultValue = NumProblemValue_UndefNumValue # value returned if lookup cannot be achieved
		self.NoMatchBehaviour = 'Return-default' # behaviour if supplied key not found in Keys. Permitted values:
		# 'Return-default': return DefaultValue
		# 'Round-up', 'Round-down': match to next higher/lower Key (if out of range of Keys, Under/OverrangeValue will be returned)
		self.UnderrangeValue = self.OverrangeValue = NumProblemValue_UndefNumValue  # value returned if supplied key is out of range of Keys
		self.CaseSensitive = False # whether text match to key is case sensitive
		self.MatchPrecisionMin = 0.99 # min ratio of search value to key, to consider it "equal" and therefore matched
		self.MatchPrecisionMax = 1.01
		self.SeverityDimensionIndex = None # which dimension contains severity values, counting from 0

	def Matched(self, x, y):  # return bool - whether x and y (numerical values) are considered equal (TODO move to top level so it can also be used by SwitchItem)
		# handle case where y is zero, so ratio can't be calculated
		if abs(y) < info.ZeroThreshold: return (abs(x) < info.ZeroThreshold)  # true if x is also zero
		return (x / y < self.MatchPrecisionMax) and (x / y > self.MatchPrecisionMin)

	def Lookup(self, Categories=[]):
		# look up in table, get value item matching Categories (list of category objects, one per dimension)
		assert len(Categories) == self.HowManyDimensions
		for ThisCatIndex, ThisCategory in enumerate(Categories): assert ThisCategory in self.Keys[ThisCatIndex]
		# step through levels in self.Values, fetching lists of values at each depth according to category keys supplied
		ThisLevelResult = self.Values[:]
		for DimensionIndex in range(0, self.HowManyDimensions):
			# get the n'th sublist where n is the index of the requested category in this dimension
			ThisLevelResult = ThisLevelResult[self.Keys[DimensionIndex].index(Categories[DimensionIndex])]
		return ThisLevelResult

	def GetMyValue_Old(self, InputKey, RR=DefaultRiskReceptor):
		# Look up value from matrix. InputKey is list of values (str or float) to look up in each dimension
		# returns value looked up
		# Old version - based on looking up numerical values and determining which category to select
		# check whether specified risk receptor (RR) is in the table
		if RR not in self.Keys: RR = DefaultRiskReceptor
		# is it a text match?
		if isinstance(self.Keys[RR][0], str): # FIXME this and subsequent lines will only work for 1D
			assert isinstance(InputKey, str)
			SearchKeys = copy.copy(self.Keys[RR])  # work on a copy so that the next line doesn't mangle the table
			if self.CaseSensitive:
				SearchKeys = [s.upper() for s in SearchKeys]  # convert all keys to uppercase
				InputKey = InputKey.upper()
			# InputKey found?
			if InputKey in SearchKeys:
				return self.Values[RR][SearchKeys.index(InputKey)]
			else:
				return DefaultValue
		else:  # numeric match
			# test for exact match
			ExactMatch = [self.Matched(InputKey, k) for k in self.Keys[RR]]
			if True in ExactMatch: return self.Values[RR][ExactMatch.index(True)]
			# test for out of range
			if InputKey < self.Keys[RR][0]: return self.UnderrangeValue
			if InputKey > self.Keys[RR][-1]: return self.OverrangeValue
			# handle value that is in range, but doesn't exactly match a key in the table
			if self.NoMatchBehaviour == 'Return-default': return self.DefaultValue
			# find the point at which the InputKey crosses the Keys
			FirstGreaterKeyIndex = [(k > InputKey) for k in self.Keys[RR]].index(True)
			# if rounding down, we'll use the key just before the cross point
			if self.NoMatchBehaviour == 'Round-down': FirstGreaterKeyIndex -= 1
			return self.Values[RR][FirstGreaterKeyIndex]


#class SwitchItem(object): # decision item used by SwitchNumValueItem
# for future implementation
#	def __init__(self):
#		Formula = None # FormulaItem instance whose value is calculated to test the condition
#		Comparator = None # ComparatorItem used for boolean test
#		Threshold = None # NumValueItem tested against


class TextStyleItem(object):  # defines default and initial character style of text.
	# Used as an attribute of other objects in conjunction with a rich string

	def __init__(self):
		object.__init__(self)
		# default values below are used in DefaultTextStyleItem. If we don't want that, change when defining DefaultTextStyleItem
		self.Bold = False
		self.Italic = False
		self.Underlined = 'Nil'  # can be 'Nil', 'Single' or 'Double' (in future, may add others such as 'Dotted')
		self.Font = None  # ProjectFontItem instance
		self.Size = 12  # point size at 100% zoom
		self.Spacing = 100  # % of normal spacing of characters
		# (0 = totally overlapping, 100 = normal, 200 = twice the normal space between left edges)
		self.VertOffset = 0  # no offset from baseline


class IPLKindItem(
	object):  # defines categories of IPLs such as "relief valve", with parameters that can be applied as defaults to IPL instances
	# Actual IPLs are instances of other classes such as IPLItem, not of this class

	def __init__(self, HumanName='<undefined>', DefaultValue=None):
		object.__init__(self)
		self.HumanName = HumanName
		self.DefaultValue = DefaultValue # should be an instance of ConstantNumItem


class CauseKindItem(
	object):  # defines categories of Causes such as "control loop failure", with parameters that can be applied as defaults to Cause instances
	# Actual Causes are instances of other classes (TBD), not of this class

	def __init__(self, HumanName='<undefined>', DefaultValue=None):
		object.__init__(self)
		self.HumanName = HumanName
		self.DefaultValue = DefaultValue # should be an instance of ConstantNumItem


class PHAModelMetaClass(type): # a class used to build a list of PHAModel classes.
	# When a class with metaclass == this class is initialized, this class's __init__ procedure is run.
	PHAModelClasses = [] # for list of PHAModel classes

	def __init__(self, name, bases, dic):
		type.__init__(type, name, bases, dic)
		# add new PHAModel class to the list, except the base class
		if not self.IsBaseClass:
			PHAModelMetaClass.PHAModelClasses.append(self)

class PHAModelBaseClass(object, metaclass=PHAModelMetaClass):
	# base class for all PHA objects such as fault tree or HAZOP
	AllPHAModelObjects = [] # register of all PHA object instances defined
	CanBeCreatedManually = True # whether user can be invited to create a PHAModel of this class.
	IsBaseClass = True # needed by metaclass. Subclasses should set this to False

	def __init__(self, Proj, **Args):
		# if ID is supplied as an arg, reapply it as existing ID, else fetch a new ID
		object.__init__(self)
		if 'ID' in Args.keys():
			assert isinstance(Args['ID'], str)
			assert Args['ID'] # ensure it's not blank
			self.ID = Args['ID']
		else: self.ID = Proj.GetNewID() # find next available ID
		PHAModelBaseClass.AllPHAModelObjects.append(self) # add instance to register; must do after assigning self.ID
		self.Proj = Proj
		self.Viewports = [] # list of Viewport shadow instances for this PHA model instance
		self.EditAllowed = True
		# capture any attribs provided in Args (risky, no checks performed)
		self.__dict__.update(Args)

class MilestoneItem(object): # item storing info required for navigation back/forwards, and for reverting display on undo
	def __init__(self, Proj, **Args):
		AttribInfo = [ ('Displayable', bool), ('Zoom', (int, float)), ('PanX', (int, float)), ('PanY', (int, float)) ]
		for AttribName, AttribType in AttribInfo:
			if AttribName in Args: assert isinstance(Args[AttribName], AttribType)
		object.__init__(self)
		self.ID = Proj.GetNewID() # find next available ID
		self.Proj = Proj
		self.Displayable = Args.get('Displayable', True) # whether the user is allowed to navigate to this milestone.
			# If it's only for Undo purposes, Displayable may be False.
		self.Viewport = Args.get('Viewport', None) # which Viewport to display on the display device
		if hasattr(self.Viewport, 'GetMilestoneData'):
			self.ViewportData = self.Viewport.GetMilestoneData()
		else: self.ViewportData = {}
		self.DisplDevice = Args.get('DisplDevice', None) # which display device was showing the Viewport
		self.Zoom = int(round(Args.get('Zoom', 100))) # Zoom value to apply on the Viewport
		self.PanX = int(round(Args.get('PanX', 0))) # Pan value to apply on the Viewport
		self.PanY = int(round(Args.get('PanY', 0))) # Pan value to apply on the Viewport
		self.IsZoomChange = Args.get('IsZoomChange', False) # True if this object is a change of zoom in the same Viewport, all other attribs unchanged except Pan
		self.IsPanChange = Args.get('IsPanChange', False) # True if this object is a change of pan in the same Viewport, all other attribs unchanged except Zoom

class RootCauseItem(object):  # class of PHA events that are root/initiating causes
	# Numbering is defined not here, but in subclasses, as it is unlikely to be the same between various PHA models

	def __init__(self):
		object.__init__(self)
		self.RootCauseGroups = []  # list of groups, TODO define class of group item
		self.Comments = []  # AssociatedTextItem instances
		self.Recommendations = []  # AssociatedTextItem instances
		self.Kinds = []  # items from CauseKinds, an attribute of Project
		self.Text = None  # instance of TextItem class; contains rich text describing the cause
		self.LinkedTo = []  # list of LinkItem instances
		self.Value = None  # NumValueItem subclass instance: the frequency of the item


class NumberingItem(object):
	# defines the numbering applied to a PHA object. Consists of a series of chunks that are concatenated to make the
	# required number for display.
	# Chunks can be strings (eg separators), a PHA object to take the number from (eg node number from a HAZOPNodeItem),
	# or a serial number per item.
	# Only 0 or 1 serial chunks allowed.

	def __init__(self):
		object.__init__(self)
		self.NumberStructure = [] # list of numbering chunks, see comment just above; instances of types listed in
		#	NumberChunkTypes
		self.ShowInDisplay = True # whether number is displayed in Viewport
		self.ShowInOutput = True # whether number is displayed in PHA model export

	def __eq__(self, other): # returns True if self and other (a NumberingItem instance) are considered identical
		# this method allows comparison of NumberingItem instances simply by (Instance1 == Instance2)
		assert isinstance(other, NumberingItem)
		if self is other: return True # if comparing the same object, no further checks
		# compare NumberStructure contents of self and other
		Match = len(self.NumberStructure) == len(other.NumberStructure)
		ThisIndex = 0
		while Match and (ThisIndex < len(self.NumberStructure)):
			ThisItemInSelf = self.NumberStructure[ThisIndex]
			ThisItemInOther = other.NumberStructure[ThisIndex]
			# each item can be str, ParentNumberChunkItem or SerialNumberChunkItem. Check their types and contents match
			Match = (ThisItemInSelf == ThisItemInOther) if isinstance(ThisItemInOther, type(ThisItemInSelf)) else False
			ThisIndex += 1
		return Match and (self.ShowInDisplay == other.ShowInDisplay) and (self.ShowInOutput == other.ShowInOutput)

	def HumanValue(self, PHAItem, Host, Levels=999, PHAObjectsReferenced=[]):
		# get the number for display for PHAItem.
		# Host = iterable containing all similar PHA items to consider in serial numbering at lowest level
		# NumberingItem instances in PHAItem instances within Host should be called Numbering, else serial numbering
		# won't work properly
		# returns (string containing the number as displayed, number of numerical chunks returned (int))
		# returns only the last <Levels> numerical items (not counting string chunks, which are assumed to be separators)
		# PHAObjectsReferenced is for circular reference trapping
		NumString = '' # build up the number string chunkwise
		NumChunksAdded = 0 # counter for numerical chunks added
		for Chunk in [self.NumberStructure[-Index] for Index in
					  range(len(self.NumberStructure))]:  # work through list of chunks in reverse
			if type(Chunk) is str:
				NumString = Chunk + NumString # prepend string chunk as-is
			elif type(Chunk) is ParentNumberChunkItem:
				(ParentChunk, LevelsAdded) = Chunk.Result(Levels=Levels - NumChunksAdded,
					PHAObjectsReferenced=PHAObjectsReferenced)
				NumString = ParentChunk + NumString
				NumChunksAdded += LevelsAdded
			elif type(Chunk) is SerialNumberChunkItem:
				NumString = str(Chunk.GetMyNumber(PHAItem, Host)) + NumString
				NumChunksAdded += 1
			else:  # unrecognised chunk type
				NumString = '<?>' + NumString
				NumChunksAdded += 1
				print("Oops, unrecognised numbering chunk type '%s' (problem code DA664). This is a bug; please report it" % str(
					type(Chunk)))
			if NumChunksAdded >= Levels: break # stop when enough chunks have been added
		return (NumString, NumChunksAdded)

	def GetSerialChunk(self): # return serial number chunk of this NumberingItem instance, or None if there isn't any
		ChunkTypes = [type(Chunk) for Chunk in self.NumberStructure]
		if SerialNumberChunkItem in ChunkTypes: # find serial chunk, if any
			return self.NumberStructure[ChunkTypes.index(SerialNumberChunkItem)]
		else:
			return None

	def GetSerialValue(self, PHAItem):  # return value of serial chunk of PHAItem, or None if there isn't one
		ChunkTypes = [type(Chunk) for Chunk in self.NumberStructure]  # find serial chunk, if any
		if SerialNumberChunkItem in ChunkTypes:
			return self.NumberStructure[ChunkTypes.index(SerialNumberChunkItem)].Result(PHAItem)
		else:
			return None

#	def SetSerialValue(self,
#					   InputValue):  # set initial value of any serial chunk to InputValue (int). Do nothing if there's no serial chunk
#		ChunkTypes = [type(Chunk) for Chunk in self.NumberStructure]  # find serial chunk, if any
#		if SerialNumberChunkItem in ChunkTypes: self.NumberStructure[
#			ChunkTypes.index(SerialNumberChunkItem)].InitialValue = InputValue
#
#	Serial = property(fget=GetSerialValue, fset=SetSerialValue)

class StrNumberChunkItem(object):
	# a chunk in a NumberingItem instance, that inserts a fixed string
	XMLName = info.NumberSystemStringType

	def __init__(self):
		object.__init__(self)
		self.Value = ''

class ParentNumberChunkItem(object):
	# a chunk in a NumberingItem instance, that takes numbering from a PHA object (eg node, cause).
	XMLName = info.NumberSystemParentType

	def __init__(self):
		object.__init__(self)
		self.Source = None # (str) PHA item instance to take numbering from
		# Note: If Source is any object other than a PHA element, update projects.ReconnectParentNumberChunks()
		self.HierarchyLevels = 999 # (int) how many levels of numbering to return.
			# If <=1, only return the serial number of the Source item

	def __eq__(self, other):
		assert isinstance(other, ParentNumberChunkItem)
		return (self.Source == other.Source) and (self.HierarchyLevels == other.HierarchyLevels)

	def GetMyNumber(self, PHAObjectsReferenced=[]): # Gets number of Source
		# returns tuple: (self.Source's number (limited to the last <Levels> numerical items), how many levels returned)
		# PHAObjectsReferenced is for circular reference trapping
		if self.Source:
			if hasattr(self.Source, 'Number'):
				if self.Source not in PHAObjectsReferenced: # circular reference checking
					return self.Source.Number.HumanValue(PHAItem=self.Source, Levels=self.HierarchyLevels,
														 PHAObjectsReferenced=PHAObjectsReferenced + [Source])
				else:
					return (_('<circular ref>'), Levels)
			else:
				return (_('<no number>'), 0)
		else:
			return (_('<no source>'), 0)

	Result = property(fget=GetMyNumber)

class SerialNumberChunkItem(object):  # a chunk in a NumberingItem instance, that provides a serial number for a PHA object
	XMLName = info.NumberSystemSerialType

	def __init__(self):
		object.__init__(self)
		self.FieldWidth = 3  # (int) how many digits to return
		self.PadChar = '0'  # (str) left padding to use in returned number to fill up FieldWidth
		self.StartSequenceAt = 1 # (int) number to return for first item in sequence
		self.SkipTo = None # if defined (int), returns this number if greater than position in sequence
			# (taking GapBefore into account)
		self.GapBefore = 0 # (int >= 0) how many unused values to leave before this item
		self.IncludeInNumbering = True # (bool) whether to count this item in serial numbering
			# (if False, GetMyNumber() returns NoValue string)
		self.NoValue = '- -' # (str) value returned if IncludeInNumbering is False

	def __eq__(self, other):
		assert isinstance(other, SerialNumberChunkItem)
		AttribsToCompare = ['FieldWidth', 'PadChar', 'StartSequenceAt', 'SkipTo', 'GapBefore', 'IncludeInNumbering', 'NoValue']
		return False not in [ (getattr(self, AttribName) == getattr(other, AttribName) for AttribName in AttribsToCompare) ]

	def GetMyNumber(self, PHAItem=None, Host=None, NoValue='- -'):
		# Returns serial number of PHAItem within Host (iterable), suitably padded
		# NoValue (str): returns this value if self.IncludeInNumbering is False
		if PHAItem:
			if self.IncludeInNumbering:
				if PHAItem in Host:
					assert isinstance(self.StartSequenceAt, int)
					assert isinstance(self.SkipTo, int) or (self.SkipTo is None)
					assert isinstance(self.GapBefore, int)
					assert self.GapBefore >= 0
					NumberSoFar = self.StartSequenceAt - 1
					for ThisPHAItem in Host[:Host.index(PHAItem) + 1]: # refer to all PHAItems up to and including this one
						ThisNumberingObj = getattr(ThisPHAItem, 'Numbering', None)
						if ThisNumberingObj is None: # can't refer to numbering objects of previous items; just provide simple count
							print("Warning, misnamed numbering object (problem code CC991)")
							NumberSoFar += 1
						else: # numbering object found; check its SkipTo, IncludeInNumbering and GapBefore attribs
							ThisSerialChunk = ThisNumberingObj.GetSerialChunk() # find any serial chunk in this item
							if getattr(ThisSerialChunk, 'IncludeInNumbering', False):
								if ThisSerialChunk.SkipTo is None: ThisSkipTo = NumberSoFar # ignoring SkipTo
								else: ThisSkipTo = ThisSerialChunk.SkipTo
								NumberSoFar = max(NumberSoFar + 1, ThisSkipTo) + ThisSerialChunk.GapBefore
					Serial = NumberSoFar
				else:  # PHAItem isn't in its host list, that's a bug
					Serial = self.FieldWidth * '?'
					print("Oops, PHA item not found in its host list (problem code CC723). This is a bug; please report it")
					raise ValueError
			else: return NoValue # IncludeInNumbering is False
		else:  # no PHAItem defined
			Serial = self.FieldWidth * '?'
			print("Oops, PHA item not defined in numbering scheme (problem code CC726). This is a bug; please report it")
		return Serial

NumberChunkTypes = [StrNumberChunkItem, ParentNumberChunkItem, SerialNumberChunkItem]

class NumberSystem(object):  # superclass of numbering systems such as 1/2/3, a/b/c, I/II/III
	# Only classes are invoked, not instances, so there's no __init__ method
	@classmethod
	def TargetFieldWidth(cls, MaxValue=0):
		# returns no of digits corresponding to MaxValue. e.g. ArabicNumberSystem.TargetFieldWidth(10) returns 2.
		# For MaxValue == 0, returns 1.
		# If MaxValue < 0, considers abs(MaxValue) only, i.e. no allowance for '-' sign.
		# Overridden for RomanNumberSystem
		assert isinstance(MaxValue, int)
		if MaxValue == 0: return 1
		else: return int(math.log(abs(MaxValue) - int(not cls.HasZero)) // cls.LogDigits) + 1

class ArabicNumberSystem(NumberSystem):  # decimal number system using 0/1/2...

	HumanName = _('Arabic (1, 2...)')  # human-readable name of the numbering system
	Digits = '0 1 2 3 4 5 6 7 8 9'.split()
	LogDigits = math.log(len(Digits))
	MinValue = 0  # min and max acceptable value in terms of int equivalent
	MaxValue = 9999
	StartIndex = 1  # digits in higher placeholders (not the 'units' digit) start from index 1 (eg ten = 10 not 00)
	StartValue = 1
	PadChar = '0' # default left-padding character for use in serial chunks of NumberingItem instances
	HasZero = True # whether the first digit represents zero

	@staticmethod
	def HumanValue(TargetValue=0, FieldWidth=1):
		# returns string representation of TargetValue (int) in the numbering system, left-padded to required width
		return utilities.Pad(str(min(ArabicNumberSystem.MaxValue, max(ArabicNumberSystem.MinValue, int(TargetValue)))),
			FieldWidth=FieldWidth, PadChar=ArabicNumberSystem.PadChar)


class SequenceNumberSystem(NumberSystem):  # number system using any sequence of digits, eg a/b/c...
	# to write a class for a different sequence, it should be sufficient to define only HumanName and Digits

	MinValue = 0 # min and max acceptable value in terms of int equivalent
	MaxValue = 99999999
	StartIndex = 0
	StartValue = 0
	PadChar = ' '
	HasZero = False # whether the first digit represents zero

	@classmethod
	def HumanValue(cls, TargetValue=0, FieldWidth=1):
		# returns string representation of TargetValue (int) in the numbering system, left-padded to required width
		Remainder = min(cls.MaxValue, max(cls.MinValue, TargetValue))
		Result = ''  # build up result string
		ZeroAdj = int(not cls.HasZero) # adjustment term needed if number system has no zero; either 0 or 1
		# work through significant digits from lowest to highest
		while Remainder:
			ThisDigitValue = ZeroAdj + int((Remainder - ZeroAdj) % cls.Base) # get least significant digit
			Result = cls.Digits[ThisDigitValue - ZeroAdj] + Result # prepend it to Result
			Remainder = (Remainder - ThisDigitValue) / cls.Base # deduct value of last digit from Remainder
		return utilities.Pad(Result, FieldWidth=FieldWidth, PadChar=cls.PadChar)

class LowerCaseLetterNumberSystem(SequenceNumberSystem): # number system using a/b/c...
	HumanName = _('Lower case (a, b...)')
	Digits = [chr(x) for x in range(ord('a'), ord('z') + 1)]
	LogDigits = math.log(len(Digits))
	Base = len(Digits)
	MinValue = 1

class UpperCaseLetterNumberSystem(SequenceNumberSystem): # number system using A/B/C...
	# this is used to generate column names for Excel spreadsheets
	HumanName = _('Upper case (A, B...)')
	Digits = [chr(x) for x in range(ord('A'), ord('Z') + 1)]
	LogDigits = math.log(len(Digits))
	Base = len(Digits)
	MinValue = 1

class RomanNumberSystem(NumberSystem):
	MinValue = 1 # min and max acceptable value in terms of int equivalent
	MaxValue = 4999
	PadChar = ' '
	HasZero = False # whether the first value (I) represents zero

	@classmethod
	def HumanValue(cls, TargetValue=0, FieldWidth=1):
		# returns string representation of TargetValue (int) in the numbering system, left-padded to required width
		# make string for each part of the number
		Remainder = TargetValue
		HowManyThousands = int(Remainder // 1000)
		Thousands = cls.ThousandSymbol * HowManyThousands
		Remainder -= (1000 * HowManyThousands)
		HowManyHundreds = int(Remainder // 100)
		Hundreds = cls.HundredSequence[HowManyHundreds]
		Remainder -= (100 * HowManyHundreds)
		HowManyTens = int(Remainder // 10)
		Tens = cls.TenSequence[HowManyTens]
		HowManyUnits = Remainder - (10 * HowManyTens)
		Units = cls.UnitSequence[HowManyUnits]
		return utilities.Pad(Thousands + Hundreds + Tens + Units, FieldWidth=FieldWidth, PadChar=cls.PadChar)

	@classmethod
	def TargetFieldWidth(cls, MaxValue=0):
		# returns no of digits corresponding to MaxValue. e.g. TargetFieldWidth(16) returns 4, because the longest
		# number in the range 1..16 is 8 (VIII), which has 4 digits.
		# For MaxValue == 0, returns 1.
		# If MaxValue < 0, considers abs(MaxValue) only, i.e. no allowance for '-' sign.
		assert isinstance(MaxValue, int)
		if MaxValue == 0: return 1
		else: return max([len(cls.HumanValue(n)) for n in range(1, abs(MaxValue) + 1)])

class UpperCaseRomanNumberSystem(RomanNumberSystem):
	HumanName = _('Roman (I, II...)')
	ThousandSymbol = 'M'
	HundredSequence = ['', 'C', 'CC', 'CCC', 'CD', 'D', 'DC', 'DCC', 'DCCC', 'CM']
	TenSequence = ['', 'X', 'XX', 'XXX', 'XL', 'L', 'LX', 'LXX', 'LXXX', 'XC']
	UnitSequence = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']

class LowerCaseRomanNumberSystem(RomanNumberSystem):
	HumanName = _('Roman (i, ii...)')
	ThousandSymbol = 'm'
	HundredSequence = ['', 'c', 'cc', 'ccc', 'cd', 'd', 'dc', 'dcc', 'dccc', 'cm']
	TenSequence = ['', 'x', 'xx', 'xxx', 'xl', 'l', 'lx', 'lxx', 'lxxx', 'xc']
	UnitSequence = ['', 'i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix']

NumberSystems = [ArabicNumberSystem, LowerCaseLetterNumberSystem, UpperCaseLetterNumberSystem,
	UpperCaseRomanNumberSystem, LowerCaseRomanNumberSystem]

class TextItem(object):  # text forming part of a PHA object, such as a description
	DefaultTextHorizAlignment = 'Centre'
	DefaultTextVertAlignment = 'Centre'

	def __init__(self, Proj, PHAObjClass=None, Host=None):
		# PHAObjectClass is the class of PHA object with which the text is associated
		# Host: the parent PHA object (e.g. FTEvent) - not currently used
		object.__init__(self)
		self.Content = '' # content as rich string with embedded formatting commands
		self.ParaHorizAlignment = TextItem.DefaultTextHorizAlignment
		self.ParaVertAlignment = TextItem.DefaultTextVertAlignment
		self.InitialTextStyle = Proj.MostRecentInitialTextStyle.get(PHAObjClass,
			Proj.MostRecentInitialTextStyle['Default'])

class AssociatedTextItem(TextItem):  # 'smart text' used for comments, action items and parking lot items

	def __init__(self, Proj, PHAObjClass=None, Host=None):
		# names of attribs marked + are assumed to match corresponding labels in module info, e.g. info.ResponsibilityLabel
		TextItem.__init__(self, Proj, PHAObjClass, Host)
		self.ID = ''
		self.Tack = None # reference to a position object on a PIDItem, or another PHA object, referred to by this text
		self.Numbering = NumberingItem()
		self.Responsibility = '' # who is responsible for closing out the item +
		self.Deadline = '' # deadline for closeout +
		self.Status = '' # whether item is open, closed etc +

# English names for associated text kinds. Translated at point of use, because they could be subject or object
AssociatedTextEnglishNamesSingular = {info.ActionItemLabel: 'action item', info.ParkingLotItemLabel: 'parking lot item'}
AssociatedTextEnglishNamesPlural = {info.ActionItemLabel: 'action items', info.ParkingLotItemLabel: 'parking lot items'}

DefaultTextStyleItem = TextStyleItem()

class BuilderDisplayItem(object):  # superclass of button items shown in PHA Viewports, allowing user to build up the
	# model, such as "add item" buttons

	def __init__(self):
		object.__init__(self)
		self.Shape = 'Rectangle'  # overall shape
		self.PosX = self.PosY = 10  # position of top left corner in model display, in canvas coords
		self.SizeX = self.SizeY = 50  # size in canvas coords
		self.State = 'Available'  # can be 'Available' (can be clicked), 'Activated' (clicked and acting), 'Over' (mouse over, but not clicked),
		# 'Not-Available' (can't be clicked)
		self.FillColour = {'Default': (0xff, 0x00, 0x00)}  # fill colour per State. Must include 'Default' key
		self.BorderColour = {'Default': (0xff, 0xff, 0x00)}  # fill colour per State. Must include 'Default' key
		self.Icon = {'Default': None}  # displayed graphic per State. Must include 'Default' key
		self.Text = ''  # text shown in the item. Plain text only
		self.TextStyle = DefaultTextStyleItem  # style (formatting) of text shown
		self.Visible = True  # whether shown in Viewport
		self.Clickable = ['Left', 'ShortTouch']  # which clicks will activate

	def Hit(self, ScreenX, ScreenY, Zoom, PanX, PanY, TolXInPx, TolYInPx):  # returns whether screen coord X, Y is inside the item
		# Zoom, PanX, PanY are the zoom and pan factors currently applied to the display
		# Get min and max canvas coords corresponding to screen pos, allowing for wooliness
		(MinCanvasX, MinCanvasY) = utilities.CanvasCoords(ScreenX - TolXInPx, ScreenY - TolYInPx, Zoom, PanX, PanY)
		(MaxCanvasX, MaxCanvasY) = utilities.CanvasCoords(ScreenX + TolXInPx, ScreenY + TolYInPx, Zoom, PanX, PanY)
		if self.Shape == 'Rectangle':
			HitSuccess = (MaxCanvasX >= self.PosX) and (MinCanvasX <= (self.PosX + self.SizeX)) and \
						 (MaxCanvasY >= self.PosY) and (MinCanvasY <= (self.PosY + self.SizeY))
		else:
			HitSuccess = False
			print("Oops, unrecognised object shape '%s' (problem code: DA872). This is a bug; please report it" % self.Shape)
		return HitSuccess

	def CanActivate(self, ScreenX, ScreenY, MouseAction, Zoom, PanX,
					PanY):  # returns whether item would be activated by MouseAction at the coords given
		# MouseAction: list containing zero or more of 'Left', 'Middle', 'Right', 'ShortTouch', 'LongTouch' (may add 'LeftDouble' etc later)
		if self.Hit(ScreenX, ScreenY, Zoom, PanX, PanY):
			return bool(set(MouseAction).intersection(set(self.Clickable)))
		else:
			return False

class LinkItem(object):
	# Objects defining a data link between one input (LinkMaster) and >=1 output PHA objects (LinkSlaves), such as causes
	LinkTypes = ['Copy', 'Link', 'LinkWithSmartTags']

	def __init__(self, LinkType='Link', LinkMaster=None, LinkSlave=None):
		object.__init__(self)
		if __debug__ == 1:
			assert isinstance(LinkType, str), "Non-string supplied as LinkType for new LinkItem"
			assert LinkType in LinkItem.LinkTypes, "Invalid LinkType '%s' supplied for new LinkItem" % LinkType
			# TODO test type of LinkMaster and LinkSlave. At present, there's no superclass for these
		self.Type = LinkType
		self.Master = LinkMaster
		if LinkSlave:
			self.LinkSlaves = [LinkSlave]
		else:
			self.LinkSlaves = []

class CollapseGroup(object):
	# group of PHA objects that can be collapsed for compact display
	AllCollapseGroups = [] # register of all collapse groups currently active in Vizop; used to generate unique IDs
		# Potential gotcha: Items in this list are not guaranteed to exist in PHA models. When they are deleted from
		# PHA models, currently no attempt is made to remove them from this list. (Potential memory leak?)

	def __init__(self):
		object.__init__(self)
		self.ID = str(utilities.NextID(CollapseGroup.AllCollapseGroups)) # generate unique ID; stored as str
		CollapseGroup.AllCollapseGroups.append(self) # add this CollapseGroup to register (must be after NextID() call)
		self.PHAObjects = [] # list of PHA objects in group
		self.Collapsed = False # whether group is currently collapsed
		self.Description = TextItem() # visible group description when collapsed

def DoTypeChecks(TypeChecks=[], IterableChecks=[], MemberChecks=[]):
	# perform type checking.
	# TypeChecks: list of tuples: (Attrib as str, Expected type)
	# IterableChecks: list of tuples: (Attribs which are iterables, Expected type of each item in Attrib)
	# MemberChecks: list of tuples: (Attrib, list/set that Attrib's value should belong to)
	# We considered supplying Attribs as string names and converting to values using eval(`Attrib`) but this would fail
	# because the namespace is different
	for CheckIndex, (Attrib, ExpectedType) in enumerate(TypeChecks):
		assert isinstance(Attrib, ExpectedType), "Item # %d in TypeChecks failed type check" % CheckIndex
	for CheckIndex, (AttribList, ExpectedType) in enumerate(IterableChecks):
		for ListIndex, i in enumerate(AttribList):
			assert isinstance(i, ExpectedType),\
				"List index # %d of item # %d in IterableChecks failed type check" % (ListIndex, CheckIndex)
	for CheckIndex, (Attrib, ExpectedValues) in enumerate(MemberChecks):
		assert Attrib in ExpectedValues, "Item # %d in MemberChecks failed inclusion check" % CheckIndex

def FirstProblemValueIn(Values):  # return:
	# ( first NumProblemValue in Values (list) (or None if there aren't any),
	# index of that NumProblemValue in Operands or -1 if there aren't any)
	ProblemValues = [v for v in Values if isinstance(Op, NumProblemValue)]
	if ProblemValues:
		return ProblemValues[0], Values.index(ProblemValues[0])
	else:
		return None, -1

class TolRiskModel(object): # superclass of tolerable risk model classes

	def __init__(self, Proj):
		object.__init__(self)
		self.Proj = Proj
		self.ID = Proj.GetNewID()
		self.RiskReceptors = [] # ordered list of RR's for this model
		self.SeverityUnits = ['']  # ordered list of units mapping to RiskReceptors
		self.MinSeverity = [ [] ]  # list of (lists of severity values for each severity category), one list per RR, in same order as RiskReceptors
		self.SeverityDescriptions = [[]]  # severity descriptions (human readable str), same structure as MinSeverity
		self.TolFreqUnit = PerYearUnit  # tolerable risk unit, typically '/yr'
		self.ShowSeverityValues = True  # whether severity values are visible to the user
		self.ShowSeverityDescriptions = True  # whether severity descriptions are visible to the user

	def GetTolFreq(
			self):  # dummy to allow property statement below. GetTolFreq is overridden by each subclass of this class
		pass

	TolFreq = property(fget=GetTolFreq)

class TolRiskFCatItem(TolRiskModel): # frequency categories model to determine tolerable risk

	def __init__(self, Proj):
		TolRiskModel.__init__(self, Proj)

	def GetTolFreq(self, RiskReceptor=DefaultRiskReceptor, SeverityValue=None, SeverityDescription=None):
		# returns tolerable frequency (NumValueItem instance) corresponding to the SeverityValue (NumValueItem) if supplied,
		# or the SeverityDescription (str) if not
		# First, check if RiskReceptor is recognised
		if RiskReceptor in self.RiskReceptors:
			RRIndex = self.RiskReceptors.index(RiskReceptor)
		else:
			return NumProblemValue_RRMissingInTolRiskModel
		SevCatIndex = None  # will be the index of the selected item in severity category list
		# look at severity values first: are they defined, and is there an input severity value?
		if self.MinSeverity[RRIndex] and SeverityValue:
			# check if the input value is not less than the first severity value
			if SeverityValue >= self.MinSeverity[RRIndex][0]:
				SevCatIndex = 0  # we will use the first (highest) severity category
			# find the first severity value that's not less than the input value
			else:
				SevCatIndex = [(SeverityValue < self.MinSeverity[RRIndex][i]) for i in
							   range(len(self.MinSeverity[RRIndex]))].index(False) - 1
		# next, look at severity descriptions and try to find a match with input description
		elif self.SeverityDescriptions[RRIndex] and SeverityDescription:
			if SeverityDescription in self.SeverityDescriptions[RRIndex]:
				SevCatIndex = self.SeverityDescriptions[RRIndex].index(SeverityDescription)
			else:
				return NumProblemValue_TolRiskNoMatchSevCat
		# did we successfully choose a severity category? If not, return a problem value
		if SevCatIndex is None: return NumProblemValue_TolRiskNoSelFreq
		# return a tolerable frequency value
		Result = NumValueItem()
		Result.Value = self.TolFreq[RRIndex][SevCatIndex]
		Result.Unit = self.TolFreqUnit
		return Result

def FontInstance(Size=12, Italics=False, Bold=False, Underlined=False, Font=''):
	# return wx.Font instance matching supplied args
	# Size is absolute; zooming, standout etc need to be handled by the calling procedure
	return wx.Font(Size, family=wx.DEFAULT, style={False: wx.NORMAL, True: wx.ITALIC}[Italics],
		weight={False: wx.NORMAL, True: wx.BOLD}[Bold], underline=Underlined, faceName=Font)

class TeamMember(object):

	def __init__(self, ID = '', Name = '', Role = '', Affiliation = ''):
		object.__init__(self)
		assert type(ID) == str
		assert ID # ensure it's not blank
		assert type(Name) == str
		assert type(Role) == str
		assert type(Affiliation) == str
		self.ID = ID # team member ID
		self.Name = Name # team member name
		self.Role = Role # team member role
		self.Affiliation = Affiliation # team member affiliation

class Comment(object):
	# implement a simple comment system for XML export. Not used; comments are instances of AssociatedTextItem
	def __init__(self, ID = 0, content = '', isVisible = True, showInReport = True):
		object.__init__(self)
		assert type(ID) == int
		assert type(content) == str
		assert type(isVisible) == bool
		assert type(showInReport) == bool
		self.ID = ID # comment ID
		self.content = content # content
		self.isVisible = isVisible # flag if visible or not, initially always True. For potential future features
		self.showInReport = showInReport # flag if shown in the report, initially always True. For potential future features

class Bookmark(object):
	# implement a simple bookmark system for XML export
	def __init__(self, iD = '0', isDeleted = False):
		assert type(iD) == str
		assert type(isDeleted) == bool

		self.iD = iD # bookmark ID
		self.isDeleted = isDeleted # flag if bookmark is deleted

		pass

class ChoiceItem(object): # represents an item in a group of items the user can select from, in an instance of
	# FTForDisplay (such as a risk receptor) or an instance of a PHA object shadow or an FT element
	def __init__(self, XMLName='', HumanName='', Applicable=True, **Args):
		# XMLName (str): stores the 'Serial' tag value received from FTObjectInCore
		# Applicable (bool): whether the item applies to this instance (ie whether this is the "current" one)
		assert isinstance(HumanName, str)
		assert isinstance(XMLName, str)
		assert len(XMLName) > 0
		assert isinstance(Applicable, bool)
		object.__init__(self)
		self.HumanName = HumanName
		self.XMLName = XMLName
		self.Applicable = Applicable
		self.__dict__.update(Args) # extract any other attribs supplied

class ImageFileType(object): # type of file that can be offered for image export

	def __init__(self, HumanName='', XMLName='', Extension='', SupportsMultiPage=False):
		# SupportsMultiPage: whether the file can contain more than one page
		assert isinstance(HumanName, str)
		assert isinstance(XMLName, str)
		assert isinstance(Extension, str)
		assert isinstance(SupportsMultiPage, bool)
		object.__init__(self)
		self.HumanName = HumanName
		self.XMLName = XMLName
		self.Extension = Extension
		self.SupportsMultiPage = SupportsMultiPage

PDFFileType = ImageFileType(HumanName='PDF', XMLName='PDF', Extension='pdf', SupportsMultiPage=True)
JPGFileType = ImageFileType(HumanName='JPG', XMLName='JPG', Extension='jpg', SupportsMultiPage=False)
PNGFileType = ImageFileType(HumanName='PNG', XMLName='PNG', Extension='png', SupportsMultiPage=False)
TIFFFileType = ImageFileType(HumanName='TIFF', XMLName='TIFF', Extension='tiff', SupportsMultiPage=False)
# file types to be offered for image file exports
ImageFileTypesSupported = [PDFFileType, JPGFileType, PNGFileType, TIFFFileType]
# check default is one of these
assert info.DefaultImageFileType in [t.Extension for t in ImageFileTypesSupported]

class PaperSize(object): # paper size that can be offered for image export
	# In future, see if we can use wx.PaperSize instead (haven't figured it out yet)

	def __init__(self, HumanName='', XMLName='', HumanDescription='', SizeShortAxis=0, SizeLongAxis=0): # sizes are in mm
		assert isinstance(HumanName, str)
		assert isinstance(XMLName, str)
		assert isinstance(HumanDescription, str)
		assert isinstance(SizeShortAxis, (int, float))
		assert isinstance(SizeLongAxis, (int, float))
		assert SizeShortAxis <= SizeLongAxis # must be portrait aspect
		object.__init__(self)
		self.HumanName = HumanName
		self.XMLName = XMLName
		self.HumanDescription = HumanDescription
		self.SizeShortAxis = SizeShortAxis
		self.SizeLongAxis = SizeLongAxis

	def GetFullNameForDisplay(self):
		return self.HumanName + ' (' + self.HumanDescription + ')'
	FullNameForDisplay = property(fget=GetFullNameForDisplay)

	def HumanDescriptor(self): # return str containing HumanName and size, e.g. 'A4 (210 x 297mm)'
		return '%s (%d x %d mm)' % (self.HumanName, self.SizeX, self.SizeY)

PaperSizeA4 = PaperSize(HumanName='A4', XMLName='A4', HumanDescription='210 x 297mm', SizeShortAxis=210, SizeLongAxis=297)
PaperSizeA5 = PaperSize(HumanName='A5', XMLName='A5', HumanDescription='148.5 x 210mm', SizeShortAxis=148.5, SizeLongAxis=210)
PaperSizeLegal = PaperSize(HumanName='Legal', XMLName='Legal', HumanDescription='8.5 x 14"', SizeShortAxis=216, SizeLongAxis=356)
PaperSizeA3 = PaperSize(HumanName='A3', XMLName='A3', HumanDescription='297 x 420mm', SizeShortAxis=297, SizeLongAxis=420)
PaperSizeLetter = PaperSize(HumanName='ANSI A (Letter)', XMLName='Letter', HumanDescription='8.5 x 11"', SizeShortAxis=216, SizeLongAxis=279)
PaperSize11_17 = PaperSize(HumanName='ANSI B (11 x 17)', XMLName='11x17', HumanDescription='11 x 17"', SizeShortAxis=279, SizeLongAxis=432)
PaperSizeB3 = PaperSize(HumanName='B3', XMLName='B3', HumanDescription='353 x 500mm', SizeShortAxis=353, SizeLongAxis=500)
PaperSizeB4 = PaperSize(HumanName='B4', XMLName='B4', HumanDescription='250 x 353mm', SizeShortAxis=250, SizeLongAxis=353)
PaperSizeB5 = PaperSize(HumanName='B5', XMLName='B5', HumanDescription='176 x 250mm', SizeShortAxis=176, SizeLongAxis=250)
PaperSizes = [PaperSizeA3, PaperSizeA4, PaperSizeA5, PaperSizeLetter, PaperSizeLegal, PaperSize11_17, PaperSizeB3,
	PaperSizeB4, PaperSizeB5]

# set up date choices; at least one must have 'Default' attrib
ProjCreationDate = ChoiceItem(XMLName='ProjCreation', HumanName='Project created')
FTCreationDate = ChoiceItem(XMLName='FTCreation', HumanName='Fault tree created')
LastEditDate = ChoiceItem(XMLName='LastEdit', HumanName='Last edited', Default=True)
TodayDate = ChoiceItem(XMLName='Today', HumanName='Today')
DateChoices = [ProjCreationDate, FTCreationDate, LastEditDate, TodayDate]

class ProblemReportItem(object):
	# defines a problem found during project file loading/saving
	def __init__(self, ProblemKind='', HumanDescription='', Fatal=False):
		assert isinstance(ProblemKind, str)
		assert ProblemKind # ensure it's not blank
		assert isinstance(HumanDescription, str)
		assert HumanDescription
		assert isinstance(Fatal, bool)
		object.__init__(self)
		self.ProblemKind = ProblemKind # a category of problem. Can be used to group problems or eliminate duplicates.
		#	Valid ProblemKind values not yet defined
		self.HumanDescription = HumanDescription # already translated
		self.Fatal = Fatal # whether the problem makes it impossible to complete the task, e.g. loading a project file

del _ # remove dummy definition
