''' This module makes it possible to draw annotations on different
backends with an unified API. Currently, you can draw rectangles and labels with 
:mod:`~backpack.annotation` on ``panoramasdk.media`` and OpenCV images 
(:class:`numpy arrays <numpy.ndarray>`).'''

from typing import Tuple, Optional, Any, Iterable, NamedTuple, Union
import collections.abc
from enum import Enum
import datetime
import logging
from abc import ABC, abstractmethod
import cv2
import numpy as np

from .timepiece import local_now
from .geometry import Point, Line

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

    The :attr:`point` refers to the position of the anchor point.

    Args:
        point (Point): The origin of the label
        text (str): The text to be rendered
        color (Color): The color of the text
    '''
    class HorizontalAnchor(Enum):
        ''' Horizontal anchor point location. '''
        LEFT = 1,
        ''' Left anchor point '''
        CENTER = 2,
        ''' Center anchor point '''
        RIGHT = 3
        ''' Right anchor point '''

    class VerticalAnchor(Enum):
        ''' Vertical anchor point location. '''
        TOP = 1
        ''' Top anchor point '''
        CENTER = 2
        ''' Center anchor point '''
        BASELINE = 3
        ''' Text baseline anchor point ''' 
        BOTTOM = 4
        ''' Bottom anchor point '''

    point: Point
    ''' The origin of the label. '''

    text: str
    ''' The text to be rendered. '''

    color: Color = None
    ''' The color of the text. If `None`, the default drawing color will be used. '''

    horizontal_anchor: HorizontalAnchor = HorizontalAnchor.LEFT
    ''' Horizontal anchor point location '''

    vertical_anchor: VerticalAnchor = VerticalAnchor.BOTTOM
    ''' Vertical anchor point location '''


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

    @property
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
        line (Line): The line segment to be drawn
        color (Color): The color of the line
    '''
    line: Line
    ''' The line segment to be drawn '''

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

    Args:
        timestamp: The timestamp to be rendered. If not specified, the current local time
            will be used.
        point: The origin of the timestamp. If not specified, the timestamp will be places
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

    @staticmethod
    def to_point(point: Any) -> Tuple[float, float]:
        ''' Aims to convert different point representations to a `(x, y)` tuple. 
        
        Args:
            point: an object with attributes `x` and `y`, or an iterable with length of 2

        Returns:
            A tuple of float containing the x and y coordinates of the point.
        
        Raises:
            ValueError: if the conversation was not successful
        '''
        if hasattr(point, 'x') and hasattr(point, 'y'):
            return (float(point.x), float(point.y))
        elif isinstance(point, (collections.abc.Sequence, np.ndarray)) and len(point) >= 2:
            return (float(point[0]), float(point[1]))
        else:
            raise ValueError('Could not convert %s to a point.' % point)

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
        x1, y1 = AnnotationDriverBase.to_point(rect.point1)
        x2, y2 = AnnotationDriverBase.to_point(rect.point2)
        context.add_rect(x1, y1, x2, y2)

    def add_label(self, label: LabelAnnotation, context: 'panoramasdk.media') -> None:
        x, y = AnnotationDriverBase.to_point(label.point)
        context.add_label(label.text, x, y)

    def add_marker(self, marker: MarkerAnnotation, context: 'panoramasdk.media') -> None:
        marker_str = PanoramaMediaAnnotationDriver.MARKER_STYLE_TO_STR.get(marker.style, '.')
        x, y = AnnotationDriverBase.to_point(marker.point)
        context.add_label(marker_str, x, y)
    
    def add_line(self, label: LineAnnotation, context: Any) -> None:
        print('WARNING: PanoramaMediaAnnotationDriver.add_line is not implemented')


class OpenCVImageAnnotationDriver(AnnotationDriverBase):
    ''' Annotation driver implementation for OpenCV images. 
    
    You should pass an :class:`numpy.ndarray` instance as the context argument of the 
    :meth:`~backpack.annotation.AnnotationDriverBase.render()` method. '''

    DEFAULT_COLOR = Color(255, 255, 255)
    DEFAULT_LINEWIDTH = 1
    DEFAULT_FONT = cv2.FONT_HERSHEY_PLAIN

    IMG_HEIGHT_FOR_UNIT_FONT_SCALE = 400
    ''' The height of the image where 1.0 font_scale will be used. '''

    DEFAULT_TEXT_PADDING = (2, 2)

    MARKER_STYLE_TO_CV2 = {
        MarkerAnnotation.Style.CROSS: cv2.MARKER_DIAMOND,
        MarkerAnnotation.Style.TILTED_CROSS: cv2.MARKER_TILTED_CROSS,
        MarkerAnnotation.Style.STAR: cv2.MARKER_STAR,
        MarkerAnnotation.Style.DIAMOND: cv2.MARKER_DIAMOND,
        MarkerAnnotation.Style.SQUARE: cv2.MARKER_SQUARE,
        MarkerAnnotation.Style.TRIANGLE_UP: cv2.MARKER_TRIANGLE_UP,
        MarkerAnnotation.Style.TRIANGLE_DOWN: cv2.MARKER_TRIANGLE_DOWN,
    }

    @staticmethod
    def scale(point: Any, context: 'numpy.ndarray') -> Tuple[float, float]:
        ''' Converts and scales a point instance to an image context '''
        x, y = AnnotationDriverBase.to_point(point)
        return (int(x * context.shape[1]), int(y * context.shape[0]))

    def _color_to_cv2(self, color: Color) -> Tuple[int, int, int]:
        return tuple(reversed(color)) if color is not None else self.DEFAULT_COLOR

    def add_rect(self, rect: RectAnnotation, context: 'numpy.ndarray') -> None:
        cv2.rectangle(
            context,
            OpenCVImageAnnotationDriver.scale(rect.point1, context),
            OpenCVImageAnnotationDriver.scale(rect.point2, context),
            self._color_to_cv2(rect.color),
            self.DEFAULT_LINEWIDTH
        )

    @staticmethod
    def _get_anchor_shift(
        horizontal_anchor: LabelAnnotation.HorizontalAnchor, 
        vertical_anchor: LabelAnnotation.VerticalAnchor, 
        size_x: int, 
        size_y: int, 
        baseline: int
    ) -> Tuple[int, int]:
        ''' Gets the shift of the text position based on anchor point location and size of the 
        text. '''
        padding_x, padding_y = OpenCVImageAnnotationDriver.DEFAULT_TEXT_PADDING
        shift_x, shift_y = (padding_x, -padding_y)
        if horizontal_anchor == LabelAnnotation.HorizontalAnchor.CENTER:
            shift_x = -size_x / 2
        elif horizontal_anchor == LabelAnnotation.HorizontalAnchor.RIGHT:
            shift_x = -(size_x + padding_x)
        if vertical_anchor == LabelAnnotation.VerticalAnchor.CENTER:
            shift_y = size_y / 2
        elif vertical_anchor == LabelAnnotation.VerticalAnchor.TOP:
            shift_y = size_y * 1.2 + padding_x
        elif vertical_anchor == LabelAnnotation.VerticalAnchor.BASELINE:
            shift_y = baseline
        return (int(shift_x), int(shift_y))

    def add_label(self, label: LabelAnnotation, context: 'numpy.ndarray') -> None:
        ctx_height = context.shape[0]
        scale = ctx_height / self.IMG_HEIGHT_FOR_UNIT_FONT_SCALE
        thickness = max(int(scale), 1)
        font = self.DEFAULT_FONT
        shift_x, shift_y = (0, 0)
        if (label.horizontal_anchor != LabelAnnotation.HorizontalAnchor.LEFT or
            label.vertical_anchor != LabelAnnotation.VerticalAnchor.BOTTOM):
            (size_x, size_y), baseline = cv2.getTextSize(
                text=label.text, fontFace=font, fontScale=scale, thickness=thickness
            )
            shift_x, shift_y = OpenCVImageAnnotationDriver._get_anchor_shift(
                label.horizontal_anchor,
                label.vertical_anchor,
                size_x, size_y, baseline
            )

        x, y = OpenCVImageAnnotationDriver.scale(label.point, context)
        x += shift_x
        y += shift_y
        cv2.putText(
            img=context,
            text=label.text,
            org=(x, y),
            fontFace=font,
            fontScale=scale,
            color=self._color_to_cv2(label.color),
            thickness=thickness
        )

    def add_marker(self, marker: MarkerAnnotation, context: 'numpy.ndarray') -> None:
        markerType = OpenCVImageAnnotationDriver.MARKER_STYLE_TO_CV2.get(
            marker.style, cv2.MARKER_DIAMOND
        )
        cv2.drawMarker(
            context,
            OpenCVImageAnnotationDriver.scale(marker.point, context),
            self._color_to_cv2(marker.color),
            markerType
        )

    def add_line(self, line: LineAnnotation, context: Any) -> None:
        cv2.line(
            context,
            OpenCVImageAnnotationDriver.scale(line.point1, context),
            OpenCVImageAnnotationDriver.scale(line.point2, context),
            self._color_to_cv2(line.color),
            line.thickness
        )
