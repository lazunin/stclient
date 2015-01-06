# -*- coding: utf-8 -*-

from guimporter import *

import codecs, os, sys

#import perverted as perv
pathname = os.path.dirname(sys.argv[0])
owndir = os.path.abspath(pathname) + os.sep
imgdir = owndir
if os.name != 'nt':
	imgdir = "file://" + owndir

class user_info_window(QtGui.QWidget):
	
	def __init__(self, parent, uid, ch, langdict, countries):
		super(user_info_window, self).__init__(None)#(parent)

		self.parent = parent
		self.content = QtWebKit.QWebView(self)
		
		self.user = uid
		#print "user_info_window for " + self.user
		self.ch = ch
		self.parent = parent
		self.langdict = langdict
		self.countries = countries
		
		hbox = QtGui.QHBoxLayout(self)
		hbox.addWidget(self.content)
		self.setLayout(hbox)
		#QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
			
		self.upd_uinfo()
		
		#self.content.Bind(html.EVT_HTML_LINK_CLICKED, self.on_link_clicked)
		#self.content.setHtml("")
		self.content.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
		self.content.linkClicked.connect(self.on_link_clicked)
	
	def upd_uinfo(self):
		uinfo = self.ch.get_user_info(self.user)
		uinfo = [codecs.decode(x, "utf-8") for x in uinfo]
		ui = self.ch.get_all_users_dict()[self.user]
		ui = [codecs.decode(x, "utf-8") for x in ui]
		
		c = "<html><head></head><body><table width=\"100%\" border=\"0\" cellpadding=\"1\" cellspacing=\"1\">"
		c += "<tr bgcolor = \"#FACE8D\"> <th colspan=2>%(fname)s %(lname)s, %(sex)s</th></tr>" % {"fname" : ui[0], "lname" : ui[1], "sex" : ("male" if ui[2]=="M" else "female")}
		c += "<tr bgcolor = \"#F6F6F6\"><td width=\"100\">Age:</td><td align=\"left\">%s</td></tr>" % (ui[3])
		c += "<tr bgcolor = \"#ECEDF3\"><td width=\"100\">Country:</td><td align=\"left\">%s</td></tr>" % (self.countries[ui[6]] if ui[6] in self.countries.keys() else ui[6])
		c += "<tr bgcolor = \"#F6F6F6\"><td width=\"100\">Knows:</td><td align=\"left\">%s</td></tr>" % (", ".join([ self.langdict[x] if x in self.langdict.keys() else x for x in ui[5].split("|") ]))
		c += "<tr bgcolor = \"#ECEDF3\"><td width=\"100\">Learns:</td><td align=\"left\">%s</td></tr>" % (", ".join([ self.langdict[x] if x in self.langdict.keys() else x for x in ui[4].split("|") ]))
		c += "<tr bgcolor = \"#F6F6F6\"><td width=\"100\">City:</td><td align=\"left\">%s</td></tr>" % (uinfo[0])
		c += "<tr bgcolor = \"#ECEDF3\"><th colspan=2 align=\"left\">%s</th></tr>" % uinfo[1]
		
		ignore = self.ch.get_ignore_list()
		if not self.user in ignore:
			c += "<tr bgcolor = \"#F6F6F6\"><th colspan=2 align=\"left\"><a href=\"call_%(uid)s\"><img src=\"%(img)s\"></a>&nbsp;<a href=\"call_%(uid)s\">Private call</a></th></tr>" % {"uid" : self.user, "img": imgdir + "talk.png"}
			#c += "<tr bgcolor = \"#F6F6F6\"><th colspan=2 align=\"left\"><a href=\"call_%(uid)s\"><img src=\"" + imgdir + "talk.png" + "\"></a>&nbsp;<a href=\"call_%(uid)s\">Private call</a></th></tr>" % {"uid" : self.user}
			c += "<tr bgcolor = \"#ECEDF3\"><th colspan=2 align=\"left\"><a href=\"addtoignore_%(uid)s\"><img src=\"" + imgdir + "ignore.png" + "\"></a>&nbsp;<a href=\"addtoignore_%(uid)s\">Add to ignore list</a></th></tr>" % {"uid" : self.user}
		else:
			#c += "<tr bgcolor = \"#F6F6F6\"><th colspan=2 align=\"left\">This user is in your ignore list.</th></tr>"
			c += "<tr bgcolor = \"#ECEDF3\"><th colspan=2 align=\"left\">This user is in your ignore list. <br><a href=\"rehab_%(uid)s\"><img src=\"" + imgdir + "rehab.png" + "\"></a>&nbsp;<a href=\"rehab_%(uid)s\">Rehabilitate</a></th></tr>" % {"uid" : self.user}
		
		c += "<tr bgcolor = \"#F6F6F6\"><th colspan=2 align=\"left\"><a href=\"filter_%(fname)s\"><img src=\"" + imgdir + "filter.png" + "\"></a>&nbsp;<a href=\"filter_%(fname)s\">Filter</a></th></tr>" % {"fname" : ui[0]}
		
		c += "</table></body></html>"
		self.content.setHtml(c)
		#self.content.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
		
	
	def on_link_clicked(self, link):
		href = link.path()
		#print "on_link_clicked " + href
		self.parent.user_action(href)
		self.upd_uinfo()
	
