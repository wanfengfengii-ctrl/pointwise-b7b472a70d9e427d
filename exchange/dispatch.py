from dataclasses import dataclass

from exchange.codec import ExchangeEnvelope, encode_exchange


@dataclass(frozen=True, slots=True)
class DispatchRecord:
    station: str
    issue_id: int
    body_sha256: str
    envelope: ExchangeEnvelope


def prepare_dispatch(evidence):
    envelope = encode_exchange(evidence)
    return DispatchRecord(evidence.station, evidence.issue_id, envelope.body_sha256, envelope)
