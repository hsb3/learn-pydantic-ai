# Lesson authoring & quality guide — Track 02

> **This is a living document.** It defines how Track 02 lessons are written and
> how they are quality-checked. Update it whenever the lesson format, the
> authoring rules, or the QC process changes — and add a line to the
> [Revision log](#revision-log) when you do. If a lesson and this guide
> disagree, fix one of them; they are not allowed to drift.

Companion files:

- [`lesson-template.md`](lesson-template.md) — the copy-paste skeleton for a
  new lesson.
- [`ai_gen/2026-05-24-track-02-colocation-revamp.md`](ai_gen/2026-05-24-track-02-colocation-revamp.md)
  — the point-in-time rationale for why the track moved to this format.
  Historical; this guide supersedes it as the working standard.

## 1. Approach

### Teaching-first

A lesson is a teaching artifact, not reference documentation. Optimise every
decision for a first-time learner working through the track in order. Depth is
welcome; **brevity is not a goal**. Do not trim a lesson to hit a word count —
the project-README length conventions (250–500 words, etc.) explicitly **do
not** apply to lesson READMEs. Cut a sentence only when removing it makes the
lesson *clearer*, never merely shorter.

The failure mode to avoid is redundancy, not length: if four sections restate
the same idea, the learner starts skimming and then skims the parts that
*do* carry new information. Each section must do a distinct job.

### Co-location

Each lesson is a self-contained directory under `examples/`. Its `README.md`
*is* the lesson narrative, sitting next to the code it explains:

```
examples/NN_<slug>/
  README.md        the lesson narrative
  workflows.py     (or workflow.py / agents/ / activities.py / ...)
  worker.py
  example.py       (or starter.py / app.py)
```

One directory is the whole lesson. There is no separate `lessons/` tree. A
learner never cross-references two locations, and the narrative cannot drift
away from code it sits beside.

### Learner-walkthrough mindset

Before a lesson is considered done, someone reads it cold — top to bottom, as a
first-timer who has done the previous lessons and nothing more — and writes
down every point of friction. This is QC step 7 below. It is the check that
catches contradictions a structural scan cannot (e.g. a "Files" section saying
"no docker needed" while "Run it" says `make temporal-up`).

## 2. Lesson README template

Twelve sections, in this order. Each has exactly one job. The skeleton is in
[`lesson-template.md`](lesson-template.md); the worked reference is
[`02_stateful_workflow/README.md`](../../tracks/02-temporal/lessons/02_stateful_workflow/README.md).

| Section | Job |
|---|---|
| `# Lesson NN — title` + blockquote | Title, then a one-line note that the code is in this folder and the page quotes it. |
| `## Review` | The *one* prior-lesson mechanic the reader needs in hand. 1–2 sentences. Omitted only by Lesson 01. |
| `## Goal` | The concrete artifact this lesson builds. |
| `## Files in this lesson` | A table mapping every file to its role. See rule 3.1. |
| `## How it works` | The single authoritative explanation. Absorbs what older drafts split across "TL;DR", "Why it matters", and "Mental model". ASCII diagrams live here. |
| `## Coming from LangGraph?` | The translation table. Omit the section if the concept has no LangGraph analogue. |
| `## Walk the code` | Symbol-anchored tour, grouped by file. See rule 3.2. |
| `## Run it` | Commands + expected output. |
| `## Try it` | 2–4 modification exercises. |
| `## Gotchas` | Failure modes — what breaks, and why. |
| `## Bridge` | What the reader can now do + a link to the next lesson. |
| `## Pattern` | The canonical code shape, for a months-later re-read. |

## 3. Authoring rules

### 3.1 "Files in this lesson" is mandatory

Every lesson lists each code file with a one-line role. Whenever a lesson
introduces a file the previous lesson did not have, flag it:
`**New this lesson:** <file> — <why it exists>`. Lessons 03–04 also carry a
one-sentence "Temporal mandates no file layout" note linking the
[Anatomy of a Temporal lesson](../../tracks/02-temporal/README.md#anatomy-of-a-temporal-lesson)
explainer in the track README.

### 3.2 "Walk the code" is symbol-anchored — never line numbers

Refer to code by **symbol** — class, method, function, variable name — never by
line number. Line numbers go stale on the next edit, aren't clickable, and
say nothing about what's there. Group the walk by file under `###` subheadings,
and embed a short (3–8 line) snippet, copied **verbatim** from the real file,
for each thing you point at. The reader should be able to follow the walk
without leaving the page.

### 3.3 The How-it-works / Walk-the-code de-duplication rule

"How it works" may show a *minimal* snippet when it introduces a named piece
(the "meet the pieces one at a time" device). When it does, "Walk the code"
must **not** re-paste an identical snippet — it either shows the fuller,
in-context version (e.g. the real argument values instead of a `…` placeholder)
or just discusses the symbol and references "How it works". The learner should
never read the exact same code block twice in one lesson.

Default: keep code out of "How it works" entirely (prose + diagrams only) and
let "Walk the code" be the single home for snippets. Lesson 02 is the model.

### 3.4 Keep the narrative in sync with the code

The lesson README and the lesson's `.py` files are one unit. When you change a
lesson's code, update its README in the **same** change — the Files table, the
Walk-the-code snippets, the diagrams, the Try-it steps. A README that describes
code that no longer exists is worse than no README. (This is how Lesson 11's
narrative had drifted a full revision behind its `workflow.py`.)

### 3.5 Cross-links and accuracy

- Link other lessons as `../NN_<slug>/README.md`; link the anatomy explainer as
  `../../README.md#anatomy-of-a-temporal-lesson`.
- Code snippets are copied from the real files, not paraphrased or remembered.
- Tone: technical, precise, direct. No filler, no flattery.

### 3.6 File decomposition — split only when something forces it

A single `.py` file is the default. Split a lesson into multiple files when (and only when) one of these conditions holds:

1. **Temporal sandbox isolation** — the workflow class must live in a module with no top-level I/O, network calls, or non-deterministic imports. The sandbox re-imports workflow modules during replay, so anything that runs at import time can break determinism. This is why Track 02 Lessons 02–09 split `workflows.py` (clean) from `worker.py` (does I/O at startup) and `example.py` / `starter.py` (talks to the cluster).
2. **Two-process study loop** — when the learner runs the worker in one terminal and the starter in another, those are necessarily different processes and therefore different entry-point files (`worker.py` + `example.py` / `starter.py`). Use this split when the lesson's value comes from watching the cluster mediate between the two.
3. **Capstone complexity** — when the supporting code passes ~3 files of logic, split by role: `agents/`, `activities.py`, `schemas.py`, etc. Don't pre-split a small lesson into named-by-role files just because a future one does.
4. **External framework boundaries** — when one file is consumed by a different runtime (e.g. `app.py` by `uvicorn`, `ui.py` by `streamlit`), it gets its own file.

If none of the above apply, **keep the lesson in one file.** Track 01 Lessons 02–12 are single-file because Pydantic AI itself imposes none of those constraints — there's no sandbox, no two-process loop, and the lesson scope is one mechanic.

A lesson README that introduces a new file must say *which* of these reasons drove the split (see rule 3.1's "New this lesson" annotation).

### 3.7 Every lesson's code is tested

A learner must never be the first to find out a lesson's code is broken. Every
lesson ships with an automated test that runs its code end to end — the
workflow executes, the activities and tools fire, and the expected result
comes back.

- Lessons 02–11: a `tests/test_lesson_NN.py` that drives the workflow under
  `WorkflowEnvironment.start_local()` — an in-process server, no docker
  needed. The test covers the lesson's helper files (`flaky_tool.py`,
  `scraper.py`, `agents/`, `activities.py`, …) transitively, because the
  workflow it runs imports and exercises them.
- Lesson 01 (notebook): covered by `make nb-exec`, which executes the notebook
  headless.
- **Writing the test is not enough — it must be run and pass before the lesson
  is considered done.** A lesson with an unrun or failing test does not ship.
  See QC step 6.
- Rule 3.4 applies to tests too: when you change a lesson's code, update its
  test in the same change.

## 4. Quality-control procedures

Run every check below before considering a lesson (or a batch of edits) done.
Paths assume the repo root.

**1. All lessons present, section structure intact**

```bash
for f in tracks/02-temporal/lessons/*/README.md; do
  echo "$f -> $(grep -cE '^## ' "$f") sections"
done
```

Expect 11 sections each (10 for Lesson 01 — it omits Review).

**2. No broken relative links**

```bash
for f in tracks/02-temporal/README.md tracks/02-temporal/lessons/*/README.md; do
  d=$(dirname "$f")
  grep -oE '\]\([^)]+\)' "$f" | sed -E 's/^\]\(//; s/\)$//' | while read -r l; do
    case "$l" in http*|\#*) continue;; esac
    t="${l%%#*}"; [ -z "$t" ] && continue
    [ -e "$d/$t" ] || echo "BROKEN: $f -> $l"
  done
done
```

**3. No line-number code references** (rule 3.2)

```bash
grep -rnE '`?[a-z_]+\.py:[0-9]+' tracks/02-temporal/lessons/*/README.md || echo clean
```

**4. No stray tool/XML tags** (leaked tool-call markup)

```bash
grep -rnE '</?(content|invoke|antml|parameter|function)' tracks/02-temporal/**/*.md || echo clean
```

**5. Snippet accuracy** — for each snippet in "Walk the code", open the real
file and confirm the code matches. Snippets are verbatim, not approximate.

**6. Every lesson is tested, and the whole suite is green**

Every lesson must have an automated test (rule 3.7) — a lesson is not done
until its test exists. Run the full suite; it must pass before any lesson
ships:

```bash
make test-lessons-temporal      # lessons 02–11, in-process server, no docker
make nb-exec                    # runs paired notebooks headless, incl. Lesson 01
```

Then confirm the Makefile resolves each lesson's entry point
(`make temporal-NN` / `make temporal-NN-worker`).

**8. Learner walkthrough** — read the lesson cold, top to bottom, as a
first-timer who has done the prior lessons and nothing else. Write down every
point of friction: contradictions, unexplained jargon, an instruction that
assumes setup the lesson never described, a forward reference that doesn't
resolve. Fix what you find. This step is not optional — it is the check that
finds what the greps cannot.

## 5. Revision log

- **2026-05-25** — Added authoring rule 3.6 (file decomposition: split only
  when something forces it). Codifies what Track 02 already does and explains
  why Track 01 stays single-file. Previous rule 3.6 (every lesson is tested)
  is now 3.7.
- **2026-05-25** — Renamed `tracks/02-temporal/examples/` → `lessons/` for naming
  consistency with the on-disk reality (each subdir is a lesson). Dropped QC
  step 5 ("no lesson README references the retired `lessons/` tree") — moot
  after rename — and renumbered the remaining checks. Live references updated;
  earlier revision-log entries kept verbatim.
- **2026-05-24** — Guide created (as `LESSON-DEVELOPMENT-GUIDE.md`) alongside
  the Track 02 co-located rebuild of all 11 lessons. Established rules 3.1–3.5
  and QC steps 1–8. The point-in-time rationale is
  `ai_gen/2026-05-24-track-02-colocation-revamp.md`.
- **2026-05-24** — Guide and lesson template relocated to `docs/dev_docs/`.
  Added authoring rule 3.6 (every lesson's code is tested) and rewrote QC
  step 7 to require the test exist and the suite be green.
