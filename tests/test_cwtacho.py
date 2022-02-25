import unittest
from unittest.mock import patch, Mock
import datetime

import botocore
from backpack.cwtacho import CWTachometer

time = Mock()

@patch('backpack.timepiece.time')
@patch('backpack.timepiece.local_now')
class TestCWTacho(unittest.TestCase):
    
    def setUp(self):
        self.namespace = 'unit_test'
        self.metric_name = 'test_metric'
        self.dimensions = {
            'dim1': 'val1',
            'dim2': 'val2'
        }
        self.boto3_session = Mock()
        self.cloudwatch = self.boto3_session.client('cloudwatch')
        parent_logger = Mock()
        self.logger = parent_logger.getChild('test_logger')
        self.cw_tacho = CWTachometer(
            namespace=self.namespace,
            metric_name=self.metric_name,
            dimensions=self.dimensions,
            boto3_session=self.boto3_session,
            parent_logger=parent_logger
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
        self.assertEqual(self.cw_tacho.namespace, self.namespace, 'namespace is correct')
        self.assertEqual(self.cw_tacho.metric_name, self.metric_name, 'metric_name is correct')
        self.assertEqual(self.cw_tacho.dimensions, self.dimensions, 'dimensions are correct')
        self.assertIs(self.cw_tacho.cloudwatch, self.cloudwatch, 'cloudwatch client is correct')

    def _do_test_callback(self, backpack_mock_local_now):
        for i in range(60 + 1):
            backpack_mock_local_now.return_value = self.start + datetime.timedelta(seconds=i)
            fired, res = self.cw_tacho.tick()
            time.sleep(1)
        return res

    def test_callback(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        cb_called, cb_return_value = self._do_test_callback(backpack_mock_local_now)
        self.assertIs(cb_called, True, 'Stats callback reported to be called')

        expected_metrics = {
            'MetricName': 'test_metric', 
            'Dimensions': [{'Name': 'dim1', 'Value': 'val1'}, {'Name': 'dim2', 'Value': 'val2'}], 
            'Timestamp': self.start + datetime.timedelta(seconds=60), 
            'StatisticValues': {'SampleCount': 60, 'Sum': 60, 'Minimum': 1, 'Maximum': 1}, 
            'Unit': 'Seconds'
        }
        self.assertEqual(cb_return_value, expected_metrics, 'callback returned correct value')
        
        cw_args, cw_kwargs = self.cloudwatch.put_metric_data.call_args
        self.assertEqual(cw_kwargs['Namespace'], self.namespace, 
                         'CloudWatch client was called with correct Namespace')
        metric_data = cw_kwargs['MetricData']
        self.assertEqual(len(metric_data), 1)
        first_metric_data = metric_data[0]
        self.assertEqual(first_metric_data, expected_metrics, 
                         'CloudWatch client was called with correct MetricData')

    def test_clienterror_handling(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        error_payload = {'Error': {'Code': 'TestException', 'Message': 'test error message'}}
        self.cloudwatch.put_metric_data.side_effect = \
            botocore.exceptions.ClientError(error_payload, 'test_operation')
        cb_called, cb_return_value = self._do_test_callback(backpack_mock_local_now)
        self.assertTrue(self.logger.warning.called)
        log_args, log_kwargs = self.logger.warning.call_args
        self.assertTrue('TestException' in log_args[0])
        
    def test_attributeerror_handling(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self.cloudwatch.put_metric_data.side_effect = AttributeError
        cb_called, cb_return_value = self._do_test_callback(backpack_mock_local_now)
        self.assertTrue(self.logger.warning.called)

    def test_otherexception_raise(self, backpack_mock_local_now, backpack_mock_time):
        self._setup_mocks(backpack_mock_time)
        self.cloudwatch.put_metric_data.side_effect = RuntimeError
        with self.assertRaises(RuntimeError):
            self._do_test_callback(backpack_mock_local_now)
