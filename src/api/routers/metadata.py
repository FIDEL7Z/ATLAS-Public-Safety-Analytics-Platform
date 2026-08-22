from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas.metadata import (
    AbrangenciaOption,
    MetadataResponse,
    MunicipalityOption,
    UFOption,
)
from src.api.services import metadata as service

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.get("", response_model=MetadataResponse, summary="Visão geral do dataset (período, cobertura, ano parcial)")
def get_metadata(db: Session = Depends(get_db)) -> MetadataResponse:
    return MetadataResponse(**service.get_metadata(db))


@router.get("/ufs", response_model=list[UFOption], summary="UFs disponíveis para filtro")
def list_ufs(db: Session = Depends(get_db)) -> list[UFOption]:
    return [UFOption(**r) for r in service.list_ufs(db)]


@router.get("/years", response_model=list[int], summary="Anos disponíveis para filtro")
def list_years(db: Session = Depends(get_db)) -> list[int]:
    return service.list_years(db)


@router.get("/abrangencias", response_model=list[AbrangenciaOption], summary="Abrangências disponíveis para filtro")
def list_abrangencias(db: Session = Depends(get_db)) -> list[AbrangenciaOption]:
    return [AbrangenciaOption(**r) for r in service.list_abrangencias(db)]


@router.get("/municipalities", response_model=list[MunicipalityOption], summary="Municípios disponíveis para filtro")
def list_municipalities(
    uf: str | None = Query(None, min_length=2, max_length=2),
    db: Session = Depends(get_db),
) -> list[MunicipalityOption]:
    return [MunicipalityOption(**r) for r in service.list_municipalities(db, uf.upper() if uf else None)]
