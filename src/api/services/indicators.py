from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.repositories import indicators as repo


def list_indicators(db: Session) -> tuple[list[dict], int]:
    rows = repo.list_indicators(db)
    return rows, len(rows)


def get_indicator(db: Session, indicator_id: int) -> dict:
    row = repo.get_indicator(db, indicator_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")
    return row
