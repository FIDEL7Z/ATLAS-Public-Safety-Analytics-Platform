from sqlalchemy.orm import Session

from src.api.repositories import metadata as repo


def get_metadata(db: Session) -> dict:
    r = repo.get_resumo(db)
    return {
        "dataset": {
            "start": r["periodo_inicio"].strftime("%Y-%m"),
            "end": r["periodo_fim"].strftime("%Y-%m"),
            "partial_year": r["anos_parciais"] > 0,
        },
        "coverage": {
            "indicators": r["n_indicadores"],
            "ufs": r["n_ufs"],
            "municipalities": r["n_municipios_distintos"],
        },
    }


def list_ufs(db: Session) -> list[dict]:
    return repo.list_ufs(db)


def list_years(db: Session) -> list[int]:
    return repo.list_years(db)


def list_abrangencias(db: Session) -> list[dict]:
    return repo.list_abrangencias(db)


def list_municipalities(db: Session, uf: str | None) -> list[dict]:
    return repo.list_municipalities(db, uf)
