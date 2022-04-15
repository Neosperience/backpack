''' Reports Tachometer stastitics to AWS CloudWatch Metrics. '''

import datetime
import logging
from typing import Optional, Dict

import boto3
import botocore

from .timepiece import Tachometer

class CWTachometer(Tachometer):
    ''' Reports Tachometer stastitics to AWS CloudWatch Metrics.

    The IAM policy associated with the Panorama Appplication Role of this app should grant
    the execution of `cloudwatch:PutMetricData` operation.

    :param namespace: The name of the CloudWatch namespace of this custom metrics.
        It can be for example the name of your project.
    :param metric_name: The name of the CloudWatch metrics. This can be for example
        `frame_processing_time`, if you use CWTachometer to measure frame processing
        time statistics.
    :param dimensions: Additional CloudWatch metrics dimensions of this metric. This
        can be for example the device and application identifier.
    :param stats_interval: Report statistics to CloudWatch with this interval. If using
        standard resolution metrics, this should not be less than 1 minute.
    :param executor: If specified, the metrics will be reported asynchronously, using
        this executor.
    :param region: The AWS region of the CloudWatch metrics.
    :param boto3_session: The boto3 session to be used for sending the CloudWatch metrics.
        If left to None, CWTachometer will use the default session. If the default session
        does not have a default region configured, you might get errors.
    :param parent_logger: If you want to connect the logger of this class to a parent,
        specify it here.
    '''

    # pylint: disable=too-many-arguments,too-few-public-methods
    # We could group the CloudWatch related parameters into a group, but why?
    # Also, public methods are inherited from base class

    def __init__(
        self,
        namespace: str,
        metric_name: str,
        dimensions: Optional[Dict[str, str]] = None,
        stats_interval: datetime.timedelta = datetime.timedelta(seconds=60),
        executor: Optional['concurrent.futures.Executor']=None,
        region: Optional[str] = None,
        boto3_session: Optional[boto3.Session] = None,
        parent_logger: Optional[logging.Logger] = None
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

    def _stats_calback(self, timestamp, ticker):
        metric_data = {
            'MetricName': self.metric_name,
            'Dimensions': self._cw_dimensions(),
            'Timestamp': timestamp.astimezone(datetime.timezone.utc),
            'StatisticValues': {
                'SampleCount': ticker.len(),
                'Sum': ticker.sum(),
                'Minimum': ticker.min(),
                'Maximum': ticker.max()
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
