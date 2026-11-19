from dataclasses import dataclass

from exchange.catalog import AdmissionRecord


@dataclass(frozen=True, slots=True)
class ReportOrigin:
    station: str
    admission_id: str
    issue_id: int
    freeze_id: int
    revision_id: int


def origin_from_admission(admission: AdmissionRecord):
    evidence = admission.envelope.evidence
    return ReportOrigin(evidence.station, admission.admission_id, evidence.issue_id,
                        evidence.freeze_id, evidence.revision_id)
