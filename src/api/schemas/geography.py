from pydantic import BaseModel


class UFItem(BaseModel):
    uf: str
    regiao: str
    value: float


class UFResponse(BaseModel):
    indicator: str
    indicator_id: int
    unit: str
    data: list[UFItem]


class MunicipalityItem(BaseModel):
    uf: str
    municipio: str
    value: float


class MunicipalityResponse(BaseModel):
    page: int
    page_size: int
    total: int
    indicator: str
    indicator_id: int
    unit: str
    data: list[MunicipalityItem]
