---
title: Replacing langgraph-api with Temporal + Pydantic AI — research log
date: 2026-05-24
tags: [temporal, pydantic-ai, langgraph, durable-execution, agents, azure, architecture]
status: research-complete · building · contribution-deferred
---

# Replacing langgraph-api with Temporal + Pydantic AI

> **Read this first if you (future me, or someone new) are asking "what was this about, and did we decide anything?"** This is a narrative lab log, not just a findings list. Premise → conclusions → how we got there → decisions → evidence → what's unfinished.

## Premise — why this conversation happened

I've run a custom **langgraph-api** server in production on Azure for ~6 months (managed Redis + Postgres, Container App behind an NGINX proxy that exists only to bolt on auth, because langgraph-api blocks non-LangSmith deployments). I'm frustrated with LangGraph Platform's proprietary coupling and debugging opacity. The question driving everything below: **can I replace it with a homegrown stack — FastAPI + Temporal + Pydantic AI — and what would it actually cost me to build?** The thread ran from "remind me what Temporal even is" all the way to "I now understand agents well enough to weigh contributing to Pydantic AI."

**Glossary** (terms used throughout): **Temporal** = durable-execution engine (crash-proof workflows via replay). **Pydantic AI (PA)** = type-safe agent framework with a native Temporal integration. **BSP** = Bulk Synchronous Parallel (LangGraph/Pregel's superstep model). **DSL** = Domain-Specific Language (e.g. LangGraph's graph-authoring API). **HITL** = Human-In-The-Loop. **SSE** = Server-Sent Events. **PE/NSG/MI** = Private Endpoint / Network Security Group / Managed Identity. **KEDA** = event-driven autoscaler (what Azure Container Apps uses under the hood).

## Conclusions (the headline answers)

1. **Yes — the homegrown stack is viable and arguably cleaner than langgraph-api.** A working scaffold (`duragraph`) was built and its hardest piece (streaming) verified against the real library.
2. **The durable "magic" is mostly pre-built.** Pydantic AI's native Temporal integration converts model/tool/MCP calls into durable activities automatically — I'm not reinventing durability.
3. **The framework bet is de-risked by architecture, not faith.** PA is a one-file coupling behind surfaces I own (the FastAPI contract + Temporal), so it's swappable. That's what makes the maturity/bus-factor risk acceptable.
4. **Don't port LangGraph onto Temporal.** Mapping `CompiledStateGraph` onto Temporal means reimplementing Pregel — a research project. Wrap coarse if needed; port to PA for native durability.
5. **My langgraph fluency isn't sunk cost.** What's valuable is conceptual (state machines, control flow, reducers) and transfers; only API method-names are throwaway.

## How we got there (the arc)

1. **Re-grounded on Temporal:** durable execution = your code survives crashes because every step is journaled and **replayed** (completed work isn't re-run; recorded results are fed back). Workers/workflows/activities.
2. **Mapped Temporal's surface** (interfaces, CLI, packaged UI, visibility, auth) and found it fits self-hosting *better* than langgraph-api — first-class auth hooks instead of my NGINX workaround, and full UI search on my existing Postgres with no Elasticsearch.
3. **Designed the Azure deployment** (Container Apps + managed Postgres), then hardened it into a secure private-networking topology, then re-rendered it with branded Azure icons (D2 diagrams).
4. **Pinned down scaling responsibilities:** Temporal packages the polling; *I* own replica scaling (KEDA on backlog, not CPU). Surfaced the scale-to-zero tension with my low-frequency cost model.
5. **Settled the architecture** — API server in front, Temporal as the durable backend, PA as the agent core — and identified **streaming** as the single genuinely hard piece.
6. **Found the OSS to borrow** (PA's native Temporal integration is the unlock; `temporal-ai-agent` is the closest end-to-end reference shape).
7. **Built `duragraph`** — a langgraph-api-shaped server on the new stack — and **verified the streaming handler** against pydantic-ai 1.102.0 with a repo test.
8. **Went conceptual** to make sure I understood what I was replacing: langgraph-api is *not* Temporal — it's LangGraph's own Pregel engine with snapshot durability, bundled into one image.
9. **Tested whether I could keep LangGraph and just swap the runtime** — concluded no (Pregel's state snapshot is intrinsic; you'd rewrite the executor), and that my fluency transfers regardless.
10. **Assessed framework risk** (PA company is Sequoia-funded and strategically motivated; velocity/bus-factor risk is real but bounded by the swappable architecture).
11. **Compared LangChain 1.0 middleware to PA** — discovered PA already shipped the equivalent abstraction (Capabilities + hooks); the gap is library breadth and docs, and durability actually favors PA.
12. **Built a shared mental model** that retroactively explained the whole architecture: an agent is a loop mutating a JSON blob, split into a control plane (decide) and data plane (do) — which is exactly what Temporal's workflow/activity split makes physical.

## Standing decisions (these constrain future choices)

- Go homegrown: **FastAPI (contract) + Temporal (durability) + Pydantic AI (agent core).**
- Keep the agent framework **swappable** — isolate it to one module (`worker/agents.py`); OpenAI Agents SDK is the fallback (also has a Temporal integration).
- **Do not build a LangGraph→Temporal compiler.** Coarse-wrap legacy graphs or port them to PA.
- **Don't scale workers on CPU; don't chase scale-to-zero.** Scale on schedule-to-start latency; `minReplicas ≥ 1`; graceful drain.
- **Pin versions; fork unmerged upstream PRs rather than wait.** The verified handler test is the upgrade canary.
- **Contribution to PA is deferred** until I've finished building my own understanding and product.

## Findings — confirmed (seem true)

| Hypothesis | Note |
|---|---|
| Temporal = durable execution via **replay**; workflow (deterministic) + activities (journaled I/O) | On recovery, activities are not re-run — recorded results are fed back. |
| One gRPC frontend `:7233`; `WorkflowService`=data plane, `OperatorService`=control plane; CLI = `temporal` | `tctl` legacy; schema via `temporal-sql-tool`. |
| Packaged self-hosted UI (`temporalio/ui`); full search on **Postgres, no Elasticsearch** | Advanced visibility: server ≥1.20, Postgres ≥12; standard removed in 1.24. |
| Native HTTP/JSON API + pluggable authorizer | Better than langgraph-api's auth block + my NGINX workaround. |
| SDK packages polling + in-process concurrency; **replica scaling is mine** | KEDA Temporal scaler v2.17+; ACA autoscaling is KEDA-based. |
| Worker scale-to-zero possible but **unreliable** | Backlog ignores in-flight tasks; keep min ≥ 1. |
| Postgres Flexible Server networking mode is **immutable at creation** | Private VNet-integration vs public+PE; recreate+migrate to switch. |
| PA has **native, co-maintained** Temporal integration | `TemporalAgent` auto-activitizes model/tool/MCP calls. **2MB** event-history payload ceiling. |
| `event_stream_handler` maps PA events → stream modes | **Verified against pydantic-ai 1.102.0** via repo test (switch on `event_kind`/`part_delta_kind`). |
| PA already shipped a **middleware-equivalent** | **Capabilities** + `before/wrap/after_model_request` hooks; `FallbackModel`, `ModelRetry`, `ProcessHistory`, deferred-tool HITL; "Harness" library + YAML specs. |
| Replay tolerates LLM non-determinism | I/O quarantined in journaled activities; only deterministic control flow replays. |
| Pydantic (company) is funded + motivated to maintain PA | Sequoia-backed ~$17.2M; revenue = Logfire; PA is the funnel into it. |
| PA has LangChain tool adapters (`tool_from_langchain`, `LangChainToolset`) | But PA doesn't validate their args — a bridge, not a destination. |

## Findings — corrected / refuted (seemed true, weren't)

| Claim | Correction |
|---|---|
| "langgraph-api builds a Temporal server from config + code." | It runs LangGraph's **own Pregel engine** with **snapshot** durability, bundled in **one Docker image** — not Temporal. (Two-layer instinct right; engine wrong.) |
| "A LangChain core engineer contributes to PA." | Verifiable flow is the **opposite**: Sydney Runkle, ex-core-Pydantic, now leads LangGraph at LangChain. |
| "Reuse `CompiledStateGraph` on Temporal without the weight." | Topology/properties are cheap; but **step durability forces the full channel snapshot each superstep** (intrinsic to BSP) → collides with the 2MB ceiling + two durability models. |
| "Keep the LangGraph surface and reuse Pregel on Temporal for free." | Keep the authoring surface, but you must **rewrite the executor**; you can't reuse Pregel. Costs a determinism audit + loss of time-travel/state-history. |
| (My earlier claim) "PA de-emphasizes extensibility." | **Stale.** PA shipped the full Capabilities+hooks system. Gap is breadth + docs, not the abstraction. |

## Findings — unverified (re-check before acting)

- PA's single-maintainer / stalled-PR bus-factor (my anecdotal read; consistent with history but not confirmed).
- Whether PA's "Harness" capability library matches LangChain's ~20+ prebuilt middlewares in breadth.
- My production Postgres's networking mode (must confirm before designing the Azure topology — it's immutable).

## The mental model that survived

**An agent is a loop mutating a JSON conversation blob:** send to model → watch for tool-call → execute → fold result back → repeat until final. Split into **data plane (do)** = model call, tool watch/dispatch, tool execution, the blob; and **control plane (decide)** = request-shaping (middleware/Capabilities), orchestration of order + conditions, externalization of data per declared intent.

Maps onto Temporal with no leftovers: orchestration → **workflow** (deterministic = decisions replay), execution → **activities** (journaled). "Keep hook state **serializable**" = anything crossing the control↔data boundary must be plain JSON (no live handles), because that boundary is where Temporal writes state down to survive a crash. **Externalize by intent** → different store per scope: in-memory (turn) · event history (resumable run) · Supabase (cross-run) · Redis (ephemeral stream) · audit log. Fuzzy seams: the tool-call watcher straddles planes; streaming deliberately violates the boundary. And "control/data plane" has two altitudes — platform (`Operator`/`Workflow` services) vs agent-execution (orchestration vs calls) — don't conflate.

Bonus framing: middleware ≅ **composition** over the model-call morphism `(Request→Response)→(Request→Response)`. LangChain expresses it as graph nodes; PA as typed composable units.

## Open threads / next actions

- **Streaming:** handler verified at unit level; **not yet proven end-to-end** against a live provider.
- **Auth dependency** (to retire NGINX) — not built.
- **Supabase persistence** for the thread/assistant catalog — not built (durable run state already lives in Temporal).
- **Message-history threading** — currently stringified; refine, watch the 2MB ceiling.
- **Resumable streams** (Redis Streams + Last-Event-ID) — only if refresh-mid-response / multi-device is needed.
- Rename `duragraph` (placeholder); a truncated diagram was never redrawn (cosmetic).
- **Contribution (when ready):** the LangChain-middleware → PA-Capability translation map; porting capabilities into the Harness; Temporal-durability notes for capability authors; the "middleware = composition" framing doc.

## State at close

Leaning strongly toward building on **Pydantic AI + Temporal**. The earlier tensions — fear of losing LangGraph fluency, doubts about PA maturity — are largely resolved: the fluency is conceptual and transfers, and PA is further along (a shipped Capabilities system, durable-runtime-friendly) than I'd perceived. Contribution is appealing and well-suited to my strengths (translation/framing/math over heavy engineering) but **deliberately deferred** — focus on my own understanding and product first.

## References

**Repos**
- [pydantic/pydantic-ai-temporal-example](https://github.com/pydantic/pydantic-ai-temporal-example) — official PA + Temporal example (the wiring + thread-actor loop).
- [steveandroulakis/temporal-ai-agent](https://github.com/steveandroulakis/temporal-ai-agent) — closest end-to-end langgraph-api-like reference (community fork: [temporal-community/temporal-ai-agent](https://github.com/temporal-community/temporal-ai-agent)).
- [temporal-community/ai-agents-workshop-python](https://github.com/temporal-community/ai-agents-workshop-python) — progressive HITL / multi-agent patterns.
- [temporal-community/openai-agents-demos](https://github.com/temporal-community/openai-agents-demos) — OpenAI Agents SDK on Temporal.
- [temporalio/samples-python](https://github.com/temporalio/samples-python) — official samples, incl. the `workflow_streams` sample.
- [temporalio/sdk-python](https://github.com/temporalio/sdk-python) — the Temporal Python SDK.
- [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) — the framework itself.
- [benc-uk/icon-collection](https://github.com/benc-uk/icon-collection) — Azure SVG icons (used in the D2 diagrams).

**Docs**
- Pydantic AI: [durable execution / Temporal](https://ai.pydantic.dev/durable_execution/temporal/) · [Capabilities](https://pydantic.dev/docs/ai/core-concepts/capabilities/) · [message history](https://pydantic.dev/docs/ai/core-concepts/message-history/) · [third-party (LangChain) tools](https://ai.pydantic.dev/third-party-tools/).
- Temporal: [Workflow Streams (Python)](https://docs.temporal.io/develop/python/workflows/workflow-streams) — now a native `temporalio.contrib` library, the first-class alternative to the Redis→SSE pattern · [Python developer guide](https://docs.temporal.io/develop/python).
- LangChain: [prebuilt middleware](https://docs.langchain.com/oss/python/langchain/middleware/built-in) · [agent middleware design blog](https://blog.langchain.com/agent-middleware/).

**Streaming** — [Architecting Bytes: Temporal workers → Redis → SSE](https://www.architectingbytes.com/posts/temporal-redis-sse/) (the pattern to copy if not using native Workflow Streams).

**Company / funding** — [Logfire launch + Series A](https://pydantic.dev/articles/logfire-announcement) · [TechCrunch: Sequoia backs Pydantic](https://techcrunch.com/2024/10/01/sequoia-backs-pydantic-to-expand-beyond-its-open-source-data-validation-framework) · [original company / seed announcement](https://pydantic.dev/articles/company-announcement).
