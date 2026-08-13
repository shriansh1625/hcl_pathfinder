"""Pack sequenced resources into weeks under a weekly hour budget."""

from __future__ import annotations

from math import ceil

from app.services.recommendation.models import PlannedItem, ScoredCandidate


def pack_weeks(
    ordered: list[ScoredCandidate],
    weekly_hours: float,
) -> list[PlannedItem]:
    hours = weekly_hours if weekly_hours > 0 else 1.0
    week = 1
    used = 0.0
    packed: list[PlannedItem] = []
    for position, candidate in enumerate(ordered):
        duration = candidate.resource.duration_hours
        if duration > hours:
            if used > 0:
                week += 1
                used = 0.0
            packed.append(PlannedItem(candidate=candidate, position=position, week_index=week))
            week += max(1, ceil(duration / hours)) - 1
            week += 1
            used = 0.0
            continue
        if used > 0 and used + duration > hours + 1e-9:
            week += 1
            used = 0.0
        packed.append(PlannedItem(candidate=candidate, position=position, week_index=week))
        used += duration
    return packed
