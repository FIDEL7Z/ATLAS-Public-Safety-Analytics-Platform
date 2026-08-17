"""Construção das dimensões do esquema estrela (formato longo).

Chaves substitutas (surrogate keys) são inteiros sequenciais atribuídos de
forma determinística (valores únicos ordenados -> 1..N), para que o ETL
produza os mesmos IDs em execuções repetidas sobre os mesmos dados fonte.
"""
import pandas as pd

from src.config import MONTHS_PER_FULL_YEAR, get_logger
from src.transformation.reference_data import (
    UF_REGIAO,
    indicador_classification_df,
    validate_evento_coverage,
    validate_uf_coverage,
)

logger = get_logger(__name__)

SEXO_FEMININO = "Feminino"
SEXO_MASCULINO = "Masculino"
SEXO_NAO_INFORMADO = "Não Informado"


def _surrogate_key_table(values: pd.Series, id_name: str, value_name: str) -> pd.DataFrame:
    uniques = sorted(values.dropna().unique().tolist())
    return pd.DataFrame({id_name: range(1, len(uniques) + 1), value_name: uniques})


def build_dim_tempo(stg: pd.DataFrame) -> pd.DataFrame:
    meses_por_ano = (
        stg[["ano_origem", "data_referencia"]]
        .drop_duplicates()
        .groupby("ano_origem")["data_referencia"]
        .nunique()
    )
    anos_parciais = set(meses_por_ano[meses_por_ano < MONTHS_PER_FULL_YEAR].index)
    if anos_parciais:
        logger.info(f"Anos com cobertura parcial (< {MONTHS_PER_FULL_YEAR} meses na fonte): {sorted(anos_parciais)}")

    datas = sorted(stg["data_referencia"].unique())
    dim = pd.DataFrame({"data_referencia": datas})
    dim["tempo_id"] = range(1, len(dim) + 1)
    dim["ano"] = dim["data_referencia"].dt.year
    dim["mes"] = dim["data_referencia"].dt.month
    dim["trimestre"] = dim["data_referencia"].dt.quarter
    dim["nome_mes"] = dim["data_referencia"].dt.strftime("%B")
    dim["is_partial_year"] = dim["ano"].isin(anos_parciais)

    return dim[["tempo_id", "data_referencia", "ano", "mes", "trimestre", "nome_mes", "is_partial_year"]]


def build_dim_localidade(stg: pd.DataFrame) -> pd.DataFrame:
    validate_uf_coverage(set(stg["uf"].unique()))

    dim = stg[["uf", "municipio"]].drop_duplicates().sort_values(["uf", "municipio"]).reset_index(drop=True)
    dim["localidade_id"] = range(1, len(dim) + 1)
    dim["regiao"] = dim["uf"].map(UF_REGIAO)

    return dim[["localidade_id", "uf", "municipio", "regiao"]]


def build_dim_indicador(stg: pd.DataFrame) -> pd.DataFrame:
    validate_evento_coverage(set(stg["evento"].unique()))

    dim = indicador_classification_df().sort_values("evento").reset_index(drop=True)
    dim["indicador_id"] = range(1, len(dim) + 1)

    return dim[["indicador_id", "evento", "familia_medida", "unidade", "tipo_indicador"]]


def build_dim_abrangencia(stg: pd.DataFrame) -> pd.DataFrame:
    return _surrogate_key_table(stg["abrangencia"], "abrangencia_id", "abrangencia")


def build_dim_agente(stg: pd.DataFrame) -> pd.DataFrame:
    return _surrogate_key_table(stg["agente"], "agente_id", "agente")


def build_dim_arma(stg: pd.DataFrame) -> pd.DataFrame:
    return _surrogate_key_table(stg["arma"], "arma_id", "arma")


def build_dim_faixa_etaria(stg: pd.DataFrame) -> pd.DataFrame:
    return _surrogate_key_table(stg["faixa_etaria"], "faixa_etaria_id", "faixa_etaria")


def build_dim_sexo() -> pd.DataFrame:
    valores = [SEXO_FEMININO, SEXO_MASCULINO, SEXO_NAO_INFORMADO]
    return pd.DataFrame({"sexo_id": range(1, len(valores) + 1), "sexo": valores})


def build_all_dimensions(stg: pd.DataFrame) -> dict[str, pd.DataFrame]:
    dims = {
        "dim_tempo": build_dim_tempo(stg),
        "dim_localidade": build_dim_localidade(stg),
        "dim_indicador": build_dim_indicador(stg),
        "dim_abrangencia": build_dim_abrangencia(stg),
        "dim_agente": build_dim_agente(stg),
        "dim_arma": build_dim_arma(stg),
        "dim_faixa_etaria": build_dim_faixa_etaria(stg),
        "dim_sexo": build_dim_sexo(),
    }
    for name, df in dims.items():
        logger.info(f"{name}: {len(df)} linhas")
    return dims
