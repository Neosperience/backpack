''' This module contains config serdes for objects from backpack.geometry module. '''

from typing import Optional
import dataclasses
import json

from backpack.geometry import PolyLine

from .serde import ConfigSerDeBase

class PolyLineSerDe(ConfigSerDeBase):
    ''' De/serializes a json string containing a polygon definition.

    Example string: ``[[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [0.5, 0.5], [0.1, 0.9]]``
    '''
    name : str = 'JSON encoded Polygon'

    @staticmethod
    def serialize(value: PolyLine) -> str:
        ''' Serializes a PolyLine into a string.

        Args:
            value (PolyLine): The PolyLine to be serialized.

        Returns:
            The PolyLine serialized into a string.
        '''
        return json.dumps(dataclasses.astuple(value)[0])

    @staticmethod
    def deserialize(value: str) -> Optional[PolyLine]:
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
