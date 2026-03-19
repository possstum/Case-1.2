from __future__ import annotations

from app.providers.base import (
    MusicProvider,
    ProviderArtist,
    ProviderEntityKind,
    ProviderName,
    ProviderSearchHit,
    ProviderSearchResult,
)
from app.utils.normalization import display_norm, match_norm


class StubProvider(MusicProvider):
    provider_name = ProviderName.YOUTUBE

    def __init__(self) -> None:
        self.artist = ProviderArtist(
            provider=ProviderName.YOUTUBE,
            provider_id="stub-artist",
            name="Кровосток",
            display_norm=display_norm("Кровосток"),
            match_norm=match_norm("Кровосток"),
        )

    def search(
        self,
        query: str,
        *,
        limit: int | None,
        kind: ProviderEntityKind | None = None,
    ) -> ProviderSearchResult:
        return ProviderSearchResult(
            query=query,
            items=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=self.artist)],
        )

    def get_artist(self, provider_id: str) -> ProviderArtist:
        assert provider_id == self.artist.provider_id
        return self.artist

    def get_release(self, provider_id: str):
        raise NotImplementedError

    def get_track(self, provider_id: str):
        raise NotImplementedError


def test_provider_contract_is_mockable_without_http() -> None:
    provider = StubProvider()

    search_result = provider.search("кровосток", limit=5, kind=ProviderEntityKind.ARTIST)
    artist = provider.get_artist("stub-artist")

    assert search_result.items[0].entity.provider_id == "stub-artist"
    assert artist.match_norm == "krovostok"
