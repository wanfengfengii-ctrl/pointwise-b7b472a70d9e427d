from dataclasses import dataclass
from fractions import Fraction

from station.protocol import StationProtocol, valid_label
from station.rational import parse_rational


@dataclass(frozen=True, slots=True)
class Reading:
    channel: str
    coordinate: int
    numerator: Fraction
    denominator: Fraction


def parse_reading(protocol: StationProtocol, channel, x, numerator, denominator):
    if not valid_label(channel) or channel not in protocol.channels:
        raise ValueError('unknown channel for station protocol')
    coordinate = parse_rational(x)
    if coordinate not in protocol.coordinates:
        raise ValueError('reading coordinate must be 0 or 1')
    return Reading(channel, int(coordinate), parse_rational(numerator), parse_rational(denominator))


def decode_reading_row(row):
    channel, coordinate, numerator, denominator = row
    return Reading(channel, coordinate, parse_rational(numerator), parse_rational(denominator))
