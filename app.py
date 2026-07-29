

from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context
from flask_cors import CORS

from config import FLASK_PORT, RSS_FEEDS
from pipeline.chatbot import chat as chatbot_chat
from pipeline.csv_store import load_articles_from_csv
from pipeline.fetcher import (
    get_pipeline_state,
    run_scrape_cycle,
    start_background_fetcher,
    update_pipeline_state,
)
from pipeline.nlp_engine import process_all_articles
from pipeline import trend_tracker
from alerts import detect_alerts
from bias import compare_coverage
from digest import generate_brief
from health import update_health
from pdf_export import generate_executive_pdf
from config import PDF_EXPORT_PATH

# ── Flask app ──────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── Shared in-memory store (protected by _data_lock) ──────────────────────
_data_lock         = threading.Lock()
_processed_entities: list = []
_processed_articles: list = []
_executive_intelligence: dict = {
    "brief": {"text": "Waiting for the first pipeline run.", "source": "Unavailable"},
    "alerts": [], "coverage": [], "health": {"status": "Unavailable", "cards": []},
    "pdf_available": False,
}


# ── NLP runner ─────────────────────────────────────────────────────────────

def _run_nlp() -> None:
    """Load the CSV and run the NLP pipeline; update the shared store."""
    global _processed_entities, _processed_articles, _executive_intelligence

    update_pipeline_state(
        phase="nlp_processing",
        progress_message="Loading articles from CSV for NLP processing…",
    )
    articles = load_articles_from_csv()
    update_pipeline_state(
        progress_message=f"Running NLP on {len(articles)} articles…"
    )
    entities = process_all_articles(articles)

    # Optional Python intelligence steps never block the original dashboard.
    try: brief = generate_brief(entities, articles)
    except Exception: brief = {"text": "Executive brief is temporarily unavailable.", "source": "Unavailable"}
    try: alerts = detect_alerts(entities)
    except Exception: alerts = []
    try: coverage = compare_coverage(entities, articles)
    except Exception: coverage = []
    try: health = update_health(articles)
    except Exception: health = {"status": "Unavailable", "cards": []}
    try: pdf_available = bool(generate_executive_pdf(entities, brief, alerts, health, PDF_EXPORT_PATH))
    except Exception: pdf_available = False

    with _data_lock:
        _processed_entities = entities
        _processed_articles = articles
        _executive_intelligence = {"brief": brief, "alerts": alerts, "coverage": coverage,
                                  "health": health, "pdf_available": pdf_available}
    update_pipeline_state(
        phase="ready",
        progress_message=f"Done — {len(entities)} people found in {len(articles)} articles.",
        entity_count=len(entities),
        last_run=datetime.now().strftime("%H:%M:%S"),
    )
    # Record snapshot for trending timeline
    trend_tracker.record_snapshot(entities)
    print(f"[APP] Pipeline done — {len(entities)} entities / {len(articles)} articles.")


def _full_pipeline() -> None:
    """Scrape → NLP in sequence; called once at startup."""
    try:
        run_scrape_cycle()
        _run_nlp()
    except Exception as exc:
        print(f"[PIPELINE ERROR] {exc}")
        update_pipeline_state(
            phase="ready",
            error=str(exc),
            progress_message="Pipeline encountered an error. See logs.",
        )


# ── Routes ─────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    return jsonify(get_pipeline_state())


@app.route("/api/trigger", methods=["POST"])
def api_trigger():
    """Start a fresh scrape + NLP cycle in the background."""
    def _run():
        try:
            run_scrape_cycle()
            _run_nlp()
        except Exception as exc:
            update_pipeline_state(phase="ready", error=str(exc))

    threading.Thread(target=_run, daemon=True, name="manual-trigger").start()
    return jsonify({"status": "triggered"})


@app.route("/api/version")
def api_version():
    """Returns the last data update timestamp — used by frontend to detect fresh data."""
    state = get_pipeline_state()
    with _data_lock:
        entity_count = len(_processed_entities)
        article_count = len(_processed_articles)
    return jsonify({
        "last_updated": state.get("last_run", ""),
        "entity_count": entity_count,
        "article_count": article_count,
    })


@app.route("/api/sentiment")
def api_sentiment():
    """Returns sentiment breakdown across all entities."""
    with _data_lock:
        entities = list(_processed_entities)
    if not entities:
        return jsonify({"positive": 0, "negative": 0, "neutral": 0, "breakdown": []})

    pos = sum(1 for e in entities if e.get("sentiment_label") == "Positive")
    neg = sum(1 for e in entities if e.get("sentiment_label") == "Negative")
    neu = sum(1 for e in entities if e.get("sentiment_label") == "Neutral")
    total = len(entities) or 1

    # Top positive and negative people
    pos_people = sorted(
        [e for e in entities if e.get("sentiment_label") == "Positive"],
        key=lambda x: x.get("sentiment_score", 0), reverse=True
    )[:5]
    neg_people = sorted(
        [e for e in entities if e.get("sentiment_label") == "Negative"],
        key=lambda x: x.get("sentiment_score", 0)
    )[:5]

    return jsonify({
        "positive":      pos,
        "negative":      neg,
        "neutral":       neu,
        "positive_pct":  round(pos / total * 100, 1),
        "negative_pct":  round(neg / total * 100, 1),
        "neutral_pct":   round(neu / total * 100, 1),
        "top_positive":  [{"name": e["name"], "score": e.get("sentiment_score", 0),
                           "article": e["article_title"][:60]} for e in pos_people],
        "top_negative":  [{"name": e["name"], "score": e.get("sentiment_score", 0),
                           "article": e["article_title"][:60]} for e in neg_people],
    })


@app.route("/api/trending")
def api_trending():
    """Returns trending entity data for the timeline chart."""
    data = trend_tracker.get_trending(top_n=8)
    return jsonify(data)


@app.route("/api/network")
def api_network():
    """
    Returns co-occurrence network data for D3.js graph.
    Nodes = people, Edges = appeared together in same article.
    """
    with _data_lock:
        entities = list(_processed_entities)

    if not entities:
        return jsonify({"nodes": [], "links": []})

    # Group entities by article URL
    from collections import defaultdict as _dd
    article_people: dict = _dd(list)
    for e in entities:
        url = e.get("article_url", "")
        if url:
            article_people[url].append(e)

    # Build co-occurrence counts
    pair_counts: Counter = Counter()
    pair_meta: dict = {}
    for url, people in article_people.items():
        if len(people) < 2:
            continue
        names = list({p["name"] for p in people})   # unique names per article
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = sorted([names[i], names[j]])
                key  = (a, b)
                pair_counts[key] += 1
                pair_meta[key] = {
                    "article": people[0]["article_title"][:60],
                    "channel": people[0]["channel"],
                }

    # Build node list (people who co-occur with at least 1 other)
    mentioned_in_pairs = set()
    for (a, b) in pair_counts:
        mentioned_in_pairs.add(a)
        mentioned_in_pairs.add(b)

    # Map names to entity info
    name_info = {}
    for e in entities:
        if e["name"] not in name_info:
            name_info[e["name"]] = e

    nodes = [
        {
            "id":       name,
            "category": name_info[name]["category"],
            "sentiment":name_info[name].get("sentiment_label", "Neutral"),
            "count":    sum(1 for e in entities if e["name"] == name),
        }
        for name in mentioned_in_pairs
        if name in name_info
    ]

    # Top 80 pairs by co-occurrence
    top_pairs = pair_counts.most_common(80)
    links = [
        {
            "source":  a,
            "target":  b,
            "value":   count,
            "article": pair_meta.get((a, b), {}).get("article", ""),
            "channel": pair_meta.get((a, b), {}).get("channel", ""),
        }
        for (a, b), count in top_pairs
        if a in mentioned_in_pairs and b in mentioned_in_pairs
    ]

    return jsonify({"nodes": nodes, "links": links})


@app.route("/api/kpis")
def api_kpis():
    with _data_lock:
        entities = list(_processed_entities)
        articles = list(_processed_articles)

    cat_counts  = Counter(e["category"]        for e in entities)
    role_counts = Counter(e["specific_detail"] for e in entities)

    return jsonify({
        "total_articles":   len(articles),
        "total_entities":   len(entities),
        "category_breakdown": dict(cat_counts.most_common()),
        "role_breakdown":     dict(role_counts.most_common(15)),
        "channels":           list(RSS_FEEDS.keys()),
        "last_updated":       get_pipeline_state().get("last_run", "Never"),
    })


@app.route("/api/data")
def api_data():
    with _data_lock:
        entities = list(_processed_entities)
    return jsonify({"entities": entities, "total": len(entities)})


@app.route("/api/executive")
def api_executive():
    """Serves the additive Python-generated executive dashboard data."""
    with _data_lock:
        return jsonify(_executive_intelligence)


@app.route("/executive_daily_brief.pdf")
def executive_pdf_download():
    if not os.path.isfile(PDF_EXPORT_PATH):
        return jsonify({"error": "Executive PDF is not available yet."}), 404
    return send_from_directory("output", "executive_daily_brief.pdf", as_attachment=True)


@app.route("/api/channel_stats")
def api_channel_stats():
    with _data_lock:
        entities = list(_processed_entities)

    result: dict = {}

    # Initialise every channel so the UI always has a card to render
    for ch in RSS_FEEDS:
        result[ch] = {"total": 0, "categories": {}, "top_entities": []}

    channel_data: dict = defaultdict(
        lambda: {"total": 0, "categories": defaultdict(int), "names": []}
    )
    for e in entities:
        ch = e["channel"]
        channel_data[ch]["total"]                       += 1
        channel_data[ch]["categories"][e["specific_detail"]] += 1
        channel_data[ch]["names"].append(e["name"])

    for ch, data in channel_data.items():
        result[ch] = {
            "total":       data["total"],
            "categories":  dict(
                sorted(data["categories"].items(), key=lambda x: -x[1])
            ),
            "top_entities": list(dict.fromkeys(data["names"]))[:10],
        }

    return jsonify(result)


@app.route("/api/compare", methods=["POST"])
def api_compare():
    """
    Body: {"names": ["Modi", "Yogi"]}
    Returns articles where ALL queried names appear (substring match on entity
    names within that article), plus the entities found in those articles.
    """
    body        = request.get_json(force=True, silent=True) or {}
    raw_names   = body.get("names", [])
    query_names = [n.strip().lower() for n in raw_names if n.strip()]

    if len(query_names) < 2:
        return jsonify({"error": "Provide at least 2 names to compare."}), 400

    with _data_lock:
        entities = list(_processed_entities)

    # Build a map: article_url → {set of lowercased entity names, article meta}
    article_map: dict = defaultdict(lambda: {"names": set(), "meta": {}})
    for e in entities:
        url = e["article_url"]
        article_map[url]["names"].add(e["name"].lower())
        article_map[url]["meta"] = {
            "title":    e["article_title"],
            "channel":  e["channel"],
            "datetime": e["exact_datetime"],
            "url":      url,
        }

    # Find articles where EVERY query name is a substring of at least one entity
    matching: list = []
    for url, data in article_map.items():
        names_in_article = data["names"]
        if all(
            any(qn in entity_name for entity_name in names_in_article)
            for qn in query_names
        ):
            meta = dict(data["meta"])
            # Attach entities that appear in this article
            meta["entities"] = [
                e["name"] for e in entities if e["article_url"] == url
            ]
            matching.append(meta)

    return jsonify({
        "query":   query_names,
        "results": matching,
        "count":   len(matching),
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    body    = request.get_json(force=True, silent=True) or {}
    message = body.get("message", "").strip()

    if not message:
        return jsonify({"error": "Empty message."}), 400

    with _data_lock:
        entities = list(_processed_entities)
        articles = list(_processed_articles)

    response = chatbot_chat(message, entities, articles)
    return jsonify({"response": response})


@app.route("/stream/progress")
def stream_progress():
    """
    Server-Sent Events endpoint.  Polls the pipeline state every second
    and pushes JSON updates to the browser until phase == 'ready'.
    """
    def generate():
        for _ in range(600):          # cap at 10 minutes
            state   = get_pipeline_state()
            payload = json.dumps({
                "phase":         state.get("phase", "idle"),
                "message":       state.get("progress_message", ""),
                "article_count": state.get("article_count", 0),
                "entity_count":  state.get("entity_count", 0),
                "error":         state.get("error"),
            })
            yield f"data: {payload}\n\n"

            if state.get("phase") == "ready":
                break
            time.sleep(1)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Combined auto-refresh background loop ─────────────────────────────────

def _background_refresh_loop() -> None:
    """
    Runs forever in a daemon thread.
    Every FETCH_INTERVAL_SECONDS: scrape new articles → run NLP → update store.
    This ensures the dashboard always has fresh data automatically.
    """
    import time as _time
    from config import FETCH_INTERVAL_SECONDS
    print(f"[AUTO-REFRESH] Background refresh loop started (every {FETCH_INTERVAL_SECONDS}s).")
    while True:
        _time.sleep(FETCH_INTERVAL_SECONDS)
        print("[AUTO-REFRESH] Starting scheduled scrape + NLP cycle...")
        try:
            run_scrape_cycle()
            _run_nlp()
            print("[AUTO-REFRESH] Cycle complete. Dashboard data updated.")
        except Exception as exc:
            print(f"[AUTO-REFRESH ERROR] {exc}")


# ── Application factory ────────────────────────────────────────────────────

def create_app() -> Flask:
    """
    1. Runs initial scrape + NLP immediately in a daemon thread.
    2. Starts a combined auto-refresh loop (scrape + NLP) every 5 minutes.
    """
    # Initial pipeline on startup
    threading.Thread(
        target=_full_pipeline, daemon=True, name="initial-pipeline"
    ).start()

    # Combined background auto-refresh (starts after 60s delay so it
    # doesn't collide with the initial pipeline run)
    def _delayed_start():
        import time as _time
        _time.sleep(60)
        _background_refresh_loop()   # runs forever

    threading.Thread(
        target=_delayed_start, daemon=True, name="auto-refresh-loop"
    ).start()

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(
        host="0.0.0.0",
        port=FLASK_PORT,
        debug=False,
        threaded=True,
        use_reloader=False,
    )
