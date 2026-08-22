from fastapi import APIRouter, Response, status

from src.api.database import check_database_connection
from src.api.schemas.common import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verifica a saúde da API e a conexão com o banco",
    description="Retorna 200 com database='connected' se o PostgreSQL responder; "
    "503 com database='disconnected' caso contrário. Nunca expõe detalhes internos da exceção.",
)
def health(response: Response) -> HealthResponse:
    if check_database_connection():
        return HealthResponse(status="ok", database="connected")
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(status="error", database="disconnected")
