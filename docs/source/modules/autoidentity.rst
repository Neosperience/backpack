.. _autoidentity-readme:

AutoIdentity
------------

When your application's code is running in a Panorama application, there is no official way to know 
which device is running your app or which deployment version of your app is currently running. 
:class:`~backpack.autoidentity.AutoIdentity` queries these details directly by calling AWS Panorama 
management services based on the UID of your Application that you typically can find in the 
``AppGraph_Uid`` environment variable. When instantiating the 
:class:`~backpack.autoidentity.AutoIdentity` object, you should pass the AWS region name where 
you provisioned the Panorama appliance. You can pass the region name, for example, as an 
application parameter.

To successfully use :class:`~backpack.autoidentity.AutoIdentity`, you should grant the execution 
of the following operations to the Panorama Application IAM Role:

 - ``panorama:ListApplicationInstances``

Example usage:

.. code-block:: python

    from backpack.autoidentity import AutoIdentity

    auto_identity = AutoIdentity(device_region='us-east-1')
    print(auto_identity)

The code above prints details of the running application in the CloudWatch log stream of your 
Panorama app, something similar to::

    <AutoIdentity 
        application_created_time="2022-02-17 16:38:05.510000+00:00"
        application_description="Sample application description"
        application_instance_id="applicationInstance-0123456789abcdefghijklmn"
        application_name="sample_app"
        application_status="RUNNING"
        application_tags={"foo": "bar"}
        device_id="device-0123456789abcdefghijklmn"
        device_name="my_panorama"
    >

You can access all these details as the properties of the 
:class:`~backpack.autoidentity.AutoIdentity` object, for example, using 
``auto_identity.application_description``.

For more information, refer to the :ref:`autoidentity API documentation <autoidentity-api>`.
