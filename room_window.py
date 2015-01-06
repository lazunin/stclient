from __future__ import with_statement

from collections import defaultdict
import codecs

from chatterbox import chatterbox

import thread, time
import xml.sax.saxutils as sx

#import perverted as perv
import userinfowindow as uiw
user_info_window = None

from guimporter import *


langdict = {}
countries = {}

import sys, os


pathname = os.path.dirname(sys.argv[0])
owndir = os.path.abspath(pathname) + os.sep
imgdir = owndir
if os.name != 'nt':
	imgdir = "file://" + owndir
#dct = read_settings(owndir + "settings.ini")


def get_doubled_names(dct):
	dn = {}
	for k, v in dct.items():
		nk = codecs.decode(k, "utf-8")
		nv = codecs.decode(v[0], "utf-8")
		if nv in dn.keys():
			dn[nv] += [nk]
		else:
			dn[nv] = [nk]
	u_keys = [k for k, v in dn.items() if len(v) <= 1]
	for u in u_keys:
		dn.pop(u)
	return dn

	
class MessageEditor(QtGui.QTextEdit):
	
	addMessage = Signal(str)
	keyDown = Signal()
	
	def __init__(self, parent):
		super(MessageEditor, self).__init__(parent)
	
	def keyPressEvent(self, e):
		if (e.key() == QtCore.Qt.Key.Key_Enter) or (e.key() == QtCore.Qt.Key.Key_Return):
			self.addMessage.emit(self.toPlainText())
			self.setPlainText("")
		else:
			super(MessageEditor, self).keyPressEvent(e)
			self.keyDown.emit()

class MessagesWindow(QtWebKit.QWebView):
	
	def __init__(self, parent):
		super(MessagesWindow, self).__init__(parent)
		
		self.messages = [] #[('user', 'message')]
	
	def add_message(self, msg):
		self.messages.append((u"Nuigurumi", msg))
		self.update_content()
	
	def update_content(self):
		s = "<html><head></head><body>"
		s += "<table>"
		for m in self.messages:
			s += "<tr><td>"
			s += m[0]
			s += "</td<td>"
			s += m[1]
			s += "</td></tr>"
		s += "</table></body></html>"
		self.setHtml(s)
	
	def keyPressEvent(self, e):
		if (e.key() == QtCore.Qt.Key_C) and (e.modifiers() == QtCore.Qt.ControlModifier):
			self.triggerPageAction(QtWebKit.QWebPage.Copy)

class UsersWindow(QtWebKit.QWebView):
	
	def __init__(self, parent):
		super(UsersWindow, self).__init__(parent)
		
		#self.setHtml("<html><head></head><body><a href='motherfucker'>Click me!</a></body></html>")
		self.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
		
		#self.linkClicked.connect(self.click)
	
	def click(self, link):
		print link.path()


class room_window(QtGui.QWidget):
	
	#def __init__(self, parent, id, title):
	def __init__(self, parent, chat, settings, room, private=False):
		super(room_window, self).__init__(parent)
		
		self.is_private = private
		
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
		
		# self.Bind(
			# wx.EVT_SASH_DRAGGED_RANGE, self.OnSashDrag, id=ID_WINDOW_LEFT, 
			# id2=ID_WINDOW_BOTTOM
			# )
		
		hbox = QtGui.QHBoxLayout(self)


		self.edit = MessageEditor(self)
		self.edit.setFrameShape(QtGui.QFrame.StyledPanel)
			
		
		
		self.dct = settings
		
		self.userlist = UsersWindow(self)
		self.content = MessagesWindow(self)
		
		self.paused = False
		
		splitter1 = QtGui.QSplitter(QtCore.Qt.Horizontal)
		splitter1.addWidget(self.content)
		splitter1.addWidget(self.userlist)
		
		splitter1.setSizes([100, 20])

		splitter2 = QtGui.QSplitter(QtCore.Qt.Vertical)
		splitter2.addWidget(splitter1)
		splitter2.addWidget(self.edit)
		
		splitter2.setSizes([200, 50])

		hbox.addWidget(splitter2)
		self.setLayout(hbox)
		QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
		
		self.setGeometry(300, 300, 300, 200)
		
		#-
		#self.userlist.Bind(wx.html.EVT_HTML_LINK_CLICKED, self.on_user_clicked)
		self.userlist.linkClicked.connect(self.on_user_clicked)
		#-
	
		self.room = room
		self.ch = chat
		
		self.pcallback = None

		self.cur_uinfo = ""
		
		if not self.is_private:
			self.ch.join_room(self.room)
		else:
			if "-" in self.room:
				self.ch.join_private(self.room)
			else:
				self.room = self.ch.join_my_private(self.room)
				#self.room = 
		
		self.uniroom = codecs.encode(self.room, "utf-8")
		
		"""
		import chardet
		print self.room, chardet.detect(self.room)
		print self.uniroom, chardet.detect(self.uniroom)
		"""
		
		#self.uniroom = self.room
		
		self.tmr = QtCore.QTimer()
		self.tmr.timeout.connect(self.on_timer)
		self.tmr.start(4000)
		
		#-
		# doesn't work (crash)
		#self.the_lock = thread.allocate_lock()			
		#tid = thread.start_new_thread(self.update_room, ())
		#-
		
		#self.edit.Bind(wx.EVT_KEY_DOWN, self.on_edit_key_down)
		self.edit.keyDown.connect(self.on_edit_key_down)	#not enter
		self.edit.addMessage.connect(self.on_add_message) #enter
		
		self.msg_printed = 0
		
		self.ie_file_pos = 0
		
		self.pencil = False
		
		self.csplit = int(self.dct["split"])
		
		self.ie_file_name = self.room + ".html"
		self.log = []
		#self.init_iehtml()
		self.active = False
		
		self.doubling_names = {}
		
		#self.names_to_filter = set([])
		
		#self.Bind(wx.EVT_SIZE, self.OnSize)
	
	def user_action(self, action):
		if action.startswith("call_"):
			rm = action.split("_")[1]
			self.ch.call_user(rm)
			return
		elif action.startswith("addtoignore_"):
			rm = action.split("_")[1]
			self.ch.add_to_ignore_list(rm)
			self.update_users()
			return
		elif action.startswith("rehab_"):
			rm = action.split("_")[1]
			self.ch.remove_from_ignore_list(rm)
			self.update_users()
			return
		elif action.startswith("ignore_"):
			rm = href.split("_")[1]
			self.ch.ignore_private(rm)
			return
		elif action.startswith("filter_"):
			rm = action.split("_")[1]
			self.filter_name(rm)
			return
	
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
		user_info_window = uiw.user_info_window(self, href, self.ch, langdict, countries)
		#user_info_window.content.linkClicked.connect(self.on_user_clicked)
		user_info_window.show()
	
	
	def update_users(self):
		self.room_users = self.ch.get_room_users(self.room)
		ud = self.room_users
		
		#ud is {'1052203' : ['Greenbi', 'K.', 'M', '28', '8|1', '11', '127'], ....}
		
		self.doubling_names = get_doubled_names(ud)
		
		ul = u"<html><head></head><body>"
		ul += "<table width=\"100%\" border=\"0\" cellpadding=\"1\" cellspacing=\"1\">"
		for k, v in ud.items():
			u = [codecs.decode(x, "utf-8") for x in v]
			if u[2]=="F": img = "rwfat.png" if not self.ch.is_user_ignored(k) else "rwfat_bw.png"
			else: img = "bmfat.png" if not self.ch.is_user_ignored(k) else "bmfat_bw.png"
			
			img = img
			username = u[0]
			username += " " + u[1]
			if u[0] in self.doubling_names.keys():
				username += "<sup>%d</sup>" % (self.doubling_names[u[0]].index(k)+1)
			
			ul += u"<tr bgcolor = \"#ECEDF3\"><td align=\"center\"><a href=\"%(call)s\" title=\"Private call\"><img src=\"%(img)s\"></a></td><td valign=\"center\"><a href=\"%(href)s\" title=\"User info\">%(name)s</a></td><td>%(age)s</td></tr>\n" % {'img' : imgdir + img, 'name' : username, 'age' : u[3], 'href' : k, 'call' : "call_" + k}
		
		ul += "</table>"
		ul += "<br><br>"
		ul += self.cur_uinfo
		
		if self.paused:
			ul += "<a href=\"play\" title=\"Resume updating chat window\"><img src=\"" + imgdir + "play.png" + "\"></a>"
		else:
			ul += "<a href=\"pause\" title=\"Pause updating chat window\"><img src=\"" + imgdir + "pause.png" + "\"></a>"
		
		ul += "<a href=\"filter\" title=\"Remove all messages of a user by name\"><img src=\"" + imgdir + "filter.png" + "\"></a>"
		
		#for privates
		line = self.ch.get_private_waiting_list()
		if len(line) > 0:
			ul += "<table width=\"100%\" border=\"0\" cellpadding=\"1\" cellspacing=\"1\">"
			aud = self.ch.get_all_users_dict()
			for puser in line[0]:
				k = puser.split("-")[0]
				
				if not k in aud.keys():
					self.ch.ignore_private(puser)
					continue
				
				u = aud[k]
				u = [codecs.decode(x, "utf-8") for x in u]
				if u[2]=="F": img= "rwfat.png"
				else: img="bmfat.png"
				#ul += u"<tr><td align=\"center\" bgcolor = \"#ECEDF3\"><img src=\"%(img)s\"></td><td valign=\"center\" bgcolor = \"#ECEDF3\"><a href=\"%(href)s\" title=\"aaabbb\">%(name)s</a></td><td bgcolor = \"#ECEDF3\">%(age)s</td></tr>\n" % {'img' : img, 'name' : u[0] + " " + u[1], 'age' : u[3], 'href' : k}
				ul += u"<tr bgcolor = \"#ECEDF3\"><td align=\"center\"><img src=\"%(img)s\"></td><td valign=\"center\"><a href=\"%(href)s\" title=\"aaabbb\">%(name)s</a></td><td>%(age)s</td></tr>\n" % {'img' : imgdir + img, 'name' : u[0] + " " + u[1], 'age' : u[3], 'href' : k}
				ul += u"<tr bgcolor = \"#ECEDF3\"><th colspan=3 align=\"center\"> <a href=\"%(accept)s\"><img src=\"%(img_accept)s\"></a>  <a href=\"%(decline)s\"><img src=\"%(img_decline)s\"></a>   <a href=\"%(ignore)s\"><img src=\"%(img_ignore)s\"></a> </th></tr>\n" % {'accept' : "accept_" + puser, 'decline' : "decline_" + puser, 'ignore' : "ignore_" + puser, "img_accept": imgdir + "accept.png", "img_decline": imgdir + "decline.png", "img_ignore": imgdir + "ignore.png"}
		ul += "</table>"
		#------------
		ul += u"</body></html>"
		self.userlist.setHtml(ul)
	
	
	def on_timer(self):
		
		if self.pencil:
			self.ch.toggle_pencil(self.uniroom)
			self.pencil = False
		
		if self.paused: return
		
		self.update_users()		
		self.update_messages()

	
	def filter_name(self, name):
		#names = set([x[0] for x in self.log])
		#if name in names: print name + " in " + `names`
		#else: print name + " not in " + `names`
		self.log = [x for x in self.log if x[0] != name]		
		self.update_messages()
		
	def update_messages(self, rewrite = False):
		
		ud = self.room_users
		
		msgs_new = []
		msgs_get = self.ch.get_room_messages(self.room)
		if len(msgs_get) == 0: return
		for m in msgs_get:
			uid = codecs.decode(m[0], "utf-8")
			if uid in ud.keys():
				username = codecs.decode(ud[uid][0], "utf-8")
				if username in self.doubling_names.keys():
					username += u"<sup>%d</sup>" % (self.doubling_names[username].index(uid)+1)
			else:
				username = uid
			
			b = codecs.decode(m[1], "utf-8")
			
			msg = [username.strip(), b] + list(m[2:])
			
			msgs_new.append(msg)
			
		msgs = self.log + msgs_new		
		
		
		cnt = self.msg_printed
		self.msg_printed += len(msgs)
		
		fsz = 4
		
		s = u"<html><head></head><body>"
		
		s += u"<table width=\"800\" border=\"0\" cellpadding=\"0\" cellspacing=\"1\">"
		
		username_prev = u''
		
		bgcolors = [u"#ECEDF3", u"#F6F6F6"]
		
		bgcolor_prev = bgcolors[0]
		bgcnt = 0
		
		
		s += u"<tr><td></td><td>"
		for m in msgs:
			
			dopstyles = u''
			
			username = m[0]
			b2 = m[1]
			
			if ((u"http://" in b2) or (u"https://" in b2)) and (len(b2) > 80):
				dopstyles = u"width: 600px; overflow-x: auto"
			
			un, same_user = (username, False) if (username != username_prev) else (u'', True)
			username_prev = username
			
			color = u"#000000"
			
			if not same_user:
				bgcnt = (bgcnt + 1) % 2
				bgcolor = bgcolors[bgcnt]
			else:
				bgcolor = bgcolor_prev
			
			bgcolor_prev = bgcolor
			
			if len(m) > 2: bgcolor = u"#FACE8D"
			"""
			s += u"<tr><td align=\"right\" valign=\"top\" color=\"%(cl)s\" bgcolor=\"%(bg)s\"><b>%(a)s </b></td><td color=\"%(cl)s\" bgcolor=\"%(bg)s\"><div style='width: 80%%; overflow: hidden'><font size=%(fsz)d>%(b)s</font></div></td></tr>" % {u'a':un, u'b':b2, u'bg':bgcolor, u'cl':color, u'fsz': fsz}
			"""
			if not same_user:
				s += u"</td></tr><tr><td align=\"right\" valign=\"top\" color=\"%(cl)s\"><b>%(a)s </b></td><td color=\"%(cl)s\">" % {u'a':un, u'b':b2, u'bg':bgcolor, u'cl':color, u'fsz': fsz}
			s += u"<div style='margin: 0px 1px 1px 1px; padding: 0px 2px 0px 2px; border: 1px solid #55AA55; border-radius: 5px; float: left; background-color: %(bg)s;%(dopstyles)s;'><font size=%(fsz)d>%(b)s</font></div>" % {u'a':un, u'b':b2, u'bg':bgcolor, u'cl':color, u'fsz': fsz, u'dopstyles': dopstyles}
			
			cnt += 1
			
			
		s += u"</td></tr></table><a name='%d'></a>"%(self.msg_printed)
		s += "</body></html>"
		
		mf = self.content.page().mainFrame()
		sbval = mf.scrollBarValue(QtCore.Qt.Vertical)	#the current before we update
		sbmax = mf.scrollBarMaximum(QtCore.Qt.Vertical) #the maximum before we update
		
		self.content.setHtml(s)
		#self.content.scroll(0, 100500)
		#mf = self.content.page().mainFrame()
		
		if sbval == sbmax:
			#it was at the bottom before, scroll it to the bottom after
			sbval = mf.scrollBarMaximum(QtCore.Qt.Vertical)
		#otherwise scroll to the same absolute position as before
		
		mf.setScrollBarValue(QtCore.Qt.Vertical, sbval)
		#self.content.ScrollToAnchor(`self.msg_printed`)
		#self.content_upd_once = True
		
		self.log += msgs_new
	
	def save_log(self):
		#doubling - unnesessary - re-write!
		s = "<html><head>"
		s += "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\"></head><body>"
		s += "<table width=\"100%\" border=\"0\" cellpadding=\"1\" cellspacing=\"1\">"
		
		cnt = 0
		for m in self.log:
			color = "#000000"
			if cnt%2 == 0: bgcolor = "#ECEDF3"
			else: bgcolor = "#F6F6F6"
			#a = codecs.decode(m[0], "utf-8")
			a = m[0]
			#b = codecs.decode(m[1], "utf-8")
			b = m[1]
			if len(m) > 2: bgcolor = "#FACE8D"
			s += "<tr><td align=\"right\" valign=\"top\" bgcolor=\"%(bg)s\"><b>%(a)s </b></td><td bgcolor=\"%(bg)s\">%(b)s</td></tr>\n" % {'a':a, 'b':b, 'bg':bgcolor}
			cnt += 1
		s += "</table><a name='bottom'>&nbsp;</a></body></html>"
		
		try:
			f = codecs.open(owndir + self.ie_file_name, "w", "utf-8")
		except:
			import os.path as pt
			dts = pt.expanduser('~') + "\\" + self.ie_file_name
			f = open(dts, "w", "utf-8")
		f.write(s)
		f.close()
	
	def on_add_message(self, msg):
		self.pencil = False
		txt = msg
		txt = sx.escape(txt)
		txt = codecs.encode(txt, "utf-8")
		self.ch.send_message(txt, self.uniroom)

	def on_edit_key_down(self):
			self.pencil = True

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
