"""Orquestrador do ETL do ATLAS — Fase 1.

RAW -> STAGING -> (agregação pelo grão real) -> FACT (formato longo) -> PostgreSQL
com validação de qualidade e reconciliação em cada etapa crítica.

Uso: python -m src.run_etl
"""
import sys
import time

from src.config import DIMENSIONS_DIR, FACTS_DIR, STAGING_DIR, ensure_dirs, get_logger
from src.ingestion.load_raw import load_all_raw
from src.transformation.dimensions import build_all_dimensions
from src.transformation.fact import (
    aggregate_to_real_grain,
    build_fact_indicadores,
    compute_nao_informado_stats,
)
from src.transformation.staging import build_staging
from src.validation.data_quality import run_all_checks, write_data_quality_report
from src.validation.reconciliation import build_reconciliation, write_reconciliation_report

logger = get_logger(__name__)


def main() -> dict:
    t_start = time.time()
    ensure_dirs()

    logger.info("=" * 80)
    logger.info("ATLAS ETL — Fase 1 — início da execução")
    logger.info("=" * 80)

    # ---- RAW ----
    raw_by_year = load_all_raw()
    n_raw = sum(len(df) for df in raw_by_year.values())

    # ---- STAGING ----
    stg = build_staging(raw_by_year)
    stg.to_parquet(STAGING_DIR / "stg_sinesp.parquet", index=False)

    # ---- TRANSFORM: agregação pelo grão real + dimensões + fato ----
    agg = aggregate_to_real_grain(stg)

    dims = build_all_dimensions(stg)
    for name, df in dims.items():
        df.to_parquet(DIMENSIONS_DIR / f"{name}.parquet", index=False)

    fact = build_fact_indicadores(agg, dims)
    fact.to_parquet(FACTS_DIR / "fact_indicadores.parquet", index=False)

    # ---- DATA QUALITY ----
    nao_informado_stats = compute_nao_informado_stats(agg, dims["dim_indicador"])
    checks = run_all_checks(n_raw, stg, fact, dims)
    row_counts = {
        "RAW (soma dos 3 arquivos)": n_raw,
        "STAGING (stg_sinesp)": len(stg),
        "Grão real agregado (intermediário)": len(agg),
        "FACT (fact_indicadores, formato longo)": len(fact),
    }
    write_data_quality_report(checks, nao_informado_stats, row_counts)

    # ---- RECONCILIAÇÃO ----
    reconciliation = build_reconciliation(raw_by_year, stg, fact, dims["dim_indicador"])
    write_reconciliation_report(reconciliation)

    n_fail_checks = sum(1 for c in checks if c["status"] == "FAIL")
    n_fail_reconciliation = (reconciliation["status"] == "FAIL").sum()

    # ---- CARGA NO POSTGRESQL (best-effort — não derruba o pipeline se indisponível) ----
    postgres_status = "não tentado"
    try:
        from src.loading.postgres_loader import load_all as load_postgres
        load_postgres(stg, dims, fact)
        postgres_status = "OK"
    except Exception as exc:  # noqa: BLE001
        postgres_status = f"FALHOU: {exc}"
        logger.error(f"Carga no PostgreSQL falhou (pipeline de arquivos Parquet segue válido): {exc}")

    elapsed = time.time() - t_start
    logger.info("=" * 80)
    logger.info(f"ATLAS ETL — Fase 1 — concluído em {elapsed / 60:.1f} min")
    logger.info(f"Checks de qualidade: {len(checks) - n_fail_checks}/{len(checks)} PASS")
    logger.info(f"Reconciliação: {(reconciliation['status'] == 'PASS').sum()}/{len(reconciliation)} PASS")
    logger.info(f"PostgreSQL: {postgres_status}")
    logger.info("=" * 80)

    summary = {
        "n_raw": n_raw,
        "n_staging": len(stg),
        "n_grain_real": len(agg),
        "n_fact": len(fact),
        "n_indicadores": len(dims["dim_indicador"]),
        "n_ufs": dims["dim_localidade"]["uf"].nunique(),
        "n_municipios": dims["dim_localidade"]["municipio"].nunique(),
        "periodo_min": str(dims["dim_tempo"]["data_referencia"].min().date()),
        "periodo_max": str(dims["dim_tempo"]["data_referencia"].max().date()),
        "anos_parciais": sorted(dims["dim_tempo"].loc[dims["dim_tempo"]["is_partial_year"], "ano"].unique().tolist()),
        "dq_checks_pass": len(checks) - n_fail_checks,
        "dq_checks_total": len(checks),
        "reconciliation_pass": int((reconciliation["status"] == "PASS").sum()),
        "reconciliation_total": len(reconciliation),
        "postgres_status": postgres_status,
        "elapsed_minutes": round(elapsed / 60, 1),
    }
    return summary


if __name__ == "__main__":
    result = main()
    print(result)
    if result["dq_checks_pass"] != result["dq_checks_total"] or result["reconciliation_pass"] != result["reconciliation_total"]:
        sys.exit(1)
