from report.receipts import make_receipt
from report.store import ReportSnapshot, ReportStore


class MissingReport(KeyError):
    pass


def publish_report(db, request, origin, segments):
    if request.admission_id != origin.admission_id:
        raise ValueError('request and report origin disagree')
    segments = tuple(segments)
    store = ReportStore(db)
    with db:
        report_id = store.insert_report(request, origin, segments)
        receipt = make_receipt(report_id, origin)
        store.insert_receipt(receipt)
    return ReportSnapshot(report_id, request, origin, segments, receipt)


def read(db, report_id):
    snapshot = ReportStore(db).fetch_report(report_id)
    if snapshot is None:
        raise MissingReport(report_id)
    return snapshot
