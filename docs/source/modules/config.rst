.. _config-readme:

Config
------

Config module provides a way to standardize the configuration of Panorama applications via
deploy-time parameters. It can automatically parse deploy-time parameters from the Panorama
application's input port to a Python `dataclass`_ based configuration structure. It also provides
a development tool: a small command-line interface program that can be used to generate JSON
snippets to be pasted into the Panorama application's ``graph.json``, the business logic package
definition file ``package.json``, or even generate markdown documentation about the usage of the
parameters.

This pattern helps you to have a single source of truth about your application parameters: a
:class:`~backpack.config.config.ConfigBase` subclass that you implement.

.. _`dataclass`: https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass


Defining the config structure
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You should define the configuration parameters of your application in a
:class:`~backpack.config.ConfigBase` subclass. You can use primitive parameter types supported
by Panorama SDK (``int``, ``float``, ``str`` and ``bool``), make `ConfigBase` parse custom
structures from a string or numeric value, and define cascaded configuration. The following
example showcases these features:

.. code-block:: python

    # my_object_detector_config.py
    from typing import Sequence
    from dataclasses import dataclass, field
    from backpack.config import ConfigBase, IntegerListSerDe, cli

    @dataclass
    class MyObjectDetectorConfig(ConfigBase):

        example_string_param: str = field(default='default_value', metadata={
            'doc': 'This is an example string parameter.'
        })
        example_int_param: int = field(default=42, metadata={
            'doc': 'This is an example integer parameter.'
        })
        example_float_param: float = field(default=0.85, metadata={
            'doc': 'This is an example float parameter.'
        })
        example_bool_param: str = field(default=True, metadata={
            'doc': 'This is an example bool parameter.'
        })
        example_integer_list_param: Sequence[int] = field(default=(1, 2, 3, 5, 8, 13), metadata={
            'doc': 'A comma-separated list of integers.',
            'type': 'string',
            'serde': IntegerListSerDe
        })

        @dataclass
        class EmbeddedConfig(ConfigBase):
            embedded_param: int = field(default=84, metadata={
                'doc': 'This is an embedded parameter.'
            })

        child_struct: EmbeddedConfig = EmbeddedConfig()

    if __name__=='__main__':
        cli('my_object_detector', MyObjectDetectorConfig())

The above class defines the config application config structure as a standard Python
`dataclass`_. :class:`~backpack.config.ConfigBase` searches for several keys in the field
metadata dictionary to support full functionality. The following metadata keys are defined:

- ``doc``: a textual description of the parameter that will be used in the application descriptor
  ``graph.json`` as well as in the markdown documentation
- ``type``: ConfigBase will try to infer the Panorama config type (``int32``, ``float32``,
  ``string`` or ``boolean``) from the Python type. However, for parsed config types you should
  manually define the Panorama config type in this field.
- ``serde``: SerDes (serializer/deserializer) lets ConfigBase automatically convert a raw string
  or number parameter value to a complex Python structure. The ``example_integer_list_param``
  parameter in the above example demonstrates the usage of ``IntegerListSerDe`` that converts
  a string containing a comma-separated list of numbers (for example, ``"1, 1, 2, 3, 5, 8, 13"``)
  to a proper Python list of integers. You should define the SerDe class to be used with
  this key.


Using the developer tool
^^^^^^^^^^^^^^^^^^^^^^^^

You are encouraged to define the command-line interface (CLI) of your config structure adding
a call to the :meth:`~backpack.config.tool` method, behind the main module guard. This is
illustrated in the last two lines of the example above. If you saved the config structure in a file
named ``my_object_detector_config.py``, you can execute the following command from the directory
where the file can be found::

    $ python -m my_object_detector_config -h

The CLI help should guide you through the usage of the tool:

.. code-block:: text

    usage: config.py [-h] [--code-node CODE_NODE] [--template TEMPLATE]
                 {nodes,edges,interface,markdown,render}

    Configuration snippet generator for my_object_detector application.

    This program can generate json and markdown snippets that you can copy-paste to the
    metadata and package definitions of your AWS Panorama project. The snippets contain the
    definitions of the application parameters in the required format. The following formats
    are supported:

    - nodes: generates a json snippet to be pasted in the nodeGraph.nodes field of graph.json
    - edges: generates a json snippet to be pasted in the nodeGraph.edges field of graph.json.
        Specify the code node name.
    - interface: generates json a snippet to be pasted in nodePackage.interfaces field of the
        package.json of the application code package
    - markdown: generates a markdown snippet that you can paste to the README of your project,
        or other parts of the documentation.
    - render: renders a Jinja2 template. Specify the template filename and the code node name.

    positional arguments:
    {nodes,edges,interface,markdown,render}
                            Prints configuration snippets for graph.json nodes, edges,
                            application interface in package.json, or in markdown format.

    optional arguments:
    -h, --help            show this help message and exit
    --code-node CODE_NODE, -c CODE_NODE
                            Code node name (used in edges snippet)
    --template TEMPLATE, -t TEMPLATE
                            Template file (used in render command)

For example, the following call::

     $ python -m my_object_detector_config nodes --code-node my_object_detector_business_logic

will generate the following json snippet, ready to be pasted into ``graph.json``:

.. code-block:: json

    [
        {
            "name": "example_string_param",
            "interface": "string",
            "value": "default_value",
            "overridable": true,
            "decorator": {
                "title": "example_string_param",
                "description": "This is an example string parameter."
            }
        },
        {
            "name": "example_int_param",
            "interface": "int32",
            "value": 42,
            "overridable": true,
            "decorator": {
                "title": "example_int_param",
                "description": "This is an example integer parameter."
            }
        },
        {
            "name": "example_float_param",
            "interface": "float32",
            "value": 0.85,
            "overridable": true,
            "decorator": {
                "title": "example_float_param",
                "description": "This is an example float parameter."
            }
        },
        {
            "name": "example_bool_param",
            "interface": "string",
            "value": true,
            "overridable": true,
            "decorator": {
                "title": "example_bool_param",
                "description": "This is an example bool parameter."
            }
        },
        {
            "name": "example_integer_list_param",
            "interface": "string",
            "value": "1, 1, 2, 3, 5, 8, 13",
            "overridable": true,
            "decorator": {
                "title": "example_integer_list_param",
                "description": "A comma-separated list of integers."
            }
        },
        {
            "name": "child_struct_embedded_param",
            "interface": "int32",
            "value": 84,
            "overridable": true,
            "decorator": {
                "title": "child_struct_embedded_param",
                "description": "This is an embedded parameter."
            }
        }
    ]

You can also write your ``graph.json``, application ``package.json`` and markdown documentation
as `Jinja2`_ templates. In this case you can automatize the update of these artifacts after
modifying your :class:`~backpack.config.ConfigBase` subclass. The config tool CLI offers the
following template variables:

- ``nodes``: list of dictionaries containing the nodes to be placed in ``graph.json``
- ``edges``: list of dictionaries containing the edges to be placed in ``graph.json``
- ``interface``: list of dictionaries containing the interface to be placed in application's
    ``package.json``
- ``markdown``: Markdown documentation as string.

.. _`Jinja2`: https://jinja.palletsprojects.com/

For example, you could use the following template ``graph.json.jinja`` for your manifest:

.. code-block:: jinja

    {
        "nodeGraph": {
            "envelopeVersion": "2021-01-01",
            "packages": [
                {
                    "name": "panorama::abstract_rtsp_media_source",
                    "version": "1.0"
                },
                {
                    "name": "panorama::hdmi_data_sink",
                    "version": "1.0"
                },
                {
                    "name": "123456789012::my_app_logic",
                    "version": "1.0"
                },
                {
                    "name": "123456789012::my_model",
                    "version": "1.0"
                }
            ],
            "nodes": [
                {
                    "name": "camera_input",
                    "interface": "panorama::abstract_rtsp_media_source.rtsp_v1_interface",
                    "overridable": true,
                    "launch": "onAppStart",
                    "decorator": {
                        "title": "Camera camera_input",
                        "description": "Abstract camera input of the application."
                    }
                },
                {
                    "name": "display_output",
                    "interface": "panorama::hdmi_data_sink.hdmi0",
                    "overridable": false,
                    "launch": "onAppStart"
                },
                {
                    "name": "my_model_node",
                    "interface": "123456789012::my_model.interface",
                    "overridable": false,
                    "launch": "onAppStart"
                },
                {
                    "name": "my_app_logic_node",
                    "interface": "123456789012::my_app_logic.interface",
                    "overridable": false,
                    "launch": "onAppStart"
                }{{ "," if nodes|length > 0 else "" }}
    {% for node in nodes %}
                {{ node|to_pretty_json|indent(width=12) }}{{ "," if not loop.last else "" }}
    {% endfor %}
            ],
            "edges": [
                {
                    "producer": "camera_input.video_out",
                    "consumer": "my_app_logic_node.video_in"
                },
                {
                    "producer": "my_app_logic_node.video_out",
                    "consumer": "display_output.video_in"
                }{{ "," if nodes|length > 0 else "" }}
    {% for edge in edges %}
                {{ edge|to_pretty_json|indent(width=12) }}{{ "," if not loop.last else "" }}
    {% endfor %}
            ]
        }
    }

Using this template, you can generate your ``graph.json`` with::

    $ python -m my_object_detector_config render \
        --code-node my_object_detector_business_logic \
        --template path_to/graph.json.jinja \
        > path_to/graph.json

An example ``package.json.jinja`` template:

.. code-block:: jinja

    {
        "nodePackage": {
            "envelopeVersion": "2021-01-01",
            "name": "my_app_logic",
            "version": "1.0",
            "description": "Default description for package my_app_logic",
            "assets": [
                {
                    "name": "my_app_logic_logic_asset",
                    "implementations": [
                        {
                            "type": "container",
                            "assetUri": "deadbeaf.tar.gz",
                            "descriptorUri": "deadbeaf.json"
                        }
                    ]
                }
            ],
            "interfaces": [
                {
                    "name": "interface",
                    "category": "business_logic",
                    "asset": "my_app_logic_logic_asset",
                    "inputs": [
                        {
                            "name": "video_in",
                            "type": "media"
                        }{{ "," if interface|length > 0 else "" }}
    {% for item in interface %}
                        {{ item|to_pretty_json|indent(width=20) }}{{ "," if not loop.last else "" }}
    {% endfor %}
                    ],
                    "outputs": [
                        {
                            "name": "video_out",
                            "type": "media"
                        }
                    ]
                }
            ]
        }
    }
