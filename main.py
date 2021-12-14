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
import socket

import config




# Detect if running on raspberry pi
IS_PI = platform.machine() == "armv7l"
RASPIRAW_PATH = os.path.abspath(os.path.join(config.DEP_PATH, "fork-raspiraw/raspiraw"))
DCRAW_PATH = os.path.abspath(os.path.join(config.DEP_PATH, "dcraw/dcraw"))

if IS_PI:
	import RPi.GPIO as GPIO
else:
	print("Not running on raspberry pi")
	print("Some features might not work")

def raspiraw_command(dist, use_ram = True, device=10, fps=1007, gain=100, t=1000, height=75, debug=True):
	dist = os.path.abspath(dist)
	command = [RASPIRAW_PATH]
	command += ["-md", "7"] # 640x480 mode
	command += ["-g", str(gain)]
	command += ["-t", str(t)]
	command += ["-ts", os.path.join(dist, "tstamps.csv")]
	command += ["-hd0", os.path.join(dist, "hd0.32k")]
	command += ["-h", str(height)]
	command += ["-sr 1"] # Save every frame
	command += ["--voinc 01"]
	command += ["--fps", str(fps)]
	command += ["-y", str(device)]
	command += ["-o", os.path.join(config.RAMDISK_PATH if use_ram else dist, config.RAW_PATTERN)]
	if not debug:
		command += ["2>/dev/null >/dev/null"]
	
	return " ".join(command)
	
def clear_ram_command():
	return "rm -f /dev/shm/out.*.raw"
	
class WebSocketServer(tornado.websocket.WebSocketHandler):
	clients = set()

	def open(self):
		WebSocketServer.clients.add(self)

	def on_close(self):
		WebSocketServer.clients.remove(self)

	@classmethod
	def send_message(cls, message: str):
		#cls.prepare_cam()
		if len(cls.clients) > 0:
			print(f"Sending data to {len(cls.clients)} client{'' if len(cls.clients)==1 else 's'}.")
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

	def send_status(self, msg):
		self.send_message(json.dumps({
			"type": "status",
			"message": msg
		}))

	@gen.coroutine
	def capture_video(self, capture_ms):
		if not IS_PI:
			self.send_status("Server not on raspberry pi. Simulating capture delay.")
			save_refresh = config.REFRESH_DELAY
			config.REFRESH_DELAY = -1
			yield gen.sleep(capture_ms / 1000)
			self.send_status("Capture finished.")
			config.REFRESH_DELAY = save_refresh
			return


		save_path = config.SAVE_PATH + "/" + datetime.now().strftime("%Y-%m-%dT%T")
		save_path = os.path.abspath(save_path)
		os.makedirs(save_path)
		print(f"Saving recording to {save_path}")
		print(raspiraw_command(save_path, t=capture_ms))
		save_refresh = config.REFRESH_DELAY
		config.REFRESH_DELAY = -1
		#proc = Subprocess(["./scripts/capture_to_ram.sh", save_path, raspiraw_command(save_path, t=capture_ms)], stdout=Subprocess.STREAM,
		#								  stderr=Subprocess.STREAM)
		
		proc = Subprocess(["./scripts/raspiraw_trigger.sh", str(capture_ms), save_path], stdout=Subprocess.STREAM,
										  stderr=Subprocess.STREAM)
		
		
		yield proc.wait_for_exit(raise_error=False)
		out, err = yield [proc.stdout.read_until_close(),
				   proc.stderr.read_until_close()]
		print(out.decode())
		print("Capture finished")
		self.send_status("Capture finished. Transferring raw files from RAM...")
		
		proc = Subprocess(["./scripts/ram_to_disk.sh", save_path], stdout=Subprocess.STREAM,
										  stderr=Subprocess.STREAM)
		
		yield proc.wait_for_exit(raise_error=False)
		out, err = yield [proc.stdout.read_until_close(),
				   proc.stderr.read_until_close()]
		print(out.decode())
		print("Transferred")
		self.send_status("Raw files saved. Stats: \n" + out.decode())
		self.send_status("Decoding raw images...")
	
		proc = Subprocess(["./scripts/convert_to_jpg.sh", save_path], stdout=Subprocess.STREAM,
										  stderr=Subprocess.STREAM)
		
		yield proc.wait_for_exit(raise_error=False)
		out, err = yield [proc.stdout.read_until_close(),
				   proc.stderr.read_until_close()]
		print(out.decode())
		print("Converted")
		self.send_status("Raw images decoded. Updating preview")
		
		config.REFRESH_DELAY = save_refresh
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
		if config.REFRESH_DELAY/1000 + self.last_tick < now and config.REFRESH_DELAY > 1:
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
				send_callback(json.dumps({
					"type": "image",
					"image": msg
				}))

def main():
	app = tornado.web.Application(
		[(r"/websocket/", WebSocketServer),
		 (r"/", MainHandler)],
		websocket_ping_interval=10,
		websocket_ping_timeout=30,
		debug=True,
	)
	app.listen(config.PORT)
	

	# Print control panel address
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	print("="*70+"\n")
	print("\tServer started!")
	try:
		s.connect(('10.255.255.255', 1))
		IP = s.getsockname()[0]
		print(f"\tControl panel: http://{IP}:{config.PORT}")
	except Exception:
		print(f"\tControl panel: http://localhost:{config.PORT}")
	finally:
		s.close()
	print("\n"+"="*70)
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
