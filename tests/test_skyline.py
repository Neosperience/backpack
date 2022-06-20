import logging
import unittest
from unittest.mock import patch, Mock

mock_cv2 = Mock()
mock_dotenv = Mock()
with patch.dict('sys.modules', cv2=mock_cv2, dotenv=mock_dotenv):
    from backpack.skyline import SkyLine

time = Mock()

logging.basicConfig(level='CRITICAL')

LD_LIBRARY_PATH = 'dummy_ld_library_path'
GST_PLUGIN_PATH = 'dummy_gst_plugin_path'
LD_PRELOAD = 'dummy_ld_preload'
GST_DEBUG = 'dummy_gst_debug_level'
GST_DEBUG_FILE = '/dummy_gst_debug_file_path'
DUMMY_PLUGIN_NAME = 'dummy_plugin'

WARMUP_FRAMES = 3
TEST_FRAME_WIDTH = 600
TEST_FRAME_HEIGHT = 400
TEST_FPS = 15

mock_dotenv.find_dotenv.return_value = '/dummy_dotenv_path'
mock_dotenv.dotenv_values.return_value = {
    'LD_LIBRARY_PATH': LD_LIBRARY_PATH,
    'GST_PLUGIN_PATH': GST_PLUGIN_PATH,
    'LD_PRELOAD': LD_PRELOAD
}

class PluginNotFoundError(RuntimeError):
    pass

class FakeCalledProcessError(RuntimeError):
    def __init__(self):
        self.returncode = -1
        self.output = b'foobar'

class DummySkyLine(SkyLine):
    ''' As SkyLine is an abstract base class, we will create this dummy child class
    in order to be able to test it. '''
    PIPELINE_TEMPLATE = 'dummy_pipeline fps={} width={} height={}'
    FPS_METER_WARMUP_FRAMES = WARMUP_FRAMES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._check_gst_plugin(plugin_name=DUMMY_PLUGIN_NAME):
            raise PluginNotFoundError(f'{DUMMY_PLUGIN_NAME} GStreamer plugin was not found')

    def _get_pipeline(self, fps: float, width: int, height: int) -> str:
        return DummySkyLine.PIPELINE_TEMPLATE.format(fps, width, height)


@patch('backpack.skyline.subprocess')
@patch('backpack.skyline.os')
class TestSkyLine(unittest.TestCase):

    def setUp(self):
        self.parent_logger = logging.getLogger()
        self.logger = self.parent_logger.getChild('DummySkyLine')
        self.frame = Mock()
        self.frame.shape = [TEST_FRAME_HEIGHT, TEST_FRAME_WIDTH, 3]
        self.current_time = 0
        mock_cv2.VideoWriter().isOpened.return_value = True

    def _setup_os_mock(self, mock_os):
        mock_os.path.isfile.return_value = True

    def _setup_time_mock(self, mock_time):
        def _mock_time_sleep(secs):
            self.current_time += secs
        def _mock_time_perf_counter():
            return self.current_time
        mock_time.perf_counter.side_effect = _mock_time_perf_counter
        time.sleep.side_effect = _mock_time_sleep

    # ---------- Init tests ----------

    def test_init_config(self, mock_os, _):
        self._setup_os_mock(mock_os)
        DummySkyLine(
            parent_logger=self.parent_logger,
            gst_log_file=GST_DEBUG_FILE,
            gst_log_level=GST_DEBUG
        )
        mock_os.environ.__setitem__.assert_any_call('LD_LIBRARY_PATH', LD_LIBRARY_PATH)
        mock_os.environ.__setitem__.assert_any_call('GST_PLUGIN_PATH', GST_PLUGIN_PATH)
        mock_os.environ.__setitem__.assert_any_call('GST_DEBUG', GST_DEBUG)
        mock_os.environ.__setitem__.assert_any_call('GST_DEBUG_FILE', GST_DEBUG_FILE)
        mock_os.environ.__setitem__.assert_any_call('LD_PRELOAD', LD_PRELOAD)

    def test_init_no_dotenv(self, mock_os, mock_subprocess):
        mock_os.path.isfile.return_value = False
        with self.assertLogs(self.logger, 'WARNING'):
            DummySkyLine(parent_logger=self.parent_logger)

    def test_init_add_ld_path(self, mock_os, mock_subprocess):
        EXISTING_ENVIRON_VALUE = 'fake_existing_value'
        mock_os.environ.__contains__.return_value = True
        mock_os.environ.get.return_value = EXISTING_ENVIRON_VALUE
        mock_os.environ.__getitem__.return_value = EXISTING_ENVIRON_VALUE
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        mock_os.environ.__setitem__.assert_any_call(
            'LD_LIBRARY_PATH',
            EXISTING_ENVIRON_VALUE + ':' + LD_LIBRARY_PATH
        )

    def test_init_check_gst_plugin(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        mock_subprocess.check_output.assert_called_with(
            ['gst-inspect-1.0', DUMMY_PLUGIN_NAME, '--plugin'],
            env=unittest.mock.ANY,
            stderr=mock_subprocess.STDOUT
        )

    def test_init_no_gst_plugin(self, mock_os, mock_subprocess):
        def fail_check_output(*args, **kwargs):
            raise FakeCalledProcessError()
        self._setup_os_mock(mock_os)
        self.parent_logger = Mock()
        self.logger = self.parent_logger.getChild('DummySkyLine')
        mock_subprocess.CalledProcessError = FakeCalledProcessError
        mock_subprocess.check_output.side_effect = fail_check_output
        with self.assertRaises(PluginNotFoundError):
            skyline = DummySkyLine(parent_logger=self.parent_logger)
        self.logger.warning.assert_called()

    def test_init_missing_env_var(self, mock_os, mock_subprocess):
        mock_os.environ.get.return_value = None
        with self.assertLogs(self.logger, 'WARNING'):
            DummySkyLine(parent_logger=self.parent_logger)

    # ---------- Runtime tests ----------

    def test_run_start_warmup(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        self.assertEqual(skyline.state, SkyLine.State.STOPPED)
        skyline.start_streaming()
        self.assertEqual(skyline.state, SkyLine.State.START_WARMUP)
        ret = skyline.put(self.frame)
        self.assertEqual(skyline.state, SkyLine.State.WARMUP)
        self.assertFalse(ret)

    def test_run_start_streaming_during_warmup(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        skyline.start_streaming()
        skyline.put(self.frame)
        self.assertEqual(skyline.state, SkyLine.State.WARMUP)
        # start_streaming called during warmup
        skyline.start_streaming()
        self.assertEqual(skyline.state, SkyLine.State.START_WARMUP)
        self.assertFalse(skyline.put(self.frame))
        self.assertEqual(skyline.state, SkyLine.State.WARMUP)

    def test_run_put_frame_in_stopped(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        ret = skyline.put(self.frame)
        self.assertFalse(ret)

    def assertStreaming(self, skyline):
        self.assertEqual(skyline.state, SkyLine.State.STREAMING)
        self.assertEqual(skyline.video_width, TEST_FRAME_WIDTH)
        self.assertEqual(skyline.video_height, TEST_FRAME_HEIGHT)
        self.assertAlmostEqual(skyline.video_fps, TEST_FPS)

    @patch('backpack.timepiece.time')
    def test_run_warmup(self, mock_time, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        self._setup_time_mock(mock_time)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        skyline.start_streaming()
        for i in range(DummySkyLine.FPS_METER_WARMUP_FRAMES):
            self.assertFalse(skyline.put(self.frame))
            self.assertEqual(skyline.state, SkyLine.State.WARMUP)
            time.sleep(1 / TEST_FPS)
        self.assertTrue(skyline.put(self.frame))
        self.assertEqual(skyline.state, SkyLine.State.STREAMING)
        self.assertStreaming(skyline)

    def test_run_start_streaming(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        skyline.start_streaming(fps=TEST_FPS, width=TEST_FRAME_WIDTH, height=TEST_FRAME_HEIGHT)
        self.assertStreaming(skyline)
        mock_cv2.VideoWriter.assert_called_with(
            skyline._get_pipeline(TEST_FPS, TEST_FRAME_WIDTH, TEST_FRAME_HEIGHT),
            unittest.mock.ANY,
            0,
            TEST_FPS,
            (TEST_FRAME_WIDTH, TEST_FRAME_HEIGHT)
        )
        skyline.put(self.frame)
        mock_cv2.resize.assert_called_with(
            self.frame,
            (TEST_FRAME_WIDTH, TEST_FRAME_HEIGHT),
            interpolation=unittest.mock.ANY
        )
        mock_cv2.VideoWriter().write.assert_called_with(mock_cv2.resize())

    def test_run_restart_use_last(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        skyline.start_streaming(fps=TEST_FPS, width=TEST_FRAME_WIDTH, height=TEST_FRAME_HEIGHT)
        self.assertTrue(skyline.put(self.frame))
        skyline.stop_streaming()
        self.assertEqual(skyline.state, SkyLine.State.STOPPED)
        skyline.start_streaming()
        self.assertTrue(skyline.put(self.frame))
        self.assertStreaming(skyline)

    def test_run_videowriter_open_error(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        mock_cv2.VideoWriter().isOpened.return_value = False
        with self.assertLogs(skyline.logger, level='WARNING') as logs:
            skyline.start_streaming(fps=TEST_FPS, width=TEST_FRAME_WIDTH, height=TEST_FRAME_HEIGHT)
            self.assertIn('Could not open cv2.VideoWriter', logs.output[0])
        self.assertEqual(skyline.state, SkyLine.State.ERROR)
        self.assertFalse(skyline.put(self.frame))

    def test_run_videowriter_dies(self, mock_os, mock_subprocess):
        self._setup_os_mock(mock_os)
        skyline = DummySkyLine(parent_logger=self.parent_logger)
        skyline.start_streaming(fps=TEST_FPS, width=TEST_FRAME_WIDTH, height=TEST_FRAME_HEIGHT)
        self.assertTrue(skyline.put(self.frame))
        mock_cv2.VideoWriter().isOpened.return_value = False
        with self.assertLogs(skyline.logger, level='WARNING') as logs:
            self.assertFalse(skyline.put(self.frame))
            self.assertIn('Tried to write to cv2.VideoWriter but it is not opened', logs.output[0])
