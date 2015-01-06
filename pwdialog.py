from guimporter import *

class pwdialog(QtGui.QDialog):
	def __init__(self):
		super(pwdialog, self).__init__()
		
		self.name = ""
		self.password = ""
		self.ok = False
		
		label_name = QtGui.QLabel("Login:")
		label_password = QtGui.QLabel("Password:")
		self.edit_name = QtGui.QLineEdit(self)
		self.edit_password = QtGui.QLineEdit(self)
		self.edit_password.setEchoMode(QtGui.QLineEdit.Password)
		
		btn_ok = QtGui.QPushButton("OK", self)
		btn_cancel = QtGui.QPushButton("Cancel", self)
		
		btn_ok.clicked.connect(self.on_ok)
		btn_cancel.clicked.connect(self.on_cancel)
		
		grid = QtGui.QGridLayout()
		grid.addWidget(label_name, 0, 0)
		grid.addWidget(self.edit_name, 0, 1)
		grid.addWidget(label_password, 1, 0)
		grid.addWidget(self.edit_password, 1, 1)
		grid.addWidget(btn_ok, 2, 0)
		grid.addWidget(btn_cancel, 2, 1)
		
		self.setLayout(grid)
		self.setWindowTitle("Login")
		self.setModal(True)
		#self.show()
		self.exec_()
	
	def on_ok(self):
		self.name = self.edit_name.text()
		self.password = self.edit_password.text()
		self.ok = True
		self.close()
	
	def on_cancel(self):
		self.close()