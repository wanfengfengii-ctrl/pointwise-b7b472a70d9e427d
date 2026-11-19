from fractions import Fraction

from calibration.affine import Affine, ChannelResponse
from station.protocol import valid_label


class InvalidCalibration(ValueError):
    pass


def require_valid_responses(responses):
    if not isinstance(responses, tuple) or len(responses) != 2:
        raise InvalidCalibration('expected two channel responses')
    for response in responses:
        if not isinstance(response, ChannelResponse) or not valid_label(response.channel):
            raise InvalidCalibration('invalid channel response')
        for affine in (response.numerator, response.denominator):
            if (not isinstance(affine, Affine)
                    or not isinstance(affine.intercept, Fraction)
                    or not isinstance(affine.slope, Fraction)):
                raise InvalidCalibration('expected exact affine coefficients')
        if response.denominator == Affine(Fraction(0), Fraction(0)):
            raise InvalidCalibration(f'channel {response.channel!r} has an identically zero denominator')
    if responses[0].channel == responses[1].channel:
        raise InvalidCalibration('repeated channel label')
    return responses
