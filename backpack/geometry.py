''' 2D geometry primitives and implementation of some geometric algorithms. '''

from typing import List, Sequence, Tuple
import collections.abc
import dataclasses
from dataclasses import dataclass
import math
from itertools import islice, cycle, groupby
from . import lazy_property

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


@dataclass(frozen=True)
class Line:
    ''' A line segment. 

    Args:
        pt1 (float): The first point of the line segment
        pt2 (float): The second point of the line segment
    '''
    pt1: Point
    ''' The first point of the line segment '''

    pt2: Point
    ''' The second point of the line segment '''

    def __post_init__(self):
        if not isinstance(self.pt1, Point) or not isinstance(self.pt2, Point):
            raise ValueError('Line arguments "pt1" and "pt2" must be Point objects.')

    def intersects(self, other: 'Line') -> bool:
        ''' Determines if this line segment intersects an other one.
        
        Args:
            other: The other line segment
            
        Returns:
            `True` if the two segments intersect each other.
        '''
        return (
            Point.ccw(self.pt1, other.pt1, other.pt2) != Point.ccw(self.pt2, other.pt1, other.pt2) 
            and 
            Point.ccw(self.pt1, self.pt2, other.pt1) != Point.ccw(self.pt1, self.pt2, other.pt2)
        )


@dataclass(frozen=True)
class Rectangle:
    ''' An axis aligned rectangle. 

    Args:
        pt1 (Point): The first corner of the rectangle
        pt2 (Point): The second corner of the rectangle
    '''

    pt1: dataclasses.InitVar[Point]
    ''' The first corner of the rectangle '''

    pt2: dataclasses.InitVar[Point]
    ''' The second corner of the rectangle '''

    pt_min: Point = dataclasses.field(init=False)
    ''' The corner with minimum coordinates of the rectangle '''

    pt_max: Point = dataclasses.field(init=False)
    ''' The corner with maximum coordinates of the rectangle '''

    def __post_init__(self, pt1, pt2):
        if not isinstance(pt1, Point) or not isinstance(pt2, Point):
            raise ValueError('Rectangle arguments "pt1" and "pt2" must be Point objects.')
        object.__setattr__(self, 'pt_min', Point(min(pt1.x, pt2.x), min(pt1.y, pt2.y)))
        object.__setattr__(self, 'pt_max', Point(max(pt1.x, pt2.x), max(pt1.y, pt2.y)))

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
        return self.pt_max.x - self.pt_min.x, self.pt_max.y - self.pt_min.y


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
        
        # Iterate over consequitive point triplets
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
