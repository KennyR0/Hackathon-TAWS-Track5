"""Persistence boundary for idempotent worker tasks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol
from urllib.parse import urlsplit

from supabase import Client

from app.contracts.fixtures import FixtureBundle
from app.market_universe import MarketUniverse
from app.news_clustering import ParsedNewsArticle, group_articles_for_events
from app.news_links import extract_article_url, is_linkable_url
from app.news_resolution import should_persist_news_result
from app.providers.live_market import MarketRuntimeSnapshot


class OperationStore(Protocol):
    def ingest(self, bundle: FixtureBundle) -> tuple[int, int]: ...
    def market(self, bundle: FixtureBundle, *, macro: bool) -> tuple[int, int]: ...
    def reconcile(self, bundle: FixtureBundle) -> tuple[int, int]: ...
    def cleanup(self, now: datetime) -> tuple[int, int]: ...
    def market_runtime(
        self, snapshot: MarketRuntimeSnapshot, universe: MarketUniverse
    ) -> tuple[int, int]: ...
    def ingest_runtime(
        self, snapshot: MarketRuntimeSnapshot, universe: MarketUniverse
    ) -> tuple[int, int]: ...


@dataclass
class InMemoryOperationStore:
    records: dict[str, set[str]] = field(default_factory=dict)

    def _upsert(self, table: str, ids: set[str]) -> tuple[int, int]:
        current = self.records.setdefault(table, set())
        before = len(current)
        current.update(ids)
        return len(ids), len(current) - before

    def ingest(self, bundle: FixtureBundle) -> tuple[int, int]:
        raw = self._upsert(
            "raw_source_snapshots",
            {item.id for item in bundle.raw_source_snapshots},
        )
        articles = self._upsert("articles", {item.id for item in bundle.articles})
        return raw[0] + articles[0], raw[1] + articles[1]

    def market(self, bundle: FixtureBundle, *, macro: bool) -> tuple[int, int]:
        snapshots = {
            item.id for item in bundle.market_snapshots if (item.series_id is not None) is macro
        }
        return self._upsert("market_snapshots", snapshots)

    def reconcile(self, bundle: FixtureBundle) -> tuple[int, int]:
        links = {
            f"{event.id}:{article_id}"
            for event in bundle.events
            for article_id in event.article_ids
        }
        return self._upsert("event_articles", links)

    def cleanup(self, now: datetime) -> tuple[int, int]:
        _ = now
        expired = self.records.pop("expired", set())
        return len(expired), len(expired)

    def market_runtime(
        self, snapshot: MarketRuntimeSnapshot, universe: MarketUniverse
    ) -> tuple[int, int]:
        known_symbols = {item.symbol for item in universe.instruments}
        ids = {
            f"live:{symbol}"
            for symbol, result in snapshot.checks.items()
            if symbol in known_symbols and _quote_value(result.payload) is not None
        }
        return self._upsert("market_snapshots_live", ids)

    def ingest_runtime(
        self, snapshot: MarketRuntimeSnapshot, universe: MarketUniverse
    ) -> tuple[int, int]:
        articles = _persistable_news_articles(snapshot)
        ids = {
            _stable_id("art", f"{snapshot.checks['news'].provider}:{_article_provider_id(item)}")
            for item in articles
        }
        return self._upsert("articles_live", ids)


class SupabaseOperationStore:
    def __init__(self, client: Client) -> None:
        self._client = client

    @staticmethod
    def _json_row(model, *, exclude: set[str] | None = None) -> dict[str, object]:
        return model.model_dump(mode="json", by_alias=False, exclude=exclude or set())

    def ingest(self, bundle: FixtureBundle) -> tuple[int, int]:
        raw_rows = [self._json_row(item) for item in bundle.raw_source_snapshots]
        article_rows = [self._json_row(item) for item in bundle.articles]
        if raw_rows:
            self._client.table("raw_source_snapshots").upsert(raw_rows).execute()
        if article_rows:
            self._client.table("articles").upsert(article_rows).execute()
        total = len(raw_rows) + len(article_rows)
        return total, total

    def market(self, bundle: FixtureBundle, *, macro: bool) -> tuple[int, int]:
        snapshots = [
            item for item in bundle.market_snapshots if (item.series_id is not None) is macro
        ]
        snapshot_rows = [self._json_row(item, exclude={"observations"}) for item in snapshots]
        observation_rows = [
            {
                "market_snapshot_id": snapshot.id,
                "observed_at": point.timestamp.isoformat(),
                "close_value": point.close,
                "volume": point.volume,
                "open_value": point.open,
                "high_value": point.high,
                "low_value": point.low,
            }
            for snapshot in snapshots
            for point in snapshot.observations
        ]
        if snapshot_rows:
            self._client.table("market_snapshots").upsert(snapshot_rows).execute()
        if observation_rows:
            self._client.table("market_observations").upsert(
                observation_rows,
                on_conflict="market_snapshot_id,observed_at",
            ).execute()
        total = len(snapshot_rows) + len(observation_rows)
        return total, total

    def reconcile(self, bundle: FixtureBundle) -> tuple[int, int]:
        rows = [
            {"event_id": event.id, "article_id": article_id, "position": index}
            for event in bundle.events
            for index, article_id in enumerate(event.article_ids)
        ]
        if rows:
            self._client.table("event_articles").upsert(
                rows,
                on_conflict="event_id,article_id",
            ).execute()
        return len(rows), len(rows)

    def cleanup(self, now: datetime) -> tuple[int, int]:
        timestamp = now.astimezone(UTC).isoformat()
        idempotency = (
            self._client.table("idempotency_keys").delete().lt("expires_at", timestamp).execute()
        )
        cache = self._client.table("provider_cache").delete().lt("expires_at", timestamp).execute()
        deleted = len(idempotency.data or []) + len(cache.data or [])
        return deleted, deleted

    def market_runtime(
        self, snapshot: MarketRuntimeSnapshot, universe: MarketUniverse
    ) -> tuple[int, int]:
        now = datetime.now(UTC)
        by_symbol = {item.symbol: item for item in universe.instruments}
        asset_ids = {item.symbol: item.id for item in universe.instruments}
        asset_rows = [
            {
                "id": item.id,
                "symbol": item.symbol,
                "name": item.name,
                "instrument_type": item.instrument_type.value,
                "currency": item.currency,
                "exchange": item.exchange,
                "benchmark_asset_id": asset_ids.get(item.benchmark_symbol),
                "series_id": item.series_id,
            }
            for item in universe.instruments
        ]
        self._client.table("assets").upsert(asset_rows, on_conflict="symbol").execute()
        self._client.table("watchlists").upsert(
            {"id": "watchlist_demo_global", "organization_id": "org_demo", "name": "Global"}
        ).execute()
        self._client.table("watchlist_assets").upsert(
            [
                {
                    "watchlist_id": "watchlist_demo_global",
                    "asset_id": item.id,
                    "position": position,
                }
                for position, item in enumerate(universe.instruments)
            ],
            on_conflict="watchlist_id,asset_id",
        ).execute()

        snapshot_rows: list[dict[str, object]] = []
        observation_rows: list[dict[str, object]] = []
        for symbol, result in snapshot.checks.items():
            instrument = by_symbol.get(symbol)
            value = _quote_value(result.payload)
            if instrument is None or value is None:
                continue
            historical_points = _quote_history(result.payload)
            observed_at = (
                _history_point_datetime(historical_points[-1])
                if historical_points
                else _quote_timestamp(result.payload, now)
            )
            history_start = (
                _history_point_datetime(historical_points[0])
                if historical_points
                else observed_at
            )
            snapshot_id = f"mkt_live_{symbol.lower().replace('-', '_')}_1d"
            existing = (
                self._client.table("market_snapshots")
                .select("start_at")
                .eq("id", snapshot_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            start_at = history_start.isoformat()
            if existing and isinstance(existing[0].get("start_at"), str):
                start_at = min(existing[0]["start_at"], start_at)
            warnings = list(result.warnings)
            if result.data_mode != "live" and not warnings:
                warnings = ["LIVE_QUOTE_FALLBACK"]
            snapshot_rows.append(
                {
                    "id": snapshot_id,
                    "asset_id": instrument.id,
                    "benchmark_asset_id": asset_ids.get(instrument.benchmark_symbol),
                    "series_id": instrument.series_id,
                    "interval": "1d",
                    "currency": instrument.currency,
                    "timezone": "UTC",
                    "start_at": start_at,
                    "end_at": observed_at.isoformat(),
                    "source_url": _provider_source_url(result.provider),
                    "missing_value_policy": (
                        "skip_non_trading_days" if instrument.series_id else "none"
                    ),
                    "content_hash": _quote_hash(symbol, result.payload),
                    "data_mode": result.data_mode,
                    "provider": result.provider,
                    "retrieved_at": now.isoformat(),
                    "data_as_of": observed_at.isoformat(),
                    "freshness": {
                        "evaluatedAt": now.isoformat(),
                        "staleAfterSeconds": 86400,
                        "isStale": (now - observed_at).total_seconds() > 86400,
                    },
                    "warnings": warnings,
                }
            )
            if historical_points:
                observation_rows.extend(
                    {
                        "market_snapshot_id": snapshot_id,
                        **point,
                    }
                    for point in historical_points
                )
            else:
                observation_rows.append(
                    {
                        "market_snapshot_id": snapshot_id,
                        "observed_at": observed_at.isoformat(),
                        "close_value": value,
                        "volume": None,
                        "open_value": None,
                        "high_value": None,
                        "low_value": None,
                    }
                )
        if snapshot_rows:
            self._client.table("market_snapshots").upsert(snapshot_rows).execute()
        if observation_rows:
            self._client.table("market_observations").upsert(
                observation_rows,
                on_conflict="market_snapshot_id,observed_at",
            ).execute()
        total = len(asset_rows) + len(snapshot_rows) + len(observation_rows)
        return total, total

    def list_persisted_news_articles(self, *, limit: int = 50) -> list[dict[str, object]]:
        rows = (
            self._client.table("articles")
            .select("*")
            .eq("is_synthetic", False)
            .in_("data_mode", ["live", "fallback"])
            .order("retrieved_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        articles: list[dict[str, object]] = []
        for row in rows:
            url = row.get("url")
            if not isinstance(url, str) or not is_linkable_url(url):
                continue
            articles.append(
                {
                    "url": url,
                    "title": row.get("headline"),
                    "headline": row.get("headline"),
                    "summary": row.get("summary"),
                    "publishedAt": row.get("published_at"),
                    "providerArticleId": row.get("provider_article_id"),
                    "domain": row.get("provider"),
                }
            )
        return articles

    def ingest_runtime(
        self, snapshot: MarketRuntimeSnapshot, universe: MarketUniverse
    ) -> tuple[int, int]:
        news_result = snapshot.checks.get("news")
        if news_result is None or not should_persist_news_result(news_result):
            return 0, 0
        articles = _persistable_news_articles(snapshot)
        if not articles:
            return 0, 0
        now = datetime.now(UTC)
        by_symbol = {item.symbol: item for item in universe.instruments}
        parsed_articles: list[ParsedNewsArticle] = []
        for item in articles:
            article_url = extract_article_url(item)
            if article_url is None:
                continue
            title = _article_title(item)
            summary = _article_summary(item, title)
            symbol = _match_article_symbol(title, summary, universe) or "AAPL"
            parsed_articles.append(
                ParsedNewsArticle(
                    payload=item,
                    title=title,
                    summary=summary,
                    symbol=symbol,
                    published_at=_article_published_at(item, now),
                    url=article_url,
                )
            )
        if not parsed_articles:
            return 0, 0
        source_rows: dict[str, dict[str, object]] = {}
        raw_rows: list[dict[str, object]] = []
        article_rows: list[dict[str, object]] = []
        event_rows: list[dict[str, object]] = []
        event_article_rows: list[dict[str, object]] = []
        event_asset_rows: list[dict[str, object]] = []
        warnings = list(news_result.warnings)
        for cluster in group_articles_for_events(parsed_articles):
            lead = cluster.articles[0]
            instrument = by_symbol[cluster.symbol]
            event_id = _stable_id("evt", cluster.cluster_key)
            event_rows.append(
                {
                    "id": event_id,
                    "organization_id": "org_demo",
                    "title": lead.title,
                    "summary": lead.summary,
                    "event_at": lead.published_at.isoformat(),
                    "data_mode": news_result.data_mode,
                    "provider": news_result.provider,
                    "retrieved_at": now.isoformat(),
                    "data_as_of": lead.published_at.isoformat(),
                    "freshness": {
                        "evaluatedAt": now.isoformat(),
                        "staleAfterSeconds": 86400,
                        "isStale": (now - lead.published_at).total_seconds() > 86400,
                    },
                    "warnings": warnings,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat(),
                }
            )
            event_asset_rows.append(
                {
                    "event_id": event_id,
                    "asset_id": instrument.id,
                    "relationship": "direct",
                    "reason": f"Entity match for {instrument.name}",
                    "entity_match_score": 0.9,
                }
            )
            for position, parsed in enumerate(cluster.articles):
                item = parsed.payload
                provider = str(item.get("provider") or news_result.provider)
                provider_id = _article_provider_id(item)
                article_url = parsed.url
                domain = _article_domain(item, article_url)
                source_id = _stable_id("src", domain)
                raw_id = _stable_id("raw", f"{provider}:{provider_id}")
                article_id = _stable_id("art", f"{provider}:{provider_id}")
                raw_hash = _content_hash(item)
                source_rows[source_id] = {
                    "id": source_id,
                    "name": domain,
                    "domain": domain,
                    "tier": "B",
                    "publisher_group_id": _stable_id("grp", domain),
                    "is_original_publisher": True,
                    "is_aggregator": False,
                    "fixture_only": False,
                    "homepage_url": f"https://{domain}",
                    "country_code": "US",
                    "language": "en",
                }
                raw_rows.append(
                    {
                        "id": raw_id,
                        "source_id": source_id,
                        "provider": provider,
                        "provider_article_id": provider_id,
                        "captured_at": now.isoformat(),
                        "payload": item,
                        "content_hash": raw_hash,
                    }
                )
                article_rows.append(
                    {
                        "id": article_id,
                        "source_id": source_id,
                        "provider_article_id": provider_id,
                        "headline": parsed.title,
                        "summary": parsed.summary,
                        "published_at": parsed.published_at.isoformat(),
                        "url": article_url,
                        "language": "en",
                        "source_snapshot_id": raw_id,
                        "content_hash": raw_hash,
                        "is_synthetic": False,
                        "data_mode": news_result.data_mode,
                        "provider": provider,
                        "retrieved_at": now.isoformat(),
                        "data_as_of": parsed.published_at.isoformat(),
                        "freshness": {
                            "evaluatedAt": now.isoformat(),
                            "staleAfterSeconds": 86400,
                            "isStale": (now - parsed.published_at).total_seconds() > 86400,
                        },
                        "warnings": warnings,
                    }
                )
                event_article_rows.append(
                    {"event_id": event_id, "article_id": article_id, "position": position}
                )
        self._client.table("sources").upsert(list(source_rows.values())).execute()
        self._client.table("raw_source_snapshots").upsert(
            raw_rows, on_conflict="provider,provider_article_id"
        ).execute()
        self._client.table("articles").upsert(
            article_rows, on_conflict="source_id,provider_article_id"
        ).execute()
        self._client.table("events").upsert(event_rows).execute()
        self._client.table("event_articles").upsert(
            event_article_rows, on_conflict="event_id,article_id"
        ).execute()
        self._client.table("event_asset_relations").upsert(
            event_asset_rows, on_conflict="event_id,asset_id"
        ).execute()
        total = sum(
            len(rows)
            for rows in (
                source_rows,
                raw_rows,
                article_rows,
                event_rows,
                event_article_rows,
                event_asset_rows,
            )
        )
        return total, total


def _quote_value(payload: dict[str, object]) -> float | None:
    raw = (
        payload.get("close") or payload.get("current") or payload.get("usd") or payload.get("value")
    )
    try:
        value = float(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    return value if value is not None and value > 0 else None


def _quote_timestamp(payload: dict[str, object], fallback: datetime) -> datetime:
    updated_at = payload.get("lastUpdatedAt")
    if isinstance(updated_at, (int, float)):
        return datetime.fromtimestamp(updated_at, tz=UTC)
    observed_on = payload.get("date")
    if isinstance(observed_on, str):
        try:
            return datetime.fromisoformat(observed_on).replace(tzinfo=UTC)
        except ValueError:
            pass
    return fallback


def _quote_history(payload: dict[str, object]) -> list[dict[str, object]]:
    history = payload.get("history")
    if not isinstance(history, list):
        return []
    points: list[dict[str, object]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        timestamp = item.get("timestamp")
        if isinstance(timestamp, (int, float)):
            observed_at = datetime.fromtimestamp(timestamp, tz=UTC)
        elif isinstance(timestamp, str):
            try:
                observed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                continue
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=UTC)
        else:
            continue
        close = _positive_number(item.get("close"))
        if close is None:
            continue
        points.append(
            {
                "observed_at": observed_at.isoformat(),
                "close_value": close,
                "volume": _non_negative_number(item.get("volume")),
                "open_value": _positive_number(item.get("open")),
                "high_value": _positive_number(item.get("high")),
                "low_value": _positive_number(item.get("low")),
            }
        )
    return sorted(points, key=lambda point: str(point["observed_at"]))


def _history_point_datetime(point: dict[str, object]) -> datetime:
    return datetime.fromisoformat(str(point["observed_at"]).replace("Z", "+00:00"))


def _positive_number(value: object) -> float | None:
    parsed = _non_negative_number(value)
    return parsed if parsed is not None and parsed > 0 else None


def _non_negative_number(value: object) -> float | None:
    if not isinstance(value, (int, float, str)):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _provider_source_url(provider: str) -> str:
    return {
        "twelve_data": "https://api.twelvedata.com/quote",
        "finnhub": "https://finnhub.io/api/v1/quote",
        "coingecko": "https://api.coingecko.com/api/v3/simple/price",
        "rapidapi_yh_finance": "https://rapidapi.com/sparior/api/yahoo-finance15",
        "fred": "https://api.stlouisfed.org/fred/series/observations",
        "eia": "https://api.eia.gov/v2/petroleum/pri/spt/data/",
    }.get(provider, "https://api.nexomercado.example/market")


def _quote_hash(symbol: str, payload: dict[str, object]) -> str:
    body = json.dumps({"symbol": symbol, "payload": payload}, sort_keys=True, default=str)
    return f"sha256:{sha256(body.encode('utf-8')).hexdigest()}"


def _news_articles(snapshot: MarketRuntimeSnapshot) -> list[dict[str, object]]:
    result = snapshot.checks.get("news")
    if result is None or not result.ok:
        return []
    articles = result.payload.get("articles")
    if not isinstance(articles, list):
        return []
    return [item for item in articles if isinstance(item, dict)]


def _persistable_news_articles(snapshot: MarketRuntimeSnapshot) -> list[dict[str, object]]:
    return [
        item
        for item in _news_articles(snapshot)
        if extract_article_url(item) is not None
    ]


def _article_provider_id(item: dict[str, object]) -> str:
    value = item.get("id") or item.get("url") or item.get("title") or item.get("headline")
    return str(value or _content_hash(item))[:250]


def _article_title(item: dict[str, object]) -> str:
    return str(item.get("title") or item.get("headline") or "Market update")[:500]


def _article_summary(item: dict[str, object], title: str) -> str:
    return str(item.get("summary") or item.get("description") or title)[:2000]


def _article_domain(item: dict[str, object], url: str) -> str:
    raw = str(item.get("domain") or item.get("source") or urlsplit(url).hostname or "reuters.com")
    domain = raw.lower().removeprefix("www.")
    domain = re.sub(r"[^a-z0-9.-]", "-", domain).strip("-.")
    return domain if "." in domain else f"{domain or 'market-source'}.com"


def _article_published_at(item: dict[str, object], now: datetime) -> datetime:
    raw = item.get("datetime") or item.get("seendate") or item.get("publishedAt")
    if isinstance(raw, (int, float)):
        parsed = datetime.fromtimestamp(raw, tz=UTC)
        return min(parsed, now)
    if isinstance(raw, str):
        for value in (raw, raw.replace("Z", "+00:00")):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return min(parsed.astimezone(UTC), now)
            except ValueError:
                continue
    return now


def _match_article_symbol(title: str, summary: str, universe: MarketUniverse) -> str | None:
    content = f"{title} {summary}".casefold()
    for item in universe.instruments:
        company_token = item.name.split()[0].casefold()
        if item.symbol.casefold() in content or company_token in content:
            return item.symbol
    return None


def _content_hash(value: object) -> str:
    body = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return f"sha256:{sha256(body.encode('utf-8')).hexdigest()}"


def _stable_id(prefix: str, value: str) -> str:
    digest = sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


__all__ = ["InMemoryOperationStore", "OperationStore", "SupabaseOperationStore"]
