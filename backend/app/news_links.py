"""Rules for external news URLs and clickability."""

from __future__ import annotations

from urllib.parse import urlsplit

from app.contracts.entities import Article, DataMode, Evidence

_DEMO_HOST_SUFFIXES = (".test", ".localhost", ".invalid", ".example")
_DEMO_HOSTS = frozenset({"fixtures.nexomercado.test"})


def normalize_external_url(value: object) -> str | None:
    """Return a normalized https URL or None when the value is not linkable."""

    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if raw.startswith("http://"):
        raw = f"https://{raw.removeprefix('http://')}"
    if not raw.startswith("https://"):
        return None
    parsed = urlsplit(raw)
    hostname = (parsed.hostname or "").lower().removeprefix("www.")
    if not hostname or "." not in hostname:
        return None
    if hostname in _DEMO_HOSTS or any(hostname.endswith(suffix) for suffix in _DEMO_HOST_SUFFIXES):
        return None
    return raw


def extract_article_url(item: dict[str, object]) -> str | None:
    for key in ("url", "link", "sourceUrl"):
        normalized = normalize_external_url(item.get(key))
        if normalized is not None:
            return normalized
    return None


def is_linkable_url(url: object) -> bool:
    return normalize_external_url(url) is not None


def is_article_linkable(article: Article) -> bool:
    return (
        article.data_mode in {DataMode.LIVE, DataMode.FALLBACK}
        and not article.is_synthetic
        and is_linkable_url(str(article.url))
    )


def is_evidence_linkable(evidence: Evidence) -> bool:
    return is_linkable_url(str(evidence.source_url))


__all__ = [
    "extract_article_url",
    "is_article_linkable",
    "is_evidence_linkable",
    "is_linkable_url",
    "normalize_external_url",
]
