''' This module makes it possible to draw annotations on different
backends with an unified API. Currently, you can draw rectangles and labels with
:mod:`~backpack.annotation` on ``panoramasdk.media`` and OpenCV images
(:class:`numpy arrays <numpy.ndarray>`).'''

from .annotation import (
    Annotation, LabelAnnotation, RectAnnotation, LineAnnotation, MarkerAnnotation,
    PolyLineAnnotation, TimestampAnnotation, BoundingBoxAnnotation
)

from .color import Color
