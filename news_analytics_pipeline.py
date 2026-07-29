import os
import re
import sys
from collections import defaultdict, Counter
from datetime import datetime
from dateutil import parser as date_parser
import spacy
from transformers import pipeline
import feedparser
from newspaper import Article
from jinja2 import Environment, FileSystemLoader
from digest import generate_brief
from alerts import detect_alerts
from bias import compare_coverage
from health import update_health
from pdf_export import generate_executive_pdf
from config import PDF_EXPORT_PATH

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RSS_FEEDS = {
    "Times of India": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "The Hindu": "https://www.thehindu.com/feeder/default.rss",
    "NDTV": "https://feeds.feedburner.com/ndtvnews-top-stories",
    "India Today": "https://www.indiatoday.in/rss/home",
    "Indian Express": "https://indianexpress.com/feed/"
}

ARTICLES_PER_FEED = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

SPACY_MODEL = "en_core_web_sm"
ZERO_SHOT_MODEL = "facebook/bart-large-mnli"

PRIMARY_CATEGORIES = [
    "Sportsperson",
    "Politician",
    "Author",
    "Actor / Entertainer",
    "Businessman",
    "Government Official"
]

SPORTS_LIST = ["Cricket", "Football", "Tennis", "Badminton", "Basketball", "Hockey", "Chess", "Athletics", "Motorsport", "Golf"]

POLITICAL_PARTIES = [
    ("BJP", r"\b(BJP|Bharatiya Janata Party)\b"),
    ("Congress", r"\b(Congress|INC|Indian National Congress)\b"),
    ("AAP", r"\b(AAP|Aam Aadmi Party)\b"),
    ("TMC", r"\b(TMC|Trinamool|Trinamool Congress)\b"),
    ("DMK", r"\b(DMK|Dravida Munnetra Kazhagam)\b"),
    ("SP", r"\b(Samajwadi Party|SP)\b"),
    ("BSP", r"\b(Bahujan Samaj Party|BSP)\b"),
    ("Democratic Party", r"\b(Democrats?|Democratic Party)\b"),
    ("Republican Party", r"\b(Republicans?|GOP|Republican Party)\b"),
]

print("[INIT] Loading spaCy NLP model...")
nlp = spacy.load(SPACY_MODEL)

print("[INIT] Loading Hugging Face Zero-Shot Classifier (facebook/bart-large-mnli)...")
zero_shot_classifier = pipeline("zero-shot-classification", model=ZERO_SHOT_MODEL)

CLASSIFICATION_CACHE = {}

def classify_entity_cached(entity_name, candidate_labels):
    key = (entity_name.lower().strip(), tuple(candidate_labels))
    if key in CLASSIFICATION_CACHE:
        return CLASSIFICATION_CACHE[key]
    result = zero_shot_classifier(entity_name, candidate_labels=candidate_labels)
    top_label = result['labels'][0]
    CLASSIFICATION_CACHE[key] = top_label
    return top_label

def parse_exact_datetime(raw_date_str, article_date):
    if article_date:
        return article_date.strftime("%Y-%m-%d %H:%M:%S")
    if raw_date_str and raw_date_str != "Unknown":
        try:
            parsed_dt = date_parser.parse(raw_date_str)
            return parsed_dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            pass
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fetch_and_scrape_articles():
    scraped_articles = []

    for channel_name, feed_url in RSS_FEEDS.items():
        print(f"\n[INGEST] Fetching RSS feed: {channel_name}...")
        feed = feedparser.parse(feed_url, agent=USER_AGENT)
        entries = feed.entries[:ARTICLES_PER_FEED]

        for entry in entries:
            link = getattr(entry, "link", None)
            if not link:
                continue

            try:
                article = Article(link, browser_user_agent=USER_AGENT)
                article.download()
                article.parse()

                full_text = article.text if len(article.text) > 100 else entry.get("summary", "")
                title = article.title or getattr(entry, "title", "Untitled")
                exact_datetime = parse_exact_datetime(getattr(entry, "published", None), article.publish_date)
                scraped_articles.append({
                    "channel": channel_name,
                    "title": title,
                    "url": link,
                    "exact_datetime": exact_datetime,
                    "full_text": full_text
                })
                print(f"  [OK] Downloaded: {title[:50]}...")
            except Exception as e:
                title = getattr(entry, "title", "Untitled")
                scraped_articles.append({
                    "channel": channel_name,
                    "title": title,
                    "url": link,
                    "exact_datetime": parse_exact_datetime(getattr(entry, "published", None), None),
                    "full_text": f"{title}. {entry.get('summary', '')}"
                })
                print(f"  [WARN] Scrape fallback for {channel_name} link ({e}). Using RSS summary.")

    return scraped_articles

def extract_political_party(text):
    for party_name, pattern in POLITICAL_PARTIES:
        if re.search(pattern, text, re.IGNORECASE):
            return party_name
    return "Government & Politics"

def extract_published_book(doc, text):
    for ent in doc.ents:
        if ent.label_ in ["WORK_OF_ART", "LAW"]:
            return f"'{ent.text.strip()}'"
    match = re.search(r'author of ["\']([^"\']+)["\']|book titled ["\']([^"\']+)["\']', text, re.IGNORECASE)
    if match:
        title = match.group(1) or match.group(2)
        return f"'{title}'"
    return "Recent Publication / Article"

def extract_sub_detail(entity_name, category, text, doc):
    if category == "Sportsperson":
        res = zero_shot_classifier(text[:1000], candidate_labels=SPORTS_LIST)
        top_sport = res['labels'][0]
        return f"Sportsperson ({top_sport})"

    elif category == "Politician":
        party = extract_political_party(text)
        return f"Politician ({party})"

    elif category == "Author":
        book = extract_published_book(doc, text)
        return f"Author (Book: {book})"

    elif category == "Actor / Entertainer":
        return "Actor / Cinema & Media"

    elif category == "Businessman":
        return "Businessman / Industry Leader"

    elif category == "Government Official":
        return "Government Official / Institution"

    return category

def process_entities_from_articles(articles):
    processed_entities = []

    for article in articles:
        text = article["full_text"]
        if not text:
            continue

        doc = nlp(text[:3000])
        seen_entities = set()

        for ent in doc.ents:
            clean_name = ent.text.strip()
            
            if ent.label_ == "PERSON" and len(clean_name.split()) >= 2:
                key = clean_name.lower()
                if key in seen_entities:
                    continue
                seen_entities.add(key)

                primary_cat = classify_entity_cached(clean_name, PRIMARY_CATEGORIES)
                formatted_detail = extract_sub_detail(clean_name, primary_cat, text, doc)

                processed_entities.append({
                    "name": clean_name,
                    "category": primary_cat,
                    "specific_detail": formatted_detail,
                    "channel": article["channel"],
                    "exact_datetime": article["exact_datetime"],
                    "article_title": article["title"],
                    "article_url": article["url"]
                })

    return processed_entities

def get_time_slot(datetime_str):
    try:
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        hour = dt.hour
    except Exception:
        hour = 12

    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 21:
        return "Evening"
    else:
        return "Night"

def compute_channel_analytics(entities):
    channel_slot_counts = defaultdict(lambda: defaultdict(list))
    channel_overall_counts = defaultdict(list)

    for entity in entities:
        channel = entity["channel"]
        time_slot = get_time_slot(entity["exact_datetime"])
        category = entity["category"]
        channel_slot_counts[channel][time_slot].append(category)
        channel_overall_counts[channel].append(category)

    time_slots = ["Morning", "Afternoon", "Evening", "Night"]
    analytics_result = {}

    all_channels = sorted(list(RSS_FEEDS.keys()))
    for channel in all_channels:
        analytics_result[channel] = {}

        if channel_overall_counts[channel]:
            overall_top_cat, _ = Counter(channel_overall_counts[channel]).most_common(1)[0]
        else:
            overall_top_cat = "Politician"

        for slot in time_slots:
            categories_in_slot = channel_slot_counts[channel][slot]
            if categories_in_slot:
                counter = Counter(categories_in_slot)
                most_common_cat, count = counter.most_common(1)[0]
                summary_text = f"Mostly {most_common_cat}s ({count} mentions)"
            else:
                most_common_cat = overall_top_cat
                summary_text = f"Dominant: {overall_top_cat}"

            analytics_result[channel][slot] = {
                "dominant_category": most_common_cat,
                "summary": summary_text,
                "count": len(categories_in_slot)
            }

    return analytics_result

def build_intelligence_context(entities, articles):
    try: brief = generate_brief(entities, articles)
    except Exception: brief = {"text": "Executive brief is temporarily unavailable.", "source": "Unavailable"}
    try: alerts = detect_alerts(entities)
    except Exception: alerts = []
    try: coverage = compare_coverage(entities, articles)
    except Exception: coverage = []
    try: health = update_health(articles)
    except Exception: health = {"status": "Unavailable", "cards": []}
    try: pdf_path = generate_executive_pdf(entities, brief, alerts, health, PDF_EXPORT_PATH)
    except Exception: pdf_path = None
    return {"brief": brief, "alerts": alerts, "coverage": coverage, "health": health,
            "pdf_available": bool(pdf_path), "pdf_filename": "executive_daily_brief.pdf"}

def generate_html_report(entities, analytics, intelligence=None, output_path="output/index.html"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report_template.html")

    rendered_html = template.render(
        entities=entities,
        analytics=analytics,
        intelligence=intelligence or {},
        generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    root_index = "index.html"
    with open(root_index, "w", encoding="utf-8") as f:
        f.write(rendered_html)

    print(f"\n[REPORT SUCCESS] HTML Report saved at both '{output_path}' and '{root_index}'.")
    return output_path

def run_pipeline():
    print("=" * 70)
    print(" STEP 1: FETCHING & SCRAPING NEWS ARTICLES")
    print("=" * 70)
    articles = fetch_and_scrape_articles()
    
    print("\n" + "=" * 70)
    print(" STEP 2: EXTRACTING SPECIFIC ENTITIES")
    print("=" * 70)
    entities = process_entities_from_articles(articles)
    print(f"[INFO] Processed {len(entities)} specific proper noun entities.")

    print("\n" + "=" * 70)
    print(" STEP 3: COMPUTING CHANNEL TIME-SLOT ANALYTICS")
    print("=" * 70)
    analytics = compute_channel_analytics(entities)

    print("\n" + "=" * 70)
    print(" STEP 4: RENDERING JINJA2 DASHBOARD")
    print("=" * 70)
    intelligence = build_intelligence_context(entities, articles)
    generate_html_report(entities, analytics, intelligence, output_path="output/index.html")

if __name__ == "__main__":
    run_pipeline()
