from typing import Any
import multiprocessing

import gi

gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GLib, Gst, GstRtspServer

from .spyglass import SpyGlass

class RTSPServer(multiprocessing.Process):

    # TODO: this should be a singleton among all RTSPSpyGlasses

    def __init__(self, port: str) -> None:
        super().__init__(name='RTSPSpyGlassServerProcess')
        self._port = port
        self.gst_server = GstRtspServer.RTSPServer()
        self.gst_server.service = port
        self.streams = {}
        self.gst_server.attach()
        self.loop = None

    def add_stream(self, mount_point: str, pipeline: str) -> None:
        mounts = self.gst_server.get_mount_points()
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch(pipeline)
        factory.set_shared(True)
        mounts.add_factory(mount_point, factory)
        self.streams[mount_point] = pipeline

    def remove_stream(self, mount_point: str) -> None:
        mounts = self.gst_server.get_mount_points()
        mounts.remove_factory(mount_point)
        del self.streams[mount_point]

    def run(self):
        self.loop = GLib.MainLoop()
        self.loop.run()

    @property
    def port(self) -> str:
        return self._port

    def __repr__(self) -> str:
        streams_repr = [f'rtsp://127.0.0.1:{self.port}{mp}' for mp in self.streams.keys()]
        return f'<{self.__class__.__name__} streams=[{", ".join(streams_repr)}]>'



class RTSPSpyGlass(SpyGlass):

    LOCALHOST = '127.0.0.1'
    last_loopback_port = 5000

    def __init__(self, port: str, path: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server = RTSPServer(port)
        self.path = path
        self.loopback_port = RTSPSpyGlass.last_loopback_port
        RTSPSpyGlass.last_loopback_port += 1

    def _get_pipeline(self, fps: float, width: int, height: int) -> str:
        return ' ! '.join([
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

    def _try_open_stream(self, fps, width, height):
        success = super()._try_open_stream(fps, width, height)
        if success:
            server_pipeline = self._get_server_pipeline()
            self.server.add_stream(self.path, server_pipeline)
            self.server.start()
        return success
