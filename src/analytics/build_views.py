"""Aplica a camada analítica (sql/analytics/*.sql) no PostgreSQL.

Não toca em stg_sinesp, dim_* ou fact_indicadores — apenas cria o schema
`analytics` e suas views, sobre os dados já carregados pela Fase 1.

Uso: python -m src.analytics.build_views
"""
from src.config import ROOT_DIR, get_logger
from src.loading.postgres_loader import get_connection

logger = get_logger(__name__)

ANALYTICS_SQL_DIR = ROOT_DIR / "sql" / "analytics"


def build_all_views() -> None:
    sql_files = sorted(ANALYTICS_SQL_DIR.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"Nenhum arquivo .sql encontrado em {ANALYTICS_SQL_DIR}")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            for sql_file in sql_files:
                logger.info(f"Aplicando {sql_file.relative_to(ROOT_DIR)}")
                cur.execute(sql_file.read_text(encoding="utf-8"))
        conn.commit()
        logger.info(f"Camada analítica aplicada: {len(sql_files)} arquivo(s) SQL executado(s).")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    build_all_views()
