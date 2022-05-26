import unittest
import unittest.mock
from unittest.mock import patch, Mock, DEFAULT, call, ANY

import datetime

mock_cv2 = Mock(name='mock_cv2')
mock_np = Mock(name='mock_np')
with patch.dict('sys.modules', cv2=mock_cv2, numpy=mock_np):
    from backpack.annotation import (
        TimestampAnnotation, LabelAnnotation, LineAnnotation, RectAnnotation, MarkerAnnotation,
        BoundingBoxAnnotation, PolyLineAnnotation,
        AnnotationDriverBase, PanoramaMediaAnnotationDriver, OpenCVImageAnnotationDriver,
        Color
    )

from backpack.geometry import Point, Line, Rectangle, PolyLine

TEST_POINT = Point(0.3, 0.4)
TEST_COLOR = Color(50, 100, 150)
TEST_COLOR2 = Color(25, 75, 125)
TEST_RECT = Rectangle(Point(0.1, 0.2), Point(0.8, 0.9))
TEST_LINE = Line(Point(0.1, 0.2), Point(0.3, 0.4))
TEST_POLYLINE = PolyLine(
        [Point(0, 0), Point(2, 0), Point(2, 2), Point(1, 1), Point(0, 2)], 
        closed=True
    )

TEST_RECT_ANNO = RectAnnotation(TEST_RECT, color=TEST_COLOR)
TEST_LABEL_ANNO = LabelAnnotation(TEST_POINT, 'Hello World', color=TEST_COLOR)
TEST_LINE_ANNO = LineAnnotation(TEST_LINE, color=TEST_COLOR)
TEST_MARKER_ANNO = MarkerAnnotation(TEST_POINT, style=MarkerAnnotation.Style.STAR, color=TEST_COLOR)
TEST_POLYLINE_ANNO = PolyLineAnnotation(TEST_POLYLINE, 2, color=TEST_COLOR, fill_color=TEST_COLOR2)
TEST_BB_ANNO = BoundingBoxAnnotation(TEST_RECT, 'top label', 'bottom label', color=TEST_COLOR)

class TestColor(unittest.TestCase):

    hex_int = 0x5777A5
    hex_str = '#5777A5'
    expected_color = Color(87, 119, 165)
    expected_color_alpha = Color(87, 119, 165, 0.3)

    def test_from_hex(self):
        with self.subTest('integer'):
            self.assertEqual(Color.from_hex(self.hex_int), self.expected_color)
        with self.subTest('string'):
            self.assertEqual(Color.from_hex(self.hex_str), self.expected_color)
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Color.from_hex(['foo'])

    def test_from_value(self):
        with self.subTest('identity'):
            self.assertEqual(Color.from_value(self.expected_color), self.expected_color)
        with self.subTest('hex'):
            self.assertEqual(Color.from_value(self.hex_str), self.expected_color)
        with self.subTest('sequence'):
            self.assertEqual(Color.from_value([87, 119, 165]), self.expected_color)
        with self.subTest('sequence with transparency'):
            self.assertEqual(Color.from_value([87, 119, 165, 0.3]), self.expected_color_alpha)
        with self.subTest('mapping'):
            self.assertEqual(Color.from_value({'r': 87, 'g': 119, 'b': 165}), self.expected_color)
        with self.subTest('mapping with transparency'):
            self.assertEqual(
                Color.from_value({'r': 87, 'g': 119, 'b': 165, 'alpha': 0.3}), 
                self.expected_color_alpha
            )
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                Color.from_value(['foo'])
            with self.assertRaises(ValueError):
                Color.from_value([1, 2, 3, 'foo'])
            with self.assertRaises(ValueError):
                Color.from_value({'r': 87, 'g': 119, 'foo': 'bar'})


class TestTimestampAnnotation(unittest.TestCase):
    
    def test_timestamp_annotation(self):
        now = datetime.datetime(2022, 2, 22, 22, 22, 22)
        origin = Point(0.3, 0.7)
        ts_anno = TimestampAnnotation(timestamp=now, point=origin)
        self.assertEqual(ts_anno.text, '2022-02-22 22:22:22')
        self.assertEqual(ts_anno.point, origin)

@patch.multiple(AnnotationDriverBase,
    add_rect=DEFAULT,
    add_label=DEFAULT,
    add_marker=DEFAULT,
    add_line=DEFAULT,
    add_polyline=DEFAULT,
    __abstractmethods__=set()
)
class TestAnnotationDriverBase(unittest.TestCase):

    def render_subtest(self, name, anno, driver_mock):
        driver = AnnotationDriverBase()
        context = Mock()
        with self.subTest(name):
            driver.render([anno], context)
            driver_mock.assert_called_once_with(anno, context)

    def test_render(self, **kwargs):
        self.render_subtest('label', TEST_LABEL_ANNO, kwargs['add_label'])
        self.render_subtest('rect', TEST_RECT_ANNO, kwargs['add_rect'])
        self.render_subtest('marker', TEST_MARKER_ANNO, kwargs['add_marker'])
        self.render_subtest('line', TEST_LINE_ANNO, kwargs['add_line'])
        self.render_subtest('polyline', TEST_POLYLINE_ANNO, kwargs['add_polyline'])
        with self.subTest('bounding box'):
            with patch.object(AnnotationDriverBase, 'add_bounding_box') as bounding_box_mock:
                self.render_subtest('bounding_box', TEST_BB_ANNO, bounding_box_mock)
        with self.subTest('invalid'):
            with self.assertRaises(ValueError):
                AnnotationDriverBase().render(['foo'], Mock())

    def test_add_bounding_box(self, **kwargs):
        driver = AnnotationDriverBase()
        context = Mock()
        expected_rect = TEST_BB_ANNO.rectangle
        expected_rect_anno = RectAnnotation(expected_rect, TEST_COLOR)
        driver.render([TEST_BB_ANNO], context)
        driver.add_rect.assert_called_once_with(expected_rect_anno, context)
        driver.add_label.assert_has_calls([
            call(LabelAnnotation(
                    point=expected_rect.pt_min,
                    text='top label',
                    color=TEST_COLOR,
                    horizontal_anchor=LabelAnnotation.HorizontalAnchor.LEFT,
                    vertical_anchor=LabelAnnotation.VerticalAnchor.BOTTOM
                ), context),
            call(LabelAnnotation(
                    point=ANY,
                    text='bottom label',
                    color=TEST_COLOR,
                    horizontal_anchor=LabelAnnotation.HorizontalAnchor.LEFT,
                    vertical_anchor=LabelAnnotation.VerticalAnchor.TOP
                ), context)
        ])

class TestPanoramaMediaAnnotationDriver(unittest.TestCase):
    
    def setUp(self):
        self.driver = PanoramaMediaAnnotationDriver()

    def test_rect(self):
        context = Mock()
        self.driver.render(annotations=[TEST_RECT_ANNO], context=context)
        context.add_rect.assert_called_once_with(
            TEST_RECT_ANNO.rect.pt_min.x, TEST_RECT_ANNO.rect.pt_min.y, 
            TEST_RECT_ANNO.rect.pt_max.x, TEST_RECT_ANNO.rect.pt_max.y
        )

    def test_label(self):
        context = Mock()
        self.driver.render(annotations=[TEST_LABEL_ANNO], context=context)
        context.add_label.assert_called_once_with(
            TEST_LABEL_ANNO.text, TEST_LABEL_ANNO.point.x, TEST_LABEL_ANNO.point.y
        )

    def test_marker(self):
        context = Mock()
        self.driver.render(annotations=[TEST_MARKER_ANNO], context=context)
        context.add_label.assert_called_once_with(
            '*', TEST_POINT.x, TEST_POINT.y
        )
    
    def test_invalid(self):
        with self.assertRaises(ValueError):
            self.driver.render(annotations=['foobar'], context=Mock())


class TestOpenCVImageAnnotationDriver(unittest.TestCase):

    EXPECTED_CV2_COLOR = (150, 100, 50)
    
    def setUp(self):
        mock_cv2.reset_mock()
        mock_np.reset_mock()
        self.driver = OpenCVImageAnnotationDriver()

    def test_scale(self):
        img = Mock()
        img.shape = [200, 100, 3]
        self.assertEqual(
            (int(TEST_POINT.x * 100), int(TEST_POINT.y * 200)), 
            OpenCVImageAnnotationDriver.scale(TEST_POINT, img)
        )

    def test_rect(self):
        img = Mock()
        img.shape = [200, 100, 3] 
        self.driver.render(annotations=[TEST_RECT_ANNO], context=img)
        mock_cv2.rectangle.assert_called_once_with(
            img=img,
            pt1=(int(TEST_RECT_ANNO.rect.pt_min.x * 100), int(TEST_RECT_ANNO.rect.pt_min.y * 200)),
            pt2=(int(TEST_RECT_ANNO.rect.pt_max.x * 100), int(TEST_RECT_ANNO.rect.pt_max.y * 200)),
            color=self.EXPECTED_CV2_COLOR,
            thickness=OpenCVImageAnnotationDriver.DEFAULT_LINEWIDTH
        )

    def do_test_label_anchor(
        self, 
        horizontal_anchor=None, 
        vertical_anchor=None, 
        shift_x=lambda *_: 0, 
        shift_y=lambda *_: 0
    ):
        with self.subTest(horizontal_anchor=horizontal_anchor, vertical_anchor=vertical_anchor):
            mock_cv2.reset_mock()
            img = Mock()
            img.shape = [200, 100, 3] 
            text_size_x, text_size_y = (120, 15)
            baseline = 3
            mock_cv2.getTextSize.return_value = ((text_size_x, text_size_y), baseline)
            lbl_args = {
                'point': TEST_POINT,
                'text': 'Hello World',
                'color': TEST_COLOR,
            }
            if horizontal_anchor is not None:
                lbl_args['horizontal_anchor'] = horizontal_anchor
            if vertical_anchor is not None:
                lbl_args['vertical_anchor'] = vertical_anchor
            lbl = LabelAnnotation(**lbl_args)
            x, y = OpenCVImageAnnotationDriver.scale(lbl.point, img)
            self.driver.render(annotations=[lbl], context=img)
            mock_cv2.putText.assert_called_once_with(
                img=img, 
                text=lbl.text,
                org=ANY,
                fontFace=OpenCVImageAnnotationDriver.DEFAULT_FONT,
                fontScale=unittest.mock.ANY,
                color=self.EXPECTED_CV2_COLOR,
                thickness=unittest.mock.ANY
            )
            self.assertEqual(mock_cv2.putText.call_count, 1)
            called_org = mock_cv2.putText.call_args.kwargs['org']
            self.assertAlmostEqual(
                called_org[0], 
                x + shift_x(text_size_x, baseline), 
                delta=OpenCVImageAnnotationDriver.DEFAULT_TEXT_PADDING[0]
            )
            self.assertAlmostEqual(
                called_org[1], 
                y + shift_y(text_size_y, baseline), 
                delta=OpenCVImageAnnotationDriver.DEFAULT_TEXT_PADDING[1]
            )

    def test_label(self):
        img = Mock()
        img.shape = [200, 100, 3]
        with self.subTest('default anchor'):
            self.driver.render(annotations=[TEST_LABEL_ANNO], context=img)
            mock_cv2.putText.assert_called_once_with(
                img=img, 
                text=TEST_LABEL_ANNO.text,
                org=OpenCVImageAnnotationDriver.scale(TEST_LABEL_ANNO.point, img),
                fontFace=OpenCVImageAnnotationDriver.DEFAULT_FONT,
                fontScale=unittest.mock.ANY,
                color=self.EXPECTED_CV2_COLOR,
                thickness=unittest.mock.ANY
            )
        self.do_test_label_anchor(
            horizontal_anchor=LabelAnnotation.HorizontalAnchor.CENTER,
            shift_x=lambda text_x, _: -text_x / 2
        )
        self.do_test_label_anchor(
            horizontal_anchor=LabelAnnotation.HorizontalAnchor.RIGHT,
            shift_x=lambda text_x, _: -text_x
        )
        self.do_test_label_anchor(
            vertical_anchor=LabelAnnotation.VerticalAnchor.CENTER,
            shift_y=lambda text_y, _: text_y / 2
        )
        self.do_test_label_anchor(
            vertical_anchor=LabelAnnotation.VerticalAnchor.TOP,
            shift_y=lambda text_y, _: text_y
        )
        self.do_test_label_anchor(
            vertical_anchor=LabelAnnotation.VerticalAnchor.BASELINE,
            shift_y=lambda _, baseline: baseline
        )

    def test_line(self):
        img = Mock()
        img.shape = [200, 100, 3]
        self.driver.render(annotations=[TEST_LINE_ANNO], context=img)
        mock_cv2.line.assert_called_once_with(
            img=img,
            pt1=OpenCVImageAnnotationDriver.scale(TEST_LINE_ANNO.line.pt1, img),
            pt2=OpenCVImageAnnotationDriver.scale(TEST_LINE_ANNO.line.pt2, img),
            color=self.EXPECTED_CV2_COLOR,
            thickness=TEST_LINE_ANNO.thickness
        )

    def test_transparent(self):
        context = Mock(name='context_mock')
        drawer = Mock(name='drawer_mock')
        def reset_mocks():
            context.reset_mock()
            drawer.reset_mock()
        with self.subTest(alpha=1.0):
            reset_mocks()
            self.driver.draw_transparent(1.0, context, drawer)
            drawer.assert_called_once_with(context)
        with self.subTest(alpha=0.0):
            reset_mocks()
            self.driver.draw_transparent(0.0, context, drawer)
            drawer.assert_not_called()
            context.assert_not_called()
        with self.subTest(alpha=0.3):
            reset_mocks()
            alpha = 0.3
            self.driver.draw_transparent(alpha, context, drawer)
            overlay = context.copy()
            drawer.assert_called_once_with(overlay)
            mock_cv2.addWeighted.assert_called_once_with(overlay, alpha, context, 1 - alpha, 0)
