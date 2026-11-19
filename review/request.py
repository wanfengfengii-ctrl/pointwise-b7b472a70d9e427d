from dataclasses import dataclass
from fractions import Fraction

from station.rational import parse_rational


@dataclass(frozen=True, slots=True)
class ReviewRequest:
    admission_id: str
    left: Fraction
    right: Fraction
    tolerance: Fraction


def parse_review_request(admission_id, left, right, tolerance):
    if type(admission_id) is not str or not admission_id.strip():
        raise ValueError('expected an admission id')
    left, right, tolerance = map(parse_rational, (left, right, tolerance))
    if left > right:
        raise ValueError('review window is reversed')
    if tolerance < 0:
        raise ValueError('tolerance must be nonnegative')
    return ReviewRequest(admission_id, left, right, tolerance)
