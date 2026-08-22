"""Sentinel.io Analytics API — ponto de entrada.

Uso local: uvicorn src.api.main:app --reload --port 8000
Swagger:   http://localhost:8000/docs
"""
import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.config import settings
from src.api.routers import geography, health, indicators, kpis, metadata, radar, rankings, temporal

logger = logging.getLogger("atlas.api")
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

app = FastAPI(
    title="Sentinel.io Analytics API",
    description=(
        "REST API para consulta dos indicadores analíticos da plataforma "
        "Sentinel.io — Public Safety Analytics Platform. Somente leitura: consulta "
        "o Data Warehouse já validado nas Fases 1-2 (PostgreSQL + camada "
        "analítica SQL); nenhuma regra de agregação, unidade ou ano parcial "
        "é recalculada em Python — tudo herdado do banco."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # nunca ["*"] — sempre da env CORS_ORIGINS
    allow_credentials=True,
    allow_methods=["GET"],  # API somente leitura (regra 29 da Fase 5)
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    # Nunca logar corpo da requisição, headers de autenticação, nem query
    # params que possam conter dados sensíveis — só método/rota/status/tempo.
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)")
    return response


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    code_by_status = {
        400: "INVALID_PARAMETER",
        404: "NOT_FOUND",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_by_status.get(exc.status_code, "ERROR")
    return JSONResponse(status_code=exc.status_code, content=_error_body(code, str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p != "query")
    message = f"Parâmetro inválido: {field} — {first.get('msg', 'valor inválido')}" if field else "Parâmetros inválidos"
    return JSONResponse(status_code=422, content=_error_body("VALIDATION_ERROR", message))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Loga o erro real internamente; NUNCA devolve stack trace/detalhe interno
    # ao cliente (regra 22/23 da Fase 5).
    logger.exception(f"Erro não tratado em {request.method} {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body("INTERNAL_ERROR", "Erro interno do servidor"),
    )


app.include_router(health.router)
app.include_router(indicators.router)
app.include_router(kpis.router)
app.include_router(temporal.router)
app.include_router(geography.router)
app.include_router(rankings.router)
app.include_router(radar.router)
app.include_router(metadata.router)
