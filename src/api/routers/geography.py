from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import PageParams, get_db
from src.api.schemas.common import ErrorResponse
from src.api.schemas.geography import MunicipalityResponse, UFResponse
from src.api.services import geography as service

router = APIRouter(prefix="/api/v1/geography", tags=["geography"])


@router.get(
    "/uf",
    response_model=UFResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Totais por UF de um indicador",
)
def get_uf(
    indicator_id: int = Query(...),
    ano: int | None = Query(None, ge=2000, le=2100),
    mes: int | None = Query(None, ge=1, le=12),
    regiao: str | None = Query(None),
    abrangencia: str | None = Query(None),
    db: Session = Depends(get_db),
) -> UFResponse:
    result = service.get_uf_breakdown(db, indicator_id, ano, mes, regiao, abrangencia)
    return UFResponse(**result)


@router.get(
    "/municipalities",
    response_model=MunicipalityResponse,
    responses={404: {"model": ErrorResponse}},
    summary="Totais por município de um indicador (paginado)",
)
def get_municipalities(
    indicator_id: int = Query(...),
    uf: str | None = Query(None, min_length=2, max_length=2),
    ano: int | None = Query(None, ge=2000, le=2100),
    page_params: PageParams = Depends(),
    db: Session = Depends(get_db),
) -> MunicipalityResponse:
    result = service.get_municipalities(
        db, indicator_id, uf.upper() if uf else None, ano, page_params.page, page_params.page_size
    )
    return MunicipalityResponse(**result)
