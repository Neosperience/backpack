Installation
------------

Backpack consists of several loosely coupled components, each solving a specific task. Backpack 
python package is expected to be installed in the docker container of your Panorama application 
with pip, so you would add the following line to your ``Dockerfile``:

.. code-block:: docker

    RUN pip install git+https://github.com/neosperience/backpack.git

Some components have particular dependencies that can not be installed with the standard pip 
dependency resolver. For example, if you want to use :class:`~backpack.kvs.KVSSpyGlass` to restream 
the output video of your machine learning model to AWS Kinesis Video Streams, you should have 
several particularly configured libraries in the docker container to make everything work correctly. 
You will find detailed instructions and ``Dockerfile`` snippets in the rest of this documentation 
that will help you put together all dependencies.
