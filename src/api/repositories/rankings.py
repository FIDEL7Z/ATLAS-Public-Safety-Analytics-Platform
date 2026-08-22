"""Repositório de rankings — reusa as views prontas da Fase 2
(analytics.vw_ranking_uf / vw_ranking_municipio / vw_ranking_indicador) sem
reimplementar a lógica de RANK() aqui. Elas já cobrem exatamente os filtros
pedidos nesta fase (indicator_id/ano/limit; grupo_semantico/ano/limit)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_RANKING_UF = text("""
    SELECT ranking AS rank, uf, regiao, total AS value
    FROM analytics.vw_ranking_uf v
    JOIN dim_indicador i ON i.evento = v.evento
    WHERE i.indicador_id = :indicator_id AND v.ano = :ano
    ORDER BY ranking
    LIMIT :limit
""")

_SELECT_RANKING_MUNICIPALITY = text("""
    SELECT ranking AS rank, uf, municipio, total AS value
    FROM analytics.vw_ranking_municipio v
    JOIN dim_indicador i ON i.evento = v.evento
    WHERE i.indicador_id = :indicator_id AND v.ano = :ano
    ORDER BY ranking
    LIMIT :limit
""")

_SELECT_RANKING_INDICATOR = text("""
    SELECT ranking AS rank, evento, grupo_semantico, total AS value
    FROM analytics.vw_ranking_indicador
    WHERE grupo_semantico = :grupo_semantico AND ano = :ano
    ORDER BY ranking
    LIMIT :limit
""")


def get_ranking_uf(db: Session, indicator_id: int, ano: int, limit: int) -> list[dict]:
    params = {"indicator_id": indicator_id, "ano": ano, "limit": limit}
    return [dict(row) for row in db.execute(_SELECT_RANKING_UF, params).mappings().all()]


def get_ranking_municipality(db: Session, indicator_id: int, ano: int, limit: int) -> list[dict]:
    params = {"indicator_id": indicator_id, "ano": ano, "limit": limit}
    return [dict(row) for row in db.execute(_SELECT_RANKING_MUNICIPALITY, params).mappings().all()]


def get_ranking_indicator(db: Session, grupo_semantico: str, ano: int, limit: int) -> list[dict]:
    params = {"grupo_semantico": grupo_semantico, "ano": ano, "limit": limit}
    return [dict(row) for row in db.execute(_SELECT_RANKING_INDICATOR, params).mappings().all()]
