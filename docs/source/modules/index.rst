.. _modules:

Modules
-------

Backpack provides the following modules:

 - :ref:`autoidentity-readme` allows your application to learn more about itself and the host
   device. It gives access to the Panorama device id, application instance id, application name and
   description, and other similar information.
 - :ref:`timepiece-readme` is a collection of timing and profiling classes that allows you to efficiently
   measure the frame processing time of your app, time profile different stages of frame processing
   (preprocessing, model invocation, postprocessing), and send a selected subset of these metrics
   to AWS CloudWatch to monitor your application in real-time, and even create CloudWatch alarms
   if your app stops processing frames.
 - :ref:`skyline-readme` provides a framework to restream the processed video (annotated by
   your application) to media endpoints supported by `GStreamer`_. Two implementation of the
   abstract base class :class:`~backpack.skyline.SkyLine` is provided:

     - :class:`~backpack.kvs.KVSSkyLine` lets you send the processed video to `AWS Kinesis Video
       Streams`_ service
     - :class:`~backpack.rtsp.RTSPSkyLine` configures an RTSP server directly in your Panorama
       application. You can play back the video stream with an RTSP client (for example, with
       `VLC Media Player`_), directly from your workstation.

 - :ref:`annotation-readme` is a unified API for drawing on different backends like the core
   `panoramasdk.media`_ class or OpenCV images.
 - :ref:`geometry-readme` is a collection of classes representing 2D geometric primitives like
   points, lines, polylines, and some useful geometric algorithms.

.. _`AWS Kinesis Video Streams`: https://aws.amazon.com/kinesis/video-streams/
.. _`VLC Media Player`: https://www.videolan.org
.. _`panoramasdk.media`: https://github.com/awsdocs/aws-panorama-developer-guide/blob/main/resources/applicationsdk-reference.md#media
.. _`GStreamer`: https://gstreamer.freedesktop.org

.. toctree::
   :hidden:

   autoidentity
   timepiece
   skyline
   annotation
   geometry
