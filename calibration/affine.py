from dataclasses import dataclass
from fractions import Fraction

from station.freeze import FrozenRoster


@dataclass(frozen=True, slots=True)
class Affine:
    intercept: Fraction
    slope: Fraction

    @classmethod
    def from_marks(cls, at_zero, at_one):
        return cls(at_zero, at_one - at_zero)

    def at(self, x):
        return self.intercept + self.slope * x

    def zero(self):
        if self.slope:
            return -self.intercept / self.slope
        return None


@dataclass(frozen=True, slots=True)
class ChannelResponse:
    channel: str
    numerator: Affine
    denominator: Affine


def fit_responses(roster: FrozenRoster):
    by_point = {(reading.channel, reading.coordinate): reading for reading in roster.readings}
    responses = []
    for channel in roster.channels:
        zero = by_point[(channel, 0)]
        one = by_point[(channel, 1)]
        responses.append(ChannelResponse(
            channel,
            Affine.from_marks(zero.numerator, one.numerator),
            Affine.from_marks(zero.denominator, one.denominator),
        ))
    return tuple(responses)
