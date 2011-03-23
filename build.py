"""
This script is designed to support creation of the binary
distributions of the QTI migration tool.

Usage (Mac OS X):
	python build.py py2app

Usage (Windows):
	python build.py py2exe
"""

import sys, os

# Modify the path to ensure that our lib modules are picked up
wd=os.getcwd()
sys.path.append(os.path.join(wd,"lib"))

mainscript='migrate.py'

try:
	import vobject
except:
	print "ERROR: vobject should be installed when creating binary executables"
	sys.exit(1)

if sys.platform == 'darwin':
	from setuptools import setup
	extra_options = dict(
		setup_requires=['py2app'],
		app=[mainscript],
		# Cross-platform applications generally expect sys.argv to
		# be used for opening files.
		options=dict(py2app=dict(argv_emulation=True)),
	)
elif sys.platform == 'win32':
	from distutils.core import setup
	import py2exe
	extra_options = dict(
		setup_requires=['py2exe'],
		app=[mainscript],
		console=[dict(script='migrate.py',icon_resources=[(1,"QTIMigrate.ico"),(2,"folder.ico"),(3,"readme.ico")])]
	)
else:
	print "ERROR: build for unsupported target"
	sys.exit(1)

setup(
	name="QTIMigration",
	data_files = ['IMSLogo.bmp'],
	**extra_options
)
