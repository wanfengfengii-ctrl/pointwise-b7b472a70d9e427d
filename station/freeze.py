from dataclasses import dataclass

from station.protocol import require_protocol
from station.readings import Reading, decode_reading_row
from station.revisions import read_revision
from station.store import is_rowid


@dataclass(frozen=True, slots=True)
class FrozenRoster:
    freeze_id: int
    station: str
    revision_id: int
    channels: tuple[str, str]
    readings: tuple[Reading, ...]


def freeze(db, station, revision_id):
    protocol = require_protocol(db, station)
    revision = read_revision(db, station, revision_id)
    expected = {(channel, x) for channel in protocol.channels for x in protocol.coordinates}
    actual = {(reading.channel, reading.coordinate) for reading in revision.readings}
    if actual != expected or len(revision.readings) != len(expected):
        raise ValueError('freezing requires both coordinates on both channels')
    with db:
        cursor = db.execute('''
            INSERT INTO frozen_rosters (revision_id, station) VALUES (?, ?)
        ''', (revision_id, station))
        freeze_id = cursor.lastrowid
        db.execute('''
            INSERT INTO frozen_readings (freeze_id, channel, coordinate, numerator, denominator)
            SELECT ?, channel, coordinate, numerator, denominator
            FROM readings WHERE revision_id = ?
        ''', (freeze_id, revision_id))
    return FrozenRoster(freeze_id, station, revision_id, protocol.channels, revision.readings)


def read_frozen_roster(db, freeze_id):
    if not is_rowid(freeze_id):
        raise ValueError('invalid freeze id')
    row = db.execute('SELECT station, revision_id FROM frozen_rosters WHERE freeze_id = ?',
                     (freeze_id,)).fetchone()
    if row is None:
        raise KeyError(f'unknown freeze {freeze_id}')
    station, revision_id = row
    readings = db.execute('''
        SELECT channel, coordinate, numerator, denominator FROM frozen_readings
        WHERE freeze_id = ? ORDER BY channel, coordinate
    ''', (freeze_id,))
    return FrozenRoster(freeze_id, station, revision_id, require_protocol(db, station).channels,
                        tuple(map(decode_reading_row, readings)))
