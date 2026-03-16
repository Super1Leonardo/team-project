from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from backend.app.modules.brandradar.schemas import (
    MentionConfidenceThreshold,
    MentionPeriod,
    ProjectUpdateRequest,
    SourceUpdateRequest,
)


def test_mention_confidence_threshold_values_map_to_floats() -> None:
    assert MentionConfidenceThreshold.at_least_05.threshold == 0.5
    assert MentionConfidenceThreshold.at_least_07.threshold == 0.7
    assert MentionConfidenceThreshold.at_least_09.threshold == 0.9


def test_mention_period_values_map_to_timedeltas() -> None:
    assert MentionPeriod.last_24_hours.delta == timedelta(hours=24)
    assert MentionPeriod.last_7_days.delta == timedelta(days=7)
    assert MentionPeriod.last_30_days.delta == timedelta(days=30)


def test_project_update_request_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="Provide at least one field"):
        ProjectUpdateRequest()


def test_project_update_request_rejects_empty_keywords_list() -> None:
    with pytest.raises(ValidationError, match="Project keywords must contain at least one item"):
        ProjectUpdateRequest(keywords=[])


def test_source_update_request_requires_at_least_one_field() -> None:
    with pytest.raises(ValidationError, match="Provide at least one field"):
        SourceUpdateRequest()
