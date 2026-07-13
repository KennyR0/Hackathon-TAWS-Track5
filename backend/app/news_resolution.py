"""News provider resolution: live, persisted cache, fixture demo."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from app.contracts.entities import DataMode
from app.news_links import extract_article_url
from app.providers.base import ProviderProbeResult

if TYPE_CHECKING:
    pass

PersistedNewsLoader = Callable[[int], Sequence[dict[str, object]]]
NewsProbe = Callable[[], ProviderProbeResult]

STALE_PERSISTED_NEWS_WARNING = "STALE_PERSISTED_NEWS"
FIXTURE_NEWS_FALLBACK_WARNING = "FIXTURE_NEWS_FALLBACK_ACTIVE"


def should_persist_news_result(result: ProviderProbeResult) -> bool:
    if not result.ok:
        return False
    if result.provider in {"fixture_news", "persisted_news"}:
        return False
    if result.data_mode == DataMode.FIXTURE.value:
        return False
    blocked = {
        FIXTURE_NEWS_FALLBACK_WARNING,
        STALE_PERSISTED_NEWS_WARNING,
    }
    return not any(warning in blocked for warning in result.warnings)


def resolve_news_probe(
    *,
    probe_primary: NewsProbe,
    probe_fallback: NewsProbe | None,
    load_persisted: PersistedNewsLoader | None,
    fixture_fallback: Callable[[ProviderProbeResult], ProviderProbeResult],
) -> ProviderProbeResult:
    primary = probe_primary()
    if primary.ok:
        return primary

    if probe_fallback is not None:
        fallback = probe_fallback()
        merged = _merge_news_failover(
            primary,
            fallback,
            failover_warning="GDELT_TO_FINNHUB_FAILOVER",
        )
        if merged.ok:
            return merged
        primary = merged

    if load_persisted is not None:
        articles = [item for item in load_persisted(50) if isinstance(item, dict)]
        if articles:
            warnings = tuple(dict.fromkeys((*primary.warnings, STALE_PERSISTED_NEWS_WARNING)))
            return ProviderProbeResult(
                provider="persisted_news",
                data_mode=DataMode.FALLBACK.value,
                ok=True,
                warnings=warnings,
                payload={
                    "articleCount": len(articles),
                    "titles": [
                        str(item.get("title") or item.get("headline") or "Market update")
                        for item in articles[:3]
                    ],
                    "articles": articles,
                },
            )

    return fixture_fallback(primary)


def _merge_news_failover(
    primary: ProviderProbeResult,
    fallback: ProviderProbeResult,
    *,
    failover_warning: str,
) -> ProviderProbeResult:
    warnings = tuple(dict.fromkeys((*primary.warnings, *fallback.warnings, failover_warning)))
    if fallback.ok:
        merged_articles = _dedupe_articles_by_url(
            _articles_from_payload(primary.payload) + _articles_from_payload(fallback.payload)
        )
        payload = dict(fallback.payload)
        if merged_articles:
            payload["articles"] = merged_articles
            payload["articleCount"] = len(merged_articles)
            payload["titles"] = [
                str(item.get("title") or item.get("headline") or "Market update")
                for item in merged_articles[:3]
            ]
        return ProviderProbeResult(
            provider=fallback.provider,
            data_mode=fallback.data_mode,
            ok=True,
            warnings=warnings,
            payload=payload,
        )
    return ProviderProbeResult(
        provider=primary.provider,
        data_mode=DataMode.FALLBACK.value,
        ok=False,
        warnings=warnings,
        payload=primary.payload,
    )


def _articles_from_payload(payload: dict[str, object]) -> list[dict[str, object]]:
    articles = payload.get("articles")
    if not isinstance(articles, list):
        return []
    return [item for item in articles if isinstance(item, dict)]


def _dedupe_articles_by_url(articles: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in articles:
        key = _article_dedupe_key(item)
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged


def _article_dedupe_key(item: dict[str, object]) -> str:
    url = extract_article_url(item)
    if url:
        return url
    for field in ("id", "title", "headline"):
        value = item.get(field)
        if value:
            return str(value)
    return ""


__all__ = [
    "FIXTURE_NEWS_FALLBACK_WARNING",
    "STALE_PERSISTED_NEWS_WARNING",
    "resolve_news_probe",
    "should_persist_news_result",
]
