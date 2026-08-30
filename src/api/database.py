"""Camada centralizada de conexão com o banco (SQLAlchemy).

A API é somente leitura e consulta exclusivamente tabelas/views já existentes
— nenhuma migração/DDL roda a partir daqui.

Dois engines (Fase 6), selecionados por settings.database_engine:
  - postgres: pool de conexões (Development).
  - duckdb:   arquivo embarcado, read-only, NullPool (produção/serving).
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from src.api.config import settings

if settings.is_duckdb:
    # DuckDB embarcado, somente leitura. Pool pequeno de conexões PERSISTENTES:
    # abrir o arquivo custa ~15-20 ms (catálogo + parse das views), então
    # reaprovamos as conexões em vez de abrir uma por request. read_only=True
    # impede qualquer escrita e permite N processos lendo o mesmo arquivo.
    # As conexões DuckDB são thread-safe (serializam internamente).
    engine = create_engine(
        settings.database_url,
        connect_args={"read_only": True},
        poolclass=QueuePool,
        pool_size=4,
        max_overflow=8,
        pool_recycle=-1,
        future=True,
    )
else:
    # pool_size=5 / max_overflow=10: até 15 conexões simultâneas. Dimensionado
    # para uma API de leitura de portfólio/demo — folga para múltiplas abas do
    # Swagger e o frontend sem esgotar as conexões default do Postgres (100).
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
