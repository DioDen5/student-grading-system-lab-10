from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pytest

from grade_service.benchmark import statistics_equal
from grade_service.performance import (
    AcademicStatisticsCache,
    SynchronizedGradeBook,
    baseline_academic_summary,
    baseline_grade_statistics,
    generate_dataset,
    import_grade_files_sequential,
    import_grade_files_threaded,
    numpy_academic_summary,
    numpy_grade_statistics,
    process_grade_statistics,
    threaded_grade_statistics,
    write_grade_csv,
)


def test_dataset_is_deterministic_and_valid():
    left = generate_dataset(50, students=7, subjects=3)
    right = generate_dataset(50, students=7, subjects=3)
    assert all(np.array_equal(a, b) for a, b in zip(left, right, strict=True))
    assert left[2].min() >= 1 and left[2].max() <= 12


@pytest.mark.parametrize(
    "kwargs", [{"size": 0}, {"size": 1, "students": 0}, {"size": 1, "subjects": 0}]
)
def test_dataset_rejects_invalid_dimensions(kwargs):
    with pytest.raises(ValueError):
        generate_dataset(**kwargs)


def test_all_statistics_implementations_are_equal():
    _, _, grades = generate_dataset(2_000)
    expected = baseline_grade_statistics(grades)
    assert statistics_equal(numpy_grade_statistics(grades), expected)
    assert statistics_equal(threaded_grade_statistics(grades, workers=2), expected)
    try:
        process_result = process_grade_statistics(grades, workers=2)
    except PermissionError:
        pytest.skip("ProcessPool semaphores are blocked by the test sandbox")
    assert statistics_equal(process_result, expected)


@pytest.mark.parametrize("function", [baseline_grade_statistics, numpy_grade_statistics])
def test_statistics_reject_empty(function):
    with pytest.raises(ValueError):
        function(np.array([], dtype=np.int32))


@pytest.mark.parametrize("function", [threaded_grade_statistics, process_grade_statistics])
def test_pools_validate_worker_count(function):
    with pytest.raises(ValueError):
        function(np.array([10], dtype=np.int32), workers=0)


def test_academic_numpy_matches_baseline():
    student_ids, subject_ids, grades = generate_dataset(2_000, students=80, subjects=5)
    expected = baseline_academic_summary(student_ids, subject_ids, grades, students=80, subjects=5)
    actual = numpy_academic_summary(student_ids, subject_ids, grades, students=80, subjects=5)
    assert statistics_equal(actual.overall, expected.overall)
    assert actual.student_averages == pytest.approx(expected.student_averages)
    assert actual.subject_averages == pytest.approx(expected.subject_averages)
    assert actual.ranking == expected.ranking
    assert actual.above_threshold == expected.above_threshold


def test_csv_import_is_equal_for_sequential_and_threads(tmp_path):
    paths = []
    expected = []
    for index in range(4):
        rows = [(index, subject, 8 + subject) for subject in range(3)]
        path = tmp_path / f"grades_{index}.csv"
        write_grade_csv(path, rows)
        paths.append(path)
        expected.extend(rows)
    assert import_grade_files_sequential(paths) == expected
    assert import_grade_files_threaded(paths, workers=3) == expected
    with pytest.raises(ValueError):
        import_grade_files_threaded(paths, workers=0)


def test_gradebook_uses_lock_for_shared_state():
    gradebook = SynchronizedGradeBook()
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(gradebook.add, [7] * 500))
    assert gradebook.count == 500
    with pytest.raises(ValueError):
        gradebook.add(13)


def test_cache_hits_misses_and_invalidation():
    cache = AcademicStatisticsCache({7: [7, 9, 11]})
    first = cache.get(7)
    assert cache.get(7) is first
    assert (cache.hits, cache.misses) == (1, 1)
    cache.update_grade(7, 0, 12)
    assert cache.get(7).average != first.average
    assert cache.misses == 2
    cache.invalidate(7)
    with pytest.raises(ValueError):
        cache.update_grade(7, 0, 0)
