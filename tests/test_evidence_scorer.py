import unittest
from unittest.mock import patch

from career_discovery.analysis import load_catalogue
from career_discovery.diagnostics import evidence_report


class EvidenceScorerTests(unittest.TestCase):
    def test_counts_each_line_separately_including_negatives(self):
        rows = [{'id': 'one', 'text': 'First example.', 'tasks': ['triage', 'sql']},
                {'id': 'two', 'text': 'Second example.', 'tasks': []}]
        predictions = {'one': ['triage'], 'two': ['sql']}
        catalogue = load_catalogue()
        with patch('career_discovery.diagnostics.evidence_tags', return_value=predictions) as tagger:
            result = evidence_report(rows, catalogue)
        profile, used_catalogue = tagger.call_args.args
        self.assertIs(used_catalogue, catalogue)
        self.assertEqual([item.text for item in profile.usable_evidence], [row['text'] for row in rows])
        self.assertEqual(result['lines'], 2)
        self.assertEqual(result['tasks'], {'precision': 0.5, 'recall': 0.5, 'f1': 0.5,
                                           'true_positive': 1, 'predicted': 2, 'expected': 2})
