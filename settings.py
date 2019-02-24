# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright xSeriCon, 2018
"""
The settings module deals with storing persistent data across program restarts and
also for handling configuration options for Vizop. Almost all of the functionality
is accessed through the _SettingsManager class which should be created using the 
SettingsManager function (to ensure only one instance of it exists). See the 
docstrings for _SettingsManager for details.
"""

import atexit
import os.path
import pickle
import warnings
import copy
import configparser
import inspect
import weakref

# vizop modules needed
from utilities import str_to_bool
import info, vizop_misc

class VizopConfig:
	"""
	Container class for Vizop configs. All args must be strings.
	
		*name - name of the config (must be unique)
		*datatype - data type of config e.g. 'float', 'bool' etc.
		*section - the section of the config files that it should appear under 
				   e.g. 'Interface_Behaviour'
		*default - the default value for this config. This will be used if the
				   the config is not specified in either of the config files
		*desc - a simple description of what changing this config will do (not translated as we assume it's not visible to user)
	
	"""
	def __init__(self, name, datatype, section, default, desc):
		# all args must be strings - double check that here
		for arg in [name, datatype, section, default, desc]:
			assert isinstance(arg, str), "All arguments to VizopConfig() must be strings."
		
		# value must be convertible to its correct data type - check here
		try:
			_validators[datatype](default)
		except ValueError:
			raise ValueError("Default value \'%s\' is incompatible with its "
							 "datatype \'%s\'" % (default, datatype))
		except KeyError:
			raise ValueError("Failed to create config \'%s\'. No validator "
							 "function defined for datatype "
							 "\'%s\'" % (name, datatype))   
		
		self.name = name
		self.datatype = datatype
		self.section = section
		self.value = default
		self.desc = desc



#dict of validator functions that convert string config values into their 
#proper datatypes. These functions should raise ValueError if the
#string cannot be converted
_validators = {
			   'bool': str_to_bool,
			   'int': int,
			   'float': float,
			   'str': str
			   }


#list of config objects. All configs that are to be used by Vizop MUST be
#listed here.
_configs = [
			VizopConfig('RecentProjectsListMaxSize', 'int', 'History', '10',
					   'Max number of entries in the recent projects list'),
			VizopConfig('ProjFileExt', 'str', 'Files','vip',
					   'File extension for project files'),
			VizopConfig('CanvasMaxX', 'int', 'Interface_Behaviour', '10000',
					   'Arbitrary limit on x coordinate of graphical objects'),
			VizopConfig('CanvasMaxY', 'int', 'Interface_Behaviour', '10000',
					   'Arbitrary limit on y coordinate of graphical objects'),
			VizopConfig('CanvasMinX', 'int', 'Interface_Behaviour', '-10000',
					   'Arbitrary limit on x coordinate of graphical objects'),
			VizopConfig('CanvasMinY', 'int', 'Interface_Behaviour', '-10000',
					   'Arbitrary limit on y coordinate of graphical objects'),
			VizopConfig('NewProjDir', 'str', 'File_Handling', '',
					   'Default directory shown in file open/store dialogues')
			]


class _SettingsManager:
	"""
	This is the main class used to deal with persistent settings in Vizop and
	is probably the only thing you need to use in this module. The class should
	not be created directly, instead use the SettingsManager() function to 
	get a reference to the global instance of the _SettingsManager class. This
	ensures that only one _SettingsManager exists per program.
	
	There are two types of persistent variables in Vizop: values, and configs.
	
		values:
		  These are global read/write variables for the program to use to store
		  state across program re-starts. They are not supposed to be used for
		  user specified values. They are manipulated using the get_value() and 
		  set_value() methods. No guarantee is made that these variables will 
		  exist, nor that their value will be what you expect. As such, all 
		  calls to get_value() should be protected by try-except blocks and you
		  should be prepared to use a default value instead if the method 
		  cannot retrieve the variable you asked for. Persistence is achieved
		  using the pickle module, so in theory any object can be stored using
		  values. Calling set_value() is enough to ensure persistence (provided
		  that the program does not crash horribly afterwards), the values will
		  be saved to file automatically when the program exits, and reloaded on
		  startup.
		  
		  example:
			  sm = SettingsManager()
			  sm.set_value("last_dir_used","/home/me/Vizop")
			  ---program restart---
			  sm = SettingsManager()
			  print sm.get_value("last_dir_used")
			  "/home/me/Vizop"
		  
		  
		configs:
		  These are global settings that are used to store user preferences. 
		  They are not for storing program state (use values for this), and 
		  should be treated as read-only. They can be written to, but this is
		  reserved for a user preferences editor. Unlike values, configs are
		  guaranteed to exist and will always have the expected data type. 
		  All configs must therefore be listed in the _configs list in this 
		  module along with their default values and data types. The defaults
		  can then be overridden by the user by specifying new values for them
		  in either a system wide config file, or a user space config file.
		  Values specified in the user space file will override values specified
		  in the system config file, which in turn will override the hardcoded 
		  values. Configs are accessed using the get_config() method. 
		  
		  Additionally, there are methods for registering callback functions to
		  be run if/when the user decides to change the value of a config. This
		  allows changes to be easily propagated across the program.
	"""
	def __init__(self):
		#setup _save() to be run when the program exits. This just stores
		#the cache file - see _ConfigEditor class for saving config files
		atexit.register(self._save)
		
		self.__sys_config_file = os.path.join(vizop_misc.get_sys_runtime_files_dir(),
											  "%s.cfg" % info.PROG_SHORT_NAME)
		
		self._usr_config_file = os.path.join(vizop_misc.get_usr_runtime_files_dir(),
											  "%s.cfg" % info.PROG_SHORT_NAME)
		
		self.__cache_file = os.path.join(vizop_misc.get_usr_runtime_files_dir(), 'cache')
		
		self._usr_config = configparser.ConfigParser()
		self.__sys_config = configparser.ConfigParser()
		self.__config_editor = _ConfigEditor(self)
		self.__callbacks = {}
		self.__callback_ids = {}
		
		self._default_configs = {}
		for cfg in _configs:
			#don't allow multiple definitions with the same name
			assert cfg.name not in self._default_configs, ("Multiple definitions of config \'%s\'" % cfg.name)
			self._default_configs[cfg.name] = cfg
		
		self._load_config_files()
		
		#attempt to load the cached values from the cache file
		try:
			with open(self.__cache_file, "rb") as ifp:
				self.__cached_values = pickle.load(ifp)
		
		except:
			self.__cached_values = {}
		
			   
	def _save(self):
		"""
		Writes the values to a file. This is called automatically on program exit.
		"""
		try:
			with open(self.__cache_file, "wb") as ofp:
				pickle.dump(self.__cached_values, ofp)
		except Exception as e:
			print("settings: Failed to save the cache file \'%s\' pickle.dump() reports \'%s\'" % (self.__cache_file, e.args))

	
	def _load_config_files(self):
		"""
		Loads both the user space and system wide config files if they exist and 
		are not empty.
		"""
		self.__sys_config.read(self.__sys_config_file)
		self._usr_config.read(self._usr_config_file)
	
	
	def get_value(self, name):
		"""
		Returns a deepcopy of the value with the specified name. 
		Raises KeyError if no value with this name exists. The data type
		of the returned value will be whatever was last stored in it - you
		are advised to check that it is what you were expecting!
		
		Also, there is no guarantee that this method will be able to locate
		the value that you asked for - so you should handle KeyErrors
		gracefully and specify your own default value.
		"""
		return copy.deepcopy(self.__cached_values[name])

	
	def set_value(self, name, value):
		"""
		Sets the specified value. "name" must be a hashable
		object.
		"""
		self.__cached_values[name] = copy.deepcopy(value)
	
	
	def get_config(self, name):
		"""
		Returns a value for the named config. 'name' must be the name of
		one of the configs in the _configs list in this module. This method
		will always return a value for the config of the correct datatype. 
		Values specified in the user space config file will be returned in 
		preference to those specified in the system wide config file. If neither
		file specifies the config, the a default value will be returned.
		"""
		try:
			default_cfg = self._default_configs[name]
			validator = _validators[default_cfg.datatype]
		except KeyError:
			raise KeyError("No config defined with name \'%s\'" % name)
		
		#first look to see if the config is defined in the user config file
		if self._usr_config.has_option(default_cfg.section, name):
			try:
				return validator(self._usr_config.get(default_cfg.section, name))
			except ValueError:
				warnings.warn("Failed to convert config \'%s\' defined in "
							  "\'%s\' to type \'%s\'. Falling back to "
							  "default value." % (name, self._usr_config_file,
												default_cfg.datatype))
		
		#now look to see if it is in the system config file
		if self.__sys_config.has_option(default_cfg.section, name):
			try:
				return validator(self.__sys_config.get(default_cfg.section, name))
			except ValueError:
				warnings.warn("Failed to convert config \'%s\' defined in "
							  "\'%s\' to type \'%s\'. Falling back to "
							  "default value." % (name, self.__sys_config_file,
												default_cfg.datatype))
		#since it is not defined anywhere else, return the default value
		return validator(default_cfg.value)
	
	
	def __remove_broken_proxy_callbacks(self):
		"""
		Searches the list of callbacks for proxies of class methods whose class
		instance has been deleted, and removes them. 
		"""
		for _id, val in self.__callback_ids.items():
			names, func = val
			if isinstance(func, WeakRefCallbackProxy):
				if func.is_broken():
					print("SettingsManager: Auto-removing callback <%s> with "
						   "ID %d on the following configs: %s"%(func.__name__, _id, names))
					self.unregister_config_change_callback(_id)
				
	
	def register_config_change_callback(self, name, func):
		"""
		Register a callback function to be executed when the named config is 
		changed. If None is passed as the name argument, then the callback
		will be run if ANY of the configs are changed.
		
		Returns a unique ID (integer) for this callback, which can be used to
		unregister it at a later time if you wish. If you register a class
		method as the callback, then it will automatically be unregistered 
		when the associated class instance gets garbage collected.
		
		As many callbacks can be registered for a given name as you like. There
		is also nothing to stop you from registering the same function multiple
		times for the same name - it will only ever be executed once per config 
		change though.
		
		  *name - the name of a config, or None
		  *func - any callable (which takes no arguments)
		  
		"""
		#make sure that the specified func is callable
		assert callable(func), "func argument must be callable"
		
		#if the callback is a class method, then it needs special treatment - otherwise
		#the reference we store to the class instance in the callbacks list will prevent it 
		#from ever being garbage collected. Instead we create a proxy object to the class
		#method which uses weak references to prevent this from happening. The list of 
		#callbacks is searched for broken proxies each time get_callbacks() is called - so
		#we don't have to worry about unregistering callbacks before objects get destroyed.
		if inspect.ismethod(func):
			if not hasattr(func, '__name__'):
				raise ValueError("Cannot register class methods that do not have" 
								 " a __name__ attribute as callbacks")
				
			func = WeakRefCallbackProxy(weakref.ref(func.__self__),
										func.__name__)
		
		#create a new ID for this callback. These must all be unique within one
		#run of the program, otherwise you could get strange behaviour when you
		#unregister due to autoderegistering
		current_ids = self.__callback_ids.keys()
		if current_ids:
			_id = max(current_ids)+1
		else:
			_id = 0
		
		if name is None:
			#then register the callback for all config names
			names_to_register_for = self._default_configs.keys()
		else:
			#check that the specified config actually exists
			if name not in self._default_configs:
				raise KeyError("Cannot set callback for \'%s\'. "
							   "No such config." % name)
			names_to_register_for = [name]
		
		self.__callback_ids[_id] = ([],func) #([list of names], callback)
		
		for cfg_name in names_to_register_for:		
			if cfg_name not in self.__callbacks:
				self.__callbacks[cfg_name] = []
			
			#note that we allow the list of callbacks to have multiple entries
			#of the same callable. This is deliberate to prevent one call to 
			#unregister from removing callbacks that may have been registered
			#from other places. However, even if there are multiple instances
			#of the same callable, it will only be executed once.
			self.__callbacks[cfg_name].append(func)
			self.__callback_ids[_id][0].append(cfg_name)
				
		return _id
	
	
	def unregister_config_change_callback(self,_id):
		"""
		Remove a callback function that has previously been registered.
		
		Important! If the callback was an instance method, then it will be
		automatically unregistered when the instance is deleted (i.e. when its
		reference count falls to 0). If try to unregister the callback after the
		instance has been deleted then you will get a ValueError, since it will
		have already been unregistered.
		
		   *_id - the id returned by register_config_change_callback() when
				  you registered the callback.
		"""
		
		#check that _id is an integer
		assert isinstance(_id, int)
		
		#check that this id exists
		if _id not in self.__callback_ids:
			raise ValueError("No callback registered with ID %d"%_id)
		
		#remove the callback
		names, func = self.__callback_ids[_id]
		for cfg_name in names:
			try:
				self.__callbacks[cfg_name].remove(func)
			except (KeyError, ValueError):
				raise ValueError("\'%s\' was not registered as a callback for "
								 "config \'%s\'" % (func.__name__, cfg_name))
		
		self.__callback_ids.pop(_id)
	
	
	def get_callbacks(self):
		"""
		Returns a copy of the callbacks dict object which has the form:
		{'name':[callable_1, callable_2], 'name2':[]}
		"""
		self.__remove_broken_proxy_callbacks()
		return self.__callbacks.copy()
		
	
	def get_config_editor(self):
		"""
		Returns a _ConfigEditor object, which can be used for setting the values
		of configs. See the docstring for _ConfigEditor.
		"""
		return self.__config_editor

	
	def get_usr_config_filename(self):
		"""
		Returns the filename of the user space config file. Note that this file
		may not exist.
		"""
		return self._usr_config_file
	
	
	def get_sys_config_filename(self):
		"""
		Returns the filename of the system wide config file. Note that this file
		may not exist.
		"""
		return self._sys_config_file



class _ConfigEditor:
	"""
	The ConfigEditor class allows the values of configs to be changed.
	The idea is to provide a way for a user preferences window to store
	user input values for the various configs. This class should not be 
	created directly - instead use the _SettingsManager.get_config_editor()
	method. The values of configs are manipulated using set_config(), however,
	no changes will be made until apply_changes() is called. This allows you to
	edit many configs without all the callbacks being executed every time.
	
	Note that this class only allows you to change configs in the user space
	file. There is no mechanism for editing the system wide config file yet - 
	this would require root access anyway, so probably has to be done externally.
	"""
	def __init__(self, settings_manager):
		self.settings_manager = settings_manager
		self.__changed_configs = set([])
	
	
	def cancel_changes(self):
		"""
		Cancel any pending changes to the configs.
		"""
		self.__changed_configs = set([])
	
	
	def apply_changes(self):
		"""
		Write any changes to the configs to the user space config file and
		run any necessary callbacks.
		"""
		if self.__changed_configs:
			self.__write_configs_to_file()
			self.settings_manager._load_config_files()
			callbacks = self.settings_manager.get_callbacks()
			
			#build a list of unique callbacks for the changed configs 
			unique_callbacks = set([])
			while self.__changed_configs:
				cfg = self.__changed_configs.pop() #name of changed config
				try:
					for func in callbacks[cfg]:
						unique_callbacks.add(func)
				except KeyError:
					#there was no callback registered for this config
					pass
				
			#now run any callbacks for configs that have changed
			for func in unique_callbacks:
				try:
					func()
				except ReferenceError:
					print("Failed to run callback - missing object")
					#the function is a weak reference to a callable that has expried, skip it
					pass
				except Exception as e:
					warnings.warn("Failed to execute callback \'%s\'. Callable"
								  " reported %s." % (func.__name__, e.args))

		
	def __write_configs_to_file(self):
		"""
		Stores the new configs to the user space config file. You should not
		call this method directly - use apply_changes() instead.
		"""
		with open(self.settings_manager._usr_config_file, 'w') as ofp:
			self.settings_manager._usr_config.write(ofp)
	
	
	def restore_all_defaults(self):
		"""
		This deletes all entries in the user space config file. Configs will
		go back to having their default values (or their values specified in the
		system wide config file). You do not need to call apply_changes() after
		calling this method.
		"""
		for section in self.settings_manager._usr_config.sections():
			for opt in self.settings_manager._usr_config.options(section):
				self.__changed_configs.add(opt)
			self.settings_manager._usr_config.remove_section(section)
		
		self.apply_changes()
	
	
	def set_config(self, name, value):
		"""
		Change the value of the config called 'name' to 'value'. The change will
		not be implemented until apply_changes() is called. Value must have the 
		correct datatype for the config (see the _configs list in this module).
		
		 *name - the name of the config to change
		 *value - the new value for the config. This may be a string representation
				  of the value e.g. 'true' or the value itself.
		 
		Raises ValueError if 'name' is not a valid config, or if 'value' does not
		have the correct data type.
		"""
		#check that a config with this name exists
		if name not in self.settings_manager._default_configs:
			raise ValueError("Cannot set \'%s\' to \'%s\'. No such config." % (name, value))
		
		default_cfg = self.settings_manager._default_configs[name]
		
		#check that the specified value is of the correct type
		try:
			actual_value = _validators[default_cfg.datatype](str(value))
			
		except ValueError:
			raise ValueError("Cannot set \'%s\' to \'%s\'. Expecting datatype "
							 "of \'%s\'." % (name, value, default_cfg.datatype))
		
		#check if the value of the config is actually being changed
		prev_val = self.settings_manager.get_config(name)
		if actual_value == prev_val:
			return
		
		#create the section in the config object if it doesn't already exist
		if not self.settings_manager._usr_config.has_section(default_cfg.section):
			self.settings_manager._usr_config.add_section(default_cfg.section)
		
		#set the new config value and flag it as having been changed
		self.settings_manager._usr_config.set(default_cfg.section, name, str(value))
		self.__changed_configs.add(name)
		


class WeakRefCallbackProxy:
	"""
	There is a problem when registering instance methods as callbacks because
	the reference held to the method by the SettingsManager will prevent the 
	instance from ever being garbage collected. Moreover, the callbacks will
	continue to be called after all "visible" references to the instance have
	been deleted. To get around this, instance methods are not registered as 
	callbacks, instead a WeakRefCallbackProxy is registered, which behaves the same
	as the instance method, except it only keeps a weak reference to the instance
	and so does not prevent it from being garbage collected.
	
	The SettingsManager will then automatically remove callbacks when the weak
	reference is no longer valid (i.e. when the class instance has been deleted).
	"""
	def __init__(self, proxy, method_name):
		self.__name__ = "WeakRefCallbackProxy of \'%s\'"%method_name
		self.proxy = proxy
		self.method_name = method_name
		
		obj = self.proxy()
		func = getattr(obj, self.method_name)
		
		#we need to cache the hash vaue now, because it's possible we will
		#need to compare the proxy (self) to another object after
		#the class instance associated with the proxy has been garbage collected
		self.hash_value = func.__hash__()
			
			
	def __call__(self):
		"""
		Calls the instance method that the proxy represents.
		"""
		#get a hard reference to the class instance
		obj = self.proxy()
		
		if obj is None:
			raise ReferenceError("Attempt to call <%s> after its associated"
								 " class instance has been deleted."%self.__name__)
		
		#retrieve the instance method that we need and call it
		func = getattr(obj, self.method_name)
		func()
	
	
	def __hash__(self):
		#return the hash value we cached in __init__
		return self.hash_value
	
	
	def __cmp__(self, o):
		#compare objects by hash value. FIXME uses obsolete cmp(), won't work
		return cmp(self.hash_value, o.__hash__())
	   
	   
	def is_broken(self):
		"""
		Returns True if the class instance associated with this proxy 
		has been garbage collected.
		"""
		if self.proxy() is None:
			return True
		return False
	
		
	   
def SettingsManager():
	"""
	Returns a reference to the global settings storage class. Which can be 
	used for storing settings across program restarts. See the docstring
	for _SettingsManager.
	"""
	if not hasattr(SettingsManager, 'global_settings_manager'):
		SettingsManager.global_settings_manager = _SettingsManager()

	return SettingsManager.global_settings_manager	
		
