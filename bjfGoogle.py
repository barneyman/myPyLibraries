import httplib2
from oauth2client import client
from oauth2client import file
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

from datetime import datetime
from datetime import timedelta

from apiclient.discovery import build
from apiclient.http import MediaIoBaseUpload

import io
import csv

from googleapiclient.errors import HttpError

import sys
import json

from pathlib import Path


class bjfGoogle:

	def __init__(self, api_key=None):
		self.api_key=api_key

	def Authenticate(self,client_secret_file, credential_store, scopeRequired):

		# FIRST - the client_secret_file HAs to exist!
		if not Path(client_secret_file).is_file():
			print(client_secret_file)
			print("client secret file must exist! Download from Google Developer Console")
			return False;


		# https://developers.google.com/api-client-library/python/guide/aaa_oauth
		authStorage=Storage(credential_store)
		self.cachedAuthorisation=authStorage.get()
		if self.cachedAuthorisation is None or self.cachedAuthorisation.invalid or not self.cachedAuthorisation.has_scopes(scopeRequired):
			flow = client.flow_from_clientsecrets(client_secret_file,
				scopeRequired,
				redirect_uri='urn:ietf:wg:oauth:2.0:oob')
			auth_uri = flow.step1_get_authorize_url()
			print ("Please visit the following URL and authenticate:")
			print 
			print (self.ShortenUrl(auth_uri))
			print
			auth_code = input('Enter the auth code: ')
			self.cachedAuthorisation = flow.step2_exchange(auth_code)

		#if (self.cachedAuthorisation.token_expiry - datetime.utcnow()) < timedelta(minutes=5):
		#	http = self.cachedAuthorisation.authorize(httplib2.Http())
		#	self.cachedAuthorisation.refresh(http)

		# create an authorised http
		http=httplib2.Http()
		self.HTTPauthed=self.cachedAuthorisation.authorize(http)

		authStorage.put(self.cachedAuthorisation)

		return True;

	def AuthorisedHTTP(self):
		#http=httplib2.Http()
		#http = self.cachedAuthorisation.authorize(http)

		# if we haven't expired, return the http, otherwise, refresh it
		if (self.cachedAuthorisation.token_expiry - datetime.utcnow()) < timedelta(minutes=5):
			self.HTTPauthed = self.cachedAuthorisation.authorize(httplib2.Http())
			self.cachedAuthorisation.refresh(self.HTTPauthed)

		return self.HTTPauthed


#	scope='https://www.googleapis.com/auth/photos https://www.googleapis.com/auth/userinfo.profile',
	def GetPhotoService(self,access_token):
		user_agent='bjfapp'
		gd_client = gdata.photos.service.PhotosService(source=user_agent,
			email="default",
			additional_headers={'Authorization' : 'Bearer %s' % access_token})
		return gd_client

# sheets - RO - "https://www.googleapis.com/auth/spreadsheets.readonly"
# sheets - RW - https://www.googleapis.com/auth/spreadsheets
	def GetSheetsService(self):
		discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
		                    'version=v4')
		service=build('sheets', 'v4', http=self.AuthorisedHTTP(),discoveryServiceUrl=discoveryUrl)
		return service

# ='https://www.googleapis.com/auth/fusiontables'
# https://developers.google.com/api-client-library/python/guide/aaa_oauth
	def GetFusionService(self):
		service=build("fusiontables","v2",http=self.AuthorisedHTTP())
		return service

	def ShortenUrl(self, longUrl):
		# quick check
		if self.api_key is None:
			return longUrl
		try:
			service=build('urlshortener', 'v1', developerKey=self.api_key)
			url=service.url()
			body={'longUrl':longUrl}
			resp=url.insert(body=body).execute()
			return resp['id']
		except HttpError:
			return longUrl
		except:
			print ("Exception occurred ",sys.exc_info()[0])
			return longUrl

class bjfSheetsService:

	def __init__(self, bjfGoogleInstance):
		self.bjfGinstance=bjfGoogleInstance
		self.service=build('sheets', 'v4',http=self.bjfGinstance.AuthorisedHTTP())

	def AppendSheetRange(self,sheetID, rowValues, rangeName, valInputOption="USER_ENTERED", insertOption="INSERT_ROWS"):
		body={ 'values':rowValues }
		self.service.spreadsheets().values().append(spreadsheetId=sheetID, range=rangeName, body=body, valueInputOption=valInputOption,insertDataOption=insertOption).execute()

	def UpdateSheetRange(self, sheetID, rowValues, rangeName, valInputOption="USER_ENTERED"):
		body={ 'values':rowValues }
		self.service.spreadsheets().values().update(spreadsheetId=sheetID, range=rangeName, body=body, valueInputOption=valInputOption).execute()

# ??
# https://www.googleapis.com/auth/gmail.readonly
# https://www.googleapis.com/auth/gmail

# to send emails
# https://www.googleapis.com/auth/gmail.compose

class bjfGmailService:
	def __init__(self, bjfGoogleInstance):
		self.bjfGinstance=bjfGoogleInstance
		self.service=build("gmail","v1",http=self.bjfGinstance.AuthorisedHTTP())

	def send(self, recipient, subject, message_text,message_text_html=None):

		try:
			message = self.buildMessageMime(recipient, subject, message_text, message_text_html)

			messageDetails=self.service.users().messages().send(userId='me', body=message).execute()

			print ('Message Id: %s' % messageDetails['id'])
			return messageDetails
		except HttpError as error:
			print ('An error occurred: %s') % error



	def buildMessageMime(self, recipient, subject, message_text, message_text_html=None):

		try:
			if message_text_html is None:
				message = MIMEText(message_text)
			else:
				message=MIMEMultipart('alternative')
				message.attach(MIMEText(message_text, 'plain'))
				message.attach(MIMEText(message_text_html, 'html'))

			message['to'] = recipient
			message['from'] = "bf@g.com"
			message['subject'] = subject

			# py2
			# return {'raw': base64.urlsafe_b64encode(message.as_string())}
			# py3
			return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}

		except HttpError as error:
			print ('An error occurred: %s') % error

# ='https://www.googleapis.com/auth/fusiontables'
# https://developers.google.com/api-client-library/python/guide/aaa_oauth

class bjfFusionService:

	def __init__(self, bjfGoogleInstance):
		self.bjfGinstance=bjfGoogleInstance
		self.service=build("fusiontables","v2",http=self.bjfGinstance.AuthorisedHTTP())

	def GetTableByName(self,name):
		# list all tables 
		found=self.service.table().list().execute()
		while "items" in found:
			for each in found["items"]:
				if each["name"]==name:
					return self.OpenTable(each["tableId"])
			if not "nextPageToken" in found:
				break
			found=self.service.table().list(pageToken=found["nextPageToken"]).execute()
		return None

	def CreateTable(self,body):
		return self.service.table().insert(body=body).execute();

	def OpenTable(self,tableid):
		return self.service.table().get(tableId=tableid).execute();

	def InsertRowData(self,tableObject, rowDictionary):

		sump=io.StringIO()
		w=csv.writer(sump, quoting=csv.QUOTE_ALL)
		w.writerows(rowDictionary)
		mu=MediaIoBaseUpload(sump,mimetype="application/octet-stream")
		return self.service.table().importRows(tableId=tableObject["tableId"], media_body=mu).execute()








