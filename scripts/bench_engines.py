"""Benchmark: Sentinel.io Analytics API sobre PostgreSQL vs DuckDB.

Sobe a API (uvicorn) em cada engine, aquece, mede N repetições por endpoint e
imprime uma tabela comparativa (tempo médio, máximo, tamanho da resposta).

Uso:  python -m scripts.bench_engines [--reps 25]
Requer: PostgreSQL Development no ar + data/production/atlas_public.duckdb.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from statistics import mean

import httpx

BASE = "http://127.0.0.1:8071"
ENDPOINTS = [
    ("/api/v1/health", "health"),
    ("/api/v1/indicators", "indicators"),
    ("/api/v1/kpis", "kpis (sem filtro)"),
    ("/api/v1/kpis?indicator_id=25&ano=2025", "kpis (filtrado)"),
    ("/api/v1/temporal?indicator_id=25", "temporal"),
    ("/api/v1/temporal/yoy?indicator_id=25&base_year=2024&comparison_year=2025", "temporal/yoy"),
    ("/api/v1/geography/uf?indicator_id=25&ano=2025", "geography/uf"),
    ("/api/v1/geography/municipalities?indicator_id=25&page_size=50", "geography/municipalities"),
    ("/api/v1/rankings/uf?indicator_id=25&ano=2025", "rankings/uf"),
    ("/api/v1/rankings/municipalities?indicator_id=25&ano=2025", "rankings/municipalities"),
    ("/api/v1/rankings/indicators?grupo_semantico=Ocorr%C3%AAncias&ano=2025", "rankings/indicators"),
    ("/api/v1/radar?min_abs_z=2&limit=100", "radar"),
    ("/api/v1/metadata", "metadata"),
]


def _wait_up(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if httpx.get(f"{BASE}/api/v1/health", timeout=2).status_code == 200:
                return
        except Exception:
            time.sleep(0.4)
    raise RuntimeError("API não subiu a tempo")


def _bench_engine(engine: str, reps: int) -> dict[str, dict]:
    env = {**os.environ, "DATABASE_ENGINE": engine}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1",
         "--port", "8071", "--log-level", "warning"],
        env=env,
    )
    try:
        _wait_up()
        results: dict[str, dict] = {}
        with httpx.Client(timeout=60) as client:
            for path, label in ENDPOINTS:
                client.get(f"{BASE}{path}")  # aquece (planner / cache de página)
                samples, size = [], 0
                for _ in range(reps):
                    t0 = time.perf_counter()
                    r = client.get(f"{BASE}{path}")
                    samples.append((time.perf_counter() - t0) * 1000)
                    size = len(r.content)
                    assert r.status_code == 200, f"{path} -> {r.status_code}"
                results[label] = {
                    "avg_ms": round(mean(samples), 1),
                    "max_ms": round(max(samples), 1),
                    "bytes": size,
                }
        return results
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=25)
    args = ap.parse_args()

    print(f"Benchmark — {args.reps} reps/endpoint\n")
    pg = _bench_engine("postgres", args.reps)
    time.sleep(1)
    dd = _bench_engine("duckdb", args.reps)

    print(f"\n{'endpoint':<28} {'PG avg':>9} {'PG max':>9} {'DDB avg':>9} {'DDB max':>9} {'ganho':>7} {'bytes':>8}")
    print("-" * 84)
    for _, label in ENDPOINTS:
        p, d = pg[label], dd[label]
        gain = f"{p['avg_ms'] / d['avg_ms']:.1f}x" if d["avg_ms"] else "-"
        match = "=" if p["bytes"] == d["bytes"] else f"PG {p['bytes']} / DDB {d['bytes']}"
        print(f"{label:<28} {p['avg_ms']:>8}m {p['max_ms']:>8}m {d['avg_ms']:>8}m {d['max_ms']:>8}m {gain:>7} {match:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
