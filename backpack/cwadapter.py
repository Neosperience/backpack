''' Reports timer statistics to AWS CloudWatch Metrics. '''

import datetime
import logging
from typing import Optional, Dict

import boto3
import botocore

from .timepiece import BaseTimer

class CloudWatchTimerAdapter:
    ''' Reports timer statistics to AWS CloudWatch Metrics.

    The IAM policy associated with the Panorama Application Role of this app should grant
    the execution of `cloudwatch:PutMetricData` operation.

    Args:
        namespace (str): The name of the CloudWatch namespace of this custom metrics.
            It can be for example the name of your project.
        metric_name (str): The name of the CloudWatch metrics. This can be for example
            `frame_processing_time`, if you use CWTachometer to measure frame processing
            time statistics.
        dimensions (Optional[Dict[str, str]]): Additional CloudWatch metrics dimensions of this
            metric. This can be for example the device and application identifier.
        region (Optional[str]): The AWS region of the CloudWatch metrics.
        boto3_session (Optional[boto3.Session]): The boto3 session to be used for sending the
            CloudWatch metrics. If left to None, CWTachometer will use the default session. If the
            default session does not have a default region configured, you might get errors.
        parent_logger (Optional[logging.Logger]): If you want to connect the logger of this class
            to a parent, specify it here.
    '''

    def __init__(self,
        namespace: str,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None,
        region: Optional[str] = None,
        boto3_session: Optional[boto3.Session] = None,
        parent_logger: Optional[logging.Logger] = None
    ):
        self.logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
        self.dimensions = CloudWatchTimerAdapter._cw_dimensions(dimensions or {})
        self.namespace = namespace
        self.metric_name = metric_name
        boto3_session = boto3_session or boto3.Session(region_name=region)
        self.cloudwatch = boto3_session.client('cloudwatch')

    @staticmethod
    def _cw_dimensions(dimensions):
        return [{ 'Name': name, 'Value': value } for name, value in dimensions.items()]

    def send_metrics(self, timestamp: datetime.datetime, timer: BaseTimer) -> None:
        ''' Sends timer statistics to CloudWatch.

        This method can be used as a callback in Tachometer instances.

        For example::

            cw_adapter = CloudWatchTimerAdapter(
                namespace='my_namespace',
                metric_name='my_metric',
                dimensions={'foo': 'bar'}
            )
            tacho = TickerTachometer(
                stats_callback=cw_adapter.send_metrics
            )
            tacho.tick()

        Args:
            timestamp (datetime.datetime): The timestamp the statistics refers to.
            timer (BaseTimer): The timer that collected the statistics.
        '''
        metric_data = {
            'MetricName': self.metric_name,
            'Dimensions': self.dimensions,
            'Timestamp': timestamp.astimezone(datetime.timezone.utc),
            'StatisticValues': {
                'SampleCount': timer.len(),
                'Sum': timer.sum(),
                'Minimum': timer.min(),
                'Maximum': timer.max()
            },
            'Unit': 'Seconds'
        }
        try:
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
        except botocore.exceptions.ClientError as error:
            self.logger.warning('Couldn\'t put data for metric %s.%s',
                                self.namespace, self.metric_name)
            self.logger.warning(str(error))
        except AttributeError:
            self.logger.warning('CloudWatch client is not available.')
        return metric_data
