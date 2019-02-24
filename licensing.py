# -*- coding: utf-8 -*-
# This file is part of Vizop. Copyright 2018 xSeriCon. Almost the same as SILability licensing module.

"""Vizop licensing module
This module contains functions for license handling.
"""

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import uuid, urllib2, socket
try:
	import xml.etree.ElementTree as ElementTree # used for parsing XML returned from licensing server
except ImportError:
	import ElementTree # a MacOS workaround needed up to 10.12.6, may not be needed any more

# SILability modules
import info, settings

MachineID = str(uuid.getnode())

def TextAsString(XMLTag): # return text from XMLTag. If empty (no text) or tag doesn't exist, returns ''
	# (We use this procedure because just calling XMLTag.text will return None if text is empty)
	# A similar procedure is provided in module projects (not imported as it causes import problems)
	if XMLTag is None: return ''
	else:
		T = XMLTag.text
		return {True: '', False: T}[T is None]

def CheckLicenseStatusOnServer(LicenseKey):
	# interrogate license server to get data about validity of license.
	# return Allow (bool), Status (str), EndDate (str: yyyy-mm-dd), Options (str), Msg (str) fields from getstatus.php call
	global MachineID
	SILabilityID = info.SOFTWARE_CODE_FOR_LICENSING
	SILabVersion = info.VERSION
	LicenseCheckURL = info.LICENSE_CHECK_URL
	if InternetAvailable(): # <bypass> here if necessary by adding: and False
		# strip out all invalid chars from license key, leaving only A~Z, a~z, 0~9, - and _
		ValidChars = [chr(x) for x in range(48, 58)] + [chr(x) for x in range(65, 91)] +\
					 [chr(x) for x in range(97, 123)] + ['-', '_']
		LicenseKey = ''.join([c for c in LicenseKey if c in ValidChars])
		try: # to trap problem of unable to reach license server, or server returns HTTP error 500
			ServerDataObj = urllib2.urlopen(LicenseCheckURL + '?deviceid=%s' % MachineID + '&prodid=%s' % SILabilityID \
				+ '&lic=%s' % LicenseKey + '&verid=%s' % SILabVersion + '&out=xml')
			ServerResponded = True
		except: ServerResponded = False # if unable to get valid response from licensing server
		if ServerResponded:
			# fetch and parse XML data returned from ServerDataObj
			try: # to trap problems with ElementTree.parse seen in some old versions of MacOS
				LicenseCheckReturnData = ElementTree.parse(ServerDataObj)
				Allow = LicenseCheckReturnData.find('Allow').text
				Status = TextAsString(LicenseCheckReturnData.find('Status'))
				EndDate = TextAsString(LicenseCheckReturnData.find('EndDate'))
				Options = TextAsString(LicenseCheckReturnData.find('Options'))
				Msg = TextAsString(LicenseCheckReturnData.find('Msg'))
			except: # unable to use XML parser
				Allow = 'false'
				Status = 'XMLParserFailed'
				EndDate = ''
				Options = ''
				Msg = ''
		else: # unable to get valid response from licensing server
			Allow = 'false'
			Status = 'NoResponseFromServer'
			EndDate = ''
			Options = ''
			Msg = ''
		return (Allow == 'true'), Status, EndDate, Options, Msg
	else: # can't access internet to check license
		# return False, 'NoInternet', '', '', ''
		print "LI70 licence check bypassed"
		return True, '', '', 'Licensed', '' # for emergency <bypass>

def GetLicenseStatus(WelcomeFrame, LicenseKey):
	# check license and inform user of progress in welcome frame
	# WelcomeFrame (instance of NoProjectOpenFrame): the welcome frame currently visible
	# LicenseKey (str): license key originally supplied by xSeriCon
	# returns (str) 'LicenseFullyValid', 'Unlicensed', 'Trial'; (str) message to user, translated
	Allow, Status, EndDate, Options, Msg = CheckLicenseStatusOnServer(LicenseKey)
	# convert all messages to lower case to avoid problems if a typo is made when setting up a license
	StatusLower = Status.lower()
	OptionsLower = Options.lower()
	MsgLower = Msg.lower()
	# case -1: we have internet access but license server timed out
	if (not Allow) and (StatusLower == 'noresponsefromserver'):
		Result = 'Unlicensed'
		MessageToUser = _("We're sorry, there's a problem with the licensing server. Try launching SILability again")
	# case 0: no internet access
	elif (not Allow) and (StatusLower == 'nointernet'):
		Result = 'Unlicensed'
		MessageToUser = _('Please connect to the internet to allow SILability to authorize your license')
	# cases 1, 6 and 9: no license key provided
	elif (Allow and (StatusLower == 'trial')) or ((not Allow) and (StatusLower == 'trialexpired')):
		Result = 'Unlicensed'
		MessageToUser = _('Your copy of SILability is unlicensed. Please enter your license key')
	# case 2: valid license key for trial
	elif Allow and (OptionsLower == 'xsericontrial'):
		Result = 'Trial'
		MessageToUser = _('You have a trial license. Please contact xSeriCon if you would like to purchase a full license')
	# case 3: expired trial license key
	elif (not Allow) and (StatusLower == 'revoked'):
		Result = 'Unlicensed'
		MessageToUser = _('Your trial has expired. Please contact xSeriCon if you would like to purchase a full license')
	# case 4: valid full license key
	elif Allow and (OptionsLower == 'licensed'):
		Result = 'LicenseFullyValid'
		MessageToUser = _('Your copy of SILability is fully licensed')
	# case 5: expired full license key
	elif (not Allow) and (StatusLower == 'expired'):
		Result = 'Unlicensed'
		MessageToUser = _('Your license has expired. Please contact xSeriCon if you would like to renew your license')
	# cases 7 and 8: invalid license key, or wrong major version of SILability
	elif (not Allow) and ('license not found' in MsgLower):
		Result = 'Unlicensed'
		MessageToUser = _("Sorry, your license key didn't work. Please contact xSeriCon for assistance")
	# case 10: license key already in use on another device
	elif (not Allow) and (StatusLower == 'invalidlicenseid'):
		Result = 'Unlicensed'
		MessageToUser = _("Your license key is already registered to another computer. Please contact xSeriCon for assistance")
	# case 11: Device ID key already has changed
	elif (not Allow) and (StatusLower == 'invaliddeviceid'):
		Result = 'Unlicensed'
		MessageToUser = _("Your computer seems to have changed. Please contact xSeriCon for licensing assistance")
	# case 12: XML parser failed
	elif (not Allow) and (StatusLower == 'xmlparserfailed'):
		Result = 'Unlicensed'
		MessageToUser = _('SILability hit a compatibility problem. Please contact xSeriCon for assistance')
	# any other case:
	else:
		Result = 'Unlicensed'
		MessageToUser = _("Sorry, there's a problem with your license. Please contact xSeriCon for assistance")
	return Result, MessageToUser

def GetLicenseKeyFromConfigData():
	# retrieve and return stored license key from the user's config data
	# returns default (see settings module) if no key has been stored
	sm = settings.SettingsManager()
	return sm.get_config('License_Key')

def StoreLicenseKeyInConfigData(LicenseKey):
	# store a new license key (str) in user's config data file
	assert isinstance(LicenseKey, str)
	sm = settings.SettingsManager()
	ce = sm.get_config_editor()
	ce.set_config('License_Key', LicenseKey)
	ce.apply_changes() # save config changes in SettingsManager

def InternetAvailable():
	# check if SILability can reach the internet. Return bool (True if internet reached)
	# following method at http://stackoverflow.com/questions/3764291/checking-network-connection
	# it works by trying to set up a socket connection to a DNS, 8.8.8.8 over port 53/tcp.
	# This will time out in 1 second if not available.
	try:
		socket.setdefaulttimeout(1)
		socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
		return True
	except Exception as ex:
		pass
	return False