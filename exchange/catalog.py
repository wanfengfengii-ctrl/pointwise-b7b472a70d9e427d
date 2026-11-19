from dataclasses import dataclass
import re

from exchange.codec import ExchangeEnvelope, decode_exchange
from station.store import is_rowid


_ADMISSION_ID = re.compile(r'A([1-9][0-9]{0,18})')


class MissingAdmission(KeyError):
    pass


class AdmissionConflict(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AdmissionRecord:
    admission_id: str
    envelope: ExchangeEnvelope


def initialize_catalog(db):
    with db:
        db.execute('''
            CREATE TABLE IF NOT EXISTS admissions (
                admission_no INTEGER PRIMARY KEY,
                station TEXT NOT NULL,
                issue_id INTEGER NOT NULL,
                wire TEXT NOT NULL,
                UNIQUE (station, issue_id)
            )
        ''')


def _record(row):
    number, station, issue_id, wire = row
    envelope = decode_exchange(wire)
    if (station, issue_id) != (envelope.evidence.station, envelope.evidence.issue_id):
        raise ValueError('stored exchange identity disagrees with its admission')
    return AdmissionRecord(f'A{number}', envelope)


def get_admission(db, admission_id):
    match = _ADMISSION_ID.fullmatch(admission_id) if type(admission_id) is str else None
    if match is None or not is_rowid(number := int(match[1])):
        raise ValueError('invalid admission id')
    row = db.execute('''
        SELECT admission_no, station, issue_id, wire FROM admissions WHERE admission_no = ?
    ''', (number,)).fetchone()
    if row is None:
        raise MissingAdmission(admission_id)
    return _record(row)


def register_or_replay(db, envelope: ExchangeEnvelope):
    identity = (envelope.evidence.station, envelope.evidence.issue_id)
    with db:
        db.execute('''
            INSERT INTO admissions (station, issue_id, wire) VALUES (?, ?, ?)
            ON CONFLICT (station, issue_id) DO NOTHING
        ''', (*identity, envelope.wire))
        row = db.execute('''
            SELECT admission_no, station, issue_id, wire FROM admissions
            WHERE station = ? AND issue_id = ?
        ''', identity).fetchone()
        record = _record(row)
        if record.envelope.evidence != envelope.evidence:
            raise AdmissionConflict('different body for an admitted station and issue')
    return record
