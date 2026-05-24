"""Lesson 05 — the flaky tool used to demo retries.

The tool's logic is split out from `workflows.py` so the failure counter is
unambiguously module-level state living in the **activity worker process**
(not the workflow process). Module state in workflow code would violate
determinism — but activities are normal Python and may keep state across
invocations of the same worker process.

The tool will fail with a transient `RuntimeError` for the first `FAIL_FIRST_N`
calls within this worker process, then succeed. That gives us a deterministic
"three attempts" demo where Temporal's retry policy is what makes the workflow
ultimately succeed.

Key Functions:
    flaky_lookup(): The pydantic-ai tool body. Tracks its own attempt count.
    reset_counter(): Used by tests to reset state between runs.

Limitations:
    - The counter lives in the worker process, so restarting the worker resets
      it. That's fine for a teaching demo; production code would use a real
      datastore.
"""

from __future__ import annotations

import logging

_log = logging.getLogger(__name__)

# How many calls fail before the tool finally succeeds. With the default
# RetryPolicy(maximum_attempts=5) below, the third attempt succeeds and the
# workflow returns. Bump this to 6+ to see the policy give up and surface
# the error as an activity failure.
FAIL_FIRST_N = 2

# Module-level counter — survives across activity invocations within the same
# worker process. Reset by restarting the worker (or `reset_counter()` in tests).
_attempts = 0


async def flaky_lookup(query: str) -> str:
    """Look up information about `query`.

    Pretend this is a flaky upstream service: the first couple of calls fail
    with a transient error, and then it starts succeeding. Temporal will
    retry per the configured `RetryPolicy` until one attempt completes.
    """
    global _attempts
    _attempts += 1
    _log.info("flaky_lookup attempt #%d for query=%r", _attempts, query)
    if _attempts <= FAIL_FIRST_N:
        raise RuntimeError(
            f"transient upstream error on attempt {_attempts} "
            f"(will succeed on attempt {FAIL_FIRST_N + 1})"
        )
    return f"Looked up {query!r} successfully on attempt {_attempts}."


def reset_counter() -> None:
    """Reset the attempt counter (used by tests, not by the lesson narrative)."""
    global _attempts
    _attempts = 0
