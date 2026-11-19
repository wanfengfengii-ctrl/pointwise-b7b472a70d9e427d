from exchange.catalog import register_or_replay
from exchange.codec import decode_exchange
from station.protocol import valid_label


class StationMismatch(ValueError):
    pass


def admit(db, station, wire):
    if not valid_label(station):
        raise ValueError('invalid receiving station')
    envelope = decode_exchange(wire)
    if envelope.evidence.station != station:
        raise StationMismatch('exchange belongs to a different station')
    return register_or_replay(db, envelope).admission_id
