from contextlib import closing
import json

from calibration.issue import initialize_issues, issue
from demo import record_marks, require_equal
from exchange.admission import admit
from report.export import export_report
from report.store import open_center_store
from review.inspection import review
from station.freeze import freeze
from station.protocol import register_protocol
from station.store import open_station_store
from tests.fixtures import CONSTANT, HOLE, ISOLATED, STATION


MARKS = {
    "hole": HOLE,
    "zero_tie": ISOLATED,
    "positive_tie": (*ISOLATED[:2], ("乙", 0, -2, 0), ("乙", 1, -2, 1)),
    "boundary_tie": (("甲", 0, 1, 1), ("甲", 1, 2, 2),
                     ("乙", 0, -1, 0), ("乙", 1, 0, 1)),
    "constant_with_hole": (*HOLE[:2], ("乙", 0, -1, -1), ("乙", 1, 0, 0)),
}


def open_sample_station(path):
    source = open_station_store(path)
    try:
        initialize_issues(source)
        register_protocol(source, STATION, ("甲", "乙"))
    except BaseException:
        source.close()
        raise
    return source


def admit_marks(source, center, marks, base_revision=None):
    revision = record_marks(source, STATION, marks, base_revision)
    issued = issue(source, freeze(source, STATION, revision).freeze_id)
    return admit(center, STATION, issued.wire), issued


def main():
    cases = (
        ("hole", 0, 2, 0, 0, 1),
        ("hole", 1, 1, 0, 0, 1),
        ("corrected", 1, 1, 0, 1, 0),
        ("zero_tie", -2, 2, 0, 2, 1),
        ("positive_tie", -2, 2, "14/5", 0, 1),
        ("positive_tie", -2, 2, "17/6", 2, 1),
        ("boundary_tie", -1, 1, 1, 1, 2),
        ("constant_with_hole", 0, 2, 0, 2, 1),
    )
    with closing(open_center_store(":memory:")) as center:
        with closing(open_sample_station(":memory:")) as source:
            admitted = {name: admit_marks(source, center, marks) for name, marks in MARKS.items()}
            _, original = admitted["hole"]
            admitted["corrected"] = admit_marks(source, center, CONSTANT[:2],
                                                 original.evidence.revision_id)
        for name, left, right, tolerance, qualified_count, unreadable_count in cases:
            admission_id, issued = admitted[name]
            result = review(center, admission_id, left, right, tolerance)
            require_equal(result.origin.admission_id, admission_id, name)
            require_equal(result.origin.revision_id, issued.evidence.revision_id, name)
            require_equal(result.receipt.issue_id, issued.issue_id, name)
            saved = json.loads(export_report(center, result.report_id))
            selected = [item for item in saved["segments"] if item["category"] == "qualified"]
            holes = [item["left"] for item in saved["segments"] if item["category"] == "unreadable"]
            require_equal((len(selected), len(holes)), (qualified_count, unreadable_count), name)
            print(json.dumps({"sample": name, "window": [left, right], "tolerance": tolerance,
                              "qualified": selected, "unreadable": holes, "receipt": saved["receipt"]},
                             ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
