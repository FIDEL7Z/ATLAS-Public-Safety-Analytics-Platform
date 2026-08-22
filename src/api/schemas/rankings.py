from pydantic import BaseModel


class RankingUFItem(BaseModel):
    rank: int
    uf: str
    regiao: str
    value: float


class RankingUFResponse(BaseModel):
    indicator: str
    indicator_id: int
    unit: str
    ano: int
    data: list[RankingUFItem]


class RankingMunicipalityItem(BaseModel):
    rank: int
    uf: str
    municipio: str
    value: float


class RankingMunicipalityResponse(BaseModel):
    indicator: str
    indicator_id: int
    unit: str
    ano: int
    data: list[RankingMunicipalityItem]


class RankingIndicatorItem(BaseModel):
    rank: int
    evento: str
    grupo_semantico: str
    value: float


class RankingIndicatorResponse(BaseModel):
    grupo_semantico: str
    ano: int
    data: list[RankingIndicatorItem]
