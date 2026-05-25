---
name: inspiration-notes
description: Patterns mined from steveandroulakis reference repos that could inform learn-pydantic-ai organization
created: 2026-05-25
---

# Inspiration: steveandroulakis reference repos

## temporal-ralph-wiggum
### File layout
Simple, flat structure: `src/ralph_wiggum/{workflows.py, activities.py, models.py, worker.py}`. Single workflow class, activities as module-level functions.

### Notable patterns

**Activity naming:** Verb-noun conventions (`decide_iteration_mode`, `generate_tasks`, `execute_task`, `evaluate_iteration_completion`, `extract_final_result`). Clear intent from the name alone.

**Input/output typing:** Every activity takes a single typed input object (e.g., `DecideIterationInput`) and returns a single typed output (e.g., `DecideIterationOutput`). Both defined in `models.py`. Eliminates parameter ambiguity.

**Workflow as state machine:** `RalphWorkflow` exposes query methods (`get_current_iteration()`, `get_progress_summary()`, `get_current_tasks()`) for external monitoring. Activity retries use consistent config: `start_to_close_timeout=timedelta(minutes=2)`, 3 attempts, exponential backoff.

**Continue-as-new strategy:** Preserves only essential state across workflow boundaries (iteration count, conversation history, progress summary). README explicitly calls this out as preventing "unbounded event logs" — a teaching moment.

### What I'd borrow
- **Input/output dataclass discipline**: Forces clarity about what each activity needs and produces. Easy to add to LESSON-DEVELOPMENT-GUIDE as a checkpoint rule.
- **Query methods for observability**: Great for showing students how to monitor long-running workflows without adding debugging clutter.
- **Explicit timeout/retry patterns**: The README explains *why* continue-as-new exists. Replicable explanation style.

---

## temporal-langgraph-checkpoint-recovery
### File layout
Layered: `langgraph_agent/{workflow.py, activities.py, adapters/{base.py, langgraph.py, sleeping.py}, graph.py, shared.py, runner.py}`. Adapter pattern separates agent implementations from Temporal infrastructure.

### Notable patterns

**Adapter abstraction:** Base class defines three methods: `setup()`, `run()` (yields `StepResult` with optional checkpoint_id), and `get_final_output()`. Concrete adapters (LangGraphAdapter, SleepingAgentAdapter) implement recovery behavior differently.

**Heartbeat + checkpoint coordination:** Activities use "dual heartbeat pattern" — background heartbeats combined with immediate superstep checkpoints. `supports_checkpointing` property on the adapter signals whether resume-from-checkpoint is possible.

**Selective error handling:** Workflow retries exclude auth/validation errors but allow up to 5 attempts for transient failures. Comments in code distinguish recoverable vs. permanent failures.

**Activity execution discipline:** Both workflows use explicit timeout (e.g., `start_to_close_timeout=timedelta(minutes=10)`) and per-failure-type retry logic, never defaults.

### What I'd borrow
- **Adapter pattern for agent frameworks**: If Track 03 adds other agent frameworks (AutoGen, LLaMA-Index), this pattern scales without duplicating Temporal boilerplate. Document the three-file plug-in pattern ("Modify graph.py, shared.py, adapters/provider.py; runner.py stays unchanged").
- **Checkpoint-aware step iteration**: The `StepResult` + checkpoint_id pattern is a concrete way to teach incremental state capture. Useful for Lesson 09 (Temporal + observability).
- **Error taxonomy in retry policies**: Shows students the difference between transient and permanent failures — often overlooked in toy examples.

---

## Cross-cutting takeaways

1. **Naming wins clarity**: Verb-noun activity names + consistent input/output dataclass pattern make code self-documenting. No need to read function bodies to understand contracts.

2. **Adapter pattern scales agent diversity**: Both repos avoid duplicating Temporal infrastructure code. If you teach multiple agent frameworks (or multiple Pydantic AI agent patterns), an adapter layer keeps the Temporal lesson separate from the agent lesson.

3. **Query methods + explicit retry policy are teaching affordances**: Both repos expose workflow state and explain timeout/retry reasoning in README. These aren't performance optimizations; they're windows into distributed system thinking.

4. **Continue-as-new is the long-running safety valve**: Ralph Wiggum's explicit progress preservation across workflow boundaries is worth a mini-lesson. It's the answer to "what happens when a workflow runs for days?"

---

## Potential teach-forward connections (Track 02)

- **Lesson 05** (Tuning retries & timeouts): error-taxonomy retry policies from `temporal-langgraph-checkpoint-recovery` — concrete worked example of "retry transient, fail-fast on auth/validation."
- **Lesson 07** (HITL with signals): query methods from `temporal-ralph-wiggum` as a *non-blocking* observability counterpart to signals.
- **Lesson 08** (Long-running activities): dual-heartbeat + checkpoint coordination from `temporal-langgraph-checkpoint-recovery` — concrete production-grade heartbeat pattern.
- **Lesson 09** (Observability with Logfire): query methods as a complementary in-cluster observability channel alongside Logfire traces.
- **Capstones (10, 11)**: continue-as-new for multi-hour workflows; adapter pattern if a future capstone wants to plug in a non-Pydantic-AI agent framework.
