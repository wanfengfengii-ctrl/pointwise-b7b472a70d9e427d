from report.publish import read
from station.rational import parse_rational


def point(db, report_id, x):
    x = parse_rational(x)
    snapshot = read(db, report_id)
    if not snapshot.request.left <= x <= snapshot.request.right:
        raise ValueError('setpoint is outside the report window')
    for segment in snapshot.segments:
        if segment.contains(x):
            return segment.category
    raise ValueError('stored report does not cover the requested setpoint')
