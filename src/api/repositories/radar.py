"""Repositório do radar analítico — reusa analytics.vw_desvio_media_historica
(Fase 2) sem recalcular z-score em Python. Suporta filtro opcional por
indicador, ano e |z-score| mínimo (para "maiores anomalias primeiro")."""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_RADAR = text("""
    SELECT
        v.evento AS indicator, v.ano AS year, v.mes AS month, v.total AS value,
        v.media_historica AS historical_mean, v.desvio_padrao_historico AS standard_deviation,
        v.z_score
    FROM analytics.vw_desvio_media_historica v
    JOIN dim_indicador i ON i.evento = v.evento
    WHERE (CAST(:indicator_id AS INTEGER) IS NULL OR i.indicador_id = :indicator_id)
      AND (CAST(:ano AS SMALLINT) IS NULL OR v.ano = :ano)
      AND (CAST(:min_abs_z AS DOUBLE PRECISION) IS NULL OR ABS(v.z_score) >= :min_abs_z)
    ORDER BY ABS(v.z_score) DESC NULLS LAST
    LIMIT :limit
""")


def get_radar(
    db: Session, indicator_id: int | None, ano: int | None, min_abs_z: float | None, limit: int,
) -> list[dict]:
    params = {"indicator_id": indicator_id, "ano": ano, "min_abs_z": min_abs_z, "limit": limit}
    return [dict(row) for row in db.execute(_SELECT_RADAR, params).mappings().all()]
