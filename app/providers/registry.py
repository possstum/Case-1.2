from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.providers.base import MusicProvider


@dataclass(frozen=True)
class ProviderRegistry:
    providers: tuple[MusicProvider, ...]

    def all(self) -> tuple[MusicProvider, ...]:
        return self.providers

    def get(self, provider_name: str) -> Optional[MusicProvider]:
        for provider in self.providers:
            if provider.provider_name.value == provider_name:
                return provider
        return None
