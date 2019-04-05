"""[----------TEMPLATE---------- """
""" ----------TEMPLATE----------]""" 

"""[----------IMPORT---------- """
import wx
from VIZOP_Parser import *
""" ----------IMPORT----------]""" 

def main():
	#create GUI
    app = wx.App(False)
	#create Form
    frame = MyForm()
    frame.Show()
    app.MainLoop()

class MyForm(wx.Frame):

	def __init__(self):
		#initialise frame
		wx.Frame.__init__(self, None, wx.ID_ANY, "VIZOP Testing Menu")
		panel = wx.Panel(self, wx.ID_ANY)

		button = wx.Button(panel, id=wx.ID_ANY, label="Write test project")
		button.Bind(wx.EVT_BUTTON, self.onButton)
		
	def onButton(self, event):
		#on-click event
		testCreateProject()
		pass
 
# Run the program

"""[----------TESTING AREA---------- """

def testCreateProject():
	#Initiate id of objects

	Node.cur_node_id = 1
	Bookmark.cur_bookmark_id = 1
	Comment.cur_comment_id = 1
	
	Bookmark1 = Bookmark(isBookmarked = True)
	Comment1 = Comment('Comment test')
	
	#<Project>
	Project = createNode(input_ParentNodes = set([]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'Project', input_node_values = ['VIZOP'])
		#<VizopProject>
	VizopProject = createNode(input_ParentNodes = set([Project]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'VizopProject', input_node_values = [])
			#<VizopProject_Version>
	VizopProject_Version = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'VizopVersion', input_node_values = ['1.0'])
			#<VizopProject_ShortTitle>
	VizopProject_ShortTitle = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ShortTitle', input_node_values = ['V'])
			#<ProjectNumber>
	ProjectNumber = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectNumber', input_node_values = ['0001'])
			#<ProjectEditNumber>
	ProjectEditNumber = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'EditNumber', input_node_values = ['0001'])
			#<ProjectName>
	ProjectName = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'VizopVersion', input_node_values = ['1.0'])
			#<ProjectDescription>
	ProjectDescription = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectDescription', input_node_values = ['The purpose of this project is to...'])

			#<ProjectTeamMembers>
	ProjectTeamMembers = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMembers', input_node_values = [])
				#<ProjectTeamMember>
	ProjectTeamMember = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMember', input_node_values = [])
					#<ProjectTeamMemberID>
	ProjectTeamMemberID = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberID', input_node_values = ['1'])
					#<ProjectTeamMemberName>
	ProjectTeamMemberName = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberName', input_node_values = ['John'])
					#<ProjectTeamMemberRole>
	ProjectTeamMemberRole = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberRole', input_node_values = ['Team Lead'])
					#<ProjectTeamMemberAffiliation>
	ProjectTeamMemberAffiliation = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberAffiliation', input_node_values = ['Mary'])
					#<ProjectTeamMember>
	ProjectTeamMember = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMember', input_node_values = [])
					#<ProjectTeamMemberID>
	ProjectTeamMemberID = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberID', input_node_values = ['2'])
					#<ProjectTeamMemberName>
	ProjectTeamMemberName = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberName', input_node_values = ['Mary'])
					#<ProjectTeamMemberRole>
	ProjectTeamMemberRole = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberRole', input_node_values = ['Consultant'])
					#<ProjectTeamMemberAffiliation>
	ProjectTeamMemberAffiliation = createNode(input_ParentNodes = set([ProjectTeamMembers]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ProjectTeamMemberAffiliation', input_node_values = ['John'])

			#<ProcessUnit>
	ProcessUnit = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Process_Unit', input_node_kind = 'User', input_node_tag_name = 'ProcessUnit', input_node_values = [])
				#<ProcessUnit_ID>
	ProcessUnit_ID = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Number', input_node_kind = 'User', input_node_tag_name = 'ID', input_node_values = ['0001'])
				#<ProcessUnit_UnitNumber>
	ProcessUnit_UnitNumber = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'UnitNumber', input_node_values = ['John'])
				#<ProcessUnit_ShortName>
	ProcessUnit_ShortName = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ShortName', input_node_values = ['UnitShortName'])
				#<ProcessUnit_LongName>
	ProcessUnit_LongName = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'LongName', input_node_values = ['UnitLongName'])
	
			#<RiskReceptor>
	RiskReceptor = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'Process_Unit', input_node_kind = 'User', input_node_tag_name = 'RiskReceptor', input_node_values = [])
				#<RiskReceptor_ID>
	RiskReceptor_ID = createNode(input_ParentNodes = set([RiskReceptor]), input_ChildNodes = set([]), input_node_type = 'Number', input_node_kind = 'User', input_node_tag_name = 'ID', input_node_values = ['0001'])
				#<RiskReceptor_HumanName>
	RiskReceptor_HumanName = createNode(input_ParentNodes = set([RiskReceptor]), input_ChildNodes = set([]), input_node_type = 'Number', input_node_kind = 'User', input_node_tag_name = 'HumanName', input_node_values = ['0001'])

			#<PHAObject>
	PHAObject = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'PHAObject', input_node_values = [])
				#<FT>
	FT = createNode(input_ParentNodes = set([PHAObject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'PHAObject')
				#<AlarmRationalization>
	AlarmRationalization = createNode(input_ParentNodes = set([PHAObject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'PHAObject')
	
			#<NumberingSystem>
	NumberingSystem = createNode(input_ParentNodes = set([VizopProject]), input_ChildNodes = set([]), input_node_type = 'PHA_Object', input_node_kind = 'User', input_node_tag_name = 'NumberingSystem', input_node_values = [])
				#<NumberingSystem_ID>
	NumberingSystem_ID = createNode(input_ParentNodes = set([NumberingSystem]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'ID', input_node_values = [])
				#<Chunk>
	NumberingSystem_Chunk = createNode(input_ParentNodes = set([NumberingSystem]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'Chunk', input_node_values = [])
					#<Type>
	NumberingSystem_Chunk_Type = createNode(input_ParentNodes = set([NumberingSystem]), input_ChildNodes = set([]), input_node_type = 'Name', input_node_kind = 'User', input_node_tag_name = 'Type', input_node_values = ['str'])
						#<strValue>

	print ('getNumberOfInstance:{}'.format(getNumberOfInstance(Node)))
	print ('convertProjectToXml:{}'.format(convertProjectToXml(Project)))

""" ----------TESTING AREA----------]"""  

"""[----------RUN MAIN PROGRAM---------- """
if __name__ == '__main__':
	main()
"""----------RUN MAIN PROGRAM----------] """
