# AI-generated dev docs

This folder holds **AI-generated planning, strategy, and status documents** —
point-in-time records of work done with an AI assistant. They are *historical
artifacts*, not living documentation: each captures the reasoning and plan
behind a piece of work at the moment it was done. Living standards — documents
you keep updating — live as their own maintained files (e.g.
[`../LESSON-DEVELOPMENT-GUIDE.md`](../LESSON-DEVELOPMENT-GUIDE.md)), not here.

The point of this folder — and the convention below — is that when you open one
of these in six months you can tell, without reading the body, **what it is,
why it exists, and whether it still matters.**

## Naming convention

```
YYYY-MM-DD-<slug>.md
```

- `YYYY-MM-DD` — the date the document was created. The folder then sorts
  chronologically, and "when" is visible without opening the file.
- `<slug>` — a short kebab-case description of the topic.

Example: `2026-05-24-track-02-colocation-revamp.md`.

## Required frontmatter

Every document in this folder begins with a YAML frontmatter block:

```yaml
---
title: "Human-readable title"
type: strategy            # plan | strategy | status | retro | decision
status: completed         # draft | active | completed | superseded | archived
created: 2026-05-24       # matches the filename date prefix
updated: 2026-05-24       # optional — last meaningful edit
generated-by: claude (cowork)
summary: >
  One to three lines: why this document exists and what it covers.
related:                  # optional — repo-root-relative paths
  - docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md
---
```

| Field | Required | Notes |
|---|---|---|
| `title` | yes | Human-readable; not the filename. |
| `type` | yes | `plan`, `strategy`, `status`, `retro`, or `decision`. Extend the list deliberately, not ad hoc. |
| `status` | yes | `draft` → `active` → `completed`, or `superseded` / `archived`. Keep it current — a stale `active` is worse than no field. |
| `created` | yes | `YYYY-MM-DD`; must match the filename's date prefix. |
| `updated` | no | Last meaningful edit, if different from `created`. |
| `generated-by` | yes | What produced it, e.g. `claude (cowork)`. This folder is for AI-generated docs — say so. |
| `summary` | yes | One to three lines. The single most important field: the "why does this exist" answer for a future reader. |
| `related` | no | Repo-root-relative paths to the code or docs the document concerns. |
| `superseded-by` | no | Repo-root-relative path to the document that replaces this one. Set it whenever `status: superseded`. |

## Lifecycle

- A document is born `draft` or `active`, and moves to `completed` when the
  work it describes is done.
- When a later document replaces it, set `status: superseded` and add
  `superseded-by:`. Don't delete superseded docs — the trail is the point.
- `archived` is for documents kept only for the record, no longer worth
  reading.

## This README

This README is the folder's standing index and is **exempt** from the
per-document convention above — no date prefix, no frontmatter — because it is
not itself a point-in-time document.
