from sqlalchemy.orm import Session

from src.api.repositories import kpis as repo


def get_kpis(
    db: Session,
    indicator_id: int | None,
    uf: str | None,
    municipio: str | None,
    ano: int | None,
    abrangencia: str | None,
) -> list[dict]:
    # Cada linha retornada já vem de UM indicador só (GROUP BY no repositório)
    # — nunca existe uma linha somando familias/unidades diferentes, mesmo
    # quando indicator_id é omitido (regra "nunca misturar pessoas/kg/ocorrências").
    return repo.get_kpis(db, indicator_id, uf, municipio, ano, abrangencia)
