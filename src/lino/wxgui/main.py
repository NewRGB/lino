#----------------------------------------------------------------------
# main.py
#				
#				
# Created:	 2003-10-26
# Copyright: (c) 2003 Luc Saffre
# License:	 GPL
#----------------------------------------------------------------------

import wx
import os

from lino.adamo.widgets import Action
from lino.adamo.datasource import DataCell

class EventCaller(Action):
	"ignores the event"
	def __init__(self,form,meth,*args,**kw):
		self._form = form
		Action.__init__(self,meth,*args,**kw)
	def __call__(self,evt):
		#self._form.getSession().notifyMessage("%s called %s." % (
		#	str(evt), str(self)))
		self.execute()



class wxDataCell(DataCell):
		
	def makeEditor(self,parent):
		self.editor = wx.TextCtrl(parent,-1,self.format())

		#self.Bind(wx.EVT_TEXT, self.EvtText, t1)
		#editor.Bind(wx.EVT_CHAR, self.EvtChar)
		#editor.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
		self.editor.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
		#editor.Bind(wx.EVT_WINDOW_DESTROY, self.OnWindowDestroy)
		return self.editor

	def OnKillFocus(self,evt):
		v = self.editor.GetValue()
		if len(v) == 0:
			v = None
		self.col.setCellValue(self.row,v)
		evt.Skip()
			

class FormFrame(wx.Frame):
	# overviewText = "wxPython Overview"

	def __init__(self, form):
		print "FormFrame.__init__()"
		#self.ui = ui
		title = form.getLabel()
		#title = self.session.db.getLabel()
		parent = form.getSession().getCurrentForm()
		wx.Frame.__init__(self, parent, -1, title,
								size = (400, 300),
								style=wx.DEFAULT_FRAME_STYLE|
								wx.NO_FULL_REPAINT_ON_RESIZE)

		wx.EVT_IDLE(self, self.OnIdle)
		wx.EVT_CLOSE(self, self.OnCloseWindow)
		wx.EVT_ICONIZE(self, self.OnIconfiy)
		wx.EVT_MAXIMIZE(self, self.OnMaximize)

		self.Centre(wx.BOTH)
		self.CreateStatusBar(1, wx.ST_SIZEGRIP)

		self.setForm(form)
		
		self.Show()



	def setForm(self,form):
		self.form = form
		
		if len(form.getMenus()) != 0:
			wxMenuBar = wx.MenuBar()
			for mnu in self.form.getMenus():
				wxm = self._createMenuWidget(mnu)
				wxMenuBar.Append(wxm,mnu.getLabel())

			self.SetMenuBar(wxMenuBar)
			db = self.form.getSession().db
			self.SetTitle(db.getLabel() +" - " \
							  + self.form.getLabel().replace(db.schema.HK_CHAR, ''))
			
		#self.SetBackgroundColour(wx.RED)

		if len(form) > 0:

			fieldsPanel = wx.Panel(self,-1)

			vbox = wx.BoxSizer(wx.VERTICAL)
			for cell in form:
				p = wx.Panel(fieldsPanel,-1)
				vbox.Add(p)

				hbox = wx.BoxSizer(wx.HORIZONTAL)
				label = wx.StaticText(p, -1, cell.col.rowAttr.getLabel()) 
				#label.SetBackgroundColour(wx.GREEN)
				hbox.Add(label, 1, wx.ALL,10)

				editor = cell.makeEditor(p)
				hbox.Add(editor, 1, wx.ALL,10)
				p.SetSizer(hbox)


			fieldsPanel.SetSizer( vbox )


			vbox = wx.BoxSizer(wx.VERTICAL)
			vbox.Add(fieldsPanel,1,wx.EXPAND|wx.ALL,10)

			buttons = form.getButtons()
			if len(buttons):
				buttonPanel = wx.Panel(self,-1) 
				hbox = wx.BoxSizer(wx.HORIZONTAL)
				for (name,meth) in buttons: 
					winId = wx.NewId()
					button = wx.Button(buttonPanel,winId,name,
											 wx.DefaultPosition, wx.DefaultSize)
					hbox.Add(button, 1, wx.ALL,10)

					wx.EVT_BUTTON(self, winId, EventCaller(form,meth))

				buttonPanel.SetSizer(hbox)
				hbox.Fit(fieldsPanel)

				vbox.Add(buttonPanel,1,wx.EXPAND|wx.ALL,10)

			self.SetAutoLayout( True ) # tell dialog to use sizer

			self.SetSizer( vbox )		# actually set the sizer


			vbox.Fit( self ) # set size to minimum size as calculated by the sizer
			#vbox.SetSizeHints( self ) # set size hints to honour mininum size
			
		self.Layout()




	def _createMenuWidget(self,mnu):
		wxMenu = wx.Menu()
		for mi in mnu.getItems():
			#print repr(mi.getLabel())
			#"%s must be a String" % repr(mi.getLabel())
			winId = wx.NewId()
			doc = mi.getDoc()
			if doc is None:
				doc=""
			wxMenu.Append(winId,mi.getLabel(),doc)
			wx.EVT_MENU(self, winId, EventCaller(self.form,
															 mi.execute))
		return wxMenu

	def OnCloseWindow(self, event):
		self.dying = True
		#self.window = None
		self.mainMenu = None
		#if hasattr(self, "tbicon"):
		#	del self.tbicon
		self.Destroy()


	def OnIdle(self, evt):
		#wx.LogMessage("OnIdle")
		evt.Skip()

	def OnIconfiy(self, evt):
		wx.LogMessage("OnIconfiy")
		evt.Skip()

	def OnMaximize(self, evt):
		wx.LogMessage("OnMaximize")
		evt.Skip()


from lino.adamo.session import AdamoSession, Application

class WxSession(AdamoSession):
	
	_dataCellFactory = wxDataCell
	
	_windowFactory = FormFrame
	
	def __init__(self,wxapp,adamoApp):
		AdamoSession.__init__(self,adamoApp)

	def errorMessage(self,msg):
		return self.app.console.notify(msg)

	def notifyMessage(self,msg):
		return self.app.console.notify(msg)
		
	def progress(self,msg):
		return self.app.console.progress(msg)


class WxApp(wx.App):

	def __init__(self,adamoApp):
		wx.App.__init__(self,0)
		self.session = WxSession(self,adamoApp)


	def OnInit(self):
		wx.InitAllImageHandlers()
		self.session.onBeginSession()
		
## 		self.session.onStartUI()
## 		frame = self.session.getCurrentForm() # forms.login
## 		#assert frame is not None
## 		#print frame
## 		#frame = FormFrame(None, -1, form)
## 		self.SetTopWindow(frame)
		return True

	def OnExit(self):
		self.session.shutdown()

## class wxApplication(Application):
## 	def __init__(self,**kw):
## 		Application.__init__(self,**kw)
## 		self.wxapp = wxAppInstance(self)
		
## 	def createSession(self,**kw):
## 		return wxSession(self,**kw)
		
## 	def run(self):
## 		self.wxapp.MainLoop()
		
