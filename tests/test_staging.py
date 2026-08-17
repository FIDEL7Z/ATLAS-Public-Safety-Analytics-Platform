from src.transformation.staging import STAGING_COLUMNS, build_staging


def test_staging_preserves_row_count(sample_raw_by_year):
    n_raw = sum(len(df) for df in sample_raw_by_year.values())
    stg = build_staging(sample_raw_by_year)
    assert len(stg) == n_raw


def test_staging_drops_total_vitima(sample_raw_by_year):
    stg = build_staging(sample_raw_by_year)
    assert "total_vitima" not in stg.columns
    assert list(stg.columns) == STAGING_COLUMNS


def test_staging_preserves_apparent_duplicates(sample_raw_by_year):
    """As 2 linhas do padrão DF devem continuar como 2 linhas na staging —
    a agregação só acontece na camada de transformação."""
    stg = build_staging(sample_raw_by_year)
    df_rows = stg[(stg["uf"] == "DF") & (stg["evento"] == "Homicídio doloso")]
    assert len(df_rows) == 2


def test_staging_ano_origem_matches_source_year(sample_raw_by_year):
    stg = build_staging(sample_raw_by_year)
    for ano, df in sample_raw_by_year.items():
        assert (stg.loc[stg["ano_origem"] == ano].shape[0]) == len(df)
