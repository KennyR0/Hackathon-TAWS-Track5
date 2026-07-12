"""Role-based permission checks aligned with database RLS matrix."""

from __future__ import annotations

from fastapi import HTTPException, status

from app.security.auth import AppUserContext

REVIEW_ROLES = frozenset({"analyst", "senior_analyst", "advisor", "admin"})
SHAREABLE_BRIEFING_ROLES = frozenset({"senior_analyst", "advisor", "admin"})
ADMIN_ROLES = frozenset({"admin"})


def assert_can_create_review(user: AppUserContext) -> None:
    if user.role not in REVIEW_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Review not permitted")


def assert_can_create_shareable_briefing(user: AppUserContext) -> None:
    if user.role not in SHAREABLE_BRIEFING_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Shareable briefing not permitted",
        )


def assert_admin(user: AppUserContext) -> None:
    if user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin required")


__all__ = [
    "ADMIN_ROLES",
    "REVIEW_ROLES",
    "SHAREABLE_BRIEFING_ROLES",
    "assert_admin",
    "assert_can_create_review",
    "assert_can_create_shareable_briefing",
]
