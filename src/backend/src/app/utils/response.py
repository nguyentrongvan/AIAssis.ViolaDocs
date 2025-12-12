from fastapi.responses import JSONResponse
from typing import Any, Optional


def success_response(data: Any = None, message: str = "Success", status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "is_success": True,
            "message": message,
            "status_code": status_code,
            "data": data
        }
    )


def error_response(message: str, status_code: int = 400, details: Optional[Any] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "is_success": False,
            "message": message,
            "status_code": status_code,
            "data": {
                "error": {
                    "code": status_code,
                    "message": message,
                    "details": details
                }
            }
        }
    )






