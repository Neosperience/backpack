.. _annotation-readme:

Annotations
-----------

*Annotations* and *annotation drivers* provide a unified way to draw annotations on different
rendering backends. Currently, two annotation drivers are implemented:

 - :class:`~backpack.annotation.PanoramaMediaAnnotationDriver` allows you to draw on
   `panoramasdk.media`_ object, and
 - :class:`~backpack.annotation.OpenCVImageAnnotationDriver` allows you to draw on an OpenCV image
   (numpy array) object.

Two types of annotations can be drawn: labels and rectangles. Not all annotation drivers necessarily
implement all features specified by annotations, for example, one driver might decide to ignore
colors.

.. _`panoramasdk.media`: https://github.com/awsdocs/aws-panorama-developer-guide/blob/main/resources/applicationsdk-reference.md#media


Using annotations
^^^^^^^^^^^^^^^^^

You can create one or more annotation driver instances at the beginning of the video frame
processing loop, depending on the available backends. During the process of a single frame, you are
expected to collect all annotations to be drawn on the frame in a python collection (for example, in
a ``list``). When the processing is finished, you can call the
:meth:`~backpack.annotation.AnnotationDriverBase.render` method on any number of drivers, passing
the same collection of annotations. All coordinates used in annotation are normalized to the range
of ``[0; 1)``.

Example usage:

.. code-block:: python

    import panoramasdk
    from backpack.annotation import (
        Point, LabelAnnotation, RectAnnotation, TimestampAnnotation,
        OpenCVImageAnnotationDriver, 
        PanoramaMediaAnnotationDriver
    )

    class Application(panoramasdk.node):

        def __init__(self):
            super().__init__()
            # self.spyglass = ... 
            self.panorama_driver = PanoramaMediaAnnotationDriver()
            self.cv2_driver = OpenCVImageAnnotationDriver()

        # called from video processing loop:
        def process_streams(self):
            streams = self.inputs.video_in.get()
            for idx, stream in enumerate(streams):
                annotations = [
                    TimestampAnnotation(),
                    RectAnnotation(point1=Point(0.1, 0.1), point2=Point(0.9, 0.9)),
                    LabelAnnotation(point=Point(0.5, 0.5), text='Hello World!')
                ]
                self.panorama_driver.render(annotations, stream)

                # TODO: eventually multiplex streams to a single frame
                if idx == 0:
                    rendered = self.cv2_driver.render(annotations, stream.image.copy())
                    # self.spyglass.put(rendered)

For more information, refer to the :ref:`annotation-api` API documentation.
