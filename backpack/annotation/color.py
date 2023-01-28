''' This module defines the :class:`~backpack.annotation.color.Color` class, an abstraction over
RGBA colors, as well ass :class:`~backpack.annotation.color.ColorMap`, that lets you easily access
frequently used colors.
'''

from dataclasses import dataclass
from typing import Union, Optional, Sequence, Mapping, OrderedDict
import collections
import hashlib

@dataclass(frozen=True)
class Color:
    ''' A color in the red, blue, green space.

    The color coordinates are integers in the [0; 255] range.

    Args:
        r (int): The red component of the color
        g (int): The green component of the color
        b (int): The blue component of the color
        alpha (float): The alpha channel of transparency, ranged from `0` to `1`
    '''
    r: int
    ''' The red component of the color. '''
    g: int
    ''' The green component of the color. '''
    b: int
    ''' The blue component of the color. '''
    alpha: float = 1.0
    ''' The alpha component of transparency. '''

    @classmethod
    def from_hex(cls, value: Union[str, int]) -> 'Color':
        ''' Creates a color object from its hexadecimal representation.

        Args:
            value: integer or HTML color string

        Returns:
            a new color object
        '''
        if isinstance(value, str):
            value = value.lstrip('#')
            rgb = tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
            return cls(*rgb)
        elif isinstance(value, int):
            rgb = tuple((value & (0xff << (i * 8))) >> (i * 8) for i in (2, 1, 0))
            return cls(*rgb)
        else:
            raise ValueError('Value argument must be str or int')

    @classmethod
    def from_value(cls, value: Union[str, int, Sequence, Mapping, 'Color']):
        ''' Converts an integer (interpreted as 3 bytes hex value), a HTML color string, a
        sequence of 3 or 4 integers, or a dictionary containing 'r', 'g', 'b' and optionally
        'alpha' keys to a Color object.

        Args:
            value: The value to be converted.

        Returns:
            The new Color object.

        Raises:
            ValueError: If the conversion was not successful.
        '''
        if isinstance(value, Color):
            return value
        if isinstance(value, (str, int)):
            return cls.from_hex(value)
        elif (
            isinstance(value, collections.abc.Sequence) and
            (len(value) == 3 or len(value) == 4) and
            all(isinstance(e, int if idx < 3 else float) for idx, e in enumerate(value))
        ):
            return cls(*value)
        elif (
            isinstance(value, collections.abc.Mapping) and
            'r' in value and 'g' in value and 'b' in value
        ):
            params = {k: v for k, v in value.items() if k in ('r', 'g', 'b')}
            alpha = value.get('a', value.get('alpha'))
            if alpha is not None:
                params['alpha'] = alpha
            return cls(**params)
        else:
            raise ValueError(f'Could not convert {value} to a Color')

    @classmethod
    def from_id(cls, identifier: int, salt: str = 'salt') -> 'Color':
        ''' Creates a pseudo-random color from an integer identifier.

        For the same identifier and salt the same color will be generated.

        Args:
            identifier: the identifier
            salt: the salt, change this if you want a different color for the same identifier

        Returns:
            A pseudo-random color based on the identifier and the salt.
        '''
        h = hashlib.md5((salt + str(identifier)).encode('utf-8')).digest()
        return Color(h[0], h[1], h[2])

    def brightness(self, brightness: float) -> 'Color':
        ''' Returns a new Color instance with changed brightness.

        Args:
            brightness: The new brightness, if greater than 1, a brighter color will be returned,
                if smaller than 1, a darker color.

        Returns:
            A new color instance with changed brightness.
        '''
        conv = lambda ch: min(255, int(ch * brightness))
        return Color(r=conv(self.r), g=conv(self.g), b=conv(self.b), alpha=self.alpha)

    def with_alpha(self, alpha: float) -> 'Color':
        ''' Returns a new Color instance with changed alpha.

        Args:
            alpha: The new alpha.

        Returns:
            A new color instance with changed alpha.
        '''
        return Color(r=self.r, g=self.g, b=self.b, alpha=alpha)


class ColorMap:
    ''' A simply color map implementation. '''

    colors: Mapping[str, Color] = OrderedDict()
    ''' A map of colors by name. Subclasses are supposed to override this argument. '''

    @classmethod
    def from_name(cls, name: str) -> Optional[Color]:
        ''' Returns a color from its name. '''
        return cls.colors.get(name)

    @classmethod
    def as_list(cls) -> Sequence[Color]:
        ''' Returns the colors of this color map as a list. '''
        return list(cls.colors.values())

    @classmethod
    def color_from_id(cls, identifier: int) -> Color:
        colors = cls.as_list()
        return colors[identifier % len(colors)]


class HTMLColors(ColorMap):
    ''' HTML Basic colors as of https://en.wikipedia.org/wiki/Web_colors#HTML_color_names '''

    WHITE   = Color(255, 255, 255)
    SILVER  = Color(192, 192, 192)
    GRAY    = Color(128, 128, 128)
    BLACK   = Color(  0,   0,   0)
    RED     = Color(255,   0,   0)
    MAROON  = Color(128, 128, 128)
    YELLOW  = Color(255, 255,   0)
    OLIVE   = Color(128, 128,   0)
    LIME    = Color(  0, 255,   0)
    GREEN   = Color(  0, 128,   0)
    AQUA    = Color(  0, 255, 255)
    TEAL    = Color(255, 128, 128)
    BLUE    = Color(  0,   0, 255)
    NAVY    = Color(  0,   0, 128)
    FUCHSIA = Color(255,   0, 255)
    PURPLE  = Color(128,   0, 128)

    colors: Mapping[str, Color] = OrderedDict([
        ('white', WHITE),
        ('silver', SILVER),
        ('gray', GRAY),
        ('black', BLACK),
        ('red', RED),
        ('maroon', MAROON),
        ('yellow', YELLOW),
        ('olive', OLIVE),
        ('lime', LIME),
        ('green', GREEN),
        ('aqua', AQUA),
        ('teal', TEAL),
        ('blue', BLUE),
        ('navy', NAVY),
        ('fuchsia', FUCHSIA),
        ('purple', PURPLE)
    ])
