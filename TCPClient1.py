from socket import socket
from sys import argv
from time import sleep
import json
import random

class State:
    CurrentContext = None
    def __init__(self, Context):
        self.CurrentContext = Context
    def trigger(self):
        return True

class StateContext:
    state = None
    CurrentState = None
    availableStates = {}

    def setState(self, newstate):
        try:
            self.CurrentState = self.availableStates[newstate]
            self.state = newstate
            self.CurrentState.trigger()
            return True
        except KeyError: #incorrect state key specified
            return False

    def getStateIndex(self):
        return self.state

class Transition:
    def synSent(self):
        print ("Error!")
        return False
    def established(self):
        print("Error!")
        return False

class Closed(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def synSent(self):
        self.CurrentContext.setState("SYN_SENT")
    def trigger(self):
        try:
            self.CurrentContext.socket.close()
            self.connection_address=0
            print("Connection Closed")
            return True
        except:
            return False

class synSent(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def established(self):
        self.CurrentContext.setState("ESTABLISHED")
    def makeConnection(self):
        self.CurrentContext.socket = socket()
        try:
            print("test")
            self.CurrentContext.socket.connect((self.CurrentContext.host, self.CurrentContext.port))
            self.CurrentContext.connection_address = self.CurrentContext.host
        except Exception as err:
            print(err)
            exit()
    def synAck(self):
        inbound = self.CurrentContext.recvpacket()
        if inbound["SYN"]== True and inbound["ACK"]== True:
            print("SYN+ACK received from ",self.CurrentContext.connection_address)
            self.CurrentContext.established()
    def trigger(self):
        self.makeConnection()
        self.CurrentContext.packet["SYN"] = True
        self.CurrentContext.sendpacket()
        self.synAck()
        return True

class established(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def finWait1 (self):
        self.CurrentContext.setState("FINWAIT1")
    def send (self,text):
        self.CurrentContext.packet["MSG"] = text
        self.CurrentContext.sendpacket()
    def streamData(self):
        while True:
            inbound = self.CurrentContext.recvpacket()
            print (inbound["MSG"])
            text = input("PLease enter something to send to server")
            if text == "CLOSE":
                print("Closing connection")
                self.CurrentContext.finWait1()
                return True
            self.send(text)
    def trigger(self):
        self.CurrentContext.packet["ACK"] = True
        self.CurrentContext.sendpacket()
        self.streamData()
        return True

class finWait1(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def finWait2(self):
        self.CurrentContext.setState("FINWAIT2")
    def trigger(self):
        self.CurrentContext.packet["FIN"] = True
        self.CurrentContext.sendpacket()
        print("Closing connection")
        inbound = self.CurrentContext.recvpacket()
        if inbound["ACK"]:
            self.CurrentContext.finWait2()
            return True
        else:
            return False

class finWait2(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def timedWait(self):
        self.CurrentContext.setState("TIMEDWAIT")
    def trigger(self):
        inbound = self.CurrentContext.recvpacket()
        if inbound["FIN"]:
            self.timeout()
            return True
        else:
            return False

class timedWait(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def closed(self):
        self.CurrentContext.setState("CLOSED")
    def trigger(self):
        self.CurrentContext.packet["ACK"] = True
        self.CurrentContext.sendpacket()
        sleep(2)
        print("Connection closed")
        self.CurrentContext.closed()

class TCPClient(StateContext, Transition):
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 5000
        self.connection_address = 0
        self.socket = None
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["SYN_SENT"] = synSent(self)
        self.availableStates["ESTABLISHED"] = established(self)
        self.availableStates["FIN_WAIT1"] = finWait1(self)
        self.availableStates["FIN_WAIT2"] = finWait2(self)
        self.availableStates["TIMEOUT"] = timedWait(self)
        self.setState("CLOSED")
        self.packet = {
            "SYN": False,
            "ACK": False,
            "FIN": False,
            "MSG":"",
            "seq num":random.randint(0000,9999),
            "Ack num":0
        }

    def resetflags(self):
        self.packet["SYN"] = False
        self.packet["ACK"] = False
        self.packet["Fin"] = False
        self.packet["MSG"] = ""
    def sendpacket(self):
        outbound = json.dumps(self.packet)
        self.socket.send(outbound.encode())
        self.resetflags()
    def recvpacket(self):
        inboundpacket = self.socket.recv(1024)
        inboundpacket = inboundpacket.decode()
        inboundpacket = json.loads(inboundpacket)
        if inboundpacket["Ack num"] != self.packet["seq num"]-1 and self.packet["Ack num"]!=0:
            print("Error! Sequence number does not match acknowledgement number")
        self.packet["Ack num"] = inboundpacket["seq num"]
        return inboundpacket

    def closed(self):
        return self.CurrentState.closed()
    def synSent(self):
        return self.CurrentState.synSent()
    def established(self):
        return self.CurrentState.established()
    def finWait1(self):
        return self.CurrentState.finWait1()
    def finWait2(self):
        return self.CurrentState.finWait2()
    def timedWait(self):
        return self.CurrentState.timedWait()

if __name__=="__main__":
    client = TCPClient()
    print("Running client")
    client.synSent()
