from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.api.repositories import indicators as indicators_repo
from src.api.repositories import temporal as repo


def get_temporal_series(
    db: Session,
    indicator_id: int,
    uf: str | None,
    municipio: str | None,
    abrangencia: str | None,
    ano_inicio: int | None,
    ano_fim: int | None,
) -> dict:
    indicator = indicators_repo.get_indicator(db, indicator_id)
    if indicator is None:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")

    points = repo.get_temporal_series(db, indicator_id, uf, municipio, abrangencia, ano_inicio, ano_fim)
    return {
        "indicator": indicator["evento"],
        "indicator_id": indicator_id,
        "familia_medida": indicator["familia_medida"],
        "unit": indicator["unidade"],
        "data": points,
    }


def get_yoy(db: Session, indicator_id: int, base_year: int | None, comparison_year: int | None) -> dict:
    indicator = indicators_repo.get_indicator(db, indicator_id)
    if indicator is None:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")

    if comparison_year is None:
        comparison_year = max(row["year"] for row in repo.get_temporal_series(db, indicator_id, None, None, None, None, None))
    if base_year is None:
        base_year = comparison_year - 1

    rows = repo.get_yoy(db, indicator_id, base_year, comparison_year)
    by_year = {r["year"]: r for r in rows}

    if base_year not in by_year or comparison_year not in by_year:
        raise HTTPException(
            status_code=400,
            detail=f"Não há dados suficientes para comparar {base_year} e {comparison_year} para este indicador",
        )

    base_row = by_year[base_year]
    comp_row = by_year[comparison_year]
    base_value = float(base_row["value"])
    comp_value = float(comp_row["value"])
    variation_abs = comp_value - base_value
    variation_pct = (variation_abs / base_value * 100) if base_value else None

    return {
        "indicator": indicator["evento"],
        "indicator_id": indicator_id,
        "unit": indicator["unidade"],
        "base_value": base_value,
        "comparison_value": comp_value,
        "variation_absolute": variation_abs,
        "variation_percent": round(variation_pct, 2) if variation_pct is not None else None,
        "comparison": {
            "base_year": base_year,
            "comparison_year": comparison_year,
            # meses_incluidos é o MESMO corte para os dois anos (a view já
            # garante isso) — nunca Jan-Dez de um ano vs Jan-Jun de outro.
            "months_compared": comp_row["meses_incluidos"],
            "partial_period": bool(base_row["is_partial_year"] or comp_row["is_partial_year"]),
        },
    }
