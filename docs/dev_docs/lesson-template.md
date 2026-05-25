# Lesson template

Skeleton for a new Track 02 lesson. Copy this into a new
`examples/NN_<slug>/README.md` and fill it in. Lesson 02
(`02_stateful_workflow/README.md`) is the worked reference — match its voice
and formatting.

Twelve sections, in this order. Every section has one job; don't restate
across sections. Keep substantive depth — the goal is teaching, not brevity.

```markdown
# Lesson NN — <title>

> The code for this lesson is the .py files in this folder. Read this page top
> to bottom; it quotes every part of the code you need to see.

## Review

One or two sentences: the single mechanic from the previous lesson the reader
needs in hand here. (Omit only for Lesson 01 — there is no prior lesson.)

## Goal

The concrete artifact this lesson builds, in 2–3 sentences.

## Files in this lesson

| File | Role |
|---|---|
| `workflows.py` | ... |
| `worker.py` | The worker process. Run in terminal A. |
| `example.py` | The client. Run in terminal B. |

If the lesson adds a file the previous lesson didn't have, flag it:
**New this lesson:** `<file>` — <one line on why it exists>.
Link the structure explainer once: see
[Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

The single authoritative explanation. This section absorbs what older drafts
split across "TL;DR", "Why it matters", and "Mental model" — say each idea
once, well. Put any ASCII diagram here. Use `###` subsections for deeper dives.

## Coming from LangGraph?

The translation table, if the concept has a LangGraph analogue. Omit the
section if it doesn't.

## Walk the code

Group by file with `###` subheadings. Refer to code by SYMBOL NAME — class,
method, function, variable — never by line number (line numbers go stale the
moment anyone edits the file). Embed a short (3–8 line) snippet, copied
accurately from the real file, for each thing you point at. The reader should
be able to follow the walk without leaving this page.

### `workflows.py` — ...

**`SomeClass.some_method`** does X.

​```python
# a short, accurate snippet
​```

## Run it

The commands (server, worker, starter) and the expected output.

## Try it

2–4 modification exercises that change behaviour and reward inspection.

## Gotchas

The failure modes — what breaks, and why.

## Bridge

What the reader can now do, and a link to the next lesson:
[Lesson NN+1](../NN+1_<slug>/README.md).

## Pattern

The canonical code shape, for a months-later re-read.
```
