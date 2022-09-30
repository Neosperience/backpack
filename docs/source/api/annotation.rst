.. _annotation-api:

annotation
==========

Colors
------

.. automodule:: backpack.annotation.color

Annotation types
----------------

.. autoclass:: backpack.annotation.LabelAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.RectAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.LineAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.MarkerAnnotation
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.TimestampAnnotation
   :members:
   :show-inheritance:

Annotation driver API
---------------------

:class:`~backpack.annotation.driver.AnnotationDriverBase` specifies the unified API to draw
annotation on different backends.

.. autoclass:: backpack.annotation.driver.AnnotationDriverBase
   :members:
   :show-inheritance:

Annotation driver implementations
---------------------------------

Currently, annotations can be drawn on panoramasdk.media and OpenCV images.

.. autoclass:: backpack.annotation.panorama.PanoramaMediaAnnotationDriver
   :members:
   :show-inheritance:

.. autoclass:: backpack.annotation.opencv.OpenCVImageAnnotationDriver
   :members:
   :show-inheritance:
