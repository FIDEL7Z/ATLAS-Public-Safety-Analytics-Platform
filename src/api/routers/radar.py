from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas.radar import RadarResponse
from src.api.services import radar as service

router = APIRouter(prefix="/api/v1", tags=["radar"])


@router.get(
    "/radar",
    response_model=RadarResponse,
    summary="Radar analítico — desvios em relação à média histórica de cada indicador",
    description=(
        "z_score é um valor estatístico (desvio padronizado). A API não afirma "
        "causalidade nem rotula um valor como 'crime', 'causa' ou 'problema' — "
        "a interpretação é responsabilidade de quem consome a API. Ver docs/API.md."
    ),
)
def get_radar(
    indicator_id: int | None = Query(None),
    ano: int | None = Query(None, ge=2000, le=2100),
    min_abs_z: float | None = Query(None, ge=0, description="Só retorna |z_score| >= este valor"),
    limit: int = Query(50, ge=1, le=930, description="Máximo = nº de indicadores x meses disponíveis"),
    db: Session = Depends(get_db),
) -> RadarResponse:
    return RadarResponse(**service.get_radar(db, indicator_id, ano, min_abs_z, limit))
