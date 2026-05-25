---
title: "Track 02 — lesson co-location revamp"
type: strategy
status: completed
created: 2026-05-24
generated-by: claude (cowork)
summary: >
  Why Track 02's lesson narratives were restructured into co-located
  per-lesson READMEs (retiring the separate lessons/ tree), and the
  template and plan the rebuild followed.
related:
  - docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md
  - tracks/02-temporal/README.md
---

# Track 02 (Temporal) — learning-tool revamp strategy

This is the point-in-time rationale for the Track 02 co-location revamp: why
the lesson narratives were restructured, and the template and plan the rebuild
followed.

## TL;DR

The lesson narratives and the lesson code live in two separate directory trees
(`lessons/` and `examples/`), linked by stale line numbers. The fix:

1. **Co-locate.** Each lesson becomes one self-contained folder. Its
   `README.md` *is* the narrative, sitting next to the code it explains.
   `lessons/` is retired.
2. **Kill line-number references.** "Walk the code" stops citing
   `workflows.py:33`. It refers to code by *symbol name* and embeds short
   snippets inline, so the doc and the code can't drift apart.
3. **Add a "Files in this lesson" section** to every README, and answer —
   once, plainly — the question "does Temporal require this folder layout?"
   (It does not. See [Anatomy](#anatomy-of-a-temporal-lesson-canonical-text).)

Nothing about the code's correctness changes. This is a teaching-layer rebuild.

## What I reviewed

All 11 lesson narratives (`lessons/00`–`11`), the example code, the track and
root READMEs, the `Makefile`, the pytest harness (`tests/conftest.py`,
`test_lesson_*.py`), and the installed `temporalio` 1.27.2 SDK.

## The diagnosis — 6 concrete problems

Evidence is drawn from Lesson 02, the lesson you flagged.

### 1. Narrative and code are in two separate trees

`tracks/02-temporal/lessons/02-stateful-workflow.md` describes
`tracks/02-temporal/examples/02_stateful_workflow/`. To study one lesson you
keep two locations open in different parts of the tree and mentally join them.
This is the "going back and forth" you described.

### 2. The doc-to-code link is line numbers — the most brittle coupling possible

Lesson 02's "Walk the code" cites `workflows.py:33`, `:41`, `:46`, `:51`,
`:61`. Insert one import and every number is wrong. The references aren't
clickable, don't survive reformatting, and tell you nothing about *what* is at
that line until you open the file. This is the mechanism that makes the
back-and-forth actively unpleasant.

### 3. A lesson never introduces its own files

Reading `02-stateful-workflow.md` top to bottom, you are never told that the
lesson is three files or what each does. "Walk the code" jumps straight to
`workflows.py:33`. `worker.py` is never mentioned in Lesson 02 *at all*. The
information exists — in the code files' docstrings, and generically in
`00-orientation.md` — but never in front of you at the moment you need it.
This is exactly the `example.py` / `worker.py` / `workflows.py` confusion you
called out.

### 4. "Does Temporal require this structure?" is never answered

The docs say "by convention" and "two files minimum" in wording that conflates
two different things: the runtime fact that a Temporal app needs a worker
*process* and a client *process*, with this repo's *choice* to split workflow
code, worker bootstrap, and client into three *files*. A learner cannot tell
which constraints are Temporal's and which are the repo's. The honest answer is
never stated. (It is below, and goes into the track README verbatim.)

### 5. Heavy redundancy trains the reader to skim

Lesson 02 states "a workflow is a class because it shares mutable state across
run / signal / query" in the **title**, **Review**, **Goal**, **TL;DR**,
**Why it matters**, and **Mental model** — six times before "Walk the code."
The problem isn't length (you said cutting isn't a goal). It's that four
sections paraphrase one sentence, so the reader learns nothing new from
sections 3–6 and starts skimming — and then skims the parts that *do* carry new
information. Fix: each section gets one distinct job. No content is dropped;
the three overlapping sections are consolidated into one strong explanation.

### 6. Unexplained inconsistencies the reader must silently absorb

- `workflows.py` (plural, lessons 02–09) vs `workflow.py` (singular,
  capstones 10–11).
- `example.py` vs `starter.py` vs `app.py`.
- Helper files (`flaky_tool.py`, `scraper.py`, `activities.py`, `agents/`)
  appear with no "this lesson adds a file, here's why" callout.
- Lesson 01 is a flat notebook; lessons 02+ are directories. The format shift
  mid-track isn't announced.

## The decision — co-locate

Each lesson becomes a single self-contained directory under `examples/`:

```
examples/02_stateful_workflow/
  README.md        <- the lesson narrative (was lessons/02-stateful-workflow.md)
  workflows.py
  worker.py
  example.py
```

Opening the folder — in an IDE or on GitHub — renders the README directly above
the code it describes. One location. The "two trees" problem is gone by
construction, not by discipline. The `lessons/` directory is retired; its
orientation content folds into the track `README.md`.

Lesson 01 is currently a bare notebook (`examples/01_temporal_tour.py` +
`.ipynb`). It moves into `examples/01_temporal_tour/` so every lesson is a
directory — uniform layout, and the notebook gets a co-located README too.

## New lesson README template

Twelve sections. Every existing section is kept; the only structural change is
the new **Files in this lesson** section and merging three overlapping sections
into one. Each section now has exactly one job.

| Section | Job | Change from today |
|---|---|---|
| `# Lesson NN — title` | — | — |
| `## Review` | The *one* prior mechanic you need in hand. 1–2 sentences. | Tightened |
| `## Goal` | The concrete artifact you'll build. | Kept |
| `## Files in this lesson` | Table: file → role. Links to the Anatomy explainer. Flags any new file. | **New** |
| `## How it works` | The single authoritative explanation. ASCII diagram lives here. | **Merged** from TL;DR + Why it matters + Mental model |
| `## Coming from LangGraph` | The translation table. | Kept where present |
| `## Walk the code` | Symbol-anchored tour, grouped by file, short inline snippets. | **Rewritten** — no line numbers |
| `## Run it` | Commands + expected output. | Kept |
| `## Try it` | Modification exercises. | Kept |
| `## Gotchas` | Failure modes. | Kept |
| `## Bridge` | What you can now do + link to the next lesson's folder. | Kept |
| `## Pattern` | The canonical snippet, for a months-later re-read. | Kept |

### The two rules that fix the back-and-forth

**"Files in this lesson" is mandatory and comes early.** A small table, e.g.
for Lesson 02:

| File | Role |
|---|---|
| `workflows.py` | Defines `TallyWorkflow` — the `@workflow.defn` class. The deterministic code. |
| `worker.py` | The worker process. Registers `TallyWorkflow` and polls the task queue. Run in terminal A. |
| `example.py` | The client. Starts the workflow, signals it, queries it. Run in terminal B. |

Lessons 02–04 also carry the Anatomy explainer (below) or a link to it. Later
lessons get a one-line callout whenever they add a file (e.g. "New this
lesson: `flaky_tool.py` — a deliberately unreliable activity").

**"Walk the code" is symbol-anchored, not line-anchored.** Instead of
`workflows.py:33`, the walk says:

> **`TallyWorkflow.__init__`** sets `self._total` and `self._closed` — the
> shared state every signal, query, and the run body read. It runs on start
> *and* every replay, so it must stay deterministic.
> ```python
> def __init__(self) -> None:
>     self._total: int = 0
>     self._closed: bool = False
> ```

Symbol names survive edits; line numbers don't. Embedding the snippet means the
reader sees the code in the doc and rarely needs to switch files at all — and
the doc can't fall out of sync, because it quotes the code rather than pointing
at coordinates in it.

## Anatomy of a Temporal lesson (canonical text)

This goes verbatim into the track `README.md`; every lesson's "Files" section
links to it. It is the answer to "does Temporal expect a folder structure?"

> **Temporal does not require any file or folder layout.** A worker is created
> with `Worker(client, task_queue="...", workflows=[SomeClass],
> activities=[some_fn])` — a task-queue string and two lists of Python objects.
> Workflows are classes decorated with `@workflow.defn`; activities are
> functions decorated with `@activity.defn`. Where you define them — one file
> or twenty — is entirely your choice. A whole Temporal app can be one `.py`.
>
> What a running Temporal app genuinely needs is **three roles** — and they are
> roles, not files:
>
> 1. **Workflow definition** — the `@workflow.defn` class. Deterministic
>    orchestration code.
> 2. **Worker** — a long-lived *process* that connects to the server, polls a
>    task queue, and runs whatever workflow/activity code it was given.
> 3. **Client / starter** — a *process* that tells the server "run workflow X"
>    and optionally signals or queries it.
>
> This track puts each role in its own file (`workflows.py`, `worker.py`,
> `example.py`) for two reasons — both pedagogical or operational, neither a
> Temporal rule:
>
> - **The two-terminal study loop.** You run the worker in terminal A and the
>   starter in terminal B to watch both sides at once. That needs two
>   independently runnable entry points — hence two files with
>   `if __name__ == "__main__"`.
> - **The one real constraint: workflow modules must be import-safe.**
>   Temporal's workflow sandbox *re-imports* your workflow module to
>   reconstruct state during replay. If that module does I/O at import time
>   (opens a file, hits the network, reads a clock), replay diverges from
>   recorded history. Keeping the workflow class alone in `workflows.py`, with
>   no top-level side effects, makes import-safety easy to guarantee. The
>   worker and starter files *do* have side effects — which is the reason they
>   are kept *out* of the workflow module.
>
> So: `workflows.py` is separate because of a genuine Temporal constraint
> (import-safety). `worker.py` and `example.py` are separate because the study
> loop wants two terminals. None of the three filenames is mandated by
> Temporal; a production app might package the worker and its workflows
> together and ship the client as a separate service.

## File-by-file change plan

**Create (11):** `examples/NN_slug/README.md` for every lesson, from the
existing `lessons/NN-*.md` content, restructured to the template.

**Move:** `examples/01_temporal_tour.py` + `.ipynb` →
`examples/01_temporal_tour/`. Update the notebook's docstring line that says
"Read `lessons/01-temporal-tour.md` alongside."

**Edit:**
- `tracks/02-temporal/README.md` — absorb `00-orientation.md`, add the Anatomy
  explainer, point the lesson index at `examples/NN_slug/`.
- Root `README.md` — note that Track 02 now co-locates (the layout diverges
  from Track 01, which is unchanged this pass).
- `Makefile` — `temporal-%` notebook detection now looks *inside* the lesson
  directory for Lesson 01.

**Delete:** `tracks/02-temporal/lessons/` (all 12 files). Content has moved.

**Untouched:** all `.py` lesson code, `tests/`, `docker/`,
`learn_pydantic_ai/`. The pytest harness resolves lessons via
`conftest.use_lesson(slug)` against `examples/NN_slug/` and has no dependency
on `lessons/` — verified. Adding a `README.md` to a lesson dir changes
nothing for the tests.

## Risks and out-of-scope follow-ups

- **Lesson 01 move + Makefile change** is the only change that touches a
  runnable path. Mitigation: explicit verification step that `make temporal-01`
  and the notebook pairing still resolve.
- **Filename standardization** (`workflow.py` → `workflows.py`,
  `starter.py`/`app.py`) is deliberately *out of scope* — it would touch
  imports and tests for a cosmetic gain. The READMEs explain the variance
  instead. Worth a separate, focused pass later if desired.
- **Track 01** keeps its `lessons/` + `examples/` split this pass. If the
  co-located format works well here, applying it to Track 01 is a clean
  follow-up.
- A copy of the template skeleton lands at `examples/_lesson-template.md` so
  future lessons start in the right shape. The `_` prefix keeps it out of the
  `NN_` lesson namespace and the Makefile globs.
