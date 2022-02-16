import datetime
import logging

import boto3
import botocore

from .timepiece import Tachometer

class CWTachometer(Tachometer):
    ''' Reports Tachometer stastitics to AWS CloudWatch Metrics. '''
    def __init__(
        self,
        namespace,
        metric_name,
        dimensions=None,
        stats_interval=datetime.timedelta(seconds=60),
        executor=None,
        region=None,
        boto3_session=None,
        parent_logger: logging.Logger=None
    ):
        super().__init__(
            stats_callback=self._stats_calback,
            stats_interval=stats_interval,
            executor=executor
        )
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
        self.dimensions = dimensions or {}
        self.namespace = namespace
        self.metric_name = metric_name
        boto3_session = boto3_session or boto3.Session(region_name=region)
        self.cloudwatch = boto3_session.client('cloudwatch')

    def _cw_dimensions(self):
        return [{ 'Name': name, 'Value': value } for name, value in self.dimensions.items()]

    def _stats_calback(
        self, timestamp, 
        min_proc_time, max_proc_time, 
        sum_proc_time, num_events
    ):
        metric_data = {
            'MetricName': self.metric_name,
            'Dimensions': self._cw_dimensions(),
            'Timestamp': timestamp,
            'StatisticValues': {
                'SampleCount': num_events,
                'Sum': sum_proc_time,
                'Minimum': min_proc_time,
                'Maximum': max_proc_time
            },
            'Unit': 'Seconds'
        }
        # self.logger.info('Putting CloudWatch metric data: %s', metric_data)
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
        except botocore.exceptions.ClientError as e:
            self.logger.warning("Couldn't put data for metric %s.%s", self.namespace, self.metric_name)
            self.logger.warning(str(e))
        except AttributeError:
            self.logger.warning("CloudWatch client is not available.")
        except Exception as e:
            self.logger.warning("Exception during CloudWatch metric put: " + str(e))


if __name__ == '__main__':
    import random
    import time
    logging.basicConfig(level=logging.INFO)
    session = boto3.Session()
    from concurrent.futures import ThreadPoolExecutor
    executor = ThreadPoolExecutor()
    tacho = CWTachometer(
        namespace='PeopleAnalytics-test',
        metric_name='frame_processing_time',
        dimensions={
            'application': 'cwtacho_test',
            'device_id': 'foobar'
        },
        stats_interval=datetime.timedelta(seconds=10),
        executor=executor,
        boto3_session=session
    )
    tacho.logger.info(f'AWS region: {session.region_name}')
    for i in range(10 * 60 * 10):
        tacho.tick()
        time.sleep(random.random() / 10)
