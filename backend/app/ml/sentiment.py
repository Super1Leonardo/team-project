from __future__ import annotations


class LexiconSentimentAnalyzer:
    NEGATIVE_WORDS = {
        "сбой",
        "утеч",
        "мошенн",
        "взлом",
        "жалоб",
        "ошибк",
        "проблем",
        "паден",
        "отказ",
        "негатив",
        "скандал",
        "штраф",
    }
    POSITIVE_WORDS = {
        "запуск",
        "рост",
        "успех",
        "улучш",
        "прибыл",
        "награ",
        "лидер",
        "побед",
        "рекорд",
    }

    def analyze(self, text: str) -> tuple[str, float]:
        normalized = self._normalize(text)
        negative_hits = sum(word in normalized for word in self.NEGATIVE_WORDS)
        positive_hits = sum(word in normalized for word in self.POSITIVE_WORDS)

        if negative_hits > positive_hits:
            score = -min(1.0, 0.2 + 0.15 * (negative_hits - positive_hits))
            return "negative", score
        if positive_hits > negative_hits:
            score = min(1.0, 0.2 + 0.15 * (positive_hits - negative_hits))
            return "positive", score
        return "neutral", 0.0

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())
