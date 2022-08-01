''' This module makes it possible to draw annotations on different
backends with an unified API. Currently, you can draw rectangles and labels with
:mod:`~backpack.annotation` on ``panoramasdk.media`` and OpenCV images
(:class:`numpy arrays <numpy.ndarray>`).'''

from typing import Tuple, Optional, Any, Iterable, NamedTuple, Union, Callable, Sequence, Mapping
import collections.abc
from enum import Enum
import datetime
import logging
from abc import ABC, abstractmethod
import hashlib
import cv2
import numpy as np

from .timepiece import local_now
from .geometry import Point, Rectangle, Line, PolyLine
from .detector import Detection, TrackedObject

class Color(NamedTuple):
    ''' A color in the red, blue, green space.

    The color coordinates are integers in the [0; 255] range.

    Args:
        r (int): The red component of the color
        g (int): The green component of the color
        b (int): The blue component of the color
        alpha (float): The alpha channel of transparency, ranged from `0` to `1`
    '''
    r: int
    ''' The red component of the color. '''
    g: int
    ''' The green component of the color. '''
    b: int
    ''' The blue component of the color. '''
    alpha: float = 1.0
    ''' The alpha component of transparency. '''

    @classmethod
    def from_hex(cls, value: Union[str, int]) -> 'Color':
        ''' Creates a color object from its hexadeciman representation.

        Args:
            value: integer or HTML color string

        Returns:
            a new color object
        '''
        if isinstance(value, str):
            value = value.lstrip('#')
            rgb = tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
            return cls(*rgb)
        elif isinstance(value, int):
            rgb = tuple((value & (0xff << (i * 8))) >> (i * 8) for i in (2, 1, 0))
            return cls(*rgb)
        else:
            raise ValueError('Value argument must be str or int')

    @classmethod
    def from_value(cls, value: Union[str, int, Sequence, Mapping, 'Color']):
        ''' Converts an integer (interpreted as 3 bytes hex value), a HTML color string, a
        sequence of 3 or 4 integers, or a dictionary containing 'r', 'g', 'b' and optionally
        'alpha' keys to a Color object.

        Args:
            value: The value to be converted.

        Returns:
            The new Color object.

        Raises:
            ValueError if the conversion was not successful.
        '''
        if isinstance(value, Color):
            return value
        if isinstance(value, (str, int)):
            return cls.from_hex(value)
        elif (
            isinstance(value, collections.abc.Sequence) and
            (len(value) == 3 or len(value) == 4) and
            all(isinstance(e, int if idx < 3 else float) for idx, e in enumerate(value))
        ):
            return cls(*value)
        elif (
            isinstance(value, collections.abc.Mapping) and
            'r' in value and 'g' in value and 'b' in value
        ):
            params = {k: v for k, v in value.items() if k in ('r', 'g', 'b')}
            alpha = value.get('a', value.get('alpha'))
            if alpha is not None:
                params['alpha'] = alpha
            return cls(**params)
        else:
            raise ValueError(f'Could not convert {value} to a Color')

    @classmethod
    def from_id(cls, identifier: int, salt: str = 'salt') -> 'Color':
        ''' Creates a pseudo-random color from an integer identifier.

        For the same identifier and salt the same color will be generated.

        Args:
            identifier: the identifier
            salt: the salt, change this if you want a different color for the same identifier

        Returns:
            A pseudo-random color based on the identifier and the salt.
        '''
        h = hashlib.md5((salt + str(identifier)).encode('utf-8')).digest()
        return Color(h[0], h[1], h[2])

    def brightness(self, brightness: float) -> 'Color':
        ''' Returns a new Color instance with changed brightness.

        Args:
            brightness: The new brightness, if greater than 1, a brighter color will be returned,
                if smaller than 1, a darker color.

        Returns:
            A new color instance with changed brightness.
        '''
        conv = lambda ch: min(255, int(ch * brightness))
        return Color(r=conv(self.r), g=conv(self.g), b=conv(self.b), alpha=self.alpha)


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

    size: float = 1.0
    ''' The relative size of the text '''


class RectAnnotation(NamedTuple):
    ''' A rectangle annotation to be rendered in an AnnotationDriver context.

    Args:
        rect: The rectangle to be rendered in the AnnotationDriver context.
        color: The line color of the rectangle.
    '''
    rect: Rectangle
    ''' The rectangle to be rendered in the AnnotationDriver context '''

    color: Color = None
    ''' The line color of the rectangle. If `None`, the default drawing color will be used. '''


class LineAnnotation(NamedTuple):
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


class PolyLineAnnotation(NamedTuple):
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


class BoundingBoxAnnotation(NamedTuple):
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

    @staticmethod
    def from_detection(
        detection: Detection,
        color: Optional[Color]=None
    ):
        ''' Creates a BoundingBoxAnnotation from a detected object.

        Args:
            detection: the detected object
            color: the color of the annotation
        '''
        name = detection.class_name or str(detection.class_id)
        return BoundingBoxAnnotation(
            rectangle=detection.box,
            top_label=f'{name}: {detection.score:.2%}',
            color=color
        )

    @staticmethod
    def from_tracked_object(
        tracked_object: TrackedObject,
        color: Optional[Color]=None,
        brightness: float=1.0
    ):
        ''' Creates a BoundingBoxAnnotation from a tracked object.

        Args:
            detection: the detected object
            color: the color of the annotation. If not specified, a pseudo-random color will be
                generated based on the track_id of the tracked object.
            brightness: if the color is generated, changes the luminosity of the color.
        '''
        name = tracked_object.class_name or str(tracked_object.class_id)
        if color is None:
            color = Color.from_id(tracked_object.track_id).brightness(brightness)
        return BoundingBoxAnnotation(
            rectangle=tracked_object.box,
            top_label=f'{name}: {tracked_object.score:.2%}',
            bottom_label=f'id: {tracked_object.track_id}',
            color=color
        )


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
            elif isinstance(anno, PolyLineAnnotation):
                self.add_polyline(anno, context)
            elif isinstance(anno, BoundingBoxAnnotation):
                self.add_bounding_box(anno, context)
            else:
                raise ValueError(f'Unknown annotation type: {type(anno)}')
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

    @abstractmethod
    def add_polyline(self, polyline: PolyLineAnnotation, context: Any) -> None:
        ''' Renders a polyline.

        Args:
            polyline: A polyline annotation.
            context: A backend-specific context object that was passed to the :meth:`render` method.
        '''

    def add_bounding_box(self, bounding_box: BoundingBoxAnnotation, context: Any) -> None:
        ''' Renders a bounding box.

        Args:
            bounding_box: A bounding box annotation.
            context: A backend-specific context object that was passed to the :meth:`render` method.
        '''
        rect = bounding_box.rectangle
        annos = [RectAnnotation(rect=rect, color=bounding_box.color)]
        if bounding_box.top_label:
            annos.append(
                LabelAnnotation(
                    point=rect.pt_min,
                    text=bounding_box.top_label,
                    color=bounding_box.color,
                    horizontal_anchor=LabelAnnotation.HorizontalAnchor.LEFT,
                    vertical_anchor=LabelAnnotation.VerticalAnchor.BOTTOM
                )
            )
        if bounding_box.bottom_label:
            annos.append(
                LabelAnnotation(
                    point=Point(rect.pt_min.x, rect.pt_max.y),
                    text=bounding_box.bottom_label,
                    color=bounding_box.color,
                    horizontal_anchor=LabelAnnotation.HorizontalAnchor.LEFT,
                    vertical_anchor=LabelAnnotation.VerticalAnchor.TOP
                )
            )
        self.render(annos, context)


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

    def add_rect(self, rect_anno: RectAnnotation, context: 'panoramasdk.media') -> None:
        x1, y1 = rect_anno.rect.pt_min
        x2, y2 = rect_anno.rect.pt_max
        context.add_rect(float(x1), float(y1), float(x2), float(y2))

    def add_label(self, label: LabelAnnotation, context: 'panoramasdk.media') -> None:
        x, y = label.point
        context.add_label(label.text, x, y)

    def add_marker(self, marker: MarkerAnnotation, context: 'panoramasdk.media') -> None:
        marker_str = PanoramaMediaAnnotationDriver.MARKER_STYLE_TO_STR.get(marker.style, '.')
        x, y = marker.point
        context.add_label(marker_str, x, y)

    def add_line(self, label: LineAnnotation, context: Any) -> None:
        print( # pragma: no cover
            'WARNING: PanoramaMediaAnnotationDriver.add_line is not implemented'
        )

    def add_polyline(self, polyline: PolyLineAnnotation, context: Any) -> None:
        print( # pragma: no cover
            'WARNING: PanoramaMediaAnnotationDriver.add_line is not implemented'
        )


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

    def draw_transparent(self,
        alpha: float,
        context: np.ndarray,
        drawer: Callable[[np.ndarray], None]
    ) -> None:
        ''' Semi-transparent drawing.

        Args:
            alpha: The transparency factor. Set 0 for opaque drawing, 1 for complete transparency.
            context: The drawing context.
            drawer: A callable that will draw an opaque drawing on the passed-in context. This
                method will make this drawing semi-transparent and render it on the context.
        '''
        if alpha == 1.0:
            drawer(context)
        elif alpha == 0.0:
            return
        else:
            overlay = context.copy()
            drawer(overlay)
            result = cv2.addWeighted(overlay, alpha, context, 1 - alpha, 0)
            np.copyto(context, result)

    @staticmethod
    def scale(point: Any, context: np.ndarray) -> Tuple[float, float]:
        ''' Converts and scales a point instance to an image context '''
        x, y = Point.from_value(point)
        return (int(x * context.shape[1]), int(y * context.shape[0]))

    @staticmethod
    def _color_to_cv2(color: Color) -> Tuple[int, int, int]:
        return (color.b, color.g, color.r)

    def add_rect(self, anno: RectAnnotation, context: np.ndarray) -> None:
        color = anno.color or OpenCVImageAnnotationDriver.DEFAULT_COLOR
        drawer = lambda context: \
            cv2.rectangle(
                img=context,
                pt1=OpenCVImageAnnotationDriver.scale(anno.rect.pt_min, context),
                pt2=OpenCVImageAnnotationDriver.scale(anno.rect.pt_max, context),
                color=OpenCVImageAnnotationDriver._color_to_cv2(color),
                thickness=OpenCVImageAnnotationDriver.DEFAULT_LINEWIDTH
            )
        self.draw_transparent(color.alpha, context, drawer)


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
            shift_y = size_y + padding_y
        elif vertical_anchor == LabelAnnotation.VerticalAnchor.BASELINE:
            shift_y = baseline
        return (int(shift_x), int(shift_y))

    def add_label(self, anno: LabelAnnotation, context: np.ndarray) -> None:
        ctx_height = context.shape[0]
        scale = ctx_height / OpenCVImageAnnotationDriver.IMG_HEIGHT_FOR_UNIT_FONT_SCALE * anno.size
        thickness = max(int(scale), 1)
        font = OpenCVImageAnnotationDriver.DEFAULT_FONT
        x, y = OpenCVImageAnnotationDriver.scale(anno.point, context)
        color = anno.color or OpenCVImageAnnotationDriver.DEFAULT_COLOR
        if (anno.horizontal_anchor != LabelAnnotation.HorizontalAnchor.LEFT or
            anno.vertical_anchor != LabelAnnotation.VerticalAnchor.BOTTOM):
            (size_x, size_y), baseline = cv2.getTextSize(
                text=anno.text, fontFace=font, fontScale=scale, thickness=thickness
            )
            shift_x, shift_y = OpenCVImageAnnotationDriver._get_anchor_shift(
                anno.horizontal_anchor,
                anno.vertical_anchor,
                size_x, size_y, baseline
            )
            x += shift_x
            y += shift_y

        drawer = lambda context: \
            cv2.putText(
                img=context,
                text=anno.text,
                org=(x, y),
                fontFace=font,
                fontScale=scale,
                color=OpenCVImageAnnotationDriver._color_to_cv2(color),
                thickness=thickness
            )
        self.draw_transparent(color.alpha, context, drawer)

    def add_marker(self, anno: MarkerAnnotation, context: np.ndarray) -> None:
        markerType = OpenCVImageAnnotationDriver.MARKER_STYLE_TO_CV2.get(
            anno.style, cv2.MARKER_DIAMOND
        )
        color = anno.color or OpenCVImageAnnotationDriver.DEFAULT_COLOR
        drawer = lambda context: \
            cv2.drawMarker(
                img=context,
                position=OpenCVImageAnnotationDriver.scale(anno.point, context),
                color=OpenCVImageAnnotationDriver._color_to_cv2(color),
                markerType=markerType
            )
        self.draw_transparent(color.alpha, context, drawer)

    def add_line(self, anno: LineAnnotation, context: Any) -> None:
        color = anno.color or OpenCVImageAnnotationDriver.DEFAULT_COLOR
        drawer = lambda context: \
            cv2.line(
                img=context,
                pt1=OpenCVImageAnnotationDriver.scale(anno.line.pt1, context),
                pt2=OpenCVImageAnnotationDriver.scale(anno.line.pt2, context),
                color=OpenCVImageAnnotationDriver._color_to_cv2(color),
                thickness=anno.thickness
            )
        self.draw_transparent(color.alpha, context, drawer)

    def add_polyline(self, anno: PolyLineAnnotation, context: Any) -> None:
        pts = [OpenCVImageAnnotationDriver.scale(pt, context) for pt in anno.polyline.points]
        pts = [np.array(pts, dtype=np.int32)]
        if anno.fill_color is not None:
            fill_color = OpenCVImageAnnotationDriver._color_to_cv2(anno.fill_color)
            if anno.polyline.is_convex:
                drawer = lambda context: \
                    cv2.fillConvexPoly(img=context, points=pts[0], color=fill_color)
            else:
                drawer = lambda context: \
                    cv2.fillPoly(img=context, pts=pts, color=fill_color)
            self.draw_transparent(anno.fill_color.alpha, context, drawer)

        color = anno.color or OpenCVImageAnnotationDriver.DEFAULT_COLOR
        drawer = lambda context: \
            cv2.polylines(
                img=context,
                pts=pts,
                isClosed=anno.polyline.closed,
                color=OpenCVImageAnnotationDriver._color_to_cv2(color),
                thickness=anno.thickness
            )
        self.draw_transparent(color.alpha, context, drawer)
