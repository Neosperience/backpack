.. _config-api:

config
======

.. automodule:: backpack.config

Defining config structures
--------------------------

.. automodule:: backpack.config.config

.. autoclass:: backpack.config.ConfigBase
   :members:
   :show-inheritance:

Command-line interface
----------------------

.. automodule:: backpack.config.tool
.. automethod:: backpack.config.cli


Defining serializers/deserializers
----------------------------------

.. automodule:: backpack.config.serde
.. autoclass:: backpack.config.ConfigSerDeBase
   :members:
   :show-inheritance:

List of SerDe implementations
-----------------------------

.. autoclass:: backpack.config.IntegerListSerDe
   :members:
   :show-inheritance:

.. autoclass:: backpack.config.geometry.PolyLineSerDe
   :members:
   :show-inheritance:
