import unittest

from backpack.geometry import Point, Line, Rectangle, PolyLine

class TestPoint(unittest.TestCase):

    def test_counterclockwise(self):
        pt1 = Point(0, 0)
        pt2 = Point(1, 0)
        pt3 = Point(1, 1)
        self.assertTrue(Point.counterclockwise(pt1, pt2, pt3))
        self.assertFalse(Point.counterclockwise(pt3, pt2, pt1))

    def test_distance(self):
        pt1 = Point(0, 3)
        pt2 = Point(4, 0)
        self.assertAlmostEqual(pt1.distance(pt2), 5)

    def test_isinstance(self):
        class DummyPoint:
            x = 0
            y = 0
        self.assertTrue(isinstance(Point(0, 0), Point))
        self.assertTrue(isinstance(DummyPoint, Point))
        self.assertFalse(isinstance({'x': 0, 'y': 0}, Point))
        self.assertFalse(isinstance('foobar', Point))


class TestLine(unittest.TestCase):

    def test_init(self):
        with self.assertRaises(ValueError) as ctx:
            Line('foo', 'bar')
        self.assertEqual(
            str(ctx.exception), 
            'Line arguments "pt1" and "pt2" must be Point objects.'
        )

    def test_intersects(self):
        l1 = Line(Point(-1, 0), Point(1, 0))
        l2 = Line(Point(0, -1), Point(0, 1))
        self.assertTrue(l1.intersects(l2))
        l3 = Line(Point(-1, 2), Point(1, 2))
        self.assertFalse(l3.intersects(l1))
        self.assertFalse(l3.intersects(l2))


class TestRectangle(unittest.TestCase):

    pt00 = Point(0, 0)
    pt01 = Point(0, 2)
    pt10 = Point(4, 0)
    pt11 = Point(4, 2)

    def setUp(self) -> None:
        super().setUp()
        self.rect = Rectangle(self.pt00, self.pt11)
        print(self.rect)

    def test_init(self):
        self.assertEqual(self.rect.pt_min, self.pt00)
        self.assertEqual(self.rect.pt_max, self.pt11)
        r2 = Rectangle(self.pt01, self.pt10)
        self.assertEqual(r2.pt_min, self.pt00)
        self.assertEqual(r2.pt_max, self.pt11)
        with self.assertRaises(ValueError) as ctx:
            Rectangle('foo', 'bar')
        self.assertEqual(
            str(ctx.exception), 
            'Rectangle arguments "pt1" and "pt2" must be Point objects.'
        )
    
    def test_hasinside(self):
        self.assertTrue(self.rect.hasinside(Point(1, 1)))
        self.assertFalse(self.rect.hasinside(Point(4, 4)))

    def test_center(self) -> None:
        self.assertEqual(self.rect.center, Point(2, 1))
    
    def test_base(self) -> None:
        self.assertEqual(self.rect.base, Point(2, 0))

    def test_size(self) -> None:
        self.assertEqual(self.rect.size, (4, 2))

class TestPolyLine(unittest.TestCase):

    pt1, pt2, pt3, pt4 = Point(-4, 0), Point(0, 4), Point(4, 0), Point(0, -4)

    test_points = [pt1, pt2, pt3, pt4]

    test_lines_open = [Line(pt1, pt2), Line(pt2, pt3), Line(pt3, pt4)]
    test_lines_closed = [Line(pt1, pt2), Line(pt2, pt3), Line(pt3, pt4), Line(pt4, pt1)]

    def setUp(self) -> None:
        super().setUp()
        self.poly_closed = PolyLine(self.test_points)
        self.poly_open = PolyLine(self.test_points, closed=False)

    def test_init(self) -> None:
        self.assertEqual(self.poly_closed.lines, self.test_lines_closed)
        self.assertTrue(self.poly_closed.closed)
        with self.assertRaises(ValueError) as ctx:
            PolyLine([Point(1, 1)])
        self.assertEqual(str(ctx.exception), 'PolyLine should contain at least two points.')
        with self.assertRaises(ValueError) as ctx:
            PolyLine(1)
        self.assertEqual(str(ctx.exception), 'PolyLine points argument must be a Sequence.')
        with self.assertRaises(ValueError) as ctx:
            PolyLine('foo')
        self.assertEqual(str(ctx.exception), 'The elements of PolyLine points argument must be Point objects.')
        
    def test_open(self) -> None:
        self.assertEqual(self.poly_open.lines, self.test_lines_open)
        self.assertFalse(self.poly_open.closed)

    def test_boundingbox(self) -> None:
        expected_bb = Rectangle(Point(-4, -4), Point(4, 4))
        self.assertEqual(self.poly_closed.boundingbox, expected_bb)
    
    def test_hasinside(self) -> None:
        self.assertTrue(self.poly_closed.hasinside(Point(0, 0)))
        self.assertFalse(self.poly_closed.hasinside(Point(5, 5)))
        self.assertFalse(self.poly_closed.hasinside(Point(3, 3)))
        with self.assertRaises(ValueError) as ctx:
            self.poly_open.hasinside(Point(0, 0))
        self.assertEqual(str(ctx.exception), 'PolyLine.hasinside works only for closed polylines.')
