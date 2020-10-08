# -*- coding: utf-8 -*-
# Module: socket_test. This file is part of Vizop. Copyright xSeriCon, 2017
# Minimal test to get communications on REQ/REP socket pairs working.

"""
The controlframe module contains code for the main Vizop control and navigation screen.
"""

# standard modules needed:
import zmq, vizop_misc, time

def ProcessRequest(MessageReceived):
    print("13 Request received: ", MessageReceived)
    return vizop_misc.MakeXMLMessage("Thanks")

def ProcessReply(MessageReceived):
    print("17 Reply received: ", MessageReceived)
    return vizop_misc.MakeXMLMessage("Got it")

print("12 Starting socket_test")
zmqContext = zmq.Context() # context for communications sockets. Must be only 1 instance for whole of Vizop instance
RemoteREQSocket, RemoteREQSocketObj = vizop_misc.SetupNewSocket(SocketType='REQ', SocketLabel='RemoteREQ',
    DispModel=None, PHAObj=None, SocketNo=None, BelongsToDatacore=True, AddToRegister=True)
LocalREPSocket, LocalREPSocketObj = vizop_misc.SetupNewSocket(SocketType='REP', SocketLabel='LocalREP', DispModel=None,
    PHAObj=None, SocketNo=RemoteREQSocketObj.SocketNo, BelongsToDatacore=False, AddToRegister=True)
print("17 Sending request")
vizop_misc.SendRequest(Socket=RemoteREQSocket, Command='RQ_Null')
time.sleep(1)
vizop_misc.ListenToSocket(LocalREPSocket, Handler=ProcessRequest, SendReply2=True)
time.sleep(1)
vizop_misc.ListenToSocket(RemoteREQSocket, Handler=ProcessReply, SendReply2=False)
print("31 finished")
