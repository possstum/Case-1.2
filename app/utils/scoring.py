from __future__ import annotations

from difflib import SequenceMatcher
from typing import Iterable, Optional


def rounded(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


def sequence_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return rounded(SequenceMatcher(a=left, b=right).ratio())


def token_jaccard(left_tokens: Iterable[str], right_tokens: Iterable[str]) -> float:
    left_set = {token for token in left_tokens if token}
    right_set = {token for token in right_tokens if token}
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return rounded(len(left_set & right_set) / len(left_set | right_set))


def overlap_coefficient(left_tokens: Iterable[str], right_tokens: Iterable[str]) -> float:
    left_set = {token for token in left_tokens if token}
    right_set = {token for token in right_tokens if token}
    if not left_set and not right_set:
        return 1.0
    if not left_set or not right_set:
        return 0.0
    return rounded(len(left_set & right_set) / min(len(left_set), len(right_set)))


def year_proximity(left_year: Optional[int], right_year: Optional[int]) -> float:
    if left_year is None or right_year is None:
        return 0.5
    diff = abs(left_year - right_year)
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.8
    if diff == 2:
        return 0.6
    if diff <= 5:
        return rounded(max(0.0, 0.6 - (diff - 2) * 0.15))
    return 0.0


def count_proximity(left_count: Optional[int], right_count: Optional[int]) -> float:
    if left_count is None or right_count is None:
        return 0.5
    if left_count == right_count:
        return 1.0
    diff = abs(left_count - right_count)
    baseline = max(left_count, right_count, 1)
    return rounded(max(0.0, 1 - diff / baseline))


def duration_proximity(left_ms: Optional[int], right_ms: Optional[int]) -> float:
    if left_ms is None or right_ms is None:
        return 0.5
    diff = abs(left_ms - right_ms)
    if diff == 0:
        return 1.0
    if diff >= 90_000:
        return 0.0
    return rounded(max(0.0, 1 - diff / 90_000))
