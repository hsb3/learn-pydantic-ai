"""03 — Structured output.

Force the model to return a typed Pydantic model instead of free text by
passing `output_type=` to the Agent. The model is given a schema and must
fill it; `result.output` is then a validated instance of that model.

Why this matters: parsing free text is brittle. Schema-constrained output
gives you something you can pass to the rest of your program with confidence.
"""

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from _common import FLASH


class CityLocation(BaseModel):
    city: str
    country: str
    latitude: float = Field(description="Decimal degrees, north positive.")
    longitude: float = Field(description="Decimal degrees, east positive.")


agent = Agent(FLASH, output_type=CityLocation)


def main() -> None:
    result = agent.run_sync("Where were the 2012 Summer Olympics held?")
    # result.output is a CityLocation — fully typed.
    out: CityLocation = result.output
    print(f"{out.city}, {out.country}  ({out.latitude:.2f}, {out.longitude:.2f})")
    print("---")
    print(result.usage)


if __name__ == "__main__":
    main()
