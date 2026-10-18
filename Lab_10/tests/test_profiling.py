from grade_service.performance import baseline_grade_statistics
from grade_service.profiling import cprofile_text, memory_profile


def test_cprofile_and_tracemalloc_helpers():
    result, profile = cprofile_text(baseline_grade_statistics, [5, 7, 9], limit=5)
    assert result.average == 7
    assert "ncalls" in profile and "tottime" in profile and "cumtime" in profile
    memory_result, memory = memory_profile(baseline_grade_statistics, [5, 7, 9])
    assert memory_result == result
    assert memory.peak_bytes >= memory.current_bytes >= 0
