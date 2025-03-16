import socket
import time

from picamera2 import Picamera2, Preview
from picamera2.encoders import H264Encoder
from picamera2.outputs import FileOutput
import time


picam2 = Picamera2()
picam2.start_preview(Preview.DRM, x=1000, y=100)

preview_config = picam2.create_preview_configuration({"size": (1280, 720)})
picam2.configure(preview_config)

picam2.start()
time.sleep(10)