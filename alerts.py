
from __future__ import annotations

import json
import math
import os
from collections import Counter
from datetime import datetime

from config import ALERT_Z_SCORE_THRESHOLD, HISTORY_MAX_RUNS, HISTORY_PATH


def _load_history(path: str = HISTORY_PATH) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_history(history: list[dict], path: str = HISTORY_PATH) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(history[-HISTORY_MAX_RUNS:], handle, indent=2)


def detect_alerts(entities: list[dict], history_path: str = HISTORY_PATH) -> list[dict]:
    
    history = _load_history(history_path)
    current = Counter(e.get("name", "").strip() for e in entities if e.get("name"))
    alerts: list[dict] = []
    for name, count in current.items():
        baseline = [run.get("counts", {}).get(name, 0) for run in history]
        seen_before = any(value > 0 for value in baseline)
        if not seen_before and count >= 2:
            alerts.append({"entity": name, "count": count, "kind": "New & trending", "z_score": None})
            continue
        if len(baseline) >= 2:
            mean = sum(baseline) / len(baseline)
            variance = sum((value - mean) ** 2 for value in baseline) / len(baseline)
            deviation = math.sqrt(variance)
            z_score = (count - mean) / deviation if deviation else (float("inf") if count > mean else 0)
            if z_score >= ALERT_Z_SCORE_THRESHOLD:
                alerts.append({"entity": name, "count": count, "kind": "Spiking", "z_score": round(z_score, 1)})
    _save_history(history + [{"timestamp": datetime.now().isoformat(timespec="seconds"), "counts": dict(current)}], history_path)
    return sorted(alerts, key=lambda item: item["count"], reverse=True)[:10]
