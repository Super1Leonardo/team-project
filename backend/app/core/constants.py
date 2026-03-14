DEFAULT_SPIKE_THRESHOLD = 3
DEFAULT_SPIKE_WINDOW_MINUTES = 60
DEFAULT_SPIKE_COOLDOWN_MINUTES = 60

NEGATIVE_HINT_WORDS = {
    "авария",
    "бойкот",
    "жалоба",
    "негатив",
    "ошибка",
    "провал",
    "проблема",
    "скандал",
    "сбой",
    "упал",
    "утечка",
    "crash",
    "fail",
    "issue",
    "negative",
    "outage",
    "problem",
}

POSITIVE_HINT_WORDS = {
    "growth",
    "improved",
    "launch",
    "love",
    "успех",
    "хвалят",
    "хороший",
    "рост",
    "стабильно",
    "улучшение",
}

CRITICAL_HINT_WORDS = {
    "авария",
    "бойкот",
    "иск",
    "катастрофа",
    "критический",
    "массовый",
    "outage",
    "recall",
    "lawsuit",
}

EVENT_PROJECT_CREATED = "project_created"
EVENT_BRAND_CREATED = "brand_created"
EVENT_BRAND_UPDATED = "brand_updated"
EVENT_SOURCE_CREATED = "source_created"
EVENT_SOURCE_FAILED = "source_failed"
EVENT_MENTION_INGESTED = "mention_ingested"
EVENT_DUPLICATE_DETECTED = "duplicate_detected"
EVENT_ML_FAILED = "ml_failed"
EVENT_ML_UNAVAILABLE = "ml_unavailable"
EVENT_ALERT_CREATED = "alert_created"
EVENT_NOTIFICATION_SENT = "notification_sent"
EVENT_HEALTH_CHECK_FAILED = "health_check_failed"
