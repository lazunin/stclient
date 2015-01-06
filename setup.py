from distutils.core import setup
import sys
sys.path.append('..')
import py2exe

setup( options = {"py2exe" : {"optimize":2, 'includes': ['PySide.QtNetwork']}}, 
	windows=["stclient.pyw"]
	)

#C:\Program Files (x86)\Microsoft Visual Studio 9.0\VC\redist\x86\Microsoft.VC90.CRT
#need the dlls and the manifest from there