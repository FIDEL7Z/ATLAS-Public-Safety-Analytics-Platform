from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas.common import ErrorResponse
from src.api.schemas.indicators import IndicatorListResponse, IndicatorResponse
from src.api.services import indicators as service

router = APIRouter(prefix="/api/v1", tags=["indicators"])


def _to_response(row: dict) -> IndicatorResponse:
    return IndicatorResponse(
        id=row["indicador_id"],
        evento=row["evento"],
        familia_medida=row["familia_medida"],
        unidade=row["unidade"],
        tipo_indicador=row["tipo_indicador"],
        grupo_semantico=row["grupo_semantico"],
    )


@router.get(
    "/indicators",
    response_model=IndicatorListResponse,
    summary="Lista os indicadores disponíveis",
    description="Retorna os 31 indicadores do Sinesp VDE, lidos de analytics.vw_dim_indicador — nunca uma lista fixa no código.",
)
def list_indicators(db: Session = Depends(get_db)) -> IndicatorListResponse:
    rows, total = service.list_indicators(db)
    return IndicatorListResponse(data=[_to_response(r) for r in rows], total=total)


@router.get(
    "/indicators/{indicator_id}",
    response_model=IndicatorResponse,
    responses={404: {"model": ErrorResponse, "description": "Indicador não encontrado"}},
    summary="Metadados de um indicador específico",
)
def get_indicator(indicator_id: int, db: Session = Depends(get_db)) -> IndicatorResponse:
    row = service.get_indicator(db, indicator_id)
    return _to_response(row)
