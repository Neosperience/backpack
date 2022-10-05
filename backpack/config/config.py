''' This module defines :class:`~backpack.config.ConfigBase`, a base class for Panorama application
configurations. The class offers two basic functionalities:

- parse parameters from the Panorama application input ports (``panoramasdk.node.inputs``)
- generate configuration file snippets for ``graph.json`` and ``package.json`` in your Panorama
  project. For more information about how to use the CLI, refer to :meth:`~backpack.config.tool`.
'''

import dataclasses
from typing import Sequence, List, Any, Type, TypeVar, Mapping
import dataclasses

T = TypeVar('T', bound='ConfigBase')

class ConfigBase:
    ''' Base class for configuration structures.

    Subclasses must be also dataclasses.
    '''

    TYPE_MAP = {
        int: 'int32',
        float: 'float32',
        str: 'string',
        bool: 'boolean'
    }

    def __init__(self) -> None:
        assert dataclasses.is_dataclass(self), 'ConfigBase instances must be also dataclasses.'

    def param_walker(self,
        prefix: Sequence[List]=[],
        serde_metadata: Mapping[str, Any]={}
    ):
        fields = dataclasses.fields(self)
        for fld in fields:
            name_components = prefix + [fld.name]
            if dataclasses.is_dataclass(fld.type):
                obj = getattr(self, fld.name)
                for sub_result in obj.param_walker(prefix=name_components, serde_metadata=serde_metadata):
                    yield sub_result
            else:
                # Get type name
                if 'type' in fld.metadata:
                    typename = fld.metadata['type']
                else:
                    typename = ConfigBase.TYPE_MAP.get(fld.type)
                if typename is None:
                    raise ValueError(f'Dataclass {self} field has unsupported type: {fld}')

                # Get default value
                if fld.default is not dataclasses.MISSING:
                    default = fld.default
                elif fld.default_factory  is not dataclasses.MISSING:
                    default = fld.default_factory()
                else:
                    default = None

                # Get serde
                serde = fld.metadata.get('serde')
                if serde is not None and default is not None:
                    default = serde.serialize(default, metadata=serde_metadata)

                name = '_'.join(name_components)
                doc = fld.metadata.get('__doc__', fld.metadata.get('doc'))
                yield (name, typename, default, doc, name_components, fld)

    def get_panorama_definitions(self,
        serde_metadata: Mapping[str, Any]={}
    ) -> List[Mapping[str, Any]]:
        ''' Generate the ``nodeGraph.nodes`` snippet in ``graph.json``.

        Returns:
            A list of dictionaries containing the application parameter node definitions.
        '''
        return [
            {
                'name': name,
                'interface': typename,
                'value': default,
                'overridable': True,
                'decorator': {
                    'title': name,
                    'description': doc
                }
            }
            for (name, typename, default, doc, *_) in self.param_walker(serde_metadata=serde_metadata)
        ]

    def get_panorama_edges(self,
        code_node_name: str,
        serde_metadata: Mapping[str, Any]={}
    ) -> List[Mapping[str, str]]:
        ''' Generate the ``nodeGraph.edges`` snippet in ``graph.json``

        Returns:
            A list of dictionaries containing the application edge definitions.
        '''
        return [
            {
                "producer": name,
                "consumer": code_node_name + "." + name
            }
            for (name, *_) in self.param_walker(serde_metadata=serde_metadata)
        ]

    def get_panorama_app_interface(self,
        serde_metadata: Mapping[str, Any]={}
    ) -> List[Mapping[str, str]]:
        ''' Generate the application interface snippet in app node ``package.json``.

        Returns:
            A list of dictionaries containing the elements of the application interface definition.
        '''
        return [
            {
                "name": name,
                "type": typename
            }
            for (name, typename, *_) in self.param_walker(serde_metadata=serde_metadata)
        ]

    def get_panorama_markdown_doc(self, serde_metadata: Mapping[str, Any]={}) -> str:
        ''' Generates a markdown table of the parameters that can be used in documentation.

        Returns:
            Markdown formatted text containing the parameter documentation.
        '''
        header = (
            '| name | type    | default | description |\n'
            '|------|---------|---------|-------------|\n'
        )
        body = '\n'.join([
            f'| {name} | {typename} | {default} | {doc} |'
            for name, typename, default, doc, *_ in self.param_walker(serde_metadata=serde_metadata)
        ])
        return header + body

    @classmethod
    def from_panorama_params(cls: Type[T],
        inputs: 'panoramasdk.port',
        serde_metadata: Mapping[str, Any]={}
    ) -> T:
        ''' Parses the config values form AWS Panorama input parameters.

        A new Config object is created with the default values. If a particular value is
        found in the input parameter, its value will override the default value.

        Args:
            inputs (panoramasdk.port): The input port of the Panorama application node.

        Returns:
            The config instance filled with the parameter values read from the input port.
        '''
        result = cls()
        for name, typename, default, doc, name_components, f in result.param_walker(serde_metadata=serde_metadata):
            obj = result
            for name_part in name_components[:-1]:
                obj = getattr(obj, name_part)
            key = name_components[-1]
            if not hasattr(inputs, name):
                continue
            value = getattr(inputs, name).get()
            serde = f.metadata.get('serde')
            if serde is not None:
                value = serde.deserialize(value, metadata=serde_metadata)
            setattr(obj, key, value)
        return result

    def asdict(self):
        return dataclasses.asdict(self)
