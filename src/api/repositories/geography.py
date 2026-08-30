"""Repositório geográfico (UF e Municípios).

Mesma decisão de design de repositories/temporal.py: analytics.vw_uf/
vw_municipio (Fase 2) não têm mês nem abrangência — como os endpoints desta
fase pedem esses filtros, a agregação roda direto sobre fact_indicadores
(parametrizada), mantendo um único caminho correto de código.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_UF = text("""
    SELECT l.uf, l.regiao, SUM(f.valor) AS value
    FROM fact_indicadores f
    JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
    JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
    JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
    WHERE f.indicador_id = :indicator_id
      AND (CAST(:ano AS SMALLINT) IS NULL OR t.ano = :ano)
      AND (CAST(:mes AS SMALLINT) IS NULL OR t.mes = :mes)
      AND (CAST(:regiao AS TEXT) IS NULL OR l.regiao = :regiao)
      AND (CAST(:abrangencia AS TEXT) IS NULL OR ab.abrangencia = :abrangencia)
    GROUP BY l.uf, l.regiao
    ORDER BY value DESC
""")

_SELECT_MUNICIPALITIES_COUNT = text("""
    SELECT COUNT(*) AS total FROM (
        SELECT l.municipio
        FROM fact_indicadores f
        JOIN dim_tempo t       ON f.tempo_id = t.tempo_id
        JOIN dim_localidade l  ON f.localidade_id = l.localidade_id
        WHERE f.indicador_id = :indicator_id
          AND (CAST(:uf AS VARCHAR) IS NULL OR l.uf = :uf)
          AND (CAST(:ano AS SMALLINT) IS NULL OR t.ano = :ano)
        GROUP BY l.uf, l.municipio
    ) sub
""")

_SELECT_MUNICIPALITIES_PAGE = text("""
    SELECT l.uf, l.municipio, SUM(f.valor) AS value
    FROM fact_indicadores f
    JOIN dim_tempo t       ON f.tempo_id = t.tempo_id
    JOIN dim_localidade l  ON f.localidade_id = l.localidade_id
    WHERE f.indicador_id = :indicator_id
      AND (CAST(:uf AS CHAR(2)) IS NULL OR l.uf = :uf)
      AND (CAST(:ano AS SMALLINT) IS NULL OR t.ano = :ano)
    GROUP BY l.uf, l.municipio
    ORDER BY value DESC, l.municipio
    LIMIT :limit OFFSET :offset
""")


def get_uf_breakdown(
    db: Session, indicator_id: int, ano: int | None, mes: int | None,
    regiao: str | None, abrangencia: str | None,
) -> list[dict]:
    params = {"indicator_id": indicator_id, "ano": ano, "mes": mes, "regiao": regiao, "abrangencia": abrangencia}
    return [dict(row) for row in db.execute(_SELECT_UF, params).mappings().all()]


def count_municipalities(db: Session, indicator_id: int, uf: str | None, ano: int | None) -> int:
    params = {"indicator_id": indicator_id, "uf": uf, "ano": ano}
    return db.execute(_SELECT_MUNICIPALITIES_COUNT, params).scalar_one()


def get_municipalities_page(
    db: Session, indicator_id: int, uf: str | None, ano: int | None, limit: int, offset: int,
) -> list[dict]:
    params = {"indicator_id": indicator_id, "uf": uf, "ano": ano, "limit": limit, "offset": offset}
    return [dict(row) for row in db.execute(_SELECT_MUNICIPALITIES_PAGE, params).mappings().all()]
