from pydantic import BaseModel, Field


class IndicatorResponse(BaseModel):
    id: int = Field(..., description="indicador_id")
    evento: str
    familia_medida: str = Field(..., description="'vitima' | 'contagem' | 'peso'")
    unidade: str
    tipo_indicador: str
    grupo_semantico: str = Field(
        ..., description="Vítimas | Ações Policiais | Ocorrências | Apreensões (Peso) | Apreensões (Unidade) | Serviços"
    )


class IndicatorListResponse(BaseModel):
    data: list[IndicatorResponse]
    total: int
