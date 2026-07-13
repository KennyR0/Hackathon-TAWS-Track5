"""Deterministic clustering of live news articles into market events."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

_MAX_HEADLINE_TOKENS = 12


def normalize_headline(title: str) -> str:
    lowered = title.casefold()
    cleaned = re.sub(r"[^\w\s]", " ", lowered, flags=re.UNICODE)
    tokens = [token for token in cleaned.split() if len(token) > 1]
    return " ".join(tokens[:_MAX_HEADLINE_TOKENS])


def event_cluster_key(title: str, symbol: str) -> str:
    return f"{symbol.casefold()}:{normalize_headline(title)}"


@dataclass(frozen=True)
class ParsedNewsArticle:
    payload: dict[str, object]
    title: str
    summary: str
    symbol: str
    published_at: datetime
    url: str


@dataclass(frozen=True)
class ArticleCluster:
    cluster_key: str
    symbol: str
    articles: tuple[ParsedNewsArticle, ...]


def group_articles_for_events(articles: list[ParsedNewsArticle]) -> tuple[ArticleCluster, ...]:
    buckets: dict[str, list[ParsedNewsArticle]] = {}
    for article in articles:
        key = event_cluster_key(article.title, article.symbol)
        buckets.setdefault(key, []).append(article)
    clusters: list[ArticleCluster] = []
    for key, items in buckets.items():
        sorted_items = tuple(sorted(items, key=lambda item: item.published_at, reverse=True))
        clusters.append(
            ArticleCluster(
                cluster_key=key,
                symbol=sorted_items[0].symbol,
                articles=sorted_items,
            )
        )
    return tuple(clusters)


__all__ = [
    "ArticleCluster",
    "ParsedNewsArticle",
    "event_cluster_key",
    "group_articles_for_events",
    "normalize_headline",
]
