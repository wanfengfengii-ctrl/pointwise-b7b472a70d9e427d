from contextlib import closing
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from calibration.issue import initialize_issues, issue
from exchange.admission import admit
from report.export import export_report
from report.publish import read
from report.store import open_center_store
from review.inspection import review
from review.setpoint import point
from station.freeze import freeze
from station.protocol import register_protocol
from station.revisions import load
from station.store import open_station_store


def record_marks(db, station, marks, revision=None):
    for mark in marks:
        revision = load(db, station, *mark, base_revision=revision)
    return revision


def require_equal(actual, expected, context):
    if actual != expected:
        raise RuntimeError(f'{context}: expected {expected!r}, got {actual!r}')


def report_shape(exported):
    return [[segment['category'], segment['left'][1:], segment['right'][1:],
             segment['left_closed'], segment['right_closed']]
            for segment in exported['segments']]


def main():
    sample = json.loads(Path(__file__).with_name('sample.json').read_text(encoding='utf-8'))
    station = sample['station']
    left, right = sample['window']
    x = sample['setpoint']
    expected = [
        ['out_of_tolerance', [0, 1], [1, 2], True, False],
        ['qualified', [1, 2], [1, 1], True, False],
        ['unreadable', [1, 1], [1, 1], True, True],
        ['qualified', [1, 1], [3, 2], False, True],
        ['out_of_tolerance', [3, 2], [2, 1], False, True],
    ]
    with TemporaryDirectory(prefix='ratio-shift-') as directory:
        station_path = Path(directory) / 'station.sqlite3'
        center_path = Path(directory) / 'center.sqlite3'
        with closing(open_station_store(station_path)) as source, closing(open_center_store(center_path)) as center:
            initialize_issues(source)
            register_protocol(source, station, sample['channels'])
            original_revision = record_marks(source, station, sample['readings'])
            original = issue(source, freeze(source, station, original_revision).freeze_id)
            corrected_revision = record_marks(source, station, sample['corrections'], original_revision)
            corrected = issue(source, freeze(source, station, corrected_revision).freeze_id)
            first_id = admit(center, station, original.wire)
            second_id = admit(center, station, corrected.wire)
        with closing(open_center_store(center_path)) as center:
            first = review(center, first_id, left, right, sample['tolerance'])
            second = review(center, second_id, left, right, sample['tolerance'])
        with closing(open_center_store(center_path)) as center:
            require_equal(read(center, first.report_id), first, 'original report after reopening')
            require_equal(read(center, second.report_id), second, 'corrected report after reopening')
            saved = json.loads(export_report(center, first.report_id))
            saved_corrected = json.loads(export_report(center, second.report_id))
            result = report_shape(saved)
            require_equal(result, expected, 'original report shape')
            require_equal(report_shape(saved_corrected), [expected[0],
                          ['qualified', [1, 2], [3, 2], True, True], expected[-1]], 'corrected shape')
            actual_point = point(center, first.report_id, x)
            corrected_point = point(center, second.report_id, x)
            require_equal(actual_point, 'unreadable', 'original setpoint')
            require_equal(corrected_point, 'qualified', 'corrected setpoint')
            require_equal(saved['receipt']['issue_id'], original.issue_id, 'original receipt')
            require_equal(saved_corrected['receipt']['issue_id'], corrected.issue_id, 'corrected receipt')
            observation = {
                'case_id': 'V5',
                'input': {key: sample[key] for key in ('station', 'readings', 'window', 'tolerance', 'setpoint')},
                'expected': expected,
                'actual': result,
                'downstream_expected': {'point': 'unreadable', 'issue_id': original.issue_id},
                'downstream_actual': {'point': actual_point, 'issue_id': saved['receipt']['issue_id']},
                'code_paths': ['calibration/issue.py', 'exchange/admission.py', 'review/partition.py',
                               'review/setpoint.py', 'report/export.py'],
                'oracle': 'x≠1 时差为 1−x，故达标窗为 [1/2,3/2]。原分母 x−1 在 1 为零，须挖掉该点。回执与实际发行号核对。',
            }
            print('POINTWISE_SCENARIO ' + json.dumps(observation, ensure_ascii=False, sort_keys=True))
            print(json.dumps({'original_report': saved, 'corrected_report': saved_corrected,
                              'setpoint_classifications': [actual_point, corrected_point]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
