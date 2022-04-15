.. _annotation-api:

annotation
==========

.. automodule:: backpack.annotation

Annotation types
----------------

.. autoclass:: backpack.annotation.LabelAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.RectAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.TimestampAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.Point
   :members:
   :show-inheritance:

Annotation driver API
---------------------

:class:`~backpack.annotation.AnnotationDriverBase` specifies the unified API to draw annotation
on different backends.

.. autoclass:: backpack.annotation.AnnotationDriverBase
   :members:
   :show-inheritance:

Annotation driver implementations
---------------------------------

Currently, annotations can be drawn on panoramasdk.media and OpenCV images.

.. autoclass:: backpack.annotation.PanoramaMediaAnnotationDriver
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.OpenCVImageAnnotationDriver
   :members:
   :show-inheritance:
