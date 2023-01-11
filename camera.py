#Modified by smartbuilds.io
#Date: 27.09.20
#Desc: This scrtipt script..

import cv2 as cv
from imutils.video.pivideostream import PiVideoStream
import imutils
import time
from datetime import datetime
import numpy as np

class VideoCamera(object):
    def __init__(self, flip = False, file_type  = ".jpg", photo_string= "stream_photo"):
        self.vs = PiVideoStream(resolution=(960, 544), framerate=20).start()
        self.flip = flip # Flip frame vertically
        self.file_type = file_type # image type i.e. .jpg
        self.photo_string = photo_string # Name to save the photo
        self.activated = True
        time.sleep(2.0)

    def __del__(self):
        self.vs.stop()

    def flip_if_needed(self, frame):
        if self.flip:
            return np.flip(frame, 0)
        return frame

    def get_frame(self):
        if self.activated:
            frame = self.flip_if_needed(self.vs.read())
            ret, jpeg = cv.imencode(self.file_type, frame)
            self.previous_frame = jpeg
            return jpeg.tobytes()
        return None

    # Take a photo, called by camera button
    def take_picture(self):
        if self.activated:
            frame = self.flip_if_needed(self.vs.read())
            ret, image = cv.imencode(self.file_type, frame)
            today_date = datetime.now().strftime("%m%d%Y-%H%M%S") # get current time
            cv.imwrite(str(self.photo_string + "_" + today_date + self.file_type), frame)
        return None

    def stop(self):
        self.vs.stop()
        self.activated = False

    def start(self):
        self.vs.start()
        self.activated = True

    def is_activated(self):
        return self.activated

