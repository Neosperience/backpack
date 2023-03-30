''' This module contains the :class:`AutoIdentity` class that provides information about the
application execution environment. '''

import os
import logging
import datetime
from typing import Dict, Optional, Iterator, Any
import time

import boto3
from pydantic import BaseModel, Field

class AutoIdentityData(BaseModel):
    ''' Data class to store auto identity information. '''

    application_instance_id: str = Field(alias='ApplicationInstanceId')
    ''' Application instance id. '''

    application_name: str = Field(alias='Name')
    ''' Name of this application. '''

    application_tags: Dict[str, str] = Field(alias='Tags')
    ''' Tags associated with this application. '''

    device_id: str = Field(alias='DefaultRuntimeContextDevice')
    ''' Device id of the appliance running this application. '''

    device_name: str = Field(alias='DefaultRuntimeContextDeviceName')
    '''  Name of this application. '''

    application_created_time: datetime.datetime = Field(alias='CreatedTime')
    ''' Application deployment time. '''

    application_status: str = Field(alias='HealthStatus')
    ''' Health status of this application. '''

    application_description: str = Field(alias='Description')
    ''' The description of this application. '''

    @classmethod
    def for_test_environment(cls, application_instance_id: str, application_name: str):
        ''' Initializes a dummy AutoIdentityData to be used in test environment. '''
        return cls(
            ApplicationInstanceId=application_instance_id,
            Name=application_name,
            Tags={},
            DefaultRuntimeContextDevice='emulator',
            DefaultRuntimeContextDeviceName='test_utility_emulator',
            CreatedTime=datetime.datetime.now(),
            HealthStatus='TEST_UTILITY',
            Description=application_name,
        )


class AutoIdentityFetcher:
    ''' AutoIdentity instance queries metadata of the current application instance.

    The IAM policy associated with the `Panorama Application Role`_
    of this app should grant the execution of
    `panorama:ListApplicationInstances`_ operation.

    Args:
        device_region: The AWS region where this Panorama appliance is registered.
        application_instance_id: The application instance id. If left to `None`,
            :class:`AutoIdentity` will try to find the instance id in the environment variable.
        parent_logger: If you want to connect the logger to a parent, specify it here.

    .. _`Panorama Application Role`:
        https://docs.aws.amazon.com/panorama/latest/dev/permissions-application.html
    .. _`panorama:ListApplicationInstances`:
        https://docs.aws.amazon.com/service-authorization/latest/reference/list_awspanorama.html#awspanorama-actions-as-permissions
    '''

    # pylint: disable=too-many-instance-attributes,too-few-public-methods
    # This class functions as a data class that reads its values from the environment

    def __init__(self,
        device_region: str,
        application_instance_id: Optional[str] = None,
        parent_logger: Optional[logging.Logger] = None
    ):
        self._logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
        self.application_instance_id = (
            application_instance_id or os.environ.get('AppGraph_Uid')
        )
        if not self.application_instance_id:
            raise RuntimeError(
                'Could not find application instance id in environment variable "AppGraph_Uid"'
            )
        self.device_region = device_region

    def get_data(self, retry_freq: Optional[float] = None) -> AutoIdentityData:
        ''' Fetches the auto identity data.

        Args:
            retry_freq (Optional[float]): If set to a float number, AutoIdentity will keep retrying
                fetching the auto identity data from remote services if the status of the app was
                "NOT_AVAILABLE". If set to None, will not retry.

        Raises:
            RuntimeError: if could not fetch the auto identity information, and retry_freq is set
                to None.
        '''

        def fetch() -> Dict[str, Any]:
            app_instance_data = self._app_instance_data(self.application_instance_id)
            if not app_instance_data:
                raise RuntimeError(
                    'Could not find application instance in service response. '
                    'Check if application_instance_id=%s '
                    'and device_region=%s parameters are correct.'
                    .format(self.application_instance_id, self.device_region)
                )
            else:
                return app_instance_data

        while True:
            app_instance_data = fetch()
            status = app_instance_data.get('HealthStatus', 'NOT_AVAILABLE')
            if status == 'NOT_AVAILABLE':
                if retry_freq is None:
                    raise RuntimeError(
                        'Application HealthStatus is "NOT_AVAILABLE" and retry is disabled.'
                    )
                else:
                    time.sleep(retry_freq)
                    continue
            elif status == 'ERROR':
                raise RuntimeError('Application HealthStatus is "ERROR"')
            else:
                return AutoIdentityData(**app_instance_data)

    def _list_app_instances(self, deployed_only=True) -> Iterator[Dict[str, Any]]:
        session = boto3.Session(region_name=self.device_region)
        panorama = session.client('panorama')
        next_token = None
        while True:
            kwargs = {'StatusFilter': 'DEPLOYMENT_SUCCEEDED'} if deployed_only else {}
            if next_token:
                kwargs['NextToken'] = next_token
            response = panorama.list_application_instances(**kwargs)
            inst: Dict[str, Any]
            for inst in response['ApplicationInstances']:
                yield inst
            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                break

    def _app_instance_data(self, application_instance_id) -> Optional[Dict[str, Any]]:
        matches = (inst
            for inst in self._list_app_instances()
            if inst.get('ApplicationInstanceId') == application_instance_id
        )
        return next(matches, None)
