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
    def closed(self):
        print("Error!")
        return False
    def listen(self):
        print ("Error!")
        return False
    def syn_recvd(self):
        print ("Error!")
        return False
    def established(self):
        print ("Error!")
        return False
    def closeWait(self):
        print("Error!")
        return False
    def lastack(self):
        print ("Error!")
        return False

class Closed(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def listen(self):
        print("Going to listen")
        self.CurrentContext.setState("LISTEN")
    def trigger(self):
        try:
            self.CurrentContext.socket.close()
            self.connection_address = 0
            print('Connection Closed')
            return True
        except:
            return False

class Listen(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def syn_recvd (self):
        self.CurrentContext.setState("SYN_RECIEVED")
    def synack(self):
        inbound = self.CurrentContext.recvpacket()
        if inbound["SYN"]:
            print ("Recieved SYN from ",self.CurrentContext.connection_address)
            self.CurrentContext.syn_recvd()
        else:
            print("Connection failed, Terminating testing")
            self.CurrentContext.setState("CLOSED")
    def trigger(self):
        self.CurrentContext.socket = socket()
        try:
            self.CurrentContext.socket.bind((self.CurrentContext.host,self.CurrentContext.port))
            self.CurrentContext.socket.listen(1)
            self.CurrentContext.connection , self.CurrentContext.connection_address = self.CurrentContext.socket.accept()
            self.synack()
            return True
        except Exception as err:
            print(err)
            print ("Can't connect")
            return False

class Syn_Recvd(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def established(self):
        self.CurrentContext.setState("ESTABLISHED")
    def check_ack(self):
        inbound  = self.CurrentContext.recvpacket()
        if inbound["ACK"]:
            print ("ACK recieved, connection established")
            self.CurrentContext.established()
        else:
            print("Connection failed, Termination")
    def trigger(self):
        try:
            self.CurrentContext.packet["SYN"]= True
            self.CurrentContext.packet["ACK"] = True
            self.CurrentContext.sendpacket()
            self.check_ack()
            return True
        except Exception as err:
            print (err)
            print("Connection failed, Terminating")
            self.CurrentContext.setState("CLOSED")
            return False

class Established(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def send (self, text):
        self.CurrentContext.packet["MSG"] = text
        self.CurrentContext.sendpacket()
    def closeWait(self):
        self.CurrentContext.setState("CLOSE_WAIT")
    def trigger(self):
        while True:
            text = input("PLease enter something to send to client :")
            self.send(text)
            inbound = self.CurrentContext.recvpacket()
            if inbound["FIN"]:
                print ("Connection closing")
                self.CurrentContext.closeWait()
                return True
            print(inbound["MSG"])


class Close_Wait(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def lastack(self):
        self.CurrentContext.setState("LAST_ACK")
    def trigger(self):
        try:
            self.CurrentContext.packet["ACK"] = True
            self.CurrentContext.sendpacket()
            print("ACK sent")
            self.CurrentContext.lastack()
            return True
        except Exception as err:
            print (err)
            return False

class Last_Ack(State,Transition):
    def __init__(self,Context):
        State.__init__(self,Context)
    def closed(self):
        self.CurrentContext.setState("CLOSED")
    def trigger(self):
        try:
            print("waiting to close connection")
            self.CurrentContext.packet["FIN"] = True
            self.CurrentContext.sendpacket()
            inbound = self.CurrentContext.recvpacket()
            if inbound["ACK"]:
                self.CurrentContext.closed()
                return True
            else:
                return False
        except Exception as err:
            print (err)
            return False

class TCPserver(StateContext,Transition):
    def __init__(self):
        self.host = ""
        self.port = 5000
        self.connection_address = 0
        self.socket = None
        self.availableStates["CLOSED"] = Closed(self)
        self.availableStates["LISTEN"] = Listen(self)
        self.availableStates["SYN_RECIEVED"] = Syn_Recvd(self)
        self.availableStates["ESTABLISHED"] = Established(self)
        self.availableStates["CLOSE_WAIT"] = Close_Wait(self)
        self.availableStates["LAST_ACK"] = Last_Ack(self)
        self.setState("CLOSED")
        self.packet = {"SYN": False, "ACK": False, "FIN": False, "MSG": "", "seq num": random.randint(0000,9999), "Ack num": 0}

    def resetflags(self):
        self.packet["SYN"] = False
        self.packet["ACK"] = False
        self.packet["Fin"] = False
        self.packet["MSG"] = ""
        self.packet["seq num"] = self.packet["seq num"]+1

    def sendpacket(self):
        outbound = json.dumps(self.packet)
        self.connection.send(outbound.encode())
        self.resetflags()

    def recvpacket(self):
        inboundpacket = self.connection.recv(1024)
        inboundpacket = inboundpacket.decode()
        inboundpacket = json.loads(inboundpacket)
        if inboundpacket["Ack num"] != self.packet["seq num"]-1 and self.packet["Ack num"]!=0:
            print("Error! Sequence number does not match acknowledgement number")
        self.packet["Ack num"] = inboundpacket["seq num"]
        return inboundpacket

    def closed(self):
        return self.CurrentState.closed()
    def listen(self):
        return self.CurrentState.listen()
    def syn_recvd(self):
        return self.CurrentState.syn_recvd()
    def established(self):
        return self.CurrentState.established()
    def closeWait(self):
        return self.CurrentState.closeWait()
    def lastack(self):
        return self.CurrentState.lastack()

if __name__ == "__main__":
    server = TCPserver()
    print("Running server")
    server.listen()
