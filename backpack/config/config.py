''' This module defines :class:`~backpack.config.ConfigBase`, a base class for Panorama application
configurations. The class offers two basic functionalities:

- parse parameters from the Panorama application input ports (``panoramasdk.node.inputs``)
- generate configuration file snippets for ``graph.json`` and ``package.json`` in your Panorama
  project. For more information about how to use the CLI, refer to :meth:`~backpack.config.tool`.
'''

import dataclasses
from typing import Sequence, List, Any, Type, TypeVar, Mapping, Tuple, Optional

from .serde import ConfigSerDeBase

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

    @staticmethod
    def _get_param_name(full_path: Sequence[str]=[]) -> str:
        return '_'.join(full_path)

    @staticmethod
    def _get_param_type(field: dataclasses.field) -> str:
        if 'type' in field.metadata:
            typename = field.metadata['type']
        else:
            typename = ConfigBase.TYPE_MAP.get(field.type)
        if typename is None:
            raise ValueError(f'Field has unsupported type: {field}')
        return typename

    @staticmethod
    def _get_param_serde(field: dataclasses.field) -> Optional[Type[ConfigSerDeBase]]:
        return field.metadata.get('serde')

    @staticmethod
    def _get_param_default(
        field: dataclasses.field,
        serde_metadata: Mapping[str, Any]
    ) -> Optional[str]:
        if field.default is not dataclasses.MISSING:
            default = field.default
        elif field.default_factory  is not dataclasses.MISSING:
            default = field.default_factory()
        else:
            default = None
        serde = ConfigBase._get_param_serde(field)
        if serde is not None and default is not None:
            default = serde.serialize(default, metadata=serde_metadata)
        return default

    @staticmethod
    def _get_param_doc(field: dataclasses.field) -> Optional[str]:
        return field.metadata.get('__doc__', field.metadata.get('doc'))

    def _param_walker(self, _current_path: Sequence[str]=[]) -> Tuple[str, dataclasses.field]:
        ''' Recursively walks all parameters in the config structure.

        Args:
            _current_path (Sequence[str]): The current path in the config structure. This is an
                internal recursion parameter and users should always leave the default empty
                list value.

        Returns:
            A generator that yields a tuple for each parameter. The tuple consists of the
            following values:
                - full_path (Sequence[str]): The full path of the parameter in the hierarchy
                - field (dataclasses.field): The original field of the
        '''
        fields = dataclasses.fields(self)
        for fld in fields:
            current_path = _current_path + [fld.name]
            if dataclasses.is_dataclass(fld.type):
                obj = getattr(self, fld.name)
                for sub_result in obj._param_walker(_current_path=current_path):
                    yield sub_result
            else:
                yield (current_path, fld)

    def get_panorama_definitions(self, serde_metadata: Mapping[str, Any]={}) -> List[Mapping[str, Any]]:
        ''' Generate the ``nodeGraph.nodes`` snippet in ``graph.json``.

        Returns:
            A list of dictionaries containing the application parameter node definitions.
        '''
        return [
            {
                'name': ConfigBase._get_param_name(full_path=full_path),
                'interface': ConfigBase._get_param_type(field=field),
                'value': ConfigBase._get_param_default(field=field, serde_metadata=serde_metadata),
                'overridable': True,
                'decorator': {
                    'title': ConfigBase._get_param_name(full_path=full_path),
                    'description': ConfigBase._get_param_doc(field=field)
                }
            }
            for (full_path, field) in self._param_walker()
        ]

    def get_panorama_edges(self, code_node_name: str) -> List[Mapping[str, str]]:
        ''' Generate the ``nodeGraph.edges`` snippet in ``graph.json``

        Returns:
            A list of dictionaries containing the application edge definitions.
        '''
        return [
            {
                "producer": ConfigBase._get_param_name(full_path=full_path),
                "consumer": code_node_name + "." + ConfigBase._get_param_name(full_path=full_path)
            }
            for (full_path, _) in self._param_walker()
        ]

    def get_panorama_app_interface(self) -> List[Mapping[str, str]]:
        ''' Generate the application interface snippet in app node ``package.json``.

        Returns:
            A list of dictionaries containing the elements of the application interface definition.
        '''
        return [
            {
                "name": ConfigBase._get_param_name(full_path=full_path),
                "type": ConfigBase._get_param_type(field=field)
            }
            for (full_path, field) in self._param_walker()
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
            f'| {ConfigBase._get_param_name(full_path=full_path)} '
            f'| {ConfigBase._get_param_type(field=field)} '
            f'| {ConfigBase._get_param_default(field=field, serde_metadata=serde_metadata)} '
            f'| {ConfigBase._get_param_doc(field=field)} |'
            for (full_path, field) in self._param_walker()
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

        for (full_path, fld) in result._param_walker():
            obj = result
            for name_part in full_path[:-1]:
                obj = getattr(obj, name_part)
            key = full_path[-1]
            name = ConfigBase._get_param_name(full_path=full_path)
            if not hasattr(inputs, name):
                continue
            value = getattr(inputs, name).get()
            serde = ConfigBase._get_param_serde(field=fld)
            if serde is not None:
                value = serde.deserialize(value, metadata=serde_metadata)
            setattr(obj, key, value)
        return result

    def asdict(self):
        return dataclasses.asdict(self)
