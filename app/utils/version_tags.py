from __future__ import annotations

import re

from app.utils.normalization import display_norm, transliterate_cyrillic

TAG_PATTERNS = {
    "live": [r"\blive\b", r"\bzhiv", r"\bconcert\b"],
    "acoustic": [r"\bacoustic\b", r"\bakust"],
    "remaster": [r"\bremaster(?:ed)?\b", r"\bremastering\b", r"\bremast\b"],
    "remix": [r"\bremix\b", r"\bmix\b"],
    "instrumental": [r"\binstrumental\b"],
    "karaoke": [r"\bkaraoke\b"],
    "demo": [r"\bdemo\b"],
    "radio_edit": [r"\bradio edit\b"],
    "edit": [r"\bedit\b"],
    "extended": [r"\bextended\b"],
    "deluxe": [r"\bdeluxe\b"],
    "clean": [r"\bclean\b"],
    "explicit": [r"\bexplicit\b"],
    "mono": [r"\bmono\b"],
    "stereo": [r"\bstereo\b"],
    "original_mix": [r"\boriginal mix\b"],
    "bonus": [r"\bbonus\b"],
    "anniversary": [r"\banniversary\b"],
    "reissue": [r"\breissue\b"],
}
STRONG_VERSION_TAGS = {
    "live",
    "acoustic",
    "remix",
    "instrumental",
    "karaoke",
    "demo",
    "radio_edit",
    "extended",
    "deluxe",
    "clean",
    "explicit",
    "mono",
    "stereo",
    "original_mix",
    "reissue",
}


def extract_version_tags(*values: str | None) -> list[str]:
    normalized_parts = [
        transliterate_cyrillic(display_norm(value or ""))
        for value in values
        if value
    ]
    normalized_text = " ".join(part for part in normalized_parts if part)
    if not normalized_text:
        return []

    detected_tags: set[str] = set()
    for tag, patterns in TAG_PATTERNS.items():
        if any(re.search(pattern, normalized_text) for pattern in patterns):
            detected_tags.add(tag)
    return sorted(detected_tags)


def version_compatibility(
    left_tags: list[str],
    right_tags: list[str],
) -> tuple[float, list[str]]:
    left_set = set(left_tags)
    right_set = set(right_tags)
    symmetric_diff = sorted(left_set.symmetric_difference(right_set))
    strong_conflicts = sorted(
        tag for tag in symmetric_diff if tag in STRONG_VERSION_TAGS
    )

    if not left_set and not right_set:
        return 1.0, []
    if left_set == right_set:
        return 1.0, []
    if strong_conflicts:
        return 0.45, strong_conflicts

    overlap = len(left_set & right_set)
    union = len(left_set | right_set)
    return round(overlap / union if union else 1.0, 4), symmetric_diff
