"""Repositório de indicadores — lê de analytics.vw_dim_indicador (Fase 3),
que já carrega grupo_semantico. Nenhuma lista hardcoded (regra 10 da Fase 5)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_ALL = text("""
    SELECT indicador_id, evento, familia_medida, unidade, tipo_indicador, grupo_semantico
    FROM analytics.vw_dim_indicador
    ORDER BY evento
""")

_SELECT_ONE = text("""
    SELECT indicador_id, evento, familia_medida, unidade, tipo_indicador, grupo_semantico
    FROM analytics.vw_dim_indicador
    WHERE indicador_id = :indicator_id
""")


def list_indicators(db: Session) -> list[dict]:
    return [dict(row) for row in db.execute(_SELECT_ALL).mappings().all()]


def get_indicator(db: Session, indicator_id: int) -> dict | None:
    row = db.execute(_SELECT_ONE, {"indicator_id": indicator_id}).mappings().first()
    return dict(row) if row else None
