"""Carga das camadas staging/dimensões/fato no PostgreSQL (Docker).

Usa COPY (via psycopg2) em vez de INSERT linha a linha — necessário para
carregar ~2M+ linhas em tempo hábil.
"""
import io
import os
from pathlib import Path

import pandas as pd
import psycopg2
from dotenv import load_dotenv

from src.config import ROOT_DIR, get_logger

logger = get_logger(__name__)

load_dotenv(ROOT_DIR / ".env")

DDL_FILES_IN_ORDER = [
    ROOT_DIR / "sql" / "staging" / "001_create_stg_sinesp.sql",
    ROOT_DIR / "sql" / "dimensions" / "001_create_dimensions.sql",
    ROOT_DIR / "sql" / "facts" / "001_create_fact_indicadores.sql",
]


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "atlas"),
        user=os.environ.get("POSTGRES_USER", "atlas"),
        password=os.environ.get("POSTGRES_PASSWORD", "atlas_dev_only"),
    )


def run_ddl(conn) -> None:
    with conn.cursor() as cur:
        for sql_file in DDL_FILES_IN_ORDER:
            logger.info(f"Executando DDL: {sql_file.relative_to(ROOT_DIR)}")
            cur.execute(sql_file.read_text(encoding="utf-8"))
    conn.commit()


def copy_dataframe(conn, df: pd.DataFrame, table_name: str) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="", date_format="%Y-%m-%d")
    buf.seek(0)

    columns = ", ".join(df.columns)
    with conn.cursor() as cur:
        cur.copy_expert(
            f"COPY {table_name} ({columns}) FROM STDIN WITH (FORMAT csv, NULL '')",
            buf,
        )
    conn.commit()
    logger.info(f"COPY concluído: {len(df):,} linhas -> {table_name}")


def load_all(stg: pd.DataFrame, dims: dict[str, pd.DataFrame], fact: pd.DataFrame) -> None:
    conn = get_connection()
    try:
        run_ddl(conn)

        copy_dataframe(conn, stg, "stg_sinesp")

        # ordem de carga: dimensões antes do fato (respeita as FKs)
        for name in ["dim_tempo", "dim_localidade", "dim_indicador", "dim_abrangencia",
                     "dim_agente", "dim_arma", "dim_faixa_etaria", "dim_sexo"]:
            copy_dataframe(conn, dims[name], name)

        copy_dataframe(conn, fact, "fact_indicadores")
    finally:
        conn.close()
