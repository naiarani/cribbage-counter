from threading import Thread
import cv2
import numpy as np
from picamera2 import Picamera2
import drm

class VideoStream:
    """Camera object with DRM display support"""
    def __init__(self, resolution=(640, 480), framerate=30, PiOrUSB=1, src=0):
        self.PiOrUSB = PiOrUSB

        if self.PiOrUSB == 1:  # PiCamera (libcamera)
            self.camera = Picamera2()
            config = self.camera.create_preview_configuration({"size": resolution})
            self.camera.configure(config)
            self.camera.start()

            self.frame = None

        if self.PiOrUSB == 2:  # USB camera
            self.stream = cv2.VideoCapture(src)
            self.stream.set(3, resolution[0])
            self.stream.set(4, resolution[1])

            (self.grabbed, self.frame) = self.stream.read()

        # DRM setup
        self.drm_display = drm.DrmDisplay()
        self.stopped = False

    def start(self):
        Thread(target=self.update, args=()).start()
        return self

    def update(self):
        if self.PiOrUSB == 1:  # PiCamera (libcamera)
            while not self.stopped:
                self.frame = self.camera.capture_array()

        if self.PiOrUSB == 2:  # USB camera
            while not self.stopped:
                (self.grabbed, self.frame) = self.stream.read()

    def read(self):
        return self.frame

    def display_frame(self, frame):
        if frame is not None:
            # Convert frame to RGB for DRM compatibility
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.drm_display.show(rgb_frame)

    def stop(self):
        self.stopped = True
        if self.PiOrUSB == 1:  # PiCamera (libcamera)
            self.camera.close()
        if self.PiOrUSB == 2:  # USB camera
            self.stream.release()




# from threading import Thread
# import cv2
# import numpy as np
# from picamera2 import Picamera2

# class VideoStream:
#     """Camera object"""
#     def __init__(self, resolution=(640, 480), framerate=30, PiOrUSB=1, src=0):

#         self.PiOrUSB = PiOrUSB

#         if self.PiOrUSB == 1:  # PiCamera (libcamera)
#             self.camera = Picamera2()
#             config = self.camera.create_preview_configuration({"size": resolution})
#             self.camera.configure(config)
#             self.camera.start()

#             # Initialize variable to store the camera frame
#             self.frame = None

#         if self.PiOrUSB == 2:  # USB camera
#             self.stream = cv2.VideoCapture(src)
#             self.stream.set(3, resolution[0])
#             self.stream.set(4, resolution[1])

#             # Read the first frame from the stream
#             (self.grabbed, self.frame) = self.stream.read()

#         self.stopped = False

#     def start(self):
#         Thread(target=self.update, args=()).start()
#         return self

#     def update(self):
#         if self.PiOrUSB == 1:  # PiCamera (libcamera)
#             while not self.stopped:
#                 # Capture a frame from the camera using libcamera
#                 self.frame = self.camera.capture_array()

#         if self.PiOrUSB == 2:  # USB camera
#             while not self.stopped:
#                 (self.grabbed, self.frame) = self.stream.read()

#     def read(self):
#         return self.frame

#     def stop(self):
#         self.stopped = True
#         if self.PiOrUSB == 1:  # PiCamera (libcamera)
#             self.camera.close()
#         if self.PiOrUSB == 2:  # USB camera
#             self.stream.release()
