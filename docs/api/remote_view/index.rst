#######################################
Remote viewing the Panorama application
#######################################

Backpack contains classes that can stream the video output of your AWS Panorama application to 
remote services. These classes inherit from the abstract base class 
:class:`~backpack.spyglass.SpyGlass`.  


SpyGlass API
------------

API documentation for :class:`~backpack.spyglass.SpyGlass`:

.. toctree::
   :maxdepth: 2

   spyglass

SpyGlass implementations
------------------------

Currently, the following :class:`~backpack.spyglass.SpyGlass` implementations are available:

.. toctree::
   :maxdepth: 2

   kvs
   rtsp

Annotation API
--------------

Additionally, you can use the :mod:`~backpack.annotation` module to draw annotations on different
backends with an unified API. Currently, you can draw rectangles and labels with 
:mod:`~backpack.annotation` on ``panoramasdk.media`` and OpenCV images (numpy arrays). Refer
to the API documentation of :mod:`~backpack.annotation` for more details:

.. toctree::
   :maxdepth: 2

   annotation