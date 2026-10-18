"""Baseline and optimized academic analytics for Lab_10."""

from __future__ import annotations

import csv
import threading
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

IntArray = NDArray[np.int32]


@dataclass(frozen=True)
class GradeStatistics:
    count: int
    average: float
    minimum: int
    maximum: int
    variance: float


@dataclass(frozen=True)
class AcademicSummary:
    overall: GradeStatistics
    student_averages: tuple[float, ...]
    subject_averages: tuple[float, ...]
    ranking: tuple[int, ...]
    above_threshold: tuple[int, ...]


def generate_dataset(
    size: int,
    *,
    students: int = 10_000,
    subjects: int = 20,
    seed: int = 7,
) -> tuple[IntArray, IntArray, IntArray]:
    """Generate a deterministic dataset, including the required one-million-row case."""
    if size < 1 or students < 1 or subjects < 1:
        raise ValueError("Dataset dimensions must be positive")
    rng = np.random.default_rng(seed)
    student_ids = rng.integers(0, students, size=size, dtype=np.int32)
    subject_ids = rng.integers(0, subjects, size=size, dtype=np.int32)
    grades = rng.integers(1, 13, size=size, dtype=np.int32)
    return student_ids, subject_ids, grades


def _stats_from_parts(
    count: int, total: int, square_total: int, minimum: int, maximum: int
) -> GradeStatistics:
    average = total / count
    variance = square_total / count - average * average
    return GradeStatistics(count, average, minimum, maximum, variance)


def baseline_grade_statistics(grades: Sequence[int] | IntArray) -> GradeStatistics:
    """CPU-bound baseline implemented with Python loops."""
    if len(grades) == 0:
        raise ValueError("At least one grade is required")
    total = 0
    square_total = 0
    minimum = 12
    maximum = 1
    for raw in grades:
        value = int(raw)
        total += value
        square_total += value * value
        minimum = min(minimum, value)
        maximum = max(maximum, value)
    return _stats_from_parts(len(grades), total, square_total, minimum, maximum)


def numpy_grade_statistics(grades: Sequence[int] | IntArray) -> GradeStatistics:
    """Vectorized grade statistics."""
    values = np.asarray(grades, dtype=np.int32)
    if values.size == 0:
        raise ValueError("At least one grade is required")
    return GradeStatistics(
        int(values.size),
        float(np.mean(values, dtype=np.float64)),
        int(np.min(values)),
        int(np.max(values)),
        float(np.var(values, dtype=np.float64)),
    )


def _partial_statistics(chunk: IntArray) -> tuple[int, int, int, int, int]:
    if chunk.size == 0:
        return 0, 0, 0, 13, 0
    values = chunk.astype(np.int64, copy=False)
    return (
        int(values.size),
        int(np.sum(values)),
        int(np.sum(values * values)),
        int(np.min(values)),
        int(np.max(values)),
    )


def _merge_parts(parts: Iterable[tuple[int, int, int, int, int]]) -> GradeStatistics:
    count = total = square_total = 0
    minimum, maximum = 13, 0
    for part_count, part_total, part_square, part_min, part_max in parts:
        count += part_count
        total += part_total
        square_total += part_square
        minimum = min(minimum, part_min)
        maximum = max(maximum, part_max)
    if count == 0:
        raise ValueError("At least one grade is required")
    return _stats_from_parts(count, total, square_total, minimum, maximum)


def threaded_grade_statistics(grades: IntArray, *, workers: int = 4) -> GradeStatistics:
    """ThreadPool comparison for the same CPU-bound calculation."""
    if workers < 1:
        raise ValueError("workers must be positive")
    chunks = [chunk for chunk in np.array_split(grades, workers) if chunk.size]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return _merge_parts(executor.map(_partial_statistics, chunks))


def process_grade_statistics(grades: IntArray, *, workers: int = 4) -> GradeStatistics:
    """ProcessPool implementation for CPU-bound calculation."""
    if workers < 1:
        raise ValueError("workers must be positive")
    chunks = [chunk for chunk in np.array_split(grades, workers) if chunk.size]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        return _merge_parts(executor.map(_partial_statistics, chunks))


def baseline_academic_summary(
    student_ids: IntArray,
    subject_ids: IntArray,
    grades: IntArray,
    *,
    students: int,
    subjects: int,
    threshold: float = 9.0,
) -> AcademicSummary:
    """Baseline per-student/per-subject aggregation using Python loops."""
    student_totals = [0] * students
    student_counts = [0] * students
    subject_totals = [0] * subjects
    subject_counts = [0] * subjects
    for student, subject, raw_grade in zip(student_ids, subject_ids, grades, strict=True):
        value = int(raw_grade)
        sid = int(student)
        subid = int(subject)
        student_totals[sid] += value
        student_counts[sid] += 1
        subject_totals[subid] += value
        subject_counts[subid] += 1
    student_averages = tuple(
        total / count if count else 0.0
        for total, count in zip(student_totals, student_counts, strict=True)
    )
    subject_averages = tuple(
        total / count if count else 0.0
        for total, count in zip(subject_totals, subject_counts, strict=True)
    )
    ranking = tuple(sorted(range(students), key=lambda item: (-student_averages[item], item)))
    above = tuple(item for item in ranking if student_averages[item] > threshold)
    return AcademicSummary(
        baseline_grade_statistics(grades), student_averages, subject_averages, ranking, above
    )


def numpy_academic_summary(
    student_ids: IntArray,
    subject_ids: IntArray,
    grades: IntArray,
    *,
    students: int,
    subjects: int,
    threshold: float = 9.0,
) -> AcademicSummary:
    """Vectorized averages, dispersion, ranking and threshold search."""
    values = grades.astype(np.float64, copy=False)
    student_counts = np.bincount(student_ids, minlength=students)
    student_totals = np.bincount(student_ids, weights=values, minlength=students)
    subject_counts = np.bincount(subject_ids, minlength=subjects)
    subject_totals = np.bincount(subject_ids, weights=values, minlength=subjects)
    student_averages = np.divide(
        student_totals, student_counts, out=np.zeros(students), where=student_counts != 0
    )
    subject_averages = np.divide(
        subject_totals, subject_counts, out=np.zeros(subjects), where=subject_counts != 0
    )
    ranking_array = np.lexsort((np.arange(students), -student_averages))
    above = ranking_array[student_averages[ranking_array] > threshold]
    return AcademicSummary(
        numpy_grade_statistics(grades),
        tuple(float(value) for value in student_averages),
        tuple(float(value) for value in subject_averages),
        tuple(int(value) for value in ranking_array),
        tuple(int(value) for value in above),
    )


def write_grade_csv(path: Path, rows: Iterable[tuple[int, int, int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["student_id", "subject_id", "grade"])
        writer.writerows(rows)


def read_grade_csv(path: Path) -> list[tuple[int, int, int]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        return [
            (int(row["student_id"]), int(row["subject_id"]), int(row["grade"])) for row in reader
        ]


def import_grade_files_sequential(paths: Sequence[Path]) -> list[tuple[int, int, int]]:
    return [row for path in paths for row in read_grade_csv(path)]


def import_grade_files_threaded(
    paths: Sequence[Path], *, workers: int = 4
) -> list[tuple[int, int, int]]:
    if workers < 1:
        raise ValueError("workers must be positive")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        return [row for rows in executor.map(read_grade_csv, paths) for row in rows]


class SynchronizedGradeBook:
    """Shared mutable state protected by Lock against race conditions."""

    def __init__(self) -> None:
        self._grades: list[int] = []
        self._lock = threading.Lock()

    def add(self, value: int) -> None:
        if not 1 <= value <= 12:
            raise ValueError("Grade must be between 1 and 12")
        with self._lock:
            self._grades.append(value)

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._grades)


class AcademicStatisticsCache:
    """Student statistics cache with explicit invalidation after grade updates."""

    def __init__(self, grades_by_student: dict[int, list[int]]) -> None:
        self._data = grades_by_student
        self._cache: dict[int, GradeStatistics] = {}
        self.hits = 0
        self.misses = 0

    def get(self, student_id: int) -> GradeStatistics:
        if student_id in self._cache:
            self.hits += 1
            return self._cache[student_id]
        self.misses += 1
        statistics = baseline_grade_statistics(self._data[student_id])
        self._cache[student_id] = statistics
        return statistics

    def update_grade(self, student_id: int, index: int, value: int) -> None:
        if not 1 <= value <= 12:
            raise ValueError("Grade must be between 1 and 12")
        self._data[student_id][index] = value
        self.invalidate(student_id)

    def invalidate(self, student_id: int) -> None:
        self._cache.pop(student_id, None)
