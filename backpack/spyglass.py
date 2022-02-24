''' SpyGlass can be used to send OpenCV frames to a GStreamer pipeline, and
annotation drivers unify the drawing API of different backends (for example,
OpenCV or panoramasdk.media). '''

import os
import time
import subprocess
import logging
from collections import OrderedDict
import datetime
from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod

import cv2
from dotenv import find_dotenv, dotenv_values

class SpyGlass(ABC):

    ''' Abstract base class for sending OpenCV frames to a remote service using GStreamer.

    SpyGlass can be used to create programatically a video stream and send it to
    an external video ingestion service supported by GStreamer. Once the SpyGlass
    instances is configured and the streaming pipeline was opened by calling
    `start_streaming`, successive frames can be passed to the `put` method of the
    instance in OpenCV image format (numpy arrays with a shape of `(height, width, 3)`,
    BGR channel order, `np.uint8` type).

    The frequency of frames (frames per second) as well as the image
    dimensions (width, heigth) are static during the streaming. You can either
    specify these properties upfront in the constructor, or let SpyGlass figure out
    these values. In the later case, up to `SpyGlass._FPS_METER_WARMUP_FRAMES`
    frames (by default 100) will be discarded at the begining of the streaming
    and during this period the value of the stream fps, width and height will
    be determined automatically. In all cases you are expected to call the `put`
    method with the frequency of the `video_fps` property, and send images
    of (`video_width`, `video_height`) size.

    You should also specify `GST_PLUGIN_PATH` variable to the folder
    where the kvssink plugin binaries were built, and add the open-source
    dependency folder of kvssink to the `LD_LIBRARY_PATH` variable.
    You can define these variables as environment variables, or in a file
    called `.env` in the same folder where this file can be found.

    :param video_width: The declared width of the video. Leave this to the default
        None to determine this value automatically.
    :param video_height: The declared heigth of the video. Leave this to the default
        None to determine this value automatically.
    :param video_fps: The declared frame per seconds of the video. Leave this to
        the default None to determine this value automatically.
    :param parent_logger: If you want to connect the logger of KVS to a parent,
        specify it here.
    :param gst_log_file: If you want to redirect GStreamer logs to a file, specify
        the full path of the file in this parameter.
    :param gst_log_level: If you want to override GStreamer log level configuration,
        specify in this parameter.
    :param dotenv_path: The path of the .env configuration file. If left to None,
        SpyGlass will use the default search mechanism of the python-dotenv library
        to search for the .env file (searching in the current and parent folders).
    '''

    _FRAME_LOG_FREQUENCY = datetime.timedelta(seconds=60)

    # Wait for so many put() requests before starting streaming.
    # During this period the avgerage FPS will be measured and the
    # stream will be initialized with this FPS
    _FPS_METER_WARMUP_FRAMES = 100

    class State(Enum):
        ''' States of the SpyGlass. '''
        STOPPED = 0
        START_WARMUP = 1
        WARMUP = 2
        STREAMING = 3
        ERROR = -1

    def __init__(self,
        video_width: Optional[int] = None,
        video_height: Optional[int] = None,
        video_fps: Optional[float] = None,
        parent_logger: Optional[logging.Logger] = None,
        gst_log_file: Optional[str] = None,
        gst_log_level: Optional[str] = None,
        dotenv_path: Optional[str] = None
    ):
        self.video_width = video_width
        self.video_height = video_height
        self.video_fps = video_fps
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
        self._fps_meter_start = None
        self._int_fps = 0.0
        self._int_width = 0
        self._int_height = 0
        self._video_writer = None
        self.state = SpyGlass.State.STOPPED

    def _check_gst_plugin(self, plugin_name: str) -> bool:
        ''' Checks if a given GStreamer plugin can be correctly loaded.

        :param plugin_name: The name of the GStreamer plugin
        :return: True if the plugin can be loaded by the GStreamer system.
        '''
        try:
            cmd = f'gst-inspect-1.0 {plugin_name} --plugin'
            env = os.environ.copy()
            env['GST_DEBUG'] = '0'
            subprocess.check_output(cmd.split(' '), stderr=subprocess.STDOUT, env=env)
            self.logger.info(f'"{cmd}" returned no error')
            return True
        except subprocess.CalledProcessError as error:
            self.logger.warning(
                f'"{cmd}" returned error code={error.returncode}, '
                f'output:\n{error.output.decode()}'
            )
            return False

    @abstractmethod
    def _get_pipeline(self, fps: float, width: int, height: int) -> str:
        ''' Returns to GStreamer pipeline definition.

        Implement this method in subclasses and return the GStreamer pipeline
        definition.'''
        raise NotImplementedError(
            'SpyGlass._get_pipeline() should be implemented in subclasses'
        )

    def _put_frame(self, frame):
        size = (self._int_width, self._int_height)
        resized = cv2.resize(frame, size, interpolation=cv2.INTER_LINEAR)
        if not self._video_writer or not self._video_writer.isOpened():
            self._frame_log(lambda: self.logger.warning(
                'Tried to write to cv2.VideoWriter but it is not opened'
            ))
            return False
        self._video_writer.write(resized)
        return True

    def _config_env(self, dotenv_path=None):
        dotenv_path = dotenv_path or find_dotenv()
        self.logger.info(f'Loading config variables from {dotenv_path}')
        if not dotenv_path or not os.path.isfile(dotenv_path):
            self.logger.warning(f'dotenv configuration file was not found at path: {dotenv_path}')
            return
        cfg = dotenv_values(dotenv_path=dotenv_path)
        self.logger.info(f'Loaded env config structure: {cfg}')
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
        os.environ['GST_DEBUG_NO_COLOR'] = '1'

    def _check_env(self):
        def _check_var(var_name, warn=True):
            val = os.environ.get(var_name)
            if val:
                self.logger.info(f'{var_name}={val}')
            elif warn:
                self.logger.warning(f'{var_name} environment variable is not defined')

        _check_var('GST_PLUGIN_PATH')
        _check_var('LD_LIBRARY_PATH')
        _check_var('GST_DEBUG', warn=False)
        _check_var('GST_DEBUG_FILE', warn=False)

        self.logger.info(f'Local time on host: {datetime.datetime.now().isoformat()}')
        self.logger.info(f'UTC time on host: {datetime.datetime.utcnow().isoformat()}')

    def _open_stream(self, fps, width, height):
        pipeline = self._get_pipeline(fps, width, height)
        self.logger.info('Opening streaming pipeline')
        self._video_writer = cv2.VideoWriter(
            pipeline, cv2.CAP_GSTREAMER, 0, fps, (width, height)
        )
        self._int_fps = fps
        self._int_width = width
        self._int_height = height
        return self._video_writer.isOpened()

    def _close_stream(self):
        self._video_writer.release()
        self._video_writer = None

    def _frame_log(self, log_fn):
        now = datetime.datetime.now()
        if now - self._last_log > self._FRAME_LOG_FREQUENCY:
            log_fn()
            self._last_log = now

    def _start_warmup(self):
        self._fps_meter_start = time.perf_counter()
        self._fps_meter_warmup_cnt = self._FPS_METER_WARMUP_FRAMES

    def _finish_warmup(self, frame):
        fps = round(self._FPS_METER_WARMUP_FRAMES / (time.perf_counter() - self._fps_meter_start))
        height, width = frame.shape[0], frame.shape[1]
        fps = fps if self.video_fps is None else self.video_fps
        width = width if self.video_width is None else self.video_width
        height = height if self.video_height is None else self.video_height
        return fps, width, height

    @property
    def state(self) -> 'SpyGlass.State':
        ''' State of the SpyGlass. '''
        return self._state

    @state.setter
    def state(self, state: 'SpyGlass.State') -> None:
        ''' Set the state of the SpyGlass. '''
        self.logger.info(f'state = {state}')
        self._state = state

    # Events

    def start_streaming(self) -> None:
        ''' Start the streaming.

        After calling this method, you are exepcted to call the `put` method at
        regular intervals. The streaming can be stopped and restarted arbitrary times on
        the same SpyGlass() instance.
        '''
        if self.state in [SpyGlass.State.WARMUP, SpyGlass.State.STREAMING]:
            self._close_stream()
        if any(p is None for p in (self.video_fps, self.video_width, self.video_height)):
            self.logger.info('Starting FPS meter warmup.')
            self.state = SpyGlass.State.START_WARMUP
        else:
            self.logger.info('No FPS meter warmup needed.')
            self._open_stream(self.video_fps, self.video_width, self.video_height)
            self.state = SpyGlass.State.STREAMING

    def put(
        self,
        frame: 'np.array',
    ) -> bool:
        ''' Put a frame to the video stream.

        :param frame: A numpy array of (height, width, 3) shape and of `np.uint8` type.
        :return: True if the frame was effectively put on the downstream pipeline.
        '''

        if self.state == SpyGlass.State.STOPPED:
            # Streamer paused
            return False

        if self.state == SpyGlass.State.ERROR:
            self._frame_log(
                lambda: self.logger.warning(
                    f'{self.__class__.__name__}.put() was called in {self.state} state'
                )
            )
            return False

        if self.state == SpyGlass.State.START_WARMUP:
            self._start_warmup()
            self.state = SpyGlass.State.WARMUP
            return False

        if self.state == SpyGlass.State.WARMUP:
            self._fps_meter_warmup_cnt -= 1
            if self._fps_meter_warmup_cnt == 0:
                fps, width, height = self._finish_warmup(frame)
                self.logger.info(
                    'Finished FPS meter warmup. Determined '
                    f'fps={fps}, width={width}, height={height}'
                )
                if self._open_stream(fps, width, height):
                    self.state = SpyGlass.State.STREAMING
                else:
                    self.logger.warning('Could not open cv2.VideoWriter')
                    self.state = SpyGlass.State.ERROR

            return False

        if self.state == SpyGlass.State.STREAMING:
            return self._put_frame(frame)

        # Should not arrive here
        assert False, f'Unhandled SpyGlass state {self.state}'
        return False

    def stop_streaming(self) -> None:
        ''' Stops the streaming.

        Successive calls to `put` method will silently discard the frames.
        '''
        self._close_stream()
        self.state = SpyGlass.State.STOPPED
