from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StationProtocol:
    station: str
    channels: tuple[str, str]
    coordinates: tuple[int, int] = (0, 1)


def valid_label(value):
    return type(value) is str and bool(value) and value == value.strip()


def require_protocol(db, station):
    if not valid_label(station):
        raise ValueError('invalid station identity')
    row = db.execute(
        'SELECT first_channel, second_channel FROM protocols WHERE station = ?',
        (station,),
    ).fetchone()
    if row is None:
        raise KeyError(f'unknown station {station!r}')
    return StationProtocol(station, tuple(row))


def register_protocol(db, station, channels):
    if (not valid_label(station) or not isinstance(channels, (tuple, list))
            or len(channels) != 2 or not all(map(valid_label, channels))
            or channels[0] == channels[1]):
        raise ValueError('a protocol requires a station and two distinct channel labels')
    protocol = StationProtocol(station, tuple(channels))
    with db:
        db.execute('''
            INSERT INTO protocols (station, first_channel, second_channel)
            VALUES (?, ?, ?) ON CONFLICT(station) DO NOTHING
        ''', (station, *protocol.channels))
        if require_protocol(db, station) != protocol:
            raise ValueError('station already uses a different protocol')
    return protocol
