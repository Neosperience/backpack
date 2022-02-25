import unittest
from unittest.mock import patch, Mock

import datetime

mock_cv2 = Mock()
with patch.dict('sys.modules', cv2=mock_cv2):
    from backpack.annotation import (
        Point, TimestampAnnotation, LabelAnnotation, RectAnnotation,
        PanoramaMediaAnnotationDriver, OpenCVImageAnnotationDriver
    )

TEST_RECT = RectAnnotation(Point(0.1, 0.2), Point(0.8, 0.9))
TEST_LABEL = LabelAnnotation(Point(0.3, 0.4), 'Hello World')

class TestPoint(unittest.TestCase):
    
    def setUp(self):
        self.point = Point(0.3, 0.7)
    
    def test_scale(self):
        scaled_x, scaled_y = self.point.scale(100, 100)
        self.assertEqual(scaled_x, 30)
        self.assertEqual(scaled_y, 70)

    def test_in_image(self):
        img = Mock()
        img.shape = [100, 100, 3]
        scaled_x, scaled_y = self.point.in_image(img)
        self.assertEqual(scaled_x, 30)
        self.assertEqual(scaled_y, 70)


class TestTimestampAnnotation(unittest.TestCase):
    
    def test_timestamp_annotation(self):
        now = datetime.datetime(2022, 2, 22, 22, 22, 22)
        origin = Point(0.3, 0.7)
        ts_anno = TimestampAnnotation(timestamp=now, point=origin)
        self.assertEqual(ts_anno.text, '2022-02-22 22:22:22')
        self.assertEqual(ts_anno.point, origin)


class TestPanoramaMediaAnnotationDriver(unittest.TestCase):
    
    def setUp(self):
        self.driver = PanoramaMediaAnnotationDriver()

    def test_rect(self):
        context = Mock()
        self.driver.render(annotations=[TEST_RECT], context=context)
        context.add_rect.assert_called_once_with(
            TEST_RECT.point1.x, TEST_RECT.point1.y, TEST_RECT.point2.x, TEST_RECT.point2.y
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

    def test_rect(self):
        img = Mock()
        img.shape = [100, 100, 3] 
        self.driver.render(annotations=[TEST_RECT], context=img)
        mock_cv2.rectangle.assert_called_once_with(
            img,
            TEST_RECT.point1.in_image(img),
            TEST_RECT.point2.in_image(img),
            OpenCVImageAnnotationDriver.DEFAULT_OPENCV_COLOR,
            OpenCVImageAnnotationDriver.DEFAULT_OPENCV_LINEWIDTH
        )

    def test_label(self):
        img = Mock()
        img.shape = [100, 100, 3] 
        self.driver.render(annotations=[TEST_LABEL], context=img)
        mock_cv2.putText.assert_called_once_with(
            img, 
            TEST_LABEL.text, 
            TEST_LABEL.point.in_image(img),
            OpenCVImageAnnotationDriver.DEFAULT_OPENCV_FONT,
            OpenCVImageAnnotationDriver.DEFAULT_OPENCV_FONT_SCALE,
            OpenCVImageAnnotationDriver.DEFAULT_OPENCV_COLOR
        )

    def test_invalid(self):
        with self.assertRaises(ValueError):
            self.driver.render(annotations=['foobar'], context=Mock())
