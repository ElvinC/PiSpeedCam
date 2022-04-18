import time
import sys

def debug():
	for i in range(100):
		print(i)
		sys.stdout.flush()
		time.sleep(1)
import random
import json
import tornado.ioloop
import tornado.web
import tornado.websocket
from tornado.process import Subprocess
from tornado import gen
from subprocess import PIPE
import subprocess as SP
import base64
import platform
import os
from datetime import datetime
import socket

abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

import config

# Detect if running on raspberry pi
IS_PI = platform.machine() == "armv7l"
RASPIRAW_PATH = os.path.abspath(os.path.join(config.DEP_PATH, "fork-raspiraw/raspiraw"))
DCRAW_PATH = os.path.abspath(os.path.join(config.DEP_PATH, "dcraw/dcraw"))
CAM_I2C_PATH = os.path.abspath(os.path.join(config.DEP_PATH, "fork-raspiraw/camera_i2c"))
print(CAM_I2C_PATH)
sys.stdout.flush()
trigger_pin = 14
trigger_capture_length = config.DEFAULT_CAPTURE_MS

if IS_PI:
	import RPi.GPIO as GPIO
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(trigger_pin, GPIO.OUT)
	for i in range(10):
		GPIO.output(trigger_pin, True)
		time.sleep(0.1)
		GPIO.output(trigger_pin, False)
		time.sleep(0.1)
	GPIO.setup(trigger_pin, GPIO.IN)
else:
	print("Not running on raspberry pi")
	print("Some features might not work")

config.all_recordings = {rec: {"name": rec, "frames": 0} for rec in sorted(os.listdir(config.SAVE_PATH)) if rec[0].isnumeric()}
for recording in config.all_recordings:
	tstampfile = os.path.join(config.SAVE_PATH, config.all_recordings.get(recording)["name"], "tstamps.csv")
	try:
		with open(tstampfile) as f:
			config.all_recordings.get(recording)["frames"] = sum(1 for line in f)
	except FileNotFoundError:
		pass
#for c in config.all_recordings.keys():
#	print(c)

def cam_i2c_command():
	command = [CAM_I2C_PATH]
	res = SP.check_output(command)
	print(res.decode("utf8"))

cam_i2c_command()

def gain_from_file():
	gain = 150
	with open("gain.txt", "r") as f:
		try:
			newgain = int(f.readlines()[0])
			print(newgain)
			gain = newgain
		except:
			pass
	return max(min(gain, 240), 1)

def gain_to_file(gain=150):
	with open("gain.txt", "w") as f:
		f.write(str(gain))

default_gain = gain_from_file()

def raspiraw_command(dist, use_ram = True, sr=1, device=10, fps=1007, gain=100, eus=600, t=1000, height=75, outfile=False, debug=False):
	dist = os.path.abspath(dist)
	command = [RASPIRAW_PATH]
	command += ["-md", "7"] # 640x480 mode
	command += ["-g", str(gain)]
	#command += ["-eus", str(eus)]
	command += ["-t", str(t)]
	command += ["-ts", os.path.join(dist, "tstamps.csv")]
	command += ["-hd0", os.path.join(dist, "hd0.32k")]
	command += ["-h", str(height)]
	command += ["-sr", str(sr)] # Save every frame
	command += ["--voinc", "01"]
	command += ["--fps", str(fps)]
	command += ["-y", str(device)]
	if not outfile:
		command += ["-o", os.path.join(config.RAMDISK_PATH if use_ram else dist, config.RAW_PATTERN)]
	else:
		command += ["-o", outfile]
	
	if not debug:
		command += ["2>/dev/null", ">/dev/null"]
	
	return " ".join(command)
	
class WebSocketServer(tornado.websocket.WebSocketHandler):
	clients = set()
	currently_recording = False
	capture_ms = 5000
	gain = default_gain
	exposure = 700

	@classmethod
	def get_recording_json(self):
		return json.dumps({
			"type": "recordings",
			"recordings": list(config.all_recordings.values()),
			"homepath": os.path.join(os.path.abspath(os.getcwd()), config.SAVE_PATH, "")
		})

	def open(self):
		WebSocketServer.clients.add(self)
		self.write_message(self.get_recording_json())

	def on_close(self):
		WebSocketServer.clients.remove(self)

	@classmethod
	def send_message(cls, message: str):
		#cls.prepare_cam()
		if len(cls.clients) > 0:
			print(f"Sending data to {len(cls.clients)} client{'' if len(cls.clients)==1 else 's'}.")
			for client in cls.clients:
				client.write_message(message)
	@classmethod
	@gen.coroutine
	def send_live_image(self):
		if self.currently_recording:
			return

		out, err = yield self.execute_bash(self, ["rm", "-f", "/dev/shm/out.*.raw"])
		print("0")
		self.currently_recording = True
		out, err = yield self.execute_bash(self, raspiraw_command("/dev/shm/", t=30, sr=4, outfile= "/dev/shm/preview%04d.raw", debug=False), shell=True)
		self.currently_recording = False
		print("1")
		out, err = yield self.execute_bash(self, ["cat /dev/shm/hd0.32k /dev/shm/preview0001.raw > /dev/shm/preview.ppm"], shell=True)
		print("2")	
		out, err = yield self.execute_bash(self, [DCRAW_PATH + " -c -W /dev/shm/preview.ppm | pnmtojpeg -quality=90 > /dev/shm/preview.jpg"], shell=True)
		
		with open("/dev/shm/preview.jpg", "rb") as f:
			msg = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
			
			self.send_message(json.dumps({
				"type": "image",
				"image": msg
			}))

	def on_message(self, message):
		print("Received: " + message)
		data = json.loads(message)
		if data.get("command") == "CONFIG":
			config.SKIP_FRAMES = data.get("skip_frames")
			config.REFRESH_DELAY = data.get("frame_delay")
			
		elif data.get("command") == "CAPTURE":
			self.capture_video(data.get("capture_ms"), data.get("gain"), data.get("exposure"))
			print("Capturing...")
		elif data.get("command") == "PROCESS":
			self.process_video(os.path.join(config.SAVE_PATH ,data.get("recording")))
			print("Processing")
		elif data.get("command") == "PLAY":
			play_folder = os.path.join(config.SAVE_PATH, data.get("recording"))
			if os.path.isdir(play_folder):
				config.PLAYBACK_FOLDER = play_folder
		else:
			print("Unknown command from client:")
			print(data)

	@classmethod
	@gen.coroutine
	def send_status(self, msg):
		self.send_message(json.dumps({
			"type": "status",
			"message": msg
		}))

	@classmethod
	@gen.coroutine
	def execute_bash(self, cmd, shell=False):
		proc = Subprocess(cmd, stdout=Subprocess.STREAM, stderr=Subprocess.STREAM, shell=shell)
		
		yield proc.wait_for_exit(raise_error=False)
		out, err = yield [proc.stdout.read_until_close(),
				   proc.stderr.read_until_close()]
		return out, err

	@classmethod
	@gen.coroutine
	def capture_default(self):
		self.capture_video(trigger_capture_length, self.gain, self.exposure)

	@classmethod
	@gen.coroutine
	def capture_video(self, capture_ms, gain, exposure):
		self.capture_ms = capture_ms
		self.gain = gain
		self.exposure = exposure
		for i in range(1000):
			yield gen.sleep(0.05)
			if not self.currently_recording:
				break
		if self.currently_recording:
			print("Camera lockup, try rebooting the pi")
			return
			
		if not IS_PI:
			self.send_status("Server not on raspberry pi. Simulating capture delay.")
			save_refresh = config.REFRESH_DELAY
			config.REFRESH_DELAY = -1
			yield gen.sleep(capture_ms / 1000)
			self.send_status("Capture finished.")
			config.REFRESH_DELAY = save_refresh
			return

		self.currently_recording = True
		foldername = datetime.now().strftime("%Y-%m-%dT%H.%M.%S")
		save_path = config.SAVE_PATH + "/" + foldername
		save_path = os.path.abspath(save_path)
		os.makedirs(save_path)
		print(f"Saving recording to {save_path}")
		save_refresh = config.REFRESH_DELAY
		config.REFRESH_DELAY = -1
		
		out, err = yield self.execute_bash(["rm -f /dev/shm/out.*.raw"], shell=True)
		raspicommand = raspiraw_command(save_path, t=capture_ms, gain=gain, eus=exposure, debug=False)
		print(raspicommand)
		out, err = yield self.execute_bash(raspicommand, shell=True)
		
		print(out.decode())
		print("Capture finished. Transferring...")
		self.send_status("Capture finished. Transferring raw files from RAM...")
		
		out, err = yield self.execute_bash(["./scripts/ram_to_disk.sh", save_path])
		print(out.decode())
		print("Transferred. Starting decode")
		self.send_status("Raw files saved. Stats: \n" + out.decode())
		self.currently_recording = False
		config.LAST_PATH = save_path
		
		out, err = yield self.execute_bash([DCRAW_PATH + f" -c -r 1.2 1 1.3 1 -k 63 -W {save_path + '/out.0001.raw'} | pnmtopng > {save_path + '/out.0001.ppm.png'}"], shell=True)

		tstampfile = os.path.join(save_path, "tstamps.csv")
		number_frames = 0
		try:
			with open(tstampfile) as f:
				number_frames = sum(1 for line in f)
		except FileNotFoundError:
			pass

		config.all_recordings[foldername] = {"name": foldername, "frames": number_frames}
		self.send_message(self.get_recording_json())
		gain_to_file(self.gain)
		config.REFRESH_DELAY = save_refresh
		config.PLAYBACK_FOLDER = save_path
		
	@gen.coroutine
	def process_frames_worker(self, save_path, start = 1, stop= False, worker_id=0, total_workers=4):
		idx = start
		infilepattern = "out.{:04d}.raw"
		outfilepattern = "out.{:04d}.ppm.png"
		while not stop or idx <= stop: 
			thisfile = os.path.join(save_path, infilepattern.format(idx))
			
			if idx % total_workers == worker_id:				
				if not os.path.isfile(thisfile):
					break
					
				# Convert file
				outfile = os.path.join(save_path, outfilepattern.format(idx))
				print(idx)
				out, err = yield self.execute_bash([DCRAW_PATH + f" -c -r 1.2 1 1.3 1 -k 63 -W {thisfile} | pnmtopng > {outfile}"], shell=True)
				
			if idx % 100 == 0 and worker_id==0:
				self.send_status(f"{idx} frames processed")
			idx += 1

	@gen.coroutine
	def process_video(self, save_path=None):
		if not save_path:
			save_path = config.LAST_PATH
		config.PLAYBACK_FOLDER = save_path
		res = yield tornado.gen.multi([self.process_frames_worker(save_path, worker_id=idx, total_workers=config.converter_threads) for idx in range(config.converter_threads)])
		print("Processing done")
		config.PLAYBACK_FOLDER = save_path
		return 0
		self.send_status("Decoding raw images...")
		
		out, err = yield self.execute_bash(["./scripts/convert_to_jpg.sh", save_path])
		
		print(out.decode())
		print("Converted")
		self.send_status("Raw images decoded. Updating preview")
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
		if config.REFRESH_DELAY/1000 + self.last_tick < now and config.REFRESH_DELAY > 1: # 
			self.last_tick = now
			#send_callback()
			#return
			filepattern = "out.{:04d}.ppm.png"
			thisfile = os.path.join(config.PLAYBACK_FOLDER, filepattern.format(self.current_id))
			#print(config.PLAYBACK_FOLDER)
			
			
			if not os.path.isfile(thisfile):
				self.current_id = 1
				thisfile = os.path.join(config.PLAYBACK_FOLDER, filepattern.format(self.current_id))
				
			if os.path.isfile(thisfile):
				with open(thisfile, "rb") as f:
					#self.current_id = (self.current_id + 1 ) % self.num_images
					self.current_id += config.SKIP_FRAMES
					msg = "data:image/png;base64," + base64.b64encode(f.read()).decode()
					send_callback(json.dumps({
						"type": "image",
						"image": msg,
						"frame_id": self.current_id
					}))
class Trigger:
	def __init__(self):
		self.past_state = False
		self.state = False
	def trigger_tick(self, trigger_callback):
		self.past_state = self.state
		self.state = GPIO.input(trigger_pin)

		if self.state and not self.past_state:
			trigger_callback()


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
	trig = Trigger()

	periodic_callback = tornado.ioloop.PeriodicCallback(
		lambda: sender.send_image_tick(WebSocketServer.send_message), 1
	)
	periodic_callback.start()

	trig_callback = tornado.ioloop.PeriodicCallback(
		lambda: trig.trigger_tick(WebSocketServer.capture_default), 10
	)
	trig_callback.start()

	# Start the event loop.
	io_loop.start()


if __name__ == "__main__":
	main()
