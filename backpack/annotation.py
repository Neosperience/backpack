''' This module makes it possible to draw annotations on different
backends with an unified API. Currently, you can draw rectangles and labels with 
:mod:`~backpack.annotation` on ``panoramasdk.media`` and OpenCV images 
(:class:`numpy arrays <numpy.ndarray>`).'''

from typing import Tuple, Optional, Any, Iterable, NamedTuple, Union
from enum import Enum
import datetime
import logging
from abc import ABC, abstractmethod
import cv2

from .timepiece import local_now

class Point(NamedTuple):
    ''' A point with both coordinates normalized to the [0; 1) range.

    Args:
        x (float): The x coordinate of the point
        y (float): The y coordinate of the point
    '''
    x: float
    ''' The x coordinate of the point '''

    y: float
    ''' The y coordinate of the point '''

    def scale(self, width: float, height: float) -> Tuple[int, int]:
        ''' Scales this point to image coordinates.

        :param width: The width of the target image
        :param height: The height of the target image
        :returns: The integer (pixel) coordinates of the point, scaled to the image dimensions.
        '''
        return (int(self.x * width), int(self.y * height))

    def in_image(self, img: 'numpy.ndarray') -> Tuple[int, int]:
        ''' Scales this point in an OpenCV image.

        :param img: The OpenCV image of ``(height, width, channels)`` shape
        :returns: The integer (pixel) coordinates of the point, scaled to the image dimensions.
        '''
        return self.scale(width=img.shape[1], height=img.shape[0])


class Color(NamedTuple):
    ''' A color in the red, blue, green space.
    
    The color coordinates are integers in the [0; 255] range.
    
    Args:
        r (int): The red component of the color
        g (int): The green component of the color
        b (int): The blue component of the color
    '''
    r: int
    ''' The red component of the color. '''
    g: int
    ''' The green component of the color. '''
    b: int
    ''' The blue component of the color. '''


class LabelAnnotation(NamedTuple):
    ''' A label annotation to be rendered in an :class:`AnnotationDriver` context.

    Args:
        point (Point): The origin of the label
        text (str): The text to be rendered
        color (Color): The color of the text
    '''
    point: Point
    ''' The origin of the label. '''

    text: str
    ''' The text to be rendered. '''

    color: Color = None
    ''' The color of the text. If `None`, the default drawing color will be used. '''


class RectAnnotation(NamedTuple):
    ''' A rectangle annotation to be rendered in an AnnotationDriver context.

    Args:
        point1 (Point): The top-left corner of the rectangle
        point2 (Point): The bottom-right corner of the rectangle
        color (Color): The line color of the rectangle
    '''
    point1: Point
    ''' The top-left corner of the rectangle '''

    point2: Point
    ''' The bottom-right corner of the rectangle '''

    color: Color = None
    ''' The line color of the rectangle. If `None`, the default drawing color will be used. '''

    @property
    def center(self) -> Point:
        ''' The center of the rectangle. '''
        return Point((self.point1.x + self.point2.x) / 2, (self.point1.y + self.point2.y) / 2)

    def base(self) -> Point:
        ''' Returns the center of the base of the rectangle. '''
        return Point((self.point1.x + self.point2.x) / 2, self.point2.y)

    @property
    def size(self) -> Tuple[float, float]:
        ''' The width and height of the rectangle. '''
        return abs(self.point1.y - self.point2.y), abs(self.point1.x - self.point2.x)


class LineAnnotation(NamedTuple):
    ''' A line annotation to be rendered in an AnnotationDriver context.

    Args:
        point1 (Point): The first end of the line
        point2 (Point): The second end of the line
        color (Color): The color of the line
    '''
    point1: Point
    ''' The first end of the line '''

    point2: Point
    ''' The second end of the line '''

    color: Color = None
    ''' The color of the line. If `None`, the default drawing color will be used. '''

    thickness: int = 1
    ''' The thickness of the line. '''


class MarkerAnnotation(NamedTuple):
    ''' A marker annotation to be rendered in an AnnotationDriver context.
    
    Args:
        point (Point): The coordinates of the maker
        style (MarkerAnnotation.Style): The style of the marker
        color (Color): The color of the maker
    '''
    class Style(Enum):
        ''' Possible set of marker types. '''
        CROSS = 1
        ''' A crosshair marker shape. '''
        TILTED_CROSS = 2
        ''' A 45 degree tilted crosshair marker shape. '''
        STAR = 3
        ''' A star marker shape, combination of cross and tilted cross. '''
        DIAMOND = 4
        ''' A diamond marker shape. '''
        SQUARE = 5
        ''' A square marker shape. '''
        TRIANGLE_UP = 6
        ''' An upwards pointing triangle marker shape. '''
        TRIANGLE_DOWN = 7
        ''' A downwards pointing triangle marker shape. '''

    point: Point
    ''' The coordinates of the maker. '''
    style: Style = Style.CROSS
    ''' The style of the marker. '''
    color: Color = None
    ''' The color of the maker. '''


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

    Args:
        parent_logger: If you want to connect the logger of the annotation driver to a parent,
            specify it here.
    '''
    def __init__(self, parent_logger: Optional[logging.Logger] = None):
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )

    def render(
        self, 
        annotations: Iterable[Union[LabelAnnotation, RectAnnotation]], 
        context: Any
    ) -> Any:
        ''' Renders a collection of annotations on a context.

        Args:
            annotations: An iterable collection of annotation type definied in this module.
            context: The context of the backend. Type is implementation-specific.

        Returns: 
            The context.
        '''
        for anno in annotations:
            if isinstance(anno, LabelAnnotation):
                self.add_label(anno, context)
            elif isinstance(anno, RectAnnotation):
                self.add_rect(anno, context)
            elif isinstance(anno, MarkerAnnotation):
                self.add_marker(anno, context)
            elif isinstance(anno, LineAnnotation):
                self.add_line(anno, context)
            else:
                raise ValueError('Unknown annotation type')
        return context

    @abstractmethod
    def add_rect(self, rect: RectAnnotation, context: Any) -> None:
        ''' Renders a rectangle on the frame. 
        
        Args:
            rect: A rectangle annotation.
            context: A backend-specific context object that was passed to the :meth:`render` method.
        '''

    @abstractmethod
    def add_label(self, label: LabelAnnotation, context: Any) -> None:
        ''' Renders a label on the frame. 
        
        Args:
            label: A label annotation.
            context: A backend-specific context object that was passed to the :meth:`render` method.
        '''

    @abstractmethod
    def add_marker(self, marker: MarkerAnnotation, context: Any) -> None:
        ''' Renders a marker on the frame. 
        
        Args:
            marker: A marker annotation.
            context: A backend-specific context object that was passed to the :meth:`render` method.
        '''

    @abstractmethod
    def add_line(self, label: LineAnnotation, context: Any) -> None:
        ''' Renders a line on the frame. 
        
        Args:
            line: A line annotation.
            context: A backend-specific context object that was passed to the :meth:`render` method.
        '''


class PanoramaMediaAnnotationDriver(AnnotationDriverBase):
    ''' Annotation driver implementation for Panorama media type images. 
    
    You should pass an ``panoramasdk.media`` instance as the context argument of the 
    :meth:`~backpack.annotation.AnnotationDriverBase.render()` method. 
    
    :class:`PanoramaMediaAnnotationDriver` currently does not support colors.
    '''

    MARKER_STYLE_TO_STR = {
        MarkerAnnotation.Style.CROSS: '+',
        MarkerAnnotation.Style.TILTED_CROSS: 'x',
        MarkerAnnotation.Style.STAR: '*',
        MarkerAnnotation.Style.DIAMOND: '<>',
        MarkerAnnotation.Style.SQUARE: '||',
        MarkerAnnotation.Style.TRIANGLE_UP: '/\\',
        MarkerAnnotation.Style.TRIANGLE_DOWN: '\\/',
    }

    def add_rect(self, rect: RectAnnotation, context: 'panoramasdk.media') -> None:
        context.add_rect(rect.point1.x, rect.point1.y, rect.point2.x, rect.point2.y)

    def add_label(self, label: LabelAnnotation, context: 'panoramasdk.media') -> None:
        context.add_label(label.text, label.point.x, label.point.y)

    def add_marker(self, marker: MarkerAnnotation, context: 'panoramasdk.media') -> None:
        marker_str = PanoramaMediaAnnotationDriver.MARKER_STYLE_TO_STR.get(marker.style, '.')
        context.add_label(marker_str, marker.point.x, marker.point.y)
    
    def add_line(self, label: LineAnnotation, context: Any) -> None:
        print('WARNING: PanoramaMediaAnnotationDriver.add_line is not implemented')


class OpenCVImageAnnotationDriver(AnnotationDriverBase):
    ''' Annotation driver implementation for OpenCV images. 
    
    You should pass an :class:`numpy.ndarray` instance as the context argument of the 
    :meth:`~backpack.annotation.AnnotationDriverBase.render()` method. '''

    DEFAULT_OPENCV_COLOR = Color(255, 255, 255)
    DEFAULT_OPENCV_LINEWIDTH = 1
    DEFAULT_OPENCV_FONT = cv2.FONT_HERSHEY_PLAIN
    DEFAULT_OPENCV_FONT_SCALE = 1.0

    MARKER_STYLE_TO_CV2 = {
        MarkerAnnotation.Style.CROSS: cv2.MARKER_DIAMOND,
        MarkerAnnotation.Style.TILTED_CROSS: cv2.MARKER_TILTED_CROSS,
        MarkerAnnotation.Style.STAR: cv2.MARKER_STAR,
        MarkerAnnotation.Style.DIAMOND: cv2.MARKER_DIAMOND,
        MarkerAnnotation.Style.SQUARE: cv2.MARKER_SQUARE,
        MarkerAnnotation.Style.TRIANGLE_UP: cv2.MARKER_TRIANGLE_UP,
        MarkerAnnotation.Style.TRIANGLE_DOWN: cv2.MARKER_TRIANGLE_DOWN,
    }

    def _color_to_cv2(self, color: Color) -> Tuple[int, int, int]:
        return tuple(reversed(color)) if color is not None else self.DEFAULT_OPENCV_COLOR

    def add_rect(self, rect: RectAnnotation, context: 'numpy.ndarray') -> None:
        cv2.rectangle(
            context,
            rect.point1.in_image(context),
            rect.point2.in_image(context),
            self._color_to_cv2(rect.color),
            self.DEFAULT_OPENCV_LINEWIDTH
        )

    def add_label(self, label: LabelAnnotation, context: 'numpy.ndarray') -> None:
        cv2.putText(
            context,
            label.text,
            label.point.in_image(context),
            self.DEFAULT_OPENCV_FONT,
            self.DEFAULT_OPENCV_FONT_SCALE,
            self._color_to_cv2(label.color)
        )

    def add_marker(self, marker: MarkerAnnotation, context: 'numpy.ndarray') -> None:
        markerType = OpenCVImageAnnotationDriver.MARKER_STYLE_TO_CV2.get(
            marker.style, cv2.MARKER_DIAMOND
        )
        cv2.drawMarker(
            context,
            marker.point.in_image(context),
            self._color_to_cv2(marker.color),
            markerType
        )

    def add_line(self, line: LineAnnotation, context: Any) -> None:
        cv2.line(
            context,
            line.point1.in_image(context),
            line.point2.in_image(context),
            self._color_to_cv2(line.color),
            line.thickness
        )
