"""Configuração da ATLAS Analytics API — variáveis de ambiente, nada hardcoded.

Reaproveita as variáveis POSTGRES_* já usadas pelo ETL (Fases 1-2), em vez de
introduzir um segundo conjunto de nomes (DATABASE_*) para a mesma conexão —
evita duas fontes de verdade para a mesma credencial. API_HOST/API_PORT/
CORS_ORIGINS são as únicas variáveis novas da Fase 5.

Fase 6 — dois modos de banco, escolhidos por DATABASE_ENGINE:
  - "postgres" (padrão): ambiente Development / engenharia de dados.
  - "duckdb": produção (serving), lê data/production/atlas_public.duckdb,
    somente leitura. Ver docs/PRODUCTION_ARCHITECTURE.md.
"""
import os

from dotenv import load_dotenv

from src.config import ROOT_DIR

load_dotenv(ROOT_DIR / ".env")

_DEFAULT_DUCKDB = ROOT_DIR / "data" / "production" / "atlas_public.duckdb"


class Settings:
    database_engine: str = os.environ.get("DATABASE_ENGINE", "postgres").strip().lower()
    duckdb_path: str = os.environ.get("DUCKDB_PATH", str(_DEFAULT_DUCKDB))

    postgres_host: str = os.environ.get("POSTGRES_HOST", "localhost")
    postgres_port: str = os.environ.get("POSTGRES_PORT", "5433")
    postgres_db: str = os.environ.get("POSTGRES_DB", "atlas")
    postgres_user: str = os.environ.get("POSTGRES_USER", "atlas")
    postgres_password: str = os.environ.get("POSTGRES_PASSWORD", "atlas_dev_only")

    api_host: str = os.environ.get("API_HOST", "0.0.0.0")
    api_port: int = int(os.environ.get("API_PORT", "8000"))

    cors_origins: list[str] = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
        if o.strip()
    ]

    max_page_size: int = 100
    default_page_size: int = 50

    @property
    def is_duckdb(self) -> bool:
        return self.database_engine == "duckdb"

    @property
    def database_url(self) -> str:
        if self.is_duckdb:
            return f"duckdb:///{self.duckdb_path}"
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
