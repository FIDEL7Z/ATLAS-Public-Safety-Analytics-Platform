from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.api.dependencies import get_db
from src.api.schemas.kpis import KPIItem, KPIResponse
from src.api.services import kpis as service

router = APIRouter(prefix="/api/v1", tags=["kpis"])


@router.get(
    "/kpis",
    response_model=KPIResponse,
    summary="KPIs agregados por indicador, com filtros opcionais",
    description=(
        "Cada item da resposta pertence a UM indicador só — a API nunca soma "
        "pessoas + ocorrências + kg num único total, mesmo sem indicator_id informado."
    ),
)
def get_kpis(
    indicator_id: int | None = Query(None, description="Filtra por um indicador"),
    uf: str | None = Query(None, min_length=2, max_length=2, description="Sigla da UF, ex.: PB"),
    municipio: str | None = Query(None, description="Nome do município"),
    ano: int | None = Query(None, ge=2000, le=2100),
    abrangencia: str | None = Query(None, description="Estadual | Polícia Federal | Polícia Rodoviária Federal"),
    db: Session = Depends(get_db),
) -> KPIResponse:
    rows = service.get_kpis(db, indicator_id, uf.upper() if uf else None, municipio, ano, abrangencia)
    return KPIResponse(
        filters={"indicator_id": indicator_id, "uf": uf, "municipio": municipio, "ano": ano, "abrangencia": abrangencia},
        data=[
            KPIItem(
                indicator_id=r["indicador_id"], indicator=r["indicator"], familia_medida=r["familia_medida"],
                value=float(r["value"]), unit=r["unit"], n_registros=r["n_registros"],
            )
            for r in rows
        ],
    )
