# Lesson 03 — Structured output

**Code:** `03_structured_output.py`

## Goal
Force the model to return a validated Pydantic model instead of free text.

## Why it matters
Free text means downstream code has to parse, regex, and pray. With `output_type=`, the model is given a JSON schema and pydantic-ai validates the response before you ever see it. Your call site gets a fully typed object.

## Mental model
Setting `output_type=YourModel` swaps the model's job from "produce text" to "fill this schema". Behind the scenes, pydantic-ai registers a hidden `final_result` tool whose schema mirrors your model — the model "calls" that tool with the answer, and pydantic-ai validates the args into a `YourModel` instance.

## Walk the code

**`CityLocation`** is just a Pydantic `BaseModel`. `Field(description=...)` text is included in the schema sent to the model, so it actually shapes the answer.

```python
class CityLocation(BaseModel):
    city: str
    country: str
    latitude: float = Field(description="Decimal degrees, north positive.")
    longitude: float = Field(description="Decimal degrees, east positive.")
```

**`agent`** is constructed with `output_type=CityLocation`. No tools, no special config — the type alone is the contract.

```python
agent = Agent(FLASH, output_type=CityLocation)
```

**`result.output`** comes back already validated; assigning it to a typed local makes the editor's intellisense fully aware of the shape (`out.latitude` is a `float`).

```python
out: CityLocation = result.output
```

## Run
```bash
uv run python 03_structured_output.py
```
Expected: `London, United Kingdom (51.51, -0.13)`.

## Try it
1. Add a `population: int` field with a `Field(ge=0)` constraint. Rerun and check the value looks sane.
2. Make `latitude` and `longitude` required-but-bounded: `Field(ge=-90, le=90)`, `Field(ge=-180, le=180)`. If the model returns nonsense, pydantic-ai will raise.
3. Change `output_type=` to `list[CityLocation]` and ask for "all cities that have hosted the Summer Olympics since 2000". You get a typed list back.

## Gotchas
- **`str` in a union opens an escape hatch.** `output_type=CityLocation | str` lets the model bail out to free text. If you want to *force* structure, omit `str`.
- **Description fields matter.** A `Field(description="decimal degrees, north positive")` significantly reduces ambiguous answers. Treat them as part of the prompt.
- **Don't over-spec.** Asking for 30 fields in one model burns tokens and increases failure rate. If you have a complex shape, decompose with tools (lesson 03).

## Bridge
Structured *output* is half the story. Lesson 04 gives the agent structured *capability* — tools it can call mid-run.
