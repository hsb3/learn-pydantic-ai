"""Lesson 08 — agent picks a URL, workflow runs a long activity to fetch it.

The split:

- The **agent** (a `TemporalAgent` wrapping a regular pydantic-ai `Agent`)
  picks one URL from a list. That's fast, deterministic-shaped work that
  benefits from being wrapped in activities for retry semantics.
- The **`long_scrape` activity** does the slow side-effecting work. It
  heartbeats every second so Temporal doesn't decide the worker died and
  reschedule the whole job.

The workflow body orchestrates both: agent first, then activity. Each is
durable on its own — if `long_scrape` fails halfway, only it retries; the
agent's pick is already memoized in workflow history.

Activity timeouts to know:

- `start_to_close_timeout` — the budget for a single attempt. After this
  elapses, Temporal marks the attempt failed and (per `retry_policy`)
  schedules a new attempt.
- `heartbeat_timeout` — the max gap between heartbeats before Temporal
  decides the worker died. MUST be less than `start_to_close_timeout`.
- `schedule_to_close_timeout` — the budget across ALL attempts. We don't
  set it here; the default is no cap.

For workflows that need to live longer than Temporal's per-workflow
history limit (~50k events), use `workflow.continue_as_new(...)` to start
a fresh history with the current state as input. That's out of scope for
this lesson — see https://docs.temporal.io/workflows#continue-as-new.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow

from learn_pydantic_ai import FLASH
from scraper import long_scrape


_base = Agent(
    model=FLASH,
    name="url_picker",
    instructions=(
        "You pick the single best URL for a research topic from a small "
        "candidate list. Reply with ONLY the URL — no explanation, no quotes."
    ),
)
url_agent = TemporalAgent(_base)


_CANDIDATES: list[str] = [
    "https://docs.temporal.io/workflows",
    "https://ai.pydantic.dev/durable_execution/temporal/",
    "https://docs.pydantic.dev/latest/concepts/models/",
]


@workflow.defn
class LongScrapeWorkflow(PydanticAIWorkflow):
    """One agent pick + one long-running activity, with heartbeats."""

    __pydantic_ai_agents__ = [url_agent]

    @workflow.run
    async def run(self, topic: str) -> str:
        workflow.logger.info("LongScrapeWorkflow topic=%s", topic)

        # 1. Agent decides which URL to scrape.
        prompt = f"Topic: {topic}\n\nCandidates:\n" + "\n".join(
            f"- {u}" for u in _CANDIDATES
        )
        pick = await url_agent.run(prompt)
        url = pick.output.strip()
        workflow.logger.info("Agent picked url=%s", url)

        # 2. Workflow body invokes the long-running activity directly.
        # `start_to_close_timeout` budgets a single attempt; if the worker
        # stops heartbeating for longer than `heartbeat_timeout`, Temporal
        # gives up on this attempt and retries.
        scraped = await workflow.execute_activity(
            long_scrape,
            url,
            start_to_close_timeout=timedelta(seconds=30),
            heartbeat_timeout=timedelta(seconds=2),
        )
        workflow.logger.info("Scrape complete")

        return f"Topic: {topic}\nURL: {url}\nResult: {scraped}"
