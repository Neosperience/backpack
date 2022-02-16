''' Utility functions for AWS Panorama development. '''

from typing import Tuple, Optional
import datetime

import cv2

def add_timestamp(
    img: 'np.array',
    timestamp: Optional[datetime.datetime]=None,
    origin: Tuple[int, int]=(10, 20),
    color: Tuple[int, int, int]=(255, 255, 255)
):
    ''' Adds a timestamp to the cv2 image. '''
    timestamp = timestamp or datetime.datetime.now()
    time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    cv2.putText(img, time_str, origin, cv2.FONT_HERSHEY_PLAIN, 1.0, color)

def to_datetime(panorama_ts: Tuple[int, int]) -> datetime.datetime:
    ''' Converts panoramasdk.media.time_stamp (seconds, microsececonds)
    tuple to python datetime.
    '''
    sec, microsec = panorama_ts
    return datetime.datetime.fromtimestamp(sec + microsec / 1000000.0)


class AnnotationWrapper:
    ''' This class wraps the different APIs of panoramasdk.media and OpenCV draw methods. '''

    DEFAULT_OPENCV_COLOR = (255, 255, 255)
    DEFAULT_OPENCV_LINEWIDTH = 1
    DEFAULT_OPENCV_FONT = cv2.FONT_HERSHEY_PLAIN
    DEFAULT_OPENCV_FONT_SCALE = 1.0

    def __init__(self):
        self.labels = []
        self.rectangles = []

    def add_rect(self, left, top, right, bottom):
        self.rectangles.append((left, top, right, bottom))

    def add_label(self, x, y, text):
        self.labels.append((x, y, text))

    def render_on_panorama_media(self, media: 'panoramasdk.media'):
        ''' Renders the annotations on a panoramasdk media object. '''
        for (left, top, right, bottom) in self.rectangles:
            media.add_rect(left, top, right, bottom)
        for (x, y, text) in self.labels:
            media.add_label(x, y, text)

    def render_on_cv2_image(self, img: 'np.array'):
        ''' Renders the annotations on an OpenCV image object. '''
        height, width, _ = img.shape
        for (left, top, right, bottom) in self.rectangles:
            point1 = (int(left * width), int(top * height))
            point2 = (int(right * width), int(bottom * height))
            cv2.rectangle(
                img,
                point1,
                point2,
                self.DEFAULT_OPENCV_COLOR,
                self.DEFAULT_OPENCV_LINEWIDTH
            )
        for (x, y, text) in self.labels:
            point = (int(x * width), int(y * height))
            cv2.putText(
                img,
                text,
                point,
                self.DEFAULT_OPENCV_FONT,
                self.DEFAULT_OPENCV_FONT_SCALE,
                self.DEFAULT_OPENCV_COLOR
            )

if __name__ == '__main__':
    import numpy as np
    aw = AnnotationWrapper()
    aw.add_rect(0.1, 0.1, 0.9, 0.9)
    aw.add_label(0.5, 0.5, 'Janos')
    img = np.zeros((500, 500, 3), np.uint8)
    aw.render_on_cv2_image(img)
    cv2.imwrite('aw.png', img)
