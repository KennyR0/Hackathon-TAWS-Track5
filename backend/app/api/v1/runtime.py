"""Auditable runtime provider endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_provider_demo_service
from app.contracts.api import ProviderRuntimeResponse
from app.services.provider_demo_service import ProviderDemoService

router = APIRouter(tags=["runtime"])
ProviderDemoServiceDep = Annotated[
    ProviderDemoService,
    Depends(get_provider_demo_service),
]


@router.get(
    "/runtime/providers",
    response_model=ProviderRuntimeResponse,
    operation_id="getProviderRuntimeStatus",
)
def get_provider_runtime_status(
    service: ProviderDemoServiceDep,
) -> ProviderRuntimeResponse:
    return service.get_status()
