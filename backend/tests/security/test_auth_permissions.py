from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.api import dependencies
from app.main import create_app
from app.security.auth import AppUserContext, get_auth_config, resolve_app_user
from app.security.permissions import (
    assert_can_create_review,
    assert_can_create_shareable_briefing,
)


def test_auth_disabled_by_default() -> None:
    config = get_auth_config()
    assert config.enabled is False


def test_analyst_can_review() -> None:
    user = AppUserContext(
        id="usr_analista_demo",
        organization_id="org_demo",
        role="analyst",
        display_name="Analista",
        is_active=True,
    )
    assert_can_create_review(user)


def test_analyst_cannot_shareable_briefing() -> None:
    user = AppUserContext(
        id="usr_analista_demo",
        organization_id="org_demo",
        role="analyst",
        display_name="Analista",
        is_active=True,
    )
    with pytest.raises(HTTPException) as exc:
        assert_can_create_shareable_briefing(user)
    assert exc.value.status_code == 403


def test_senior_analyst_can_shareable_briefing() -> None:
    user = AppUserContext(
        id="usr_senior",
        organization_id="org_demo",
        role="senior_analyst",
        display_name="Senior",
        is_active=True,
    )
    assert_can_create_shareable_briefing(user)


def test_auth_enabled_protects_all_api_routes_but_not_health(monkeypatch) -> None:
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setattr(dependencies, "get_supabase_client", lambda: object())
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        for path in ("/api/v1/events", "/api/v1/signals", "/api/v1/analyses/missing"):
            assert client.get(path).status_code == 401


def test_valid_bearer_resolves_database_app_user(monkeypatch) -> None:
    expected = AppUserContext(
        id="usr_senior",
        organization_id="org_demo",
        role="senior_analyst",
        display_name="Senior",
        is_active=True,
    )
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setattr(dependencies, "get_supabase_client", lambda: object())
    monkeypatch.setattr(dependencies, "extract_auth_user_id", lambda *_args, **_kwargs: "auth-1")
    monkeypatch.setattr(dependencies, "resolve_app_user", lambda *_args: expected)

    resolved = dependencies.get_current_app_user(
        HTTPAuthorizationCredentials(scheme="Bearer", credentials="token")
    )

    assert resolved == expected


def test_inactive_database_user_is_rejected() -> None:
    class Query:
        def select(self, _columns):
            return self

        def eq(self, _column, _value):
            return self

        def limit(self, _count):
            return self

        def execute(self):
            return SimpleNamespace(data=[{
                "id": "usr_inactive",
                "organization_id": "org_demo",
                "role": "analyst",
                "display_name": "Inactive",
                "is_active": False,
            }])

    client = SimpleNamespace(table=lambda _name: Query())
    with pytest.raises(HTTPException) as exc:
        resolve_app_user(client, "auth-inactive")
    assert exc.value.status_code == 403
