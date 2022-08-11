from typing import Callable, Tuple, Any

try:
    import cv2
except ImportError as e:
    raise ImportError(
        'In order to use OpenCVImageAnnotationDriver you should have the optional dependency '
        'OpenCV installed. You can install it with: pip install "panorama-backpack[opencv]"'
    )

import numpy as np

from ..geometry import Point
from .driver import AnnotationDriverBase
from .annotation import (
    MarkerAnnotation, RectAnnotation, LabelAnnotation, LineAnnotation, PolyLineAnnotation
)
from .color import Color

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
