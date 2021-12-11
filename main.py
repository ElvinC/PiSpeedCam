import random
import json
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.process import Subprocess
from tornado import gen
from subprocess import PIPE
import base64
import platform
import os
import time
from datetime import datetime

import config

# Detect if running on raspberry pi
IS_PI = platform.machine() == "armv7l"

if IS_PI:
	import RPi.GPIO as GPIO
else:
	print("Not running on raspberry pi")
	print("Some features might not work")

class WebSocketServer(tornado.websocket.WebSocketHandler):
	clients = set()

	def open(self):
		WebSocketServer.clients.add(self)

	def on_close(self):
		WebSocketServer.clients.remove(self)

	@classmethod
	def send_message(cls, message: str):
		#cls.prepare_cam()
		print(f"Sending data to {len(cls.clients)} client(s).")
		for client in cls.clients:
			client.write_message(message)

	def on_message(self, message):
		print("Received: " + message)
		data = json.loads(message)
		if data.get("command") == "CONFIG":
			config.SKIP_FRAMES = data.get("skip_frames")
			config.REFRESH_DELAY = data.get("frame_delay")
			
		elif data.get("command") == "CAPTURE":
			self.capture_video(data.get("capture_ms"))
			print("Capturing...")
			
		

	@gen.coroutine
	def capture_video(self, capture_ms):
		save_path = config.SAVE_PATH + "/" + datetime.now().strftime("%Y-%m-%dT%T")
		save_path = os.path.abspath(save_path)
		os.makedirs(save_path)
		print(f"Saving recording to {save_path}")
		
		proc = Subprocess(["./scripts/raspiraw_trigger.sh", str(capture_ms), save_path], stdout=Subprocess.STREAM,
										  stderr=Subprocess.STREAM)
		
		yield proc.wait_for_exit(raise_error=False)
		out, err = yield [proc.stdout.read_until_close(),
				   proc.stderr.read_until_close()]
		print(out.decode())
		print("Capture and processing finished")
		config.PLAYBACK_FOLDER = save_path

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("client_static/client.html")

class ImageSender:
	def __init__(self):
		self.current_id = 0
		self.num_images = 2
		self.last_tick = time.time()

	def send_image_tick(self, send_callback):
		now = time.time()
		if config.REFRESH_DELAY/1000 + self.last_tick < now:
			self.last_tick = now
			filepattern = "out.{:04d}.ppm.png"
			thisfile = os.path.join(config.PLAYBACK_FOLDER, filepattern.format(self.current_id))
			
			
			if not os.path.isfile(thisfile):
				self.current_id = 1
				thisfile = os.path.join(config.PLAYBACK_FOLDER, filepattern.format(self.current_id))
				
			with open(thisfile, "rb") as f:
				#self.current_id = (self.current_id + 1 ) % self.num_images
				self.current_id += config.SKIP_FRAMES
				msg = "data:image/png;base64," + base64.b64encode(f.read()).decode()
				send_callback(msg)

def main():
	app = tornado.web.Application(
		[(r"/websocket/", WebSocketServer),
		 (r"/", MainHandler)],
		websocket_ping_interval=10,
		websocket_ping_timeout=30,
		debug=True,
	)
	app.listen(config.PORT)

	io_loop = tornado.ioloop.IOLoop.current()

	# Send image
	sender = ImageSender()
	periodic_callback = tornado.ioloop.PeriodicCallback(
		lambda: sender.send_image_tick(WebSocketServer.send_message), 1
	)
	periodic_callback.start()

	# Start the event loop.
	io_loop.start()


if __name__ == "__main__":
	main()
