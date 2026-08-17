"""Camada RAW: leitura pura dos arquivos BancoVDE <ano>.xlsx.

Os arquivos originais em data/raw/ nunca são alterados. Esta função apenas
lê e retorna os dados exatamente como estão na fonte, sem nenhuma
transformação, tipagem adicional ou remoção de linhas.
"""
import time

import pandas as pd

from src.config import RAW_FILES, get_logger

logger = get_logger(__name__)

RAW_COLUMNS = [
    "uf", "municipio", "evento", "data_referencia", "agente", "arma",
    "faixa_etaria", "feminino", "masculino", "nao_informado", "total_vitima",
    "total", "total_peso", "abrangencia",
]


def load_raw_year(ano: int) -> pd.DataFrame:
    path = RAW_FILES[ano]
    if not path.exists():
        raise FileNotFoundError(f"Arquivo raw não encontrado para {ano}: {path}")

    t0 = time.time()
    logger.info(f"Carregando RAW {ano}: {path.name}")
    df = pd.read_excel(path, sheet_name=str(ano), engine="openpyxl")
    elapsed = time.time() - t0

    missing = set(RAW_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Arquivo {ano} não contém as colunas esperadas: {missing}")

    logger.info(f"RAW {ano} carregado em {elapsed:.1f}s — {len(df):,} linhas, {df.shape[1]} colunas")
    return df


def load_all_raw() -> dict[int, pd.DataFrame]:
    return {ano: load_raw_year(ano) for ano in sorted(RAW_FILES)}
