.. _api:

API Documentation
-----------------

Backpack consists of several modules for getting information about execution environment, time
profiling your Panorama application, and remote view the output of your model.

 - :ref:`autoidentity-api` provides information about the application execution environmen
 - :ref:`timepiece-api` contains time-related utility methods for measuring code execution time and
   scheduling tasks in an external event loop.
 - :ref:`skyline-api` contains an abstract base class to stream OpenCV frames to a GStreamer
   pipeline

    - :ref:`kvs-api` is a concrete SkyLine implementation that streams the output of the AWS
      Panorama application to AWS Kinesis Video Streams service.
    - :ref:`rtsp-api` is another SkyLine implementation that serves a sequence of OpenCV images as
      video streams using the RTSP protocol

 - :ref:`annotation-api` makes it possible to draw annotations on different backends with an unified
   API
 - :ref:`geometry-api` contains 2D geometry primitives and implementation of some geometric
   algorithms
 - :ref:`config-api` provides a way to standardize the configuration of Panorama applications via
   deploy-time parameters

.. toctree::
    :hidden:

    autoidentity
    timepiece
    skyline
    kvs
    rtsp
    annotation
    geometry
    config

