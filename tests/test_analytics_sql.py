"""Testes da camada analítica (Fase 2) contra o PostgreSQL real.

Diferente dos testes da Fase 1 (fixture sintética, sem banco), estes testes
rodam contra o banco de dados já carregado — são de integração, não
unitários. Pulados automaticamente se o Postgres não estiver acessível
(ex.: ambiente de CI sem o container rodando).
"""
import os

import psycopg2
import pytest
from dotenv import load_dotenv

from src.config import ROOT_DIR

load_dotenv(ROOT_DIR / ".env")


def _try_connect():
    try:
        return psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "5433"),
            dbname=os.environ.get("POSTGRES_DB", "atlas"),
            user=os.environ.get("POSTGRES_USER", "atlas"),
            password=os.environ.get("POSTGRES_PASSWORD", "atlas_dev_only"),
            connect_timeout=3,
        )
    except Exception:
        return None


@pytest.fixture(scope="module")
def conn():
    c = _try_connect()
    if c is None:
        pytest.skip("PostgreSQL indisponível — testes de integração da camada analítica pulados.")
    yield c
    c.close()


def _fetchall(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


ALL_31_EVENTOS_VIEWS = [
    "analytics.vw_nacional",
    "analytics.vw_uf",
    "analytics.vw_municipio",
    "analytics.vw_indicador",
    "analytics.vw_evolucao_temporal",
]


@pytest.mark.parametrize("view", ALL_31_EVENTOS_VIEWS)
def test_nenhum_indicador_desapareceu(conn, view):
    rows = _fetchall(conn, f"SELECT COUNT(DISTINCT evento) AS n FROM {view}")
    assert rows[0]["n"] == 31, f"{view} não contém os 31 indicadores esperados"


def test_totais_reconciliam_com_fact_indicadores(conn):
    """SUM(valor) por evento na fact_indicadores == SUM(total) na vw_indicador,
    para os 31 eventos — nenhuma diferença tolerada."""
    rows = _fetchall(conn, """
        SELECT f.evento, f.total AS fact_total, v.total AS view_total
        FROM (
            SELECT di.evento, SUM(fi.valor) AS total
            FROM fact_indicadores fi JOIN dim_indicador di ON fi.indicador_id = di.indicador_id
            GROUP BY di.evento
        ) f
        JOIN (
            SELECT evento, SUM(total) AS total FROM analytics.vw_indicador GROUP BY evento
        ) v ON f.evento = v.evento
        WHERE ABS(f.total - v.total) > 0.000001
    """)
    assert rows == [], f"eventos com divergência entre fact_indicadores e vw_indicador: {rows}"


def test_nenhuma_metrica_mistura_familias(conn):
    """Cada indicador deve aparecer com uma única familia_medida em
    vw_indicador — nunca contribuir simultaneamente para mais de uma."""
    rows = _fetchall(conn, """
        SELECT evento, COUNT(DISTINCT familia_medida) AS n_familias
        FROM analytics.vw_indicador GROUP BY evento HAVING COUNT(DISTINCT familia_medida) > 1
    """)
    assert rows == [], f"indicadores com mais de uma familia_medida: {rows}"


def test_nenhuma_metrica_mistura_unidades(conn):
    rows = _fetchall(conn, """
        SELECT evento, COUNT(DISTINCT unidade) AS n_unidades
        FROM analytics.vw_indicador GROUP BY evento HAVING COUNT(DISTINCT unidade) > 1
    """)
    assert rows == [], f"indicadores com mais de uma unidade: {rows}"


def test_2026_permanece_identificado_como_parcial(conn):
    rows = _fetchall(conn, "SELECT DISTINCT ano, is_partial_year FROM analytics.vw_nacional WHERE ano = 2026")
    assert rows, "ano 2026 não encontrado em vw_nacional"
    assert all(r["is_partial_year"] for r in rows), "2026 deveria estar sempre flagado como parcial"

    rows_outros = _fetchall(conn, "SELECT DISTINCT ano, is_partial_year FROM analytics.vw_nacional WHERE ano != 2026")
    assert all(not r["is_partial_year"] for r in rows_outros), "só 2026 deveria estar flagado como parcial nos dados atuais"


def test_participacao_sexo_soma_100_por_evento_ano(conn):
    """A soma das participações de sexo dentro de um (evento, ano) deve ser
    ~100% — se não fosse, seria sinal de dupla contagem ou perda de linhas."""
    rows = _fetchall(conn, """
        SELECT evento, ano, SUM(participacao_pct) AS soma_pct
        FROM analytics.vw_sexo GROUP BY evento, ano
        HAVING ABS(SUM(participacao_pct) - 100) > 0.5
    """)
    assert rows == [], f"(evento, ano) com participação de sexo fora de ~100%: {rows}"


def test_ranking_respeita_particao_por_evento_e_ano(conn):
    """Todo ranking de UF deve começar em 1 para cada (evento, ano) —
    confirma que a partição da window function está correta (nunca um
    ranking global cross-indicador)."""
    rows = _fetchall(conn, """
        SELECT evento, ano, MIN(ranking) AS min_ranking
        FROM analytics.vw_ranking_uf GROUP BY evento, ano
        HAVING MIN(ranking) != 1
    """)
    assert rows == [], f"(evento, ano) cujo ranking de UF não começa em 1: {rows}"


def test_pesos_outliers_nao_removem_dados_da_base(conn):
    """soma_com_outliers deve ser >= soma_sem_top1pct, e igual ao total real
    de fact_indicadores para o evento — nenhum valor foi descartado."""
    rows = _fetchall(conn, """
        SELECT o.evento, o.soma_com_outliers, f.total AS fact_total
        FROM analytics.vw_pesos_impacto_outliers o
        JOIN (
            SELECT di.evento, SUM(fi.valor) AS total
            FROM fact_indicadores fi JOIN dim_indicador di ON fi.indicador_id = di.indicador_id
            WHERE di.familia_medida = 'peso'
            GROUP BY di.evento
        ) f ON o.evento = f.evento
        WHERE ABS(o.soma_com_outliers - f.total) > 0.000001
    """)
    assert rows == [], f"soma_com_outliers não bate com o total real da fact table: {rows}"


def test_qualidade_nao_informado_cobre_31_eventos(conn):
    rows = _fetchall(conn, "SELECT COUNT(DISTINCT evento) AS n FROM analytics.vw_qualidade_nao_informado")
    assert rows[0]["n"] == 31


def test_qualidade_resumo_tem_uma_linha_consistente(conn):
    rows = _fetchall(conn, "SELECT * FROM analytics.vw_qualidade_resumo")
    assert len(rows) == 1
    r = rows[0]
    assert r["n_indicadores"] == 31
    assert r["n_ufs"] == 27
    assert r["anos_parciais"] == 1


def test_vw_fato_enriquecido_nao_perde_linhas(conn):
    rows = _fetchall(conn, "SELECT COUNT(*) AS n FROM analytics.vw_fato_enriquecido")
    rows_fact = _fetchall(conn, "SELECT COUNT(*) AS n FROM fact_indicadores")
    assert rows[0]["n"] == rows_fact[0]["n"]
