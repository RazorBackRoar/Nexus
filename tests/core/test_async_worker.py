"""Regression tests for AsyncWorker error handling."""

from nexus.gui.widgets import AsyncWorker


async def _raise_value_error():
    raise ValueError("boom")


def test_async_worker_exposes_result_signal():
    worker = AsyncWorker(_raise_value_error)
    assert hasattr(worker, "result_ready")


def test_async_worker_catches_unexpected_exception():
    worker = AsyncWorker(_raise_value_error)
    worker.run()
