from dataclasses import dataclass

from station.protocol import require_protocol
from station.readings import Reading, decode_reading_row, parse_reading
from station.store import is_rowid


@dataclass(frozen=True, slots=True)
class ReadingRevision:
    revision_id: int
    station: str
    parent_id: int | None
    readings: tuple[Reading, ...]


def read_revision(db, station, revision_id):
    require_protocol(db, station)
    if not is_rowid(revision_id):
        raise ValueError('invalid revision id')
    row = db.execute('''
        SELECT parent_id FROM revisions WHERE revision_id = ? AND station = ?
    ''', (revision_id, station)).fetchone()
    if row is None:
        raise KeyError(f'unknown revision {revision_id} for {station!r}')
    readings = db.execute('''
        SELECT channel, coordinate, numerator, denominator FROM readings
        WHERE revision_id = ? ORDER BY channel, coordinate
    ''', (revision_id,))
    return ReadingRevision(revision_id, station, row[0], tuple(map(decode_reading_row, readings)))


def load(db, station, channel, x, numerator, denominator, base_revision=None):
    protocol = require_protocol(db, station)
    reading = parse_reading(protocol, channel, x, numerator, denominator)
    points = {}
    if base_revision is not None:
        parent = read_revision(db, station, base_revision)
        points.update(((item.channel, item.coordinate), item) for item in parent.readings)
    points[(reading.channel, reading.coordinate)] = reading
    with db:
        cursor = db.execute('INSERT INTO revisions (station, parent_id) VALUES (?, ?)',
                            (station, base_revision))
        revision_id = cursor.lastrowid
        db.executemany('''
            INSERT INTO readings (revision_id, channel, coordinate, numerator, denominator)
            VALUES (?, ?, ?, ?, ?)
        ''', ((revision_id, item.channel, item.coordinate, str(item.numerator),
               str(item.denominator)) for item in points.values()))
    return revision_id
