# -*- coding: utf-8 -*-
# This file is part of vizop. Copyright Peter Clarke, 2015

"""vizop messaging module
This module contains functions for communications between display models and the data core. Not currently used.
"""

# library modules
from __future__ import division # makes a/b yield exact, not truncated, result. Must be 1st import
import zmq # if this import fails, see instructions in "zeromq info" in vizop supporting docs

# initialize messaging
ZMQContext = zmq.Context()
# initialize publish/subscribe server and bind it for publishing
MaxSocketNumber = 5556 # highest socket number used so far
PubSubSocket = ZMQContext.socket(zmq.PUB)
PubSubSocket.bind("tcp://*:%d" % MaxSocketNumber)


def InitializeMessagingForNewDisplayDevice(DisplDevice): # set up zmq messaging with DisplDevice
	# Before calling this routine, DisplDevice needs to be created
	# First, establish two-way private communication with a REP/REQ socket
	DisplDevice.ZMQSocket = ZMQContext.socket(zmq.REP) # create socket
	MaxSocketNumber += 1
	ThisSocketNumber = MaxSocketNumber
	DisplDevice.ZMQSocket.bind("tcp://*:%d" % ThisSocketNumber) # bind to socket as server
	DisplDevice.ConnectToSockets(ThisSocketNumber) # get DisplDevice to connect to private socket and Pub/Sub socket
	# make sure the private and PubSub sockets are up and running
	# DisplDevice should listen on both sockets, subscribe to "NewKid" on the PubSub socket,
	# and reply 'Ack Handshake' on the private socket when it gets the Handshake message on both
	Connected = False
	ConnectTries = 10
	while (not Connected) and ConnectTries:
		DisplDevice.ZMQSocket.send("Handshake")
		DisplDevice.PubSubSocket.send("NewKid Handshake")
		DisplDevice.Handshake() # request device to read messages
		Reply = DisplDevice.ZMQSocket.recv(zmq.DONTWAIT)
		Connected = (Reply == 'Ack Handshake')
		ConnectTries -= 1
	if not Connected: # failure after many tries
		print "Oops, communication failure with display device (problem code ME40)"


