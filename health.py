
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime

from config import ARTICLES_PER_FEED, PIPELINE_HEALTH_PATH, RSS_FEEDS


def _load(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def update_health(articles: list[dict], path: str = PIPELINE_HEALTH_PATH) -> dict:
    history = _load(path)
    counts = Counter(article.get("channel") for article in articles)
    run = {"timestamp": datetime.now().isoformat(timespec="seconds"), "feeds": {name: counts.get(name, 0) for name in RSS_FEEDS}}
    history = (history + [run])[-30:]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)
    cards = []
    for feed in RSS_FEEDS:
        fetched = counts.get(feed, 0)
        successful_runs = sum(item.get("feeds", {}).get(feed, 0) > 0 for item in history)
        uptime = round((successful_runs / len(history)) * 100, 1) if history else 0.0
        cards.append({"feed": feed, "fetched": fetched, "expected": ARTICLES_PER_FEED, "success_rate": round(min(fetched / ARTICLES_PER_FEED, 1) * 100, 1), "uptime": uptime, "healthy": fetched > 0})
    return {"status": "Operational" if all(card["healthy"] for card in cards) else "Degraded", "cards": cards}
