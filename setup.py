from distutils.core import setup

setup(name='bjfGoogle',
      version='1.0',
      py_modules=['bjfGoogle'],
	  depends=['google-api-python-client', 'google-auth-httplib2', 'google-auth-oauthlib', 'pathlib']
      )

