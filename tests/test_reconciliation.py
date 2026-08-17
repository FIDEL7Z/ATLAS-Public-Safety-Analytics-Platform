import pytest

from src.transformation.dimensions import build_all_dimensions
from src.transformation.fact import aggregate_to_real_grain, build_fact_indicadores
from src.transformation.staging import build_staging
from src.validation.reconciliation import build_reconciliation


def test_reconciliation_all_pass_on_synthetic_data(sample_raw_by_year):
    stg = build_staging(sample_raw_by_year)
    agg = aggregate_to_real_grain(stg)
    dims = build_all_dimensions(stg)
    fact = build_fact_indicadores(agg, dims)

    result = build_reconciliation(sample_raw_by_year, stg, fact, dims["dim_indicador"])

    failed = result[result["status"] == "FAIL"]
    assert failed.empty, f"eventos com reconciliação FAIL: {failed[['evento', 'diferenca']].to_dict('records')}"


def test_raw_and_fact_totals_match_for_events_with_duplicates(sample_raw_by_year):
    """Caso crítico: o total do evento com o padrão de duplicação (DF) tem
    que bater entre RAW e FACT mesmo com SUM em vez de dedup."""
    stg = build_staging(sample_raw_by_year)
    agg = aggregate_to_real_grain(stg)
    dims = build_all_dimensions(stg)
    fact = build_fact_indicadores(agg, dims)

    result = build_reconciliation(sample_raw_by_year, stg, fact, dims["dim_indicador"])
    row = result[result["evento"] == "Homicídio doloso"].iloc[0]
    assert row["status"] == "PASS"
    assert row["raw_total"] == row["fact_total"]
