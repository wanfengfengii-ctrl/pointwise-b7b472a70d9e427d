from fractions import Fraction

from exchange.catalog import MissingAdmission
from report.publish import MissingReport, read
from review.endpoints import QuadraticRoot, compare_endpoints, rational_between
from review.inspection import review
from review.setpoint import point
from tests.fixtures import (HOLE, ISOLATED, OUT, QUALIFIED, RECIPROCAL, UNREADABLE,
                            ProjectCase, hole_segments, isolated_segments, row_count, span)


class TestReview(ProjectCase):
    def test_removable_hole_offline(self):
        admission, issued = self.offline(HOLE)
        result = review(self.center, admission, '0', '2', '1/2')
        self.assertEqual(result.segments, hole_segments())
        self.assertEqual(result.origin.issue_id, issued.issue_id)
        self.assertEqual(result.origin.freeze_id, issued.evidence.freeze_id)
        self.assertEqual(read(self.center, result.report_id), result)

    def test_point_edges(self):
        admission, _ = self.offline(HOLE)
        result = review(self.center, admission, 0, 2, '1/2')
        for x, expected in (('1/2', QUALIFIED), (1, UNREADABLE), ('3/2', QUALIFIED),
                            (0, OUT), (2, OUT)):
            with self.subTest(x=x):
                self.assertEqual(point(self.center, result.report_id, x), expected)
        singleton = review(self.center, admission, 1, 1, 0)
        self.assertEqual(singleton.segments, (span(UNREADABLE, 1, 1),))
        self.assertEqual(point(self.center, singleton.report_id, 1), UNREADABLE)
        equality = review(self.center, admission, '1/2', '1/2', '1/2')
        self.assertEqual(equality.segments, (span(QUALIFIED, '1/2', '1/2'),))
        with self.assertRaises(MissingReport):
            point(self.center, 999, 0)
        with self.assertRaises(ValueError):
            point(self.center, result.report_id, '5/2')
        with self.assertRaises(ValueError):
            point(self.center, result.report_id, 0.5)

    def test_invalid_request(self):
        admission, _ = self.offline(HOLE)
        for args in ((2, 0, '1/2'), (0, 2, -1), (0, 'NaN', 0), (0, 2, None), (0, 2, True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                review(self.center, admission, *args)
        with self.assertRaises(MissingAdmission):
            review(self.center, 'A999', 0, 2, '1/2')
        self.assertEqual(row_count(self.center, 'reports'), 0)
        self.assertEqual(row_count(self.center, 'report_receipts'), 0)

    def test_exact_isolated_setpoints(self):
        admission, _ = self.offline(ISOLATED)
        snapshot = review(self.center, admission, -2, 2, 0)
        self.assertEqual(snapshot.segments, isolated_segments())
        self.assertEqual(point(self.center, snapshot.report_id, -1), OUT)
        self.assertEqual(point(self.center, snapshot.report_id, 0), UNREADABLE)
        self.assertEqual(point(self.center, snapshot.report_id, '3/2'), OUT)

    def test_reciprocal_thresholds(self):
        admission, _ = self.offline(RECIPROCAL)
        snapshot = review(self.center, admission, -2, 2, 1)
        self.assertEqual(snapshot.segments, (
            span(QUALIFIED, -2, -1), span(OUT, -1, 0, False, False), span(UNREADABLE, 0, 0),
            span(OUT, 0, 1, False, False), span(QUALIFIED, 1, 2),
        ))
        self.assertEqual(point(self.center, snapshot.report_id, -1), QUALIFIED)
        self.assertEqual(point(self.center, snapshot.report_id, 1), QUALIFIED)
        self.assertEqual(point(self.center, snapshot.report_id, 0), UNREADABLE)

    def test_identical_response_with_two_original_holes(self):
        # Both responses equal one where readable, with holes at zero and one.
        marks = (('甲', 0, 0, 0), ('甲', 1, 1, 1), ('乙', 0, -1, -1), ('乙', 1, 0, 0))
        admission, _ = self.offline(marks)
        snapshot = review(self.center, admission, -1, 2, 0)
        self.assertEqual(snapshot.segments, (
            span(QUALIFIED, -1, 0, True, False), span(UNREADABLE, 0, 0),
            span(QUALIFIED, 0, 1, False, False), span(UNREADABLE, 1, 1),
            span(QUALIFIED, 1, 2, False, True),
        ))

    def test_quadratic_order_across_defining_polynomials(self):
        # 2 - sqrt(2) < sqrt(2) < sqrt(2 + 1/10**24).
        left = QuadraticRoot(1, -4, 2, -1)
        middle = QuadraticRoot(1, 0, -2, 1)
        scale = 10**24
        right = QuadraticRoot(scale, 0, -(2 * scale + 1), 1)
        self.assertEqual(compare_endpoints(left, middle), -1)
        self.assertEqual(compare_endpoints(right, middle), 1)
        witness = rational_between(middle, right)
        self.assertIsInstance(witness, Fraction)
        self.assertGreater(witness*witness, 2)
        self.assertLess(witness*witness, 2 + Fraction(1, scale))
