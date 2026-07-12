"""Pure market-return helpers."""

from __future__ import annotations

from statistics import fmean

from app.contracts.entities import MarketSnapshot, PriceReaction, allow_internal_field_names


def compute_asset_return(snapshot: MarketSnapshot) -> float:
    observations = snapshot.observations
    return observations[-1].close / observations[-2].close - 1


def compute_benchmark_return(
    *,
    asset_snapshot: MarketSnapshot,
    benchmark_snapshot: MarketSnapshot | None,
) -> float | None:
    if asset_snapshot.benchmark_asset_id is None or benchmark_snapshot is None:
        return None
    return compute_asset_return(benchmark_snapshot)


def compute_relative_volume(snapshot: MarketSnapshot) -> float | None:
    if len(snapshot.observations) < 21:
        return None
    prior_volumes = [point.volume for point in snapshot.observations[-21:-1]]
    if any(volume is None for volume in prior_volumes):
        return None
    current_volume = snapshot.observations[-1].volume
    if current_volume is None:
        return None
    return current_volume / fmean(volume for volume in prior_volumes if volume is not None)


def build_price_reaction(
    *,
    asset_return: float,
    benchmark_return: float | None,
    relative_volume: float | None,
) -> PriceReaction:
    abnormal_return = (
        None if benchmark_return is None else asset_return - benchmark_return
    )
    with allow_internal_field_names():
        return PriceReaction(
            asset_return=asset_return,
            benchmark_return=benchmark_return,
            abnormal_return=abnormal_return,
            relative_volume=relative_volume,
        )
