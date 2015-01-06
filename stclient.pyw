from __future__ import with_statement


from collections import defaultdict
import codecs

import chatterbox as cb

import thread, time


from room_window import room_window

import sys, os
user_info_window = None

from guimporter import *


def read_settings(fname):
	dct = { "use_ie" : "0", "topbottom" : "1", "fontsize" : "12", "split" : 0, "proxy" : ""}
	try:
		f = open(fname, "r")
		for s in f:
			if s.startswith(("#", "//", ";")): continue
			s2 = s.strip().split("=")
			dct[s2[0]] = s2[1]
		f.close()
	except:
		pass
	return dct

pathname = os.path.dirname(sys.argv[0])
owndir = os.path.abspath(pathname) + os.sep
dct = read_settings(owndir + "settings.ini")

import userinfowindow as uiw
user_info_window = None

langdict = {}
countries = {}

f = open(owndir + "langs.txt")
for l in f:
	n, t = [x.strip() for x in l.split(":")]
	langdict[n] = t
f.close()

f = open(owndir + "countries.txt")
for l in f:
	n, t = [x.strip() for x in l.split(":")]
	countries[n] = t
f.close()

class main_window(QtGui.QMainWindow):
	
	def __init__(self, parent = None):
		super(main_window, self).__init__(parent)
		
		self.ch = None
		
		
		action_login = QtGui.QAction("Login", self)
		action_login.triggered.connect(self.on_menu_login)
		
		self.verbose_flat = []
		self.codes_flat = []
		
		## from functools import partial
		
		## for i in xrange(len(cb.rooms_list[0])):		
		## 	id = wx.NewId()
		## 	menu.Append(id, cb.rooms_list[1][i], cb.rooms_list[1][i])
		## 	self.Bind(wx.EVT_MENU, partial(self.on_menu_join, room=cb.rooms_list[0][i]), id=id)
		
		#menu2 = wx.Menu()
		#id = wx.NewId()
		#menu2.Append(id, "Show user list", "Show user list")
		#self.Bind(wx.EVT_MENU, self.on_menu_show_user_list, id=id)
		
		menubar = self.menuBar()
		menu_login = menubar.addMenu("Login")
		menu_login.addAction(action_login)
			
		self.logged_in = False
		
		
		self.nb = QtGui.QTabWidget(self)
		self.nb.setTabsClosable(True)
		self.nb.tabCloseRequested.connect(self.on_close_room)
		self.nb.currentChanged.connect(self.on_change_room)
		
		self.setCentralWidget(self.nb)
		self.setWindowTitle('Sharedtalk')
		
		#self.destroyed.connect(self.on_close)
		#self.close.connect(self.on_close)
			
		self.ignore_privates = False
		
		self.user_list_window = None
		
		self.privates_notified = set([])
		
		self.tmr = QtCore.QTimer()
		self.tmr.timeout.connect(self.on_timer)
		self.tmr.start(4000)
		
		self.setGeometry(100, 100, 500, 500)
		self.show()
	
	def on_menu_show_user_list(self, evt):
		dlgs.messageDialog(message="Boom!", title="Baam!")
	
	def on_timer(self):
		if not self.ch or not self.logged_in: return
		if self.user_list_window: self.update_user_list()
		
		###
		privates = self.ch.get_private_waiting_list()
		to_call = set([])
		if len(privates[0]) > 0:
			aud = self.ch.get_all_users_dict()
			for puser in privates[0]:
				k = puser.split("-")[0]
				
				if k in aud.keys():
					to_call.add(k)
		
		if len(to_call - self.privates_notified) > 0:
			#pass #TODO: make a sound
			try:
				QtGui.QSound.play(owndir + "private.wav")
			except:
				print "Failed to play the sound"
		self.privates_notified = to_call
		###
		line = self.ch.get_my_accepted_privates()
		if len(line) == 0: return
		for r in line:
			self.join_my_private(r)
	
	def get_lp(self):
		import pwdialog
		dlg = pwdialog.pwdialog()
			
		ret_val = None
		
		if dlg.ok:
		    ret_val = (dlg.name, dlg.password)
		
		return ret_val

	def on_menu_login(self):
		if not self.ch:
			self.ch = cb.chatterbox(dct["proxy"])
			
			try:
				self.load_ignore()
			except:
				pass
		
		val = self.get_lp()
		if not val: return
		l, p = val
		self.logged_in = self.ch.login(l, p)			
		if not self.logged_in:
				
			status = self.ch.get_login_status()
			if status == "banned":
				msg = "You are banned."
				ttl = "Ban"
			elif status == "wrong":
				msg = "Wrong login or password."
				ttl = "Login error"
			else:
				msg = "Unknown error."
				ttl = "Error"
				
			#dlgs.messageDialog(message = msg, title = ttl)
			QtGui.QMessageBox.critical(self, ttl, msg)
			return
			
		self.ch.join_text_chat()

		menubar = self.menuBar()
		menubar.clear()
		menu = menubar.addMenu("Join")
		
		menuact = QtGui.QAction("User list", self)
		menuact.triggered.connect(self.show_user_list)
		menu.addAction(menuact)
		menu.addSeparator()
		
		from functools import partial
		
		for part in self.ch.room_list:
			for verbose in part:
				menuact = QtGui.QAction(verbose, self)
				menuact.triggered.connect(partial(self.on_menu_join, room_name = verbose, room_code = part[verbose]))
				menu.addAction(menuact)
			menu.addSeparator()

		#self.GetMenuBar().Append(menu, "Join")
		#self.GetMenuBar().Replace(0, menu, "Join")

		for part in self.ch.room_list:
			pk = part.keys()
			self.verbose_flat += pk
			for k in pk:
				self.codes_flat.append(part[k])
	
	def on_menu_join(self, room_name, room_code):
		if not room_code in self.ch.get_opened_rooms_titles():
			page = room_window(self, chat = self.ch, settings = dct, room = room_code)
			self.nb.addTab(page, room_name)
			page.pcallback = self.private_room_callback
			if self.nb.count() == 1:
				page.active = True
	
	def private_room_callback(self, room):
		pwl = self.ch.get_private_waiting_list()
		pagetitle = codecs.decode(pwl[1][pwl[0].index(room)], "utf-8")
		page = room_window(self.nb, chat = self.ch, settings=dct, 
			room=room, private=True)
		self.nb.addTab(page, pagetitle)
		if self.nb.count() == 1:
			page.active = True
	
	def show_user_list(self):
		if not self.user_list_window:
			self.user_list_window = QtWebKit.QWebView(self)
			self.user_list_window.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
			self.user_list_window.linkClicked.connect(self.on_user_clicked)
			self.nb.addTab(self.user_list_window, "All users")
			self.update_user_list()
	
	def update_user_list(self):
		mf = self.user_list_window.page().mainFrame()
		sbval = mf.scrollBarValue(QtCore.Qt.Vertical)
		
		s = "<html><head></head><body><table>"
		au = self.ch.get_all_users()
		
		ul = u"<html><head></head><body>"
		ul += "<table width=\"100%\" border=\"0\" cellpadding=\"1\" cellspacing=\"1\">"
		ul += "<tr><th colspan=2>%d users</th><th>Name</th><th>Age</th><th>Country</th><th>Studies</th><th>Speaks</th></tr>" % len(au)
		for k, v in au.items():
			#{'1052203' : ['Greenbi', 'K.', 'M', '28', '8|1', '11', '127'], ....}
			#First name, last name, sex, age, speaks, country
			#Private call link | Sex | First + last name | Age | Country | Studies | Speaks
			u = [codecs.decode(x, "utf-8") for x in v]
			if u[2]=="F": img_sex = "rwfat.png" if not self.ch.is_user_ignored(k) else "rwfat_bw.png"
			else: img_sex = "bmfat.png" if not self.ch.is_user_ignored(k) else "bmfat_bw.png"
			username = u[0]
			username += " " + u[1]
			ul += u"<tr bgcolor = \"#ECEDF3\">"
			ul += "<td align=\"center\"><a href=\"%(call)s\"><img src=\"%(img_call)s\"></a></td><td><img src=\"%(img_sex)s\"></td><td valign=\"center\"><a href=\"%(href)s\" title=\"aaabbb\">%(name)s</a></td><td>%(age)s</td>" % {'img_sex' : owndir + img_sex, 'name' : username, 'age' : u[3], 'href' : k, 'call' : "call_" + k, "img_call": owndir + "talk.png"}
			###################
			ul += "<td align=\"left\">%s</td>" % (countries[u[6]] if u[6] in countries.keys() else u[6])
			ul += "<td align=\"left\">%s</td>" % (", ".join([ langdict[x] if x in langdict.keys() else x for x in u[4].split("|") ]))
			ul += "<td align=\"left\">%s</td>" % (", ".join([ langdict[x] if x in langdict.keys() else x for x in u[5].split("|") ]))
			###################
			ul += "</tr>"
	
		ul += "</table></body></html>"
		self.user_list_window.setHtml(ul)
		
		
		mf.setScrollBarValue(QtCore.Qt.Vertical, sbval)
			
	
	def on_user_clicked(self, link):
		#print type(evt)
		#print type(evt.GetClientData())
		#print type(evt.GetEventObject())
		#print type(evt.GetEventData())
		#print type(evt.GetClientObject())
		href = link.path()
		
		if href == "pause":
			self.paused = True
			self.update_users()
			return
		if href == "filter":
			name, ok = QtGui.QInputDialog.getText(self, u"Filter", u"Erase all messages of:")
			if ok and len(name) > 0:
				self.filter_name(name)
			return
		elif href == "play":
			self.paused = False
			self.update_users()
			return
		elif href.startswith("call_"):
			rm = href.split("_")[1]
			self.ch.call_user(rm)
			return	
		elif href.startswith("accept_"):
			rm = href.split("_")[1]
			self.pcallback(rm)
			return		
		elif href.startswith("ignore_"):
			rm = href.split("_")[1]
			self.ch.ignore_private(rm)
			#self.update_users()
			return
		elif href.startswith("decline_"):
			rm = href.split("_")[1]
			self.ch.decline_private(rm)
			#self.update_users()
			return
		
		
		global user_info_window
		user_info_window = uiw.user_info_window(None, href, self.ch, langdict, countries)
		user_info_window.content.linkClicked.connect(self.on_user_clicked)
		user_info_window.show()
	
	def join_my_private(self, withwhom):
		
		pagetitle = codecs.decode(self.ch.get_user_name(withwhom), "utf-8")
		
		page = room_window(self.nb, chat = self.ch, settings=dct, room=withwhom, private=True)
		self.nb.addTab(page, pagetitle)
		if self.nb.count() == 1:
			page.active = True
	
	def on_close_room(self, n):
		sel = n
		txt = self.nb.tabText(sel)
		ob = self.nb.widget(sel)
		if txt == "All users":
			ob.close()
			self.nb.removeTab(sel)
			self.user_list_window = None
			return
		
		ob.save_log()
		ob.close()
		
		if self.nb.count() <= 1:
			self.ch.logout()
			self.logged_in = False
			self.ch = None
		else:
			#fixed access
			pal_not_u = self.ch.get_private_accepted_list()
			pal = [codecs.decode(x, "utf-8") for x in pal_not_u[1]]
			
			if txt in self.verbose_flat:
				self.ch.leave_room(self.codes_flat[self.verbose_flat.index(txt)])
			elif txt in pal:
				self.ch.leave_room(pal_not_u[0][pal.index(txt)])
		self.nb.removeTab(sel)
	
	def close(self):
		cnt = self.nb.count()
		for i in xrange(cnt):
			ob = self.nb.widget(i)
			ob.save_log()
		if self.ch:
			self.ch.logout()
		
		try:
			self.save_ignore()
		except:
			pass
			
		super(main_window, self).close()
		
		sys.exit()
	
	def save_ignore(self):
		import codecs
		pathname = os.path.dirname(sys.argv[0])
		owndir = os.path.abspath(pathname) + os.sep
		f = codecs.open(owndir + "ignore.txt", "w", "utf-8")
		#direct access
		ignore = self.ch.get_ignore_list()
		for i in ignore:
			f.write(i)
			f.write("\n")
		f.close()
	
	def load_ignore(self):
		import codecs
		pathname = os.path.dirname(sys.argv[0])
		owndir = os.path.abspath(pathname) + os.sep
		f = codecs.open(owndir + "ignore.txt", "r", "utf-8")
		for s in f:
			#fixed access
			self.ch.add_to_ignore_list(s.strip())
		f.close()
	
	def on_change_room(self):
		sel = self.nb.currentIndex()
		cnt = self.nb.count()
		for i in xrange(cnt):
			ob = self.nb.widget(i)
			ob.active = (i == sel)

app = QtGui.QApplication(sys.argv)
frame = main_window()
sys.exit(app.exec_())