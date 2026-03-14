from backend.app.infra.db.clickhouse import ClickHouseMessageStore


class MessagesRepository(ClickHouseMessageStore):
    """ClickHouse-backed messages repository."""
