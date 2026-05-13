from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    db: str


class ErrorResponse(BaseModel):
    detail: str
