"""Repositório de KPIs.

Nenhuma view da Fase 2 cobre a combinação livre de filtros pedida aqui
(indicator_id + uf + municipio + ano + abrangencia simultâneos) — a Fase 2 já
documentou (docs/ANALYTICS_MODEL.md) que suas views agregam por um grão fixo.
Em vez de recalcular em pandas, a agregação continua acontecendo no Postgres:
esta é uma consulta SQL parametrizada (nunca SQL vindo do usuário — todo
valor é bind parameter) contra fact_indicadores + dimensões, sempre agrupada
por indicador (nunca soma entre indicadores de família/unidade diferentes).
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_KPIS = text("""
    SELECT
        i.indicador_id, i.evento AS indicator, i.familia_medida,
        i.unidade AS unit, SUM(f.valor) AS value, COUNT(*) AS n_registros
    FROM fact_indicadores f
    JOIN dim_indicador i   ON f.indicador_id = i.indicador_id
    JOIN dim_tempo t       ON f.tempo_id = t.tempo_id
    JOIN dim_localidade l  ON f.localidade_id = l.localidade_id
    JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
    WHERE (CAST(:indicator_id AS INTEGER) IS NULL OR i.indicador_id = :indicator_id)
      AND (CAST(:uf AS VARCHAR) IS NULL OR l.uf = :uf)
      AND (CAST(:municipio AS TEXT) IS NULL OR l.municipio = :municipio)
      AND (CAST(:ano AS SMALLINT) IS NULL OR t.ano = :ano)
      AND (CAST(:abrangencia AS TEXT) IS NULL OR ab.abrangencia = :abrangencia)
    GROUP BY i.indicador_id, i.evento, i.familia_medida, i.unidade
    ORDER BY i.evento
""")


def get_kpis(
    db: Session,
    indicator_id: int | None,
    uf: str | None,
    municipio: str | None,
    ano: int | None,
    abrangencia: str | None,
) -> list[dict]:
    params = {
        "indicator_id": indicator_id,
        "uf": uf,
        "municipio": municipio,
        "ano": ano,
        "abrangencia": abrangencia,
    }
    return [dict(row) for row in db.execute(_SELECT_KPIS, params).mappings().all()]
