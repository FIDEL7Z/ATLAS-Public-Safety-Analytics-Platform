import pytest

from src.transformation.dimensions import build_all_dimensions
from src.transformation.reference_data import validate_evento_coverage
from src.transformation.staging import build_staging


@pytest.fixture
def stg(sample_raw_by_year):
    return build_staging(sample_raw_by_year)


def test_dim_tempo_partial_year_flag(stg):
    dims = build_all_dimensions(stg)
    dim_tempo = dims["dim_tempo"]

    ano_completo = dim_tempo[dim_tempo["ano"] == 2030]
    ano_parcial = dim_tempo[dim_tempo["ano"] == 2031]

    assert len(ano_completo) == 12
    assert not ano_completo["is_partial_year"].any()

    assert len(ano_parcial) == 3
    assert ano_parcial["is_partial_year"].all()


def test_dim_localidade_regiao_mapping(stg):
    dims = build_all_dimensions(stg)
    dim_loc = dims["dim_localidade"]

    sp = dim_loc[dim_loc["uf"] == "SP"].iloc[0]
    df_row = dim_loc[dim_loc["uf"] == "DF"].iloc[0]
    assert sp["regiao"] == "Sudeste"
    assert df_row["regiao"] == "Centro-Oeste"


def test_dim_indicador_has_no_nulls(stg):
    dims = build_all_dimensions(stg)
    dim_ind = dims["dim_indicador"]
    assert dim_ind["familia_medida"].notna().all()
    assert dim_ind["unidade"].notna().all()
    assert dim_ind["tipo_indicador"].notna().all()


def test_validate_evento_coverage_raises_on_unknown_event():
    with pytest.raises(ValueError):
        validate_evento_coverage({"Evento Que Não Existe Na Classificação"})
