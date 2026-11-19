from dataclasses import dataclass

from calibration.affine import ChannelResponse
from calibration.checks import InvalidCalibration, require_valid_responses
from station.freeze import FrozenRoster
from station.protocol import valid_label
from station.store import is_rowid


@dataclass(frozen=True, slots=True)
class CertificateEvidence:
    station: str
    issue_id: int
    freeze_id: int
    revision_id: int
    responses: tuple[ChannelResponse, ChannelResponse]

    @property
    def unreadable_setpoints(self):
        zeros = (response.denominator.zero() for response in self.responses)
        return tuple(sorted({point for point in zeros if point is not None}))


def build_evidence(issue_id, roster: FrozenRoster, responses):
    evidence = CertificateEvidence(roster.station, issue_id, roster.freeze_id,
                                   roster.revision_id, responses)
    return validate_evidence(evidence)


def validate_evidence(evidence):
    if not isinstance(evidence, CertificateEvidence) or not valid_label(evidence.station):
        raise InvalidCalibration('invalid calibration identity')
    if not all(map(is_rowid, (evidence.issue_id, evidence.freeze_id, evidence.revision_id))):
        raise InvalidCalibration('invalid calibration origin')
    require_valid_responses(evidence.responses)
    return evidence
