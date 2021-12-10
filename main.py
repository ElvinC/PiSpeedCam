import random
import tornado.ioloop
import tornado.web
import tornado.websocket
import base64


class WebSocketServer(tornado.websocket.WebSocketHandler):
	clients = set()

	def open(self):
		WebSocketServer.clients.add(self)

	def on_close(self):
		WebSocketServer.clients.remove(self)

	@classmethod
	def send_message(cls, message: str):
		print(f"Sending data to {len(cls.clients)} client(s).")
		for client in cls.clients:
			client.write_message(message)

class MainHandler(tornado.web.RequestHandler):
	def get(self):
		self.render("client_static/client.html")

	def set_extra_headers(self, path):
	    self.set_header("Cache-control", "no-cache")

class ImageSender:
	def __init__(self):
		self.current_id = 0
		self.num_images = 2

	def sample(self):
		
		with open(f"test_frames/frame{self.current_id}.png", "rb") as f:
			self.current_id = (self.current_id + 1 ) % self.num_images
			return "data:image/png;base64," + base64.b64encode(f.read()).decode()

def main():
	app = tornado.web.Application(
		[(r"/websocket/", WebSocketServer),
		 (r"/", MainHandler)],
		websocket_ping_interval=10,
		websocket_ping_timeout=30,
		debug=True,
	)
	app.listen(8081)

	# Create an event loop (what Tornado calls an IOLoop).
	io_loop = tornado.ioloop.IOLoop.current()

	# Send image
	# every 500ms.
	random_bernoulli = ImageSender()
	periodic_callback = tornado.ioloop.PeriodicCallback(
		lambda: WebSocketServer.send_message(str(random_bernoulli.sample())), 1000
	)
	periodic_callback.start()

	# Start the event loop.
	io_loop.start()


if __name__ == "__main__":
	main()