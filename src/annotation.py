''' Utility functions for AWS Panorama development. '''

from typing import List, Tuple, Optional, Any, Callable
import datetime
import logging
from abc import ABC, abstractmethod
from typing import NamedTuple
import cv2

class Point(NamedTuple):
    ''' A point with both coordinates normalized to the [0; 1) range. '''
    x: float
    y: float

    def scale(self, width, height):
        ''' Scales this point to image coordinates. '''
        return (int(self.x * width), int(self.y * height))
    
    def in_image(self, img: 'np.array'):
        return self.scale(width=img.shape[1], height=img.shape[0])



class LabelAnnotation(NamedTuple):
    ''' A label annotation. '''
    point: Point
    text: str


class RectAnnotation(NamedTuple):
    ''' A rectangle annotation. '''
    point1: Point
    point2: Point


class TimestampAnnotation(LabelAnnotation):
    ''' A timestamp annotation. '''
    def __new__(cls, timestamp: Optional[datetime.datetime]=None, point: Point=Point(0.02, 0.04)):
        timestamp = timestamp or datetime.datetime.now()
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return LabelAnnotation.__new__(cls, point=point, text=time_str)



class AnnotationDriver(ABC):
    ''' Base class for annotating drawing drivers. 
    
    :param context: The context object to draw on. The type of this object is implementation
        specific.
    '''
    def __init__(self, parent_logger: Optional[logging.Logger] = None) -> None:
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
    
    def render(self, annotations: List, context: Any) -> Any:
        for anno in annotations:
            if isinstance(anno, LabelAnnotation):
                self.add_label(anno, context)
            elif isinstance(anno, RectAnnotation):
                self.add_rect(anno, context)
            else:
                assert True, 'Unknown annotation type'
        return context

    @abstractmethod
    def add_rect(self, rect: RectAnnotation, context: Any) -> None:
        ''' Add a text label to the frame. '''
        raise NotImplementedError

    @abstractmethod
    def add_label(self, label: LabelAnnotation, context: Any) -> None:
        ''' Add a label to the frame. '''
        raise NotImplementedError



class PanoramaMediaAnnotationDriver(AnnotationDriver):
    ''' AnnotationDriver implementation for panoramasdk.media type images. '''

    def add_rect(self, rect: RectAnnotation, context: 'panoramasdk.media') -> None:
        context.add_rect(rect.point1.x, rect.point1.y, rect.point2.x, rect.point2.y)

    def add_label(self, label: LabelAnnotation, context: 'panoramasdk.media') -> None:
        context.add_label(label.text, label.point.x, label.point.y)



class OpenCVImageAnnotationDriver(AnnotationDriver):
    ''' AnnotationDriver implementation for OpenCV images. 

    :param context: The OpenCV image.
    '''

    DEFAULT_OPENCV_COLOR = (255, 255, 255)
    DEFAULT_OPENCV_LINEWIDTH = 1
    DEFAULT_OPENCV_FONT = cv2.FONT_HERSHEY_PLAIN
    DEFAULT_OPENCV_FONT_SCALE = 1.0

    def add_rect(self, rect: RectAnnotation, context: 'np.array') -> None:
        cv2.rectangle(
            context,
            rect.point1.in_image(context),
            rect.point2.in_image(context),
            self.DEFAULT_OPENCV_COLOR,
            self.DEFAULT_OPENCV_LINEWIDTH
        )

    def add_label(self, label: LabelAnnotation, context: 'np.array') -> None:
        cv2.putText(
            context,
            label.text,
            label.point.in_image(context),
            self.DEFAULT_OPENCV_FONT,
            self.DEFAULT_OPENCV_FONT_SCALE,
            self.DEFAULT_OPENCV_COLOR
        )


if __name__ == '__main__':
    import numpy as np
    img = np.zeros((500, 500, 3), np.uint8)
    annos = [
        RectAnnotation(Point(0.1, 0.1), Point(0.9, 0.9)),
        LabelAnnotation(Point(0.5, 0.5), 'Hello World'),
        TimestampAnnotation()
    ]
    cv2driver = OpenCVImageAnnotationDriver()
    cv2driver.render(annos, img)
    cv2.imwrite('aw.png', img)
