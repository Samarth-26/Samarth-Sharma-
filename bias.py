
from __future__ import annotations

from collections import defaultdict
import re

POSITIVE = {"success", "growth", "win", "praise", "benefit", "improve", "strong", "support", "progress", "record"}
NEGATIVE = {"crisis", "failure", "loss", "critic", "attack", "risk", "scandal", "decline", "controversy", "concern"}


def score_sentiment(text: str) -> tuple[str, int]:
    words = re.findall(r"\b\w+\b", (text or "").lower())
    score = sum(word in POSITIVE for word in words) - sum(word in NEGATIVE for word in words)
    return ("Positive" if score > 0 else "Negative" if score < 0 else "Neutral"), score


def compare_coverage(entities: list[dict], articles: list[dict]) -> list[dict]:
    """Return only people appearing in two or more outlets, with outlet tones."""
    text_by_url = {article.get("url"): article.get("full_text", "") for article in articles}
    coverage: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for entity in entities:
        coverage[entity.get("name", "")][entity.get("channel", "Unknown")].append(text_by_url.get(entity.get("article_url"), entity.get("article_title", "")))
    rows = []
    for name, outlets in coverage.items():
        if len(outlets) < 2:
            continue
        tones = []
        for channel, snippets in sorted(outlets.items()):
            label, score = score_sentiment(" ".join(snippets))
            tones.append({"channel": channel, "tone": label, "score": score})
        non_neutral = {tone["tone"] for tone in tones if tone["tone"] != "Neutral"}
        rows.append({"entity": name, "coverage": tones, "divergent": len(non_neutral) > 1})
    return sorted(rows, key=lambda item: (-len(item["coverage"]), item["entity"]))[:20]
