import serial
import glob
import time
from PIL import ImageTk, Image
import Tkinter as tk     # python 2
import tkFont as tkfont  # python 2
import os, sys, os.path
import subprocess, tkFileDialog, tkMessageBox
import ttk
from xmodem import XMODEM
import logging

history = [''] * 6
history_index = 0
Open = False

Window_Open = False

# Protocol bytes
NUL = b'\x00'
SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
ACK = b'\x06'
DLE = b'\x10'
NAK = b'\x15'
CAN = b'\x18'
CRC = b'C'

class serial_port(tk.Tk):
	def __init__(self, *args, **kwargs):
		tk.Tk.__init__(self, *args, **kwargs)
		logging.basicConfig()

		self.protocol("WM_DELETE_WINDOW", self.on_closing)
		global Window_Open
		Window_Open = True
		
		self.title("Serial port")
		self.resizable(False, False)
		
		self.List = tk.Listbox(self, width=13, height = len(glob.glob('/dev/ttyUSB*')), exportselection=False)
		self.has_scaned = []
		self.scan_usb_device()

		self.List.grid(row=1, column=1, sticky="w")
		
		open = tk.Button(self, text = "Open device", command=self.connect)
		open.grid(row = 1, column = 1)
		
		close = tk.Button(self, text = "Close device", command=self.disconnect)
		close.grid(row = 1, column = 1, sticky="e")
		
		send_file = tk.Button(self, text = "Send file", command=self.open_file)
		send_file.grid(row = 2, column = 1, sticky="w")
		
		clear_btn = tk.Button(self, text = "Clear", command=self.clear)
		clear_btn.grid(row = 2, column = 1, sticky="e")
		
		save_log = tk.Button(self, text = "Save to", command=self.save_to_file)
		save_log.grid(row = 2, column = 1)
		
		yscrollbar = tk.Scrollbar(self)
		yscrollbar.grid(row=4, column=2, sticky="ns")
		xscrollbar = tk.Scrollbar(self,orient="horizontal")
		xscrollbar.grid(row=5, column=1, sticky="we")
		
		self.mge = tk.Text(self, width=47, height=30,wrap="none", yscrollcommand=yscrollbar.set, xscrollcommand=xscrollbar.set)
		self.mge.grid(row=4, column=1)
		yscrollbar.config(command=self.mge.yview)
		xscrollbar.config(command=self.mge.xview)
		
		input = tk.Label(self, text = "Input:")
		input.grid(row = 6, column = 0)
		self.e1 = tk.Entry(self, bg="gray", bd=5, width=35)
		#if config and config[1] != '-1':
		#	self.e1.insert("end", config[1])
		self.e1.bind('<Return>', self.send)
		self.e1.bind('<Up>', self.history_up)
		self.e1.bind('<Down>', self.history_down)
		self.e1.grid(row = 6, column = 1, sticky="w")
		
		send_btn = tk.Button(self, text = "Send", command=self.send)
		send_btn.grid(row=6, column=1, sticky="e")
		
		self.read_loop()
		
		self.history_tmp_index = history_index
		self.filename = None
		self.file_opt={}
		self.file_opt['title'] = "Save As" 
		self.file_opt['filetypes']=[("bin","*.bin"), ("allfiles","*")]
		self.file_opt['initialdir'] = "./"
		self.file_opt['initialfile'] = "log.bin" 
		
	def save_to_file(self):
		if not self.List.curselection():
			tkMessageBox.showerror("Error", "Device lose")
			return
		if not Open:
			tkMessageBox.showerror("Error", "Device does not connect.")
			return
		data = self.mge.get("1.0",'end-1c')
		self.filename = tkFileDialog.asksaveasfilename(**self.file_opt)
		if self.filename == "":
			return
		else:
			try:
				ff = open(self.filename, 'wb')
				ff.write(data)
				ff.close()
				tkMessageBox.showinfo("Information", "Log saved.")
			except:
				tkMessageBox.showinfo("Information", "Error!")
		
	def on_closing(self):
		if tkMessageBox.askokcancel("Quit", "Do you want to quit?"):
			self.after_cancel(self.readloop_after)
			self.after_cancel(self.scanusb_after)
			
			global Open, Window_Open
			Window_Open = False
			if Open:
				self.s.close()
				Open = False
			self.destroy()
	
	def clear(self):
		self.mge.delete("1.0",'end-1c')
	
	def scan_usb_device(self):
		self.scanusb_after = self.after(10, self.scan_usb_device)
		# scan for available ports. return a list of device names.
		for device in glob.glob('/dev/ttyUSB*'):
			if not device in self.has_scaned:
				self.List.insert("end", device)
				self.has_scaned.append(device)
		index = 0
		for device in self.has_scaned:
			if not device in glob.glob('/dev/ttyUSB*'):
				self.List.delete(index)
				self.has_scaned.pop(index)
			index += 1
			
	def connect(self):
		if not self.List.curselection():
			tkMessageBox.showerror("Error", "Device lose")
			return
		device = self.List.curselection()[0]

		try:
			self.s = serial.Serial(port=self.List.get(device), baudrate=921600, bytesize=8, parity='N' ) 
			self.s.flushInput()
			self.s.flushOutput()
			global Open
			Open = True
			self.mge.insert("insert", "Device connect....\n")
		except:
			self.mge.insert("insert", "Disconnect error....\n")
	
	def disconnect(self):
		if not self.List.curselection():
			tkMessageBox.showerror("Error", "Device lose")
			return
		try:
			self.s.close()
			global Open
			Open = False
			self.mge.insert("insert", "Device disconnect....\n")
		except:
			self.mge.insert("insert", "Disconnect error....\n")
	
	def send(self, event=None):
		if not self.List.curselection():
			tkMessageBox.showerror("Error", "Device lose")
			return
		if not Open:
			tkMessageBox.showerror("Error", "Device does not connect.")
			return
		if self.e1.get() != '':
			global history_index, history
			if history_index != 5:
				history[history_index] = self.e1.get()
				history_index += 1
			else:
				for i in range(4):
					history[i] = history[i+1]
				history[4] = self.e1.get()
			self.history_tmp_index = history_index
			#print history
		
			self.s.write(self.e1.get()+'\r')
			self.e1.delete(0, 'end')
			time.sleep(0.01)
		else:
			self.s.write('\r')
			time.sleep(0.01)
			return
		
	def receive(self):
		out = ''
		while self.s.inWaiting() > 0:
			data = self.s.read(1)
			if data == NUL:
				data = ''	
			out += data
			if self.s.inWaiting() == 0:
				time.sleep(0.01)
				if self.s.inWaiting() == 0:
					break
		if out != '':
			self.mge.insert("insert", out)
			
	def read_loop(self):
		self.readloop_after = self.after(10, self.read_loop)
		if Open :
			self.receive()
			
	def history_up(self, event=None):
		if self.history_tmp_index != 0:
			self.history_tmp_index -= 1
		self.e1.delete(0, 'end')
		self.e1.insert("end", history[self.history_tmp_index])
		
	def history_down(self, event=None):
		if self.history_tmp_index != history_index:
			self.history_tmp_index += 1
		self.e1.delete(0, 'end')
		self.e1.insert("end", history[self.history_tmp_index])
		
	def open_file(self):
		if not self.List.curselection():
			tkMessageBox.showerror("Error", "Device lose")
			return
		if not Open:
			tkMessageBox.showerror("Error", "Device does not connect.")
			return

		self.filename = tkFileDialog.askopenfilename()
		print self.filename 
		if self.filename == '':
			return
		else:
			#progressbar gui
			self.win = tk.Tk()
			self.win.title("Progress")
			self.win.geometry("250x80")
			self.p = ttk.Progressbar(self.win,orient="horizontal",length=200,mode='determinate', maximum=100, value=0)
			self.label1 = tk.Label(self.win, text="Send file...")
			self.label2 = tk.Label(self.win, text="0.00%")
			self.label1.pack()
			self.p.pack()
			self.label2.pack()
			
			stream = open(self.filename, 'rb')
			if self.xmodem_send(self.s, stream):
				stream.close()
				self.mge.insert("insert", "Send file success!\n")
			else:
				stream.close()
				self.mge.insert("insert", "Send file error!\n")
				#self.win.destroy()
	

	def xmodem_send(self, serial, file):
		length = len(file.read()) / 128
		file.seek(0, 0)
		i = 1
		t, anim = 0, '|/-\\'
		serial.setTimeout(1)
		while 1:
			if serial.read(1) != NAK:
				t = t + 1
				print anim[t%len(anim)],'\r',
				if t == 60 : return False
			else:
				break

		p = 1
		s = file.read(128)
		while s:
			s = s + '\xFF'*(128 - len(s))
			chk = 0
			for c in s:
				chk+=ord(c)
			while 1:
				serial.write(SOH)
				serial.write(chr(p))
				serial.write(chr(255 - p))
				serial.write(s)
				serial.write(chr(chk%256))
				serial.flush()

				answer = serial.read(1)
				if  answer == NAK: continue
				if  answer == ACK: break
				return False
			s = file.read(128)
			p = (p + 1)%256
			
			# update progressbar
			progress = (100*i) / float(length)
			self.p["value"] = progress
			self.label2["text"] = str(round(progress, 2))+'%'
			self.win.update_idletasks()
			i += 1
			
		serial.write(EOT)
		if progress == 100:
			self.win.destroy()
			return True
		else:
			return False

if __name__ == "__main__":
	app = serial_port()
	app.mainloop()
	