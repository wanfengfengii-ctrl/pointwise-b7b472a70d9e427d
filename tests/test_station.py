from fractions import Fraction

from station.freeze import freeze, read_frozen_roster
from station.protocol import register_protocol, require_protocol
from station.readings import Reading
from station.revisions import load, read_revision
from station.store import initialize_station_store
from tests.fixtures import HOLE, ProjectCase, STATION, row_count


class TestStation(ProjectCase):
    def test_repeat_init_and_freeze(self):
        revision = self.load_marks(HOLE)
        self.station.close()
        self.station = self.open_station()
        register_protocol(self.station, STATION, ('甲', '乙'))
        roster = freeze(self.station, STATION, revision)
        expected = {Reading(channel, x, Fraction(n), Fraction(d)) for channel, x, n, d in HOLE}
        self.assertEqual(len(roster.readings), 4)
        self.assertEqual(set(roster.readings), expected)
        self.assertEqual(roster.revision_id, revision)
        initialize_station_store(self.station)
        self.assertEqual(read_frozen_roster(self.station, roster.freeze_id), roster)
        self.assertEqual(require_protocol(self.station, STATION).channels, ('甲', '乙'))

    def test_pinned_revision(self):
        original = self.load_marks(HOLE)
        corrected = self.load_marks((('甲', 0, '1/4', '1/2'),), base_revision=original)
        roster = freeze(self.station, STATION, original)
        updated = freeze(self.station, STATION, corrected)
        old = {(r.channel, r.coordinate): (r.numerator, r.denominator) for r in roster.readings}
        new = {(r.channel, r.coordinate): (r.numerator, r.denominator) for r in updated.readings}
        self.assertEqual(roster.revision_id, original)
        self.assertEqual(old, {(channel, x): (n, d) for channel, x, n, d in HOLE})
        self.assertEqual(new, dict(old) | {('甲', 0): (Fraction(1, 4), Fraction(1, 2))})
        self.assertEqual(read_revision(self.station, STATION, corrected).parent_id, original)
        self.assertEqual(read_frozen_roster(self.station, roster.freeze_id), roster)

    def test_invalid_reading(self):
        revision = self.load_marks(HOLE[:1])
        before = read_revision(self.station, STATION, revision)
        register_protocol(self.station, 'bench-B', ('甲', '乙'))
        for bad in (('丙', 0, 1, 1), ('甲', 2, 1, 1), ('甲', True, 1, 1),
                    ('甲', 0, '', 1), ('甲', 0, 1, None), ('甲', 0, '1/0', 1),
                    ('甲', 0, 0.5, 1)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                load(self.station, STATION, *bad, base_revision=revision)
        with self.assertRaises(KeyError):
            load(self.station, 'bench-B', '甲', 0, 1, 1, base_revision=revision)
        with self.assertRaises(KeyError):
            load(self.station, 'unknown', '甲', 0, 1, 1)
        with self.assertRaises(ValueError):
            register_protocol(self.station, STATION, ('乙', '甲'))
        self.assertEqual(row_count(self.station, 'revisions'), 1)
        self.assertEqual(read_revision(self.station, STATION, revision), before)

    def test_missing_reading(self):
        revision = self.load_marks((HOLE[0], HOLE[2], HOLE[3]))
        with self.assertRaises(ValueError):
            freeze(self.station, STATION, revision)
        self.assertEqual(row_count(self.station, 'frozen_rosters'), 0)

    def test_partial_roster(self):
        revision = self.load_marks(HOLE[:3])
        with self.assertRaises(ValueError):
            freeze(self.station, STATION, revision)
        self.assertEqual(row_count(self.station, 'frozen_rosters'), 0)
        complete = self.load_marks(HOLE[3:], base_revision=revision)
        roster = freeze(self.station, STATION, complete)
        self.assertEqual(len(roster.readings), 4)
        self.assertEqual(roster.revision_id, complete)
        self.assertEqual(len(read_revision(self.station, STATION, revision).readings), 3)
