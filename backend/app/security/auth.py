"""Supabase Auth JWT validation and app user resolution."""

from __future__ import annotations

from dataclasses import dataclass
from os import getenv

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthConfig:
    enabled: bool
    jwt_secret: str | None = None


@dataclass(frozen=True)
class AppUserContext:
    id: str
    organization_id: str
    role: str
    display_name: str
    is_active: bool


def get_auth_config() -> AuthConfig:
    enabled = getenv("AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    jwt_secret = getenv("SUPABASE_JWT_SECRET", "").strip() or None
    return AuthConfig(enabled=enabled, jwt_secret=jwt_secret)


def resolve_app_user(client: Client, auth_user_id: str) -> AppUserContext:
    rows = (
        client.table("app_users")
        .select("id,organization_id,role,display_name,is_active")
        .eq("auth_user_id", auth_user_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="App user not linked")
    row = rows[0]
    if not row.get("is_active", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
    return AppUserContext(
        id=row["id"],
        organization_id=row["organization_id"],
        role=row["role"],
        display_name=row["display_name"],
        is_active=row["is_active"],
    )


def extract_auth_user_id(
    client: Client,
    credentials: HTTPAuthorizationCredentials | None,
    *,
    config: AuthConfig,
) -> str | None:
    if not config.enabled:
        return None
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = credentials.credentials
    try:
        response = client.auth.get_user(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid auth token",
        ) from exc
    if response.user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")
    return str(response.user.id)


def get_optional_app_user(
    client: Client,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AppUserContext | None:
    config = get_auth_config()
    auth_user_id = extract_auth_user_id(client, credentials, config=config)
    if auth_user_id is None:
        return None
    return resolve_app_user(client, auth_user_id)


def require_app_user(
    client: Client,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AppUserContext:
    config = get_auth_config()
    if not config.enabled:
        return AppUserContext(
            id="usr_analista_demo",
            organization_id="org_demo",
            role="analyst",
            display_name="Analista Demo",
            is_active=True,
        )
    auth_user_id = extract_auth_user_id(client, credentials, config=config)
    assert auth_user_id is not None
    return resolve_app_user(client, auth_user_id)


__all__ = [
    "AppUserContext",
    "AuthConfig",
    "get_auth_config",
    "get_optional_app_user",
    "require_app_user",
    "resolve_app_user",
]
