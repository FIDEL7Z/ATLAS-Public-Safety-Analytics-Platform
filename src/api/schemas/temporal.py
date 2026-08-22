from pydantic import BaseModel, Field


class TemporalPoint(BaseModel):
    year: int
    month: int
    value: float
    is_partial_year: bool = Field(..., description="TRUE quando o ano deste ponto está incompleto na fonte")


class TemporalResponse(BaseModel):
    indicator: str
    indicator_id: int
    familia_medida: str
    unit: str
    data: list[TemporalPoint]


class YoYComparison(BaseModel):
    base_year: int
    comparison_year: int
    months_compared: int = Field(..., description="Meses incluídos na comparação (o corte comparável, nunca 12 vs 6)")
    partial_period: bool = Field(..., description="TRUE se um dos dois anos comparados é parcial")


class YoYResponse(BaseModel):
    indicator: str
    indicator_id: int
    unit: str
    base_value: float
    comparison_value: float
    variation_absolute: float
    variation_percent: float | None
    comparison: YoYComparison
