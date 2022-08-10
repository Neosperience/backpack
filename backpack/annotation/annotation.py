''' This module makes it possible to draw annotations on different
backends with an unified API. Currently, you can draw rectangles and labels with
:mod:`~backpack.annotation` on ``panoramasdk.media`` and OpenCV images
(:class:`numpy arrays <numpy.ndarray>`).'''

from typing import Optional
from enum import Enum
import datetime
from abc import ABC
from dataclasses import dataclass

from .color import Color
from ..timepiece import local_now
from ..geometry import Point, Rectangle, Line, PolyLine


class Annotation(ABC):
    ''' Abstract base class for annotations. '''


@dataclass(frozen=True)
class LabelAnnotation(Annotation):
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

    size: float = 1.0
    ''' The relative size of the text '''


@dataclass(frozen=True)
class RectAnnotation(Annotation):
    ''' A rectangle annotation to be rendered in an AnnotationDriver context.

    Args:
        rect: The rectangle to be rendered in the AnnotationDriver context.
        color: The line color of the rectangle.
    '''
    rect: Rectangle
    ''' The rectangle to be rendered in the AnnotationDriver context '''

    color: Color = None
    ''' The line color of the rectangle. If `None`, the default drawing color will be used. '''


@dataclass(frozen=True)
class LineAnnotation(Annotation):
    ''' A line annotation to be rendered in an AnnotationDriver context.

    Args:
        line: The line segment to be drawn
        color: The color of the line
    '''
    line: Line
    ''' The line segment to be drawn '''

    color: Color = None
    ''' The color of the line. If `None`, the default drawing color will be used. '''

    thickness: int = 1
    ''' The thickness of the line. '''


@dataclass(frozen=True)
class MarkerAnnotation(Annotation):
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


@dataclass(frozen=True)
class PolyLineAnnotation(Annotation):
    ''' A PolyLine annotation to be rendered in an AnnotationDriver context.

    Args:
        polyline(PolyLine): The PolyLine instance
        thickness(int): Line thickness
        color(Color): Line color
        fill_color(Color): Fill color
    '''

    polyline : PolyLine
    ''' The PolyLine instance. '''
    thickness : int = 1
    ''' Line thickness. '''
    color : Color = None
    ''' Line color. '''
    fill_color : Color = None
    ''' Fill color. '''


@dataclass(frozen=True)
class TimestampAnnotation(LabelAnnotation):
    ''' A timestamp annotation to be rendered in an AnnotationDriver context.

    Args:
        timestamp: The timestamp to be rendered. If not specified, the current local time
            will be used.
        point: The origin of the timestamp. If not specified, the timestamp will be places
            on the top-left corner of the image.
    '''
    def __init__(self, timestamp: Optional[datetime.datetime]=None, point: Point=Point(0.02, 0.04)):
        timestamp = timestamp or local_now()
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        return super().__init__(point=point, text=time_str)


@dataclass(frozen=True)
class BoundingBoxAnnotation(Annotation):
    ''' A bounding box annotation with a rectangle, and optional upper and lower labels.

    Args:
        rectangle: The rectangle of the bounding box.
        top_label: The optional top label.
        bottom_label: The optional bottom label.
        color: The color of the bounding box and the labels.
    '''

    rectangle: Rectangle
    ''' The rectangle of the bounding box. '''

    top_label: Optional[str] = None
    ''' The optional top label. '''

    bottom_label: Optional[str] = None
    ''' The optional bottom label. '''

    color: Optional[Color] = None
    ''' The color of the bounding box and the labels. '''
