"""Fase 6 — Sentinel Production Dataset.

Camada que constrói o dataset de serving (DuckDB, read-only) a partir do
output validado do ETL. O PostgreSQL continua sendo a fonte de verdade e o
ambiente de engenharia de dados; este pacote apenas produz uma réplica
portátil e otimizada para a API pública.

Ver docs/PRODUCTION_ARCHITECTURE.md.
"""
