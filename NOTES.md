

 - [ ] what is this used for: tracks/02-temporal/docker
 - [ ] are pydantic-ai capabilties analagous to langchain/langgraph middleware?
 - [ ] how do we implement agents (pydantic-ai or otherwise) having middleware in temporal?





---
learning pydantic-ai

docs: https://pydantic.dev/docs/ai/overview/






### temporal server - ui

includes:
- workflows
- schedules
- batch
- deployments
- archive
- namespaces


![temporal codec server architecture](assets/temporal-code-server-arch.png)


### using the cli/repl built into pydantic-ai

```sh
# set api key in shell
export ANTHROPIC_API_KEY=...


# start repl with specific provider/model 
uv run pai -m anthropic:claude-opus-4-7

```