"""Lesson 02 — why a Temporal workflow is a *class*.

Lesson 01's `GreetWorkflow` was a class with a single `@workflow.run`
method, and the class-ness looked like ceremony. It isn't. A workflow is
a class because one running execution needs to share mutable state across
three kinds of method:

    - `@workflow.run`     — the body, runs once per execution
    - `@workflow.signal`  — external *writes* into the running workflow
    - `@workflow.query`   — external *reads* of the running workflow

The bridge between them is **instance state** — plain attributes set in
`__init__` and mutated by signal handlers. `workflow.wait_condition`
suspends the run until that state satisfies a predicate.

`TallyWorkflow` is the whole idea with nothing else in the way: no
pydantic-ai, no activity, no I/O. You push numbers in with `add`, read
the running total with the `total` query, and the run returns once the
total crosses a target (or someone calls `close`). This is the exact
shape Lesson 07's human-in-the-loop reuses — there, a `wait_condition`
waits on an `approve` signal instead of a number.
"""

from __future__ import annotations

from temporalio import workflow


@workflow.defn
class TallyWorkflow:
    """A signal-driven counter. Pure orchestration state — no side effects."""

    def __init__(self) -> None:
        # Instance state is the bridge between signals (writers), the
        # `total` query (reader), and the run body (which waits on it).
        # `__init__` runs at the start of every execution AND on every
        # replay, so it must be deterministic — just set initial values.
        self._total: int = 0
        self._closed: bool = False

    @workflow.signal
    def add(self, n: int) -> None:
        """External write: add `n` to the tally. Signal handlers MUST be sync."""
        self._total += n

    @workflow.signal
    def close(self) -> None:
        """External write: stop early, returning whatever total we have."""
        self._closed = True

    @workflow.query
    def total(self) -> int:
        """External read: the running total. Queries MUST NOT mutate state."""
        return self._total

    @workflow.run
    async def run(self, target: int) -> int:
        # The durable pause. Costs zero CPU while waiting; Temporal re-checks
        # the predicate only when a signal changes state. It wakes when the
        # tally crosses `target` or someone calls `close`.
        await workflow.wait_condition(lambda: self._total >= target or self._closed)
        return self._total
