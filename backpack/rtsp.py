'''
This module contains RTSPSkyLine and RTSPServer. These two classes allow serving a sequence of
OpenCV images as video streams using the RTSP protocol.

To use this class you MUST have the following dependencies correctly configured on your system:

 - `GStreamer 1.0`_ installed with standard plugins pack, libav, tools and development libraries
 - `OpenCV 4.2.0`_, compiled with GStreamer support and Python bindings
 - `gst-rtsp-server`_ with development libraries (libgstrtspserver-1.0-dev)

These dependencies can not be easily specified by a ``requirements.txt`` or a Conda environment.
See the example ``Dockerfile`` on how to install these dependencies on your system.

.. _`GStreamer 1.0`: https://gstreamer.freedesktop.org
.. _`OpenCV 4.2.0`: https://opencv.org/opencv-4-2-0/
.. _`gst-rtsp-server`: https://github.com/GStreamer/gst-rtsp-server
'''

from typing import Any, Optional, List
import threading
import logging

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GLib, GstRtspServer

from .skyline import SkyLine

class RTSPServer:
    ''' The :class:`RTSPServer` instance wraps a GStreamer RTSP server that serves video streams
    to clients using the RTSP protocol.

    You typically want to have a single instance of :class:`RTSPServer` for your application.
    You can register any number of video streams that will be served by a single instance of
    RTSP server. The port number of the server should be unique among all applications on the
    device.

    For an example usage of :class:`RTSPServer`, see the documentation of :class:`RTSPSkyLine`
    class.

    Args:
        port: The port to listen on. You can not modify the port after the initialization of
            the :class:`RTSPServer` instance. Defaults to ``8554``.
        parent_logger: If you want to connect the logger of :class:`RTSPServer` to a parent,
            specify it here.
    '''

    def __init__(
        self,
        port: str = '8554',
        parent_logger: Optional[logging.Logger] = None,
    ):
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
        self.gst_server = GstRtspServer.RTSPServer()
        self.gst_server.service = port
        self.streams = {}
        self._port = port
        self._loop = GLib.MainLoop()
        self._thread = None

    def add_stream(self, mount_point: str, pipeline: str) -> None:
        ''' Registers a new video stream to the server.

        Args:
            mount_point: The path that will be used to access the stream. For example,
                if you specify ``/my_stream``, the stream will be accessible for clients using
                the ``rtsp://127.0.0.1:8854/mystream`` url (change the IP address and the port
                number accordingly).
            pipeline: The GStreamer pipeline to use for the stream. This will be typically
                a pipeline picking up the raw UDP packets from a local port and wrapping it to a
                H.264 envelope, for example:
                ``udpsrc port=5000 ! application/x-rtp,media=video,encoding-name=H264 ! rtph264depay !
                rtph264pay name=pay0``
        '''
        self.logger.info('Adding pipeline to mount point "%s"', mount_point)
        mounts = self.gst_server.get_mount_points()
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(pipeline)
        factory.set_shared(True)
        mounts.add_factory(mount_point, factory)
        self.streams[mount_point] = pipeline

    def remove_stream(self, mount_point: str) -> None:
        ''' It removes a registered stream from the server.

        Args:
            mount_point (str): The registered path of the stream.
        '''
        mounts = self.gst_server.get_mount_points()
        mounts.remove_factory(mount_point)
        del self.streams[mount_point]

    def start(self):
        ''' Starts the RTSP server asynchronously.

        After calling this method, the RTSP requests will be served.
        '''
        self.logger.info('Starting RTSPServer')
        self.gst_server.attach()
        self._thread = threading.Thread(
            name='RTSPServerThread',
            target=self._loop.run,
            daemon=True
        )
        self._thread.start()

    def stop(self):
        ''' Stops the RTSP server.

        After calling this method, no RTSP requests will be served. The server can be restarted
        later on calling the :meth:`start()` method.
        '''
        self._loop.quit()

    @property
    def port(self) -> str:
        ''' The port where this server listens to incoming connections. '''
        return self._port

    def urls(self) -> List[str]:
        ''' Returns the list of URLs where the server serves RTSP streams. '''
        return [f'rtsp://127.0.0.1:{self.port}{mp}' for mp in self.streams.keys()]

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__} streams=[{", ".join(self.urls())}]>'



class RTSPSkyLine(SkyLine):
    ''' Together with :class:`RTSPServer`, :class:`RTSPSkyLine` a sequence of OpenCV frames
    on the RTSP protocol.

    A single instance of :class:`RTSPServer` application can serve streams coming from multiple
    :class:`RTSPSkyLine` instances. You should instantiate the :class:`RTSPServer` instance first.
    For example, if you want to serve two separate RTSP streams, you could use this code to set up
    your scenario::

        server = RTSPServer(port="8554")
        skyline1 = RTSPSkyLine(server, "/stream1")
        skyline2 = RTSPSkyLine(server, "/stream2")
        skyline1.start_streaming(30, 640, 480)
        skyline2.start_streaming(30, 640, 480)
        server.start()

        while True:
            frame1 = ... # Get frame for the first stream as a numpy array of shape (640, 480, 3)
            frame2 = ... # Get frame for the second stream
            skyline1.put(frame1)
            skyline2.put(frame2)

    Using this code, you can access the streams at the following URLs:

        - ``rtsp://127.0.0.1:8554/stream1``
        - ``rtsp://127.0.0.1:8554/stream2``

    If the application (or the firewall) is configured to allow incoming connections on the ``8554``
    port, the streams will be accessibly also from the external ip of the device.

    Args:
        server: The RTSPServer instance that this stream is being served by
        path: The path to the stream. This is the path that the client will use to connect to
            the stream
        args: Positional arguments to be passed to :class:`~backpack.skyline.SkyLine`
            superclass initializer.
        kwargs: Keyword arguments to be passed to :class:`~backpack.skyline.SkyLine`
            superclass initializer.
    '''

    LOCALHOST = '127.0.0.1'
    last_loopback_port = 5000

    def __init__(self, server: RTSPServer, path: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server = server
        self.path = path if path.startswith('/') else '/' + path
        self.loopback_port = RTSPSkyLine.last_loopback_port
        RTSPSkyLine.last_loopback_port += 1
        self.server.add_stream(self.path, self._get_server_pipeline())

    def _get_pipeline(self, fps: float, width: int, height: int) -> str:
        pipeline = ' ! '.join([
            'appsrc',
            'queue',
            'videoconvert',
            f'video/x-raw,format=I420,width={width},height={height},framerate={fps}/1',
            'x264enc bframes=0 key-int-max=45 bitrate=500',
            'video/x-h264,stream-format=avc,alignment=au,profile=baseline',
            'h264parse',
            'rtph264pay',
            f'udpsink host={self.LOCALHOST} port={self.loopback_port}'
        ])
        self.logger.info(f'GStreamer application pipeline definition:\n{pipeline}')
        return pipeline

    def _get_server_pipeline(self):
        pipeline = ' ! '.join([
            f'udpsrc port={self.loopback_port}',
            'application/x-rtp,media=video,encoding-name=H264',
            'rtph264depay',
            'rtph264pay name=pay0'
        ])
        self.logger.info(f'GStreamer RTSP server pipeline definition:\n{pipeline}')
        return pipeline
