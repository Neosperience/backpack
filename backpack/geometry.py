''' 2D geometry primitives and basic functions. '''

from typing import NamedTuple
import math

class Point(NamedTuple):
    ''' A point with both coordinates normalized to the [0; 1) range.

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
        return (pt3.x - pt1.x) * (pt2.y - pt1.y) > (pt2.x - pt1.x) * (pt3.y - pt1.y)

    def distance(self, other: 'Point') -> float:
        ''' Calculates the distance between this and an other point. 
        
        Args:
            other: The other point
            
        Returns:
            The distance between this and an other point. 
        '''
        dx, dy = self.x - other.x, self.y - other.y
        return math.sqrt(dx * dx + dy * dy)


class Line(NamedTuple):
    ''' A line segment. 

    Args:
        pt1 (float): The first point of the line segment
        pt2 (float): The second point of the line segment
    '''
    pt1: Point
    ''' The first point of the line segment '''

    pt2: Point
    ''' The second point of the line segment '''

    def intersect(self, other: 'Line') -> bool:
        ''' Determines if this line segment intersects an other one.
        
        Args:
            other: The other line segment
            
        Returns:
            `True` if the two segments intersect eachother.
        '''
        ccw = Point.counterclockwise
        return (
            ccw(self.pt1, other.pt1, other.pt2) != ccw(self.pt2, other.pt1, other.pt2) and 
            ccw(self.pt1, self.pt2, other.pt1) != ccw(self.pt1, self.pt2, other.pt2)
        )
