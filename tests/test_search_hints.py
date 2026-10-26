import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'splunk/constellation/bin'))
from search_hints import preview_repair_hint

class SearchHintTests(unittest.TestCase):
    def test_timeout_feedback_is_specific_without_rewriting_or_weakening_validation(self):
        query='search index=fixture | bin response_ms bins=30 | stats count BY response_ms'
        hint=preview_repair_hint(query,'spl','preview_timeout')
        self.assertIn('span=WIDTH',hint)
        self.assertIn('recorded units',hint)
        self.assertIn('Never truncate events or widen',hint)
        self.assertIn('bins=30',query)
    def test_other_failures_languages_and_quoted_command_text_keep_ordinary_feedback(self):
        for query,language,code in [
            ('search index=fixture | bin response_ms bins=30','spl2','preview_timeout'),
            ('search index=fixture | bin response_ms bins=30','spl','preview_failed'),
            ('search index=fixture | bin response_ms span=10','spl','preview_timeout'),
            ('search index=fixture | eval note="| bin response_ms bins=30"','spl','preview_timeout')]:
            with self.subTest(query=query,language=language,code=code):self.assertEqual(preview_repair_hint(query,language,code),'')
