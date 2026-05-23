"""03 — Structured output.

Force the model to return a typed Pydantic model instead of free text by
passing `output_type=` to the Agent. The model is given a schema and must
fill it; `result.output` is then a validated instance of that model.

Why this matters: parsing free text is brittle. Schema-constrained output
gives you something you can pass to the rest of your program with confidence.
"""
from pydantic_ai.run import AgentRunResult

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from learn_pydantic_ai import FLASH


class CityLocation(BaseModel):
    city: str
    country: str
    latitude: float = Field(description="Decimal degrees, north positive.")
    longitude: float = Field(description="Decimal degrees, east positive.")


agent = Agent(FLASH, output_type=CityLocation)


def main() -> None:
    prompt = "Where were the 2012 Summer Olympics held?"
    result: AgentRunResult[str] = agent.run_sync(user_prompt=prompt)
    # result.output is a CityLocation — fully typed.
    out: CityLocation = result.output
    print("user:\n", prompt, "\n")
    print("-" * 40)

    print("ai:\n", f"{out.city}, {out.country}  ({out.latitude:.2f}, {out.longitude:.2f})", "\n")
    print("-" * 40)
    print("result.usage:\n", result.usage)


if __name__ == "__main__":
    main()
