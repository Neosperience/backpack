import logging
import unittest
from unittest.mock import patch, Mock

from backpack.autoidentity import AutoIdentity

import datetime

os = Mock()

@patch('backpack.autoidentity.boto3')
@patch('backpack.autoidentity.os')
class TestAutoIdentity(unittest.TestCase):

    APPLICATION_ID = 'dummy_app_id'
    APPLICATION_NAME = 'test_application_name'
    APPLICATION_DESCRIPTION = 'Test Application Description'
    APPLICATION_CREATED_TIME = datetime.datetime(2022, 2, 22, 22, 22, 22)
    APPLICATION_TAGS = {'test_tag': 'test_value'}
    APPLICATION_STATUS = 'TEST'
    DEVICE_ID = 'test_device_id'
    DEVICE_NAME = 'test_device_name'
    NEXT_TOKEN = 'dummy_next_token'

    APPLICATION_INSTANCE = {
        'ApplicationInstanceId': APPLICATION_ID,
        'Name': APPLICATION_NAME,
        'DefaultRuntimeContextDevice': DEVICE_ID,
        'DefaultRuntimeContextDeviceName': DEVICE_NAME,
        'CreatedTime': APPLICATION_CREATED_TIME,
        'HealthStatus': APPLICATION_STATUS,
        'Tags': APPLICATION_TAGS,
        'Description': APPLICATION_DESCRIPTION,
    }

    def setUp(self):
        self.device_region = 'dummy-region'
        self.parent_logger = logging.getLogger()
        self.logger = self.parent_logger.getChild('AutoIdentity')

    def _setup_mocks(self, backpack_mock_os, backpack_mock_boto3):
        backpack_mock_os.environ.get.return_value = TestAutoIdentity.APPLICATION_ID
        return backpack_mock_boto3.Session().client('panorama')

    def test_attributes(self, backpack_mock_os, backpack_mock_boto3):
        panorama = self._setup_mocks(backpack_mock_os, backpack_mock_boto3)
        panorama.list_application_instances.side_effect = [
            { 'ApplicationInstances': [TestAutoIdentity.APPLICATION_INSTANCE] }
        ]
        ai = AutoIdentity(
            device_region=self.device_region,
            parent_logger=self.parent_logger
        )
        panorama.list_application_instances.assert_called()
        self.assertEqual(ai.application_name, TestAutoIdentity.APPLICATION_NAME)
        self.assertEqual(ai.application_created_time, TestAutoIdentity.APPLICATION_CREATED_TIME)
        self.assertEqual(ai.application_tags, TestAutoIdentity.APPLICATION_TAGS)
        self.assertEqual(ai.application_status, TestAutoIdentity.APPLICATION_STATUS)
        self.assertEqual(ai.application_description, TestAutoIdentity.APPLICATION_DESCRIPTION)
        self.assertEqual(ai.device_id, TestAutoIdentity.DEVICE_ID)
        self.assertEqual(ai.device_name, TestAutoIdentity.DEVICE_NAME)

    def test_next_token(self, backpack_mock_os, backpack_mock_boto3):
        panorama = self._setup_mocks(backpack_mock_os, backpack_mock_boto3)
        lai = panorama.list_application_instances
        lai.side_effect = [
            {
                'ApplicationInstances': [TestAutoIdentity.APPLICATION_INSTANCE],
                'NextToken': TestAutoIdentity.NEXT_TOKEN
            },
            {
                'ApplicationInstances': [TestAutoIdentity.APPLICATION_INSTANCE]
            }
        ]
        ai = AutoIdentity(
            device_region=self.device_region,
            parent_logger=self.parent_logger
        )
        self.assertEqual(lai.call_count, 2, 'Service called twice')
        lai.assert_called_with(NextToken=TestAutoIdentity.NEXT_TOKEN, StatusFilter=unittest.mock.ANY)

    def test_no_app_instance_id(self, backpack_mock_os, backpack_mock_boto3):
        backpack_mock_os.environ.get.return_value = None
        with self.assertLogs(self.logger, 'WARNING') as logs:
            ai = AutoIdentity(
                device_region=self.device_region,
                parent_logger=self.parent_logger
            )
        self.assertEqual(ai.application_instance_id, None)

    def test_no_app_instance_data(self, backpack_mock_os, backpack_mock_boto3):
        panorama = self._setup_mocks(backpack_mock_os, backpack_mock_boto3)
        lai = panorama.list_application_instances
        wrong_instance = TestAutoIdentity.APPLICATION_INSTANCE.copy()
        wrong_instance['ApplicationInstanceId'] = 'wrong_instance_id'
        lai.side_effect = [
            {
                'ApplicationInstances': [wrong_instance]
            }
        ]
        with self.assertLogs(self.logger, 'WARNING') as logs:
            ai = AutoIdentity(
                device_region=self.device_region,
                parent_logger=self.parent_logger
            )
        self.assertEqual(ai.application_name, None)

    def test_repr(self, backpack_mock_os, backpack_mock_boto3):
        panorama = self._setup_mocks(backpack_mock_os, backpack_mock_boto3)
        panorama.list_application_instances.side_effect = [
            { 'ApplicationInstances': [TestAutoIdentity.APPLICATION_INSTANCE] }
        ]
        ai = AutoIdentity(
            device_region=self.device_region,
            parent_logger=self.parent_logger
        )
        expected_repr = (
            "<AutoIdentity application_created_time=2022-02-22 22:22:22 "
            "application_description=Test Application Description "
            "application_instance_id=dummy_app_id "
            "application_name=test_application_name "
            "application_status=TEST "
            "application_tags={'test_tag': 'test_value'} "
            "device_id=test_device_id "
            "device_name=test_device_name>"
        )
        self.assertEqual(repr(ai), expected_repr)
