"""Schemas compartilhados: erro padrão, paginação, health check."""
from typing import Literal

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str = Field(..., description="Código estável do erro, ex.: INVALID_PARAMETER")
    message: str = Field(..., description="Mensagem legível, nunca um stack trace")


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    service: Literal["atlas-api"] = "atlas-api"
    database: Literal["connected", "disconnected"]
