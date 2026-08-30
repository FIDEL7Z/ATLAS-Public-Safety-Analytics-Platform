"""Validação do dataset de produção (atlas_public.duckdb).

Checa integridade estrutural e as invariantes analíticas críticas da
plataforma (unidades nunca misturadas, 2026 parcial, anomalia do radar).
Não compara contra o PostgreSQL — isso é feito em tests/test_production_parity.py.
"""
from __future__ import annotations

from dataclasses import dataclass

import duckdb

# Views que a API consome (direta ou indiretamente). Todas devem existir e
# responder a um SELECT sem erro.
API_VIEWS = [
    "analytics.vw_dim_indicador",
    "analytics.vw_ranking_uf",
    "analytics.vw_ranking_municipio",
    "analytics.vw_ranking_indicador",
    "analytics.vw_comparacao_anual_comparavel",
    "analytics.vw_desvio_media_historica",
    "analytics.vw_evolucao_temporal",
    "analytics.vw_uf",
    "analytics.vw_municipio",
    "analytics.vw_indicador",
]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _one(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchone()[0]


def run_checks(con: duckdb.DuckDBPyConnection, expected_fact_rows: int) -> list[Check]:
    checks: list[Check] = []

    fact_rows = _one(con, "SELECT count(*) FROM fact_indicadores")
    checks.append(Check(
        "fact_indicadores no grão completo",
        fact_rows == expected_fact_rows,
        f"{fact_rows:,} linhas (esperado {expected_fact_rows:,})",
    ))

    checks.append(Check(
        "staging ausente da produção",
        _one(con, "SELECT count(*) FROM duckdb_tables() WHERE table_name = 'stg_sinesp'") == 0,
        "stg_sinesp não existe no dataset",
    ))

    n_dims = _one(con, "SELECT count(*) FROM duckdb_tables() WHERE table_name LIKE 'dim_%'")
    checks.append(Check("8 dimensões presentes", n_dims == 8, f"{n_dims} tabelas dim_*"))

    for view in API_VIEWS:
        try:
            con.execute(f"SELECT * FROM {view} LIMIT 1").fetchall()
            checks.append(Check(f"view {view}", True, "responde a SELECT"))
        except Exception as exc:  # noqa: BLE001
            checks.append(Check(f"view {view}", False, str(exc).splitlines()[0][:120]))

    # vw_qualidade_resumo deve ter virado tabela de 1 linha (sem depender de staging)
    is_table = _one(con, "SELECT count(*) FROM duckdb_tables() WHERE schema_name='analytics' AND table_name='vw_qualidade_resumo'") == 1
    resumo_rows = _one(con, "SELECT count(*) FROM analytics.vw_qualidade_resumo")
    checks.append(Check(
        "vw_qualidade_resumo materializada (1 linha, sem staging)",
        is_table and resumo_rows == 1,
        f"tabela={is_table}, linhas={resumo_rows}",
    ))

    # --- invariantes analíticas ---

    # 2026 é ano parcial de 6 meses
    meses_2026 = _one(con, "SELECT count(*) FROM dim_tempo WHERE ano = 2026")
    parcial_2026 = _one(con, "SELECT bool_and(is_partial_year) FROM dim_tempo WHERE ano = 2026")
    checks.append(Check(
        "2026 tratado como ano parcial (6 meses)",
        meses_2026 == 6 and parcial_2026 is True,
        f"{meses_2026} meses, is_partial_year={parcial_2026}",
    ))

    # KPI nunca mistura família: cada indicador tem exatamente uma familia_medida
    familias_por_indicador = _one(con, """
        SELECT max(n) FROM (
            SELECT indicador_id, count(DISTINCT familia_medida) AS n
            FROM fact_indicadores f JOIN dim_indicador i USING (indicador_id)
            GROUP BY indicador_id
        )
    """)
    checks.append(Check(
        "unidades nunca misturáveis (1 familia_medida por indicador)",
        familias_por_indicador == 1,
        f"máx famílias distintas por indicador = {familias_por_indicador}",
    ))

    # Anomalia conhecida do radar (z-score explicável, sem ML)
    z = con.execute("""
        SELECT round(z_score, 2) FROM analytics.vw_desvio_media_historica
        WHERE evento = 'Morte por intervenção de Agente do Estado'
          AND ano = 2025 AND mes = 10
    """).fetchone()
    checks.append(Check(
        "radar: anomalia out/2025 preservada (z ≈ 3.03)",
        z is not None and abs(float(z[0]) - 3.03) < 0.01,
        f"z_score = {z[0] if z else 'ausente'}",
    ))

    return checks


def format_report(checks: list[Check]) -> str:
    lines = []
    for c in checks:
        mark = "PASS" if c.ok else "FALHA"
        lines.append(f"  [{mark}] {c.name} — {c.detail}")
    n_ok = sum(1 for c in checks if c.ok)
    lines.append(f"\n  {n_ok}/{len(checks)} checks OK")
    return "\n".join(lines)
