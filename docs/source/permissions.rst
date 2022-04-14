Configuring AWS Permissions
---------------------------

Several components of Backpack call AWS services in the account where your Panorama appliance is 
provisioned. To use these components, you should grant permissions to the Panorama Application 
IAM Role to use these services. Please refer to `Panorama Application IAM Role documentation`_ for 
more information. For each component, we will list the services required by the component. For 
example, :class:`~backpack.autoidentity.AutoIdentity` needs permission to execute the following 
AWS service operations:

 - ``panorama:ListApplicationInstances``

To make this component work correctly, you should include the following inline policy in the 
Panorama Application Role:

.. code-block:: yaml

  Policies:
    - PolicyName: panorama-listapplicationinstances
      PolicyDocument:
        Version: 2012-10-17
        Statement:
          - Effect: Allow
            Action: 'panorama:ListApplicationInstances'
            Resource: '*'

.. _`Panorama Application IAM Role documentation`: https://docs.aws.amazon.com/panorama/latest/dev/permissions-application.html