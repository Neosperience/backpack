import logging
import unittest
from unittest.mock import patch, Mock
import datetime

import botocore
from backpack.cwadapter import CloudWatchTimerAdapter
from backpack.timepiece import TickerTachometer

time = Mock()

@patch('backpack.timepiece.time')
@patch('backpack.timepiece.local_now')
class TestCWAdapter(unittest.TestCase):

    def setUp(self):
        self.namespace = 'unit_test'
        self.metric_name = 'test_metric'
        self.dimensions = {
            'dim1': 'val1',
            'dim2': 'val2'
        }
        self.cw_dimensions = [
            {'Name': 'dim1', 'Value': 'val1'},
            {'Name': 'dim2', 'Value': 'val2'}
        ]
        self.boto3_session = Mock()
        self.cloudwatch = self.boto3_session.client('cloudwatch')
        parent_logger = logging.getLogger()
        self.logger = parent_logger.getChild('test_logger')
        self.cw_adapter = CloudWatchTimerAdapter(
            namespace=self.namespace,
            metric_name=self.metric_name,
            dimensions=self.dimensions,
            boto3_session=self.boto3_session,
            parent_logger=parent_logger
        )
        self.tacho = TickerTachometer(
            stats_callback=self.cw_adapter.send_metrics
        )
        self.start = datetime.datetime(2022, 2, 22, 22, 22, 0)
        self.current_perf_time = 0

    def _setup_mocks(self, backpack_mock_time):
        def _mock_time_sleep( secs):
            self.current_perf_time += secs
        def _mock_time_perf_counter():
            return self.current_perf_time
        backpack_mock_time.perf_counter.side_effect = _mock_time_perf_counter
        time.sleep.side_effect = _mock_time_sleep

    def test_init(self, backpack_mock_local_now, backpack_mock_time):
        self.assertEqual(self.cw_adapter.namespace, self.namespace, 'namespace is correct')
        self.assertEqual(self.cw_adapter.metric_name, self.metric_name, 'metric_name is correct')
        self.assertEqual(self.cw_adapter.dimensions, self.cw_dimensions, 'dimensions are correct')
        self.assertIs(self.cw_adapter.cloudwatch, self.cloudwatch, 'cloudwatch client is correct')

    def _do_test_callback(self, backpack_mock_local_now):
        for i in range(60 + 1):
            backpack_mock_local_now.return_value = self.start + datetime.timedelta(seconds=i)
            fired, res = self.tacho.tick()
            time.sleep(1)
        return res

    def test_callback(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        cb_called, cb_return_value = self._do_test_callback(backpack_mock_local_now)
        self.assertIs(cb_called, True, 'Stats callback reported to be called')

        expected_ts = (self.start + datetime.timedelta(seconds=60)).astimezone(datetime.timezone.utc)
        expected_metrics = {
            'MetricName': 'test_metric',
            'Dimensions': [{'Name': 'dim1', 'Value': 'val1'}, {'Name': 'dim2', 'Value': 'val2'}],
            'Timestamp': expected_ts,
            'StatisticValues': {'SampleCount': 60, 'Sum': 60, 'Minimum': 1, 'Maximum': 1},
            'Unit': 'Seconds'
        }
        self.assertEqual(cb_return_value, expected_metrics, 'callback returned correct value')

        self.cloudwatch.put_metric_data.assert_called_with(
            Namespace=self.namespace,
            MetricData=[expected_metrics]
        )

    def test_clienterror_handling(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        error_payload = {'Error': {'Code': 'TestException', 'Message': 'test error message'}}
        self.cloudwatch.put_metric_data.side_effect = \
            botocore.exceptions.ClientError(error_payload, 'test_operation')
        with self.assertLogs(self.cw_adapter.logger, 'WARNING') as logs:
            self._do_test_callback(backpack_mock_local_now)
            self.assertTrue(any('TestException' in o for o in logs.output))

    def test_attributeerror_handling(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self.cloudwatch.put_metric_data.side_effect = AttributeError
        with self.assertLogs(self.cw_adapter.logger, 'WARNING') as logs:
            self._do_test_callback(backpack_mock_local_now)

    def test_otherexception_raise(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self.cloudwatch.put_metric_data.side_effect = RuntimeError
        with self.assertRaises(RuntimeError):
            self._do_test_callback(backpack_mock_local_now)
