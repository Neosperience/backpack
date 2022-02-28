import logging
import datetime

import unittest
from unittest.mock import patch, Mock, MagicMock

mock_cv2 = Mock()
mock_boto3 = Mock()
mock_session = mock_boto3.Session()
mock_credentials = mock_session.get_credentials()
mock_frozen = mock_credentials.get_frozen_credentials()

with patch.dict('sys.modules', cv2=mock_cv2, boto3=mock_boto3):
    import backpack.kvs
    from backpack.kvs import (
        KVSInlineCredentialsHandler, KVSEnvironmentCredentialsHandler, KVSFileCredentialsHandler
    )

# Helpers
def utc_dt(dt):
    return dt.replace(tzinfo=datetime.timezone.utc)

# Mock constants

TEST_AWS_ACCESS_KEY_ID = 'fake_aws_access_key_id'
TEST_AWS_SECRET_KEY = 'fake_aws_secret_key'
TEST_TOKEN = 'fake_token'
TEST_CALLER_ARN = 'fake_caller_arn'
TEST_EXPIRY_TIME = utc_dt(datetime.datetime(2022, 2, 22, 22, 22, 22))
TEXT_EXPIRY_TIME_STR = '2022-02-22T22:21:22Z'

# Setup global mocks

mock_session.client('sts').get_caller_identity.return_value = {
    'Arn': TEST_CALLER_ARN
}

mock_credentials.access_key = TEST_AWS_ACCESS_KEY_ID
mock_credentials.secret_key = TEST_AWS_SECRET_KEY
mock_credentials._expiry_time = TEST_EXPIRY_TIME
mock_frozen.access_key = TEST_AWS_ACCESS_KEY_ID
mock_frozen.secret_key = TEST_AWS_SECRET_KEY
mock_frozen.token = TEST_TOKEN


class TestInlineCredentialsHandler(unittest.TestCase):
    
    def setUp(self):
        self.ch = KVSInlineCredentialsHandler(
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY
        )

    def test_plugin_config(self):
        TEMPLATE = 'access-key="{}" secret-key="{}"'
        self.assertEqual(
            self.ch.plugin_config(), 
            TEMPLATE.format(TEST_AWS_ACCESS_KEY_ID, TEST_AWS_SECRET_KEY)
        )

    def test_plugin_config_mask(self):
        plugin_config = self.ch.plugin_config()
        mask = self.ch.plugin_config_mask(plugin_config)
        self.assertNotIn(TEST_AWS_ACCESS_KEY_ID, mask)
        self.assertNotIn(TEST_AWS_SECRET_KEY, mask)

    @patch('backpack.kvs._is_refreshable', return_value=True)
    def test_refreshable_raises(self, *args):
        with self.assertRaises(RuntimeError):
            self.ch = KVSInlineCredentialsHandler()


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

    def test_save_credentials(self, kvs_os_environ):
        self._create_ch()
        self.assert_keys_set(kvs_os_environ)

    @patch('backpack.kvs._is_refreshable', return_value=True)
    def test_refreshable_save_credentials(self, _, kvs_os_environ):
        KVSEnvironmentCredentialsHandler(
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY
        )
        self.assert_keys_set(kvs_os_environ)
        kvs_os_environ.__setitem__.assert_any_call(
            'AWS_SESSION_TOKEN', TEST_TOKEN
        )


class TestFileCredentialsHandler(unittest.TestCase):
    
    TEST_CREDENTIALS_PATH = '/tmp/test_credentials.txt'

    def _create_ch(self):
        return KVSFileCredentialsHandler(
            credentials_path=self.TEST_CREDENTIALS_PATH,
            aws_access_key_id=TEST_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=TEST_AWS_SECRET_KEY
        )

    def test_plugin_config(self):
        ch = self._create_ch()
        TEMPLATE = 'credential-path="{}"'
        self.assertEqual(
            ch.plugin_config(), 
            TEMPLATE.format(self.TEST_CREDENTIALS_PATH)
        )

    @patch('backpack.kvs.open', new_callable=unittest.mock.mock_open)
    def test_save_credentials(self, mock_open):
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
        print(mock_open.mock_calls)
        mock_open.assert_any_call(
            self.TEST_CREDENTIALS_PATH, 'w', encoding='utf-8'
        )
        mock_open().write.assert_any_call(
            FILE_TEMPLATE.format(
                TEST_AWS_ACCESS_KEY_ID, 
                TEXT_EXPIRY_TIME_STR, 
                TEST_AWS_SECRET_KEY, 
                TEST_TOKEN
            )
        )
