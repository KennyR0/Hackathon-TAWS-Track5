"""Health router."""

from __future__ import annotations

from fastapi import APIRouter

from app.contracts.api import HealthResponse
from app.contracts.entities import allow_internal_field_names

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, operation_id="getHealth")
def get_health() -> HealthResponse:
    with allow_internal_field_names():
        return HealthResponse(
            status="ok",
            service="nexomercado-api",
            contract_version="0.1.0",
        )
