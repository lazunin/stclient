from __future__ import with_statement
import httplib, time

import socket, base64

import thread, time, codecs, re

import xml.sax.saxutils as sx

import sys, os

pathname = os.path.dirname(sys.argv[0])
owndir = os.path.abspath(pathname) + os.sep
lang_numbers = {}

f = open(owndir + "langs.txt")
for l in f:
	n, t = [x.strip() for x in l.split(":")]
	n = int(n)
	lang_numbers[n] = t
f.close()

lang_prefixes = {1: "En", 2: "Sp", 4: "Ja", 9: "Pt", 7: "Ch", 8: "Ru", 3: "Fr", 11: "Ko", 10: "Ar", 6: "It", 5: "Ge", 17: "Tu", 12: "Hi", 13: "Ca", 15: "Du", 18: "Sw", 22: "Th", 23: "Po", 36: "Hu"}



## rooms_list = [ 	['CREnRu', 'CREnJa', 'CRJaRu', 'CREnSp', 'CREnFr', 'CREnPt', 'CREnZh', 'CREn',     'CRSpFr', 'CRSpPt', 'CRSp', 'CRFrPt', 'CRFr', 
## 				'CRDe', 'CRJa', 'CRIt', 'CRZh', 'CRRu', 'CRPt', 'CRKo', 'CROther', 'CRSca'], 
## 			['English-Russian', 'English-Japanese', 'Japanese-Russian', 'English-Spanish', 'English-French', 'English-Portuguese', 'English-Chinese (Mandarin)', 'English-Other', 'Spanish-French', 
## 				'Spanish-Portuguese', 'Spanish-Other', 'French-Portuguese', 'French-Other', 
## 				'German', 'Japanese', 'Italian', 'Chinese (Mandarin)', 'Russian', 'Portuguese', 'Korean', 'Multi-Language', 'Scandinavian Languages']]

def get_personalized_rooms(pls, kls):
	pp = pls.strip('"').strip("'")
	kk = kls.strip('"').strip("'")
	pp = [int(p) for p in pp.split("|")]
	kk = [int(p) for p in kk.split("|")]
	rooms = {} #"verbose" : "short"

	def get_pair(p, k):
		verbose_p = lang_numbers[p]
		short_p = lang_prefixes[p] if p in lang_prefixes.keys() else str(p)
		
		verbose_k = lang_numbers[k]
		short_k = lang_prefixes[k] if k in lang_prefixes.keys() else str(k)
		
		a = [(p, verbose_p, short_p), (k, verbose_k, short_k)]
		a.sort(key = lambda x: x[0])
		return (a[0][1] + "-" + a[1][1], "CR%s%s" % (a[0][2], a[1][2]))
	
	for p in pp:
		for k in kk:
			pair = get_pair(p, k)
			rooms[pair[0]] = pair[1]

	for s in pp + kk:
		verbose = lang_numbers[s]
		short = lang_prefixes[s] if s in lang_prefixes.keys() else str(s)
		rooms[verbose] = "CR" + short

	return rooms

#print get_personalized_rooms("1|4|98", "8")

def get_tag_attributes(data):
	#data2 = data.split(" ")
	data2 = re.findall(" .*?=[\"\'].*?[\"\']", data)
	data2 = [x.strip() for x in data2]
	dct = {}
	for d in data2: 
		if "=" in d: 
			dl, dr = d.split("=")
			dct[dl] = dr
	return dct

def get_tag_attributes2(data):
	#data2 = data.split(" ")
	#data2 = re.findall(" .*?=[\"\'].*?[\"\']", data)
	data2 = re.findall(" .*?=[\"].*?[\"]", data) + re.findall(" .*?=[\'].*?[\']", data)
	data2 = [x.strip() for x in data2]
	dct = {}
	for d in data2: 
		if "=" in d: 
			dl, dr = d.split("=")
			dct[dl] = dr[1:-1]
	return dct


def send_data(conn, selector, data_s, headers_s):
	import copy
	headers2 = copy.copy(headers_s)
	headers2["Content-Length"] = str(len(data_s))
	conn.request("POST", selector, data_s, headers2)
	response = conn.getresponse()
	s, r = response.status, response.reason
	data_new = response.read()
	return (s, r, data_new)

class chatroom:
	def __init__(self):
		self.users_dict = {}
		self.messages = []


class chatterbox:
	
	def __init__(self, proxy):
		self.headers = {
		"Connection": "keep-alive",
		"Content-Length": "0",
		"Origin": "http://sharedtalk.com",
		"User-Agent" : "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.79 Safari/535.11",
		"Accept": "*/*",
		"content-type": "application/x-www-form-urlencoded",
		"Accept-Language": "en-US,en;q=0.8",
		"Accept-Encoding": "gzip,deflate,sdch",
		"Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.3",
		#"Keep-Alive": "300"		
		}
	
		self.login_dict = {} #??
		self.all_users_dict = {}
		self.rooms = {} # rooms["CRRu"] = chatroom(ud, msgs)
		
		self.msgs_limit = 200 #not in use now
		
		self.logfile = None
		self.wannaexit = False
		#self.logfile = open("0002log.txt", "wb")
		
		#self.msg s_log = open("messages_log.txt", "wb")
		
		self.pcb = None
		
		self.private_waiting_list = [[], []]
		self.private_accepted_list = [[], []]
		
		self.out_p_waiting_list = set([])
		self.out_p_accepted_list = set([])
		
		
		self.pencils = set([])
		self.incoming_pencils = set([])
		
		self.ignore_list = set([])
		
		self.login_status = ""
		
		self.use_tor = False
		
		if proxy != "":
			self.use_tor = True
			self.target_host = proxy
			print "Using a proxy: " + proxy
		else:
			self.target_host = "sharedtalk.com:80"
		
		self.the_lock = thread.allocate_lock()		
		self.data_lock = thread.allocate_lock()
		self.pencil_lock = thread.allocate_lock()

		self.room_list = [{},
				   {
					   "English-Spanish" : "CREnSp",
					   "English-Japanese" : "CREnJa",
					   "English-Portuguese" : "CREnPt",
					   "English-Chinese (Mandarin)" : "CREnCh",
					   "English-Russian" : "CREnRu",
					   "English-French" : "CREnFr",
					   "English-Korean" : "CREnKo",
					   "English-Arabic" : "CREnAr",
					   "English-Italian" : "CREnIt",
					   "English-German" : "CREnGe",
					   "English-Turkish" : "CREnTu"
					   },
				   {
					   "English" : "En",
					   "Spanish" : "Sp",
					   "French" : "Fr",
					   "Japanese" : "Ja",
					   "German" : "Ge",
					   "Italian" : "It",
					   "Chinese (Mandarin)" : "Ch",
					   "Russian" : "Ru",
					   "Portuguese" : "Pt",
					   "Arabic" : "Ar",
					   "Korean" : "Ko",
					   "Hindi" : "Hi",
					   "Chinese (Cantonese)" : "Ca",
					   "Dutch" : "Du",
					   "Turkish" : "Tu",
					   "Swedish" : "Sw",
					   "Persian (Farsi)" : "Pe",
					   "Thai" : "Th",
					   "Polish" : "Po",
					   "Hungarian" : "Hu"
					   },
				   {
					   "Multi-Language" : "Other",
					   "Scandinavian Languages" : "Sca"
					   }
				   ]
	
	def get_all_users(self):
		from copy import deepcopy
		with self.data_lock:
			return deepcopy(self.all_users_dict)
	
	def get_login_status(self):
		with self.data_lock:
			return self.login_status
	
	def get_opened_rooms_titles(self):
		with self.data_lock:
			return self.rooms.keys()
	
	def get_private_waiting_list(self):
		from copy import deepcopy
		with self.data_lock:
			return deepcopy(self.private_waiting_list)
	
	def get_my_accepted_privates(self):
		from copy import deepcopy
		with self.data_lock:
			return deepcopy(self.out_p_accepted_list)
	
	def get_private_accepted_list(self):
		from copy import deepcopy
		with self.data_lock:
			return deepcopy(self.private_accepted_list)
	
	def get_ignore_list(self):
		from copy import deepcopy
		with self.data_lock:
			return deepcopy(self.ignore_list)
	
	def add_to_ignore_list(self, user):
		with self.the_lock:
			with self.data_lock:
				self.ignore_list.add(user)
	
	def remove_from_ignore_list(self, user):
		with self.the_lock:
			with self.data_lock:
				self.ignore_list.remove(user)
	
	def is_user_ignored(self, user):
		with self.data_lock:
			return (user in self.ignore_list)
	
	def get_all_users_dict(self):
		from copy import deepcopy
		with self.data_lock:
			return deepcopy(self.all_users_dict)
		
	def send_receive(self, resource, data, postprocess):		
		if self.logfile:
			self.logfile.write("sent:\r\n" + data + "\r\n")
			self.logfile.write("\r\n-----------------\r\n")
		rsc = "sharedtalk.com" + resource if self.use_tor else resource
		s, r, received_data = send_data(self.conn, rsc, data, self.headers)
		if self.logfile:
			self.logfile.write(`s` + " " + r + "\r\n")
			self.logfile.write(received_data)
			self.logfile.write("\r\n-----------------\r\n")
		
		
		if s==200 and r=="OK":
			return postprocess(received_data)
		else:
			print s, r
			print data
			#return False
			print "trying to re-send..."
			return self.send_receive(resource, data, postprocess)


	def login(self, name, password):
		with self.the_lock:
			login_data = "<LI PW=\"%s\" UN=\"%s\" />" %(password, name)
			
			self.conn = httplib.HTTPConnection(self.target_host)
			
			def pp(ldata):
				with self.data_lock:
					if ldata.startswith("<FullBan"):
						self.login_status = "banned"
						return False
					elif ldata.startswith("<Failure"):
						self.login_status = "wrong"
						return False
					self.login_dict = get_tag_attributes(ldata[:-2])

					try:
						#print self.login_dict
						self.room_list[0] = get_personalized_rooms(self.login_dict["PLs"], self.login_dict["KLs"])
						return True
					except:
						return False
			
			return self.send_receive("/Members/Login.ashx", login_data, pp)

	def join_text_chat(self):
		self.the_lock.acquire()
		
		with self.data_lock:
			a = self.login_dict
			#join_data = "<U PLs=%s KLs=%s LID=%s A=%s G=%s LN=%s FN=%s UID=%s />" % (a["PLs"], a["KLs"], a["LID"], a["A"], a["G"], a["LN"], a["FN"], a["UID"])
			join_data = "<U SSID=%s PLs=%s KLs=%s LID=%s A=%s G=%s LN=%s FN=%s UID=%s />" % (a["SSID"], a["PLs"], a["KLs"], a["LID"], a["A"], a["G"], a["LN"], a["FN"], a["UID"])
		def pp(ldata):
			self.parse_users(ldata)			
			join_dict = get_tag_attributes(ldata[:ldata.index(">")])
			with self.data_lock:
				for k, v in join_dict.items():
					self.login_dict[k] = v
				self.login_dict["D"] = '"0"'
				self.login_dict["lupd"] = '"0"'
				self.login_dict["updc"] = 1			
			tid = thread.start_new_thread(self.update_rooms, ())
			return True
		
		res = self.send_receive("/Chat3/JoinTC.ashx", join_data, pp)
		
		self.the_lock.release()
		return res

	def join_room(self, room):
		
		self.the_lock.acquire()
		
		def pp(ldata):			
			self.update_upd_id(ldata)
			with self.data_lock:
				self.rooms[room] = chatroom()
			self.parse_users(ldata)
			self.update_room_users(room, ldata)
			self.parse_all_messages(room, ldata)
			return True
		
		with self.data_lock:
			data_s = "<E R=\"%s\" />" % (room)
			data_s = self.form_data(data_s)
			
		res = self.timed_send_receive(data_s, pp)			
		self.the_lock.release()		
		return res

	def join_private(self, room):		
		self.the_lock.acquire()		
		withwhom = room.split("-")[0]		
		with self.data_lock:
			i = self.private_waiting_list[0].index(room)
			
			pw0, pw1 = self.private_waiting_list[0], self.private_waiting_list[1]
			
			ac0, ac1 = pw0[i], pw1[i]
			self.private_accepted_list[0].append(ac0)
			self.private_accepted_list[1].append(ac1)		
			
			self.private_waiting_list[0] = pw0[:i] + pw0[i+1:]
			self.private_waiting_list[1] = pw1[:i] + pw1[i+1:]
			
			u = self.login_dict
		
		def pp(ldata):
			self.update_upd_id(ldata)		
			with self.data_lock:
				self.rooms[room] = chatroom()
				self.rooms[room].users_dict[u['UID'][1:-1]] = (u["FN"][1:-1], u["LN"][1:-1], "F" if u['G'][1:-1] == "1" else "M", u['A'][1:-1], u['PLs'][1:-1], u['KLs'][1:-1], u['LID'][1:-1])
				self.rooms[room].users_dict[withwhom] = self.all_users_dict[withwhom]
			self.parse_all_messages(room, ldata)
			self.parse_last_messages(ldata)
			return True		
		
		with self.data_lock:
			data_s = "<CR V=\"Ok\" UID=\"%s\" /><E R=\"%s\" />" % (room.split("-")[0], room)
			data_s = self.form_data(data_s)
		
		res = self.timed_send_receive(data_s, pp)
		self.the_lock.release()		
		return res

	def join_my_private(self, withwhom):
		self.the_lock.acquire()
		with self.data_lock:
			room = self.login_dict["UID"][1:-1] + "-" + withwhom
			self.out_p_accepted_list.remove(withwhom)
			u = self.login_dict
		
		def pp(ldata):
			self.update_upd_id(ldata)
			with self.data_lock:						
				self.rooms[room] = chatroom()
				self.rooms[room].users_dict[u['UID'][1:-1]] = (u["FN"][1:-1], u["LN"][1:-1], "F" if u['G'][1:-1] == "1" else "M", u['A'][1:-1], u['PLs'][1:-1], u['KLs'][1:-1], u['LID'][1:-1])
				self.rooms[room].users_dict[withwhom] = self.all_users_dict[withwhom]
			self.parse_all_messages(room, ldata)
			self.parse_last_messages(ldata)
			return room
		
		with self.data_lock:
			data_s = "<E R=\"%s\" />" % (room)
			data_s = self.form_data(data_s)
		
		res = self.timed_send_receive(data_s, pp)
		self.the_lock.release()
		
		return res

	def decline_private(self, room):
		
		self.the_lock.acquire()
		
		with self.data_lock:
			withwhom = room.split("-")[0]		
			i = self.private_waiting_list[0].index(room)		
			pw0, pw1 = self.private_waiting_list[0], self.private_waiting_list[1]		
			self.private_waiting_list[0] = pw0[:i] + pw0[i+1:]
			self.private_waiting_list[1] = pw1[:i] + pw1[i+1:]
		
		def pp(ldata):
			self.update_upd_id(ldata)
			self.parse_last_messages(ldata)
			return True
		
		with self.data_lock:
			data_s = "<CR V=\"No\" UID=\"%s\" />" % (room.split("-")[0])
			data_s = self.form_data(data_s)
		
		res = self.timed_send_receive(data_s, pp)
		self.the_lock.release()		
		return res
	

	#--------------------------
	def form_data(self, data):
		
		u = self.login_dict
		rooms = self.rooms.keys()
		Rs = ",".join(rooms)			
		Rs = codecs.encode(Rs, "utf-8")			
		if (u["D"][0] != "'") and (u["D"][0] != '"'): u["D"] = `u["D"]`
		
		data_s = "<UPDs D=%s UID=%s GUID=%s LUPD=%s UPDC=%s Rs=\"%s\"" % (u["D"], u["UID"], u["GUID"], u["lupd"], '"'+str(u["updc"])+'"', Rs)
		if data:
			data_s += ">%s</UPDs>" % data
		else:
			data_s += " />"
		
		return data_s
	
	def timed_send_receive(self, data_s, pp):
		tbefore = time.time()		
		res = self.send_receive("/Chat3/GetTCUpdate.ashx", data_s, pp)
		with self.data_lock:
			u = self.login_dict
			update_duration = time.time() - tbefore
			updtxt = str(update_duration)
			u["D"] = updtxt[updtxt.index(".")+1:][:3]
			u["updc"] += 1
		return res


	def update_messages(self, message=None, room=None):
		self.the_lock.acquire()
		
		pencils = ""
		with self.data_lock:
			for r in self.pencils:
				pencils += "<FP R=\"%s\" />" % (r)
			self.pencils = set([])
		with self.data_lock:
			
			if message:
				data_s = "<M R=\"%s\">%s</M>" % (room, message)
			elif len(pencils)>0:
				data_s = pencils
			else:
				data_s = ""
			
			data_s = self.form_data(data_s)
		def pp(ldata):
			self.update_upd_id(ldata)
			self.parse_last_messages(ldata)
			return True
		res = self.timed_send_receive(data_s, pp)
		with self.data_lock:
			if message: self.rooms[room].messages.append((self.login_dict['FN'][1:-1], message, '*'))
		self.the_lock.release()
		return res
	#--------------------------

	def call_user(self, user):
		
		self.the_lock.acquire()
		
		with self.data_lock:
			data_s = "<C UID=\"%s\" />" % (user)
			data_s = self.form_data(data_s)
		
		def pp(ldata):
			self.update_upd_id(ldata)
			self.parse_last_messages(ldata)
			with self.data_lock:
				self.out_p_waiting_list.add(user)
			return True

		res = self.timed_send_receive(data_s, pp)
		self.the_lock.release()		
		return res

	def get_user_info(self, uid, escaped=False):
		self.the_lock.acquire()
		def pp(ldata):
			import re
			b = re.findall("L=\"(.*?)\".*? D=\"(.*?)\"", ldata)
			if not escaped:
				b = [sx.unescape(x, {"&apos;" : "'", "&quot;" : "\""}) for x in b[0]]
			return b
		data_s = "<U UID=\"%s\" />"%(uid)
		res = self.send_receive("/Members/GetFullMember.aspx", data_s, pp)
		self.the_lock.release()
		return res

	def logout(self):
		with self.data_lock:
			self.wannaexit = True
	
	def get_user_name(self, userid):
		with self.data_lock:
			u = self.all_users_dict[userid]
			return " ".join(u[:2])
	
	def leave_room(self, room):
		with self.data_lock:
			self.rooms.pop(room)
			
			if room in self.private_accepted_list[0]:
				pal = self.private_accepted_list
				i = pal[0].index(room)
				self.private_accepted_list = [ pal[0][:i] + pal[0][i+1:], pal[1][:i] + pal[1][i+1:] ]
	
	def update_rooms(self):
		while True:
			self.push_pencils()
			with self.data_lock: n = len(self.rooms.keys())
			if n > 0:
				with self.data_lock:
					if self.wannaexit:
						self.login_dict = {}
						self.all_users_dict = {}
						self.rooms = {}
						self.wannaexit = False
						return
				self.update_messages()
			time.sleep(4)
	
	def send_message(self, message, room):
		self.update_messages(message=message, room=room)
	
	def toggle_pencil(self, room):
		with self.pencil_lock:
			self.incoming_pencils.add(room)
	
	def push_pencils(self):
		from copy import copy
		with self.pencil_lock:
			if len(self.incoming_pencils) == 0: return
			m_pencils = copy(self.incoming_pencils)
			self.incoming_pencils = set([])
		if self.the_lock.locked(): return
		with self.the_lock:
			with self.data_lock:
				self.pencils |= m_pencils
	
	def get_room_users(self, room):
		from copy import deepcopy
		with self.data_lock:
			ud = deepcopy(self.rooms[room].users_dict)
		return ud
	
	def get_room_messages(self, room):
		from copy import deepcopy
		with self.data_lock:
			msgs = deepcopy(self.rooms[room].messages)
			self.rooms[room].messages = []
		return msgs
	
	def update_upd_id(self, data):
		m = re.findall("<UPD ID=\'(.*?)\'>", data, re.DOTALL)
		if len(m) == 0: return
		m = [int(x) for x in m]
		with self.data_lock:
			self.login_dict["lupd"] = ``max(m)``
		
		
	def ignore_private(self, room):
		
		with self.data_lock:
			i = self.private_waiting_list[0].index(room)
			
			pw0, pw1 = self.private_waiting_list[0], self.private_waiting_list[1]
			
			ac0, ac1 = pw0[i], pw1[i]
			self.private_accepted_list[0].append(ac0)
			self.private_accepted_list[1].append(ac1)		
			
			self.private_waiting_list[0] = pw0[:i] + pw0[i+1:]
			self.private_waiting_list[1] = pw1[:i] + pw1[i+1:]
	
	def parse_all_messages(self, room, data):
		if data.find("<Error />") >= 0: 
			self.on_returned_error(data)
			return
		m = re.findall("<M><uN>(.*?)</uN><mO>(.*?)</mO></M>", data, re.DOTALL)
		m2 = [(x[0][:-3], x[1]) for x in m]
		with self.data_lock:
			self.rooms[room].messages = m2
	
	def parse_last_messages(self, data):
		if data.find("<Error />") >= 0: 
			self.on_returned_error(data)
			return
		sorted_m = re.findall("<UPD ID=\'(.*?)\'>(.*?)</UPD>", data, re.DOTALL)
		sorted_m.sort(key = lambda x: int(x[0]))
		#<Error />
		for sm in sorted_m:			
			"""
			if sm[1].startswith("<M R="): self.add_message(sm[1])
			elif sm[1].startswith("<U PLs=") or sm[1].startswith("<U SSID=") or sm[1].startswith("<U PW="): self.add_global_user(sm[1])
			elif sm[1].startswith("<DU UID="): self.del_global_user(sm[1])
			elif sm[1].startswith("<U R="): self.add_room_user(sm[1])
			elif sm[1].startswith("<DU R="): self.del_room_user(sm[1])
			elif sm[1].startswith("<C UID="): self.add_private_request(sm[1])
			elif sm[1].startswith("<CR UID="): self.on_my_private_request(sm[1])
			#elif sm[1].find("<Error />") >= 0: self.on_returned_error(sm[1])
			"""
			if sm[1].startswith("<M "): self.add_message(sm[1])
			#elif sm[1].startswith("<U ") and "SSID=" in sm[1]: self.add_global_user(sm[1])
			elif sm[1].startswith("<U ") and ("LN=" in sm[1]) and ("FN=" in sm[1]) and ("UID=" in sm[1]): self.add_global_user(sm[1])
			elif sm[1].startswith("<DU ") and "R=" in sm[1]: self.del_room_user(sm[1])
			elif sm[1].startswith("<DU ") and "UID=" in sm[1]: self.del_global_user(sm[1])
			elif sm[1].startswith("<U ") and "R=" in sm[1]: self.add_room_user(sm[1])			
			elif sm[1].startswith("<C ") and "UID=" in sm[1]: self.add_private_request(sm[1])
			elif sm[1].startswith("<CR ") and "UID=" in sm[1]: self.on_my_private_request(sm[1])

	
	#----------------- actions with messages received from sharedtalk server ------------------
	def add_message(self, message):
		#m = re.match("<M R=\'(.*?)\' UID=\'(.*?)\'>(.*?)</M>", message, re.DOTALL).groups()
		#rm = m[0]
		msg = re.match("<M .*?>(.*?)</M>", message, re.DOTALL).groups()[0]
		m = get_tag_attributes2(message)
		rm = m['R']
		with self.data_lock:
			if not rm in self.rooms.keys():
				return
			if m['UID'] in self.all_users_dict.keys():				
				#usr = self.all_users_dict[m[1]][0] #***!!!
				usr = m['UID']
			else: usr = "???"
			#msg = m[2]
			if not m['UID'] in self.ignore_list:
				self.rooms[rm].messages.append((usr, msg))
	
	def add_global_user(self, message):
		#m1 = re.match("<U SSID=\".*?\" PLs=\"(.*?)\" KLs=\"(.*?)\" LID=\"(.*?)\" A=\"(.*?)\" G=\"(.*?)\" LN=\"(.*?)\" FN=\"(.*?)\" UID=\"(.*?)\" />", message, re.DOTALL).groups()
		m = get_tag_attributes2(message)
		#print "add_global_user"
		#print message
		with self.data_lock:
			#{'LID': '121', 'A': '18', 'PLs': '1', 'SSID': '9533424711', 'G': '0', 'LN': '', 'KLs': '7', 'FN': 'Jimmy', 'UID': '1306363'}
			
			self.all_users_dict[m["UID"]] = [ m["FN"], m["LN"], ("M" if m["G"]=="0" else "F"),  m["A"], m["PLs"], m["KLs"], m["LID"] ]
		"""
		if len(m) > 0:
			with self.data_lock:
				self.all_users_dict[m[7]] = [m[6], m[5], ("M" if m[4]=="0" else "F"), m[3], m[0], m[1], m[2]]
			return
		"""
		
		
	
	def del_global_user(self, message):
		#m = re.match("<DU UID=\'(.*?)\' />", message, re.DOTALL).groups()
		m = get_tag_attributes2(message)
		#print "del_global_user"
		#print message
		with self.data_lock:
			if m['UID'] in self.all_users_dict.keys():
				self.all_users_dict.pop(m['UID'])
	
	def add_room_user(self, message):
		#m = re.match("<U R=\'(.*?)\' UID=\'(.*?)\' />", message, re.DOTALL).groups()
		m = get_tag_attributes2(message)
		#print "add_room_user"
		#print message
		with self.data_lock:
			if not m['R'] in self.rooms.keys(): return
			self.rooms[m['R']].users_dict[m['UID']] = self.all_users_dict[m['UID']]
	
	def del_room_user(self, message):
		#m = re.match("<DU R=\'(.*?)\' UID=\'(.*?)\' />", message, re.DOTALL).groups()
		m = get_tag_attributes2(message)
		#print "del_room_user"
		#print message
		with self.data_lock:
			if not m['R'] in self.rooms.keys(): return
			self.rooms[m['R']].users_dict.pop(m['UID'])
	
	def add_private_request(self, message):
		#m = re.match("<C UID=\'(.*?)\'/>", message, re.DOTALL).groups()
		m = get_tag_attributes2(message)
		with self.data_lock:
			if not m['UID'] in self.all_users_dict.keys(): return
			
			room = m['UID'] + "-" + self.login_dict["UID"][1:-1]
			
			#-
			room = codecs.encode(room, "utf-8") #***!!!
			#-
			
			pwl0, pwl1 = self.private_waiting_list[0], self.private_waiting_list[1]
			if not room in pwl0:
				pwl0.append(room)
				pwl1.append(self.all_users_dict[m['UID']][0] + " " + self.all_users_dict[m['UID']][1])
	
	def on_returned_error(self, message):
		print "Error returned - you have to re-login."
	
	def on_my_private_request(self, message):
		#m = re.match("<CR UID=\'(.*?)\' V=\'(.*?)\'/>", message, re.DOTALL).groups()
		m = get_tag_attributes2(message)
		with self.data_lock:
			if m['UID'] in self.out_p_waiting_list:
				self.out_p_waiting_list.remove(m['UID'])
				if m['V'] == "Ok":
					self.out_p_accepted_list.add(m['UID'])
	#----------------- ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ------------------
	
	def parse_users(self, data):
		#A="31" G="1"
		#m = re.findall("<U SSID=\".*?\" PLs=\"(.*?)\" KLs=\"(.*?)\" LID=\"(.*?)\" A=\"(.*?)\" G=\"(.*?)\" LN=\"(.*?)\" FN=\"(.*?)\" UID=\"(.*?)\" />", data, re.DOTALL)
		m = re.findall("<U .*? />", data, re.DOTALL)
		#0: PLs, 1: KLs, 2: LID, 3: A, 4: G, 5: LN, 6: FN, 7:UID
		
		for m2 in m:
			i = get_tag_attributes2(m2)
			#id = first name, last name, gender, age
			#print i
			with self.data_lock:
				try:
					self.all_users_dict[i['UID']] = [i['FN'], i['LN'], ("M" if i['G']=="0" else "F"), i['A'], i['PLs'], i['KLs'], i['LID']] #?
				except:
					"""
					print "Exception in parse_users"
					print data
					print "---------------------------"
					print m2
					print "---------------------------"
					print i
					"""
					self.all_users_dict[i['UID']] = ['*UNDEFINED*', '*UNDEFINED*', '*UNDEFINED*', '*UNDEFINED*', '*UNDEFINED*', '*UNDEFINED*', '*UNDEFINED*']
		"""
		#--------------------------------
		m = re.findall("<U PW=\".*?\" UN=\".*?\" PLs=\"(.*?)\" KLs=\"(.*?)\" LID=\"(.*?)\" A=\"(.*?)\" G=\"(.*?)\" LN=\"(.*?)\" FN=\"(.*?)\" UID=\"(.*?)\" />", data, re.DOTALL)
		for i in m:
			#id = first name, last name, gender, age
			with self.data_lock:
				self.all_users_dict[i[7]] = [i[6], i[5], ("M" if i[4]=="0" else "F"), i[3], i[0], i[1], i[2]] #?
		#--------------------------------
		
		#------------
		m = re.findall("<U PLs=\"(.*?)\" KLs=\"(.*?)\" LID=\"(.*?)\" A=\"(.*?)\" G=\"(.*?)\" LN=\"(.*?)\" FN=\"(.*?)\" UID=\"(.*?)\" />", data, re.DOTALL)
		for i in m:
			#id = first name, last name, gender, age
			with self.data_lock:
				self.all_users_dict[i[7]] = [i[6], i[5], ("M" if i[4]=="0" else "F"), i[3], i[0], i[1], i[2]] #?
		#------------
		
		m = re.findall("(<U .*? />)", data, re.DOTALL)
		for i in m:
			m2 = get_tag_attributes2(i)
			with self.data_lock:
				self.all_users_dict[i[7]] = [i[6], i[5], ("M" if i[4]=="0" else "F"), i[3], i[0], i[1], i[2]]
		"""
		#delete users who's left
		m = re.findall("<DU UID=\'(.*?)\' />", data, re.DOTALL)
		for i in m:
			with self.data_lock:
				if i in self.all_users_dict.keys():
					self.all_users_dict.pop(i)

	def update_room_users(self, room, data):
		#get all users in a particular room
		#called once when joining the room
		
		op = "<ER R=\'%s\'>"%(room)
		cl = "</ER>"
		if not op in data: return
		
		d = data
		d = d[d.index(op)+len(op):]
		d = d[:d.index(cl)]
		
		m = re.findall("<NU UID=\'(.*?)\' />", d, re.DOTALL)
		with self.data_lock:
			rud = self.rooms[room].users_dict
			for i in m:
				if i in self.all_users_dict.keys():
					rud[i] = self.all_users_dict[i]
			
			ld = self.login_dict
			rud[ld['UID'][1:-1]] = (ld["FN"][1:-1], ld["LN"][1:-1], "F" if ld['G'][1:-1] == "1" else "M", ld['A'][1:-1], ld['PLs'][1:-1], ld['KLs'][1:-1], ld['LID'][1:-1])

	
