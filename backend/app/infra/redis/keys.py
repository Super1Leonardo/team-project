from __future__ import annotations

import uuid
from datetime import datetime

from app.core.time import floor_to_window


def spike_counter_key(project_id: uuid.UUID, brand_id: uuid.UUID, bucket_at: datetime, window_minutes: int) -> str:
    bucket = floor_to_window(bucket_at, window_minutes).isoformat()
    return f"alerts:spike:{project_id}:{brand_id}:{window_minutes}:{bucket}"


def spike_cooldown_key(project_id: uuid.UUID, brand_id: uuid.UUID) -> str:
    return f"alerts:cooldown:{project_id}:{brand_id}"
