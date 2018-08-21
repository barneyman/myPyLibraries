import json
import http.client
import subprocess

import time
import RPi.GPIO as GPIO

class baseNode:
	def __init__(self, nodeInfo):
		self.data=nodeInfo

	def name(self):
		return self.data['name']

class ircNode(baseNode):

	def __init__(self, nodeInfo):
		return baseNode.__init__(self,nodeInfo)

	def command(self, command):
		commands=self.data["irc"]['commands']
		commandPair=commands[command]
		subprocess.call(["irsend", "SEND_ONCE", commandPair["remote"], commandPair["command"]])


class httpNode(baseNode):

	def __init__(self, nodeInfo):
		return baseNode.__init__(self,nodeInfo)
	
	def command(self, command):
		commands=self.data["http"]['commands']
		commandUrl=commands[command]

		conn=http.client.HTTPConnection(self.data["http"]['endpoint'])
		conn.request(url=commandUrl, method="GET")

		r=conn.getresponse()

		


class bjfHA:
						   
	def __init__(self, configFile):
		self.loadConfigFile(configFile)

	def loadConfigFile(self, path):
		self.data=json.load(open(path))

	def setMood(self, moodName):
		# first, grunt for that in the moods
		setup=self.data['setup']
		moods=setup['moods']
		if not moodName in moods:
			print("no corresponding moodname - ", moodName)
			return
		mood=moods[moodName]
		for each in mood:
			for key,val in each.items():
				self.sendCommand(key,val)

	def sendCommand(self, destination, command):
		host=self.resolveHost(destination)
		# if we got an array back, recurse
		if isinstance(host, list):
			print (host, " is a list ...")
			for each in host:
				self.sendCommand(each, command)								
			return
		# otherwise, do
		if isinstance(host, baseNode):
			print ("asking ", host.name(), " to ", command)
			host.command(command)

		else:
			print("resolved to something i don't understand")

	def resolveHost(self,host):
		print ("resolving ", host, )
		setup=self.data['setup']
		# if the name of the host starts with a ! it's a group name
		if host[0]=='!':
			print ("recursed")
			return setup['groups'][host[1:]]
		else:
			for each in setup['devices']:
				if each['name']==host:
					# now we need to know what it is ..
					if each['itf']=="http":
						print ("http")
						return httpNode(each)
					elif each['itf']=="irc":
						print ("irc")
						return ircNode(each)
					break

		print ("failed")
		return None
