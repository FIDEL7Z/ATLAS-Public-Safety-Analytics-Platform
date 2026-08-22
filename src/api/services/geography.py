from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.config import settings
from src.api.repositories import indicators as indicators_repo
from src.api.repositories import geography as repo


def _require_indicator(db: Session, indicator_id: int) -> dict:
    indicator = indicators_repo.get_indicator(db, indicator_id)
    if indicator is None:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")
    return indicator


def get_uf_breakdown(
    db: Session, indicator_id: int, ano: int | None, mes: int | None,
    regiao: str | None, abrangencia: str | None,
) -> dict:
    indicator = _require_indicator(db, indicator_id)
    data = repo.get_uf_breakdown(db, indicator_id, ano, mes, regiao, abrangencia)
    return {
        "indicator": indicator["evento"],
        "indicator_id": indicator_id,
        "unit": indicator["unidade"],
        "data": data,
    }


def get_municipalities(
    db: Session, indicator_id: int, uf: str | None, ano: int | None, page: int, page_size: int,
) -> dict:
    indicator = _require_indicator(db, indicator_id)
    page_size = min(page_size, settings.max_page_size)
    total = repo.count_municipalities(db, indicator_id, uf, ano)
    data = repo.get_municipalities_page(db, indicator_id, uf, ano, limit=page_size, offset=(page - 1) * page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "indicator": indicator["evento"],
        "indicator_id": indicator_id,
        "unit": indicator["unidade"],
        "data": data,
    }
