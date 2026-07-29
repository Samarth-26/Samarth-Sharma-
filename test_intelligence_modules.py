
import os
import tempfile
import unittest

from alerts import detect_alerts
from bias import compare_coverage
from digest import generate_brief
from health import update_health
from pdf_export import generate_executive_pdf


ARTICLES = [
    {"channel": "The Hindu", "url": "a", "full_text": "A major success and strong progress for Ada Lovelace."},
    {"channel": "NDTV", "url": "b", "full_text": "Critics warn of crisis and risk around Ada Lovelace."},
]
ENTITIES = [
    {"name": "Ada Lovelace", "category": "Author", "channel": "The Hindu", "article_url": "a", "article_title": "Success"},
    {"name": "Ada Lovelace", "category": "Author", "channel": "NDTV", "article_url": "b", "article_title": "Concern"},
]


class ExecutiveIntelligenceTests(unittest.TestCase):
    def test_modules_with_dummy_data(self):
        with tempfile.TemporaryDirectory() as directory:
            history = os.path.join(directory, "history.json")
            self.assertTrue(detect_alerts(ENTITIES, history))
            coverage = compare_coverage(ENTITIES, ARTICLES)
            self.assertTrue(coverage and coverage[0]["divergent"])
            brief = generate_brief(ENTITIES, ARTICLES)
            self.assertTrue(brief["text"])
            health = update_health(ARTICLES, os.path.join(directory, "health.json"))
            self.assertEqual(len(health["cards"]), 5)
            pdf = generate_executive_pdf(ENTITIES, brief, [], health, os.path.join(directory, "brief.pdf"))
            self.assertTrue(pdf and os.path.getsize(pdf) > 0)


if __name__ == "__main__":
    unittest.main()
