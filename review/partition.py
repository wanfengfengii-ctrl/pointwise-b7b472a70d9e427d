from dataclasses import dataclass, replace
from functools import cmp_to_key

from calibration.evidence import CertificateEvidence
from review.algebra import Thresholds, build_thresholds, polynomial_sign_at, real_roots
from review.endpoints import Endpoint, compare_endpoints, rational_between
from review.request import ReviewRequest


@dataclass(frozen=True, slots=True)
class Segment:
    left: Endpoint
    right: Endpoint
    left_closed: bool
    right_closed: bool
    category: str

    def contains(self, point: Endpoint):
        lower = compare_endpoints(point, self.left)
        upper = compare_endpoints(point, self.right)
        return ((lower > 0 or lower == 0 and self.left_closed)
                and (upper < 0 or upper == 0 and self.right_closed))


def classify_candidate(evidence: CertificateEvidence, thresholds: Thresholds, point: Endpoint):
    if point in evidence.unreadable_setpoints:
        return 'unreadable'
    minus = polynomial_sign_at(thresholds.minus, point)
    plus = polynomial_sign_at(thresholds.plus, point)
    return 'qualified' if minus * plus <= 0 else 'out_of_tolerance'


def _append(segments, current):
    if segments:
        previous = segments[-1]
        if (previous.category == current.category
                and compare_endpoints(previous.right, current.left) == 0
                and (previous.right_closed or current.left_closed)):
            segments[-1] = replace(previous, right=current.right, right_closed=current.right_closed)
            return
    segments.append(current)


def partition_window(evidence: CertificateEvidence, request: ReviewRequest):
    thresholds = build_thresholds(evidence, request.tolerance)
    candidates = {request.left, request.right, *evidence.unreadable_setpoints,
                  *real_roots(thresholds.minus), *real_roots(thresholds.plus)}
    boundaries = sorted((candidate for candidate in candidates
                         if compare_endpoints(request.left, candidate) <= 0
                         and compare_endpoints(candidate, request.right) <= 0),
                        key=cmp_to_key(compare_endpoints))
    segments = []
    for index, boundary in enumerate(boundaries):
        category = classify_candidate(evidence, thresholds, boundary)
        _append(segments, Segment(boundary, boundary, True, True, category))
        if index + 1 < len(boundaries):
            following = boundaries[index + 1]
            witness = rational_between(boundary, following)
            category = classify_candidate(evidence, thresholds, witness)
            _append(segments, Segment(boundary, following, False, False, category))
    return tuple(segments)
