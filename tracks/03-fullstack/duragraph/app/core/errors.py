"""One error envelope for the whole API: {code, message, detail?}.
`code` is a stable part of the contract (see README rejection map)."""
from fastapi import Request
from fastapi.responses import JSONResponse


class DomainError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, detail: dict | None = None):
        self.message = message
        self.detail = detail
        super().__init__(message)


class ThreadNotFound(DomainError):
    status_code, code = 404, "thread_not_found"


class RunNotFound(DomainError):
    status_code, code = 404, "run_not_found"


class AssistantNotFound(DomainError):
    status_code, code = 404, "assistant_not_found"


class WorkerUnavailable(DomainError):
    status_code, code = 503, "worker_unavailable"


class RunNotInterrupted(DomainError):
    status_code, code = 409, "run_not_interrupted"


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "detail": exc.detail},
    )
