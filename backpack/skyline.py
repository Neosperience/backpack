''' :class:`SkyLine` streams OpenCV frames to a `GStreamer`_ pipeline.

:class:`SkyLine` itself is an abstract base class that you can not instantiate directly. Instead,
use one of the subclasses derived from :class:`SkyLine` that provide concrete implementation.
For example, :class:`~backpack.kvs.KVSSkyLine` sends frames to AWS Kinesis Video Streams service,
and :class:`~backpack.rtsp.RTSPSkyLine` streams your frames with a built-in RTSP server.

.. _`GStreamer`: https://gstreamer.freedesktop.org
'''

import os
import subprocess
import logging
from collections import OrderedDict
import datetime
from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod

try:
    import cv2
except ImportError as e:
    raise ImportError(
        'OpenCV installation is not found. You must manually install OpenCV with GStreamer '
        'support to use SkyLine. Please refer to installation instructions for details.'
    ) from e

from dotenv import find_dotenv, dotenv_values

from .timepiece import Ticker

USE_LAST_VALUE = -999
''' Using this value for dynamic streaming attributes like fps, width and height
will cause to use the values from the last streaming session. '''

class SkyLine(ABC):

    ''' Abstract base class for sending OpenCV frames to a remote service using GStreamer.

    :class:`SkyLine` can be used to create programmatically a video stream and send it to
    an external video ingestion service supported by GStreamer. Once the :class:`SkyLine`
    instances is configured and the streaming pipeline was opened by calling
    :meth:`start_streaming`, successive frames can be passed to the :meth:`put` method of the
    instance in OpenCV image format (:class:`numpy.ndarray` with a shape of ``(height, width, 3)``,
    BGR channel order, :class:`numpy.uint8` type).

    The frequency of frames (frames per second) as well as the image
    dimensions (width, height) are static during the streaming. You can either
    specify these properties upfront in the constructor, or let SkyLine figure out
    these values. In the later case, up to :attr:`FPS_METER_WARMUP_FRAMES`
    frames (by default 100) will be discarded at the beginning of the streaming
    and during this period the value of the stream fps, width and height will
    be determined automatically. In all cases you are expected to call the :meth:`put`
    method with the frequency of the :attr:`video_fps` property, and send images
    of (:attr:`video_width`, :attr:`video_height`) size.

    You should also specify ``GST_PLUGIN_PATH`` variable to the folder
    where the kvssink plugin binaries were built, and add the open-source
    dependency folder of kvssink to the ``LD_LIBRARY_PATH`` variable.
    You can define these variables as environment variables, or in a file
    called ``.env`` in the same folder where this file can be found.

    Args:
        parent_logger: If you want to connect the logger of KVS to a parent,
            specify it here.
        gst_log_file: If you want to redirect GStreamer logs to a file, specify
            the full path of the file in this parameter.
        gst_log_level: If you want to override GStreamer log level configuration,
            specify in this parameter.
        dotenv_path: The path of the .env configuration file. If left to None,
            SkyLine will use the default search mechanism of the python-dotenv library
            to search for the .env file (searching in the current and parent folders).

    Attributes:
        video_width (int): The width of the frames in the video stream.
        video_height (int): The height of the frames in the video stream.
        video_fps (float): The number of frames per second sent to the video stream.
        logger (logging.Logger): The logger instance.
    '''

    # pylint: disable=too-many-instance-attributes
    # We could group the stream parameters like fps, width and height into a structure, but why?

    _FRAME_LOG_FREQUENCY = datetime.timedelta(seconds=60)

    # Wait for so many put() requests before starting streaming.
    # During this period the average FPS will be measured and the
    # stream will be initialized with this FPS
    FPS_METER_WARMUP_FRAMES = 100

    class State(Enum):
        ''' States of the :class:`SkyLine`.

        Attributes:
            STOPPED: The :class:`SkyLine` instance is stopped.
            START_WARMUP: The :class:`SkyLine` instance is about to start the warmup period.
            WARMUP: The :class:`SkyLine` instance is measuring frame rate and frame size during
                the warmup period.
            STREAMING: The :class:`SkyLine` instance is streaming. The
                :meth:`~SkyLine.put` method should be called regularly.
            ERROR: The :class:`SkyLine` instance is encountered an error.
        '''
        STOPPED = 0
        START_WARMUP = 1
        WARMUP = 2
        STREAMING = 3
        ERROR = -1

    def __init__(self,
        parent_logger: Optional[logging.Logger] = None,
        gst_log_file: Optional[str] = None,
        gst_log_level: Optional[str] = None,
        dotenv_path: Optional[str] = None
    ):
        self.video_width = None
        self.video_height = None
        self.video_fps = None
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
        if gst_log_file is not None:
            os.environ['GST_DEBUG_FILE'] = gst_log_file
        if gst_log_level is not None:
            os.environ['GST_DEBUG'] = gst_log_level
        self._config_env(dotenv_path)
        self._check_env()
        self._last_log = datetime.datetime.min
        self._fps_meter_warmup_cnt = 0
        self._fps_meter_ticker = Ticker(self.FPS_METER_WARMUP_FRAMES + 1)
        self._last_fps = None
        self._last_width = None
        self._last_height = None
        self._video_writer = None
        self.state = SkyLine.State.STOPPED

    def _check_gst_plugin(self, plugin_name: str) -> bool:
        ''' Checks if a given GStreamer plugin can be correctly loaded.

        Args:
            plugin_name (str): The name of the GStreamer plugin

        Returns:
            True if the plugin can be loaded by the GStreamer system.
        '''
        try:
            cmd = f'gst-inspect-1.0 {plugin_name} --plugin'
            env = os.environ.copy()
            env['GST_DEBUG'] = '0'
            subprocess.check_output(cmd.split(' '), stderr=subprocess.STDOUT, env=env)
            self.logger.info('"%s" returned no error', cmd)
            return True
        except subprocess.CalledProcessError as error:
            self.logger.warning(
                '"%s" returned error code=%d, output:\n%s',
                cmd, error.returncode, error.output.decode()
            )
            return False

    @abstractmethod
    def _get_pipeline(self, fps: float, width: int, height: int) -> str:
        ''' Returns to GStreamer pipeline definition.

        Implement this method in subclasses and return the GStreamer pipeline
        definition.'''

    def _put_frame(self, frame):
        size = (self.video_width, self.video_height)
        resized = cv2.resize(frame, size, interpolation=cv2.INTER_LINEAR)
        if not self._video_writer or not self._video_writer.isOpened():
            self._frame_log(lambda: self.logger.warning(
                'Tried to write to cv2.VideoWriter but it is not opened'
            ))
            return False
        self._video_writer.write(resized)
        return True

    def _config_env(self, dotenv_path=None):
        os.environ['GST_DEBUG_NO_COLOR'] = '1'
        dotenv_path = dotenv_path or find_dotenv()
        self.logger.info('Loading config variables from %s', dotenv_path)
        if not dotenv_path or not os.path.isfile(dotenv_path):
            self.logger.warning('dotenv configuration file was not found at path: %s', dotenv_path)
            return
        cfg = dotenv_values(dotenv_path=dotenv_path)
        self.logger.info('Loaded env config structure: %s', cfg)
        if 'GST_PLUGIN_PATH' in cfg:
            os.environ['GST_PLUGIN_PATH'] = cfg['GST_PLUGIN_PATH']
        path_elems = []
        if 'LD_LIBRARY_PATH' in os.environ:
            path_elems.extend(os.environ['LD_LIBRARY_PATH'].split(':'))
        if 'LD_LIBRARY_PATH' in cfg:
            path_elems.append(cfg['LD_LIBRARY_PATH'])
        path_elems = list(OrderedDict.fromkeys(path_elems)) # remove duplicates
        path = ':'.join(path_elems)
        path = path.replace('::', ':')
        os.environ['LD_LIBRARY_PATH'] = path
        if 'LD_PRELOAD' in cfg:
            os.environ['LD_PRELOAD'] = cfg['LD_PRELOAD']

    def _check_env(self):
        def _check_var(var_name, warn=True):
            val = os.environ.get(var_name)
            if val:
                self.logger.info('%s=%s', var_name, val)
            elif warn:
                self.logger.warning('%s environment variable is not defined', var_name)

        _check_var('GST_PLUGIN_PATH')
        _check_var('LD_LIBRARY_PATH')
        _check_var('GST_DEBUG', warn=False)
        _check_var('GST_DEBUG_FILE', warn=False)

        self.logger.info('Local time on host: %s', datetime.datetime.now().isoformat())
        self.logger.info('UTC time on host: %s', datetime.datetime.utcnow().isoformat())

    def _open_stream(self, fps, width, height):
        pipeline = self._get_pipeline(fps, width, height)
        self.logger.info('Opening streaming pipeline')
        self._video_writer = cv2.VideoWriter(
            pipeline, cv2.CAP_GSTREAMER, 0, fps, (width, height)
        )
        self.video_fps = fps
        self.video_width = width
        self.video_height = height
        self._last_fps = fps
        self._last_width = width
        self._last_height = height
        return self._video_writer.isOpened()

    def _close_stream(self):
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None

    def _frame_log(self, log_fn):
        now = datetime.datetime.now()
        if now - self._last_log > self._FRAME_LOG_FREQUENCY:
            log_fn()
            self._last_log = now

    def _start_warmup(self):
        self._fps_meter_ticker.reset()
        self._fps_meter_warmup_cnt = self.FPS_METER_WARMUP_FRAMES

    def _finish_warmup(self, frame):
        fps = self.video_fps or round(self._fps_meter_ticker.freq())
        width = self.video_width or frame.shape[1]
        height = self.video_height or frame.shape[0]
        return fps, width, height

    def _try_open_stream(self, fps, width, height):
        if not self._open_stream(fps, width, height):
            self.logger.warning('Could not open cv2.VideoWriter')
            self.state = SkyLine.State.ERROR
            return False
        self.state = SkyLine.State.STREAMING
        return True

    @property
    def state(self) -> 'SkyLine.State':
        ''' State of the SkyLine. '''
        return self._state

    @state.setter
    def state(self, state: 'SkyLine.State') -> None:
        ''' Set the state of the SkyLine. '''
        self.logger.info('state = %s', state)
        self._state = state

    # Events

    def start_streaming(
        self,
        fps: float = USE_LAST_VALUE,
        width: int = USE_LAST_VALUE,
        height: int = USE_LAST_VALUE
    ) -> None:
        ''' Start the streaming.

        After calling this method, you are expected to call the :meth:`put` method at
        regular intervals. The streaming can be stopped and restarted arbitrary times on
        the same :class:`SkyLine` instance.

        You should specify the desired frame rate and frame dimensions. Using :attr:`USE_LAST_VALUE`
        for any of theses attributes will use the value from the last streaming session. If no
        values are found (or the values are explicitly set to ``None``), a warmup session will be
        started.

        Args:
            fps: The declared frame per seconds of the video. Set this to ``None`` to determine
                this value automatically, or :attr:`USE_LAST_VALUE` to use the value from
                the last streaming session.
            width: The declared width of the video. Set this to ``None`` to determine
                this value automatically, or :attr:`USE_LAST_VALUE` to use the value from
                the last streaming session.
            height: The declared height of the video. Set this to ``None`` to determine
                this value automatically, or :attr:`USE_LAST_VALUE` to use the value from
                the last streaming session.
        '''
        self.video_fps = self._last_fps if fps == USE_LAST_VALUE else fps
        self.video_width = self._last_width if width == USE_LAST_VALUE else width
        self.video_height = self._last_height if width == USE_LAST_VALUE else height
        if self.state in [SkyLine.State.WARMUP, SkyLine.State.STREAMING]:
            self._close_stream()
        if any(p is None for p in (self.video_fps, self.video_width, self.video_height)):
            self.logger.info('Starting FPS meter warmup.')
            self.state = SkyLine.State.START_WARMUP
        else:
            self.logger.info('No FPS meter warmup needed.')
            self._try_open_stream(self.video_fps, self.video_width, self.video_height)

    def put(
        self,
        frame: 'numpy.ndarray',
    ) -> bool:
        ''' Put a frame to the video stream.

        Args:
            frame: A numpy array of ``(height, width, 3)`` shape and of :class:`numpy.uint8` type.

        Returns:
            ``True`` if the frame was effectively put on the downstream pipeline.
        '''

        if self.state == SkyLine.State.STOPPED:
            # Streamer paused
            return False

        if self.state == SkyLine.State.ERROR:
            self._frame_log(
                lambda: self.logger.warning(
                    '%s.put() was called in %s state', self.__class__.__name__, self.state
                )
            )
            return False

        if self.state == SkyLine.State.START_WARMUP:
            self._start_warmup()
            self.state = SkyLine.State.WARMUP
            return False

        if self.state == SkyLine.State.WARMUP:
            self._fps_meter_ticker.tick()
            self._fps_meter_warmup_cnt -= 1
            if self._fps_meter_warmup_cnt <= 0:
                fps, width, height = self._finish_warmup(frame)
                self.logger.info(
                    'Finished FPS meter warmup. Determined fps=%f, width=%d, height=%d',
                    fps, width, height
                )
                if self._try_open_stream(fps, width, height):
                    return self._put_frame(frame)

            return False

        if self.state == SkyLine.State.STREAMING:
            return self._put_frame(frame)

        # Should not arrive here
        assert False, f'Unhandled SkyLine state {self.state}' # pragma: no cover

    def stop_streaming(self) -> None:
        ''' Stops the streaming.

        Successive calls to :meth:`put` method will silently discard the frames.
        '''
        self._close_stream()
        self.state = SkyLine.State.STOPPED
