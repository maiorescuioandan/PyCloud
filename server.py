#!/usr/bin/python

# IP Workshop 2012
# Dragos Barosan 		(bdl_rom@yahoo.com)
# Ioan-Dan Maiorescu		(ion.maiorescu@gmail.com)
# Rudolf Winckenbauer		(rudi_winckelbauer@yahoo.com)

import select, socket, sys, thread
import threading, subprocess

HOST = '' # all available interfaces
PORT = int(sys.argv[1])
MAX_CLIENTS = 5
MAX_SIZE = 4096
lock = threading.Lock()

#Class definition: ->this class will cointain user accounts and their state.
class Client:
	def __init__(self, _nick, _pw, _admin):
		self.addr = 0
		self.nick = _nick.capitalize()
		self.pw = _pw
		self.connected = 0
		self.fd = None
		self.admin = _admin

#Reading accounts database:
with open('accounts.db') as f:
	k=0
	accounts = []
	for line in f:
		x = line.split()
		if len(x) == 3:
			accounts.append(Client(x[0], x[1], x[2]))
			k = k+1
		else:
			print "Warning: accounts.db might be corrupted!"
			print line + "==" * 8

def find_socket(fileno):
	for x in accounts:
		if x.connected == 1:
			if x.fd.fileno() == fileno:
				return x


###LOG IN THREAD
def run(client_fd, client_addr):
	global accounts
	global lock
	print 'An user is attempting to log in...'
	ack = client_fd.recv(MAX_SIZE)
	if ack == 'YES ACCOUNT':
		user = client_fd.recv(MAX_SIZE)	
		pw = client_fd.recv(MAX_SIZE)
		# Check if data is correct
		sem = 0
		for x in accounts:
			if x.nick == user.capitalize():
				sem = 1
				if x.pw == pw:
					if x.connected == 1:
						client_fd.send("::User already connected.\n")
						print 'User failed to connect (already logged in).'
						client_fd.close()
					else:							
						client_fd.send("::Connection to server established.\n")
						x.addr=client_addr
						x.connected=1
						x.fd=client_fd
						lock.acquire()
						epoll.register(x.fd.fileno(), select.EPOLLIN)
						lock.release()
						s = '::' + x.nick + ' is now online. '
						print s[2:]
						for i in accounts:
							if i.connected == 1 and i.nick != x.nick:
								i.fd.send(s)
				else:
					client_fd.send("::Connection failed. Incorrect username or password.\nType '/quit' then reconnect.")
					print 'User failed to connect'
					client_fd.close()
			else:
				continue
		if sem == 0:
			client_fd.send("::Connection failed. Incorrect username or password.\nType '/quit' then reconnect.")
			print 'User failed to connect'
			client_fd.close()			
		return sem
	elif ack == 'NO ACCOUNT':
		print 'User doesn\'t have an account.'
		ack = client_fd.recv(MAX_SIZE)
		if ack == 'CREATE':
			running = True
			while running:
				sem = 0
				while sem == 0:
					user = client_fd.recv(MAX_SIZE)
					for i in accounts:
						if user.capitalize() == i.nick:
							sem = 1
							client_fd.send('DUPLICATE')
						else:
							pass
					if sem == 0:
						sem = 1
						client_fd.send('AVAILABLE')
						pw = client_fd.recv(MAX_SIZE) 
						accounts.append(Client(user, pw, '0'))
						for i in accounts:
							if i.nick == user.capitalize():
								print i.nick
								i.connected = 1
								i.fd = client_fd
								i.addr = client_addr
								with open('accounts.db', 'a') as f:
									f.write(i.nick + ' ' + i.pw + ' 0\n')
								lock.acquire()
								epoll.register(i.fd.fileno(), select.EPOLLIN)
								lock.release()
								print 'A new user has been created:', i.nick
								i.fd.send('::User succesfully created!\n::You have now joined the chat! ')
					
						running = False					

		
		
#######################################
def command(requester, data):
	x=data.split()
# QUIT
	if x[0] == '/quit' or x[0]=='/quit\n':
		s = '::' + requester.nick + ' disconnected from server. '
		print s[2:]
		requester.connected=0
		epoll.unregister(requester.fd.fileno())
		requester.fd.close()
		for i in accounts:
			if i.connected == 1:
				i.fd.send(s)
# WHO
	elif (x[0] == '/who' or x[0] == '/who\n') and len(x) == 1:
		s = "::Online users: "	
		for i in accounts:
			if i.connected == 1:
				s = s + i.nick + ' '
		s = s + '. '
		if requester.nick == 'Admin':
			print s[2:]
		else:
			requester.fd.send(s)
# KICK
	elif x[0] == '/kick':
		if len(x) == 1:
			requester.fd.send('::Wrong usage of /kick. ')
			return
		if requester.admin == '0':
			print requester.nick, 'attempted an admin command.'
			requester.fd.send('::You do not have administrator rights. ')
		else:
			sem = 0
			for i in accounts:
				if i.nick == x[1].capitalize():
					#deconecteaza'l
					sem = 1
					s = '::' + i.nick + ' was kicked by ' + requester.nick + '. '
					#print s[2:]
					i.connected=0
					t = '::You have been kicked by ' + requester.nick + '. '
					if len(x) >= 3:
						s = s + 'Reason: '
						t = t + 'Reason: '
						for j in range(2,len(x)):
							s = s + x[j] + ' '
							t = t + x[j] + ' '
					i.fd.send(t)
					epoll.unregister(i.fd.fileno())
					i.fd.close()
					print s[2:]						
					for i in accounts:
						if i.connected == 1:
							i.fd.send(s)
			if sem == 0:
				requester.fd.send('::User is not online. ')
# PING
	elif x[0] == '/ping' or x[0] == '/ping\n':	
		if len(x) != 2:
			requester.fd.send('::Wrong usage of /ping. ')	
			return	
		for i in accounts:
			if i.nick == x[1].capitalize():
				if i.connected == 1:
					ip, port = i.addr
					host = ip
					ping = subprocess.Popen(["ping", "-c", "4", host],stdout = subprocess.PIPE,stderr = subprocess.PIPE)
					out, error = ping.communicate()
					requester.fd.send(out)				
				else:
					s = "User not online!"
					requester.fd.send(s)
# SEND
	elif x[0] == '/send' or x[0] == '/send\n':
		sem = 0
		print x, x[0], x[1], x[2]
		if len(x) == 3:
			for i in accounts:
				if i.nick == x[2].capitalize() and i.connected == 1:
					sem = 1
					s = ':: ' + i.nick + ' ' + i.addr[0] + ' '
					requester.fd.send(s)
			if sem == 0:
				requester.fd.send('::User is not currently online. ')
		else:
			requester.fd.send('::Wrong usage. Use /send TARGET_FILE TARGET_USER ')
# HELP
	elif x[0] == '/help' or x[0] == '/help\n':
		s = '==' * 8 + '\nAvailable commands:\n'
		s = s + '/quit = disconnect from server\n'
		s = s + '/who = list online users\n'
		s = s + '/ping <user>\n'
		s = s + '/w <user> = send a private message to a specific user\n'
		s = s + '/shared_view_me = see your shared files\n'
		s = s + '/shared_view <username> = see the shared files of a specific user\n'
		s = s + '/shared_add <filename> = add a file to your shared list\n'
		s = s + '/shared_del <filename> = removes a file from your shared list \n'
		s = s + '/search <filename> = search a file in the shared lists of the connected users\n'
		s = s + '/request <filename> <username> = downloads a file from the shared list of a specific user\n'
#		print '#', requester.admin
		if requester.admin == '1':
			s = s + 'Available admin commands:\n'
			s = s + '/kick <user>\n'
		requester.fd.send(s)
# WHISPER
	elif x[0]=='/w' or x[0]=='w\n':
		s=''
		for i in accounts:
			if i.nick == x[1].capitalize():			
				if i.connected==1:
					for j in range(2,len(x)):
						s = s+' ' + x[j]
					msg = requester.nick + ' whispers discretely: ' + s + ' '
					i.fd.send(msg)
				else :
					s = "::User not online! "
					requester.fd.send(s)
# VIEW
	elif (x[0] == '/shared_view' or x[0] == '/shared_view\n') and len(x) == 2:
		nume=requester.nick
		for i in accounts:
			if i.nick == x[1].capitalize():
				if i.connected == 1:
					s='/view' + ' ' + nume
					i.fd.send(s)
				else:
					requester.fd.send('::User not online. ')

	elif x[0]=='/client_list' or x[0] == '/client_list\n':
		nume = x[1]
		for i in accounts:
			if i.nick==nume:
				s=''
				for j in range(2,len(x)):
					s=s + x[j] + ' '
				i.fd.send(s)	
# SEARCH:
	elif x[0] == '/search' or x[0] == '/search\n':
		nume = requester.nick
		for i in accounts:
			if i.nick != requester.nick.capitalize() and i.connected == 1:
				s = '/search ' + x[1] + ' ' + nume
				i.fd.send(s)

	elif x[0] == '/here' or x[0] == '/here\n':
		om = requester.nick
		name = ''
		name = name + x[1]
		for i in accounts:
			if i.nick == name.capitalize():
				i.fd.send(om + ' ')
# REQUEST:
	elif x[0] == '/request' and len(x) == 3:
		for i in accounts:
			if i.nick == x[2].capitalize():
				if i.connected == 1:
					print requester.nick
					i.fd.send(x[0] + ' ' + x[1] + ' ' + x[2] + ' ' + requester.nick)
				else:
					requester.fd.send('::User not online! ')
# SENDERROR
	elif x[0] == '/senderror':
		for i in accounts:
			if i.nick == x[1].capitalize() and i.connected == 1:
				i.fd.send('::Error: file is not existent. ') 
			else:
				pass
# WRONG COMMAND:
	else:
		if requester.nick == 'Admin':
			print 'Command not recognized. '
		else: 
			requester.fd.send('::Command not recognized / Wrong usage. ')

# Create socket.
sockfd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sockfd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# Bind socket.
sockfd.bind((HOST, PORT))

# Listening state.
sockfd.listen(MAX_CLIENTS)
sockfd.setblocking(0)

epoll = select.epoll()
epoll.register(sockfd.fileno(), select.EPOLLIN)
epoll.register(sys.stdin.fileno(), select.EPOLLIN)

running = True
try:
	while running:
		events = epoll.poll(1)
		for fileno, event in events:
			if fileno == sockfd.fileno():
				client_fd, client_addr = sockfd.accept()
				thread.start_new_thread(run,(client_fd, client_addr))
			elif fileno == sys.stdin.fileno():
				# Keyboard message
				message = sys.stdin.readline()
				msg = message.split()
				if message == "/quit" or message == "/quit\n":
					running = False
				elif message[0] == "/":
					command(accounts[0],message)
				else:
					for i in accounts:
						if i.connected == 1:
							i.fd.send('Admin:' + message)
			elif event & select.EPOLLIN:
				x = find_socket(fileno) 
				data = x.fd.recv(MAX_SIZE)
				if not data:
					x.fd.close()
					epoll.unregister(fileno)
					x.connected=0
					s = x.nick + ' disconnected brutally. '
					print s
					for i in accounts:
						if i.connected == 1:
							i.fd.send(s)
				else:
					msg = x.nick + ':' + data
					print msg[:-1]
					if data[0] == '/':
						command(x, data)
					else:
						for i in accounts:
							if i.connected == 1:
								i.fd.send(msg)
			elif event & select.EPOLLHUP:
				epoll.unregister(fileno)
				x=find_socket(fileno)
				x.fd.close()
				x.connected=0
				s = x.nick + ' disconnected brutally. '
				print s
				for i in accounts:
					if i.connected == 1:
						i.fd.send(s)
finally:
	epoll.unregister(sockfd.fileno())
	epoll.close()
	sockfd.close()
