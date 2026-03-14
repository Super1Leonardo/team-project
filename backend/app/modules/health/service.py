class HealthService:
    def healthcheck(self) -> dict[str, str]:
        return {"status": "ok"}
