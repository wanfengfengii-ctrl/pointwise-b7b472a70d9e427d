import json
import sqlite3

from exchange.admission import admit
from exchange.catalog import initialize_catalog
from report.export import export_report
from report.publish import MissingReport, read
from report.store import initialize_reports
from review.inspection import review
from review.setpoint import point
from tests.fixtures import (CONSTANT, HOLE, ISOLATED, OUT, QUALIFIED, STATION, UNREADABLE,
                            ProjectCase, hole_segments, isolated_segments, reject_report_commit,
                            row_count, span)


class TestReports(ProjectCase):
    def _corrected_reports(self):
        hole = self.certificate(HOLE)
        fixed = self.certificate(CONSTANT[:2], base_revision=hole.evidence.revision_id)
        # Reverse receipt order to distinguish even the numeric portions of each id.
        fixed_admission = admit(self.center, STATION, fixed.wire)
        hole_admission = admit(self.center, STATION, hole.wire)
        self.station.close()
        original = review(self.center, hole_admission, 0, 2, '1/2')
        corrected = review(self.center, fixed_admission, 0, 2, '1/2')
        self.center.close()
        self.center = self.open_center()
        return original, corrected, hole, fixed

    def test_corrected_calibration_and_reopen(self):
        original, corrected, hole, fixed = self._corrected_reports()
        self.assertEqual(original.segments, hole_segments())
        self.assertEqual(corrected.segments, (
            span(OUT, 0, '1/2', True, False), span(QUALIFIED, '1/2', '3/2'),
            span(OUT, '3/2', 2, False, True),
        ))
        self.assertEqual(read(self.center, original.report_id), original)
        self.assertEqual(read(self.center, corrected.report_id), corrected)
        self.assertEqual(point(self.center, original.report_id, 1), UNREADABLE)
        self.assertEqual(point(self.center, corrected.report_id, 1), QUALIFIED)
        self.assertEqual(original.receipt.issue_id, hole.issue_id)
        self.assertEqual(corrected.receipt.issue_id, fixed.issue_id)
        self.assertEqual(original.origin.revision_id, hole.evidence.revision_id)
        self.assertEqual(corrected.origin.revision_id, fixed.evidence.revision_id)
        with self.assertRaises(MissingReport):
            read(self.center, 999)
        with self.assertRaises(MissingReport):
            export_report(self.center, 999)

    def test_repeat_init(self):
        original, corrected, _, _ = self._corrected_reports()
        initialize_catalog(self.center)
        initialize_reports(self.center)
        self.assertEqual(row_count(self.center, 'admissions'), 2)
        self.assertEqual(row_count(self.center, 'reports'), 2)
        self.assertEqual(row_count(self.center, 'report_receipts'), 2)
        self.assertEqual(read(self.center, original.report_id), original)
        self.assertEqual(read(self.center, corrected.report_id), corrected)

    def test_receipt_issue_namespace(self):
        original, corrected, hole, fixed = self._corrected_reports()
        for snapshot, issued in ((original, hole), (corrected, fixed)):
            saved = read(self.center, snapshot.report_id)
            self.assertNotEqual(int(saved.origin.admission_id[1:]), issued.issue_id)
            self.assertEqual(saved.receipt.report_id, saved.report_id)
            self.assertEqual(saved.receipt.issue_id, issued.issue_id)
            self.assertEqual(saved.origin.issue_id, issued.issue_id)
            self.assertEqual(saved.origin.freeze_id, issued.evidence.freeze_id)

    def test_algebraic_roundtrip(self):
        admission, issued = self.offline(ISOLATED)
        signed = review(self.center, admission, -2, 2, 0)
        before = export_report(self.center, signed.report_id)
        self.center.close()
        self.center = self.open_center()
        saved = read(self.center, signed.report_id)
        self.assertEqual(saved, signed)
        self.assertEqual(saved.segments, isolated_segments())
        exported = export_report(self.center, signed.report_id)
        self.assertEqual(exported, before)
        data = json.loads(exported)
        small, large = ['quadratic', 1, 0, -2, -1], ['quadratic', 1, 0, -2, 1]
        zero, low, high = ['rational', 0, 1], ['rational', -2, 1], ['rational', 2, 1]
        self.assertEqual([(s['category'], s['left'], s['right'], s['left_closed'], s['right_closed'])
                          for s in data['segments']], [
            (OUT, low, small, True, False), (QUALIFIED, small, small, True, True),
            (OUT, small, zero, False, False), (UNREADABLE, zero, zero, True, True),
            (OUT, zero, large, False, False), (QUALIFIED, large, large, True, True),
            (OUT, large, high, False, True),
        ])
        self.assertEqual(data['receipt'], {'report_id': signed.report_id, 'issue_id': issued.issue_id})

    def test_publish_rollback(self):
        admission, _ = self.offline(HOLE)
        reject_report_commit(self.center)
        with self.assertRaises(sqlite3.IntegrityError):
            review(self.center, admission, 0, 2, '1/2')
        self.assertEqual(row_count(self.center, 'reports'), 0)
        self.assertEqual(row_count(self.center, 'report_receipts'), 0)
        self.assertEqual(row_count(self.center, 'commit_failures'), 0)
        self.assertFalse(self.center.in_transaction)

    def test_atomic_retry(self):
        admission, issued = self.offline(HOLE)
        prior = review(self.center, admission, 0, 0, '1/2')
        reject_report_commit(self.center)
        with self.assertRaises(sqlite3.IntegrityError):
            review(self.center, admission, 0, 2, '1/2')
        self.center.close()
        self.center = self.open_center()
        self.assertEqual(row_count(self.center, 'reports'), 1)
        self.assertEqual(row_count(self.center, 'report_receipts'), 1)
        self.assertEqual(row_count(self.center, 'commit_failures'), 0)
        self.assertEqual(read(self.center, prior.report_id), prior)
        self.center.execute('DROP TRIGGER reject_report_commit')
        result = review(self.center, admission, 0, 2, '1/2')
        self.assertEqual(result.segments, hole_segments())
        self.assertEqual(read(self.center, result.report_id), result)
        self.assertEqual(result.receipt.report_id, result.report_id)
        self.assertEqual(result.receipt.issue_id, issued.issue_id)
        self.assertEqual(row_count(self.center, 'reports'), 2)
        self.assertEqual(row_count(self.center, 'report_receipts'), 2)
