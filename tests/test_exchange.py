from dataclasses import replace
from fractions import Fraction
import json

from calibration.affine import Affine
from calibration.checks import InvalidCalibration
from calibration.issue import issue, read_issue
from exchange.admission import StationMismatch, admit
from exchange.catalog import AdmissionConflict, get_admission
from exchange.codec import InvalidExchange, encode_exchange
from station.freeze import freeze
from station.protocol import register_protocol
from tests.fixtures import CONSTANT, HOLE, ProjectCase, STATION, row_count


class TestExchange(ProjectCase):
    def test_identically_zero_denominator(self):
        marks = (('甲', 0, 1, 0), ('甲', 1, 2, 0), *HOLE[2:])
        roster = freeze(self.station, STATION, self.load_marks(marks))
        with self.assertRaises(InvalidCalibration):
            issue(self.station, roster.freeze_id)
        self.assertEqual(row_count(self.station, 'issues'), 0)
        self.assertEqual(row_count(self.station, 'dispatches'), 0)
        self.assertEqual(row_count(self.station, 'frozen_rosters'), 1)
        with self.assertRaises(KeyError):
            read_issue(self.station, 1)

    def test_duplicate_and_conflict(self):
        issued = self.certificate(HOLE)
        self.assertEqual(read_issue(self.station, issued.issue_id), issued)
        admission = admit(self.center, STATION, issued.wire)
        self.assertEqual(admit(self.center, STATION, issued.wire), admission)
        reformat = json.dumps(json.loads(issued.wire), indent=2)
        self.assertEqual(admit(self.center, STATION, reformat), admission)
        altered = replace(issued.evidence, revision_id=issued.evidence.revision_id + 1)
        with self.assertRaises(AdmissionConflict):
            admit(self.center, STATION, encode_exchange(altered).wire)
        self.assertEqual(row_count(self.center, 'admissions'), 1)
        self.assertEqual(get_admission(self.center, admission).envelope.wire, issued.wire)

    def test_station_binding(self):
        register_protocol(self.station, 'bench-B', ('甲', '乙'))
        original = self.certificate(HOLE)
        foreign = self.certificate(CONSTANT, station='bench-B')
        original_id = admit(self.center, STATION, original.wire)
        with self.assertRaises(StationMismatch):
            admit(self.center, STATION, foreign.wire)
        self.assertEqual(row_count(self.center, 'admissions'), 1)
        foreign_id = admit(self.center, 'bench-B', foreign.wire)
        self.assertEqual(get_admission(self.center, foreign_id).envelope.evidence.station, 'bench-B')
        self.assertEqual(get_admission(self.center, original_id).envelope.evidence, original.evidence)

    def test_body_conflict(self):
        issued = self.certificate(HOLE)
        admission = admit(self.center, STATION, issued.wire)
        first, second = issued.evidence.responses
        changed_first = replace(first, numerator=Affine(Fraction(2), Fraction(0)))
        altered = replace(issued.evidence, responses=(changed_first, second))
        with self.assertRaises(AdmissionConflict):
            admit(self.center, STATION, encode_exchange(altered).wire)
        self.station.close()
        self.center.close()
        self.center = self.open_center()
        saved = get_admission(self.center, admission)
        self.assertEqual(saved.envelope.wire, issued.wire)
        self.assertEqual(saved.admission_id, admission)
        self.assertEqual(row_count(self.center, 'admissions'), 1)

    def test_malformed_exchange(self):
        issued = self.certificate(HOLE)
        broken_digest = json.loads(issued.wire)
        broken_digest['body']['revision_id'] += 1
        broken_binding = json.loads(issued.wire)
        broken_binding['issue_id'] += 1
        for wire in (json.dumps(broken_digest), json.dumps(broken_binding),
                     '{"version":1,"version":1}'):
            with self.subTest(wire=wire), self.assertRaises(InvalidExchange):
                admit(self.center, STATION, wire)
        self.assertEqual(row_count(self.center, 'admissions'), 0)

    def test_domain_evidence(self):
        hole = self.certificate(HOLE)
        constant = self.certificate(CONSTANT)
        hole_id = admit(self.center, STATION, hole.wire)
        constant_id = admit(self.center, STATION, constant.wire)
        self.station.close()
        hole_evidence = get_admission(self.center, hole_id).envelope.evidence
        constant_evidence = get_admission(self.center, constant_id).envelope.evidence
        self.assertEqual(hole_evidence.unreadable_setpoints, (Fraction(1),))
        self.assertEqual(constant_evidence.unreadable_setpoints, ())
        for x in (Fraction(0), Fraction(2)):
            for evidence in (hole_evidence, constant_evidence):
                first, second = evidence.responses
                self.assertEqual(first.numerator.at(x) / first.denominator.at(x), 1)
                self.assertEqual(second.numerator.at(x) / second.denominator.at(x), x)
        self.assertEqual(hole_evidence.responses[0].denominator.at(Fraction(1)), 0)
        self.assertEqual(constant_evidence.responses[0].denominator.at(Fraction(1)), 1)
