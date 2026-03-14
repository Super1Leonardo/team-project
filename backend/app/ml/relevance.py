from __future__ import annotations


class KeywordRelevanceClassifier:
    def classify(
        self,
        text: str,
        keywords: list[str],
        exclude_keywords: list[str],
    ) -> tuple[str, float]:
        normalized = self._normalize(text)
        if any(self._normalize(item) in normalized for item in exclude_keywords):
            return "irrelevant", 0.0

        matches = [
            keyword
            for keyword in keywords
            if self._normalize(keyword) and self._normalize(keyword) in normalized
        ]
        if not matches:
            return "irrelevant", 0.0

        score = min(0.55 + 0.1 * len(matches), 0.99)
        return "relevant", score

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
