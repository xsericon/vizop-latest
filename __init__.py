# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright 2015 xSeriCon

import os.path
import sys
import warnings
import gettext
import info
import vizop

try:
	from vizop.build_info import DATA_DIR
except ImportError:
	#if the vizop installer script hasn't been run yet, then the build_info module
	#will not exist. In this case, define the DATA_DIR to be the root directory
	#of the vizop package, this should allow it to be executed successfully without
	#requiring installation
	script_dir = os.path.dirname(info.__file__)
	DATA_DIR = os.path.join(script_dir, os.path.pardir, os.path.pardir, os.path.pardir)
	warnings.warn("No build_info module found. Defaulting to %s as the runtime files directory"%os.path.abspath(DATA_DIR))


def get_usr_runtime_files_dir():
	"""
	Returns the complete path to the directory that vizop uses to store 
	user specific files needed at runtime. This is platform dependent, 
	but on Linux it will be ${HOME}/.vizop
	"""
	if sys.platform == 'win32':
		#Windows doesn't really do hidden directories, so get rid of the dot
		return os.path.join(os.path.expanduser('~'),"%s"%info.PROG_SHORT_NAME)
	else:
		return os.path.join(os.path.expanduser('~'),".%s"%info.PROG_SHORT_NAME)



def get_sys_runtime_files_dir():
	"""
	Returns the complete path to the directory that vizop uses to store 
	user independent files needed at runtime. This is platform dependent, 
	but on Linux it will probably be /usr/local/share/vizop
	"""
	return os.path.join(DATA_DIR, info.PROG_SHORT_NAME)


#install _() into Python's global namespace so that we can use gettext to 
#translate the entire application without having to initialise it in every module
gettext.install(info.PROG_SHORT_NAME, os.path.join(get_sys_runtime_files_dir(),'locale'))
