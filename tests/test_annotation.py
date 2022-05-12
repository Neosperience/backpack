import unittest
import unittest.mock
from unittest.mock import patch, Mock
import numpy as np

from collections import namedtuple

import datetime

mock_cv2 = Mock()
with patch.dict('sys.modules', cv2=mock_cv2):
    from backpack.annotation import (
        TimestampAnnotation, LabelAnnotation, LineAnnotation, RectAnnotation,
        AnnotationDriverBase,
        PanoramaMediaAnnotationDriver, OpenCVImageAnnotationDriver,
        Color
    )

Point = namedtuple('Point', ('x', 'y'))
Line = namedtuple('Line', ('pt1', 'pt2'))
Rectangle = namedtuple('Rectangle', ('pt_min', 'pt_max'))

TEST_POINT = (0.3, 0.4)
TEST_RECT = RectAnnotation(Rectangle(Point(0.1, 0.2), Point(0.8, 0.9)))
TEST_LABEL = LabelAnnotation(Point(0.3, 0.4), 'Hello World')
TEST_LINE = LineAnnotation(Line(Point(0.1, 0.2), Point(0.3, 0.4)))

class TestColor(unittest.TestCase):

    def test_from_hex(self):
        hex_int = 0x5777A5
        hex_str = '#5777A5'
        expected_color = Color(87, 119, 165)
        self.assertEqual(Color.from_hex(hex_int), expected_color)
        self.assertEqual(Color.from_hex(hex_str), expected_color)

class TestTimestampAnnotation(unittest.TestCase):
    
    def test_timestamp_annotation(self):
        now = datetime.datetime(2022, 2, 22, 22, 22, 22)
        origin = Point(0.3, 0.7)
        ts_anno = TimestampAnnotation(timestamp=now, point=origin)
        self.assertEqual(ts_anno.text, '2022-02-22 22:22:22')
        self.assertEqual(ts_anno.point, origin)


class TestAnnotationDriverBase(unittest.TestCase):

    def test_to_point(self):
        tp = AnnotationDriverBase.to_point
        x, y = TEST_POINT
        self.assertEqual(TEST_POINT, tp((x, y)), msg='from tuple')
        self.assertEqual(TEST_POINT, tp([x, y]), msg='from list')
        self.assertEqual(TEST_POINT, tp(np.array([x, y])), msg='from numpy array')
        self.assertEqual(TEST_POINT, tp(Point(x, y)), msg='from named tuple')


class TestPanoramaMediaAnnotationDriver(unittest.TestCase):
    
    def setUp(self):
        self.driver = PanoramaMediaAnnotationDriver()

    def test_rect(self):
        context = Mock()
        self.driver.render(annotations=[TEST_RECT], context=context)
        context.add_rect.assert_called_once_with(
            TEST_RECT.rect.pt_min.x, TEST_RECT.rect.pt_min.y, 
            TEST_RECT.rect.pt_max.x, TEST_RECT.rect.pt_max.y
        )

    def test_label(self):
        context = Mock()
        self.driver.render(annotations=[TEST_LABEL], context=context)
        context.add_label.assert_called_once_with(
            TEST_LABEL.text, TEST_LABEL.point.x, TEST_LABEL.point.y
        )
    
    def test_invalid(self):
        with self.assertRaises(ValueError):
            self.driver.render(annotations=['foobar'], context=Mock())


class TestOpenCVImageAnnotationDriver(unittest.TestCase):
    
    def setUp(self):
        mock_cv2.reset_mock()
        self.driver = OpenCVImageAnnotationDriver()

    def test_scale(self):
        img = Mock()
        img.shape = [200, 100, 3]
        self.assertEqual(
            (int(TEST_POINT[0] * 100), int(TEST_POINT[1] * 200)), 
            OpenCVImageAnnotationDriver.scale(TEST_POINT, img)
        )

    def test_rect(self):
        img = Mock()
        img.shape = [200, 100, 3] 
        self.driver.render(annotations=[TEST_RECT], context=img)
        mock_cv2.rectangle.assert_called_once_with(
            img,
            (int(TEST_RECT.rect.pt_min.x * 100), int(TEST_RECT.rect.pt_min.y * 200)),
            (int(TEST_RECT.rect.pt_max.x * 100), int(TEST_RECT.rect.pt_max.y * 200)),
            OpenCVImageAnnotationDriver.DEFAULT_COLOR,
            OpenCVImageAnnotationDriver.DEFAULT_LINEWIDTH
        )

    def test_label(self):
        img = Mock()
        img.shape = [200, 100, 3]
        self.driver.render(annotations=[TEST_LABEL], context=img)
        mock_cv2.putText.assert_called_once_with(
            img=img, 
            text=TEST_LABEL.text,
            org=OpenCVImageAnnotationDriver.scale(TEST_LABEL.point, img),
            fontFace=OpenCVImageAnnotationDriver.DEFAULT_FONT,
            fontScale=unittest.mock.ANY,
            color=OpenCVImageAnnotationDriver.DEFAULT_COLOR,
            thickness=unittest.mock.ANY
        )

    def test_line(self):
        img = Mock()
        img.shape = [200, 100, 3]
        self.driver.render(annotations=[TEST_LINE], context=img)
        mock_cv2.line.assert_called_once_with(
            img,
            OpenCVImageAnnotationDriver.scale(TEST_LINE.line.pt1, img),
            OpenCVImageAnnotationDriver.scale(TEST_LINE.line.pt2, img),
            OpenCVImageAnnotationDriver.DEFAULT_COLOR,
            TEST_LINE.thickness
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            self.driver.render(annotations=['foobar'], context=Mock())
