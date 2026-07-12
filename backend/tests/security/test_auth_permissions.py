from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.security.auth import AppUserContext, get_auth_config
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
