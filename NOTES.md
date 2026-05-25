# Henry's Personal Notes

> Personal scratchpad. Do not edit without explicit permission.

## Active Work

### In progress
_(nothing right now)_

### Next up
_(pull from backlog when ready)_

### Backlog

**Repo organization**
- [ ] Decide a lesson file decomposition standard: when to split into `models.py` / `activities.py` / `workflows.py` / `worker.py` vs. keep in one file
- [ ] Track 01 has line-number code refs (`02_hello_agent.py:16`) — rewrite as symbol refs + verbatim snippets per [LESSON-DEVELOPMENT-GUIDE](docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md) rule 3.2

**Concept docs to write** — see [Document stubs](#document-stubs)
- [ ] Temporal Nexus explainer
- [ ] Temporal server UI tour
- [ ] Temporal server + workflow requirements
- [ ] `pai` REPL quickstart

**Research**
- [ ] Mine [steveandroulakis/temporal-ralph-wiggum](https://github.com/steveandroulakis/temporal-ralph-wiggum) and [steveandroulakis/temporal-langgraph-checkpoint-recovery](https://github.com/steveandroulakis/temporal-langgraph-checkpoint-recovery) for code-organization patterns worth borrowing

### Done
- [x] 2026-05-25 — Co-located track 1 lessons into `lessons/NN_<slug>/` dirs (mirrors track 2); moved `runtimes.md` to `docs/`; YAMLs into the lesson dirs that own them
- [x] 2026-05-25 — Drafted Temporal codec server explainer ([docs/temporal/codec-server.md](docs/temporal/codec-server.md))
- [x] 2026-05-25 — Renamed `tracks/02-temporal/examples/` → `lessons/`; Makefile, tests, READMEs, dev guide all updated
- [x] 2026-05-25 — Decided: keep `learn_pydantic_ai/` package name (Python convention > shorter)
- [x] 2026-05-25 — Reorganized this file (NOTES.md) by purpose
- [x] 2026-05-24 — Standardized AI-gen doc naming + frontmatter ([docs/dev_docs/ai_gen/README.md](docs/dev_docs/ai_gen/README.md) sets the convention)

---

## Open Questions

Promote answered questions into a lesson or doc, then move the entry to **Resolved** below with a pointer.

### Pydantic AI
_(none right now)_

### Temporal
- [ ] Are there restrictions on the return types of activities?
- [ ] Can a single Temporal server handle activities across multiple SDK languages (Python + Go + TS workers in one cluster)?
- [ ] What communication protocols does a Temporal server use to talk to worker processes?
- [ ] Does a Temporal server work with any worker bound via configuration, or is there a tighter pairing?

### Pydantic AI × Temporal
- [ ] How do we implement agent middleware (pydantic-ai or otherwise) under Temporal?

### Resolved
_(empty — link to the lesson/doc that answered it when you move entries here)_

---

## Document Stubs

Drafts to expand later. Promote to [docs/](docs/) once they have substance.

### Temporal codec server
- What it is, why it exists (encryption/redaction of payloads in the Temporal UI)
- Architecture reference: ![data converter arch](assets/temporal-data-converter-arch.png) (worker/client-side encoding — the codec server sits adjacent)
- Minimum setup
- When to use it vs. when not to

### Temporal Nexus
- What it is, what problem it solves
- vs. cross-namespace workflow calls
- Worked example

### Temporal server UI tour
Pages to cover: Workflows · Schedules · Batch · Deployments · Archive · Namespaces

### Temporal server + workflow requirements
- For the server to do its job for a workflow, the following must be true: …
- Minimum required structure for a workflow: …
- Optional elements: …

### `pai` REPL quickstart
```sh
export ANTHROPIC_API_KEY=...
uv run pai -m anthropic:claude-opus-4-7
```
- What it's good for
- Useful flags / config

---

## Resources

### Official
- [Pydantic AI docs](https://ai.pydantic.dev/)

### Inspiration repos
- [steveandroulakis/temporal-ralph-wiggum](https://github.com/steveandroulakis/temporal-ralph-wiggum)
- [steveandroulakis/temporal-langgraph-checkpoint-recovery](https://github.com/steveandroulakis/temporal-langgraph-checkpoint-recovery)

### Architecture diagrams
- ![Temporal data converter architecture](assets/temporal-data-converter-arch.png) — accompanies [docs/temporal/codec-server.md](docs/temporal/codec-server.md)

---

## Lesson Notes — As Learner

Capture aha-moments and confusions while working through lessons. Promote questions to [Open Questions](#open-questions); promote pedagogical observations to [As Designer](#lesson-notes--as-designer).

### Track 01 — Intro
_(empty)_

### Track 02 — Temporal

**Lesson 01** — see [Open Questions → Temporal](#temporal)

---

## Lesson Notes — As Designer

Capture pedagogical observations: what works, what doesn't, what's missing, what to teach next.

_(empty)_
