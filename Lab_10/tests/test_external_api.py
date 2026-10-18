import asyncio

import httpx
import pytest

from grade_service.external_api import fetch_many_student_statistics, fetch_student_statistics


def test_parallel_fetch_uses_httpx_tasks_and_gather():
    async def handler(request: httpx.Request) -> httpx.Response:
        student_id = int(request.url.path.split("/")[-2])
        await asyncio.sleep(0.001)
        return httpx.Response(200, json={"student_id": student_id, "average": 10.0})

    result = asyncio.run(
        fetch_many_student_statistics(
            "https://grading.test",
            [1, 2, 3],
            concurrency=2,
            transport=httpx.MockTransport(handler),
        )
    )
    assert [item["student_id"] for item in result] == [1, 2, 3]


def test_retry_then_success():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls < 3 else 200, json={"student_id": 1})

    result = asyncio.run(
        fetch_many_student_statistics(
            "https://grading.test",
            [1],
            attempts=3,
            transport=httpx.MockTransport(handler),
        )
    )
    assert result == [{"student_id": 1}]
    assert calls == 3


def test_retry_exhausted():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "temporary"})

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(
            fetch_many_student_statistics(
                "https://grading.test",
                [1],
                attempts=2,
                transport=httpx.MockTransport(handler),
            )
        )


def test_timeout_is_retried_and_raised():
    async def scenario():
        async def handler(request: httpx.Request) -> httpx.Response:
            await asyncio.sleep(0.03)
            return httpx.Response(200, json={"ok": True})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(asyncio.TimeoutError):
                await fetch_student_statistics(
                    client,
                    "https://grading.test/",
                    1,
                    asyncio.Semaphore(1),
                    timeout=0.001,
                    attempts=2,
                    backoff=0,
                )

    asyncio.run(scenario())


def test_invalid_async_options():
    with pytest.raises(ValueError, match="concurrency"):
        asyncio.run(fetch_many_student_statistics("https://grading.test", [1], concurrency=0))

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200))
        ) as client:
            with pytest.raises(ValueError, match="attempts"):
                await fetch_student_statistics(
                    client, "https://grading.test", 1, asyncio.Semaphore(1), attempts=0
                )

    asyncio.run(scenario())
