from dataclasses import dataclass

from report.origins import ReportOrigin


@dataclass(frozen=True, slots=True)
class Receipt:
    report_id: int
    issue_id: int


def make_receipt(report_id, origin: ReportOrigin):
    return Receipt(report_id, origin.issue_id)
