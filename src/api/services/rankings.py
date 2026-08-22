from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.repositories import indicators as indicators_repo
from src.api.repositories import rankings as repo

VALID_GRUPOS_SEMANTICOS = {
    "Vítimas", "Ações Policiais", "Ocorrências",
    "Apreensões (Peso)", "Apreensões (Unidade)", "Serviços",
}


def _require_indicator(db: Session, indicator_id: int) -> dict:
    indicator = indicators_repo.get_indicator(db, indicator_id)
    if indicator is None:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")
    return indicator


def get_ranking_uf(db: Session, indicator_id: int, ano: int, limit: int) -> dict:
    indicator = _require_indicator(db, indicator_id)
    data = repo.get_ranking_uf(db, indicator_id, ano, limit)
    return {"indicator": indicator["evento"], "indicator_id": indicator_id, "unit": indicator["unidade"], "ano": ano, "data": data}


def get_ranking_municipality(db: Session, indicator_id: int, ano: int, limit: int) -> dict:
    indicator = _require_indicator(db, indicator_id)
    data = repo.get_ranking_municipality(db, indicator_id, ano, limit)
    return {"indicator": indicator["evento"], "indicator_id": indicator_id, "unit": indicator["unidade"], "ano": ano, "data": data}


def get_ranking_indicator(db: Session, grupo_semantico: str, ano: int, limit: int) -> dict:
    if grupo_semantico not in VALID_GRUPOS_SEMANTICOS:
        raise HTTPException(
            status_code=400,
            detail=f"grupo_semantico inválido. Valores aceitos: {sorted(VALID_GRUPOS_SEMANTICOS)}",
        )
    data = repo.get_ranking_indicator(db, grupo_semantico, ano, limit)
    return {"grupo_semantico": grupo_semantico, "ano": ano, "data": data}
