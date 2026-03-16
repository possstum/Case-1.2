from __future__ import annotations

import re
import unicodedata

CYRILLIC_TO_LATIN = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "i",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)
BRACKETED_SEGMENT_RE = re.compile(r"[\(\[\{].*?[\)\]\}]")
SEPARATOR_RE = re.compile(r"[\/_|:+,&]+")
NON_ALNUM_RE = re.compile(r"[^0-9a-zа-я\s-]+", re.IGNORECASE)
HYPHEN_RE = re.compile(r"[-–—]+")
WHITESPACE_RE = re.compile(r"\s+")


def strip_diacritics(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def normalize_whitespace(value: str) -> str:
    return WHITESPACE_RE.sub(" ", value).strip()


def transliterate_cyrillic(value: str) -> str:
    return value.translate(CYRILLIC_TO_LATIN)


def display_norm(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = strip_diacritics(normalized)
    normalized = SEPARATOR_RE.sub(" ", normalized)
    normalized = HYPHEN_RE.sub(" ", normalized)
    normalized = NON_ALNUM_RE.sub(" ", normalized)
    return normalize_whitespace(normalized)


def match_norm(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).lower()
    normalized = BRACKETED_SEGMENT_RE.sub(" ", normalized)
    normalized = strip_diacritics(normalized)
    normalized = SEPARATOR_RE.sub(" ", normalized)
    normalized = HYPHEN_RE.sub(" ", normalized)
    normalized = NON_ALNUM_RE.sub(" ", normalized)
    normalized = transliterate_cyrillic(normalized)
    normalized = normalize_whitespace(normalized)
    return normalized


def norm_tokens(value: str) -> list[str]:
    normalized = match_norm(value)
    if not normalized:
        return []
    return [token for token in normalized.split(" ") if token]
