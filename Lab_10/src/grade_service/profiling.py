"""Reusable cProfile and tracemalloc measurement helpers."""

from __future__ import annotations

import cProfile
import io
import pstats
import tracemalloc
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

R = TypeVar("R")


@dataclass(frozen=True)
class MemoryProfile:
    current_bytes: int
    peak_bytes: int


def cprofile_text(
    function: Callable[..., R], *args: Any, limit: int = 15, **kwargs: Any
) -> tuple[R, str]:
    profiler = cProfile.Profile()
    profiler.enable()
    result = function(*args, **kwargs)
    profiler.disable()
    stream = io.StringIO()
    pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(limit)
    return result, stream.getvalue()


def memory_profile(
    function: Callable[..., R], *args: Any, **kwargs: Any
) -> tuple[R, MemoryProfile]:
    tracemalloc.start()
    try:
        result = function(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        return result, MemoryProfile(current, peak)
    finally:
        tracemalloc.stop()
