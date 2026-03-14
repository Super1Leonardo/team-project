from __future__ import annotations

from dataclasses import dataclass, field

from app.common.enums import RelevanceLabel
from app.common.types import combine_title_text, normalize_text
from app.modules.brands.models import Brand


@dataclass(slots=True)
class BrandMatchResult:
    brand: Brand | None
    matched_keywords: list[str] = field(default_factory=list)
    exception_hits: list[str] = field(default_factory=list)
    risk_words_hit: list[str] = field(default_factory=list)
    relevance_label: RelevanceLabel = RelevanceLabel.REVIEW
    rule_score: float = 0.0


class BrandMatchService:
    def match(self, brands: list[Brand], title: str, text: str) -> BrandMatchResult:
        haystack = normalize_text(combine_title_text(title, text))
        if not haystack:
            return BrandMatchResult(brand=None, relevance_label=RelevanceLabel.REVIEW)

        ranked: list[tuple[int, int, str, Brand, list[str], list[str], list[str]]] = []
        had_exception_hit = False

        for brand in brands:
            keyword_hits = [term for term in brand.keywords if normalize_text(term) and normalize_text(term) in haystack]
            exception_hits = [term for term in brand.exceptions if normalize_text(term) and normalize_text(term) in haystack]
            risk_hits = [term for term in brand.risk_words if normalize_text(term) and normalize_text(term) in haystack]

            if exception_hits:
                had_exception_hit = True
                continue
            if not keyword_hits:
                continue

            ranked.append(
                (
                    len(keyword_hits),
                    len(risk_hits),
                    brand.name.casefold(),
                    brand,
                    keyword_hits,
                    exception_hits,
                    risk_hits,
                )
            )

        if not ranked:
            return BrandMatchResult(
                brand=None,
                relevance_label=RelevanceLabel.IRRELEVANT if had_exception_hit else RelevanceLabel.REVIEW,
                rule_score=0.15 if had_exception_hit else 0.5,
            )

        ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
        keyword_count, risk_count, _, brand, keyword_hits, exception_hits, risk_hits = ranked[0]
        rule_score = min(0.99, 0.6 + 0.1 * keyword_count + 0.05 * risk_count)
        return BrandMatchResult(
            brand=brand,
            matched_keywords=keyword_hits,
            exception_hits=exception_hits,
            risk_words_hit=risk_hits,
            relevance_label=RelevanceLabel.RELEVANT,
            rule_score=rule_score,
        )
