"""Dependências reutilizáveis do FastAPI (injeção de sessão de banco, paginação)."""
from collections.abc import Generator

from fastapi import Query
from sqlalchemy.orm import Session

from src.api.config import settings
from src.api.database import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PageParams:
    """page >= 1, 1 <= page_size <= settings.max_page_size (regra 21 da Fase 5)."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Número da página (começa em 1)"),
        page_size: int = Query(
            settings.default_page_size,
            ge=1,
            le=settings.max_page_size,
            description=f"Itens por página (máximo {settings.max_page_size})",
        ),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
