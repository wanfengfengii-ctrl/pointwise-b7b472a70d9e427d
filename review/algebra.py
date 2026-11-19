from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isqrt, lcm

from calibration.evidence import CertificateEvidence
from review.endpoints import Endpoint, QuadraticRoot, compare_endpoints


Polynomial = tuple[Fraction, Fraction, Fraction]


@dataclass(frozen=True, slots=True)
class Thresholds:
    minus: Polynomial
    plus: Polynomial


def _multiply(first, second):
    return (first.intercept * second.intercept,
            first.slope * second.intercept + first.intercept * second.slope,
            first.slope * second.slope)


def build_thresholds(evidence: CertificateEvidence, tolerance: Fraction):
    first, second = evidence.responses
    first_cross = _multiply(first.numerator, second.denominator)
    second_cross = _multiply(second.numerator, first.denominator)
    denominator = _multiply(first.denominator, second.denominator)
    numerator = tuple(a - b for a, b in zip(first_cross, second_cross))
    return Thresholds(tuple(p - tolerance*q for p, q in zip(numerator, denominator)),
                      tuple(p + tolerance*q for p, q in zip(numerator, denominator)))


def real_roots(polynomial: Polynomial):
    """Return the finite boundary roots. A constant contributes no boundaries."""
    constant, linear, quadratic = map(Fraction, polynomial)
    if quadratic == 0:
        return (-constant / linear,) if linear else ()
    scale = lcm(constant.denominator, linear.denominator, quadratic.denominator)
    a, b, c = (int(coefficient * scale) for coefficient in (quadratic, linear, constant))
    common = gcd(a, b, c) * (1 if a > 0 else -1)
    a, b, c = a // common, b // common, c // common
    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return ()
    floor = isqrt(discriminant)
    if floor*floor == discriminant:
        small = Fraction(-b - floor, 2*a)
        return (small,) if floor == 0 else (small, Fraction(-b + floor, 2*a))
    return (QuadraticRoot(a, b, c, -1), QuadraticRoot(a, b, c, 1))


def polynomial_sign_at(polynomial: Polynomial, point: Endpoint):
    constant, linear, quadratic = map(Fraction, polynomial)
    if isinstance(point, Fraction):
        value = (quadratic * point + linear) * point + constant
        return (value > 0) - (value < 0)
    # Reduce the polynomial modulo the root's defining quadratic.
    constant -= quadratic * point.c / point.a
    linear -= quadratic * point.b / point.a
    if linear == 0:
        return (constant > 0) - (constant < 0)
    return (1 if linear > 0 else -1) * compare_endpoints(point, -constant / linear)
