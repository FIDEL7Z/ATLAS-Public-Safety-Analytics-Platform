"""Repositório de série temporal.

DECISÃO DE DESIGN: analytics.vw_evolucao_temporal (Fase 2) é nacional — não
tem UF/município/abrangência. Como o endpoint /temporal precisa suportar
esses filtros opcionais, esta consulta agrega diretamente sobre
fact_indicadores (parametrizada, nunca SQL do usuário) em vez de usar a view
— garante um único caminho de código correto para qualquer combinação de
filtro, em vez de dois caminhos (view vs. fallback) que poderiam divergir.
Continua sendo "Analytics SQL": a agregação roda inteiramente no Postgres.

/temporal/yoy, por outro lado, usa analytics.vw_comparacao_anual_comparavel
diretamente — ela já resolve exatamente a regra de período comparável
(nunca Jan-Dez vs Jan-Jun) e não precisa de filtro geográfico no escopo desta
fase.
"""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_SERIES = text("""
    SELECT
        t.ano AS year, t.mes AS month, SUM(f.valor) AS value,
        bool_or(t.is_partial_year) AS is_partial_year
    FROM fact_indicadores f
    JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
    JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
    JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
    WHERE f.indicador_id = :indicator_id
      AND (CAST(:uf AS CHAR(2)) IS NULL OR l.uf = :uf)
      AND (CAST(:municipio AS TEXT) IS NULL OR l.municipio = :municipio)
      AND (CAST(:abrangencia AS TEXT) IS NULL OR ab.abrangencia = :abrangencia)
      AND (CAST(:ano_inicio AS SMALLINT) IS NULL OR t.ano >= :ano_inicio)
      AND (CAST(:ano_fim AS SMALLINT) IS NULL OR t.ano <= :ano_fim)
    GROUP BY t.ano, t.mes
    ORDER BY t.ano, t.mes
""")

_SELECT_YOY = text("""
    SELECT ano AS year, is_partial_year, meses_incluidos, total_periodo_comparavel AS value
    FROM analytics.vw_comparacao_anual_comparavel v
    JOIN dim_indicador i ON i.evento = v.evento
    WHERE i.indicador_id = :indicator_id
      AND ano IN (:base_year, :comparison_year)
    ORDER BY ano
""")


def get_temporal_series(
    db: Session,
    indicator_id: int,
    uf: str | None,
    municipio: str | None,
    abrangencia: str | None,
    ano_inicio: int | None,
    ano_fim: int | None,
) -> list[dict]:
    params = {
        "indicator_id": indicator_id,
        "uf": uf,
        "municipio": municipio,
        "abrangencia": abrangencia,
        "ano_inicio": ano_inicio,
        "ano_fim": ano_fim,
    }
    return [dict(row) for row in db.execute(_SELECT_SERIES, params).mappings().all()]


def get_yoy(db: Session, indicator_id: int, base_year: int, comparison_year: int) -> list[dict]:
    params = {"indicator_id": indicator_id, "base_year": base_year, "comparison_year": comparison_year}
    return [dict(row) for row in db.execute(_SELECT_YOY, params).mappings().all()]
