from __future__ import annotations

from unittest.mock import MagicMock

from app.contracts.entities import DataMode
from app.market_universe import load_market_universe
from app.news_clustering import event_cluster_key, group_articles_for_events, normalize_headline
from app.news_links import (
    extract_article_url,
    is_article_linkable,
    is_evidence_linkable,
    is_linkable_url,
    normalize_external_url,
)
from app.news_resolution import (
    STALE_PERSISTED_NEWS_WARNING,
    _merge_news_failover,
    resolve_news_probe,
    should_persist_news_result,
)
from app.operations.store import SupabaseOperationStore
from app.providers.base import ProviderProbeResult
from app.providers.live_market import MarketRuntimeSnapshot

def test_normalize_external_url_accepts_http_and_rejects_demo_domains() -> None:
    assert normalize_external_url("http://www.reuters.com/markets/us/") == (
        "https://www.reuters.com/markets/us/"
    )
    assert normalize_external_url("https://finnhub.io/api/v1/company-news") == (
        "https://finnhub.io/api/v1/company-news"
    )
    assert normalize_external_url("https://finwire-fixture.test/news/demo") is None
    assert normalize_external_url("https://fixtures.nexomercado.test/methodology") is None
    assert normalize_external_url("") is None


def test_extract_article_url_reads_alternate_fields() -> None:
    assert extract_article_url({"link": "http://example.com/story"}) == "https://example.com/story"
    assert extract_article_url({"sourceUrl": "https://news.example.com/a"}) == (
        "https://news.example.com/a"
    )
    assert extract_article_url({"title": "No URL"}) is None


def test_should_persist_news_result_blocks_fixture_and_persisted_layers() -> None:
    live = ProviderProbeResult(
        provider="gdelt",
        data_mode=DataMode.LIVE.value,
        ok=True,
        warnings=(),
        payload={"articles": []},
    )
    fixture = ProviderProbeResult(
        provider="fixture_news",
        data_mode=DataMode.FALLBACK.value,
        ok=False,
        warnings=("FIXTURE_NEWS_FALLBACK_ACTIVE",),
        payload={"articles": []},
    )
    persisted = ProviderProbeResult(
        provider="persisted_news",
        data_mode=DataMode.FALLBACK.value,
        ok=True,
        warnings=("STALE_PERSISTED_NEWS",),
        payload={"articles": []},
    )

    assert should_persist_news_result(live) is True
    assert should_persist_news_result(fixture) is False
    assert should_persist_news_result(persisted) is False


def test_is_linkable_url_rejects_fixture_domains() -> None:
    assert is_linkable_url("https://www.bloomberg.com/news") is True
    assert is_linkable_url("https://businessdaily-fixture.test/news/demo") is False


def test_is_evidence_linkable_uses_source_url_policy() -> None:
    assert is_evidence_linkable(
        type(
            "EvidenceStub",
            (),
            {"source_url": "https://www.reuters.com/markets/"},
        )()
    ) is True
    assert is_evidence_linkable(
        type(
            "EvidenceStub",
            (),
            {"source_url": "https://fixtures.nexomercado.test/market/coingecko/btc-usd.json"},
        )()
    ) is False


def test_is_article_linkable_requires_live_or_fallback_non_synthetic_url() -> None:
    article = type(
        "ArticleStub",
        (),
        {
            "data_mode": DataMode.FIXTURE,
            "is_synthetic": True,
            "url": "https://www.reuters.com/markets/",
        },
    )()
    assert is_article_linkable(article) is False


def test_resolve_news_probe_uses_persisted_layer_before_fixture() -> None:
    fixture_called = {"value": False}

    def fixture_fallback(_result: ProviderProbeResult) -> ProviderProbeResult:
        fixture_called["value"] = True
        return ProviderProbeResult(
            provider="fixture_news",
            data_mode=DataMode.FALLBACK.value,
            ok=False,
            warnings=("FIXTURE_NEWS_FALLBACK_ACTIVE",),
            payload={"articles": []},
        )

    result = resolve_news_probe(
        probe_primary=lambda: ProviderProbeResult(
            provider="gdelt",
            data_mode=DataMode.FALLBACK.value,
            ok=False,
            warnings=("GDELT_TIMEOUT_FALLBACK_ACTIVE",),
            payload={},
        ),
        probe_fallback=None,
        load_persisted=lambda _limit: [
            {
                "url": "https://www.reuters.com/markets/us/",
                "headline": "Persisted headline",
            }
        ],
        fixture_fallback=fixture_fallback,
    )

    assert fixture_called["value"] is False
    assert result.provider == "persisted_news"
    assert result.ok is True
    assert STALE_PERSISTED_NEWS_WARNING in result.warnings
    assert result.payload["articles"][0]["headline"] == "Persisted headline"


def test_ingest_runtime_skips_fixture_news_without_touching_supabase() -> None:
    client = MagicMock()
    store = SupabaseOperationStore(client)
    snapshot = MarketRuntimeSnapshot(
        data_mode=DataMode.FALLBACK.value,
        provider="fixture_news",
        warnings=("FIXTURE_NEWS_FALLBACK_ACTIVE",),
        checks={
            "news": ProviderProbeResult(
                provider="fixture_news",
                data_mode=DataMode.FALLBACK.value,
                ok=False,
                warnings=("FIXTURE_NEWS_FALLBACK_ACTIVE",),
                payload={
                    "articles": [
                        {"url": "https://finwire-fixture.test/demo", "title": "Demo headline"}
                    ]
                },
            )
        },
        request_budget=8,
        requests_used=1,
    )

    rows_read, rows_written = store.ingest_runtime(snapshot, load_market_universe())

    assert rows_read == 0
    assert rows_written == 0
    client.table.assert_not_called()


def test_merge_news_failover_unions_articles_from_both_providers() -> None:
    primary = ProviderProbeResult(
        provider="gdelt",
        data_mode=DataMode.FALLBACK.value,
        ok=False,
        warnings=("GDELT_TIMEOUT_FALLBACK_ACTIVE",),
        payload={
            "articles": [
                {
                    "url": "https://www.reuters.com/markets/apple-outlook",
                    "title": "Apple outlook trimmed after earnings",
                }
            ]
        },
    )
    fallback = ProviderProbeResult(
        provider="finnhub_news",
        data_mode=DataMode.LIVE.value,
        ok=True,
        warnings=(),
        payload={
            "articles": [
                {
                    "url": "https://www.bloomberg.com/news/apple-outlook-trimmed",
                    "title": "Apple outlook trimmed after earnings!",
                }
            ]
        },
    )

    merged = _merge_news_failover(
        primary,
        fallback,
        failover_warning="GDELT_TO_FINNHUB_FAILOVER",
    )

    assert merged.ok is True
    assert merged.provider == "finnhub_news"
    assert len(merged.payload["articles"]) == 2
    assert "GDELT_TO_FINNHUB_FAILOVER" in merged.warnings


def test_event_cluster_key_normalizes_headline() -> None:
    assert normalize_headline("Apple Outlook Trimmed!!!") == "apple outlook trimmed"
    assert event_cluster_key("Apple Outlook Trimmed!!!", "AAPL") == event_cluster_key(
        "Apple outlook trimmed",
        "AAPL",
    )


def test_group_articles_for_events_clusters_same_story() -> None:
    from datetime import UTC, datetime

    from app.news_clustering import ParsedNewsArticle

    now = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)
    articles = [
        ParsedNewsArticle(
            payload={"url": "https://www.reuters.com/a"},
            title="Apple outlook trimmed",
            summary="Apple outlook trimmed",
            symbol="AAPL",
            published_at=now,
            url="https://www.reuters.com/a",
        ),
        ParsedNewsArticle(
            payload={"url": "https://www.bloomberg.com/b"},
            title="Apple outlook trimmed!",
            summary="Apple outlook trimmed",
            symbol="AAPL",
            published_at=now,
            url="https://www.bloomberg.com/b",
        ),
    ]

    clusters = group_articles_for_events(articles)

    assert len(clusters) == 1
    assert len(clusters[0].articles) == 2


def test_ingest_runtime_groups_articles_into_single_event() -> None:
    upsert_payloads: dict[str, list[object]] = {}

    def table_side_effect(name: str) -> MagicMock:
        mock = MagicMock()

        def upsert(rows: object, **_kwargs: object) -> MagicMock:
            upsert_payloads.setdefault(name, []).append(rows)
            return mock

        mock.upsert = upsert
        return mock

    client = MagicMock()
    client.table.side_effect = table_side_effect
    store = SupabaseOperationStore(client)
    snapshot = MarketRuntimeSnapshot(
        data_mode=DataMode.LIVE.value,
        provider="finnhub_news",
        warnings=(),
        checks={
            "news": ProviderProbeResult(
                provider="finnhub_news",
                data_mode=DataMode.LIVE.value,
                ok=True,
                warnings=(),
                payload={
                    "articles": [
                        {
                            "url": "https://www.reuters.com/markets/apple-outlook",
                            "title": "Apple outlook trimmed after earnings",
                            "summary": "Apple outlook trimmed after earnings",
                        },
                        {
                            "url": "https://www.bloomberg.com/news/apple-outlook-trimmed",
                            "title": "Apple outlook trimmed after earnings!",
                            "summary": "Apple outlook trimmed after earnings",
                        },
                    ]
                },
            )
        },
        request_budget=8,
        requests_used=1,
    )

    rows_read, rows_written = store.ingest_runtime(snapshot, load_market_universe())

    assert rows_read > 0
    assert rows_written > 0
    assert len(upsert_payloads["events"][0]) == 1
    assert len(upsert_payloads["event_articles"][0]) == 2
    assert len(upsert_payloads["sources"][0]) == 2
