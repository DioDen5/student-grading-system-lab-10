"""Benchmark orchestration with repeated timings and speedup."""

from __future__ import annotations

import json
import statistics
import tempfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from time import perf_counter
from typing import TypeVar

import numpy as np

from .performance import (
    AcademicStatisticsCache,
    AcademicSummary,
    GradeStatistics,
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
from .profiling import cprofile_text, memory_profile

T = TypeVar("T")


@dataclass(frozen=True)
class BenchmarkRow:
    dataset_size: int
    implementation: str
    workers: int
    median_seconds: float
    speedup: float
    peak_bytes: int


@dataclass(frozen=True)
class AcademicBenchmarkRow:
    dataset_size: int
    implementation: str
    median_seconds: float
    speedup: float


@dataclass(frozen=True)
class IoBenchmarkRow:
    implementation: str
    workers: int
    rows: int
    median_seconds: float
    speedup: float


def time_repeated(function: Callable[[], T], *, repeats: int = 3) -> tuple[T, float]:
    if repeats < 1:
        raise ValueError("repeats must be positive")
    timings: list[float] = []
    result: T | None = None
    for _ in range(repeats):
        started = perf_counter()
        result = function()
        timings.append(perf_counter() - started)
    assert result is not None
    return result, statistics.median(timings)


def statistics_equal(left: GradeStatistics, right: GradeStatistics) -> bool:
    return bool(
        left.count == right.count
        and left.minimum == right.minimum
        and left.maximum == right.maximum
        and np.isclose(left.average, right.average, rtol=1e-12, atol=1e-12)
        and np.isclose(left.variance, right.variance, rtol=1e-12, atol=1e-12)
    )


def summaries_equal(left: AcademicSummary, right: AcademicSummary) -> bool:
    return (
        statistics_equal(left.overall, right.overall)
        and np.allclose(left.student_averages, right.student_averages)
        and np.allclose(left.subject_averages, right.subject_averages)
        and left.ranking == right.ranking
        and left.above_threshold == right.above_threshold
    )


def run_academic_experiment(
    *, sizes: tuple[int, ...] = (10_000, 100_000, 1_000_000), repeats: int = 3
) -> list[AcademicBenchmarkRow]:
    rows: list[AcademicBenchmarkRow] = []
    for size in sizes:
        students = min(10_000, max(100, size // 10))
        student_ids, subject_ids, grades = generate_dataset(size, students=students)
        baseline, baseline_time = time_repeated(
            lambda: baseline_academic_summary(
                student_ids, subject_ids, grades, students=students, subjects=20
            ),
            repeats=repeats,
        )
        optimized, numpy_time = time_repeated(
            lambda: numpy_academic_summary(
                student_ids, subject_ids, grades, students=students, subjects=20
            ),
            repeats=repeats,
        )
        assert summaries_equal(baseline, optimized)
        rows.extend(
            [
                AcademicBenchmarkRow(size, "python_loops", baseline_time, 1.0),
                AcademicBenchmarkRow(size, "numpy", numpy_time, baseline_time / numpy_time),
            ]
        )
    return rows


def run_io_experiment(
    *, file_count: int = 8, rows_per_file: int = 5_000, repeats: int = 3
) -> list[IoBenchmarkRow]:
    with tempfile.TemporaryDirectory() as raw_directory:
        directory = Path(raw_directory)
        paths: list[Path] = []
        for file_number in range(file_count):
            student_ids, subject_ids, grades = generate_dataset(rows_per_file, seed=7 + file_number)
            path = directory / f"grades_{file_number}.csv"
            write_grade_csv(path, zip(student_ids, subject_ids, grades, strict=True))
            paths.append(path)
        expected, baseline_time = time_repeated(
            lambda: import_grade_files_sequential(paths), repeats=repeats
        )
        rows = [IoBenchmarkRow("sequential", 1, len(expected), baseline_time, 1.0)]
        for workers in (1, 2, 4):
            actual, elapsed = time_repeated(
                partial(import_grade_files_threaded, paths, workers=workers),
                repeats=repeats,
            )
            assert actual == expected
            rows.append(
                IoBenchmarkRow(
                    "thread_pool", workers, len(actual), elapsed, baseline_time / elapsed
                )
            )
        return rows


def run_cache_experiment(*, repeats: int = 20_000) -> dict[str, float | int]:
    grades = list(range(1, 13)) * 100
    started = perf_counter()
    for _ in range(repeats):
        baseline_grade_statistics(grades)
    uncached = perf_counter() - started
    cache = AcademicStatisticsCache({7: grades})
    started = perf_counter()
    for _ in range(repeats):
        cache.get(7)
    cached = perf_counter() - started
    return {
        "repeated_queries": repeats,
        "uncached_seconds": uncached,
        "cached_seconds": cached,
        "speedup": uncached / cached,
        "hits": cache.hits,
        "misses": cache.misses,
    }


def run_experiment(
    *,
    sizes: tuple[int, ...] = (10_000, 100_000, 1_000_000),
    worker_counts: tuple[int, ...] = (1, 2, 4),
    repeats: int = 3,
) -> tuple[list[BenchmarkRow], str, dict[str, int]]:
    rows: list[BenchmarkRow] = []
    profile_text = ""
    memory_results: dict[str, int] = {}
    for size in sizes:
        _, _, grades = generate_dataset(size)
        baseline_result, baseline_time = time_repeated(
            lambda: baseline_grade_statistics(grades), repeats=repeats
        )
        _, baseline_memory = memory_profile(baseline_grade_statistics, grades)
        rows.append(
            BenchmarkRow(size, "python_loops", 1, baseline_time, 1.0, baseline_memory.peak_bytes)
        )

        numpy_result, numpy_time = time_repeated(
            lambda: numpy_grade_statistics(grades), repeats=repeats
        )
        _, numpy_memory = memory_profile(numpy_grade_statistics, grades)
        assert statistics_equal(baseline_result, numpy_result)
        rows.append(
            BenchmarkRow(
                size, "numpy", 1, numpy_time, baseline_time / numpy_time, numpy_memory.peak_bytes
            )
        )

        for workers in worker_counts:
            thread_result, thread_time = time_repeated(
                partial(threaded_grade_statistics, grades, workers=workers),
                repeats=repeats,
            )
            assert statistics_equal(baseline_result, thread_result)
            rows.append(
                BenchmarkRow(
                    size, "thread_pool", workers, thread_time, baseline_time / thread_time, 0
                )
            )

            process_result, process_time = time_repeated(
                partial(process_grade_statistics, grades, workers=workers),
                repeats=repeats,
            )
            assert statistics_equal(baseline_result, process_result)
            rows.append(
                BenchmarkRow(
                    size, "process_pool", workers, process_time, baseline_time / process_time, 0
                )
            )

        if size == max(sizes):
            _, profile_text = cprofile_text(baseline_grade_statistics, grades, limit=12)
            memory_results = {
                "baseline_peak_bytes": baseline_memory.peak_bytes,
                "numpy_peak_bytes": numpy_memory.peak_bytes,
            }
    return rows, profile_text, memory_results


def save_results(
    directory: Path,
    rows: list[BenchmarkRow],
    profile: str,
    memory: dict[str, int],
    academic_rows: list[AcademicBenchmarkRow] | None = None,
    io_rows: list[IoBenchmarkRow] | None = None,
    cache_results: dict[str, float | int] | None = None,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "benchmark.json").write_text(
        json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (directory / "cprofile.txt").write_text(profile, encoding="utf-8")
    (directory / "memory.json").write_text(json.dumps(memory, indent=2), encoding="utf-8")
    if academic_rows is not None:
        (directory / "academic_benchmark.json").write_text(
            json.dumps([asdict(row) for row in academic_rows], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if io_rows is not None:
        (directory / "io_benchmark.json").write_text(
            json.dumps([asdict(row) for row in io_rows], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    if cache_results is not None:
        (directory / "cache_benchmark.json").write_text(
            json.dumps(cache_results, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def main() -> None:
    rows, profile, memory = run_experiment()
    academic_rows = run_academic_experiment()
    io_rows = run_io_experiment()
    cache_results = run_cache_experiment()
    output = Path("benchmarks/results")
    save_results(output, rows, profile, memory, academic_rows, io_rows, cache_results)
    print(f"Saved {len(rows)} benchmark rows to {output}")
    for benchmark_row in rows:
        print(
            f"{benchmark_row.dataset_size:>9} {benchmark_row.implementation:<13} "
            f"workers={benchmark_row.workers} time={benchmark_row.median_seconds:.6f}s "
            f"speedup={benchmark_row.speedup:.2f}x"
        )
    for academic_row in academic_rows:
        print(
            f"academic {academic_row.dataset_size:>9} {academic_row.implementation:<12} "
            f"time={academic_row.median_seconds:.6f}s speedup={academic_row.speedup:.2f}x"
        )
    for io_row in io_rows:
        print(
            f"I/O {io_row.implementation:<12} workers={io_row.workers} rows={io_row.rows} "
            f"time={io_row.median_seconds:.6f}s speedup={io_row.speedup:.2f}x"
        )
    print(
        f"cache queries={cache_results['repeated_queries']} "
        f"speedup={cache_results['speedup']:.2f}x hits={cache_results['hits']}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
