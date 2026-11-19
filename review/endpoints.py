from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isqrt

from station.rational import rational_from_parts, rational_parts


def _sign(value):
    return (value > 0) - (value < 0)


@dataclass(frozen=True, slots=True)
class QuadraticRoot:
    a: int
    b: int
    c: int
    branch: int

    def __post_init__(self):
        if (any(type(value) is not int for value in (self.a, self.b, self.c, self.branch))
                or self.a <= 0 or gcd(self.a, self.b, self.c) != 1 or self.branch not in (-1, 1)):
            raise ValueError('expected a primitive quadratic and a root branch')
        discriminant = self.discriminant
        if discriminant <= 0 or isqrt(discriminant)**2 == discriminant:
            raise ValueError('quadratic root must be real and irrational')

    @property
    def discriminant(self):
        return self.b**2 - 4 * self.a * self.c

    def compare_fraction(self, value: Fraction):
        offset = 2 * self.a * value + self.b
        if self.branch == 1:
            return 1 if offset <= 0 else _sign(self.discriminant - offset**2)
        return -1 if offset >= 0 else _sign(offset**2 - self.discriminant)

    def bounds(self):
        floor = isqrt(self.discriminant)
        first = Fraction(-self.b + self.branch * floor, 2 * self.a)
        second = Fraction(-self.b + self.branch * (floor + 1), 2 * self.a)
        return min(first, second), max(first, second)


Endpoint = Fraction | QuadraticRoot


def _refine(root, bounds):
    if isinstance(root, Fraction):
        return bounds
    low, high = bounds
    middle = (low + high) / 2
    if root.compare_fraction(middle) < 0:
        return low, middle
    return middle, high


def compare_endpoints(left: Endpoint, right: Endpoint):
    if isinstance(left, Fraction):
        if isinstance(right, Fraction):
            return _sign(left - right)
        return -right.compare_fraction(left)
    if isinstance(right, Fraction):
        return left.compare_fraction(right)
    if (left.a, left.b, left.c) == (right.a, right.b, right.c):
        return _sign(left.branch - right.branch)
    # Different primitive irreducible quadratics cannot share a root.
    left_bounds, right_bounds = left.bounds(), right.bounds()
    while True:
        if left_bounds[1] <= right_bounds[0]:
            return -1
        if right_bounds[1] <= left_bounds[0]:
            return 1
        left_bounds = _refine(left, left_bounds)
        right_bounds = _refine(right, right_bounds)


def rational_between(left: Endpoint, right: Endpoint):
    if compare_endpoints(left, right) >= 0:
        raise ValueError('interval must have positive width')
    left_bounds = (left, left) if isinstance(left, Fraction) else left.bounds()
    right_bounds = (right, right) if isinstance(right, Fraction) else right.bounds()
    while left_bounds[1] >= right_bounds[0]:
        left_bounds = _refine(left, left_bounds)
        right_bounds = _refine(right, right_bounds)
    return (left_bounds[1] + right_bounds[0]) / 2


def encode_endpoint(endpoint: Endpoint):
    if isinstance(endpoint, QuadraticRoot):
        return ['quadratic', endpoint.a, endpoint.b, endpoint.c, endpoint.branch]
    return ['rational', *rational_parts(endpoint)]


def decode_endpoint(data):
    if type(data) is list and data:
        if data[0] == 'rational' and len(data) == 3:
            return rational_from_parts(data[1:])
        if data[0] == 'quadratic' and len(data) == 5:
            return QuadraticRoot(*data[1:])
    raise ValueError('invalid endpoint encoding')
