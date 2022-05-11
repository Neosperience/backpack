''' 2D geometry primitives and implementation of some geometric algorithms. '''

from typing import List, Sequence, Tuple
import collections.abc
import dataclasses
from dataclasses import dataclass
import math

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
    def counterclockwise(pt1: 'Point', pt2: 'Point', pt3: 'Point') -> bool:
        ''' Determines if the three points form a counterclockwise angle.
        
        Args:
            pt1: The first point
            pt2: The second point
            pt3: The third point

        Returns:
            `True` if the points form a counterclockwise angle 
        '''
        return (pt2.x - pt1.x) * (pt3.y - pt1.y) > (pt3.x - pt1.x) * (pt2.y - pt1.y)
    
    def distance(self, other: 'Point') -> float:
        ''' Calculates the distance between this and an other point. 
        
        Args:
            other: The other point
            
        Returns:
            The distance between this and an other point. 
        '''
        dx, dy = self.x - other.x, self.y - other.y
        return math.sqrt(dx * dx + dy * dy)


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
        ccw = Point.counterclockwise
        return (
            ccw(self.pt1, other.pt1, other.pt2) != ccw(self.pt2, other.pt1, other.pt2) and 
            ccw(self.pt1, self.pt2, other.pt1) != ccw(self.pt1, self.pt2, other.pt2)
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

    def hasinside(self, pt: Point) -> bool:
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

    @property
    def center(self) -> Point:
        ''' The center of the rectangle. '''
        return Point((self.pt_min.x + self.pt_max.x) / 2, (self.pt_min.y + self.pt_max.y) / 2)

    @property
    def base(self) -> Point:
        ''' Returns the center of the base of the rectangle. '''
        return Point((self.pt_min.x + self.pt_max.x) / 2, self.pt_max.y)

    @property
    def size(self) -> Tuple[float, float]:
        ''' The width and height of the rectangle. '''
        return self.pt_max.x - self.pt_min.x, self.pt_max.y - self.pt_min.y


@dataclass(frozen=True)
class PolyLine:
    ''' A PolyLine is a connected series of line segments. 
    
    Args:
        points: the list of the points of the polyline
        closed: flags if the polyline is closed
    '''

    points : Sequence[Point] = dataclasses.field(repr=False)
    ''' The list of the points of the polyline '''

    closed : bool = True
    ''' `True` if the polyline is closed. '''

    lines: List[Point] = dataclasses.field(init=False)
    ''' The line segments of this PolyLine '''

    boundingbox: Rectangle = dataclasses.field(init=False)
    ''' The bounding box of this PolyLine '''

    def __post_init__(self):
        if not isinstance(self.points, collections.abc.Sequence):
            raise ValueError('PolyLine points argument must be a Sequence.')
        if len(self.points) < 2:
            raise ValueError('PolyLine should contain at least two points.')
        for pt in self.points:
            if not hasattr(pt, 'x') or not hasattr(pt, 'y'):
                raise ValueError('The elements of PolyLine points argument must be Point objects.')

        # Compute lines
        lines = [Line(start, end) for start, end in zip(self.points, self.points[1:])]
        if self.closed:
            lines.append(Line(self.points[-1], self.points[0]))
        object.__setattr__(self, 'lines', lines)

        # Compute bounding box
        minx = min(pt.x for pt in self.points)
        miny = min(pt.y for pt in self.points)
        maxx = max(pt.x for pt in self.points)
        maxy = max(pt.y for pt in self.points)
        object.__setattr__(self, 'boundingbox', Rectangle(Point(minx, miny), Point(maxx, maxy)))

    def hasinside(self, point: Point) -> bool:
        ''' Determines if a point is inside this closed `PolyLine`. 
        
        This implementation uses the `ray casting algorithm`_.

        .. _`ray casting algorithm`: 
           https://en.wikipedia.org/wiki/Point_in_polygon#Ray_casting_algorithm

        Args:
            point: The point

        Returns:
            `True` if the point is inside this closed `PolyLine`. 
        '''
        if not self.closed:
            raise ValueError('PolyLine.hasinside works only for closed polylines.')
        if not self.boundingbox.hasinside(point):
            return False
        ray = Line(Point(self.boundingbox.pt_min.x - 0.01, self.boundingbox.pt_min.y), point)
        n_ints = sum(1 if ray.intersects(line) else 0 for line in self.lines)
        return True if n_ints % 2 == 1 else False
