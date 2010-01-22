#! /usr/bin/env python
"""
GUI Script Code Copyright (c) 2004 - 2008, Pierre Gorissen
All Other Code is Copyright (c) 2004 - 2008, University of Cambridge.
"""

# Global options
# --------------
GUI_VERSION='Version: 2008-06-07'

import	sys, os, time, string
import	wx
import	wx.lib.filebrowsebutton as filebrowse

import imsqtiv1


# ==============================================================================
# some global info
#
# file filter
wildcard = "QTI files (*.xml)|*.xml"

# global ID's
ID_LOG = 100
ID_ABOUT = 101
ID_EXIT	 = 102
ID_UCVARS = 103
ID_QMDEXTENSIONS = 104
ID_FORCEFIBFLOAT = 105
ID_FORCEDTD = 106
ID_FORCELANG = 107
ID_NOCOMMENT = 108


# ==============================================================================
#
# MyFrame Class
#
# Description: this class constructs the main window
#
class MyFrame(wx.Frame):

	def __init__(self, parent, ID, title):
		self.app=wx.GetApp()
		self.options=self.app.options
		wx.Frame.__init__(self, parent, ID, title,
						 wx.DefaultPosition, wx.Size(600, 300), style=wx.DEFAULT_DIALOG_STYLE|wx.CAPTION|wx.SYSTEM_MENU)						 
		self.panel=wx.Panel(self)
		self.CreateStatusBar()
		self.SetStatusText("Program initialised")
		self.SetBackgroundColour(wx.Colour(192,192,192))
		# build menu
		self.menu1 = wx.Menu()
		self.menu1.Append(ID_LOG, 'Show Output &Log',
			'Redirect log statements to a window',wx.ITEM_CHECK)

		self.menu1.Append(ID_ABOUT, "&About",
					"More information about this program")
		self.menu1.AppendSeparator()
		self.menu1.Append(ID_EXIT, "E&xit", "Terminate the program")
		
		menu2 = wx.Menu()
		menu2.Append(ID_QMDEXTENSIONS, 'Allow Metadata Extensions',
						'Allow Metadata Extensions',
						wx.ITEM_CHECK)
		menu2.Append(ID_UCVARS, 'Force &Uppercase',
						'Force all identifiers to upper-case',
						wx.ITEM_CHECK)

		menu2.Append(ID_FORCEFIBFLOAT, 'Force &Float',
						'Force FIBs to be treated as floats',
						wx.ITEM_CHECK)
		menu2.Append(ID_FORCEDTD, 'Force DTD Location',
						'Overrule the DTD location found in the XML file')					
		menu2.Append(ID_FORCELANG, 'Default Language',
						'Provide a default language setting for converted items')						
		menu2.Append(ID_NOCOMMENT, 'Suppress Comments',
						'Suppress output of diagnostic comments in converted items',
						wx.ITEM_CHECK)						

		# Set the options
		menu2.Check(ID_QMDEXTENSIONS, self.options.qmdExtensions)
		menu2.Check(ID_UCVARS, self.options.ucVars)
		menu2.Check(ID_FORCEFIBFLOAT, self.options.forceFloat)
		menu2.Check(ID_NOCOMMENT, self.options.noComment)

		menuBar = wx.MenuBar()
		menuBar.Append(self.menu1, "&File");
		menuBar.Append(menu2, "&Options");
		self.SetMenuBar(menuBar)
		# events for menu items
		wx.EVT_MENU(self, ID_ABOUT, self.OnAbout)
		wx.EVT_MENU(self, ID_EXIT,	self.TimeToQuit)
		wx.EVT_MENU(self, ID_LOG,	self.OnToggleRedirect)
		wx.EVT_MENU(self, ID_QMDEXTENSIONS, self.OnQMDExtensions)
		wx.EVT_MENU(self, ID_UCVARS, self.OnUCVars)
		wx.EVT_MENU(self, ID_FORCEFIBFLOAT, self.OnForceFIBFloat)
		wx.EVT_MENU(self, ID_FORCEDTD,	 self.OnForceDTD)
		wx.EVT_MENU(self, ID_FORCELANG, self.OnForceLANG)
		wx.EVT_MENU(self, ID_NOCOMMENT, self.OnSuppressComments)
		
		# close event for main window
		self.Bind(wx.EVT_CLOSE, self.TimeToQuit)

		# Group FileBrowser and DirectoryBrowser
		# Only one is to be made active

		box1_title = wx.StaticBox( self.panel, 107, "Convert..." )
		self.grp1_ctrls = []
		radio1 = wx.RadioButton(self.panel, 103, "", style = wx.RB_SINGLE )
		ffb1 = filebrowse.FileBrowseButton(self.panel, 104, size = (450, -1),
										labelText = "Single QTIv1.2 File : ",
										buttonText = "Browse..",
										startDirectory = os.getcwd(),
										fileMask = wildcard, 
										fileMode = wx.OPEN,
										changeCallback = self.ffb1Callback)

		radio1.SetValue(1)
		ffb1.Enable(True)
										
		radio2 = wx.RadioButton(self.panel, 105, "", style = wx.RB_SINGLE )
		dbb1 = filebrowse.DirBrowseButton(self.panel, 106, size = (450, -1),
										labelText = "Full Directory		   : ",
										buttonText = "Browse..",
										startDirectory = os.getcwd(), 
										changeCallback = self.dbb1Callback)
																				
		radio2.SetValue(0)
		dbb1.Enable(False)						

		self.grp1_ctrls.append((radio1, ffb1))
		self.grp1_ctrls.append((radio2, dbb1))

		box1 = wx.StaticBoxSizer( box1_title, wx.VERTICAL )
		grid1 = wx.FlexGridSizer( 0, 2, 0, 0 )
		for radio, browseButton in self.grp1_ctrls:
			grid1.Add( radio, 0, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT|wx.TOP, 5 )
			grid1.Add( browseButton, 0, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT|wx.TOP, 5 )
		box1.Add( grid1, 0, wx.ALIGN_CENTRE|wx.ALL, 5 )

		# == Save files to...
		box2_title = wx.StaticBox( self.panel, 109, "Save files to..." )
		self.grp2_ctrls = []
		dbb2 = filebrowse.DirBrowseButton(self.panel, 108, size = (475, -1),
										labelText = "Select Directory				: ",
										buttonText = "Browse..",
										startDirectory = os.getcwd(),
										changeCallback = self.dbb2Callback)
		dbb2.SetValue(self.options.cpPath,0)								 

		self.grp2_ctrls.append(dbb2)
		box2 = wx.StaticBoxSizer( box2_title, wx.VERTICAL )
		box2.Add( dbb2, 0, wx.ALIGN_CENTRE|wx.ALL, 5 )
				
		# == define Convert and Cancel (close) buttons
		button1 = wx.Button(self.panel, 1003, "Convert..")
		self.Bind(wx.EVT_BUTTON, self.ConvertMe, button1)
		button2 = wx.Button(self.panel, 1004, "Close")
		self.Bind(wx.EVT_BUTTON, self.TimeToQuit, button2)
		
		# Now add everything to the border
		# First define a button row
		buttonBorder = wx.BoxSizer(wx.HORIZONTAL)
		buttonBorder.Add(button1, 0, wx.ALL, 5)
		buttonBorder.Add(button2, 0, wx.ALL, 5)
		# Add it all
		border = wx.BoxSizer(wx.VERTICAL)
		border.Add(box1, 0, wx.ALL, 5)
		border.Add(box2, 0, wx.ALL, 5)
		border.Add(buttonBorder, 0, wx.ALL, 5)
		self.SetSizer(border)
		self.SetAutoLayout(True)

		# Setup event handling and initial state for controls:
		for radio, browseButton in self.grp1_ctrls:
			self.Bind(wx.EVT_RADIOBUTTON, self.OnGroup1Select, radio )
			# radio.SetValue(0)
			# browseButton.Enable(False)

		self.app.SetMainFrame(self)
		
	# ===============================
	# reads input file or input directory from ctrls
	# checks to see if one of them is set
	# reads output directory from ctrl
	# checks to see if it is set
	# calls the parser to do the actual work
	#
	def ConvertMe(self, event):
		cpInput=None
		fileNames=[]
		self.SetStatusText("Starting Conversion")
		for radio, browseButton in self.grp1_ctrls:
			if radio.GetValue() == 1:
				cpInput = browseButton.GetValue()
				print "Input: " + cpInput				
				if (cpInput !=""):
					fileNames.append(cpInput)
				else:
					cpInput=None
					print "No Input file or folder defined. Aborting..."
					break				
		for browseButton in self.grp2_ctrls:
			#handled by call back now
			#self.options.cpPath=browseButton.GetValue()
			if (self.options.cpPath!=""):
				self.options.cpPath=os.path.abspath(self.options.cpPath)
				if os.path.exists(self.options.cpPath):
					if os.path.isdir(self.options.cpPath):
						print "Output Directory is valid...."
					else:
						print "No Output Directory selected. Aborting..."
						self.options.cpPath=''
						break
			else:
				self.options.cpPath=''
		if fileNames:
			self.ProcessFiles(fileNames)
		else:
			print "No input set. Parser aborted..."
			self.SetStatusText("Parser aborted...")
		
	def ProcessFiles(self,fileNames):
		self.SetStatusText("Parsing input files...")
		parser=imsqtiv1.QTIParserV1(self.options)
		parser.ProcessFiles(os.getcwd(),fileNames)
		if self.options.cpPath:
			print "Parsing complete"
			self.SetStatusText("Creating content package...")
			parser.DumpCP()
			print "Migration completed..."
			self.SetStatusText("")
		else:
			print "No output set. Parsing complete"
			self.SetStatusText("Parsing complete (dry run)")
		parser=None
		
	# ===============================
	# toggles visibility of either
	# file input option ctrls or
	# directory input option ctrls
	#
	def OnGroup1Select( self, event ):
		radio_selected = event.GetEventObject()

		for radio, browseButton in self.grp1_ctrls:
			if radio is radio_selected:
				browseButton.Enable(True)
				radio.SetValue(1)
			else:
				browseButton.Enable(False)
				radio.SetValue(0)
	# ===============================
	# displays about box
	#
	def OnAbout(self, event):
		msg=string.join(self.app.splashLog,'\n')
		dlg = wx.MessageDialog(self, msg,
								"About Me", wx.OK | wx.ICON_INFORMATION)
		dlg.ShowModal()
		dlg.Destroy()

	# ===============================
	# check / uncheck qmdextensions option
	#
	def OnQMDExtensions(self, event):
		self.options.qmdExtensions=abs(self.options.qmdExtensions-1)

	# ===============================
	# check / uncheck ucvars option
	#
	def OnUCVars(self, event):
		self.options.ucVars=abs(self.options.ucVars-1)
		
	# ===============================
	# check / uncheckforcefibfloat option
	#
	def OnForceFIBFloat(self, event):
		self.options.forceFloat=abs(self.options.forceFloat-1)

	# ===============================
	# displays DTD location entry box
	#
	def OnForceDTD(self, event):
		
		dlg = wx.TextEntryDialog(
				self, 'Enter the full DTD location that needs to be used.\nLeave empty to use the location provided in the QTI File.',
				'Override DTD location in QTI files', '')

		dlg.SetValue(self.options.dtdDir)

		if dlg.ShowModal() == wx.ID_OK:
			self.options.dtdDir = dlg.GetValue()
			self.options.dtdDir=os.path.abspath(self.options.dtdDir)
			print "DTD_LOCATION = "+self.options.dtdDir

		dlg.Destroy()	

	# ===============================
	# displays Language entry box
	#
	def OnForceLANG(self, event):
		
		dlg = wx.TextEntryDialog(
				self, 'Enter the language code to use.\nLeave empty to use the one provided in the QTI File.',
				'Override language in QTI files', '')

		dlg.SetValue(self.options.lang)

		if dlg.ShowModal() == wx.ID_OK:
			self.options.lang = dlg.GetValue()

		dlg.Destroy()	
		
	# ===============================
	# check / uncheck noComment option
	#
	def OnSuppressComments(self, event):
		self.options.noComment=abs(self.options.noComment-1)


	# ===============================
	# callback functions for browse buttons
	#
	def ffb1Callback(self, evt):				
		print 'FileBrowseButton: %s\n' % evt.GetString()
			
	def dbb1Callback(self, evt):				
		print 'DirBrowseButton: %s\n' % evt.GetString()	
		
	def dbb2Callback(self, evt):
		self.options.cpPath=evt.GetString()
		print 'CPOutBrowseButton: %s\n' % evt.GetString()	

	# ===============================
	# let's go home
	#	 
	def TimeToQuit(self, event):
		self.app.RestoreStdio()
		sys.exit(1)

	# ===============================
	# switch between output to
	# command box or ourput windows
	#
	def SetRedirect(self):
		# Force output to be visible
		self.menu1.Check(ID_LOG, True)
		self.app.RedirectStdio()
		
	def OnToggleRedirect(self, event):
		if event.Checked():
			self.app.RedirectStdio()
			print "Log statements will be directed to this window.\n\n"
		else:
			self.app.RestoreStdio()
			print "Log statements will be directed to this window.\n\n"

# ==============================================================================

def opj(path):
	"""Convert paths to the platform-specific separator"""
	return apply(os.path.join, tuple(path.split('/')))

# ==============================================================================
#
# MySplashScreen Class
#
# Description: show the splashscreen during startup
#
class MySplashScreen(wx.SplashScreen):
	def __init__(self):
		bmp = wx.Image(opj("IMSLogo.bmp")).ConvertToBitmap()
		wx.SplashScreen.__init__(self, bmp,
								 wx.SPLASH_CENTRE_ON_SCREEN | wx.SPLASH_TIMEOUT,
								 3000, None, -1)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

	def OnClose(self, evt):
		self.Hide()
		# Open the main window
		frame = MyFrame(None, -1, "QTI Migration Tool")
		frame.Show(True)
		frame.SetFocus()


# ==============================================================================
#
# MyApp Class
#
# Description: handles display of splashscreen and creation of main window
#

class MyApp(wx.App):
	def __init__(self,splashLog,options,fileNames):
		self.splashLog=splashLog
		self.options=options
		self.mainframe=None
		self.fileNames=fileNames
		wx.App.__init__(self,0)
	
	def SetMainFrame(self,mainframe):
		print self.fileNames
		self.mainframe=mainframe
		# Turn on IO redirection
		if self.fileNames:
			self.mainframe.SetRedirect()
			self.mainframe.ProcessFiles(self.fileNames)

	def OnInit(self):
		splash = MySplashScreen()
		splash.Show()
		self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)
		return True

	def OnCloseWindow(self, event):
		self.Destroy()

