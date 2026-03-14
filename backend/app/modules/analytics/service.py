from __future__ import annotations

from app.modules.analytics.repository import AnalyticsRepository
from app.modules.analytics.schemas import MentionsChartFilters, MentionsChartResponse


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self.repository = repository

    async def mentions_chart(self, filters: MentionsChartFilters) -> MentionsChartResponse:
        return await self.repository.mentions_chart(filters)
