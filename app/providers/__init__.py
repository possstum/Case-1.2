"""External platform provider integrations live here."""

from app.providers.base import (
    MusicProvider,
    ProviderArtist,
    ProviderEntity,
    ProviderEntityKind,
    ProviderName,
    ProviderRelease,
    ProviderSearchHit,
    ProviderSearchResult,
    ProviderTrack,
)
from app.providers.registry import ProviderRegistry

__all__ = [
    "MusicProvider",
    "ProviderArtist",
    "ProviderEntity",
    "ProviderEntityKind",
    "ProviderName",
    "ProviderRelease",
    "ProviderSearchHit",
    "ProviderSearchResult",
    "ProviderTrack",
    "ProviderRegistry",
]
