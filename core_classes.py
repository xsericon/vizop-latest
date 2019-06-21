# -*- coding: utf-8 -*-
# Module core_classes: part of Vizop, (c) 2018 xSeriCon
# contains class definitions of basic objects used throughout Vizop

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import wx # provides basic GUI functions
import copy
import xml.etree.ElementTree as ElementTree  # XML handling

# other vizop modules required here
import text, utilities
from display_utilities import *

def _(DummyArg): return DummyArg # dummy

class RiskReceptorItem(object): # class of risk receptors
	RRs = [] # list of all risk receptor instances defined in the open projects

	def __init__(self, XMLName='', HumanName='<undefined>'):
		object.__init__(self)
		self.XMLName = XMLName
		self.HumanName = HumanName
		self.ID = str(utilities.NextID(RiskReceptorItem.RRs)) # generate unique ID; stored as str
		RiskReceptorItem.RRs.append(self) # add this RiskReceptorItem to register (must be after NextID() call)

DefaultRiskReceptor = RiskReceptorItem(XMLName='Default', HumanName=_('Default'))

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
		if True in [(abs(Op) < MinDivisor) for Op in Operands[1:]]: return NumProblemValue_DivisionByZero
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

	def __init__(self, HumanName='', XMLName='', QtyKind='', UserSelectable=True, SuppressInOutput=False):
		# QtyKind must be in UnitItem.QtyKinds
		# HumanName: name shown on screen; translatable
		# XMLName: name used in XML input/output; fixed
		# SuppressInOutput (bool): whether to hide unit's HumanName in final output
		object.__init__(self)
		assert isinstance(HumanName, str), "CC150 Non-string value for HumanName in UnitItem initialization"
		assert isinstance(QtyKind, str)
		assert QtyKind in UnitItem.QtyKinds
		assert isinstance(UserSelectable, bool)
		assert isinstance(SuppressInOutput, bool)
		self.HumanName = HumanName
		self.XMLName = XMLName
		self.QtyKind = QtyKind
		if UserSelectable:
			UnitItem.UserSelectableUnits.append(self) # add to register of units
		self.SuppressInOutput = SuppressInOutput
		self.Conversion = {self: 1.0} # keys: UnitItem instances;
			# values: coefficient to convert from this unit to unit in key (float). The only compulsory key is self.

# acceptable engineering units
NullUnit = UnitItem('', '', 'Ratio', UserSelectable=False, SuppressInOutput=True) # used as problem indicator
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
DefaultBetaUnit = PercentageUnit

class OpModeType(object): # class of SIF operating modes; consistent with implementation in SILability
	DisplayName = _('Operating mode') # for display in comment header and Undo/Redo menu items

	def __init__(self, HumanName, XMLName, PermissibleTargetKinds):
		object.__init__(self)
		self.HumanName = HumanName # visible to user
		self.XMLName = XMLName # name used in XML input/output and passed to calculation engine
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

	def __init__(self, HostObj=None):
		# HostObj: None, or the object containing this NumValueItem instance,
		# which can optionally provide a CheckValue(v=NumValueItem instance) method
		object.__init__(self)
		self.HumanName = _('<undefined>')
		# set numerical values per risk receptor. Must include DefaultRiskReceptor key. None means value not defined
		self.ValueFamily = {DefaultRiskReceptor: None} # current numerical values of instance per risk receptor
		self.UserValueFamily = {DefaultRiskReceptor: None} # values provided by user.
			# Kept for reversion if we switch to another type (eg constant), then back again
		self.IsSetFlagFamily = {DefaultRiskReceptor: None} # ValueStatus (member of ValueStati) per risk receptor
		self.InfinityFlagFamily = {DefaultRiskReceptor: False} # bool per risk receptor; whether value is infinite
		self.SigFigs = {DefaultRiskReceptor: 2} # int per risk receptor; how many sig figs for display
		self.Sci = {DefaultRiskReceptor: False} # bool per risk receptor; whether to always use scientific notation
		self.MyUnit = NullUnit
		self.HostObj = HostObj

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], InvalidResult=0.0):
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
			else:  # DefaultRiskReceptor key is missing
				print("Oops, missing 'Default' key in NumValueItem risk receptors (problem code: D28). This is a bug; please report it")
				return InvalidResult
		# get the actual value
		MyStatus = self.Status(RR)
		if MyStatus == NumProblemValue_NoProblem:
			assert isinstance(self.ValueFamily[RR], float), "Numerical value '%s' is not float" % str(
				self.ValueFamily[RR])
			return float(self.ValueFamily[RR])
		else: return InvalidResult

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor):  # set numerical value of object per risk receptor
		# error checking first
		assert isinstance(NewValue, int) or isinstance(NewValue, float),\
			"NewValue '%s' isn't a valid number" % str(NewValue)
		self.ValueFamily[RR] = float(NewValue)
		self.UserValueFamily[RR] = float(NewValue) # store manually-entered value for restoration
		self.IsSetFlagFamily[RR] = True
		self.InfinityFlagFamily[RR] = False
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
		# Args can include SciThreshold (int, float or None). If it is int or float, and the absolute numerical value
		# ≥ SciThreshold, scientific notation is forced.
		assert isinstance(self.SigFigs, dict)
		assert 'Default' in self.SigFigs
		assert not [s for s in self.SigFigs.values() if not isinstance(s, int)] # confirm all SigFig values are int
		assert isinstance(self.Sci, dict)
		assert 'Default' in self.Sci
		assert not [s for s in self.Sci.values() if not isinstance(s, bool)] # confirm all Sci values are bool
		assert isinstance(self.InfinityFlagFamily, dict)
		assert 'Default' in self.InfinityFlagFamily
		assert not [s for s in self.InfinityFlagFamily.values() if not isinstance(s, bool)]
			# confirm all InfinityFlagFamily values are bool
		if self.Status(RR) == 'ValueStatus_Unset': return InvalidResult
		elif self.InfinityFlagFamily[RR]: return InfiniteResult # check if infinity flag is set
		else:
			MyValue = self.GetMyValue(RR=RR, InvalidResult=InvalidResult, **Args)
			if MyValue == InvalidResult:
				return InvalidResult
			else:
				SigFigs = self.SigFigs.get(self.GetMyUnit(), self.SigFigs['Default'])
				# round MyValue to required number of sig figs
				(TruncatedValue, Decimals) = utilities.RoundToSigFigs(MyValue, SigFigs)
				# determine whether to force scientific notation
				if Args.get('SciThreshold', None) is None: ForceSci = False
				else:
					assert isinstance(Args['SciThreshold'], (int, float))
					ForceSci = (abs(MyValue) >= Args['SciThreshold'])
				# apply string formatting to get scientific notation if required, and required number of decimal places
				if self.Sci.get(self.GetMyUnit(), self.Sci['Default']) or ForceSci: # scientific notation required for this unit?
					return '%0.*e' % (SigFigs - 1, TruncatedValue) # change 'e' to 'E' if want 1.2E6 instead of 1.2e6
				else: # non-scientific notation
					return '%0.*f' % (Decimals, TruncatedValue)

	def Status(self, RR=DefaultRiskReceptor): # return NumProblemValue item indicating status of value
		if not (RR in self.ValueFamily):  # requested risk receptor not defined for this value object
			print("Warning, missing '%s' key in NumValueItem risk receptors (problem code: CC390)" % RR)
			if DefaultRiskReceptor in self.ValueFamily:
				RR = DefaultRiskReceptor
			else:  # DefaultRiskReceptor key is missing
				print("Oops, missing 'Default' key in NumValueItem risk receptors (problem code: CC394). This is a bug; please report it")
				return NumProblemValue_Bug
		# check if value is set
		if (self.ValueFamily[RR] is None) or (self.IsSetFlagFamily[RR] != 'ValueStatus_OK'):
			# value not defined, returned 'undefined' NumProblemValue
			return NumProblemValue_UndefNumValue
		else: # value set; check if it is valid by trying to call self.HostObj.CheckValue(self)
			# (the lambda function is invoked if HostObj is None or CheckValue isn't defined
			return getattr(self.HostObj, 'CheckValue', lambda v: NumProblemValue_NoProblem)(self)

	def SetMyStatus(self, NewStatus, RR=DefaultRiskReceptor, **Args): # set status indicator (in IsSetFlagFamily)
		assert NewStatus in ValueStati
		assert RR in self.ValueFamily.keys()
		self.IsSetFlagFamily[RR] = NewStatus
		return True # indicates successful

class UserNumValueItem(NumValueItem): # class of NumValues for which user supplies a numeric value
	# Uses GetMyValue and GetMyUnit method from superclass
	ClassHumanName = _('User defined')
	XMLName = 'User'

	def __init__(self, **Args):
		NumValueItem.__init__(self)

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

class ConstantItem(NumValueItem): # user-defined constants that can be attached to any number of ConstNumValueItems
	# has values per RR, and a Unit
#	AllConstants = [] # register of all constants in use; not used, stored in Project instance instead
	def __init__(self, HumanName='', **Args):
		assert isinstance(HumanName, (bytes, unicode))
		NumValueItem.__init__(self)
		# TODO make ID
		self.HumanName = HumanName
#		ConstantItem.AllConstants.append(self) # add self to register.
		# NB if a constant is deleted, we must delete from the register (to avoid problems when storing the project)


class ConstNumValueItem(NumValueItem):  # class of constant NumValues. Refers to a ConstantItem instance
	ClassHumanName = _('Constant')
	XMLName = 'Constant'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, ConstantToReferTo=None, **Args):
		NumValueItem.__init__(self)
		self.Constant = ConstantToReferTo # needs to be assigned to an instance of ConstantItem

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[]):
		assert isinstance(self.Constant, ConstantItem)
		return self.Constant.GetMyValue(RR=RR, FormulaAntecedents=FormulaAntecedents)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		raise TypeError("Not allowed to set value of a ConstNumValueItem directly")

	def GetMyUnit(self):  # returns human-readable unit name (rich str)
		assert isinstance(self.Constant.Unit, UnitItem)
		return self.Constant.Unit.HumanName

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a ConstNumValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)


class CalcNumValueItem(NumValueItem): # class of NumValues that are calculated from a formula
	ClassHumanName = _('Calculated value')
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
	ClassHumanName = _('Problem message')
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
		assert isinstance(Value, float)
		assert isinstance(Unit, UnitItem)
		assert isinstance(Problem, NumProblemValue)
		self.Value = Value
		self.Unit = Unit
		self.Problem = Problem
		self.ProblemObj = ProblemObj

# class SwitchNumValueItem(NumValueItem): # class of values that are determined by checking against a series of yes/no conditions
# deferred until later version of Vizop
#	ClassHumanName = _('Switch')
#	XMLName = 'Switch'
#	UserSelectable = True # whether user can manually select this class when assigning a value to a PHA object
#
#	def __init__(self, **Args):
#		object.__init__(self)
#		self.DefaultValue = None # value returned if all the Routes return False
#		self.Routes = [] # list of tuples: (SwitchItem, NumValueItem). Each SwitchItem is tested in turn; if True, returns respective NumValueItem

class LookupNumValueItem(NumValueItem): # class of values found by reference to a lookup table
	ClassHumanName = _('Matrix lookup')
	XMLName = 'Lookup'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self)
		self.LookupTable = None  # instance of LookupTableItem
		self.InputValue = None  # instance of NumValueItem subclass; the value to look up in the table
		# TODO: need to develop for multidimensional lookup (currently only 1-D)

	def GetMyValue(self, RR=DefaultRiskReceptor, **args):  # return value from lookup table
		if (not self.LookupTable) or (self.InputValue is None): return NumProblemValue_UndefNumValue
		assert isinstance(self.InputValue, NumValueItem)
		assert not isinstance(self.InputValue.Value, NumProblemValue)
		return self.LookupTable.Value(RR, self.InputValue.Value, **args)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		raise TypeError("Not allowed to set value of a LookupNumValueItem directly")

	def GetMyUnit(self):  # returns human-readable unit name (rich str)
		assert isinstance(self.LookupTable, LookupTableItem)
		print("CC661 LookupValueItem GetMyUnit needs to look up the unit of the output value, not coded")
#		Unit = self.LookupTable.OutputUnit
		assert isinstance(Unit, UnitItem)
		return Unit.HumanName

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a LookupNumValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

class CategoryNameItem(NumValueItem): # class of objects defining one of a list of categories
	# Used for lookup in a matrix. Example: a severity value
	ClassHumanName = _('Categories')
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
	ClassHumanName = _('Calculated')
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
		return super(AutoNumValueItem, self).GetMyUnit(**Args)

	def Status(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], **args):
		# return NumProblemValue item indicating status of value
		return self.StatusGetter(RR, **args)
#		# get item's value to check if it is available
#		Value = self.GetMyValue(RR=RR, FormulaAntecedents=FormulaAntecedents, **args)
#		if isinstance(Value, NumProblemValue): return Value # if we got a problem report, return the report
#		else: return NumProblemValue_NoProblem # value obtained successfully

class ParentNumValueItem(NumValueItem):  # a NumValueItem whose value was copied from a parent, but is not linked to it
	ClassHumanName = _('Copied value')
	XMLName = 'Copied'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

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


class UseParentValueItem(NumValueItem):
	# class indicating values are to be linked from a parent PHA object, such as a cause or a calculated value
	ClassHumanName = _('Linked from another value')
	XMLName = 'LinkedFrom'
	UserSelectable = True  # whether user can manually select this class when assigning a value to a PHA object

	def __init__(self, **Args):
		NumValueItem.__init__(self)
		self.ParentPHAObj = None  # parent object (eg a PHA cause) containing the NumValueItem that this item is linked to

	def GetMyValue(self, RR=DefaultRiskReceptor, FormulaAntecedents=[], **args): # return value of object
		if self.ParentPHAObj is None:
			return NumProblemValue_BrokenLink # parent object not defined, can't follow link
		return self.ParentPHAObj.Value.Value(RR, FormulaAntecedents, **args)

	def SetMyValue(self, NewValue, RR=DefaultRiskReceptor): # attempting to set value of this class directly is evil
		# (it should be replaced with another NumValueItem class instance instead)
		raise TypeError("Not allowed to set value of a UseParentValueItem directly")

	def GetMyUnit(self):  # returns human-readable unit name (rich str)
		if self.ParentPHAObj is None: # parent object not defined, can't follow link
			return NullUnit
		return self.ParentPHAObj.Value.Unit.HumanName

	def SetMyUnit(self, NewUnit): # attempting to set unit of this class directly is evil
		raise TypeError("Not allowed to set unit of a UseParentValueItem directly")

	Value = property(fget=GetMyValue, fset=SetMyValue)
	Unit = property(fget=GetMyUnit, fset=SetMyUnit)

NumValueClasses = [UserNumValueItem, ConstNumValueItem, CalcNumValueItem, NumProblemValue, LookupNumValueItem,
	AutoNumValueItem, ParentNumValueItem, UseParentValueItem]
NumValueClassesToCheckValid = (UserNumValueItem, ConstNumValueItem, LookupNumValueItem,
	ParentNumValueItem, UseParentValueItem) # only these classes are checked in CheckValue() methods
	# this is a tuple, not a list, so it can be used directly in isinstance()
NumValueClassHumanNames = [c.ClassHumanName for c in NumValueClasses]  # list of names used in choice box


class LookupTableItem(object):
	# class of tables containing values that can be looked up by reference to a key value
	# The values are assumed to support all risk receptors, so there's no explicit handling of RR's here

	def __init__(self):
		object.__init__(self)
		self.HowManyDimensions = 1
		self.DimensionHumanNames = ['<Dimension1>'] # list of str, one per dimension
		self.DimensionUnits = [DimensionlessUnit] # list of UnitItem, one per dimension
		self.Keys = [ [] ]
			# list of lists of key value objects (CategoryNameItem instances) - one inner list per dimension
			# Example: [ [SlightItem, ModerateItem, SevereItem], [RareItem, ...etc] ]
		# Values: nested lists of value objects (subclasses of NumItem). Nesting depth = no of dimensions.
		# Top level list is for categories in 1st dimension; next level for 2nd dimension, etc.
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

	def Matched(self, x,
				y):  # return bool - whether x and y (numerical values) are considered equal (TODO move to top level so it can also be used by SwitchItem)
		# handle case where y is zero, so ratio can't be calculated
		if abs(y) < MinDivisor: return (abs(x) < MinDivisor)  # true if x is also zero
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
		object.__init__(self)
		self.ID = str(utilities.NextID(PHAModelBaseClass.AllPHAModelObjects)) # generate unique ID; stored as str
		PHAModelBaseClass.AllPHAModelObjects.append(self) # add instance to register; must do after assigning self.ID
		self.Proj = Proj
		self.Viewports = [] # list of Viewport instances for this PHA model; instances of subclasses of ViewportBaseClass
		self.EditAllowed = True

class MilestoneItem(object): # item storing info required for navigation back/forwards
	AllNavigationItems = [] # list of all instances created in this Vizop instance
	def __init__(self, Proj, **Args):
		AttribInfo = [ ('Displayable', bool), ('Zoom', int), ('PanX', int), ('PanY', int) ]
		for AttribName, AttribType in AttribInfo:
			if AttribName in Args: assert isinstance(Args[AttribName], AttribType)
		object.__init__(self)
		self.ID = str(utilities.NextID(MilestoneItem.AllNavigationItems)) # generate unique ID; stored as str
		self.Proj = Proj
		self.Displayable = Args.get('Displayable', True) # whether the user is allowed to go to this item. If it's only for Undo purposes,
			# Displayable may be False.
		self.Viewport = Args.get('Viewport', None) # which Viewport to display on the display device
		self.DisplDevice = Args.get('DisplDevice', None) # which display device to show the Viewport on
		self.Zoom = Args.get('Zoom', 100) # Zoom value to apply on the Viewport
		self.PanX = Args.get('PanX', 0) # Pan value to apply on the Viewport
		self.PanY = Args.get('PanY', 0) # Pan value to apply on the Viewport
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
		self.NumberStructure = [] # list of numbering chunks, see comment just above
		self.ShowInDisplay = True  # whether number is displayed in Viewport
		self.ShowInOutput = True  # whether number is displayed in PHA model export

	def __eq__(self, other): # returns True if self and other (a NumberingItem instance) are considered identical
		# this method allows comparison of NumberingItem instances simply by (Instance1 == Instance2)
		assert isinstance(other, NumberingItem)
		# compare NumberStructure contents of self and other
		Match = len(self.NumberStructure) == len(other.NumberStructure)
		ThisIndex = 0
		while Match and (ThisIndex < len(self.NumberStructure)):
			ThisItemInSelf = self.NumberStructure[ThisIndex]
			ThisItemInOther = other.NumberStructure[ThisIndex]
			# each item can be str, ParentNumberChunkItem or SerialNumberChunkItem. Check their types and contents match
			Match = (ThisItemInSelf == ThisItemInOther) if isinstance(ThisItemInOther, type(ThisItemInSelf)) else False
		return Match and (self.ShowInDisplay == other.ShowInDisplay) and (self.ShowInOutput == other.ShowInOutput)

	def HumanValue(self, PHAItem, Host, Levels=999, PHAObjectsReferenced=[]):
		# get the number for display for PHAItem.
		# Host = iterable containing all similar PHA items to consider in serial numbering at lowest level
		# NumberingItem instances in PHAItem instances within Host should be called Numbering, else serial numbering
		# won't work properly
		# returns (string containing the number as displayed, number of numerical chunks returned (int))
		# returns only the last <Levels> numerical items (not counting string chunks, which are assumed to be separators)
		# PHAObjectsReferenced is for circular reference trapping
		NumString = ''  # build up the number string chunkwise
		NumChunksAdded = 0  # counter for numerical chunks added
		for Chunk in [self.NumberStructure[-Index] for Index in
					  range(len(self.NumberStructure))]:  # work through list of chunks in reverse
			if type(Chunk) is str:
				NumString = Chunk + NumString  # prepend string chunk as-is
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


class ParentNumberChunkItem(object):
	# a chunk in a NumberingItem instance, that takes numbering from a PHA object (eg node, cause).
	XMLName = 'Parent'

	def __init__(self):
		object.__init__(self)
		self.Source = None  # PHA item instance to take numbering from
		self.HierarchyLevels = 999 # how many levels of numbering to return. If <=1, only return the serial number of the Source item

	def __eq__(self, other):
		assert isinstance(other, ParentNumberChunkItem)
		return (self.Source == other.Source) and (self.HierarchyLevels == other.HierarchyLevels)

#	def GetMyNumber(self, Levels=999,
#					PHAObjectsReferenced=[]):  # Gets number of Source, up to a maximum <Levels> levels
	def GetMyNumber(self, PHAObjectsReferenced=[]):  # Gets number of Source, up to a maximum <Levels> levels
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
	XMLName = 'Serial'

	def __init__(self):
		object.__init__(self)
		self.FieldWidth = 3  # how many digits to return
		self.PadChar = '0'  # left padding to use in returned number to fill up FieldWidth
		self.StartSequenceAt = 1 # (int) number to return for first item in sequence
		self.SkipTo = None # if defined (int), returns this number if greater than position in sequence
			# (taking GapBefore into account)
		self.GapBefore = 0 # (int >= 0) how many unused values to leave before this item
		self.IncludeInNumbering = True # whether to count this item in serial numbering
			# (if False, GetMyNumber() returns NoValue string)
		self.NoValue = '- -' # value returned if IncludeInNumbering is False

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
			else: return NoValue # IncludeInNumbering is False
		else:  # no PHAItem defined
			Serial = self.FieldWidth * '?'
			print("Oops, PHA item not defined in numbering scheme (problem code CC726). This is a bug; please report it")
		return Serial

#	Result = property(fget=GetMyNumber)


class NumberSystem(object):  # superclass of numbering systems such as 1/2/3, a/b/c, I/II/III
	# Only classes are invoked, not instances, so there's no __init__ method
	pass


class ArabicNumberSystem(NumberSystem):  # decimal number system using 0/1/2...

	HumanName = _('Arabic (1, 2...)')  # human-readable name of the numbering system
	Digits = '0 1 2 3 4 5 6 7 8 9'.split()
	MinValue = 0  # min and max acceptable value in terms of int equivalent
	MaxValue = 9999
	StartIndex = 1  # digits in higher placeholders (not the 'units' digit) start from index 1 (eg ten = 10 not 00)
	StartValue = 1
	PadChar = '0'  # default left-padding character for use in serial chunks of NumberingItem instances

	@staticmethod
	def HumanValue(TargetValue=0,
				   FieldWidth=4):  # returns string representation of TargetValue (int) in the numbering system, left-padded to required width
		return utilities.Pad(str(min(ArabicNumberSystem.MaxValue, max(ArabicNumberSystem.MinValue, int(TargetValue)))),
							 FieldWidth=FieldWidth, PadChar=ArabicNumberSystem.PadChar)


class SequenceNumberSystem(NumberSystem):  # number system using any sequence of digits, eg a/b/c...
	# to write a class for a different sequence, it should be sufficient to define only HumanName and Digits

	MinValue = 0  # min and max acceptable value in terms of int equivalent
	MaxValue = 9999
	StartIndex = 0
	StartValue = 0
	PadChar = ' '

	@classmethod
	def HumanValue(cls, TargetValue=0,
				   FieldWidth=4):  # returns string representation of TargetValue (int) in the numbering system, left-padded to required width
		Remainder = min(cls.MaxValue, max(cls.MinValue, TargetValue))
		Position = 0  # to allow for StartIndex on digits other than the least significant one
		Result = ''  # build up result string
		# work through significant digits from lowest to highest
		while Remainder >= cls.Base:
			ThisDigitValue = Remainder % cls.Base
			Result = Result + Digits[ThisDigitValue - cls.StartValue + Position]
			Remainder -= ThisDigitValue
			Position = StartIndex
		return utilities.Pad(Result, FieldWidth=FieldWidth, PadChar=cls.PadChar)


class LowerCaseLetterNumberSystem(SequenceNumberSystem):  # number system using a/b/c...
	HumanName = _('Lower case (a, b...)')
	Digits = [chr(x) for x in range(ord('a'), ord('z') + 1)]
	Base = len(Digits) + 1


class UpperCaseLetterNumberSystem(SequenceNumberSystem):  # number system using A/B/C...
	HumanName = _('Upper case (A, B...)')
	Digits = [chr(x) for x in range(ord('A'), ord('Z') + 1)]
	Base = len(Digits) + 1


NumberSystems = [ArabicNumberSystem, LowerCaseLetterNumberSystem, UpperCaseLetterNumberSystem]


class TextItem(object):  # text forming part of a PHA object, such as a description, comment or recommendation
	DefaultTextHorizAlignment = 'Centre'
	DefaultTextVertAlignment = 'Centre'

	def __init__(self, Proj,
			PHAObjClass, Host):  # PHAObjectClass is the class of PHA object with which the text is associated
		# Host: the parent PHA object (e.g. FTEvent)
		object.__init__(self)
		self.Content = ''  # content as rich string with embedded formatting commands
		self.ParaHorizAlignment = TextItem.DefaultTextHorizAlignment
		self.ParaVertAlignment = TextItem.DefaultTextVertAlignment
		self.InitialTextStyle = Proj.MostRecentInitialTextStyle.get(PHAObjClass,
																	Proj.MostRecentInitialTextStyle['Default'])


class AssociatedTextItem(TextItem):  # 'smart text' used for comments and recommendations

	def __init__(self, Proj, PHAObjClass, Host):
		TextItem.__init__(self, Proj, PHAObjClass, Host)
		self.Tack = None  # reference to a position object on a PIDItem, or another PHA object, referred to by this text
		self.Numbering = NumberingItem()

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

class TolRiskModel(object): # superclass of tolerable risk model classes. TODO add ID attrib

	def __init__(self):
		object.__init__(self)
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

class TolRiskFCatItem(TolRiskModel):  # frequency categories model to determine tolerable risk

	def __init__(self):
		TolRiskModel.__init__(self)

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

	def __init__(self, iD = 0, name = '', role = '', affiliation = ''):
		object.__init__(self)
		assert type(iD) == int
		assert type(name) == str
		assert type(role) == str
		assert type(affiliation) == str

		self.iD = iD # team member ID
		self.name = name # team member name
		self.role = role # team member role
		self.affiliation = affiliation # team member affiliation
		pass
	pass

class Comment(object):
	# implement a simple comment system for XML export
	def __init__(self, iD = 0, content = '', isVisible = True, showInReport = True):
		object.__init__(self)
		assert type(iD) == int
		assert type(content) == str
		assert type(isVisible) == bool
		assert type(showInReport) == bool

		self.iD = iD # comment ID
		self.content = content # content
		self.isVisible = isVisible # flag if visible or not, initially always True. For potential future features
		self.showInReport = showInReport # flag if shown in the report, initially always True. For potential future features

		pass

	pass

class Bookmark(object):
	# implement a simple bookmark system for XML export
	def __init__(self, iD = '0', isDeleted = False):
		assert type(iD) == str
		assert type(isDeleted) == bool

		self.iD = iD # bookmark ID
		self.isDeleted = isDeleted # flag if bookmark is deleted

		pass


del _ # remove dummy definition