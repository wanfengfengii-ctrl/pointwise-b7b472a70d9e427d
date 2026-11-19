from fractions import Fraction
import re


_RATIONAL_TEXT = re.compile(r'[+-]?(?:[0-9]+/[0-9]+|[0-9]+(?:\.[0-9]*)?|\.[0-9]+)')


def parse_rational(value):
    if isinstance(value, Fraction):
        return value
    if type(value) is int:
        return Fraction(value)
    if type(value) is str:
        text = value.strip()
        if _RATIONAL_TEXT.fullmatch(text):
            try:
                return Fraction(text)
            except ZeroDivisionError as error:
                raise ValueError('zero rational denominator') from error
    raise ValueError('expected a finite exact rational')


def rational_parts(value):
    fraction = parse_rational(value)
    return [fraction.numerator, fraction.denominator]


def rational_from_parts(parts):
    if (type(parts) is not list or len(parts) != 2
            or any(type(part) is not int for part in parts) or parts[1] <= 0):
        raise ValueError('invalid rational parts')
    fraction = Fraction(*parts)
    if rational_parts(fraction) != parts:
        raise ValueError('noncanonical rational parts')
    return fraction
