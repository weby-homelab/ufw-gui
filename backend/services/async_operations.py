"""Helpers for synchronous operations whose side effects outlive cancellation."""

import asyncio
import logging
from collections.abc import Callable
from functools import partial
from typing import Any, TypeVar

logger = logging.getLogger(__name__)
T = TypeVar("T")


async def run_to_thread_to_completion(
    function: Callable[..., T], *args: Any, **kwargs: Any
) -> T:
    """Wait for a worker thread to finish before propagating task cancellation.

    Cancelling ``asyncio.to_thread``'s awaiter does not stop its thread. Callers
    holding a mutation lock must retain that lock until the side effect ends.
    """
    loop = asyncio.get_running_loop()
    operation = loop.run_in_executor(None, partial(function, *args, **kwargs))
    try:
        return await asyncio.shield(operation)
    except asyncio.CancelledError:
        current = asyncio.current_task()
        while not operation.done():
            try:
                await asyncio.shield(operation)
            except asyncio.CancelledError:
                if current is not None:
                    current.uncancel()

        if not operation.cancelled():
            failure = operation.exception()
        else:
            failure = asyncio.CancelledError()
        if failure is not None:
            # Cancellation remains the caller-visible outcome. Do not expose
            # subprocess arguments, file paths, or exception text in logs.
            logger.error(
                "Background side effect ended during cancellation (%s).",
                type(failure).__name__,
            )
        raise
