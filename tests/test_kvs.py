import logging
import datetime

import unittest
from unittest.mock import patch, Mock, MagicMock, PropertyMock

mock_cv2 = Mock()
mock_boto3 = Mock()
mock_dotenv = Mock()
mock_os = MagicMock()
mock_session = mock_boto3.Session()
mock_credentials = mock_session.get_credentials()
mock_frozen = mock_credentials.get_frozen_credentials()

with patch.dict('sys.modules', cv2=mock_cv2, boto3=mock_boto3, dotenv=mock_dotenv, os=mock_os):
    import backpack.kvs
    from backpack.kvs import (
        KVSCredentialsHandler, KVSInlineCredentialsHandler,
        KVSEnvironmentCredentialsHandler, KVSFileCredentialsHandler,
        KVSSkyLine
    )

from backpack.timepiece import local_dt

# Mock constants

TIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
TEST_AWS_ACCESS_KEY_ID = 'fake_aws_access_key_id'
TEST_AWS_SECRET_KEY = 'fake_aws_secret_key'
TEST_TOKEN = 'fake_token'
TEST_CALLER_ARN = 'fake_caller_arn'
TEST_LOCAL_NOW = local_dt(datetime.datetime(2022, 2, 22, 22, 22, 22))
TEST_EXPIRY_TIME = local_dt(datetime.datetime(2022, 2, 22, 23, 22, 22))

TEST_FRAME_WIDTH = 600
TEST_FRAME_HEIGHT = 400
TEST_FPS = 15

LD_LIBRARY_PATH = 'dummy_ld_library_path'
GST_PLUGIN_PATH = 'dummy_gst_plugin_path'

# Setup global mocks

mock_session.client('sts').get_caller_identity.return_value = {
    'Arn': TEST_CALLER_ARN
}

mock_credentials.access_key = TEST_AWS_ACCESS_KEY_ID
mock_credentials.secret_key = TEST_AWS_SECRET_KEY
mock_credentials.refresh_needed.return_value = True
mock_credentials._expiry_time = TEST_EXPIRY_TIME
mock_frozen.access_key = TEST_AWS_ACCESS_KEY_ID
mock_frozen.secret_key = TEST_AWS_SECRET_KEY
mock_frozen.token = TEST_TOKEN

mock_dotenv.find_dotenv.return_value = '/dummy_dotenv_path'
mock_dotenv.dotenv_values.return_value = {
    'LD_LIBRARY_PATH': LD_LIBRARY_PATH,
    'GST_PLUGIN_PATH': GST_PLUGIN_PATH
}

mock_os.path.isfile.return_value = True

@patch('backpack.kvs.local_now', return_value=TEST_LOCAL_NOW)
class TestInlineCredentialsHandler(unittest.TestCase):

    def _create_ch(self):
        return KVSInlineCredentialsHandler(
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY
        )

    def test_plugin_config(self, *args):
        TEMPLATE = 'access-key="{}" secret-key="{}"'
        ch = self._create_ch()
        self.assertEqual(
            ch.plugin_config(),
            TEMPLATE.format(TEST_AWS_ACCESS_KEY_ID, TEST_AWS_SECRET_KEY)
        )

    def test_plugin_config_mask(self, *args):
        ch = self._create_ch()
        plugin_config = ch.plugin_config()
        mask = ch.plugin_config_mask(plugin_config)
        self.assertNotIn(TEST_AWS_ACCESS_KEY_ID, mask)
        self.assertNotIn(TEST_AWS_SECRET_KEY, mask)

    @patch('backpack.kvs._is_refreshable', return_value=True)
    def test_refreshable_raises(self, *args):
        with self.assertRaises(RuntimeError):
            KVSInlineCredentialsHandler()

@patch('backpack.kvs.local_now', return_value=TEST_LOCAL_NOW)
@patch('backpack.kvs.os.environ')
class TestEnvironmentCredentialsHandler(unittest.TestCase):

    def assert_keys_set(self, kvs_os_environ):
        kvs_os_environ.__setitem__.assert_any_call(
            'AWS_ACCESS_KEY_ID', TEST_AWS_ACCESS_KEY_ID
        )
        kvs_os_environ.__setitem__.assert_any_call(
            'AWS_SECRET_ACCESS_KEY', TEST_AWS_SECRET_KEY
        )

    def _create_ch(self):
        return KVSEnvironmentCredentialsHandler(
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY
        )

    def test_plugin_config(self, *args):
        ch = self._create_ch()
        self.assertEqual(ch.plugin_config(), '')

    def test_plugin_config_mask(self, *args):
        ch = self._create_ch()
        plugin_config = ch.plugin_config()
        mask = ch.plugin_config_mask(plugin_config)
        self.assertEqual(mask, '')

    def test_save_credentials(self, kvs_os_environ, *args):
        self._create_ch()
        self.assert_keys_set(kvs_os_environ)

    @patch('backpack.kvs._is_refreshable', return_value=True)
    @patch('backpack.timepiece.local_now', return_value=TEST_LOCAL_NOW)
    def test_refreshable_save_credentials(self, _1, _2, kvs_os_environ, *args):
        self._create_ch()
        self.assert_keys_set(kvs_os_environ)
        kvs_os_environ.__setitem__.assert_any_call(
            'AWS_SESSION_TOKEN', TEST_TOKEN
        )


@patch('backpack.kvs.local_now', return_value=TEST_LOCAL_NOW)
class TestFileCredentialsHandler(unittest.TestCase):

    TEST_CREDENTIALS_PATH = '/tmp/test_credentials.txt'

    def setUp(self):
        self.parent_logger = logging.getLogger()
        mock_credentials._protected_refresh.reset_mock()

    def _create_ch(self):
        ch = KVSFileCredentialsHandler(
            credentials_path=self.TEST_CREDENTIALS_PATH,
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY,
            executor=None,
            parent_logger=self.parent_logger
        )
        # ch.logger.setLevel('INFO')
        return ch

    def test_plugin_config(self, *args):
        ch = self._create_ch()
        TEMPLATE = 'credential-path="{}"'
        self.assertEqual(
            ch.plugin_config(),
            TEMPLATE.format(self.TEST_CREDENTIALS_PATH)
        )

    @patch('backpack.kvs.open', new_callable=unittest.mock.mock_open)
    def test_save_credentials(self, mock_open, *args):
        FILE_TEMPLATE = 'CREDENTIALS\t{}\t{}'
        self._create_ch()
        mock_open.assert_any_call(
            self.TEST_CREDENTIALS_PATH, 'w', encoding='utf-8'
        )
        mock_open().write.assert_any_call(
            FILE_TEMPLATE.format(TEST_AWS_ACCESS_KEY_ID, TEST_AWS_SECRET_KEY)
        )

    @patch('backpack.kvs._is_refreshable', return_value=True)
    @patch('backpack.kvs.open', new_callable=unittest.mock.mock_open)
    def test_refreshable_save_credentials(self, mock_open, *args):
        FILE_TEMPLATE = 'CREDENTIALS\t{}\t{}\t{}\t{}'
        self._create_ch()
        mock_open.assert_any_call(
            self.TEST_CREDENTIALS_PATH, 'w', encoding='utf-8'
        )
        expected_file_expiry = (
            TEST_EXPIRY_TIME -
            KVSCredentialsHandler.REFRESH_BEFORE_EXPIRATION +
            KVSFileCredentialsHandler.FILE_REFRESH_GRACE_PERIOD
        )
        mock_open().write.assert_any_call(
            FILE_TEMPLATE.format(
                TEST_AWS_ACCESS_KEY_ID,
                expected_file_expiry.strftime(TIME_FORMAT),
                TEST_AWS_SECRET_KEY,
                TEST_TOKEN
            )
        )

    @patch('backpack.timepiece.local_now')
    @patch('backpack.kvs._is_refreshable', return_value=True)
    def test_refresh(self, mock_is_refreshable, mock_timepiece_local_now, *args):
        with self.subTest(phase='refresh during init'):
            ch = self._create_ch()
            mock_credentials._protected_refresh.assert_called_once_with(is_mandatory=True)
        with self.subTest(phase='early check_refresh'):
            mock_credentials._protected_refresh.reset_mock()
            mock_timepiece_local_now.return_value = TEST_LOCAL_NOW
            ch.check_refresh()
            mock_credentials._protected_refresh.assert_not_called()
        with self.subTest(phase='refresh time'):
            expiry_time = TEST_EXPIRY_TIME + datetime.timedelta(seconds=1)
            mock_timepiece_local_now.return_value = expiry_time
            ch.check_refresh()
            mock_credentials._protected_refresh.assert_called()

    @patch('backpack.timepiece.local_now')
    @patch('backpack.kvs._is_refreshable', return_value=True)
    def test_update_in_past(self, mock_is_refreshable, mock_timepiece_local_now, *args):
        mock_credentials._expiry_time = TEST_LOCAL_NOW - datetime.timedelta(seconds=1)
        ch = self._create_ch()
        mock_timepiece_local_now.return_value = TEST_LOCAL_NOW
        mock_credentials._protected_refresh.reset_mock()
        ch.check_refresh()
        mock_credentials._protected_refresh.assert_called()
        mock_credentials._expiry_time = TEST_EXPIRY_TIME


@patch('subprocess.check_output')
@patch('backpack.skyline.os')
class TestKVSSkyLine(unittest.TestCase):

    STREAM_NAME = 'test_stream'
    STREAM_REGION = 'test-west-1'

    def setUp(self):
        self.frame = Mock()
        self.frame.shape = [TEST_FRAME_HEIGHT, TEST_FRAME_WIDTH, 3]

    def _create_skyline(self):
        ch = KVSInlineCredentialsHandler(
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY
        )
        return KVSSkyLine(
            stream_region=self.STREAM_REGION,
            stream_name=self.STREAM_NAME,
            credentials_handler=ch
        )

    def test_start_streaming(self, *args):
        skyline = self._create_skyline()
        skyline.start_streaming(fps=TEST_FPS, width=TEST_FRAME_WIDTH, height=TEST_FRAME_HEIGHT)
        kvs_config_str = ' '.join([
            'storage-size=512',
            f'stream-name="{self.STREAM_NAME}"',
            f'aws-region="{self.STREAM_REGION}"',
            f'framerate={TEST_FPS}',
            skyline.credentials_handler.plugin_config()
        ])
        expected_pipeline = ' ! '.join([
            'appsrc',
            'videoconvert',
            f'video/x-raw,format=I420,width={TEST_FRAME_WIDTH},'
            f'height={TEST_FRAME_HEIGHT},framerate={TEST_FPS}/1',
            'x264enc bframes=0 key-int-max=45 bitrate=500',
            'video/x-h264,stream-format=avc,alignment=au,profile=baseline',
            f'kvssink {kvs_config_str}'
        ])
        mock_cv2.VideoWriter.assert_called_with(
            expected_pipeline,
            unittest.mock.ANY,
            0,
            TEST_FPS,
            (TEST_FRAME_WIDTH, TEST_FRAME_HEIGHT)
        )

    @patch('backpack.kvs.KVSInlineCredentialsHandler.check_refresh')
    def test_put_frame(self, mock_check_refresh, *args):
        skyline = self._create_skyline()
        skyline.start_streaming(fps=TEST_FPS, width=TEST_FRAME_WIDTH, height=TEST_FRAME_HEIGHT)
        skyline.put(self.frame)
        mock_cv2.VideoWriter().write.assert_called_with(mock_cv2.resize())
        mock_check_refresh.assert_called()

    @patch('backpack.kvs.KVSSkyLine._check_gst_plugin', return_value=False)
    def test_no_plugin(self, *args):
        with self.assertRaises(RuntimeError):
            _ = self._create_skyline()

