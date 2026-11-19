import sqlite3


def is_rowid(value):
    return type(value) is int and 0 < value <= 2**63 - 1


def initialize_station_store(db):
    with db:
        db.executescript('''
            BEGIN;
            CREATE TABLE IF NOT EXISTS protocols (
                station TEXT PRIMARY KEY NOT NULL,
                first_channel TEXT NOT NULL,
                second_channel TEXT NOT NULL,
                CHECK (first_channel <> second_channel)
            );
            CREATE TABLE IF NOT EXISTS revisions (
                revision_id INTEGER PRIMARY KEY,
                station TEXT NOT NULL REFERENCES protocols(station),
                parent_id INTEGER REFERENCES revisions(revision_id)
            );
            CREATE TABLE IF NOT EXISTS readings (
                revision_id INTEGER NOT NULL REFERENCES revisions(revision_id),
                channel TEXT NOT NULL,
                coordinate INTEGER NOT NULL CHECK (coordinate IN (0, 1)),
                numerator TEXT NOT NULL,
                denominator TEXT NOT NULL,
                PRIMARY KEY (revision_id, channel, coordinate)
            );
            CREATE TABLE IF NOT EXISTS frozen_rosters (
                freeze_id INTEGER PRIMARY KEY,
                revision_id INTEGER NOT NULL REFERENCES revisions(revision_id),
                station TEXT NOT NULL REFERENCES protocols(station)
            );
            CREATE TABLE IF NOT EXISTS frozen_readings (
                freeze_id INTEGER NOT NULL REFERENCES frozen_rosters(freeze_id),
                channel TEXT NOT NULL,
                coordinate INTEGER NOT NULL CHECK (coordinate IN (0, 1)),
                numerator TEXT NOT NULL,
                denominator TEXT NOT NULL,
                PRIMARY KEY (freeze_id, channel, coordinate)
            );
            COMMIT;
        ''')


def open_station_store(path):
    db = sqlite3.connect(path)
    try:
        db.execute('PRAGMA foreign_keys = ON')
        initialize_station_store(db)
    except BaseException:
        db.close()
        raise
    return db
