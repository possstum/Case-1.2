from app.utils.version_tags import extract_version_tags, version_compatibility


def test_extract_version_tags_detects_common_variants() -> None:
    assert extract_version_tags("Song Title (Deluxe Remastered)") == ["deluxe", "remaster"]


def test_version_compatibility_flags_strong_conflicts() -> None:
    score, conflicts = version_compatibility(["live"], ["remix"])

    assert score == 0.45
    assert conflicts == ["live", "remix"]
