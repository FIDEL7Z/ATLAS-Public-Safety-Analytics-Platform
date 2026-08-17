"""Camada STAGING: normalização 1:1 do RAW, sem remoção nem agregação de linhas.

stg_sinesp preserva exatamente o número de linhas do RAW (validado em
validation/reconciliation.py). A única coluna do RAW que não é transportada
é `total_vitima`, porque ela é sempre derivável (feminino + masculino +
nao_informado) e não deve ser persistida (Fase 0.5, regra de modelagem).
"""
import pandas as pd

from src.config import get_logger

logger = get_logger(__name__)

STAGING_COLUMNS = [
    "uf", "municipio", "evento", "data_referencia", "agente", "arma",
    "faixa_etaria", "feminino", "masculino", "nao_informado", "total",
    "total_peso", "abrangencia", "ano_origem",
]

_STRING_COLS = ["uf", "municipio", "evento", "agente", "arma", "faixa_etaria", "abrangencia"]
_NUMERIC_COLS = ["feminino", "masculino", "nao_informado", "total", "total_peso"]


def build_staging(raw_by_year: dict[int, pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for ano, df in sorted(raw_by_year.items()):
        f = df.copy()
        f["ano_origem"] = ano
        frames.append(f)

    stg = pd.concat(frames, ignore_index=True)

    for c in _STRING_COLS:
        stg[c] = stg[c].astype("string").str.strip()

    for c in _NUMERIC_COLS:
        stg[c] = pd.to_numeric(stg[c], errors="raise")

    stg["data_referencia"] = pd.to_datetime(stg["data_referencia"]).dt.normalize()
    stg["ano_origem"] = stg["ano_origem"].astype("int16")

    stg = stg[STAGING_COLUMNS]

    n_raw = sum(len(df) for df in raw_by_year.values())
    if len(stg) != n_raw:
        raise AssertionError(
            f"Staging alterou a contagem de linhas do RAW: RAW={n_raw:,} STAGING={len(stg):,}. "
            "A camada staging não pode remover ou adicionar linhas."
        )

    logger.info(f"STAGING construído: {len(stg):,} linhas (idêntico ao RAW), {stg.shape[1]} colunas")
    return stg
