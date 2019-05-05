# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright xSeriCon, 2018

"""vizop info module
This module contains constants that are used throughout Vizop.
"""
from platform import system

def _(message):
	"""
	Dummy definition of _() so that we can mark these strings for translation
	without actually translating them yet.
	"""
	return message


DEVELOPERS = ['Peter Clarke']
OWNER = 'xSeriCon'
OWNER_EMAIL = 'info@VizopSoftware.com'
VERSION = '0.1'
PROG_NAME = 'Vizop: visual PHA software'
PROG_SHORT_NAME = 'Vizop'
HOME_PAGE = "http://VizopSoftware.com"
SHORT_DESCRIPTION = _("")
LONG_DESCRIPTION = _("")
YEAR_LAST_RELEASED = '2018'
SRC_FILE_LICENSE_TEXT = _("# This file is part of %s. Copyright %s %s"%(PROG_SHORT_NAME, YEAR_LAST_RELEASED, OWNER))

# definitions of where runtime files are expected
ProjTemplateFolderTail = 'templates'
IconFolderTail = 'icons'
CacheFolderTail = 'vizop'

# file-related constants
RestoreFileSuffix = '_Restore' # suffix for project restore filename

# display-related constants
if system() == 'Darwin': CtrlKey = u"\u2318" # 'command key' symbol on Mac
else: CtrlKey = 'Ctrl + '
ListSeparator = _(', ') # separator in human-readable lists like cat, dog, fish
EventValueSigFigs = 3 # rounding for initiating event frequency values

# XML tags and attrib names for internal communication. Those marked #f are also used in project files
IDTag = 'ID' #f
IDAttribName = 'ID'
SerialTag = 'Serial' # used for object serial numbers, where needed to avoid confusion with object IDs
OpModeTag = 'OpMode'
RiskReceptorTag = 'RiskReceptor'
RiskReceptorGroupingOptionTag = 'RiskReceptorGrouping'
SeverityCatTag = 'SeverityCategory'
ApplicableAttribName = 'Applicable'
FTColumnTag = 'Column'
FTEventTag = 'FTEvent'
FTGateTag = 'FTGate'
FTConnectorTag = 'FTConnector'
EventTypeOptionTag = 'FTEventTypeOption'
UnitOptionTag = 'UnitOption'
NumberingTag = 'Numbering'
NumberKindTag = 'NumberKind'
ConvertValueTag = 'ConvertValue'
ProblemIndicatorTag = 'ProblemIndicator'
ProblemLevelAttribName = 'ProblemLevel'
DescriptionCommentTag = 'DescriptionComment'
ShowDescriptionCommentTag = 'ShowDescriptionComments'
ValueCommentTag = 'ValueComment'
ShowValueCommentTag = 'ShowValueComments'
ActionItemTag = 'ActionItem'
ShowActionItemTag = 'ShowActionItems'
FTGateTypeOptionTag = 'FTGateTypeOption'
FTHeaderTag = 'Header'
ProjIDTag = 'ProjID'
PHAModelIDTag = 'PHAModelID'
PHAModelTypeTag = 'PHAmodelclass' #f
ProjNameTag = 'ProjectName'
ProjNoTag = 'ProjectNo'
DescriptionTag = 'Description'
ProcessUnitTag = 'ProcessUnit'
CollaboratorTag = 'Collaborator'
UnitNumberAttribName = 'UnitNumber'
ShortNameAttribName = 'ShortName'
LongNameAttribName = 'LongName'
MilestoneIDTag = 'MilestoneID'
ViewportTypeTag = 'viewporttype'
ViewportTag = 'Viewport'
SkipRefreshTag = 'skiprefresh'
ChainWaitingTag = 'chainwaiting'
ChainedTag = 'chained'
C2DSocketNoTag = 'C2DSocketNumber'
D2CSocketNoTag = 'D2CSocketNumber'
UserMessageTag = 'UserMessage'

# for alarm list
AlarmCountTag = 'AlarmCount'
TotalAlarmCountTag = 'Total'
AlarmTag = 'Alarm'
AlarmTagTag = 'AlarmTag'

# for Fault Tree
FTTag = 'FT'
ComponentHostIDTag = 'ComponentHostID'

# XML tags for project files
ProjectRootTag = 'vizop_project'
UpdateTag = 'update'
PHAModelTag = 'PHAmodel'
DeleteTag = 'delete'
ReinstateTag = 'reinstate'

FTImagePrefix = 'FT_' # filenames containing all images used in FT must begin with this
ProjInfoImagePrefix = 'ProjInfo_'
CommandTag = 'Command'
ControlFrameInSocketLabel = 'F2CREP' # label prefix for datacore end of control frame -> datacore socket
ControlFrameOutSocketLabel = 'C2FREQ' # label prefix for datacore end of datacore -> control frame socket
ViewportOutSocketLabel = 'C2VREQ' # label prefix for datacore end of datacore -> Viewport socket

# Unicode symbols
CommandSymbol = u'\u2318' # cloverleaf symbol used on Mac keyboard's Command key
InfinitySymbol = u'\u221e'

# remove the dummy definition of _()
del _
