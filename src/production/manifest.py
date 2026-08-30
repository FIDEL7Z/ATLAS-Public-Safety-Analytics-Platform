"""Manifesto do dataset de produção — rastreabilidade da build.

Grava, ao lado do atlas_public.duckdb, um manifest.json com: quando foi
construído, de quais Parquet (com hash), e o que o arquivo contém (tabelas,
views, contagens, tamanho). Serve para auditoria e para o deploy saber se o
dataset está atualizado.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path, limit_mb: int = 512) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_manifest(
    duckdb_path: Path,
    source_parquets: list[Path],
    tables: dict[str, int],
    views: list[str],
    duckdb_version: str,
) -> dict:
    return {
        "dataset": "atlas_public",
        "phase": "6 — Sentinel Production Dataset",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "duckdb_engine_version": duckdb_version,
        "file": {
            "path": str(duckdb_path),
            "size_bytes": duckdb_path.stat().st_size,
            "size_mb": round(duckdb_path.stat().st_size / 1_000_000, 2),
        },
        "source_parquets": [
            {
                "name": p.name,
                "size_bytes": p.stat().st_size,
                "sha256": _sha256(p)[:16],
            }
            for p in sorted(source_parquets)
        ],
        "tables": {name: tables[name] for name in sorted(tables)},
        "views": sorted(views),
        "notes": [
            "fact_indicadores no grão completo — nenhuma linha agregada/removida.",
            "valor: NUMERIC(14,3) do Postgres -> DECIMAL(14,3) no DuckDB (paridade de SUM).",
            "stg_sinesp NÃO incluída; vw_qualidade_resumo materializada como tabela de 1 linha.",
            "views vw_fato_enriquecido / vw_pesos_* omitidas (não usadas pela API).",
        ],
    }


def write_manifest(manifest: dict, out_dir: Path) -> Path:
    out = out_dir / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return out
