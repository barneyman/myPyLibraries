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
from googleapiclient.http import MediaFileUpload

import sys
import json

from pathlib import Path


class bjfGoogle:

	def __init__(self, api_key=None):
		self.api_key=api_key

	# client seret file is the file you can download from the Credentials screen in Developer Console
	# credential_storage is a file, created if nexist
	# scopes are ['',''] array
	def Authenticate(self, client_secret_file, credential_store, scopeRequired):

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




	# service deprecated by Google
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

# https://www.googleapis.com/auth/drive.metadata.readonly
# https://www.googleapis.com/auth/drive
# https://www.googleapis.com/auth/drive.file
# remember to enable the Drive API in DevConsole

class bjfDriveService:
	def __init__(self, bjfGoogleInstance):
		self.bjfGinstance=bjfGoogleInstance
		self.service=build('drive', 'v3',http=self.bjfGinstance.AuthorisedHTTP())

	def ListAllFiles(self):
		results=self.service.files().list(fields="nextPageToken, files(id, name, mimeType)").execute()
		items = results.get('files', [])
		return items

	def ListAllFolders(self):
		results=self.service.files().list(q="mimeType='application/vnd.google-apps.folder'", fields="nextPageToken, files(id, name)").execute()
		items = results.get('files', [])
		return items

	def ListAllFilesInFolder(self, folderId):
		results=self.service.files().list(q="{} in parents".format(folderId), fields="nextPageToken, files(id, name)").execute()
		items = results.get('files', [])
		return items

	def AddFile(self, sourceFileOnDisk, destFileName, mimeType, destinationFolderId=None):
		metaData={'name':destFileName}

		if destinationFolderId is not None:
			metaData['parents']=[destinationFolderId]

		upload=MediaFileUpload(sourceFileOnDisk,mimeType)
		fileInfo=self.service.files().create(body=metaData, media_body=upload,fields="id").execute()

		fileInfo['name']=destFileName
		return fileInfo

	def AddJPG(self, sourceFileOnDisk, destFileName, mimeType, destinationFolderId):
		return AddFile(self, sourceFileOnDisk, destFileName, "image/jpeg", destinationFolderId)

	def AddBinary(self, sourceFileOnDisk, destFileName, mimeType, destinationFolderId):
		return AddFile(self, sourceFileOnDisk, destFileName, "application/octet-stream", destinationFolderId)

class bjfTeamDriveService(bjfDriveService):
	def __init__(self, bjfGoogleInstance):
		bjfDriveService.__init__(self, bjfGoogleInstance)

	def ListAllTeamDrives(self):
		results=self.service.drives().list().execute()
		items=results.get('drives', [])
		return items

	def ListAllFilesInFolder(self, folderId):
		results=self.service.files().list(q="{} in parents".format(folderId), fields="nextPageToken, files(id, name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
		items = results.get('files', [])
		return items



class bjfSheetsService:


	class bjfSheetRangeHandler:

		def __init__(self, sheetProps):
			self.sheetProps=sheetProps

		def resolveRangeName(self, a1Notation):
			return self.Title()+"!"+a1Notation

		def FullRange(self):
			grid=self.sheetProps["gridProperties"]
			full="R[0]C[0]:R[{}]C[{}]".format(grid["rowCount"],grid["columnCount"])
			return self.resolveRangeName(full)

		def Title(self):
			return self.sheetProps["title"]


	def __init__(self, bjfGoogleInstance):
		self.bjfGinstance=bjfGoogleInstance
		self.service=build('sheets', 'v4',http=self.bjfGinstance.AuthorisedHTTP())

	def AppendSheetRange(self,sheetID, rowValues, rangeName, valInputOption="USER_ENTERED", insertOption="INSERT_ROWS"):
		body={ 'values':rowValues }
		self.service.spreadsheets().values().append(spreadsheetId=sheetID, range=rangeName, body=body, valueInputOption=valInputOption,insertDataOption=insertOption).execute()

	def UpdateSheetRange(self, sheetID, rowValues, rangeName, valInputOption="USER_ENTERED"):
		body={ 'values':rowValues }
		self.service.spreadsheets().values().update(spreadsheetId=sheetID, range=rangeName, body=body, valueInputOption=valInputOption).execute()

	def ClearSheet(self, sheetID, bjfSheetRangeHandler):
		result=self.service.spreadsheets().values().clear( spreadsheetId=sheetID, range= bjfSheetRangeHandler.FullRange() ).execute()
		
	def CreateSpreadSheet(self, titleOfSheet):
		spreadsheet_body = {
				"properties": { 
					"title": titleOfSheet
					}
			}
		result=self.service.spreadsheets().create(body=spreadsheet_body).execute()

		# now we only have one sheet
		#return { "ssid": result['spreadsheetId'], "sheetRange": self.GetSheetRanges(result['spreadsheetId']) }
		return result['spreadsheetId']

	def GetSheetRanges(self, ssid):
		# list all sheets in the spreadsheet
		ret=self._GetSpreadSheetMeta(ssid)
		if ret is not None:
			bjfSheets=[]
			for sheet in ret['sheets']:
				bjfSheets.append(self.bjfSheetRangeHandler(sheet["properties"]))
			return bjfSheets

		return None

	def GetSpreadSheetTitle(self, ssid):
		result=self._GetSpreadSheetMeta(ssid)
		if result is not None:
			return result['properties']['title']
		return None


	def _GetSpreadSheetMeta(self, ssid):
		# ostensibly a exists check
		ret=None
		try:
			ret=self.service.spreadsheets().get(spreadsheetId=ssid).execute()
		except Exception:
			return None
		return ret


	# add one, optionally, if it exists, return it
	def AddSheetToSpreadSheet(self, ssid, sheetname, failIfExists=False):

		# see if it's there
		currentSheets=self.GetSheetRanges(ssid)
		#print "Found {} sheets".format(len(currentSheets))
		for sheet in currentSheets:
			#print sheet.Title()
			if sheet.Title()==sheetname:
				if failIfExists:
					return None
				else:
					return sheet

		# doesnt exist - create it
		newSheetMeta={ "requests": [ { "addSheet":{ "properties": { "title":sheetname }  } } ] }

		result=self.service.spreadsheets().batchUpdate(spreadsheetId=ssid, body=newSheetMeta).execute()

		return self.bjfSheetRangeHandler(result["replies"][0]["addSheet"]["properties"])


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








