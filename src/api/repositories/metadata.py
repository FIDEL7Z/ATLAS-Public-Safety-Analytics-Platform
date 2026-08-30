"""Repositório de metadados — resumo do dataset (analytics.vw_qualidade_resumo,
Fase 3) e listas de valores disponíveis para filtros (direto das dimensões,
nunca hardcoded — regra 20 da Fase 5)."""
from sqlalchemy import text
from sqlalchemy.orm import Session

_SELECT_RESUMO = text("""
    SELECT periodo_inicio, periodo_fim, anos_parciais, n_indicadores, n_ufs, n_municipios_distintos
    FROM analytics.vw_qualidade_resumo
""")

_SELECT_UFS = text("SELECT DISTINCT uf, regiao FROM dim_localidade ORDER BY uf")

_SELECT_YEARS = text("SELECT DISTINCT ano FROM dim_tempo ORDER BY ano")

_SELECT_ABRANGENCIAS = text("SELECT abrangencia FROM dim_abrangencia ORDER BY abrangencia")

_SELECT_MUNICIPALITIES = text("""
    SELECT uf, municipio FROM dim_localidade
    WHERE (CAST(:uf AS VARCHAR) IS NULL OR uf = :uf)
    ORDER BY uf, municipio
""")


def get_resumo(db: Session) -> dict:
    row = db.execute(_SELECT_RESUMO).mappings().first()
    return dict(row)


def list_ufs(db: Session) -> list[dict]:
    return [dict(row) for row in db.execute(_SELECT_UFS).mappings().all()]


def list_years(db: Session) -> list[int]:
    return [row[0] for row in db.execute(_SELECT_YEARS).all()]


def list_abrangencias(db: Session) -> list[dict]:
    return [dict(row) for row in db.execute(_SELECT_ABRANGENCIAS).mappings().all()]


def list_municipalities(db: Session, uf: str | None) -> list[dict]:
    return [dict(row) for row in db.execute(_SELECT_MUNICIPALITIES, {"uf": uf}).mappings().all()]
