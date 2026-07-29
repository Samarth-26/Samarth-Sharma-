from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict
 
from dateutil import parser as date_parser
 
from classifier import ClassifiedEntity
 
 
# Time-of-day bucket boundaries (24-hour clock, hour is inclusive-start)
TIME_BUCKETS = [
    ("Morning", 5, 12),     # 05:00 - 11:59
    ("Afternoon", 12, 17),  # 12:00 - 16:59
    ("Evening", 17, 21),    # 17:00 - 20:59
    ("Night", 21, 5),       # 21:00 - 04:59 (wraps past midnight)
]
 
 
@dataclass
class TrendRow:
    """One aggregated row: how many times a category appeared for a
    given source at a given time-of-day bucket."""
    source: str
    time_bucket: str
    category: str
    count: int
 
 
@dataclass
class SourceSummary:
    """The single dominant category per time bucket for one source —
    this is the 'management view' row, e.g.
    Source=CNN, Morning=Politician, Evening=Sportsman."""
    source: str
    dominant_by_bucket: Dict[str, str]  # {"Morning": "Politician", ...}
 
 
def _get_time_bucket(article_date_str: str) -> str:
    """Map an article's publish date string to a time-of-day bucket.
    Returns 'Unknown' if the date can't be parsed (e.g. 'Unknown')."""
    if not article_date_str or article_date_str == "Unknown":
        return "Unknown"
 
    try:
        dt = date_parser.parse(article_date_str)
    except (ValueError, TypeError):
        return "Unknown"
 
    hour = dt.hour
    for label, start, end in TIME_BUCKETS:
        if start < end:
            if start <= hour < end:
                return label
        else:
            # wraps past midnight (Night: 21:00 - 04:59)
            if hour >= start or hour < end:
                return label
 
    return "Unknown"
 
 
def build_trend_table(classified_entities: List[ClassifiedEntity]) -> List[TrendRow]:
    """
    Aggregate classified entities into counts of
    (source, time_bucket, category) -> count.
    """
    counts = defaultdict(int)
 
    for entity in classified_entities:
        bucket = _get_time_bucket(entity.article_date)
        key = (entity.source, bucket, entity.category)
        counts[key] += 1
 
    rows = [
        TrendRow(source=src, time_bucket=bucket, category=cat, count=cnt)
        for (src, bucket, cat), cnt in counts.items()
    ]
 
    # Sort for readability: by source, then time bucket, then descending count
    bucket_order = {"Morning": 0, "Afternoon": 1, "Evening": 2, "Night": 3, "Unknown": 4}
    rows.sort(key=lambda r: (r.source, bucket_order.get(r.time_bucket, 5), -r.count))
    return rows
 
 
def build_source_summary(trend_rows: List[TrendRow]) -> List[SourceSummary]:
    """
    Collapse the trend table into one row per source, showing only the
    DOMINANT (most frequent) category for each time bucket. This is the
    'at a glance' management table:
 
        Source      | Morning     | Afternoon  | Evening    | Night
        BBC         | Politician  | Businessman| Sportsman  | Other
    """
    # source -> bucket -> {category: count}
    grouped: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
 
    for row in trend_rows:
        bucket_map = grouped[row.source][row.time_bucket]
        bucket_map[row.category] = row.count
 
    summaries = []
    for source, bucket_dict in grouped.items():
        dominant = {}
        for bucket, cat_counts in bucket_dict.items():
            dominant[bucket] = max(cat_counts, key=cat_counts.get)
        summaries.append(SourceSummary(source=source, dominant_by_bucket=dominant))
 
    summaries.sort(key=lambda s: s.source)
    return summaries
 
 
def analyze(classified_entities: List[ClassifiedEntity]):
    """Convenience wrapper: run both aggregation steps at once."""
    trend_rows = build_trend_table(classified_entities)
    source_summaries = build_source_summary(trend_rows)
    return trend_rows, source_summaries
 
 
if __name__ == "__main__":
    # Quick manual test with dummy data
    dummy = [
        ClassifiedEntity("Narendra Modi", "Politician", "bbc.com", "2026-07-27 07:30:00", 0.95),
        ClassifiedEntity("Rahul Gandhi", "Politician", "bbc.com", "2026-07-27 08:15:00", 0.90),
        ClassifiedEntity("Lionel Messi", "Sportsman", "bbc.com", "2026-07-27 19:00:00", 0.98),
        ClassifiedEntity("FIFA", "Sport", "bbc.com", "2026-07-27 19:05:00", 0.88),
        ClassifiedEntity("Elon Musk", "Businessman", "cnn.com", "2026-07-27 13:00:00", 0.93),
    ]
    rows, summaries = analyze(dummy)
    print("--- Trend rows ---")
    for r in rows:
        print(r)
    print("\n--- Source summaries ---")
    for s in summaries:
        print(s)