# myPyLibraries
Some helper libs i wrote for me

requires

pathlib

==bjfGoogle==

You have to authenticate before you can use it

Generate a OAUth2 credential from Google Developer console

Store that in 'client_secret.json' - Do not check this file in

Then authenticate - quoting the scopes you need 

The first time around, you will be given a link to open in a browser - clicking thru this
link will authorise your token and give you a link to paste back into your app

This needs to happen only once - as long as you preserve your creds.sto file



storeAuthFilename='creds.sto'
scopesNeeded=['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive']

goog=bjfGoogle()
goog.Authenticate('client_secret.json', storeAuthFilename,scopesNeeded)

