import unittest
import numpy as np

from backpack.geometry import Point, Line, Rectangle, PolyLine

class TestPoint(unittest.TestCase):

    def test_ccw(self):
        pt1 = Point(0, 0)
        pt2 = Point(1, 0)
        pt3 = Point(1, 1)
        self.assertTrue(Point.ccw(pt1, pt2, pt3))
        self.assertFalse(Point.ccw(pt3, pt2, pt1))
        pt4 = Point(2, 0)
        self.assertTrue(Point.ccw(pt1, pt2, pt4), msg='Collinear points')
        self.assertTrue(Point.ccw(pt1, pt1, pt2), msg='Same points')

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

    def test_add(self):
        pt1 = Point(2, 3)
        pt2 = Point(4, 5)
        self.assertEqual(pt1 + pt2, Point(6, 8))
        with self.assertRaises(TypeError) as ctx:
            pt1 + 'foo'
        self.assertEqual(str(ctx.exception), "unsupported operand type(s) for +: 'Point' and 'str'")

    def test_sub(self):
        pt1 = Point(4, 7)
        pt2 = Point(2, 3)
        self.assertEqual(pt1 - pt2, Point(2, 4))

    def test_from_value(self):
        pt1 = Point(4, 7)
        with self.subTest('identity'):
            self.assertEqual(pt1, Point.from_value(pt1))
        with self.subTest('dictionary'):
            self.assertEqual(pt1, Point.from_value({'x': 4, 'y': 7}))
        with self.subTest('sequence'):
            self.assertEqual(pt1, Point.from_value([4, 7]))
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Point.from_value('foo')

    def test_getitem(self):
        pt1 = Point(4, 7)
        self.assertEqual(pt1[0], 4)
        self.assertEqual(pt1[1], 7)
        with self.assertRaises(IndexError):
            pt1[2]
        with self.assertRaises(TypeError):
            pt1['foo']

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

    def test_from_value(self):
        line = Line(Point(1, 2), Point(3, 4))
        with self.subTest('identity'):
            self.assertEqual(line, Line.from_value(line))
        with self.subTest('dictionary'):
            self.assertEqual(line, Line.from_value(
                {'pt1': {'x': 1, 'y': 2}, 'pt2': {'x': 3, 'y': 4}}
            ))
        with self.subTest('sequence'):
            self.assertEqual(line, Line.from_value([[1, 2], [3, 4]]))
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Line.from_value('foo')

    def test_getitem(self):
        pt1 = Point(1, 2)
        pt2 = Point(3, 4)
        line = Line(pt1, pt2)
        self.assertEqual(line[0], pt1)
        self.assertEqual(line[1], pt2)
        with self.assertRaises(IndexError):
            line[2]
        with self.assertRaises(TypeError):
            line['foo']

class TestRectangle(unittest.TestCase):

    pt00 = Point(0, 0)
    pt01 = Point(0, 2)
    pt10 = Point(4, 0)
    pt11 = Point(4, 2)

    def setUp(self) -> None:
        super().setUp()
        self.rect = Rectangle(self.pt00, self.pt11)

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

    def test_has_inside(self):
        self.assertTrue(self.rect.has_inside(Point(1, 1)))
        self.assertFalse(self.rect.has_inside(Point(4, 4)))

    def test_center(self) -> None:
        self.assertEqual(self.rect.center, Point(2, 1))

    def test_base(self) -> None:
        self.assertEqual(self.rect.base, Point(2, 2))

    def test_size(self) -> None:
        self.assertEqual(self.rect.size, (4, 2))

    def test_width(self) -> None:
        self.assertEqual(self.rect.width, 4)

    def test_height(self) -> None:
        self.assertEqual(self.rect.height, 2)

    def test_area(self) -> None:
        self.assertEqual(self.rect.area, 8)

    def test_aspect_ratio(self) -> None:
        self.assertEqual(self.rect.aspect_ratio, 2)

    def test_top(self) -> None:
        self.assertEqual(self.rect.top, 0)

    def test_bottom(self) -> None:
        self.assertEqual(self.rect.bottom, 2)

    def test_left(self) -> None:
        self.assertEqual(self.rect.left, 0)

    def test_right(self) -> None:
        self.assertEqual(self.rect.right, 4)

    def test_tlbr(self) -> None:
        self.assertEqual(self.rect.tlbr, (0, 0, 2, 4))

    def test_tlwh(self) -> None:
        self.assertEqual(self.rect.tlwh, (0, 0, 4, 2))

    def test_from_value(self) -> None:
        rect = Rectangle(Point(1, 2), Point(3, 4))
        with self.subTest('identity'):
            self.assertEqual(rect, Rectangle.from_value(rect))
        with self.subTest('dictionary'):
            self.assertEqual(rect, Rectangle.from_value(
                {'pt1': {'x': 1, 'y': 2}, 'pt2': {'x': 3, 'y': 4}}
            ))
        with self.subTest('sequence'):
            self.assertEqual(rect, Rectangle.from_value([[1, 2], [3, 4]]))
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Rectangle.from_value('foo')

    def test_from_tlbr(self) -> None:
        tlbr = (1, 2, 3, 4)
        expected_rect = Rectangle(pt1=Point(2, 1), pt2=Point(4, 3))
        with self.subTest('tuple'):
            self.assertEqual(Rectangle.from_tlbr(tlbr), expected_rect)
        with self.subTest('list'):
            self.assertEqual(Rectangle.from_tlbr(list(tlbr)), expected_rect)
        with self.subTest('numpy'):
            self.assertEqual(Rectangle.from_tlbr(np.array(tlbr)), expected_rect)
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Rectangle.from_tlbr('foo')

    def test_from_tlwh(self) -> None:
        tlwh = (1, 2, 3, 2)
        expected_rect = Rectangle(pt1=Point(2, 1), pt2=Point(5, 3))
        with self.subTest('tuple'):
            self.assertEqual(Rectangle.from_tlwh(tlwh), expected_rect)
        with self.subTest('list'):
            self.assertEqual(Rectangle.from_tlwh(list(tlwh)), expected_rect)
        with self.subTest('numpy'):
            self.assertEqual(Rectangle.from_tlwh(np.array(tlwh)), expected_rect)
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Rectangle.from_tlwh('foo')

    def test_getitem(self) -> None:
        self.assertEqual(self.rect[0], self.pt00)
        self.assertEqual(self.rect[1], self.pt11)
        with self.assertRaises(IndexError):
            self.rect[2]
        with self.assertRaises(TypeError):
            self.rect['foo']


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

    def test_has_inside(self) -> None:
        self.assertTrue(self.poly_closed.has_inside(Point(0, 0)))
        self.assertFalse(self.poly_closed.has_inside(Point(5, 5)))
        self.assertFalse(self.poly_closed.has_inside(Point(3, 3)))
        with self.assertRaises(ValueError) as ctx:
            self.poly_open.has_inside(Point(0, 0))
        self.assertEqual(str(ctx.exception), 'PolyLine.has_inside works only for closed polylines.')

    def test_self_intersects(self) -> None:
        square = PolyLine([Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)], closed=True)
        self.assertFalse(square.self_intersects)
        cross = PolyLine([Point(0, 0), Point(1, 0), Point(0, 1), Point(1, 1)], closed=True)
        self.assertTrue(cross.self_intersects)

    def test_is_convex(self) -> None:

        with self.subTest('triangle is convex'):
            triangle = PolyLine([Point(0, 0), Point(1, 0), Point(0, 1)], closed=True)
            self.assertTrue(triangle.is_convex)

        with self.subTest('square is convex'):
            square = PolyLine([Point(0, 0), Point(1, 0), Point(1, 1), Point(0, 1)], closed=True)
            self.assertTrue(square.is_convex)

        with self.subTest('concave shape'):
            concave = PolyLine(
                [Point(0, 0), Point(2, 0), Point(2, 2), Point(1, 1), Point(0, 2)],
                closed=True
            )
            self.assertFalse(concave.is_convex)

    def test_from_value(self):
        with self.subTest('identity'):
            self.assertEqual(self.poly_open, PolyLine.from_value(self.poly_open))
        with self.subTest('dictionary'):
            self.assertEqual(self.poly_open, PolyLine.from_value(
                {'points': [{'x': -4, 'y': 0}, {'x': 0, 'y': 4},
                            {'x': 4, 'y': 0}, {'x': 0, 'y': -4}],
                 'closed': False }
            ))
        with self.subTest('sequence'):
            self.assertEqual(self.poly_open, PolyLine.from_value(
                [[-4, 0], [0, 4], [4, 0], [0, -4]], closed=False)
            )
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                PolyLine.from_value('foo')

    def test_getitem(self) -> None:
        for idx, pt in enumerate(self.poly_open):
            self.assertEqual(self.poly_open[idx], pt)
        with self.assertRaises(IndexError):
            self.poly_open[len(self.poly_open)]
        with self.assertRaises(TypeError):
            self.poly_open['foo']

    def test_len(self) -> None:
        self.assertEqual(len(self.poly_open), len(self.test_points))
