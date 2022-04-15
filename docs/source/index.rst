.. backpack documentation master file, created by
   sphinx-quickstart on Tue Apr 12 18:22:15 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Backpack
========

   `"Your hiking equipment for an enjoyable Panorama development experience"`

Backpack is a toolset that makes development for AWS Panorama hopefully more enjoyable. AWS Panorama
is a machine learning appliance and software development kit that can be used to develop intelligent
video analytics and computer vision applications deployed on an edge device. For more information,
refer to the `Panorama page`_ on the AWS website.

.. _`Panorama page`: https://aws.amazon.com/panorama/

Getting started
^^^^^^^^^^^^^^^

The :ref:`installation` and the :ref:`permissions` section describes how to configure your Panorama
application to work with Backpack. Some modules of Backpack needs third party libraries installed
in the docker container of your application. The relevant sections of the documentation contain the
``Dockerfile`` snippets that you will have to use.

For an overview of what you can find in Backpack, refer to the :ref:`modules` section. If you need
more details, you can find it in the low-level :ref:`api`.

.. toctree::
   :maxdepth: 3
   
   self
   install
   permissions
   modules/index
   api/index

Indices and tables
^^^^^^^^^^^^^^^^^^

* :ref:`genindex`
* :ref:`modindex`

