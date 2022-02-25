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
        self.assertTrue(context.add_rect.called)
        rect_args, _ = context.add_rect.call_args
        self.assertEqual(rect_args[0], TEST_RECT.point1.x)
        self.assertEqual(rect_args[1], TEST_RECT.point1.y)
        self.assertEqual(rect_args[2], TEST_RECT.point2.x)
        self.assertEqual(rect_args[3], TEST_RECT.point2.y)

    def test_label(self):
        context = Mock()
        self.driver.render(annotations=[TEST_LABEL], context=context)
        self.assertTrue(context.add_label.called)
        lbl_args, _ = context.add_label.call_args
        self.assertEqual(lbl_args[0], TEST_LABEL.text)
        self.assertEqual(lbl_args[1], TEST_LABEL.point.x)
        self.assertEqual(lbl_args[2], TEST_LABEL.point.y)

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
        self.assertTrue(mock_cv2.rectangle.called)
        cv2_rect_args, _ = mock_cv2.rectangle.call_args
        self.assertIs(cv2_rect_args[0], img)
        self.assertEqual(cv2_rect_args[1], TEST_RECT.point1.in_image(img))
        self.assertEqual(cv2_rect_args[2], TEST_RECT.point2.in_image(img))
        self.assertEqual(cv2_rect_args[3], OpenCVImageAnnotationDriver.DEFAULT_OPENCV_COLOR)
        self.assertEqual(cv2_rect_args[4], OpenCVImageAnnotationDriver.DEFAULT_OPENCV_LINEWIDTH)

    def test_label(self):
        img = Mock()
        img.shape = [100, 100, 3] 
        self.driver.render(annotations=[TEST_LABEL], context=img)
        self.assertTrue(mock_cv2.putText.called)
        cv2_puttext_args, _ = mock_cv2.putText.call_args
        self.assertIs(cv2_puttext_args[0], img)
        self.assertEqual(cv2_puttext_args[1], TEST_LABEL.text)
        self.assertEqual(cv2_puttext_args[2], TEST_LABEL.point.in_image(img))
        self.assertEqual(cv2_puttext_args[3], OpenCVImageAnnotationDriver.DEFAULT_OPENCV_FONT)
        self.assertEqual(cv2_puttext_args[4], OpenCVImageAnnotationDriver.DEFAULT_OPENCV_FONT_SCALE)
        self.assertEqual(cv2_puttext_args[5], OpenCVImageAnnotationDriver.DEFAULT_OPENCV_COLOR)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            self.driver.render(annotations=['foobar'], context=Mock())
