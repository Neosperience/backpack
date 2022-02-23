''' Utility functions for AWS Panorama development. '''

from typing import Tuple, Optional, Any, Iterable, NamedTuple
import datetime
import logging
from abc import ABC, abstractmethod
import cv2

from .timepiece import local_now

class Point(NamedTuple):
    ''' A point with both coordinates normalized to the [0; 1) range.

    :ivar x: The x coordinate of the point
    :ivar y: The y coordinate of the point
    '''
    x: float
    y: float

    def scale(self, width: float, height: float) -> Tuple[int, int]:
        ''' Scales this point to image coordinates.

        :param width: The width of the target image
        :param height: The height of the target image
        :returns: The integer (pixel) coordinates of the point, scaled to the image dimensions.
        '''
        return (int(self.x * width), int(self.y * height))

    def in_image(self, img: 'np.array') -> Tuple[int, int]:
        ''' Scales this point in an OpenCV image.

        :param img: The OpenCV image of (height, width, channels) shape
        :returns: The integer (pixel) coordinates of the point, scaled to the image dimensions.
        '''
        return self.scale(width=img.shape[1], height=img.shape[0])



class LabelAnnotation(NamedTuple):
    ''' A label annotation to be rendered in an AnnotationDriver context.

    :ivar point: The origin of the label
    :ivar text: The text to be rendered
    '''
    point: Point
    text: str


class RectAnnotation(NamedTuple):
    ''' A rectangle annotation to be rendered in an AnnotationDriver context.

    :ivar point1: The top-left corner of the rectangle
    :ivar point2: The bottom-right corner of the rectangle
    '''
    point1: Point
    point2: Point


class TimestampAnnotation(LabelAnnotation):
    ''' A timestamp annotation to be rendered in an AnnotationDriver context.

    :param timestamp: The timestamp to be rendered. If not specified, the current local time
        will be used.
    :param point: The origin of the timestamp. If not specified, the timestamp will be places
        on the top-left corner of the image.
    '''
    def __new__(cls, timestamp: Optional[datetime.datetime]=None, point: Point=Point(0.02, 0.04)):
        timestamp = timestamp or local_now()
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return LabelAnnotation.__new__(cls, point=point, text=time_str)



class AnnotationDriverBase(ABC):
    ''' Base class for annotating drawing drivers.

    Annotation drivers provide an unified API to draw annotations on images of different backends.
    All annotation driver should derive from `AnnotationDriverBase`.

    :param parent_logger: If you want to connect the logger of the annotation driver to a parent,
        specify it here.
    '''
    def __init__(self, parent_logger: Optional[logging.Logger] = None) -> None:
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )

    def render(self, annotations: Iterable, context: Any) -> Any:
        ''' Renders a collection of annotations on a context.

        :param annotations: An iterable collection of annotation type definied in this module.
        :param context: The context of the backend. Type is implementation-specific.
        :returns: The context.
        '''
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
        ''' Subclasses should implement this method to add a rectangle to the frame. '''
        raise NotImplementedError

    @abstractmethod
    def add_label(self, label: LabelAnnotation, context: Any) -> None:
        ''' Subclasses should implement this method to add a label to the frame. '''
        raise NotImplementedError



class PanoramaMediaAnnotationDriver(AnnotationDriverBase):
    ''' Annotation driver implementation for panoramasdk.media type images. '''

    def add_rect(self, rect: RectAnnotation, context: 'panoramasdk.media') -> None:
        context.add_rect(rect.point1.x, rect.point1.y, rect.point2.x, rect.point2.y)

    def add_label(self, label: LabelAnnotation, context: 'panoramasdk.media') -> None:
        context.add_label(label.text, label.point.x, label.point.y)



class OpenCVImageAnnotationDriver(AnnotationDriverBase):
    ''' Annotation driver implementation for OpenCV images. '''

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
    image = np.zeros((500, 500, 3), np.uint8)
    annos = [
        RectAnnotation(Point(0.1, 0.1), Point(0.9, 0.9)),
        LabelAnnotation(Point(0.5, 0.5), 'Hello World'),
        TimestampAnnotation()
    ]
    cv2driver = OpenCVImageAnnotationDriver()
    rendered = cv2driver.render(annos, image)
    cv2.imwrite('aw.png', rendered)
