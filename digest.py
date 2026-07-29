
from __future__ import annotations

from collections import Counter

from config import GROQ_API_KEY, EXECUTIVE_BRIEF_MODEL


def _fallback(entities: list[dict], articles: list[dict]) -> str:
    if not entities:
        return "No entity data is available for this run. The next successful ingestion will populate this brief."
    people = ", ".join(name for name, _ in Counter(e.get("name", "") for e in entities).most_common(3))
    categories = ", ".join(category for category, _ in Counter(e.get("category", "") for e in entities).most_common(2))
    outlets = ", ".join(f"{outlet} ({count})" for outlet, count in Counter(a.get("channel", "") for a in articles).most_common(3))
    return f"Coverage focused on {people}. The leading entity categories were {categories}. Channel activity was highest at {outlets}."


def generate_brief(entities: list[dict], articles: list[dict]) -> dict:
    fallback = _fallback(entities, articles)
    if not GROQ_API_KEY:
        return {"text": fallback, "source": "Rule-based fallback"}
    try:
        from groq import Groq
        prompt = f"Write a concise executive news brief in 65 words or fewer. Entities: {Counter(e.get('name', '') for e in entities).most_common(5)}. Categories: {Counter(e.get('category', '') for e in entities).most_common(4)}. Channels: {Counter(a.get('channel', '') for a in articles).most_common(5)}."
        response = Groq(api_key=GROQ_API_KEY).chat.completions.create(model=EXECUTIVE_BRIEF_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=120)
        text = response.choices[0].message.content.strip()
        return {"text": text or fallback, "source": "Groq" if text else "Rule-based fallback"}
    except Exception:
        return {"text": fallback, "source": "Rule-based fallback"}
