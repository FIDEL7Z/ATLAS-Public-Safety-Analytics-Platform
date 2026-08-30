"""Production Dataset Builder — Fase 6.

Constrói data/production/atlas_public.duckdb: réplica read-only, portátil e
otimizada dos dados que a Sentinel.io Analytics API consome, derivada
AUTOMATICAMENTE do output validado do ETL (data/processed/*.parquet — os
mesmos dados carregados no PostgreSQL Development).

O PostgreSQL continua sendo a fonte de verdade e o ambiente de engenharia.
Este arquivo é apenas a camada de serving de produção. Nada aqui altera o
Postgres, o ETL ou os arquivos SQL da Fase 2.

Uso:  python -m src.production.build_dataset [--out CAMINHO]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

import duckdb

from src.config import DIMENSIONS_DIR, FACTS_DIR, ROOT_DIR, STAGING_DIR
from src.production.manifest import build_manifest, write_manifest
from src.production.validation import format_report, run_checks

# Logger próprio (stdout) — não escreve no data/quality_reports/etl_run.log,
# que é artefato do ETL. A build de produção não é parte do pipeline de ETL.
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger("atlas.production")

PRODUCTION_DIR = ROOT_DIR / "data" / "production"
DEFAULT_OUT = PRODUCTION_DIR / "atlas_public.duckdb"
ANALYTICS_SQL_DIR = ROOT_DIR / "sql" / "analytics"

FACT_PARQUET = FACTS_DIR / "fact_indicadores.parquet"
STAGING_PARQUET = STAGING_DIR / "stg_sinesp.parquet"
DIM_NAMES = [
    "dim_tempo", "dim_localidade", "dim_indicador", "dim_abrangencia",
    "dim_agente", "dim_arma", "dim_faixa_etaria", "dim_sexo",
]

# Arquivos da camada analítica aplicados VERBATIM no dataset final.
# 001 (vw_fato_enriquecido usa f.fact_id, ausente na produção) e 005 (depende
# de 001) são omitidos — nenhuma das 3 views que eles criam é usada pela API.
# 007 NÃO entra no arquivo final: depende de stg_sinesp. É executado à parte,
# contra a staging, só para materializar vw_qualidade_resumo (ver abaixo).
ANALYTICS_FILES = [
    "002_visoes_dimensionais.sql",
    "003_visoes_temporais.sql",
    "004_rankings.sql",
    "006_powerbi_dim_indicador.sql",
]
QUALITY_SQL_FILE = "007_data_quality_views.sql"


def _pq(path: Path) -> str:
    """read_parquet('...') com o caminho inline — CREATE VIEW / COPY não
    aceitam prepared parameters no DuckDB. Caminho é interno (nunca input
    de usuário); ainda assim escapamos aspas simples."""
    literal = str(path).replace("\\", "/").replace("'", "''")
    return f"read_parquet('{literal}')"


def _require_parquets() -> list[Path]:
    needed = [FACT_PARQUET, STAGING_PARQUET] + [DIMENSIONS_DIR / f"{d}.parquet" for d in DIM_NAMES]
    missing = [p for p in needed if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Parquet do ETL ausente(s):\n  " + "\n  ".join(str(m) for m in missing)
            + "\n\nRode o ETL primeiro:  python -m src.run_etl"
        )
    return needed


def _load_fact(con: duckdb.DuckDBPyConnection) -> None:
    # valor: NUMERIC(14,3) no Postgres. O Parquet guarda DOUBLE; sem o cast, o
    # SUM do DuckDB acumula erro de ponto flutuante e diverge do Postgres.
    # ids -> INTEGER (mesma semântica do schema, arquivo menor). fact_id
    # (BIGSERIAL) é omitido: a API nunca filtra por ele.
    con.execute(
        """
        CREATE TABLE fact_indicadores AS
        SELECT
            CAST(tempo_id        AS INTEGER)       AS tempo_id,
            CAST(localidade_id   AS INTEGER)       AS localidade_id,
            CAST(indicador_id    AS INTEGER)       AS indicador_id,
            CAST(abrangencia_id  AS INTEGER)       AS abrangencia_id,
            CAST(agente_id       AS INTEGER)       AS agente_id,
            CAST(arma_id         AS INTEGER)       AS arma_id,
            CAST(faixa_etaria_id AS INTEGER)       AS faixa_etaria_id,
            CAST(sexo_id         AS INTEGER)       AS sexo_id,
            CAST(valor           AS DECIMAL(14,3)) AS valor,
            CAST(ano_origem      AS SMALLINT)      AS ano_origem
        FROM read_parquet(?)
        """,
        [str(FACT_PARQUET)],
    )


def _load_dims(con: duckdb.DuckDBPyConnection) -> None:
    for name in DIM_NAMES:
        con.execute(
            f"CREATE TABLE {name} AS SELECT * FROM read_parquet(?)",
            [str(DIMENSIONS_DIR / f"{name}.parquet")],
        )


def _apply_analytics(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    for fname in ANALYTICS_FILES:
        sql = (ANALYTICS_SQL_DIR / fname).read_text(encoding="utf-8")
        logger.info(f"aplicando {fname}")
        con.execute(sql)


def _compute_quality_resumo(resumo_parquet: Path) -> None:
    """Calcula vw_qualidade_resumo pela SQL REAL da view (007), numa conexão
    em memória com a staging — que NUNCA toca o arquivo final. O resultado
    (1 linha) é gravado num Parquet temporário.

    Motivo: a API lê 6 das 11 colunas de vw_qualidade_resumo; as 2 que
    dependem de stg_sinesp (linhas_raw_staging, pct_nao_informado_medio) não
    entram em nenhuma resposta. Carregar 213 MB de staging só para elas
    infla o dataset — então materializamos o resultado.
    """
    scratch = duckdb.connect(":memory:")
    try:
        scratch.execute(f"CREATE VIEW fact_indicadores AS SELECT * FROM {_pq(FACT_PARQUET)}")
        for name in DIM_NAMES:
            scratch.execute(f"CREATE VIEW {name} AS SELECT * FROM {_pq(DIMENSIONS_DIR / f'{name}.parquet')}")
        scratch.execute(f"CREATE VIEW stg_sinesp AS SELECT * FROM {_pq(STAGING_PARQUET)}")
        scratch.execute("CREATE SCHEMA analytics")
        scratch.execute((ANALYTICS_SQL_DIR / QUALITY_SQL_FILE).read_text(encoding="utf-8"))
        out_literal = str(resumo_parquet).replace("\\", "/").replace("'", "''")
        scratch.execute(
            f"COPY (SELECT * FROM analytics.vw_qualidade_resumo) TO '{out_literal}' (FORMAT parquet)"
        )
    finally:
        scratch.close()


def _materialize_quality_resumo(con: duckdb.DuckDBPyConnection, resumo_parquet: Path) -> None:
    con.execute(
        "CREATE TABLE analytics.vw_qualidade_resumo AS SELECT * FROM read_parquet(?)",
        [str(resumo_parquet)],
    )


def _inventory(con: duckdb.DuckDBPyConnection) -> tuple[dict[str, int], list[str]]:
    tables = {}
    for (schema, name) in con.execute(
        "SELECT schema_name, table_name FROM duckdb_tables() ORDER BY 1, 2"
    ).fetchall():
        key = name if schema == "main" else f"{schema}.{name}"
        tables[key] = con.execute(f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
    views = [
        f"{schema}.{name}" if schema != "main" else name
        for (schema, name) in con.execute(
            "SELECT schema_name, view_name FROM duckdb_views() WHERE NOT internal ORDER BY 1, 2"
        ).fetchall()
    ]
    return tables, views


def build(out_path: Path = DEFAULT_OUT) -> dict:
    t0 = time.time()
    source_parquets = _require_parquets()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    for sidecar in (out_path.with_suffix(".duckdb.wal"),):
        if sidecar.exists():
            sidecar.unlink()

    logger.info("=" * 78)
    logger.info(f"Production Dataset Builder — destino: {out_path}")
    logger.info("=" * 78)

    resumo_parquet = out_path.parent / "_resumo.parquet"
    logger.info("calculando vw_qualidade_resumo (SQL da view 007, staging em memória)")
    _compute_quality_resumo(resumo_parquet)

    con = duckdb.connect(str(out_path))
    try:
        expected_fact_rows = con.execute(
            "SELECT count(*) FROM read_parquet(?)", [str(FACT_PARQUET)]
        ).fetchone()[0]

        logger.info("carregando fact_indicadores (grão completo)")
        _load_fact(con)
        logger.info("carregando 8 dimensões")
        _load_dims(con)

        logger.info("aplicando camada analítica (verbatim, exceto 001/005/007)")
        _apply_analytics(con)

        logger.info("materializando vw_qualidade_resumo (tabela de 1 linha, sem staging)")
        _materialize_quality_resumo(con, resumo_parquet)

        tables, views = _inventory(con)

        logger.info("validando dataset")
        checks = run_checks(con, expected_fact_rows)

        con.execute("CHECKPOINT")
    finally:
        con.close()
        resumo_parquet.unlink(missing_ok=True)

    report = format_report(checks)
    failed = [c for c in checks if not c.ok]

    manifest = build_manifest(
        duckdb_path=out_path,
        source_parquets=source_parquets,
        tables=tables,
        views=views,
        duckdb_version=duckdb.__version__,
    )
    manifest_path = write_manifest(manifest, out_path.parent)

    elapsed = time.time() - t0
    logger.info("-" * 78)
    logger.info(f"\n{report}")
    logger.info("-" * 78)
    logger.info(f"arquivo: {out_path}  ({manifest['file']['size_mb']} MB)")
    logger.info(f"tabelas: {len(tables)}  ·  views: {len(views)}")
    logger.info(f"manifest: {manifest_path}")
    logger.info(f"concluído em {elapsed:.1f}s")
    logger.info("=" * 78)

    return {
        "out_path": str(out_path),
        "size_mb": manifest["file"]["size_mb"],
        "tables": tables,
        "views": views,
        "checks_ok": len(checks) - len(failed),
        "checks_total": len(checks),
        "failed": [c.name for c in failed],
        "elapsed_s": round(elapsed, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Constrói o atlas_public.duckdb (Fase 6).")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="caminho do .duckdb de saída")
    args = parser.parse_args()

    result = build(args.out)
    print(result)
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
