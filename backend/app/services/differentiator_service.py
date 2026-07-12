"""Phase 10 differentiator services."""

from __future__ import annotations

import re
from typing import Any

from app.contracts.api import (
    EcuadorSnapshot,
    EcuadorSnapshotListResponse,
    SimilarEvent,
    SimilarEventListResponse,
)
from app.contracts.entities import DataMode, Freshness, allow_internal_field_names
from app.contracts.fixtures import sha256_digest
from app.repositories.fixture_repository import FixtureRepository

TOKEN_RE = re.compile(r"[a-z0-9]+")


class DifferentiatorService:
    def __init__(self, repository: FixtureRepository) -> None:
        self._repository = repository

    def list_similar_events(self, event_id: str) -> SimilarEventListResponse:
        target, _ = self._repository.get_event(event_id)
        target_tokens = self._event_tokens(event_id)
        target_assets = {relation.symbol for relation in target.related_assets}
        target_groups = self._source_groups(event_id)

        similar: list[SimilarEvent] = []
        for candidate, _ in self._repository.list_events():
            if candidate.id == event_id:
                continue
            candidate_tokens = self._event_tokens(candidate.id)
            candidate_assets = {relation.symbol for relation in candidate.related_assets}
            candidate_groups = self._source_groups(candidate.id)
            token_score = self._jaccard(target_tokens, candidate_tokens)
            shared_assets = tuple(sorted(target_assets & candidate_assets))
            shared_groups = tuple(sorted(target_groups & candidate_groups))
            score = min(
                1.0,
                (0.55 if shared_assets else 0.0)
                + (0.20 if shared_groups else 0.0)
                + (0.25 * token_score),
            )
            rationale = self._similarity_rationale(
                shared_assets=shared_assets,
                shared_groups=shared_groups,
                token_score=token_score,
            )
            with allow_internal_field_names():
                similar.append(
                    SimilarEvent(
                        event_id=candidate.id,
                        title=candidate.title,
                        event_at=candidate.event_at,
                        similarity_score=round(float(score), 4),
                        shared_asset_symbols=shared_assets,
                        shared_source_groups=shared_groups,
                        rationale=rationale,
                    )
                )

        data = tuple(
            sorted(
                similar,
                key=lambda item: (-item.similarity_score, item.event_at, item.event_id),
            )
        )
        with allow_internal_field_names():
            return SimilarEventListResponse(data=data, meta=self._repository.get_meta())

    def list_ecuador_snapshots(self) -> EcuadorSnapshotListResponse:
        meta = self._repository.get_meta()
        clock = self._repository.fixture_clock
        with allow_internal_field_names():
            freshness = Freshness(
                evaluated_at=clock,
                stale_after_seconds=604_800,
                is_stale=False,
            )
        rows = (
            {
                "id": "ecuador_snapshot_bce_macro_202607",
                "title": "Contexto macro Ecuador para lectura de riesgo",
                "summary": (
                    "Snapshot institucional versionado para mantener trazabilidad local "
                    "cuando el MVP compara eventos globales con contexto ecuatoriano."
                ),
                "source_name": "Banco Central del Ecuador",
                "source_url": "https://www.bce.fin.ec/",
                "captured_at": clock,
                "provider": "ecuador_institutional_snapshot",
            },
            {
                "id": "ecuador_snapshot_supercias_market_202607",
                "title": "Referencia regulatoria ecuatoriana para emisores y mercado",
                "summary": (
                    "Snapshot institucional usado como evidencia contextual, no como "
                    "senal automatica de compra o venta."
                ),
                "source_name": "Superintendencia de Companias, Valores y Seguros",
                "source_url": "https://www.supercias.gob.ec/",
                "captured_at": clock,
                "provider": "ecuador_institutional_snapshot",
            },
        )
        snapshots: list[EcuadorSnapshot] = []
        for row in rows:
            payload: dict[str, Any] = {
                "id": row["id"],
                "title": row["title"],
                "summary": row["summary"],
                "sourceName": row["source_name"],
                "sourceUrl": row["source_url"],
                "capturedAt": row["captured_at"].isoformat(),
            }
            with allow_internal_field_names():
                snapshots.append(
                    EcuadorSnapshot(
                        id=row["id"],
                        title=row["title"],
                        summary=row["summary"],
                        country_code="EC",
                        source_name=row["source_name"],
                        source_url=row["source_url"],
                        captured_at=row["captured_at"],
                        content_hash=sha256_digest(payload),
                        data_mode=DataMode.FIXTURE,
                        provider=row["provider"],
                        retrieved_at=meta.retrieved_at,
                        data_as_of=meta.data_as_of,
                        freshness=freshness,
                        warnings=("FIXTURE_ECUADOR_SNAPSHOT", "NOT_REAL_TIME"),
                    )
                )
        with allow_internal_field_names():
            return EcuadorSnapshotListResponse(data=tuple(snapshots), meta=meta)

    def _event_tokens(self, event_id: str) -> set[str]:
        view_event, _ = self._repository.get_event(event_id)
        articles = self._repository.get_event_articles(event_id)
        text = " ".join(
            (
                view_event.title,
                view_event.summary,
                *(article.headline for article in articles),
                *(article.summary for article in articles),
            )
        )
        return {token for token in TOKEN_RE.findall(text.lower()) if len(token) > 2}

    def _source_groups(self, event_id: str) -> set[str]:
        return {
            source.publisher_group_id
            for source in self._repository.get_event_sources(event_id)
            if source.is_original_publisher and not source.is_aggregator
        }

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def _similarity_rationale(
        self,
        *,
        shared_assets: tuple[str, ...],
        shared_groups: tuple[str, ...],
        token_score: float,
    ) -> str:
        reasons: list[str] = []
        if shared_assets:
            reasons.append(f"comparte activos {', '.join(shared_assets)}")
        if shared_groups:
            reasons.append("comparte publishers originales")
        if token_score > 0:
            reasons.append(f"similitud narrativa {token_score:.2f}")
        return "; ".join(reasons) if reasons else "comparacion historica de baja similitud"


__all__ = ["DifferentiatorService"]
