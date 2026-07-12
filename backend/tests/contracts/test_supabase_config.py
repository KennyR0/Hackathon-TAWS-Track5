from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.config import DEFAULT_REPOSITORY_BACKEND, SupabaseConfig, get_runtime_config, get_supabase_config
from app.supabase_client import create_supabase_client, verify_supabase_connection


def test_runtime_config_uses_fixture_repository_backend_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REPOSITORY_BACKEND", raising=False)

    config = get_runtime_config()

    assert config.repository_backend == DEFAULT_REPOSITORY_BACKEND


def test_runtime_config_rejects_invalid_repository_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REPOSITORY_BACKEND", "redis")

    with pytest.raises(RuntimeError, match="REPOSITORY_BACKEND must be one of"):
        get_runtime_config()


def test_supabase_config_requires_server_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY"):
        get_supabase_config()


def test_supabase_config_rejects_non_https_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SUPABASE_URL", "http://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "secret-test-key")

    with pytest.raises(RuntimeError, match="must use https"):
        get_supabase_config()


def test_create_supabase_client_uses_server_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    factory = Mock(return_value=Mock())
    monkeypatch.setattr("app.supabase_client.create_client", factory)
    config = SupabaseConfig(
        url="https://example.supabase.co",
        service_role_key="secret-test-key",
    )

    client = create_supabase_client(config)

    assert client is factory.return_value
    factory.assert_called_once_with(config.url, config.service_role_key)


def test_verify_supabase_connection_reads_only_one_identifier() -> None:
    query = Mock()
    query.select.return_value = query
    query.limit.return_value = query
    query.execute.return_value = SimpleNamespace(data=[{"id": "org_demo"}])
    client = Mock()
    client.table.return_value = query

    result = verify_supabase_connection(client)

    assert result.is_connected is True
    assert result.resource == "organizations"
    assert result.rows_read == 1
    client.table.assert_called_once_with("organizations")
    query.select.assert_called_once_with("id")
    query.limit.assert_called_once_with(1)


def test_verify_supabase_connection_sanitizes_provider_errors() -> None:
    client = Mock()
    client.table.side_effect = ValueError("provider detail")

    with pytest.raises(RuntimeError, match="Supabase connectivity check failed"):
        verify_supabase_connection(client)
