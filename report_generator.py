import os
from collections import defaultdict, Counter
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
from digest import generate_brief
from alerts import detect_alerts
from bias import compare_coverage
from health import update_health
from pdf_export import generate_executive_pdf
from config import PDF_EXPORT_PATH

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

    specific_entities = [e for e in entities if e["category"] not in ["Location", "General News"]]

    for entity in specific_entities:
        channel = entity["channel"]
        time_slot = get_time_slot(entity["exact_datetime"])
        category = entity["category"]
        channel_slot_counts[channel][time_slot].append(category)
        channel_overall_counts[channel].append(category)

    time_slots = ["Morning", "Afternoon", "Evening", "Night"]
    analytics_result = {}

    all_channels = sorted(list({e["channel"] for e in entities})) if entities else ["Times of India", "The Hindu", "NDTV", "India Today", "Indian Express"]

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

def generate_report(entities, articles=None, output_path="output/index.html"):
    """Renders Jinja2 template and writes output to output/index.html AND index.html root."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    analytics = compute_channel_analytics(entities)
    
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('report_template.html')
    
    articles = articles or []
    
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
    rendered_html = template.render(
        entities=entities,
        analytics=analytics,
        intelligence={"brief": brief, "alerts": alerts, "coverage": coverage, "health": health,
                      "pdf_available": pdf_available, "pdf_filename": "executive_daily_brief.pdf"},
        generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
   
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rendered_html)

   
    root_index = "index.html"
    with open(root_index, 'w', encoding='utf-8') as f:
        f.write(rendered_html)
        
    print(f"[REPORT SUCCESS] HTML Report saved at both '{output_path}' and '{root_index}'.")
    return output_path
