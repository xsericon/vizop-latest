#!/usr/bin/python

# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright xSeriCon, 2015

"""Initial startup checks. Not currently used; all code moved to module vizop"""

import os.path
import wx

import startup_vizop, vizop_misc, info

if __name__ == '__main__':


	#check existence and readability of runtime directories.
	sys_runtime_dirs = [os.path.join(vizop_misc.get_sys_runtime_files_dir(), info.IconFolderTail),
						os.path.join(vizop_misc.get_sys_runtime_files_dir(), 'locale')]

	if not os.path.isdir(vizop.get_usr_runtime_files_dir()):
		os.makedirs(vizop.get_usr_runtime_files_dir())


	for d in sys_runtime_dirs:
		if not os.path.isdir(d) and os.access(d, os.R_OK):
			#this is likely a fatal error - there is something wrong with
			#the installation
			wx.MessageBox("%s is missing or unreadable."%d, info.PROG_NAME, wx.ICON_ERROR)

			#can't translate this message - might be missing our language files
			raise RuntimeError("%s is missing or unreadable."%d)

	print ("Installed gettext handler at localedir: ", os.path.join(vizop_misc.get_sys_runtime_files_dir(),'locale'))

	startup_vizop.launch_gui(app)
