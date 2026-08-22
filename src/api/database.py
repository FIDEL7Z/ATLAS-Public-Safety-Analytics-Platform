"""Camada centralizada de conexão com o PostgreSQL (SQLAlchemy).

A API é somente leitura e consulta exclusivamente tabelas/views já existentes
(Fases 1-2) — nenhuma migração/DDL roda a partir daqui.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api.config import settings

# pool_size=5 / max_overflow=10: até 15 conexões simultâneas. Dimensionado
# para uma API de leitura de portfólio/demo (não um serviço de alto tráfego
# em produção) — folga suficiente para múltiplas abas do Swagger e um
# frontend futuro (Fase 6) sem esgotar as conexões default do Postgres (100).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def check_database_connection() -> bool:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception:
        return False
