from app.utils.normalization import display_norm, match_norm, norm_tokens


def test_display_norm_preserves_script_but_normalizes_spacing() -> None:
    assert display_norm("  КРОВОСТОК  feat.   ??? ") == "кровосток feat"


def test_match_norm_transliterates_cyrillic_and_drops_bracketed_segments() -> None:
    assert match_norm("Кровосток (Live)") == "krovostok"


def test_norm_tokens_returns_split_match_tokens() -> None:
    assert norm_tokens("Molchat Doma") == ["molchat", "doma"]
