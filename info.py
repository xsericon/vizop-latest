# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright xSeriCon, 2020

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
YEAR_LAST_RELEASED = '2020'
SRC_FILE_LICENSE_TEXT = _("# This file is part of %s. Copyright %s %s"%(PROG_SHORT_NAME, YEAR_LAST_RELEASED, OWNER))

# definitions of where runtime files are expected
ProjTemplateFolderTail = 'templates'
IconFolderTail = 'icons'
CacheFolderTail = 'vizop'

# file-related constants
RestoreFileSuffix = '_Restore' # suffix for project restore filename
DefaultImageFileType = 'pdf' # must be Extension attrib of an instance of core_classes.ImageFileType
ExcelExtension = 'xlsx' # extension expected for reading/writing Excel files
DefaultUserDirectory = '~'

# display-related constants
if system() == 'Darwin': CtrlKey = u"\u2318" # 'command key' symbol on Mac
else: CtrlKey = 'Ctrl + '
ListSeparator = _(', ') # separator in human-readable lists like cat, dog, fish
EventValueSigFigs = 3 # rounding for initiating event frequency values
OutcomeValueSigFigs = 2 # rounding for final calculated values
DefaultSigFigs = 2 # default number of sig figs for displaying all other numbers
SciThresholdUpper = 1e5 - 1 # thresholds for displaying numbers in scientific notation
SciThresholdLower = 9.9999e-4
ZeroThreshold = 1e-20 # numbers with absolute value less than this are treated as zero
CantDisplayValueOnScreen = '- - -' # undisplayable values are shown on screen like this
EditPanelModes = ['Edit', 'Select', 'Blocked', 'Widgets'] # modes defining mouse pointer and bindings
EditCursorXOffsetAtLeftEdge = 2 # X offset of edit cursor when at left edge of text edit box, to avoid clash with box
NotDefinedText = _('<Not defined>') # shown on screen

# export-related constants
DefaultPaperSize = 'A4'
DefaultPaperOrientation = 'Portrait'
DefaultPaperTopMargin = '10' # in mm
DefaultPaperBottomMargin = '10'
DefaultPaperLeftMargin = '10'
DefaultPaperRightMargin = '10'
DefaultPaperPageNumberPos = 'Top,Right'
MinUsablePaperLength = 100 # minimum allowable distance between paper margins, in mm
MinMargin = 5 # minimum allowable paper margin on each side, in mm

# XML tags and attrib names for internal communication. Those marked #f are also used in project files
IDTag = 'ID' #f
IDAttribName = 'ID'
SerialTag = 'Serial' # used for object serial numbers, where needed to avoid confusion with object IDs
OpModeTag = 'OpMode'
RiskReceptorGroupingOptionTag = 'RiskReceptorGrouping'
SeverityCatTag = 'SeverityCategory'
ApplicableAttribName = 'Applicable'
FTColumnTag = 'Column'
FTEventTag = 'FTEvent'
FTGateTag = 'FTGate'
FTConnectorTag = 'FTConnector'
EventTypeOptionTag = 'FTEventTypeOption'
UnitTag = 'Unit'
UnitOptionTag = 'UnitOption'
ValueKindOptionTag = 'ValueKindOption'
ConstantOptionTag = 'ConstantOption'
MatrixOptionTag = 'MatrixOption'
NumberingTag = 'Numbering'
NumberKindTag = 'NumberKind'
ConvertValueTag = 'ConvertValue'
ProblemIndicatorTag = 'ProblemIndicator'
ProblemLevelAttribName = 'ProblemLevel'
DescriptionCommentTag = 'DescriptionComment'
ShowDescriptionCommentTag = 'ShowDescriptionComments'
ValueCommentTag = 'ValueComment'
ShowValueCommentTag = 'ShowValueComments'
AssociatedTextTag = 'AssociatedText'
AssociatedTextsTag = 'AssociatedTexts'
AssociatedTextIndexTag = 'AssociatedTextIndex'
AssociatedTextKindTag = 'AssociatedTextKind'
AssociatedTextIDTag = 'AssociatedTextID'
ATRowTag = 'AssociatedTextRow'
ActionItemTag = 'ActionItem'
ParkingLotItemTag = 'ParkingLotItem'
ShowActionItemTag = 'ShowActionItems'
FTGateTypeOptionTag = 'FTGateTypeOption'
FTHeaderTag = 'Header'
ProjIDTag = 'ProjID'
PHAModelIDTag = 'PHAModelID'
PHAModelTypeTag = 'PHAmodelclass' #f
PHAModelRedrawDataTag = 'PHAModelRedrawData'
PHAObjTag = 'PHAObj'
PHAElementTag = 'PHAElement'
ComponentTag = 'Component'
ProjNameTag = 'ProjectName'
ProjNoTag = 'ProjectNo'
ProcessUnitTag = 'ProcessUnit'
CollaboratorTag = 'Collaborator'
UnitNumberAttribName = 'UnitNumber'
ShortNameAttribName = 'ShortName'
LongNameAttribName = 'LongName'
MilestoneIDTag = 'MilestoneID'
ViewportTypeTag = 'viewporttype'
ViewportTag = 'Viewport'
DoomedViewportIDTag = 'ViewportToDestroy'
SkipRefreshTag = 'skiprefresh'
ChainWaitingTag = 'chainwaiting'
ChainedTag = 'chained'
C2DSocketNoTag = 'C2DSocketNumber'
D2CSocketNoTag = 'D2CSocketNumber'
UserMessageTag = 'userMessage'
ElementVisibleTag = 'elementVisible'
ComponentToHighlightTag = 'componentToHighlight'
ZoomTag = 'Zoom'
PanXTag = 'PanX'
PanYTag = 'PanY'
HumanNameTag = 'HumanName'
CanEditValueTag = 'CanEditValue'
AttribNameTag = 'AttribName'
NewAttribValueTag = 'NewAttribValue'
DisplayAttribTag = 'DisplayAttribs'
PersistentAttribsTag = 'PersistentAttribs'

# for alarm list
AlarmCountTag = 'AlarmCount'
TotalAlarmCountTag = 'Total'
AlarmTag = 'Alarm'
AlarmTagTag = 'AlarmTag'

# for Fault Tree
FTTag = 'FT'
ComponentHostIDTag = 'ComponentHostID'
FTElementContainingComponentToHighlight = 'ElContainingCptToHighlight'
FTComponentToHighlight = 'CptToHighlight'
TolFreqTag = 'TolFreq'
TolFreqUnitTag = 'TolFreqUnit'
ConnectorInsAvailableTag = 'ConnectorInsAvailable'
ConnectorInsTag = 'ConnectorInsConnected'

# XML tags for project files
ProjectRootTag = 'VizopProject'
UpdateTag = 'update'
PHAModelTag = 'PHAmodel'
DeleteTag = 'delete'
ReinstateTag = 'reinstate'
VizopVersionTag = 'VizopVersion'

ShortTitleTag = 'ShortTitle'
ProjNumberTag = 'ProjNumber'
DescriptionTag = 'Description'
EditNumberTag = 'EditNumber'
TeamMembersTag = 'TeamMembers'
TeamMemberTag = 'TeamMember'
NameTag = 'Name'
RoleTag = 'Role'
AffiliationTag = 'Affiliation'
ProcessUnitsTag = 'ProcessUnits'
UnitNumberTag = 'UnitNumber'
ShortNameTag = 'ShortName'
LongNameTag = 'LongName'
RiskReceptorsTag = 'RiskReceptors'
RiskReceptorTag = 'RiskReceptor'
NumberSystemsTag = 'NumberSystems'
NumberSystemTag = 'NumberSystem'
NumberChunkTag = 'Chunk'
NumberChunkKindTag = 'Type'
ShowInDisplayTag = 'ShowInDisplay'
ShowInOutputTag = 'ShowInOutput'
FieldWidthTag = 'FieldWidth'
PadCharTag = 'PadChar'
StartSequenceAtTag = 'StartSequenceAt'
SkipToTag = 'SkipTo'
GapBeforeTag = 'GapBefore'
IncludeInNumberingTag = 'IncludeInNumbering'
NoValueTag = 'NoValue'
NoneTag = 'None'
RiskMatricesTag = 'RiskMatrices'
RiskMatrixTag = 'RiskMatrix'
SeverityDimensionTag = 'SeverityDimension'
DimensionsTag = 'Dimensions'
DimensionTag = 'Dimension'
KeyTag = 'Key'
EntriesTag = 'Entries'
EntryTag = 'Entry'
ConstantsTag = 'Constants'
ConstantTag = 'Constant'
FaultTreesTag = 'FaultTrees'
FaultTreeTag = 'FaultTree'
SIFNameTag = 'HumanName' # possible clash with HumanNameTag; this one must be HumanName because FTObjectInCore's
	# attributes listed in TextComponentNames are assumed to have the same name and XML tag, oops
CommentsTag = 'Comments'
CommentTag = 'Comment'
CommentIndexTag = 'CommentIndex'
CommentTextTag = 'CommentText'
ContentTag = 'Content'
ResponsibilityTag = 'Responsibility'
DeadlineTag = 'Deadline'
StatusTag = 'Status'
isVisibleTag = 'IsVisible'
showInReportTag = 'ShowInReport'
BookmarksTag = 'Bookmarks'
BookmarkTag = 'Bookmark'
isDeletedTag = 'isDeleted'
TypeTag = 'Type'
ValueTag = 'Value'
LevelsTag = 'Levels'
LookupTag = 'Lookup'
CopiedTag = 'Copied'
CopiedFromTag = 'CopiedFrom'
NumberSystemStringType = 'Str'
NumberSystemParentType = 'Parent'
NumberSystemSerialType = 'Serial'
InfiniteTag = 'Infinite'
XMLNameTag = 'XMLName'

RevTag = 'Rev'
TargetRiskRedMeasureTag = 'TargetRiskRedMeasure'
SILTargetValueTag = 'SILTargetValue'
BackgColourTag = 'BackgColour'
TextColourTag = 'TextColour'
SeverityTag = 'Severity'
RRTag = 'RR'
SeverityValueTag = 'SeverityValue'
ColumnsTag = 'Columns'
FTConnectorInTag = 'FTConnectorIn'
FTConnectorOutTag = 'FTConnectorOut'
IsIPLTag = 'IsIPL'
EventTypeTag = 'EventType'
EventDescriptionTag = 'EventDescription'
OldFreqValueTag = 'OldFreqValue'
OldProbValueTag = 'OldProbValue'
LastSelectedUnitTag = 'LastSelectedUnit'
IsSIFFailureEventInRelevantOpmodeTag = 'IsSIFFailureEventInRelevantOpmode'
ShowActionItemsTag = 'ShowActionItems'
EventDescriptionCommentsTag = 'EventDescriptionComments'
ConnectorDescriptionCommentsTag = 'ConnectorDescriptionComments'
ValueCommentsTag = 'ValueComments'
ShowDescriptionCommentsTag = 'ShowDescriptionComments'
ShowValueCommentsTag = 'ShowValueComments'
ActionItemsTag = 'ActionItems'
ParkingLotItemsTag = 'ParkingLotItems'
ConnectToTag = 'ConnectTo'
LinkedFromTag = 'LinkedFrom'
QtyKindTagTag = 'QtyKindTag'
GateDescriptionTag = 'GateDescription'
AlgorithmTag = 'Algorithm'
GateDescriptionComments = 'GateDescriptionComments'
ShowDescriptionComments = 'ShowDescriptionComments'
RelatedConnectorTag = 'RelatedConnector'
StyleTag = 'Style'
TolRiskModelTag = 'TolRiskModel'
ModelGateTag = 'ModelGate'
CollapseGroupsTag = 'CollapseGroups'
CollapseGroupTag = 'CollapseGroup'
CategoriesTag = 'Categories'
CategoryTag = 'Category'
ConstValueTag = 'ConstValue'
KindTag = 'Kind'
FilterTextTag = 'FilterText'
FilterAppliedTag = 'FilterApplied'
ItemsSelectedTag = 'ItemsSelected'
AssociatedTextsSelectedTag = 'ATsSelected'
ItemsToIncludeTag = 'ItemsToInclude'
UserTag = 'User'
UnknownTag = 'Unknown'

FTImagePrefix = 'FT_' # filenames containing all images used in FT must begin with this
ProjInfoImagePrefix = 'ProjInfo_'
CommandTag = 'Command'
ControlFrameInSocketLabel = 'F2CREP' # label prefix for datacore end of control frame -> datacore socket
ControlFrameOutSocketLabel = 'C2FREQ' # label prefix for datacore end of datacore -> control frame socket
ViewportOutSocketLabel = 'C2VREQ' # label prefix for datacore end of datacore -> Viewport socket
LocalSuffix = '_Local' # suffix for datacore sockets connecting to local control frame
NullUnitInternalName = 'null'
ConvertValueMarker = '_Convert' # indicates user has requested to convert value when changing unit
ValueOutOfRangeMsg = 'ValueOutOfRange'

# strings used to label objects
ActionItemLabel = 'ActionItems'
ParkingLotItemLabel = 'ParkingLot'
ATsLabel = 'ATs' # for 'associated texts' in general
ResponsibilityLabel = 'Responsibility'
DeadlineLabel = 'Deadline'
StatusLabel = 'Status'
WhereUsedLabel = 'WhereUsed'
EditNumberLabel = 'EditNumber'
HeaderLabel = 'Header'
PortraitLabel = 'Portrait'
LandscapeLabel = 'Landscape'
AllItemsLabel = 'AllItems'
FilteredItemsLabel = 'Filtered'
NotSpecifiedLabel = 'NotSpecified'
LeftLabel = 'Left'
RightLabel = 'Right'
BelowLabel = 'Below'
AboveLabel = 'Above'
TopLabel = 'Top'
CentreLabel = 'Centre'
BottomLabel = 'Bottom'

# NO_ commands to control frame
NO_ShowViewport = 'NO_ShowViewport'
NO_RedrawAfterUndo = 'NO_RedrawAfterUndo'

# Unicode symbols
CommandSymbol = u'\u2318' # cloverleaf symbol on Mac keyboard's Command key
CommandKeyName = CommandSymbol if system() == 'Darwin' else 'Ctrl'
InfinitySymbol = u'\u221e'
NewlineSymbol = u'\u21a9'

# remove the dummy definition of _()
del _
