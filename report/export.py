from dataclasses import asdict
import json

from report.publish import read
from report.store import encode_request, encode_segments


def export_report(db, report_id):
    snapshot = read(db, report_id)
    return json.dumps({'report_id': snapshot.report_id, 'request': encode_request(snapshot.request),
                       'segments': encode_segments(snapshot.segments), 'origin': asdict(snapshot.origin),
                       'receipt': asdict(snapshot.receipt)},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))
