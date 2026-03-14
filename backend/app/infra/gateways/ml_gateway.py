from __future__ import annotations

import httpx

from app.common.enums import CriticalityLabel, RelevanceLabel, SentimentLabel
from app.core.config import Settings
from app.core.constants import CRITICAL_HINT_WORDS, NEGATIVE_HINT_WORDS, POSITIVE_HINT_WORDS
from app.infra.gateways.health_gateway import ExternalHealthGateway
from app.ports.ml import MLPrediction, MLPort, MLRequest, MLResultEnvelope


class MLGateway(MLPort):
    def __init__(self, settings: Settings, health_gateway: ExternalHealthGateway) -> None:
        self.settings = settings
        self.health_gateway = health_gateway

    async def predict(self, request: MLRequest) -> MLResultEnvelope:
        if self.settings.ml_service_url:
            try:
                return await self._predict_remote(request)
            except Exception as exc:
                return MLResultEnvelope(
                    prediction=self._fallback_prediction(request),
                    used_fallback=True,
                    failure_reason=str(exc),
                )
        return MLResultEnvelope(
            prediction=self._fallback_prediction(request),
            used_fallback=True,
            failure_reason=None,
        )

    async def healthcheck(self) -> tuple[bool, str | None, dict[str, object] | None]:
        if not self.settings.ml_service_url:
            return True, None, {"mode": "fallback"}

        url = self.settings.ml_service_url.rstrip("/") + self.settings.ml_health_path
        ok, detail, latency_ms = await self.health_gateway.check_url(url)
        return ok, detail, {"mode": "external", "latency_ms": latency_ms}

    async def _predict_remote(self, request: MLRequest) -> MLResultEnvelope:
        payload = {
            "project_id": str(request.project_id),
            "source_id": str(request.source_id),
            "title": request.title,
            "text": request.text,
            "normalized_text": request.normalized_text,
            "rule_relevance_label": request.rule_relevance_label,
            "risk_words_hit": request.risk_words_hit,
            "metadata": request.metadata,
        }
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(self.settings.ml_service_url, json=payload)
            response.raise_for_status()
            data = response.json()

        prediction = MLPrediction(
            relevance_label=RelevanceLabel(data["relevance_label"]),
            relevance_score=float(data["relevance_score"]),
            sentiment_label=SentimentLabel(data["sentiment_label"]),
            sentiment_score=float(data["sentiment_score"]),
            criticality_label=CriticalityLabel(data["criticality_label"]),
            criticality_score=float(data["criticality_score"]),
            risk_words_hit=sorted(set(data.get("risk_words_hit", []))),
            cluster_id=data.get("cluster_id"),
            provider=data.get("provider", "external-ml"),
            version=data.get("version", "v1"),
        )
        return MLResultEnvelope(prediction=prediction, used_fallback=False)

    def _fallback_prediction(self, request: MLRequest) -> MLPrediction:
        text = request.normalized_text

        negative_hits = [word for word in NEGATIVE_HINT_WORDS if word in text]
        positive_hits = [word for word in POSITIVE_HINT_WORDS if word in text]
        critical_hits = [word for word in CRITICAL_HINT_WORDS if word in text]
        risk_words_hit = sorted(set(request.risk_words_hit + negative_hits + critical_hits))

        if negative_hits or risk_words_hit:
            sentiment_label = SentimentLabel.NEGATIVE
            sentiment_score = min(0.98, 0.65 + 0.08 * len(set(negative_hits + risk_words_hit)))
        elif positive_hits:
            sentiment_label = SentimentLabel.POSITIVE
            sentiment_score = min(0.95, 0.6 + 0.05 * len(positive_hits))
        else:
            sentiment_label = SentimentLabel.NEUTRAL
            sentiment_score = 0.55

        relevance_score = {
            RelevanceLabel.RELEVANT: 0.88,
            RelevanceLabel.IRRELEVANT: 0.12,
            RelevanceLabel.REVIEW: 0.51,
        }[request.rule_relevance_label]

        if critical_hits or len(risk_words_hit) >= 3:
            criticality_label = CriticalityLabel.CRITICAL
            criticality_score = 0.94
        elif sentiment_label == SentimentLabel.NEGATIVE and risk_words_hit:
            criticality_label = CriticalityLabel.HIGH
            criticality_score = 0.82
        elif risk_words_hit:
            criticality_label = CriticalityLabel.MEDIUM
            criticality_score = 0.68
        else:
            criticality_label = CriticalityLabel.LOW
            criticality_score = 0.42

        return MLPrediction(
            relevance_label=request.rule_relevance_label,
            relevance_score=relevance_score,
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            criticality_label=criticality_label,
            criticality_score=criticality_score,
            risk_words_hit=risk_words_hit,
            cluster_id=str(request.metadata.get("content_hash", ""))[:12] or None,
            provider="fallback-rule-based",
            version="fallback-v1",
        )
