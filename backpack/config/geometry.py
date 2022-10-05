''' This module contains config serdes for objects from backpack.geometry module. '''

from typing import Optional, Mapping, Any
import dataclasses
import json

from backpack.geometry import PolyLine

from .serde import ConfigSerDeBase

class PolyLineSerDe(ConfigSerDeBase):
    ''' De/serializes a json string containing a polygon definition.

    Example string: ``[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.5, 0.5], [0.1, 0.9]]``
    '''
    description : str = 'JSON encoded Polygon'
    example: str = '[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.5, 0.5], [0.1, 0.9]]'

    @staticmethod
    def serialize(value: PolyLine, metadata: Mapping[str, Any]={}) -> str:
        ''' Serializes a PolyLine into a string.

        Args:
            value (PolyLine): The PolyLine to be serialized.

        Returns:
            The PolyLine serialized into a string.
        '''
        return json.dumps(dataclasses.astuple(value)[0])

    @staticmethod
    def deserialize(value: str, metadata: Mapping[str, Any]={}) -> Optional[PolyLine]:
        '''
        Restores a PolyLine from a string.

        Args:
            value (str): A string containing a serialized PolyLine.

        Returns:
            The PolyLine restored from the string or None if the string was empty.

        Raises:
            Exception: exceptions related to invalid string format.
        '''
        return (
            PolyLine.from_value(json.loads(value))
                if value is not None and len(value) > 0 else
            None
        )
