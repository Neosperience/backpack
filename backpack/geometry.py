''' 2D geometry primitives and implementation of some geometric algorithms. '''

from typing import List, Sequence, Tuple
import enum
import collections.abc
from dataclasses import dataclass
import math
from itertools import islice, cycle, groupby
from numbers import Number
import numpy as np

from . import lazy_property

def _issequence(value):
    ''' Returns True if value is a sequence but not a string. '''
    return isinstance(value, collections.abc.Sequence) and not isinstance(value, str)

def _issequence_or_numpy(value):
    return _issequence(value) or isinstance(value, np.ndarray)

class PointMeta(type):
    @classmethod
    def __instancecheck__(cls, instance):
        ''' Any object that has 'x' and 'y' attributes might be considered a Point '''
        return hasattr(instance, 'x') and hasattr(instance, 'y')

@dataclass(frozen=True)
class Point(metaclass=PointMeta):
    ''' A point on the 2D plane.

    Args:
        x (float): The x coordinate of the point
        y (float): The y coordinate of the point
    '''
    x: float
    ''' The x coordinate of the point '''

    y: float
    ''' The y coordinate of the point '''

    @staticmethod
    def ccw(pt1: 'Point', pt2: 'Point', pt3: 'Point') -> bool:
        ''' Determines if the three points form a counterclockwise angle. If two points are
        equal, or the three points are collinear, this method returns `True`.

        Args:
            pt1: The first point
            pt2: The second point
            pt3: The third point

        Returns:
            `True` if the points form a counterclockwise angle
        '''
        d21, d31 = pt2 - pt1, pt3 - pt1
        return d21.x * d31.y >= d31.x * d21.y

    def distance(self, other: 'Point') -> float:
        ''' Calculates the distance between this and an other point.

        Args:
            other: The other point

        Returns:
            The distance between this and an other point.
        '''
        d = self - other
        return math.sqrt(d.x * d.x + d.y * d.y)

    @classmethod
    def _check_arg(cls, arg, method_name):
        if not isinstance(arg, cls):
            raise TypeError(
                f"unsupported operand type(s) for {method_name}: "
                f"'{cls.__name__}' and '{type(arg).__name__}'"
            )

    def __add__(self, other: 'Point') -> 'Point':
        ''' Adds two points as if they were vectors.

        Arg:
            other: the other point

        Returns:
            A new point, the sum of the two points as if they were vectors.
        '''
        Point._check_arg(other, '+')
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        ''' Subtracts two points as if they were vectors.

        Arg:
            other: the other point

        Returns:
            A new point, the difference of the two points as if they were vectors.
        '''
        Point._check_arg(other, '-')
        return Point(self.x - other.x, self.y - other.y)

    def __truediv__(self, divisor: float) -> 'Point':
        ''' Interpret this point as a vector and divide it by a real number.

        Args:
            divisor: a real number

        Returns:
            The original point divided by the number as if it was a vector.
        '''
        return Point(self.x / divisor, self.y / divisor)


    def __getitem__(self, key: int) -> float:
        ''' Returns the first or the second coordinate of this Point.'''
        if not isinstance(key, int):
            raise TypeError('Point indices must be integers.')
        if key == 0:
            return self.x
        elif key == 1:
            return self.y
        else:
            raise IndexError(str(key))

    @classmethod
    def from_value(cls, value):
        ''' Deserializes a Point from different formats.

        Supported formats:

         - sequence containing exactly two numbers
         - dictionary containing numbers under 'x' and 'y' keys
         - Point instance (returns the same instance)

        Args:
            value: the value to be converted

        Return: The new Point instance

        Raises:
            ValueError: If the conversion was not successful.
        '''
        if isinstance(value, Point):
            return value
        elif isinstance(value, collections.abc.Mapping) and 'x' in value and 'y' in value:
            return cls(x=value['x'], y=value['y'])
        elif (
            _issequence(value) and
            len(value) == 2 and
            isinstance(value[0], Number) and
            isinstance(value[1], Number)
        ):
            return cls(x=value[0], y=value[1])
        else:
            raise ValueError(f'Could not convert {value} to Point.')


@dataclass(frozen=True)
class Line:
    ''' A line segment.

    Args:
        pt1 (float): The first point of the line segment
        pt2 (float): The second point of the line segment
    '''

    class Intersection(enum.Enum):
        ''' The intersection type of two line segments. '''

        LEFT = -1
        ''' The second segment intersects the first one in left direction. '''

        NONE = 0
        ''' The two segments do not intersect. '''

        RIGHT = 1
        ''' The second segment intersects the first one in right direction. '''

        def __bool__(self) -> bool:
            return bool(self.value)

    pt1: Point
    ''' The first point of the line segment '''

    pt2: Point
    ''' The second point of the line segment '''

    def __post_init__(self):
        if not isinstance(self.pt1, Point) or not isinstance(self.pt2, Point):
            raise ValueError('Line arguments "pt1" and "pt2" must be Point objects.')

    def intersects(self, other: 'Line') -> Intersection:
        ''' Determines if this line segment intersects an other one.

        The direction of intersection is interpreted as follows. Place an observer to the first
        point of this line, looking to the second point of this line. If the second point of the
        other line is on the left side, the directions of the intersection is "left", otherwise
        it is "right". Attention: when considering the line intersection direction, keep in mind
        that the geometry module uses the screen coordinate system orientation, i.e. the origin
        can be found in the upper left corner of the screen.

        Args:
            other (Line): The other line segment

        Returns:
            The line intersection type.
        '''
        if (
            Point.ccw(self.pt1, other.pt1, other.pt2) == Point.ccw(self.pt2, other.pt1, other.pt2) or
            Point.ccw(self.pt1, self.pt2, other.pt1) == Point.ccw(self.pt1, self.pt2, other.pt2)
        ):
            return Line.Intersection.NONE
        else:
            return (
                Line.Intersection.LEFT if Point.ccw(self.pt1, self.pt2, other.pt1)
                else Line.Intersection.RIGHT
            )

    @classmethod
    def from_value(cls, value):
        ''' Deserializes a Line from different formats.

        Supported formats:

         - sequence containing exactly two values that can be deserialized with Point.from_value
         - dictionary containing such Point values under 'pt1' and 'pt2' keys
         - Line instance (returns the same instance)

        Args:
            value: the value to be converted

        Returns:
            The Line instance

        Raises:
            ValueError: If the value could not be converted to a Line.
        '''
        if isinstance(value, Line):
            return value
        elif _issequence(value) and len(value) == 2:
            return cls(pt1=Point.from_value(value[0]), pt2=Point.from_value(value[1]))
        elif isinstance(value, collections.abc.Mapping) and 'pt1' in value and 'pt2' in value:
            return cls(pt1=Point.from_value(value['pt1']), pt2=Point.from_value(value['pt2']))
        else:
            raise ValueError(f'Could not convert {value} to Line.')

    def __getitem__(self, key: int) -> Point:
        ''' Returns the first or the second point of this Line.

        Args:
            key: the index passed to the bracket operator, must be 0 or 1.

        Returns:
            The first or the second point of this Line.
        '''
        if not isinstance(key, int):
            raise TypeError('Line indices must be integers.')
        if key == 0:
            return self.pt1
        elif key == 1:
            return self.pt2
        else:
            raise IndexError(str(key))


@dataclass(frozen=True)
class Rectangle:
    ''' An axis aligned rectangle.

    Args:
        pt1 (Point): The first corner of the rectangle
        pt2 (Point): The second corner of the rectangle
    '''

    pt1: Point
    ''' The first corner of the rectangle '''

    pt2: Point
    ''' The second corner of the rectangle '''

    def __post_init__(self):
        if not isinstance(self.pt1, Point) or not isinstance(self.pt2, Point):
            raise ValueError('Rectangle arguments "pt1" and "pt2" must be Point objects.')

    def has_inside(self, pt: Point) -> bool:
        ''' Determines if a point is inside this rectangle.

        Args:
            pt: the point

        Returns:
            `True` if the point lies inside this rectangle.
        '''
        return (
            pt.x >= self.pt_min.x and pt.y >= self.pt_min.y and
            pt.x <= self.pt_max.x and pt.y <= self.pt_max.y
        )

    @lazy_property
    def pt_min(self) -> Point:
        ''' The point with the minimum coordinates of this rectangle. '''
        return Point(min(self.pt1.x, self.pt2.x), min(self.pt1.y, self.pt2.y))

    @lazy_property
    def pt_max(self) -> Point:
        ''' The point with the maximum coordinates of this rectangle. '''
        return Point(max(self.pt1.x, self.pt2.x), max(self.pt1.y, self.pt2.y))

    @lazy_property
    def center(self) -> Point:
        ''' The center of the rectangle. '''
        return Point((self.pt_min.x + self.pt_max.x) / 2, (self.pt_min.y + self.pt_max.y) / 2)

    @lazy_property
    def base(self) -> Point:
        ''' Returns the center of the base of the rectangle. '''
        return Point((self.pt_min.x + self.pt_max.x) / 2, self.pt_max.y)

    @lazy_property
    def size(self) -> Tuple[float, float]:
        ''' The width and height of the rectangle. '''
        return self.width, self.height

    @lazy_property
    def width(self) -> float:
        ''' The width of the rectangle. '''
        return self.pt_max.x - self.pt_min.x

    @lazy_property
    def height(self) -> float:
        ''' The height of the rectangle. '''
        return self.pt_max.y - self.pt_min.y

    @lazy_property
    def area(self) -> float:
        ''' The area of the rectangle. '''
        return self.width * self.height

    @lazy_property
    def aspect_ratio(self) -> float:
        ''' The aspect ratio of the rectangle. '''
        return self.width / self.height

    @property
    def top(self) -> float:
        ''' The top edge of the rectangle. '''
        return self.pt_min.y

    @property
    def left(self) -> float:
        ''' The left edge of the rectangle. '''
        return self.pt_min.x

    @property
    def bottom(self) -> float:
        ''' The bottom edge of the rectangle. '''
        return self.pt_max.y

    @property
    def right(self) -> float:
        ''' The right edge of the rectangle. '''
        return self.pt_max.x

    @property
    def tlbr(self) -> Tuple[float, float, float, float]:
        ''' Returns this rectangles coordinates as a top-left-bottom-right tuple. '''
        return self.top, self.left, self.bottom, self.right

    @property
    def tlhw(self) -> Tuple[float, float, float, float]:
        ''' Returns this rectangles coordinates as a top-left-width-height tuple. '''
        return self.top, self.left, self.height, self.width

    @classmethod
    def from_value(cls, value):
        ''' Converts a tuple in the form of ((0.1, 0.2), (0.3, 0.4)) to a Rectangle.

        Args:
            value: the tuple

        Returns:
            The Rectangle instance

        Raises:
            ValueError: If the tuple could not be converted to a Rectangle.
        '''
        if isinstance(value, Rectangle):
            return value
        elif _issequence(value) and len(value) == 2:
            return cls(pt1=Point.from_value(value[0]), pt2=Point.from_value(value[1]))
        elif isinstance(value, collections.abc.Mapping) and 'pt1' in value and 'pt2' in value:
            return cls(pt1=Point.from_value(value['pt1']), pt2=Point.from_value(value['pt2']))
        else:
            raise ValueError(f'Could not convert {value} to Rectangle.')


    @classmethod
    def from_tlbr(cls, tlbr: Tuple[float, float, float, float]) -> 'Rectangle':
        ''' Converts a top-left-bottom-right sequence of floats to a Rectangle.

        Args:
            tlbr: A top-left-bottom-right sequence of floats.

        Returns:
            The Rectangle instance

        Raises:
            ValueError: If the sequence could not be converted to a Rectangle.
        '''
        if _issequence_or_numpy(tlbr) and len(tlbr) == 4:
            return cls(pt1=Point(x=tlbr[1], y=tlbr[0]), pt2=Point(x=tlbr[3], y=tlbr[2]))
        else:
            raise ValueError(f'Could not use {tlbr} as top-left-bottom-right sequence.')

    @classmethod
    def from_tlhw(cls, tlhw: Tuple[float, float, float, float]) -> 'Rectangle':
        ''' Converts a top-left-width-height sequence of floats to a Rectangle.

        Args:
            tlbr: A top-left-width-height sequence of floats.

        Returns:
            The Rectangle instance

        Raises:
            ValueError: If the sequence could not be converted to a Rectangle.
        '''
        if _issequence_or_numpy(tlhw) and len(tlhw) == 4:
            return cls(
                pt1=Point(x=tlhw[1], y=tlhw[0]),
                pt2=Point(x=tlhw[1]+tlhw[3], y=tlhw[0]+tlhw[2])
            )
        else:
            raise ValueError(f'Could not use {tlhw} as top-left-width-height sequence.')

    def __getitem__(self, key: int) -> float:
        ''' Returns the first or the second point of this Rectangle.

        Args:
            key: the index passed to the bracket operator, must be 0 or 1.

        Returns:
            The first or the second point of this Rectangle.
        '''
        if not isinstance(key, int):
            raise TypeError('Point.__getitem__ accepts only integer keys.')
        if key == 0:
            return self.pt_min
        elif key == 1:
            return self.pt_max
        else:
            raise IndexError(str(key))


@dataclass(frozen=True)
class PolyLine:
    ''' A :class:`PolyLine` is a connected series of line segments.

    Args:
        points: the list of the points of the polyline
        closed: `True` if the :class:`PolyLine` is closed
    '''

    points : Sequence[Point]
    ''' The list of the points of the :class:`PolyLine` '''

    closed : bool = True
    ''' `True` if the :class:`PolyLine` is closed. '''

    def __post_init__(self):
        if not isinstance(self.points, collections.abc.Sequence):
            raise ValueError('PolyLine points argument must be a Sequence.')
        if len(self.points) < 2:
            raise ValueError('PolyLine should contain at least two points.')
        for pt in self.points:
            if not isinstance(pt, Point):
                raise ValueError('The elements of PolyLine points argument must be Point objects.')

    @lazy_property
    def lines(self) -> List[Line]:
        ''' The line segments of this :class:`PolyLine` '''
        lines = [Line(start, end) for start, end in zip(self.points, self.points[1:])]
        if self.closed:
            lines.append(Line(self.points[-1], self.points[0]))
        return lines

    @lazy_property
    def boundingbox(self) -> Rectangle:
        ''' The bounding box of this :class:`PolyLine` '''
        minx = min(pt.x for pt in self.points)
        miny = min(pt.y for pt in self.points)
        maxx = max(pt.x for pt in self.points)
        maxy = max(pt.y for pt in self.points)
        return Rectangle(Point(minx, miny), Point(maxx, maxy))

    @lazy_property
    def self_intersects(self) -> bool:
        ''' Determines if this :class:`PolyLine` self-intersects. '''
        return any(
            l1.intersects(l2)
                for idx, l1 in enumerate(self.lines) for l2 in self.lines[idx + 2:]
        )

    @lazy_property
    def is_convex(self) -> bool:
        ''' Determines if the polygon formed from this :class:`PolyLine` is convex.

        The result of this method is undefined for complex (self-intersecting) polygons.

        Returns:
            `True` if the polygon is convex, False otherwise.
        '''
        if len(self.points) < 4:
            return True

        # Iterate over consecutive point triplets
        it0 = self.points
        it1 = islice(cycle(self.points), 1, None)
        it2 = islice(cycle(self.points), 2, None)

        # Check if all angles are ccw, see
        # https://docs.python.org/3/library/itertools.html#itertools-recipes
        group = groupby(
            Point.ccw(pt0, pt1, pt2) for pt0, pt1, pt2 in zip(it0, it1, it2)
        )
        return next(group, True) and not next(group, False)

    def has_inside(self, point: Point) -> bool:
        ''' Determines if a point is inside this closed :class:`PolyLine`.

        This implementation uses the `ray casting algorithm`_.

        .. _`ray casting algorithm`:
           https://en.wikipedia.org/wiki/Point_in_polygon#Ray_casting_algorithm

        Args:
            point: The point

        Returns:
            `True` if the point is inside this closed :class:`PolyLine`.
        '''
        if not self.closed:
            raise ValueError('PolyLine.has_inside works only for closed polylines.')
        if not self.boundingbox.has_inside(point):
            return False
        ray = Line(Point(self.boundingbox.pt_min.x - 0.01, self.boundingbox.pt_min.y), point)
        n_ints = sum(1 if ray.intersects(line) else 0 for line in self.lines)
        return True if n_ints % 2 == 1 else False

    @classmethod
    def from_value(cls, value, closed=True):
        ''' Converts a tuple in the form of ((0.1, 0.2), (0.3, 0.4), ...) to a PolyLine.

        Args:
            value: the tuple
            closed: flags if the newly created PolyLine should be closed or not.

        Returns:
            The PolyLine instance

        Raises:
            ValueError: If the tuple could not be converted to a PolyLine.
        '''
        if isinstance(value, PolyLine):
            return value
        elif _issequence(value):
            return cls(points=[Point.from_value(pt) for pt in value], closed=closed)
        elif isinstance(value, collections.abc.Mapping) and 'points' in value:
            closed = bool(value.get('closed', closed))
            return cls(points=[Point.from_value(pt) for pt in value['points']], closed=closed)
        else:
            raise ValueError(f'Could not convert {value} to PolyLine')

    def __getitem__(self, key: int) -> Point:
        ''' Returns a single point of this PolyLine.

        Args:
            key: the index passed to the bracket operator.

        Returns:
            A single point of this PolyLine.
        '''
        if not isinstance(key, int):
            raise TypeError('PolyLine indices must be integers.')
        return self.points[key]

    def __len__(self) -> int:
        ''' Returns the number of line segments in this PolyLine.

        Returns:
            The number of line segments.
        '''
        return len(self.points)