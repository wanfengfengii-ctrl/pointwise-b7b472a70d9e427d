from dataclasses import dataclass

from calibration.affine import fit_responses
from calibration.evidence import CertificateEvidence, build_evidence
from exchange.codec import decode_exchange
from exchange.dispatch import DispatchRecord, prepare_dispatch
from station.freeze import read_frozen_roster
from station.store import is_rowid


@dataclass(frozen=True, slots=True)
class IssuedCalibration:
    evidence: CertificateEvidence
    dispatch: DispatchRecord

    @property
    def issue_id(self):
        return self.evidence.issue_id

    @property
    def wire(self):
        return self.dispatch.envelope.wire


def initialize_issues(db):
    with db:
        db.executescript('''
            BEGIN;
            CREATE TABLE IF NOT EXISTS issues (
                issue_id INTEGER PRIMARY KEY,
                freeze_id INTEGER NOT NULL REFERENCES frozen_rosters(freeze_id)
            );
            CREATE TABLE IF NOT EXISTS dispatches (
                issue_id INTEGER PRIMARY KEY REFERENCES issues(issue_id),
                station TEXT NOT NULL REFERENCES protocols(station),
                body_sha256 TEXT NOT NULL,
                wire TEXT NOT NULL
            );
            COMMIT;
        ''')


def issue(db, freeze_id):
    roster = read_frozen_roster(db, freeze_id)
    responses = fit_responses(roster)
    with db:
        cursor = db.execute('INSERT INTO issues (freeze_id) VALUES (?)', (freeze_id,))
        evidence = build_evidence(cursor.lastrowid, roster, responses)
        dispatch = prepare_dispatch(evidence)
        db.execute('''
            INSERT INTO dispatches (issue_id, station, body_sha256, wire) VALUES (?, ?, ?, ?)
        ''', (dispatch.issue_id, dispatch.station, dispatch.body_sha256, dispatch.envelope.wire))
    return IssuedCalibration(evidence, dispatch)


def read_issue(db, issue_id):
    if not is_rowid(issue_id):
        raise ValueError('invalid issue id')
    row = db.execute('''
        SELECT i.freeze_id, d.station, d.body_sha256, d.wire
        FROM issues AS i JOIN dispatches AS d USING (issue_id) WHERE issue_id = ?
    ''', (issue_id,)).fetchone()
    if row is None:
        raise KeyError(f'unknown issue {issue_id}')
    freeze_id, station, digest, wire = row
    envelope = decode_exchange(wire)
    evidence = envelope.evidence
    if (evidence.freeze_id, evidence.station, evidence.issue_id, envelope.body_sha256) != (
            freeze_id, station, issue_id, digest):
        raise ValueError('stored issue and dispatch disagree')
    return IssuedCalibration(evidence, DispatchRecord(station, issue_id, digest, envelope))
