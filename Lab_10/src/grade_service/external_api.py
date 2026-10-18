"""Concurrent HTTP aggregation with Task, gather, Semaphore, timeout and retry."""

import asyncio
from collections.abc import Iterable

import httpx


async def fetch_student_statistics(
    client: httpx.AsyncClient,
    base_url: str,
    student_id: int,
    semaphore: asyncio.Semaphore,
    *,
    timeout: float = 3.0,
    attempts: int = 3,
    backoff: float = 0.05,
) -> dict:
    """Fetch one student's statistics with bounded concurrency and retry."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    async with semaphore:
        for attempt in range(1, attempts + 1):
            try:
                response = await asyncio.wait_for(
                    client.get(f"{base_url.rstrip('/')}/students/{student_id}/average"),
                    timeout=timeout,
                )
                response.raise_for_status()
                return response.json()
            except (TimeoutError, httpx.RequestError, httpx.HTTPStatusError):
                if attempt == attempts:
                    raise
                await asyncio.sleep(backoff * attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


async def fetch_many_student_statistics(
    base_url: str,
    student_ids: Iterable[int],
    *,
    concurrency: int = 3,
    timeout: float = 3.0,
    attempts: int = 3,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict]:
    """Create tasks and gather student statistics through one reused AsyncClient."""
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(transport=transport) as client:
        tasks = [
            asyncio.create_task(
                fetch_student_statistics(
                    client,
                    base_url,
                    student_id,
                    semaphore,
                    timeout=timeout,
                    attempts=attempts,
                )
            )
            for student_id in student_ids
        ]
        return await asyncio.gather(*tasks)
