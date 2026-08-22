"""Testes da Sentinel.io Analytics API (Fase 5) contra o PostgreSQL real.

Mesmo padrão de tests/test_analytics_sql.py: testes de integração, pulados
automaticamente se o Postgres não estiver acessível.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.database import check_database_connection
from src.api.main import app

if not check_database_connection():
    pytest.skip("PostgreSQL indisponível — testes da API pulados.", allow_module_level=True)

client = TestClient(app)


@pytest.fixture(scope="module")
def homicidio_doloso_id() -> int:
    r = client.get("/api/v1/indicators")
    for item in r.json()["data"]:
        if item["evento"] == "Homicídio doloso":
            return item["id"]
    pytest.fail("'Homicídio doloso' não encontrado em /api/v1/indicators")


# ---------------------------------------------------------------- health ---

def test_health_ok():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok", "service": "atlas-api", "database": "connected"}


def test_health_database_unavailable():
    with patch("src.api.routers.health.check_database_connection", return_value=False):
        r = client.get("/api/v1/health")
    assert r.status_code == 503
    body = r.json()
    assert body["status"] == "error"
    assert body["database"] == "disconnected"
    # nunca vaza senha/host/detalhe de exceção
    assert "atlas_dev_only" not in r.text
    assert "traceback" not in r.text.lower()


# ------------------------------------------------------------ indicators ---

def test_list_indicators_returns_all_31_from_db():
    r = client.get("/api/v1/indicators")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 31
    assert len(body["data"]) == 31
    first = body["data"][0]
    assert set(first.keys()) == {"id", "evento", "familia_medida", "unidade", "tipo_indicador", "grupo_semantico"}


def test_get_indicator_detail(homicidio_doloso_id):
    r = client.get(f"/api/v1/indicators/{homicidio_doloso_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["evento"] == "Homicídio doloso"
    assert body["familia_medida"] == "vitima"
    assert body["unidade"] == "pessoas"


def test_get_indicator_not_found():
    r = client.get("/api/v1/indicators/999999")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "NOT_FOUND", "message": "Indicador não encontrado"}}


def test_get_indicator_invalid_type_returns_422():
    r = client.get("/api/v1/indicators/nao-e-um-numero")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ------------------------------------------------------------------ kpis ---

def test_kpis_without_filter_never_mixes_units():
    r = client.get("/api/v1/kpis")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 31
    assert len({d["indicator_id"] for d in data}) == 31  # um indicador por linha, nunca somado entre si


def test_kpis_with_filters_echoes_them(homicidio_doloso_id):
    r = client.get("/api/v1/kpis", params={"indicator_id": homicidio_doloso_id, "ano": 2025})
    assert r.status_code == 200
    body = r.json()
    assert body["filters"] == {
        "indicator_id": homicidio_doloso_id, "uf": None, "municipio": None, "ano": 2025, "abrangencia": None,
    }
    assert len(body["data"]) == 1
    assert body["data"][0]["unit"] == "pessoas"


def test_kpis_invalid_uf_length_returns_422():
    r = client.get("/api/v1/kpis", params={"uf": "SAO"})
    assert r.status_code == 422


# -------------------------------------------------------------- temporal ---

def test_temporal_requires_indicator_id():
    r = client.get("/api/v1/temporal")
    assert r.status_code == 422


def test_temporal_series_full_year_not_flagged_partial(homicidio_doloso_id):
    r = client.get("/api/v1/temporal", params={"indicator_id": homicidio_doloso_id, "ano_inicio": 2025, "ano_fim": 2025})
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 12
    assert all(p["is_partial_year"] is False for p in body["data"])


def test_temporal_series_2026_flagged_partial(homicidio_doloso_id):
    r = client.get("/api/v1/temporal", params={"indicator_id": homicidio_doloso_id, "ano_inicio": 2026, "ano_fim": 2026})
    body = r.json()
    assert len(body["data"]) == 6
    assert all(p["is_partial_year"] is True for p in body["data"])


def test_yoy_uses_comparable_period_not_full_vs_partial(homicidio_doloso_id):
    r = client.get(
        "/api/v1/temporal/yoy",
        params={"indicator_id": homicidio_doloso_id, "base_year": 2025, "comparison_year": 2026},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["comparison"]["months_compared"] == 6  # nunca 12 vs 6
    assert body["comparison"]["partial_period"] is True
    # valores conferidos manualmente contra o Postgres (docs/POWERBI_VALIDATION.md)
    assert body["base_value"] == 16081.0
    assert body["comparison_value"] == 13931.0
    assert body["variation_percent"] == -13.37


def test_yoy_indicator_not_found():
    r = client.get("/api/v1/temporal/yoy", params={"indicator_id": 999999})
    assert r.status_code == 404


# ------------------------------------------------------------- geography ---

def test_geography_uf_matches_known_ranking(homicidio_doloso_id):
    r = client.get("/api/v1/geography/uf", params={"indicator_id": homicidio_doloso_id, "ano": 2025})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data[0] == {"uf": "BA", "regiao": "Nordeste", "value": 3663.0}


def test_geography_municipalities_pagination(homicidio_doloso_id):
    r = client.get(
        "/api/v1/geography/municipalities",
        params={"indicator_id": homicidio_doloso_id, "uf": "SP", "page": 1, "page_size": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1 and body["page_size"] == 5
    assert len(body["data"]) <= 5
    assert body["total"] >= len(body["data"])


def test_geography_municipalities_page_size_capped_at_100():
    r = client.get("/api/v1/geography/municipalities", params={"indicator_id": 1, "page_size": 101})
    assert r.status_code == 422


def test_geography_indicator_not_found():
    r = client.get("/api/v1/geography/uf", params={"indicator_id": 999999})
    assert r.status_code == 404


# -------------------------------------------------------------- rankings ---

def test_ranking_uf_ranks_start_at_1(homicidio_doloso_id):
    r = client.get("/api/v1/rankings/uf", params={"indicator_id": homicidio_doloso_id, "ano": 2025, "limit": 5})
    assert r.status_code == 200
    ranks = [d["rank"] for d in r.json()["data"]]
    assert ranks == list(range(1, len(ranks) + 1))


def test_ranking_municipalities(homicidio_doloso_id):
    r = client.get("/api/v1/rankings/municipalities", params={"indicator_id": homicidio_doloso_id, "ano": 2025, "limit": 3})
    assert r.status_code == 200
    assert len(r.json()["data"]) == 3


def test_ranking_indicators_within_group():
    r = client.get("/api/v1/rankings/indicators", params={"grupo_semantico": "Vítimas", "ano": 2025, "limit": 5})
    assert r.status_code == 200
    assert all(d["grupo_semantico"] == "Vítimas" for d in r.json()["data"])


def test_ranking_indicators_invalid_group_returns_400():
    r = client.get("/api/v1/rankings/indicators", params={"grupo_semantico": "Grupo Inexistente", "ano": 2025})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_PARAMETER"


# ------------------------------------------------------------------ radar ---

def test_radar_returns_known_anomaly():
    r = client.get("/api/v1/radar", params={"min_abs_z": 3, "limit": 20})
    assert r.status_code == 200
    data = r.json()["data"]
    assert any(
        d["indicator"] == "Morte por intervenção de Agente do Estado" and d["year"] == 2025 and d["month"] == 10
        for d in data
    )
    match = next(d for d in data if d["year"] == 2025 and d["month"] == 10 and d["indicator"] == "Morte por intervenção de Agente do Estado")
    assert match["z_score"] == 3.03


def test_radar_schema_never_implies_causality():
    from src.api.schemas.radar import RadarItem

    description = (RadarItem.model_fields["z_score"].description or "").lower()
    assert "causalidade" in description
    assert "crime" not in description


# --------------------------------------------------------------- metadata ---

def test_metadata_overview_reflects_real_dataset():
    r = client.get("/api/v1/metadata")
    assert r.status_code == 200
    body = r.json()
    assert body["dataset"] == {"start": "2024-01", "end": "2026-06", "partial_year": True}
    assert body["coverage"] == {"indicators": 31, "ufs": 27, "municipalities": 5298}


def test_metadata_ufs_not_hardcoded():
    r = client.get("/api/v1/metadata/ufs")
    assert r.status_code == 200
    assert len(r.json()) == 27


def test_metadata_years():
    r = client.get("/api/v1/metadata/years")
    assert r.json() == [2024, 2025, 2026]


def test_metadata_municipalities_filtered_by_uf():
    r = client.get("/api/v1/metadata/municipalities", params={"uf": "PB"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert all(m["uf"] == "PB" for m in data)


# ---------------------------------------------------------- docs/openapi ---

def test_swagger_docs_available():
    assert client.get("/docs").status_code == 200


def test_openapi_metadata():
    body = client.get("/openapi.json").json()
    assert body["info"]["title"] == "Sentinel.io Analytics API"
    assert body["info"]["version"] == "1.0.0"


def test_only_get_methods_exposed_read_only_api():
    body = client.get("/openapi.json").json()
    for path, methods in body["paths"].items():
        assert set(methods.keys()) <= {"get"}, f"{path} expõe método de escrita — API deve ser somente leitura"
