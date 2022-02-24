''' AWS Panorama related tools. '''

import os
import logging
import datetime
from typing import Dict

import boto3

class AutoIdentity:
    ''' AutoIdentity instance queries metadata of the current application instance.

    The IAM policy associated with the Panorama Application Role of this app should grant
    the execution of `panorama:ListApplicationInstances` operation.

    :param device_region: The AWS region where this Panorama appliance is registered.
    :param application_instance_id: The application instance id. If left to None,
        AutoIdentity will try to find the instance id in the environment variable.
    :param parent_logger: If you want to connect the logger to a parent, specify it here.

    Upon successfully initialization, AutoIdentity will fill out the following properties:

    :ivar application_created_time: Application deployment time.
    :ivar application_instance_id: Application instance id.
    :ivar application_name: Name of this application.
    :ivar application_status: Health status of this application.
    :ivar application_tags: Tags associated with this application.
    :ivar application_description: The description of this application.
    :ivar device_id: Device id of the appliance running this application.
    :ivar device_name: Name of the appliance running this application.
    '''

    def __init__(self, device_region, application_instance_id=None, parent_logger=None):
        self._logger = (
            logging.getLogger(self.__class__.__name__) if parent_logger is None else
            parent_logger.getChild(self.__class__.__name__)
        )
        self.application_instance_id: str = (
            application_instance_id or os.environ.get('AppGraph_Uid')
        )
        self.application_name: str = None
        self.device_id: str = None
        self.device_name: str = None
        self.application_created_time: datetime.datetime = None
        self.application_status: str = None
        self.application_tags: Dict[str, str]  = None
        self.application_description: str = None
        if not self.application_instance_id:
            self._logger.warning('Could not find application instance id '
                                 'in environment variable "AppGraph_Uid"')
            return
        self._session = boto3.Session(region_name=device_region)
        self._panorama = self._session.client('panorama')
        app_instance_data = self._app_instance_data(self.application_instance_id)
        if not app_instance_data:
            self._logger.warning('Could not find application instance in service response. '
                                f'Check if application_instance_id={self.application_instance_id} '
                                f'and device_region={device_region} parameters are correct.')
            return
        self._config_from_instance_data(app_instance_data)

    def __repr__(self):
        elements = [f'{a}={getattr(self, a)}' for a in dir(self) if not a.startswith('_')]
        return '<AutoIdentity ' + ' '.join(elements) + '>'

    def _config_from_instance_data(self, instance_data):
        self.application_name = instance_data.get('Name')
        self.device_id = instance_data.get('DefaultRuntimeContextDevice')
        self.device_name = instance_data.get('DefaultRuntimeContextDeviceName')
        self.application_created_time = instance_data.get('CreatedTime')
        self.application_status = instance_data.get('HealthStatus')
        self.application_tags = instance_data.get('Tags')
        self.application_description = instance_data.get('Description')

    def _list_app_instances(self, deployed_only=True):
        next_token = None
        while True:
            kwargs = {'StatusFilter': 'DEPLOYMENT_SUCCEEDED'} if deployed_only else {}
            if next_token:
                kwargs['NextToken'] = next_token
            response = self._panorama.list_application_instances(**kwargs)
            for inst in response['ApplicationInstances']:
                yield inst
            if 'NextToken' in response:
                next_token = response['NextToken']
            else:
                break

    def _app_instance_data(self, application_instance_id):
        matches = [inst for inst in self._list_app_instances()
                   if inst.get('ApplicationInstanceId') == application_instance_id]
        return matches[0] if matches else None
