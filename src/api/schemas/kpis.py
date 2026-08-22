from pydantic import BaseModel, Field


class KPIFiltersEcho(BaseModel):
    indicator_id: int | None = None
    uf: str | None = None
    municipio: str | None = None
    ano: int | None = None
    abrangencia: str | None = None


class KPIItem(BaseModel):
    indicator_id: int
    indicator: str = Field(..., description="evento")
    familia_medida: str
    value: float
    unit: str
    n_registros: int = Field(..., description="Quantidade de linhas de fato somadas neste valor")


class KPIResponse(BaseModel):
    filters: KPIFiltersEcho
    data: list[KPIItem]
