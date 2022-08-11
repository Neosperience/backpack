try:
    import panoramasdk
except ImportError as e:
    raise ImportError(
        'PanoramaMediaAnnotationDriver is supposed to be used only from a AWS Panorama SDK '
        'application, either on a Panorama device or using the test_utility.'
    ) from e

from .driver import AnnotationDriverBase

from .annotation import (
    MarkerAnnotation, RectAnnotation, LabelAnnotation, LineAnnotation, PolyLineAnnotation
)

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

    def add_line(self, label: LineAnnotation, context: 'panoramasdk.media') -> None:
        print( # pragma: no cover
            'WARNING: PanoramaMediaAnnotationDriver.add_line is not implemented'
        )

    def add_polyline(self, polyline: PolyLineAnnotation, context: 'panoramasdk.media') -> None:
        print( # pragma: no cover
            'WARNING: PanoramaMediaAnnotationDriver.add_line is not implemented'
        )
