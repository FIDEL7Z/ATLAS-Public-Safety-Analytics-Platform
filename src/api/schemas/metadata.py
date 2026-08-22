"""Schemas de metadados. Não listado explicitamente na estrutura de pastas da
Fase 5 (que só previa schemas/{common,indicators,kpis,temporal,geography,
rankings,radar}.py), mas criado para manter o mesmo padrão Router→Service→
Repository→Schema em /metadata — colocar isso em common.py misturaria
conceitos não relacionados (erro/paginação vs. metadados do dataset)."""
from pydantic import BaseModel, Field


class DatasetInfo(BaseModel):
    start: str = Field(..., description="AAAA-MM do primeiro mês disponível")
    end: str = Field(..., description="AAAA-MM do último mês disponível")
    partial_year: bool = Field(..., description="TRUE se o último ano do período está incompleto")


class CoverageInfo(BaseModel):
    indicators: int
    ufs: int
    municipalities: int


class MetadataResponse(BaseModel):
    dataset: DatasetInfo
    coverage: CoverageInfo


class UFOption(BaseModel):
    uf: str
    regiao: str


class AbrangenciaOption(BaseModel):
    abrangencia: str


class MunicipalityOption(BaseModel):
    uf: str
    municipio: str
