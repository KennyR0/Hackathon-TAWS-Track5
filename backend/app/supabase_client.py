"""Server-only Supabase client and connectivity verification."""

from __future__ import annotations

from dataclasses import dataclass

from supabase import Client, create_client

from app.config import SupabaseConfig, get_supabase_config


@dataclass(frozen=True)
class SupabaseConnectionCheck:
    is_connected: bool
    resource: str
    rows_read: int


def create_supabase_client(config: SupabaseConfig | None = None) -> Client:
    effective_config = config or get_supabase_config()
    return create_client(
        effective_config.url,
        effective_config.service_role_key,
    )


def verify_supabase_connection(client: Client) -> SupabaseConnectionCheck:
    """Read a single non-sensitive identifier to prove connectivity."""

    try:
        response = client.table("organizations").select("id").limit(1).execute()
    except Exception as exc:
        raise RuntimeError("Supabase connectivity check failed") from exc

    rows = response.data or []
    return SupabaseConnectionCheck(
        is_connected=True,
        resource="organizations",
        rows_read=len(rows),
    )


__all__ = [
    "SupabaseConnectionCheck",
    "create_supabase_client",
    "verify_supabase_connection",
]
