from dataclasses import dataclass
from hashlib import sha256
import json

from calibration.affine import Affine, ChannelResponse
from calibration.evidence import CertificateEvidence, validate_evidence
from station.rational import rational_from_parts, rational_parts
from station.store import is_rowid


class InvalidExchange(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExchangeEnvelope:
    evidence: CertificateEvidence
    body_sha256: str
    wire: str


def _canonical(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(',', ':'))


def _digest(body):
    return sha256(_canonical(body).encode('ascii')).hexdigest()


def _encode_affine(affine):
    return [rational_parts(affine.intercept), rational_parts(affine.slope)]


def _decode_affine(value):
    if type(value) is not list or len(value) != 2:
        raise InvalidExchange('invalid affine evidence')
    return Affine(*(rational_from_parts(parts) for parts in value))


def _require_fields(value, fields):
    if type(value) is not dict or value.keys() != fields:
        raise InvalidExchange('unexpected exchange fields')


def _unique_members(pairs):
    value = {}
    for key, member in pairs:
        if key in value:
            raise InvalidExchange(f'duplicate exchange field {key!r}')
        value[key] = member
    return value


def encode_exchange(evidence):
    validate_evidence(evidence)
    body = {
        'station': evidence.station, 'issue_id': evidence.issue_id,
        'freeze_id': evidence.freeze_id, 'revision_id': evidence.revision_id,
        'responses': [dict(channel=r.channel, numerator=_encode_affine(r.numerator),
                           denominator=_encode_affine(r.denominator)) for r in evidence.responses],
    }
    digest = _digest(body)
    wire = _canonical({'version': 1, 'station': evidence.station, 'issue_id': evidence.issue_id,
                       'body_sha256': digest, 'body': body})
    return ExchangeEnvelope(evidence, digest, wire)


def _decode_response(value):
    _require_fields(value, {'channel', 'numerator', 'denominator'})
    return ChannelResponse(value['channel'], _decode_affine(value['numerator']),
                           _decode_affine(value['denominator']))


def decode_exchange(wire):
    if type(wire) is not str:
        raise InvalidExchange('expected a JSON exchange string')
    try:
        envelope = json.loads(wire, object_pairs_hook=_unique_members)
        _require_fields(envelope, {'version', 'station', 'issue_id', 'body_sha256', 'body'})
        if type(envelope['version']) is not int or envelope['version'] != 1:
            raise InvalidExchange('unknown exchange version')
        body = envelope['body']
        _require_fields(body, {'station', 'issue_id', 'freeze_id', 'revision_id', 'responses'})
        if (envelope['station'] != body['station'] or not is_rowid(envelope['issue_id'])
                or envelope['issue_id'] != body['issue_id']):
            raise InvalidExchange('inner and outer identities disagree')
        if type(body['responses']) is not list or len(body['responses']) != 2:
            raise InvalidExchange('expected two response records')
        responses = tuple(map(_decode_response, body['responses']))
        evidence = validate_evidence(CertificateEvidence(
            body['station'], body['issue_id'], body['freeze_id'], body['revision_id'], responses,
        ))
        digest = _digest(body)
        if envelope['body_sha256'] != digest:
            raise InvalidExchange('exchange body digest disagrees')
    except InvalidExchange:
        raise
    except (TypeError, ValueError, RecursionError) as error:
        raise InvalidExchange('invalid exchange body') from error
    return ExchangeEnvelope(evidence, digest, wire)
