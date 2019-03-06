#!/usr/bin/python

# IP Workshop 2012
# Dragos Barosan 		(bdl_rom@yahoo.com)
# Ioan-Dan Maiorescu		(ion.maiorescu@gmail.com)
# Rudolf Winckenbauer		(rudi_winckelbauer@yahoo.com)

import sys
import socket
import select
import getpass
import threading, thread, os

if len(sys.argv) != 4:
  sys.exit("Usage " + sys.argv[0] + " SERVER_IP PORT FTP_PORT")

lock = threading.Lock()

SERVER_HOST = socket.gethostbyname(sys.argv[1])
SERVER_PORT = int(sys.argv[2])
MAX_SIZE = 4096

FTP_HOST = ''
FTP_PORT = int(sys.argv[3])

# Create socket.
sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ftp_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

ftp_fd.bind( (FTP_HOST, FTP_PORT) )
ftp_fd.listen(64)

# Connect to socket.
sockfd.connect((SERVER_HOST, SERVER_PORT))

#sockfd.setblocking(0)

# Send data. Be sure all data is sent.
fds = [sockfd, sys.stdin, ftp_fd]

running = True
ack = raw_input("::Welcome to PyCloud!\n::Do you have an account?(y/n)\n")
while running:
	if ack in ['y', 'yes', 'YES', 'Yes', 'Y']: 
		sockfd.send('YES ACCOUNT')
		running = False
		user=raw_input("::Insert username: ")
		print user
		sockfd.send(user.strip())
		pw=raw_input("::Insert password:\n")
		sockfd.send(pw.strip())
	elif ack in ['n', 'no', 'NO', 'No', 'N']:
		sockfd.send('NO ACCOUNT')
		print '::Would you like to create an account? (y/n)'
		ack = raw_input()
		running2 = True
		while running2:
			if ack in ['y', 'yes', 'YES', 'Yes', 'Y']: 
				sockfd.send('CREATE')
				user = raw_input('::Insert your desired username: ')
				print user
				sockfd.send(user)
				answer = sockfd.recv(MAX_SIZE)
				while answer == 'DUPLICATE':
					print('::Username not available. Please insert another username.')
					user = raw_input('::Insert your desired username: ')
					print user
					sockfd.send(user)
					answer = sockfd.recv(MAX_SIZE)
				pw = raw_input('::Insert your password!')
				print '\n::Your password is: ', pw
				sockfd.send(pw)
				running2 = False
			elif ack in ['n', 'no', 'NO', 'No', 'N']:	
				print "Good bye."
				sys.exit()
			else:
				print '::Invalid answer. Please answer yes or no!'
				ack = raw_input()
		running = False
	else:
		print '::Invalid answer. Please answer yes or no!'
		ack = raw_input()



# Thread for sending a file
def ftp_send(client_fd, size, path):
	f = open(path, 'rb')
	x = client_fd.recv(MAX_SIZE)
	print '::Transfer starting: ', path
	if size % 512 == 0:	
		i = size / 512
	else:
		i = size / 512 + 1
	for j in range(i):
		chunk = f.read (512)
		client_fd.send(chunk)
	print '::Transfer Completed: ', path
	client_fd.close()

# Thread for receiving a file
def ftp_recv(client_fd, size, filename):
	f = open(filename, 'w')
	client_fd.send(filename)
	print '::Transfer starting: ', filename
	running = True
	if int(size) % 512 == 0:	
		i = int(size) / 512
	else:
		i = int(size) / 512 + 1
	for j in range(i):
		data = client_fd.recv(MAX_SIZE)
		f.write(data)
	print '::Transfer Completed: ', filename
	f.close()			
	client_fd.close()
	
# If someone wants to search in my shared item list
def view(var):
	try:
		sem = 0
		sh = open ('shared.db', 'r')
		s = ''
		sockfd.send('/w ' + var + ' My files are: ')
		print '::Sending file list to ', var
		for line in sh:
			sem = 1
			s = s + ' ' + line
		if sem == 1:
			sockfd.send('/w ' + var + ' ' + s)
		sh.close()
		if sem == 0:
			sockfd.send('/w ' + var + ' -')
	except IOError:
		sockfd.send('/client_list ::User has no shared files.')

# If a client searches for a file over the whole network
def search(var1, var2):
	fisier = var1
	nume = var2
	try:	
		sh = open('shared.db', 'r')
		for line in sh:
			if fisier == line.strip():
				s = '/here ' + nume
				sockfd.send(s)
		sh.close()
	except IOError:
		pass

# If a client requests a file from your shared files:
def request(var1, var2, var3):
	try:
		sh = open ('shared.db', 'r')
		sem = 0
		for line in sh:
			print line, var1
			if line[:-1] == var1.strip():
				sem = 1
		sh.close()
		if sem == 0:
			sockfd.send('/w ' + var3 + ' The file you requested is not on my shared files list.')
			return
	except IOError:
		sockfd.send('/w ' + var3 + ' The file you requested is not on my shared files list.')
	try:
		f = open(var1, 'r')
		f.close()
		sockfd.send('/send ' + var1 + ' ' + var3 + ' ')
		answer = sockfd.recv(MAX_SIZE)
		y = answer.split()
		if len(y) != 3:
			print answer
			return		
		ip = y[2]
		path = var1
		size = os.path.getsize(path)
		ftp_client_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		ftp_client_fd.connect ((ip, FTP_PORT))
		ftp_client_fd.send(path)
		ftp_client_fd.send(str(size))
		thread.start_new_thread(ftp_send,(ftp_client_fd, size, path))
	except IOError:
		sockfd.send('/senderror ' + var3)


# Start client (after log-in)
running = True
while running:
	# Make select:
	in_ready, out_ready, except_ready = select.select(fds, [], [])
	for fd in in_ready:
		# Reading data from server
		if fd == sockfd:
			data = sockfd.recv(MAX_SIZE)
	    		if data:
					com = data.split()
					if com[0] == '/view' or com[0] == '/view\n':
						view(com[1])
					elif com[0] == '/search' or com[0] == '/search\n':
						search(com[1], com[2])	
					elif com[0] == '/request':		
						request(com[1], com[2], com[3])							
					else:
	    					print data[:-1]
	    		else:
	    			fds.remove(fd)
				fd.close()
		#Reading data from keyboard:
		if fd == sys.stdin:
			message = sys.stdin.readline()
			if message == '\n':
				continue
			x = message.split()
			# Disconnects from server
			if x[0] == "/quit" or x[0] == "/quit\n":
				sockfd.send(message)
				running = False
			# Start file transfer (sending)
			elif x[0] == '/send':
				if len(x) != 3:
					print '::Wrong usage of /send. Type /help for more info.'
					continue
				if x[2] == user or x[2] == user + '\n':
					print '::You can\'t send a file to yourself.'
					continue
				try:
					f = open(x[1], 'r')
					f.close()
				except IOError:
					print '::Failed to send file. File not found.'
					continue
				sockfd.send(message)
				answer = sockfd.recv(MAX_SIZE)
				print answer
				y = answer.split()
				if len(y) != 3:
					print answer
					continue		
				ip = y[2]
				path = x[1]
				size = os.path.getsize(path)
				ftp_client_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				ftp_client_fd.connect ((ip, FTP_PORT))
				ftp_client_fd.send(path)
				ftp_client_fd.send(str(size))
				thread.start_new_thread(ftp_send,(ftp_client_fd, size, path))
			# See your shared files
			elif x[0] == '/shared_view_me':
				try:
					sh = open('shared.db', 'r')
					sem = 0
					for line in sh:
						sem = 1
						line = line.strip()
						print line
					sh.close()
					if sem == 0:
						print '::You have no shared files.'
				except IOError:
					print '::You have no shared files.'
			# Add a new file to shared list	
			elif x[0] == '/shared_add':
				if len(x) == 1:
					print '::Incomplete command. Usage: /shared_add <filename.extension>.'
				else:
					try:
						sh = open('shared.db', 'a')
						item = x[1].lower() + '\n'
						sh.write(item)
						sh.close()
						print '::File added to shared list'
					except IOError:
						print '::The file \'shared.db\' does not exist. It will be created now.'
						sh = open('shared.db', 'w')
						item = x[1] + '\n'
						sh.write(item)
						sh.close()
			# Delete a file from the shared list
			elif x[0] == '/shared_del':
				try:
					sh = open('shared.db', 'r')
					data_list = sh.readlines()			
					sh.close()
					item = x[1]+'\n'  
					data_list.remove(item)
					sh = open ('shared.db', 'w')
					sh.writelines(data_list)
					sh.close()
					print '::File succesfully deleted.'
				except IOError:
					print '::The file \'shared.db\' does not exist. You have no shared files to delete.'
			# Sends message to server chat
			else:
				sockfd.send(message)
		if fd == ftp_fd:
			# Start file transfer (receiving)
			client_fd, client_addr = ftp_fd.accept()
			path = client_fd.recv(MAX_SIZE)
			size = client_fd.recv(MAX_SIZE)
			print 'Receiving file: ' + path
			filename = raw_input('Save as: ')
			print filename
			#while filename !='\n':
			#	filename = raw_input()
			thread.start_new_thread(ftp_recv,(client_fd, size, filename))
	
# Close socket.
sockfd.close()
