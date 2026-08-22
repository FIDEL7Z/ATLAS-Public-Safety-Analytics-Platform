from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas.common import ErrorResponse
from src.api.schemas.rankings import RankingIndicatorResponse, RankingMunicipalityResponse, RankingUFResponse
from src.api.services import rankings as service

router = APIRouter(prefix="/api/v1/rankings", tags=["rankings"])


@router.get(
    "/uf",
    response_model=RankingUFResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Ranking de UFs por indicador/ano",
)
def ranking_uf(
    indicator_id: int = Query(...),
    ano: int = Query(...),
    limit: int = Query(10, ge=1, le=27, description="Máximo 27 (número de UFs)"),
    db: Session = Depends(get_db),
) -> RankingUFResponse:
    return RankingUFResponse(**service.get_ranking_uf(db, indicator_id, ano, limit))


@router.get(
    "/municipalities",
    response_model=RankingMunicipalityResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Ranking de municípios por indicador/ano",
)
def ranking_municipalities(
    indicator_id: int = Query(...),
    ano: int = Query(...),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> RankingMunicipalityResponse:
    return RankingMunicipalityResponse(**service.get_ranking_municipality(db, indicator_id, ano, limit))


@router.get(
    "/indicators",
    response_model=RankingIndicatorResponse,
    responses={400: {"model": ErrorResponse}},
    summary="Ranking de indicadores dentro do mesmo grupo semântico",
    description=(
        "Ranking SEMPRE dentro de um único grupo_semantico (Vítimas, Ocorrências, "
        "Ações Policiais, Apreensões (Peso), Apreensões (Unidade) ou Serviços) — "
        "nunca cross-grupo, porque as unidades diferem entre grupos."
    ),
)
def ranking_indicators(
    grupo_semantico: str = Query(..., description="Ex.: 'Vítimas'"),
    ano: int = Query(...),
    limit: int = Query(10, ge=1, le=31),
    db: Session = Depends(get_db),
) -> RankingIndicatorResponse:
    return RankingIndicatorResponse(**service.get_ranking_indicator(db, grupo_semantico, ano, limit))
