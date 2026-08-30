"""Fase 6 — Paridade PostgreSQL (Development) × DuckDB (Production).

Roda a MESMA consulta analítica nos dois engines e exige resultado idêntico
(valores, totais, ordenação, %). Cobre os endpoints da Sentinel.io Analytics
API e as invariantes analíticas críticas da plataforma.

Pulado automaticamente se faltar o PostgreSQL OU o atlas_public.duckdb
(rode antes:  python -m src.production.build_dataset).
"""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import pytest

from src.api.config import settings

# ---------------------------------------------------------------- skip guard ---

_DUCKDB_PATH = Path(settings.duckdb_path)


def _pg_ok() -> bool:
    try:
        import psycopg

        with psycopg.connect(
            host=settings.postgres_host, port=settings.postgres_port,
            dbname=settings.postgres_db, user=settings.postgres_user,
            password=settings.postgres_password, connect_timeout=3,
        ):
            return True
    except Exception:
        return False


if not _DUCKDB_PATH.exists():
    pytest.skip(
        f"atlas_public.duckdb ausente ({_DUCKDB_PATH}). Rode: python -m src.production.build_dataset",
        allow_module_level=True,
    )
if not _pg_ok():
    pytest.skip("PostgreSQL Development indisponível — paridade pulada.", allow_module_level=True)


# ------------------------------------------------------------------ fixtures ---

@pytest.fixture(scope="module")
def pg():
    import psycopg

    conn = psycopg.connect(
        host=settings.postgres_host, port=settings.postgres_port,
        dbname=settings.postgres_db, user=settings.postgres_user,
        password=settings.postgres_password,
    )
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def ddb():
    import duckdb

    con = duckdb.connect(str(_DUCKDB_PATH), read_only=True)
    yield con
    con.close()


# ------------------------------------------------------------------- helpers ---

def _norm(value):
    """Normaliza para comparação: Decimal/float -> float arredondado (a API
    serializa tudo como float), datas -> ISO, resto inalterado."""
    if isinstance(value, Decimal):
        return round(float(value), 3)
    if isinstance(value, float):
        return round(value, 3)
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return value


def _rows(cursor_result) -> list[tuple]:
    return [tuple(_norm(v) for v in row) for row in cursor_result]


def _pg_rows(pg, sql: str, params: dict | None = None) -> list[tuple]:
    with pg.cursor() as cur:
        cur.execute(sql, params or {})
        return _rows(cur.fetchall())


def _ddb_rows(ddb, sql: str, params: dict | None = None) -> list[tuple]:
    # psycopg usa %(name)s; DuckDB usa $name. As queries de teste abaixo usam
    # a sintaxe DuckDB ($name) e um shim converte para o Postgres.
    return _rows(ddb.execute(sql, params or {}).fetchall())


def _both(pg, ddb, sql_ddb: str, params: dict | None = None):
    """Executa a MESMA lógica nos dois. sql_ddb usa $param (DuckDB);
    para o Postgres, $param -> %(param)s."""
    import re

    sql_pg = re.sub(r"\$(\w+)", r"%(\1)s", sql_ddb)
    return _pg_rows(pg, sql_pg, params), _ddb_rows(ddb, sql_ddb, params)


# =============================================================================
# 1. PARIDADE POR ENDPOINT — mesma query, mesmos resultados
# =============================================================================

def test_parity_indicators(pg, ddb):
    sql = """
        SELECT indicador_id, evento, familia_medida, unidade, tipo_indicador, grupo_semantico
        FROM analytics.vw_dim_indicador ORDER BY evento
    """
    p, d = _both(pg, ddb, sql)
    assert p == d
    assert len(d) == 31


def test_parity_kpis_no_filter(pg, ddb):
    sql = """
        SELECT i.indicador_id, i.evento, i.familia_medida, i.unidade,
               SUM(f.valor) AS value, COUNT(*) AS n
        FROM fact_indicadores f
        JOIN dim_indicador i    ON f.indicador_id = i.indicador_id
        JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
        JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
        JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
        GROUP BY i.indicador_id, i.evento, i.familia_medida, i.unidade
        ORDER BY i.evento
    """
    p, d = _both(pg, ddb, sql)
    assert p == d
    assert len(d) == 31
    # nenhuma linha mistura família: cada linha é 1 indicador
    assert len({row[0] for row in d}) == 31


@pytest.mark.parametrize("indicator_id,ano", [(25, 2025), (1, 2024), (13, 2026)])
def test_parity_kpis_filtered(pg, ddb, indicator_id, ano):
    sql = """
        SELECT i.indicador_id, SUM(f.valor) AS value, COUNT(*) AS n
        FROM fact_indicadores f
        JOIN dim_indicador i    ON f.indicador_id = i.indicador_id
        JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
        JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
        JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
        WHERE (CAST($indicator_id AS INTEGER) IS NULL OR i.indicador_id = $indicator_id)
          AND (CAST($ano AS SMALLINT) IS NULL OR t.ano = $ano)
        GROUP BY i.indicador_id
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": indicator_id, "ano": ano})
    assert p == d


@pytest.mark.parametrize("indicator_id", [25, 1, 13])
def test_parity_temporal_series(pg, ddb, indicator_id):
    sql = """
        SELECT t.ano, t.mes, SUM(f.valor) AS value, bool_or(t.is_partial_year) AS partial
        FROM fact_indicadores f
        JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
        JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
        JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
        WHERE f.indicador_id = $indicator_id
        GROUP BY t.ano, t.mes
        ORDER BY t.ano, t.mes
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": indicator_id})
    assert p == d


def test_parity_yoy(pg, ddb):
    sql = """
        SELECT ano, is_partial_year, meses_incluidos, total_periodo_comparavel
        FROM analytics.vw_comparacao_anual_comparavel v
        JOIN dim_indicador i ON i.evento = v.evento
        WHERE i.indicador_id = $indicator_id AND ano IN ($base, $comp)
        ORDER BY ano
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": 25, "base": 2024, "comp": 2025})
    assert p == d


@pytest.mark.parametrize("indicator_id,ano", [(25, 2025), (1, 2025)])
def test_parity_geography_uf(pg, ddb, indicator_id, ano):
    sql = """
        SELECT l.uf, l.regiao, SUM(f.valor) AS value
        FROM fact_indicadores f
        JOIN dim_tempo t        ON f.tempo_id = t.tempo_id
        JOIN dim_localidade l   ON f.localidade_id = l.localidade_id
        JOIN dim_abrangencia ab ON f.abrangencia_id = ab.abrangencia_id
        WHERE f.indicador_id = $indicator_id
          AND (CAST($ano AS SMALLINT) IS NULL OR t.ano = $ano)
        GROUP BY l.uf, l.regiao
        ORDER BY value DESC, l.uf
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": indicator_id, "ano": ano})
    assert p == d


def test_parity_geography_municipalities(pg, ddb):
    sql = """
        SELECT l.uf, l.municipio, SUM(f.valor) AS value
        FROM fact_indicadores f
        JOIN dim_tempo t      ON f.tempo_id = t.tempo_id
        JOIN dim_localidade l ON f.localidade_id = l.localidade_id
        WHERE f.indicador_id = $indicator_id
          AND (CAST($uf AS VARCHAR) IS NULL OR l.uf = $uf)
        GROUP BY l.uf, l.municipio
        ORDER BY value DESC, l.municipio
        LIMIT 50
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": 1, "uf": "BA"})
    assert p == d


@pytest.mark.parametrize("indicator_id,ano", [(25, 2025), (1, 2025), (2, 2024)])
def test_parity_ranking_uf(pg, ddb, indicator_id, ano):
    sql = """
        SELECT ranking, uf, regiao, total
        FROM analytics.vw_ranking_uf v
        JOIN dim_indicador i ON i.evento = v.evento
        WHERE i.indicador_id = $indicator_id AND v.ano = $ano
        ORDER BY ranking
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": indicator_id, "ano": ano})
    assert p == d
    # ordenação e desempate idênticos
    assert [r[0] for r in d] == [r[0] for r in p]


def test_parity_ranking_municipalities(pg, ddb):
    sql = """
        SELECT ranking, uf, municipio, total
        FROM analytics.vw_ranking_municipio v
        JOIN dim_indicador i ON i.evento = v.evento
        WHERE i.indicador_id = $indicator_id AND v.ano = $ano
        ORDER BY ranking LIMIT 100
    """
    p, d = _both(pg, ddb, sql, {"indicator_id": 25, "ano": 2025})
    assert p == d


def test_parity_ranking_indicators(pg, ddb):
    sql = """
        SELECT ranking, evento, grupo_semantico, total
        FROM analytics.vw_ranking_indicador
        WHERE grupo_semantico = $grupo AND ano = $ano
        ORDER BY ranking
    """
    p, d = _both(pg, ddb, sql, {"grupo": "Ocorrências", "ano": 2025})
    assert p == d


def test_parity_radar(pg, ddb):
    sql = """
        SELECT v.evento, v.ano, v.mes, v.total, v.media_historica,
               v.desvio_padrao_historico, v.z_score
        FROM analytics.vw_desvio_media_historica v
        JOIN dim_indicador i ON i.evento = v.evento
        WHERE ABS(v.z_score) >= 2
        ORDER BY ABS(v.z_score) DESC NULLS LAST, v.evento, v.ano, v.mes
    """
    p, d = _both(pg, ddb, sql)
    assert p == d


def test_parity_metadata_resumo(pg, ddb):
    # a query EXATA do repository (6 das 11 colunas — nenhuma toca staging)
    sql = """
        SELECT periodo_inicio, periodo_fim, anos_parciais,
               n_indicadores, n_ufs, n_municipios_distintos
        FROM analytics.vw_qualidade_resumo
    """
    p, d = _both(pg, ddb, sql)
    assert p == d


def test_parity_metadata_lists(pg, ddb):
    for sql in (
        "SELECT DISTINCT uf, regiao FROM dim_localidade ORDER BY uf",
        "SELECT DISTINCT ano FROM dim_tempo ORDER BY ano",
        "SELECT abrangencia FROM dim_abrangencia ORDER BY abrangencia",
    ):
        p, d = _both(pg, ddb, sql)
        assert p == d


# =============================================================================
# 2. INVARIANTES ANALÍTICAS (§13 do prompt da Fase 6)
# =============================================================================

def test_units_never_mixed(pg, ddb):
    sql = """
        SELECT max(n) FROM (
            SELECT i.indicador_id, count(DISTINCT i.familia_medida) AS n
            FROM fact_indicadores f JOIN dim_indicador i ON f.indicador_id = i.indicador_id
            GROUP BY i.indicador_id
        ) s
    """
    p, d = _both(pg, ddb, sql)
    assert p == d == [(1,)]


def test_2026_is_partial_six_months(pg, ddb):
    sql = "SELECT count(*), bool_and(is_partial_year) FROM dim_tempo WHERE ano = 2026"
    p, d = _both(pg, ddb, sql)
    assert p == d == [(6, True)]


def test_yoy_never_full_vs_partial(pg, ddb):
    # meses_incluidos é o MESMO corte para todos os anos
    sql = "SELECT DISTINCT meses_incluidos FROM analytics.vw_comparacao_anual_comparavel"
    p, d = _both(pg, ddb, sql)
    assert p == d
    assert len(d) == 1 and d[0][0] == 6  # 2026 só tem 6 meses -> corte = 6


def test_radar_known_anomaly(pg, ddb):
    sql = """
        SELECT round(z_score, 2)
        FROM analytics.vw_desvio_media_historica
        WHERE evento = 'Morte por intervenção de Agente do Estado'
          AND ano = 2025 AND mes = 10
    """
    p, d = _both(pg, ddb, sql)
    assert p == d
    assert d[0][0] == pytest.approx(3.03)


def test_partial_year_flag_is_data_driven_not_hardcoded(pg, ddb):
    # nenhum ano além de 2026 é parcial hoje; a flag vem dos dados
    sql = "SELECT DISTINCT ano FROM dim_tempo WHERE is_partial_year ORDER BY ano"
    p, d = _both(pg, ddb, sql)
    assert p == d == [(2026,)]
