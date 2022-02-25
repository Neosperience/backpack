import unittest
from unittest.mock import patch, Mock

import subprocess

mock_cv2 = Mock()
mock_dotenv = Mock()
with patch.dict('sys.modules', cv2=mock_cv2, dotenv=mock_dotenv):
    from backpack.spyglass import SpyGlass

LD_LIBRARY_PATH = 'dummy_ld_library_path'
GST_PLUGIN_PATH = 'dummy_gst_plugin_path'
GST_DEBUG = 'dummy_gst_debug_level'
GST_DEBUG_FILE = '/dummy_gst_debug_file_path'
DUMMY_PLUGIN_NAME = 'dummy_plugin'
    
mock_dotenv.find_dotenv.return_value = '/dummy_dotenv_path'
mock_dotenv.dotenv_values.return_value = {
    'LD_LIBRARY_PATH': LD_LIBRARY_PATH,
    'GST_PLUGIN_PATH': GST_PLUGIN_PATH
}

class PluginNotFoundError(RuntimeError):
    pass

class FakeCalledProcessError(RuntimeError):
    def __init__(self):
        self.returncode = -1
        self.output = b'foobar'

class DummySpyGlass(SpyGlass):
    ''' As SpyGlass is an abstract base class, we will create this dummy child class
    in order to be able to test it. '''
    PIPELINE_TEMPLATE = 'dummy_pipeline fps={} width={} height={}'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._check_gst_plugin(plugin_name=DUMMY_PLUGIN_NAME):
            raise PluginNotFoundError(f'{DUMMY_PLUGIN_NAME} GStreamer plugin was not found')

    def _get_pipeline(self, fps: float, width: int, height: int) -> str:
        return DummySpyGlass.PIPELINE_TEMPLATE.format(fps, width, height)


@patch('backpack.spyglass.subprocess')
@patch('backpack.spyglass.os')
class TestSpyGlass(unittest.TestCase):

    def setUp(self):
        self.parent_logger = Mock()
        self.logger = self.parent_logger.getChild()
        
    def _setup_mocks(self, mock_os, mock_subprocess):
        mock_os.path.isfile.return_value = True

    def test_config(self, mock_os, mock_subprocess):
        self._setup_mocks(mock_os, mock_subprocess)
        spyglass = DummySpyGlass(
            parent_logger=self.parent_logger, 
            gst_log_file=GST_DEBUG_FILE, 
            gst_log_level=GST_DEBUG
        )
        mock_os.environ.__setitem__.assert_any_call('LD_LIBRARY_PATH', LD_LIBRARY_PATH)
        mock_os.environ.__setitem__.assert_any_call('GST_PLUGIN_PATH', GST_PLUGIN_PATH)
        mock_os.environ.__setitem__.assert_any_call('GST_DEBUG', GST_DEBUG)
        mock_os.environ.__setitem__.assert_any_call('GST_DEBUG_FILE', GST_DEBUG_FILE)

    def test_no_dotenv(self, mock_os, mock_subprocess):
        mock_os.path.isfile.return_value = False
        with self.assertRaises(RuntimeError):
            spyglass = DummySpyGlass(parent_logger=self.parent_logger)

    def test_add_ld_path(self, mock_os, mock_subprocess):
        EXISTING_ENVIRON_VALUE = 'fake_existing_value'
        mock_os.environ.__contains__.return_value = True
        mock_os.environ.get.return_value = EXISTING_ENVIRON_VALUE
        mock_os.environ.__getitem__.return_value = EXISTING_ENVIRON_VALUE
        spyglass = DummySpyGlass(
            parent_logger=self.parent_logger
        )
        mock_os.environ.__setitem__.assert_any_call(
            'LD_LIBRARY_PATH', 
            EXISTING_ENVIRON_VALUE + ':' + LD_LIBRARY_PATH
        )

    def test_check_gst_plugin(self, mock_os, mock_subprocess):
        self._setup_mocks(mock_os, mock_subprocess)
        spyglass = DummySpyGlass(
            parent_logger=self.parent_logger
        )
        mock_subprocess.check_output.assert_called_with(
            ['gst-inspect-1.0', DUMMY_PLUGIN_NAME, '--plugin'],
            env=unittest.mock.ANY,
            stderr=mock_subprocess.STDOUT
        )

    def test_check_gst_plugin(self, mock_os, mock_subprocess):
        self._setup_mocks(mock_os, mock_subprocess)
        spyglass = DummySpyGlass(
            parent_logger=self.parent_logger
        )
        mock_subprocess.check_output.assert_called_with(
            ['gst-inspect-1.0', DUMMY_PLUGIN_NAME, '--plugin'],
            env=unittest.mock.ANY,
            stderr=mock_subprocess.STDOUT
        )

    def test_not_gst_plugin(self, mock_os, mock_subprocess):
        def fail_check_output(*args, **kwargs):
            raise FakeCalledProcessError()
        self._setup_mocks(mock_os, mock_subprocess)
        mock_subprocess.CalledProcessError = FakeCalledProcessError
        mock_subprocess.check_output.side_effect = fail_check_output
        with self.assertRaises(PluginNotFoundError):
            spyglass = DummySpyGlass(
                parent_logger=self.parent_logger
            )
        self.logger.warning.assert_called()
