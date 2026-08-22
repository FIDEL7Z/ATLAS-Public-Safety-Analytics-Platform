from pydantic import BaseModel, Field


class RadarItem(BaseModel):
    indicator: str
    year: int
    month: int
    value: float
    historical_mean: float
    standard_deviation: float
    z_score: float | None = Field(
        None, description="Desvio padronizado — NÃO implica causalidade. Ver docs/API.md."
    )


class RadarResponse(BaseModel):
    data: list[RadarItem]
    total: int
