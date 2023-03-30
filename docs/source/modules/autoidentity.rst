.. _autoidentity-readme:

AutoIdentity
------------

When your application's code is running in a Panorama application, there is no official way to know
which device is running your app or which deployment version of your app is currently running.
:class:`~backpack.autoidentity.AutoIdentityFetcher` queries these details directly by calling AWS
Panorama management services based on the UID of your Application that you typically can find in the
``AppGraph_Uid`` environment variable. When instantiating the
:class:`~backpack.autoidentity.AutoIdentityFetcher` object, you should pass the AWS region name
where you provisioned the Panorama appliance. You can pass the region name, for example, as an
application parameter.

To successfully use :class:`~backpack.autoidentity.AutoIdentityFetcher`, you should grant the
execution of the following operations to the Panorama Application IAM Role:

 - ``panorama:ListApplicationInstances``

Example usage:

.. code-block:: python

    from backpack.autoidentity import AutoIdentityFetcher

    fetcher = AutoIdentityFetcher(device_region='us-east-1')
    auto_identity = fetcher.get_data()
    print(auto_identity)

The code above prints details of the running application in the CloudWatch log stream of your
Panorama app, something similar to::

    AutoIdentityData(
        application_instance_id='applicationInstance-0123456789abcdefghijklmn',
        application_name='sample_app',
        application_tags={'sample_tag': 'sample_value'},
        device_id='device-0123456789abcdefghijklmn',
        device_name='my_panorama',
        application_created_time=datetime.datetime(2022, 2, 22, 22, 22, 22),
        application_status='TEST',
        application_description='Sample application description'
    )

You can access all these details as the properties of the returned
:class:`~backpack.autoidentity.AutoIdentityData` object, for example, using
``auto_identity.application_description``.

For more information, refer to the :ref:`autoidentity API documentation <autoidentity-api>`.
