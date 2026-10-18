import json

import numpy as np
import pytest

from grade_service.benchmark import (
    run_academic_experiment,
    run_cache_experiment,
    run_experiment,
    run_io_experiment,
    save_results,
    statistics_equal,
    summaries_equal,
    time_repeated,
)
from grade_service.performance import (
    baseline_academic_summary,
    baseline_grade_statistics,
    generate_dataset,
    numpy_academic_summary,
)


def test_time_repeated_and_validation():
    result, elapsed = time_repeated(lambda: baseline_grade_statistics([5, 10]), repeats=2)
    assert result.average == 7.5 and elapsed >= 0
    with pytest.raises(ValueError):
        time_repeated(lambda: result, repeats=0)


def test_comparison_helpers_detect_mismatch():
    first = baseline_grade_statistics([7, 9])
    assert statistics_equal(first, baseline_grade_statistics(np.array([7, 9], dtype=np.int32)))
    assert not statistics_equal(first, baseline_grade_statistics([7, 10]))
    ids, subjects, grades = generate_dataset(100, students=10, subjects=2)
    baseline = baseline_academic_summary(ids, subjects, grades, students=10, subjects=2)
    optimized = numpy_academic_summary(ids, subjects, grades, students=10, subjects=2)
    assert summaries_equal(baseline, optimized)


def test_small_experiments_and_result_files(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "grade_service.benchmark.process_grade_statistics",
        lambda grades, workers: baseline_grade_statistics(grades),
    )
    rows, profile, memory = run_experiment(sizes=(200,), worker_counts=(1, 2), repeats=1)
    academic = run_academic_experiment(sizes=(200,), repeats=1)
    io_rows = run_io_experiment(file_count=2, rows_per_file=10, repeats=1)
    cache = run_cache_experiment(repeats=2)
    assert len(rows) == 6
    assert len(academic) == 2
    assert "ncalls" in profile and memory["baseline_peak_bytes"] > 0
    assert len(io_rows) == 4 and cache["hits"] == 1 and cache["misses"] == 1
    save_results(tmp_path, rows, profile, memory, academic, io_rows, cache)
    assert len(json.loads((tmp_path / "benchmark.json").read_text())) == 6
    assert len(json.loads((tmp_path / "academic_benchmark.json").read_text())) == 2
    assert len(json.loads((tmp_path / "io_benchmark.json").read_text())) == 4
    assert json.loads((tmp_path / "cache_benchmark.json").read_text())["hits"] == 1
