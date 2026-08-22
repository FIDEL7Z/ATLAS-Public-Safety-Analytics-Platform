from sqlalchemy.orm import Session

from src.api.repositories import radar as repo


def get_radar(db: Session, indicator_id: int | None, ano: int | None, min_abs_z: float | None, limit: int) -> dict:
    # z-score é estatisticamente comparável ENTRE indicadores de famílias
    # diferentes (é um desvio padronizado, não um valor bruto) — por isso
    # este endpoint, ao contrário de /kpis, pode legitimamente retornar
    # indicadores de unidades diferentes juntos. Ver docs/API.md.
    data = repo.get_radar(db, indicator_id, ano, min_abs_z, limit)
    return {"data": data, "total": len(data)}
