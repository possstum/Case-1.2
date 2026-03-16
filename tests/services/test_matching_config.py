from __future__ import annotations

from app.core.config import clear_settings_cache
from app.services.matching_service import MatchingConfig


def test_matching_thresholds_are_configurable_via_env(monkeypatch) -> None:
    monkeypatch.setenv("MATCH_CANDIDATE_THRESHOLD", "0.4")
    monkeypatch.setenv("MATCH_AMBIGUOUS_THRESHOLD", "0.7")
    monkeypatch.setenv("MATCH_AUTO_THRESHOLD", "0.93")
    monkeypatch.setenv("MATCH_GAP_THRESHOLD", "0.02")
    clear_settings_cache()

    config = MatchingConfig.from_settings()

    assert config.candidate_threshold == 0.4
    assert config.ambiguous_threshold == 0.7
    assert config.auto_threshold == 0.93
    assert config.gap_threshold == 0.02

    clear_settings_cache()
