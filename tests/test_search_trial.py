from types import SimpleNamespace as Obj
import unittest

from career_discovery.webapi import duty_excerpt, trial_yield


class SearchTrialTests(unittest.TestCase):
    def test_search_quotes_only_duties_and_accepts_shared_task(self):
        lines = [Obj(kind="mandatory", text="Resolve customer issues", tasks=["troubleshoot"]),
                 Obj(kind="core", text="Fehler im Betrieb untersuchen", tasks=["troubleshoot"])]
        self.assertEqual(duty_excerpt(lines, ["resolve", "issues"], {"troubleshoot"}), lines[1].text)
        self.assertEqual(duty_excerpt(lines, ["betrieb"], set()), lines[1].text)
        self.assertIsNone(duty_excerpt(lines[:1], ["issues"], {"troubleshoot"}))

    def test_incremental_yield_excludes_duplicates_and_counts_plausible(self):
        def row(board, title):
            return Obj(job=Obj(source="ashby", board=board, company="Example", title=title,
                               url="https://example.org/" + title, locations=["Berlin"], availability="listed", description="duties"),
                       families=["support"], fit="strong fit", findings=[], requirements=[], lane="actionable")
        rows = [row("base", "Analyst"), row("extra", "Analyst"), row("extra", "Support"), row("extra", "Support")]
        from unittest.mock import patch
        with patch("career_discovery.webapi.supply_review_reasons", return_value=[]):
            self.assertEqual(trial_yield(rows, {("ashby","extra")}, {("ashby","base")}), {"unique":1,"plausible":1})
