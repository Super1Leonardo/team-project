from __future__ import annotations

import uuid

from app.core.time import utc_now
from app.modules.brands.models import Brand
from app.modules.mentions.services.brand_match import BrandMatchService


def make_brand(
    *,
    name: str,
    keywords: list[str],
    exceptions: list[str] | None = None,
    risk_words: list[str] | None = None,
) -> Brand:
    now = utc_now()
    return Brand(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name=name,
        keywords=keywords,
        exceptions=exceptions or [],
        risk_words=risk_words or [],
        spike_threshold=2,
        spike_window_minutes=60,
        spike_cooldown_minutes=60,
        created_at=now,
        updated_at=now,
    )


def test_brand_match_picks_brand_and_extracts_risk_words() -> None:
    service = BrandMatchService()
    acme = make_brand(name="Acme", keywords=["acme"], risk_words=["сбой", "утечка"])
    other = make_brand(name="Other", keywords=["other"], exceptions=["other kids"])

    result = service.match(
        [other, acme],
        "У Acme произошел сбой",
        "Пользователи пишут, что у Acme случился серьезный сбой сервиса.",
    )

    assert result.brand is not None
    assert result.brand.id == acme.id
    assert result.relevance_label.value == "relevant"
    assert "acme" in [value.casefold() for value in result.matched_keywords]
    assert "сбой" in [value.casefold() for value in result.risk_words_hit]


def test_brand_match_respects_exceptions() -> None:
    service = BrandMatchService()
    brand = make_brand(name="Acme", keywords=["acme"], exceptions=["acme junior"])

    result = service.match([brand], "Acme Junior", "Acme Junior снова в новостях")

    assert result.brand is None
    assert result.relevance_label.value == "irrelevant"
