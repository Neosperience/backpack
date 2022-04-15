.. _spyglass-readme:

SpyGlass
--------

As you may know, the only official way to get visual feedback on the correct functionality of your
Panorama application is to physically connect a display to the HDMI port of the Panorama appliance.
When connected, the display will show the output video stream of a single application deployed on
the device. However, physically accessing the appliance is not always feasible. SpyGlass allows you
to re-stream the output video of your Panorama application to an external service, for example, to
`AWS Kinesis Video Streams`_. This can be very convenient to remotely monitor your application.

.. _`AWS Kinesis Video Streams`: 
   https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/what-is-kinesis-video.html

Warning notes about using SpyGlass
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Even if SpyGlass is a helpful tool, it might raise two concerns that you should consider
carefully. For the same reason, we discourage using SpyGlass in a production environment: it is
principally a development aid or, at most, a debugging tool. 

The first concern is technical. Currently, the application code in a Panorama app does not
have direct access to the onboard GPU thus all video encoding codecs used by SpyGlass run on the
CPU of the device. This could take precious computing time from the CPUs that occupy with streaming
the output instead of processing the video. We measured that streaming a single output stream with
SpyGlass could require anything between 10-30% of the CPU capacity of the device. 

The second concern regards data protection. The Panorama appliance is designed so to strongly
protect the video streams being processed: it has even two ethernet interfaces to physically
separate the network of the video cameras (typically a closed-circuit local area network) and the
Internet access of the device. Using SpyGlass you might effectively relay the video stream from the
protected, closed-circuit camera network to the public Internet. For this reason, you should
carefully examine the data protection requirements of your application and the camera network 
before integrating SpyGlass.

How does it work?
^^^^^^^^^^^^^^^^^

Technically speaking, SpyGlass instantiates a `GStreamer pipeline`_ with an `appsrc`_ element at the
head. An OpenCV  `VideoWriter`_ is configured to write to the `appsrc`_ element: instead of saving
the consecutive frames to a video file, it streams to the output sink. 

When opening the `VideoWriter`_ instance, the user should specify the frame width and height, as
well as the frame rate of the output stream. You can manually specify these parameters or let
SpyGlass infer these values from the input dimensions and the frequency you send new frames to it.
If using this auto-configuration feature, some frames (by default 100) will be discarded at the
beginning of the streaming, as they will be used to calculate statistics of the frame rate and
measure the frame dimensions. This phase is referred to as the "warmup" state of SpyGlass. If later
on, you send frames of different dimensions compared to the expected width and height, SpyGlass will
redimension the input, but this has a performance penalty of the pipeline. You are also expected to
send new frames to SpyGlass with the frequency specified in the frame-per-second parameter. If you
send frames slower or faster, the KVS video fragments get out of sync and you won't be able to play
back the video continuously.

.. _`GStreamer pipeline`: 
   https://gstreamer.freedesktop.org/documentation/application-development/introduction/basics.html
.. _`appsrc`: https://gstreamer.freedesktop.org/documentation/app/appsrc.html
.. _`VideoWriter`: https://docs.opencv.org/4.5.5/dd/d43/tutorial_py_video_display.html

Configuring the Panorama Application Docker container
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

SpyGlass
~~~~~~~~

SpyGlass depends on a set of custom compiled external libraries. You should have all these libraries
compiled and configured correctly in your application's docker container in order to make SpyGlass
work correctly. These libraries include:

 - ``GStreamer 1.0`` installed with standard plugins pack, libav, tools, and development libraries
 - ``OpenCV 4.2.0``, compiled with GStreamer support and Python bindings
 - ``numpy`` (it is typically installed by the base docker image of your Panorama application)

The following snippet shows how to configure your ``Dockerfile`` to install these libraries:

.. code-block:: docker

  FROM public.ecr.aws/panorama/panorama-application
  ENV DEBIAN_FRONTEND=noninteractive

  # Install build tools and gstreamer
  RUN apt-get update -y && \
      apt-get install -y libgstreamer1.0-0 \
              build-essential cmake m4 git \
              pkg-config python3.7-dev \
              gstreamer1.0-plugins-base \
              gstreamer1.0-plugins-good \
              gstreamer1.0-plugins-bad \
              gstreamer1.0-plugins-ugly \
              gstreamer1.0-libav \
              gstreamer1.0-doc \
              gstreamer1.0-tools \
              libgstreamer1.0-dev \
              libgstreamer-plugins-base1.0-dev \
              protobuf-compiler \
              libgtk2.0-dev \
              ocl-icd-opencl-dev \
              libgirepository1.0-dev

  # Install GLib python bindings
  RUN python3 -m pip install PyGObject --ignore-installed

  # Fix GLib libraries path and numpy includes path
  RUN ln -s $(python3 -c "import numpy as np; print(np.__path__[0])")/core/include/numpy /usr/include/numpy

  # Clone OpenCV repo
  RUN mkdir -p /opt && \
      git clone https://github.com/opencv/opencv.git --branch 4.2.0 /opt/opencv
  WORKDIR /opt/opencv

  # Build OpenCV
  RUN mkdir -p /opt/opencv/build
  WORKDIR /opt/opencv/build
  ENV PYTHON_EXECUTABLE=/usr/bin/python3
  RUN PYTHON3_INCLUDE_DIR=$(python3 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") && \
      PYTHON3_PACKAGES_PATH=$(python3 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") && \
      mkdir -p $PYTHON3_INCLUDE_DIR && \
      mkdir -p $PYTHON3_PACKAGES_PATH && \
      cmake -D CMAKE_BUILD_TYPE=RELEASE \
          -D INSTALL_PYTHON_EXAMPLES=OFF \
          -D INSTALL_C_EXAMPLES=OFF \
          -D PYTHON2_EXECUTABLE=$(which python) \
          -D PYTHON_EXECUTABLE=$(which python3) \
          -D PYTHON3_EXECUTABLE=$(which python3) \
          -D PYTHON3_INCLUDE_DIR=$PYTHON3_INCLUDE_DIR \
          -D PYTHON3_PACKAGES_PATH=$PYTHON3_PACKAGES_PATH \
          -D PYTHON_DEFAULT_EXECUTABLE=$(which python3) \
          -D PYTHON3_LIBRARY=$PYTHON3_PACKAGES_PATH \
          -D BUILD_NEW_PYTHON_SUPPORT=ON \
          -D BUILD_opencv_python3=ON \
          -D HAVE_opencv_python3=ON \
          -D BUILD_opencv_python2=OFF \
          -D BUILD_TESTS=OFF \
          -D DBUILD_PERF_TESTS=OFF \
          -D CMAKE_INSTALL_PREFIX=$(python3 -c "import sys; print(sys.prefix)") \
          -D WITH_GSTREAMER=ON \
          -D BUILD_EXAMPLES=OFF \
          -D WITH_GTK=OFF \
          ..
  RUN make -j $(($(nproc) <= 4 ? $(nproc) : 4))

  # Install OpenCV
  RUN make install
  RUN ldconfig

  ENV LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1
  ENV PYTHONPATH=/usr/lib/python3.7/site-packages

  # GLib libraries for python 3.7
  RUN ln -s /usr/lib/python3/dist-packages/gi/_gi.cpython-{36m,37m}-$(uname -m)-linux-gnu.so

  # Create GStreamer cache directory
  RUN mkdir -p /root/.cache/gstreamer-1.0/

  RUN mkdir -p /panorama

KVSSpyGlass
~~~~~~~~~~~

Furthermore, if you want to use :class:`~backpack.kvs.KVSSpyGlass`, the
:class:`backpack.spyglass.SpyGlass` implementation that streams the video to Kinesis Video Streams,
you will need also the following libraries and configurations:

 - Amazon Kinesis Video Streams (KVS) Producer SDK compiled with GStreamer plugin support
 - Environment variable ``GST_PLUGIN_PATH`` configured to point to the directory where the compiled
   binaries of KVS Producer SDK GStreamer plugin is placed
 - Environment variable ``LD_LIBRARY_PATH`` including the open-source third-party dependencies
   compiled by KVS Producer SDK
 - boto3 (it is typically installed by the base docker image of your Panorama application)

You should add the following lines to the application's Dockerfile to install these libraries:

.. code-block:: docker

  # Download Kinesis Video Streams producer C++ SDK
  WORKDIR /opt
  RUN git clone https://github.com/awslabs/amazon-kinesis-video-streams-producer-sdk-cpp.git

  # Build KVS producer C++ SDK
  RUN mkdir -p /opt/amazon-kinesis-video-streams-producer-sdk-cpp/build
  WORKDIR /opt/amazon-kinesis-video-streams-producer-sdk-cpp/build
  RUN cmake -D BUILD_GSTREAMER_PLUGIN=ON \
      -D BUILD_TEST=FALSE \
      ..

  RUN make -j $(($(nproc) <= 4 ? $(nproc) : 4))

  ENV GST_PLUGIN_PATH=/opt/amazon-kinesis-video-streams-producer-sdk-cpp/build
  ENV LD_LIBRARY_PATH=/opt/amazon-kinesis-video-streams-producer-sdk-cpp/open-source/local/lib

  # for some reason, the GST_PLUGIN_PATH and LD_LIBRARY_PATH environment variables defined
  # above are not visible from within the container. We will replicate them in the
  # /panorama/.env file that will be read from application code.
  RUN echo "GST_PLUGIN_PATH=\"${GST_PLUGIN_PATH}\"\nLD_LIBRARY_PATH=\"${LD_LIBRARY_PATH}\"\n" > /panorama/.env

  # kvs log configuration example. Feel free to download and modify this file and copy your
  # custom version into the container
  RUN curl https://github.com/neosperience/backpack/raw/main/resources/kvs_log_configuration -o /kvs_log_configuration

RTSPSpyGlass
~~~~~~~~~~~~

If you wish to stream your video to an RTSP server using :class:`backpack.rtsp.RTSPSpyGlass`, in
addition to SpyGlass dependencies you will need:

- `gst-rtsp-server`_ with development libraries (libgstrtspserver-1.0-dev)

.. _`gst-rtsp-server`: https://github.com/GStreamer/gst-rtsp-server

This ``Dockerfile`` snippet will install this library correctly:

.. code-block:: docker

  # Install gst-rtsp-server
  RUN apt-get install -y libgstrtspserver-1.0-dev

We provide a sample Dockerfile in the examples folder that shows you how to install correctly these
libraries in your Docker container. In most cases, it should be enough to copy the relevant sections
from the sample to your application's Dockerfile. The first time you compile the docker container,
it might take up to one hour to correctly compile all libraries.

Usage
^^^^^

KVSSpyGlass
~~~~~~~~~~~

Compared to the :class:`~backpack.spyglass.SpyGlass` base class, :class:`~backpack.kvs.KVSSpyGlass`
adds an additional element to the pipeline: the `Amazon Kinesis Video Streams Producer Library`_,
wrapped in a GStreamer sink element. KVS Producer needs AWS credentials to function correctly: it
does not use automatically the credentials associated with the Panorama Application Role. You have
different options to provide credentials using :class:`~backpack.kvs.KVSCredentialsHandler`
subclasses, provided in the :mod:`~backpack.kvs` module. For testing purposes, you can `create an
IAM user`_ in your AWS account and `attach an IAM policy`_ to it that has the privileges only to the
following operations to write media to KVS: 
 
 - ``kinesisvideo:DescribeStream``
 - ``kinesisvideo:GetStreamingEndpoint``
 - ``kinesisvideo:PutMedia``

You should configure this user to have programmatic access to AWS resources, and get the AWS Access
Key and Secret Key pair of the user. These are so-called static credentials that do not expire. You
can create a :class:`~backpack.kvs.KVSInlineCredentialsHandler` or
:class:`~backpack.kvs.KVSEnvironmentCredentialsHandler` instance to pass these credentials to KVS
Producer Plugin directly in the GStreamer pipeline definition, or as environment variables. However
as these credentials do not expire, it is not recommended to use this setting in a production
environment. Even in a development and testing environment, you should take the appropriate security
measures to protect these credentials: never hard code them in the source code. Instead, use AWS
Secret Manager or a similar service to provision these parameters.

:class:`~backpack.kvs.KVSSpyGlass` can use also the Panorama Application Role to pass the
application's credentials to KVS Producer. These credentials are temporary, meaning that they expire
within a couple of hours, and they should be renewed. The Producer library expects temporary
credentials in a text file. :class:`~backpack.kvs.KVSFileCredentialsHandler` takes manages the
renewal of the credentials and periodically updates the text file with the new credentials. You
should always test your Panorama application - KVS integration that it still works when the
credentials are refreshed. This means letting run your application for several hours and
periodically checking if it still streams the video to KVS. You will also find diagnostic
information in the CloudWatch logs of your application when the credentials were renewed.

:class:`~backpack.kvs.KVSSpyGlass` needs also two correctly configured environment variables to make
GStreamer find the KVS Producer plugin. The name of these variables are ``GST_PLUGIN_PATH`` and
``LD_LIBRARY_PATH``. They point to the folder where the KVS Producer binary and its 3rd party
dependencies can be found. If you've used the example Dockerfile provided, the correct values of
these variables are written to a small configuration file at ``/panorama/.env``. You should pass the
path of this file to :class:`~backpack.kvs.KVSSpyGlass` or otherwise ensure that these variables
contain the correct value.

At instantiation time, you should pass at least the AWS region name where your stream is created,
the name of the stream, and a credentials handler instance. If you want to configure manually the
frame rate and the dimensions of the frames, you should also pass them here: if both are specified,
the warmup period will be skipped and your first frame will be sent directly to KVS. When you are
ready to send the frames, you should call the :meth:`~backpack.spyglass.SpyGlass.start_streaming`
method: this will open the GStreamer pipeline. After this method is called, you are expected to send
new frames to the stream calling the :meth:`~backpack.spyglass.SpyGlass.put` method periodically,
with the frequency of the frame rate specified, or inferred by :class:`~backpack.kvs.KVSSpyGlass`.
You can stop and restart streaming any number of times on the same
:class:`~backpack.kvs.KVSSpyGlass` instance.

.. _`Amazon Kinesis Video Streams Producer library`: 
   https://docs.aws.amazon.com/kinesisvideostreams/latest/dg/producer-sdk.html
.. _`create an IAM user`: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_users_create.html
.. _`attach an IAM policy`: 
   https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies_manage-edit.html

Example usage:

.. code-block:: python

  import panoramasdk
  from backpack.kvs import KVSSpyGlass, KVSFileCredentialsHandler

  # You might want to read these values from Panorama application parameters
  stream_region = 'us-east-1'
  stream_name = 'panorama-video'

  # The example Dockerfile writes static configuration variables to this file
  # If you change the .env file path in the Dockerfile, you should change it also here
  DOTENV_PATH = '/panorama/.env'

  class Application(panoramasdk.node):

      def __init__(self):
          super().__init__()
          # ...
          credentials_handler = KVSFileCredentialsHandler()
          self.spyglass = KVSSpyGlass(
              stream_region=stream_region,
              stream_name=stream_name,
              credentials_handler=credentials_handler,
              dotenv_path=DOTENV_PATH
          )
          # This call opens the streaming pipeline:
          self.spyglass.start_streaming()

      # called from video processing loop:
      def process_streams(self):
          streams = self.inputs.video_in.get()

          for idx, stream in enumerate(streams):
              
              # Process the stream, for example with:
              # self.process_media(stream)

              # TODO: eventually multiplex streams to a single frame
              if idx == 0:
                  self.spyglass.put(stream.image)

If everything worked well, you can watch the restreamed video in the `Kinesis Video Streams page`_
of the AWS console.

.. _`Kinesis Video Streams page`: https://console.aws.amazon.com/kinesisvideo/home

For more information, refer to the :ref:`spyglass-api`, :ref:`kvs-api` and the :ref:`rtsp-api`
module API documentation.

RTSPSpyGlass
~~~~~~~~~~~~

TBD
