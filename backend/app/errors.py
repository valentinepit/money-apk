from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    """HTTP-ошибка в формате конверта из docs/api/api-contract.md."""

    def __init__(self, status_code: int, code: str, message: str, details: list[dict] | None = None):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


def unauthorized(message: str = "Не авторизован") -> APIError:
    return APIError(status.HTTP_401_UNAUTHORIZED, "unauthorized", message)


def forbidden(message: str = "Доступ запрещён") -> APIError:
    return APIError(status.HTTP_403_FORBIDDEN, "forbidden", message)


def not_found(message: str = "Не найдено") -> APIError:
    return APIError(status.HTTP_404_NOT_FOUND, "not_found", message)


def conflict(code: str, message: str) -> APIError:
    return APIError(status.HTTP_409_CONFLICT, code, message)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    body = {"error": {"code": exc.code, "message": exc.message}}
    if exc.details:
        body["error"]["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(loc) for loc in err["loc"] if loc != "body"), "message": err["msg"], "code": err["type"]}
        for err in exc.errors()
    ]
    body = {"error": {"code": "validation_error", "message": "Ошибка валидации запроса", "details": details}}
    return JSONResponse(status_code=422, content=body)
