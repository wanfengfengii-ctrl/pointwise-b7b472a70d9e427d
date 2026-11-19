from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from calibration.issue import initialize_issues, issue
from exchange.admission import admit
from report.store import open_center_store
from review.endpoints import QuadraticRoot
from review.partition import Segment
from station.freeze import freeze
from station.protocol import register_protocol
from station.revisions import load
from station.store import open_station_store


HOLE = (('甲', 0, -1, -1), ('甲', 1, 0, 0), ('乙', 0, 0, 1), ('乙', 1, 1, 1))
CONSTANT = (('甲', 0, 1, 1), ('甲', 1, 1, 1), *HOLE[2:])
ISOLATED = (('甲', 0, 0, 1), ('甲', 1, 1, 1), ('乙', 0, 2, 0), ('乙', 1, 2, 1))
RECIPROCAL = (('甲', 0, 1, 0), ('甲', 1, 1, 1), ('乙', 0, 0, 1), ('乙', 1, 0, 1))
STATION = 'bench-A'
QUALIFIED = 'qualified'
OUT = 'out_of_tolerance'
UNREADABLE = 'unreadable'


def span(category, left, right, lc=True, rc=True):
    left = left if isinstance(left, QuadraticRoot) else Fraction(left)
    right = right if isinstance(right, QuadraticRoot) else Fraction(right)
    return Segment(left, right, lc, rc, category)


def hole_segments():
    return (span(OUT, 0, '1/2', True, False), span(QUALIFIED, '1/2', 1, True, False),
            span(UNREADABLE, 1, 1), span(QUALIFIED, 1, '3/2', False, True),
            span(OUT, '3/2', 2, False, True))


def isolated_segments():
    small, large = QuadraticRoot(1, 0, -2, -1), QuadraticRoot(1, 0, -2, 1)
    return (span(OUT, -2, small, True, False), span(QUALIFIED, small, small),
            span(OUT, small, 0, False, False), span(UNREADABLE, 0, 0),
            span(OUT, 0, large, False, False), span(QUALIFIED, large, large),
            span(OUT, large, 2, False, True))


def row_count(db, table):
    tables = ('revisions', 'frozen_rosters', 'issues', 'dispatches', 'admissions',
              'reports', 'report_receipts', 'commit_failures')
    if table not in tables:
        raise ValueError('unknown fixture table')
    return db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]


def reject_report_commit(db):
    db.executescript('''
        CREATE TABLE commit_targets (id INTEGER PRIMARY KEY);
        CREATE TABLE commit_failures (
            target INTEGER REFERENCES commit_targets(id) DEFERRABLE INITIALLY DEFERRED
        );
        CREATE TRIGGER reject_report_commit AFTER INSERT ON report_receipts
        BEGIN
            INSERT INTO commit_failures (target) VALUES (1);
        END;
    ''')


class ProjectCase(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ratio-tests-')
        self.addCleanup(directory.cleanup)
        self.station_path = Path(directory.name) / 'station.sqlite3'
        self.center_path = Path(directory.name) / 'center.sqlite3'
        self.station = self.open_station()
        self.center = self.open_center()
        register_protocol(self.station, STATION, ('甲', '乙'))

    def open_station(self):
        db = open_station_store(self.station_path)
        self.addCleanup(db.close)
        initialize_issues(db)
        return db

    def open_center(self):
        db = open_center_store(self.center_path)
        self.addCleanup(db.close)
        return db

    def load_marks(self, marks, station=STATION, base_revision=None):
        for mark in marks:
            base_revision = load(self.station, station, *mark, base_revision=base_revision)
        return base_revision

    def certificate(self, marks, station=STATION, base_revision=None):
        revision = self.load_marks(marks, station, base_revision)
        roster = freeze(self.station, station, revision)
        return issue(self.station, roster.freeze_id)

    def offline(self, marks):
        issued = self.certificate(marks)
        admission = admit(self.center, STATION, issued.wire)
        self.station.close()
        return admission, issued
