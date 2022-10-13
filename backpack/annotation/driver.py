import logging
from .annotation import Annotation
from typing import Iterable, Optional, Any
from abc import ABC, abstractmethod

from ..geometry import Point
from .annotation import (
    MarkerAnnotation, RectAnnotation, LabelAnnotation, LineAnnotation, PolyLineAnnotation,
    BoundingBoxAnnotation
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

    def render(self,
        annotations: Iterable[Annotation],
        context: Any
    ) -> Any:
        ''' Renders a collection of annotations on a context.

        Args:
            annotations: An iterable collection of annotation type defined in this module.
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
