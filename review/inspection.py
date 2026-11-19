from exchange.catalog import get_admission
from report.origins import origin_from_admission
from report.publish import publish_report
from review.partition import partition_window
from review.request import parse_review_request


def review(db, admission_id, left, right, tolerance):
    request = parse_review_request(admission_id, left, right, tolerance)
    admission = get_admission(db, request.admission_id)
    segments = partition_window(admission.envelope.evidence, request)
    return publish_report(db, request, origin_from_admission(admission), segments)
