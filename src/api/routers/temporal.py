from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas.common import ErrorResponse
from src.api.schemas.temporal import TemporalResponse, YoYResponse
from src.api.services import temporal as service

router = APIRouter(prefix="/api/v1", tags=["temporal"])


@router.get(
    "/temporal",
    response_model=TemporalResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Série temporal mensal de um indicador",
)
def get_temporal(
    indicator_id: int = Query(..., description="Indicador obrigatório — a série é sempre de uma única unidade"),
    uf: str | None = Query(None, min_length=2, max_length=2),
    municipio: str | None = Query(None),
    abrangencia: str | None = Query(None),
    ano_inicio: int | None = Query(None, ge=2000, le=2100),
    ano_fim: int | None = Query(None, ge=2000, le=2100),
    db: Session = Depends(get_db),
) -> TemporalResponse:
    result = service.get_temporal_series(
        db, indicator_id, uf.upper() if uf else None, municipio, abrangencia, ano_inicio, ano_fim
    )
    return TemporalResponse(**result)


@router.get(
    "/temporal/yoy",
    response_model=YoYResponse,
    responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}},
    summary="Comparação ano a ano, sempre em período comparável",
    description=(
        "Nunca compara Jan-Dez de um ano com Jan-Jun de outro: months_compared é o "
        "menor corte de meses entre os dois anos comparados (regra herdada de "
        "analytics.vw_comparacao_anual_comparavel, Fase 2)."
    ),
)
def get_yoy(
    indicator_id: int = Query(...),
    base_year: int | None = Query(None, description="Padrão: comparison_year - 1"),
    comparison_year: int | None = Query(None, description="Padrão: o último ano disponível"),
    db: Session = Depends(get_db),
) -> YoYResponse:
    result = service.get_yoy(db, indicator_id, base_year, comparison_year)
    return YoYResponse(**result)
