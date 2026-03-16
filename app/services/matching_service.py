from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.providers.base import (
    ProviderArtist,
    ProviderEntity,
    ProviderEntityKind,
    ProviderRelease,
    ProviderTrack,
)
from app.utils.normalization import norm_tokens
from app.utils.scoring import (
    count_proximity,
    duration_proximity,
    overlap_coefficient,
    rounded,
    sequence_similarity,
    token_jaccard,
    year_proximity,
)
from app.utils.version_tags import version_compatibility


class MatchDecision(str):
    AUTO = "auto"
    AMBIGUOUS = "ambiguous"
    REJECT = "reject"


class CandidateExplanation(BaseModel):
    provider: str
    provider_id: str
    kind: ProviderEntityKind
    score: float
    features_json: dict[str, Any] = Field(default_factory=dict)


class MatchResult(BaseModel):
    decision: str
    score: float
    matched_candidate: Optional[CandidateExplanation] = None
    considered_candidates: list[CandidateExplanation] = Field(default_factory=list)
    features_json: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class MatchingConfig:
    candidate_threshold: float
    ambiguous_threshold: float
    auto_threshold: float
    gap_threshold: float

    @classmethod
    def from_settings(cls) -> "MatchingConfig":
        settings = get_settings()
        return cls(
            candidate_threshold=settings.match_candidate_threshold,
            ambiguous_threshold=settings.match_ambiguous_threshold,
            auto_threshold=settings.match_auto_threshold,
            gap_threshold=settings.match_gap_threshold,
        )


class MatchingService:
    def __init__(self, config: Optional[MatchingConfig] = None) -> None:
        self.config = config or MatchingConfig.from_settings()

    def match_artists(
        self,
        subject: ProviderArtist,
        candidates: list[ProviderArtist],
    ) -> MatchResult:
        return self._match(
            subject=subject,
            candidates=candidates,
            scorer=self._score_artist,
        )

    def match_releases(
        self,
        subject: ProviderRelease,
        candidates: list[ProviderRelease],
    ) -> MatchResult:
        return self._match(
            subject=subject,
            candidates=candidates,
            scorer=self._score_release,
        )

    def match_tracks(
        self,
        subject: ProviderTrack,
        candidates: list[ProviderTrack],
    ) -> MatchResult:
        return self._match(
            subject=subject,
            candidates=candidates,
            scorer=self._score_track,
        )

    def _match(
        self,
        *,
        subject: ProviderEntity,
        candidates: list[ProviderEntity],
        scorer,
    ) -> MatchResult:
        generated_candidates = self._generate_candidates(subject, candidates)
        if not generated_candidates:
            return MatchResult(
                decision=MatchDecision.REJECT,
                score=0.0,
                features_json={
                    "entity_kind": subject.kind,
                    "reason": "no_candidates",
                },
            )

        scored_candidates = []
        for candidate in generated_candidates:
            score, features_json = scorer(subject, candidate)
            if score >= self.config.candidate_threshold:
                scored_candidates.append(
                    CandidateExplanation(
                        provider=candidate.provider.value,
                        provider_id=candidate.provider_id,
                        kind=candidate.kind,
                        score=score,
                        features_json=features_json,
                    )
                )

        if not scored_candidates:
            return MatchResult(
                decision=MatchDecision.REJECT,
                score=0.0,
                features_json={
                    "entity_kind": subject.kind,
                    "reason": "all_candidates_below_threshold",
                    "candidate_threshold": self.config.candidate_threshold,
                },
            )

        scored_candidates.sort(key=lambda item: item.score, reverse=True)
        top_candidate = scored_candidates[0]
        second_candidate = scored_candidates[1] if len(scored_candidates) > 1 else None

        decision_reasons: list[str] = []
        if top_candidate.score < self.config.ambiguous_threshold:
            decision = MatchDecision.REJECT
            decision_reasons.append("score_below_ambiguous_threshold")
        else:
            if top_candidate.score < self.config.auto_threshold:
                decision_reasons.append("score_below_auto_threshold")
            if second_candidate and (top_candidate.score - second_candidate.score) < self.config.gap_threshold:
                decision_reasons.append("top_gap_too_small")
            if top_candidate.features_json.get("version_conflicts"):
                decision_reasons.append("version_conflict")

            decision = MatchDecision.AUTO if not decision_reasons else MatchDecision.AMBIGUOUS

        features_json = {
            **top_candidate.features_json,
            "decision_reasons": decision_reasons,
            "candidate_count": len(scored_candidates),
            "candidate_threshold": self.config.candidate_threshold,
            "ambiguous_threshold": self.config.ambiguous_threshold,
            "auto_threshold": self.config.auto_threshold,
            "gap_threshold": self.config.gap_threshold,
            "top_gap": rounded(
                top_candidate.score - second_candidate.score if second_candidate else top_candidate.score
            ),
        }

        if decision == MatchDecision.REJECT:
            return MatchResult(
                decision=decision,
                score=top_candidate.score,
                matched_candidate=None,
                considered_candidates=scored_candidates,
                features_json=features_json,
            )

        top_candidate.features_json = features_json
        return MatchResult(
            decision=decision,
            score=top_candidate.score,
            matched_candidate=top_candidate,
            considered_candidates=scored_candidates,
            features_json=features_json,
        )

    def _generate_candidates(
        self,
        subject: ProviderEntity,
        candidates: list[ProviderEntity],
    ) -> list[ProviderEntity]:
        generated: list[ProviderEntity] = []
        for candidate in candidates:
            if subject.kind != candidate.kind:
                continue

            name_token_overlap = overlap_coefficient(
                norm_tokens(subject.match_norm),
                norm_tokens(candidate.match_norm),
            )

            if subject.kind == ProviderEntityKind.ARTIST:
                alias_overlap = self._artist_alias_overlap(subject, candidate)
                if max(name_token_overlap, alias_overlap) >= self.config.candidate_threshold:
                    generated.append(candidate)
                continue

            artist_overlap = overlap_coefficient(
                getattr(subject, "artist_match_norms", []),
                getattr(candidate, "artist_match_norms", []),
            )

            if name_token_overlap >= self.config.candidate_threshold and (
                artist_overlap >= 0.5 or name_token_overlap >= 0.8
            ):
                generated.append(candidate)

        return generated

    def _score_artist(
        self,
        subject: ProviderArtist,
        candidate: ProviderArtist,
    ) -> tuple[float, dict[str, Any]]:
        name_tokens_subject = norm_tokens(subject.match_norm)
        name_tokens_candidate = norm_tokens(candidate.match_norm)
        name_token_overlap = token_jaccard(name_tokens_subject, name_tokens_candidate)
        name_sequence_similarity = sequence_similarity(subject.match_norm, candidate.match_norm)
        alias_overlap = self._artist_alias_overlap(subject, candidate)

        score = rounded(
            0.45 * name_token_overlap
            + 0.35 * name_sequence_similarity
            + 0.20 * alias_overlap
        )
        return score, {
            "entity_kind": subject.kind,
            "name_token_overlap": name_token_overlap,
            "name_sequence_similarity": name_sequence_similarity,
            "alias_overlap": alias_overlap,
        }

    def _score_release(
        self,
        subject: ProviderRelease,
        candidate: ProviderRelease,
    ) -> tuple[float, dict[str, Any]]:
        title_token_overlap = token_jaccard(norm_tokens(subject.match_norm), norm_tokens(candidate.match_norm))
        title_sequence_similarity = sequence_similarity(subject.match_norm, candidate.match_norm)
        artist_overlap = overlap_coefficient(subject.artist_match_norms, candidate.artist_match_norms)
        year_score = year_proximity(subject.release_year, candidate.release_year)
        track_count_score = count_proximity(subject.track_count, candidate.track_count)
        version_score, version_conflicts = version_compatibility(
            subject.version_tags_json,
            candidate.version_tags_json,
        )

        raw_score = (
            0.32 * title_token_overlap
            + 0.20 * title_sequence_similarity
            + 0.22 * artist_overlap
            + 0.12 * year_score
            + 0.09 * track_count_score
            + 0.05 * version_score
        )
        if version_conflicts:
            raw_score -= 0.12

        score = rounded(raw_score)
        return score, {
            "entity_kind": subject.kind,
            "title_token_overlap": title_token_overlap,
            "title_sequence_similarity": title_sequence_similarity,
            "artist_overlap": artist_overlap,
            "year_score": year_score,
            "track_count_score": track_count_score,
            "version_score": version_score,
            "version_conflicts": version_conflicts,
        }

    def _score_track(
        self,
        subject: ProviderTrack,
        candidate: ProviderTrack,
    ) -> tuple[float, dict[str, Any]]:
        title_token_overlap = token_jaccard(norm_tokens(subject.match_norm), norm_tokens(candidate.match_norm))
        title_sequence_similarity = sequence_similarity(subject.match_norm, candidate.match_norm)
        artist_overlap = overlap_coefficient(subject.artist_match_norms, candidate.artist_match_norms)
        duration_score = duration_proximity(subject.duration_ms, candidate.duration_ms)
        release_score = token_jaccard(
            norm_tokens(subject.release_match_norm or ""),
            norm_tokens(candidate.release_match_norm or ""),
        )
        version_score, version_conflicts = version_compatibility(
            subject.version_tags_json,
            candidate.version_tags_json,
        )

        raw_score = (
            0.30 * title_token_overlap
            + 0.20 * title_sequence_similarity
            + 0.25 * artist_overlap
            + 0.15 * duration_score
            + 0.05 * release_score
            + 0.05 * version_score
        )
        if version_conflicts:
            raw_score -= 0.1
        if duration_score < 0.25 and title_token_overlap >= 0.8:
            raw_score -= 0.35

        score = rounded(raw_score)
        return score, {
            "entity_kind": subject.kind,
            "title_token_overlap": title_token_overlap,
            "title_sequence_similarity": title_sequence_similarity,
            "artist_overlap": artist_overlap,
            "duration_score": duration_score,
            "release_score": release_score,
            "version_score": version_score,
            "version_conflicts": version_conflicts,
        }

    def _artist_alias_overlap(
        self,
        subject: ProviderArtist,
        candidate: ProviderArtist,
    ) -> float:
        subject_aliases = list(subject.alias_match_norms) + [subject.match_norm]
        candidate_aliases = list(candidate.alias_match_norms) + [candidate.match_norm]
        best_overlap = 0.0
        for left_alias in subject_aliases:
            for right_alias in candidate_aliases:
                best_overlap = max(
                    best_overlap,
                    sequence_similarity(left_alias, right_alias),
                    token_jaccard(norm_tokens(left_alias), norm_tokens(right_alias)),
                )
        return rounded(best_overlap)
