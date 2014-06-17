# -*- coding: utf-8 -*-

from camera import Camera
from flask import Flask, render_template, session
from flask.ext.socketio import SocketIO, emit
import threading, Queue
import time, sys, os, signal
from collections import defaultdict
import RPIO as gpio

from user import UserDataParser

import config
import pygame




#create the screen

class Window(object):
	
	
	pygame.init() 


	global count
	global last_count_time

	#pygame config
	BLACK = (0, 0, 0)
	WHITE = (255, 255, 255)
	RED = (255, 0, 0)
	GREEN = (0, 255, 0)
	BLUE = (0, 0, 255)

	basicFont = pygame.font.SysFont(None, 228)

	count = 4
	last_count_time = 0

	infoObject = pygame.display.Info()
	
	def init(self):
		print ("------------------opening window")
		window = pygame.display.set_mode((640, 480))
		pygame.display.set_caption('Hello world!')
	'''
	def loop():

		window.fill(WHITE)
		if count == 0:
			pass
		elif time.time() - last_count_time >= 1:
			count = count - 1
			last_count_time = time.time()
		#draw text
		text = basicFont.render(str(count), True, BLACK)
		textRect = text.get_rect()
		textRect.left = (window.get_rect().centerx - 200)
		textRect.centery = window.get_rect().centery
		
		window.blit(text, textRect)

		#draw it to the screen
		pygame.display.flip() 

	def my_quit():
		pygame.quit
		sys.exit(0)

	#input handling (somewhat boilerplate code):
	while True:

		loop()
		
		for event in pygame.event.get(): 
				
			if (event.type is pygame.KEYDOWN and event.key == pygame.K_ESCAPE) or event.type == pygame.QUIT :
				my_quit()
				
			if (event.type is pygame.KEYDOWN and event.key == pygame.K_f):
				if window.get_flags() & pygame.FULLSCREEN:
					pygame.display.set_mode((640, 480))
					#loop()
				else:
					pygame.display.set_mode((infoObject.current_w, infoObject.current_h), pygame.FULLSCREEN) 
					#loop()
	'''
	
#import RPIO as gpio
#gpio.setmode(gpio.BCM)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.debug=True
socketio = SocketIO(app)


# Instance of class that downloads the list of users from TMW's intranet.
# It runs continuously on a thread, updating the file at the frequency
# specified (secs): ('url','localfile',frequency)
model = UserDataParser(config.user_file_url,config.local_cache_file,config.cache_refresh_rate)
camera = Camera()
window = Window()

users = []
photos = []
queue = Queue.Queue()

dims = '\'282,20,460,558\''

reset_pin = 27

window.init()




def restart_program(gpio_id, value):
	print "-----> Restart"
	try:
		gpio.cleanup()
		python = sys.executable
		os.execl(python, python, * sys.argv)
	except Exception as e:
		print e
'''		
gpio.wait_for_interrupts(threaded=True)

gpio.add_interrupt_callback(
reset_pin, \
restart_program, \
edge='both', \
pull_up_down=gpio.PUD_UP, \
threaded_callback=False, \
debounce_timeout_ms=20)
'''

@app.route('/')
@app.route('/index')
def index():
    if len(users) > 0: # if we already have an active user
        print ('New client at index, app busy')
        return render_template("busy.html")
    else:
        print ('Client at index')
        return render_template("index.html")

@socketio.on('user', namespace='/photo')
def select_user(message):
	user_input = message['data']
	user = model.get_user(user_input)
	print user
	if not user:
		success = 0
		guid = 0
		name = user_input
	else:
		success = 1
		guid = user.guid
		name = user.first_name
		users.insert(0,user)
		check_user_timeout(user)

	emit('event', {'response': success, 'data': guid, 'name': name})
	
@socketio.on('restart', namespace='/photo')
def restart(msg):
	end_user('end')

@socketio.on('take_pic', namespace='/photo')
def take_pic(msg):
	if len(users) > 0:
		#created a list to hold the user object globally
		user = users[0]
		filename = user.first_name + "_" + user.sir_name + ".jpg"
		photo = camera.take_picture(filename,user=user)
		photos.insert(0,photo)
		print "-----> web_path: " + photo.web_path
		emit('image', {'data': photo.web_path })
	else:
		pass
		

@socketio.on('send_pic', namespace='/photo')
def send_pic(message):
	if len(users) > 0:
		user = users[0]
		photo = photos[0]
		photo.send_picture(user.guid,photo.full_path)
		end_user('end')
		#end user session
	else:
		pass

@socketio.on('connect', namespace='/photo')
def test_connect():
    print ('Client connected.')
    emit('event', {'data': 'Connected'})

@socketio.on('disconnect', namespace='/photo')
def test_disconnect():
    print('Client disconnected.')


def threaded(f, daemon=False):
    import Queue

    def wrapped_f(q, *args, **kwargs):
        #this function calls the decorated function and puts the 
        #result in a queue
        ret = f(*args, **kwargs)
        q.put(ret)

    def wrap(*args, **kwargs):
        #this is the function returned from the decorator. It fires off
        #wrapped_f in a new thread and returns the thread object with
        #the result queue attached

        q = Queue.Queue()

        t = threading.Thread(target=wrapped_f, args=(q,)+args, kwargs=kwargs)
        t.daemon = daemon
        t.start()
        t.result_queue = q        
        return t

    return wrap
    
@threaded
def check_user_timeout(user):
	timeout = int(config.session_timeout)
	if len(users) > 0:
		if timeout_test(timeout) is True:
			end_user('timeout')
		else:
			time.sleep(30)
			check_user_timeout(timeout)
	
def timeout_test(timeout):
	user = users[0]
	curr_time = int(time.clock() * 1000)
	if curr_time - timeout > user.time:
		return True
	else:
		return False
	
def end_user(reason):
    del users[0]
    if len(photos) > 0:
		del photos[0]
    if reason == 'timeout':
		print "-----> User timed out"
    elif reason == 'end':
        pass


# This function creates a clean exit on ctrl+c
def signal_handler(signal, frame):
	gpio.cleanup()
	print '-----> Quit'
	sys.exit(0)
	

signal.signal(signal.SIGINT, signal_handler)



if __name__ == '__main__':
    socketio.run(app,'0.0.0.0',80)
