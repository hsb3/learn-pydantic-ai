# Lesson 12 — YAML specs + lifecycle hooks

**Code:** `examples/12_yaml_agent_with_hooks.py`, `examples/agent.yaml`

## Goal
Load an agent's configuration from YAML (template strings, capabilities, model) and attach `Hooks` for lifecycle observability.

## Why it matters
**YAML** lets non-engineers — PMs, ops, prompt engineers — tune prompts and capability bundles without touching Python. Same code, multiple agents, version-controlled prompts.

**Hooks** let you observe and intercept the agent loop without subclassing: log every model request, audit dangerous tool calls, redact PII, trap errors. They're the production toolkit that turns a prototype into something you can run with eyes open.

## Mental model
`Agent.from_file('agent.yaml', deps_type=…)` constructs an `Agent` from a spec. Template strings like `{{ user_name }}` in `instructions` are interpolated from `deps` at each run. YAML and Python *coexist* — anything you can pass to `Agent(...)` (deps_type, tools, additional capabilities) you can layer on top of the YAML.

`Hooks` is itself a capability. Inside, `@hooks.on.before_model_request`, `@hooks.on.before_tool_execute`, `@hooks.on.run_error`, etc., register callbacks for specific lifecycle events.

## Walk the code
- `examples/agent.yaml` — model, instructions with `{{ user_name }}` and `{{ today }}` template variables, a Thinking capability declared declaratively.
- `examples/12_yaml_agent_with_hooks.py:41` — `Hooks()` instance.
- `examples/12_yaml_agent_with_hooks.py:44` — `@hooks.on.before_model_request` decorator. The handler receives `RunContext[DepsT]` and a mutable `ModelRequestContext`, can transform or short-circuit the request, and must return the (possibly modified) context.
- `examples/12_yaml_agent_with_hooks.py:53` — `@hooks.on.run_error` — fires on uncaught exceptions in the run.
- `examples/12_yaml_agent_with_hooks.py:59` — `Agent.from_file(..., deps_type=UserContext, capabilities=[hooks])`. YAML capabilities + Python `Hooks` capability are merged.

## Run
```bash
uv run python examples/12_yaml_agent_with_hooks.py
```
Expected: `[hook] sending 1 messages to model`, a `---`, then a one-paragraph reply addressing the user by name.

## Try it
1. Change `effort: low` to `effort: high` in the YAML. Rerun — no Python edits needed. This is the YAML payoff.
2. Add `@hooks.on.before_tool_execute(tools=['some_tool_name'])` and a dummy `@agent.tool`. Use it as an audit log for which tools fire.
3. Move the entire agent definition into the YAML — replace the static instructions with template strings, add a Thinking and a WebSearch capability there. Then the Python file is just `Agent.from_file(...)` plus your hooks.

## Gotchas
- **Hook decorator names on `.on` don't repeat `on_`.** Use `hooks.on.run_error`, not `hooks.on.on_run_error`. The error is unintuitive — be careful.
- **Template strings need matching deps fields.** `{{ user_name }}` requires `deps.user_name` to exist. Missing fields raise at run time, not load time.
- **`Agent.from_file` returns a less-typed agent.** YAML loses the static generics — output type defaults to `str` and deps to `Any` unless you pass them explicitly. Lean on `deps_type=` and `output_type=` on `from_file()` if you want type checking back.

## Next
You've completed the curriculum. Re-read [00-orientation](./00-orientation.md) — the vocabulary section will read very differently now. From here, the productive next steps are: real Logfire integration (`logfire.instrument_pydantic_ai()`), MCP servers, the `ProcessHistory` capability for long conversations, and `iter()` for step-by-step control of the agent loop.
