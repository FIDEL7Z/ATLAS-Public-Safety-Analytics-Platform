import pytest

from src.transformation.dimensions import build_all_dimensions
from src.transformation.fact import (
    aggregate_to_real_grain,
    build_fact_indicadores,
    compute_nao_informado_stats,
)
from src.transformation.staging import build_staging


@pytest.fixture
def pipeline(sample_raw_by_year):
    stg = build_staging(sample_raw_by_year)
    agg = aggregate_to_real_grain(stg)
    dims = build_all_dimensions(stg)
    fact = build_fact_indicadores(agg, dims)
    return stg, agg, dims, fact


def _indicador_id(dims, evento):
    return dims["dim_indicador"].loc[dims["dim_indicador"]["evento"] == evento, "indicador_id"].iloc[0]


def _localidade_id(dims, uf, municipio):
    dim = dims["dim_localidade"]
    return dim.loc[(dim["uf"] == uf) & (dim["municipio"] == municipio), "localidade_id"].iloc[0]


def test_df_duplicate_rows_are_summed_not_dropped(pipeline):
    """As 2 linhas 'duplicadas' de DF/Brasília (feminino=1,masc=0) e
    (feminino=0,masc=1) devem virar SOMA (feminino=1, masculino=1), nunca
    ser deduplicadas para uma única linha original."""
    stg, agg, dims, fact = pipeline
    indicador_id = _indicador_id(dims, "Homicídio doloso")
    localidade_id = _localidade_id(dims, "DF", "BRASÍLIA")

    sub = fact[(fact["indicador_id"] == indicador_id) & (fact["localidade_id"] == localidade_id)]
    dim_sexo = dims["dim_sexo"].set_index("sexo_id")["sexo"]
    valores = {dim_sexo[row.sexo_id]: row.valor for row in sub.itertuples()}

    assert valores["Feminino"] == 1.0
    assert valores["Masculino"] == 1.0
    assert valores["Não Informado"] == 0.0


def test_nao_informado_excluded_from_fact_not_zeroed(pipeline):
    """O registro de 'Mandado de prisão cumprido' com total=None não deve
    virar uma linha na fact table (nem com valor 0)."""
    stg, agg, dims, fact = pipeline
    indicador_id = _indicador_id(dims, "Mandado de prisão cumprido")
    localidade_id = _localidade_id(dims, "SP", "OUTRACIDADE")

    sub = fact[(fact["indicador_id"] == indicador_id) & (fact["localidade_id"] == localidade_id)]
    # Só a linha de fevereiro (total=5) deve existir; a de janeiro (total=None) não.
    assert len(sub) == 1
    assert sub["valor"].iloc[0] == 5.0


def test_nao_informado_stats_captures_the_missing_value(pipeline):
    stg, agg, dims, fact = pipeline
    stats = compute_nao_informado_stats(agg, dims["dim_indicador"])
    row = stats[stats["evento"] == "Mandado de prisão cumprido"].iloc[0]
    assert row["valores_nao_informados"] == 1


def test_arma_dimension_is_part_of_grain_not_summed_together(pipeline):
    """Pistola e Fuzil apreendidos no mesmo mês/município NÃO podem virar
    uma única linha somada — são grãos distintos."""
    stg, agg, dims, fact = pipeline
    indicador_id = _indicador_id(dims, "Arma de Fogo Apreendida")
    localidade_id = _localidade_id(dims, "SP", "OUTRACIDADE")

    sub = fact[(fact["indicador_id"] == indicador_id) & (fact["localidade_id"] == localidade_id)]
    assert len(sub) == 2
    assert set(sub["valor"]) == {3.0, 2.0}


def test_no_negative_values(pipeline):
    _, _, _, fact = pipeline
    assert (fact["valor"] >= 0).all()


def test_no_null_valor(pipeline):
    _, _, _, fact = pipeline
    assert fact["valor"].notna().all()


def test_grain_uniqueness(pipeline):
    _, _, _, fact = pipeline
    grain_cols = [
        "tempo_id", "localidade_id", "indicador_id", "abrangencia_id",
        "agente_id", "arma_id", "faixa_etaria_id", "sexo_id",
    ]
    key = fact[grain_cols].astype("Int64").fillna(-1)
    assert not key.duplicated().any()


def test_total_vitima_is_never_a_stored_column(pipeline):
    _, _, _, fact = pipeline
    assert "total_vitima" not in fact.columns
