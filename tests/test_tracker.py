from datetime import date
from pathlib import Path
import sqlite3
import tempfile
import unittest

from career_discovery.demo import load_demo
from career_discovery.storage import Storage
from career_discovery.tracker import STATUSES, add_working_days, applications_csv, normalise_application


class TrackerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Storage(self.folder.name)
        self.addCleanup(self.store.close)
        self.jobs = load_demo()[1]
        self.store.import_jobs(self.jobs)
        self.key = self.jobs[0].key

    def test_follow_up_is_seven_working_days_after_applying(self):
        self.assertEqual(add_working_days(date(2026, 11, 13), 7), date(2026, 11, 24))
        self.assertEqual(add_working_days(date(2026, 11, 14), 7), date(2026, 11, 24))

    def test_new_application_defaults_follow_up_and_validates(self):
        row = normalise_application({"job_key": self.key, "status": "applied", "applied_on": "2026-11-13"},
                                    None, date(2026, 11, 17))
        self.assertEqual(row["follow_up_on"], "2026-11-24")
        self.assertEqual(set(STATUSES), {"saved", "applied", "interview", "offer", "rejected", "withdrawn"})
        with self.assertRaises(ValueError) as caught:
            normalise_application({"job_key": self.key, "status": "ghosted", "applied_on": "13.11."}, None, date(2026, 11, 17))
        self.assertEqual(set(caught.exception.fields), {"status", "applied_on"})

    def test_status_persists_across_restarts_and_is_replaced_not_duplicated(self):
        self.store.put_application({"job_key": self.key, "status": "saved", "applied_on": None,
                                    "follow_up_on": None, "notes": ""}, "2026-11-17T08:00:00+00:00")
        self.store.put_application({"job_key": self.key, "status": "interview", "applied_on": "2026-11-10",
                                    "follow_up_on": "2026-11-19", "notes": "Phone call booked"},
                                   "2026-11-17T09:00:00+00:00")
        self.store.close()
        again = Storage(self.folder.name)
        self.addCleanup(again.close)
        rows = again.applications()
        self.assertEqual([(r["status"], r["notes"], r["updated_at"]) for r in rows],
                         [("interview", "Phone call booked", "2026-11-17T09:00:00+00:00")])
        self.assertEqual(rows[0]["title"], self.jobs[0].title)
        self.assertTrue(again.delete_application(self.key))
        self.assertEqual(again.applications(), [])

    def test_existing_database_without_the_table_is_migrated(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        with sqlite3.connect(Path(folder.name) / "vacancies.sqlite") as old:
            old.execute("CREATE TABLE job (key TEXT PRIMARY KEY, source TEXT NOT NULL, board TEXT NOT NULL, "
                        "listed_at TEXT, payload TEXT NOT NULL)")
        old.close()
        store = Storage(folder.name)
        self.addCleanup(store.close)
        self.assertEqual(store.applications(), [])
        self.assertEqual(Storage(folder.name).applications(), [])

    def test_csv_is_spreadsheet_safe(self):
        text = applications_csv([{"job_key": "k", "company": "=cmd|' /C calc'!A0", "title": "Analyst, Data",
                                  "status": "applied", "applied_on": "2026-11-10", "follow_up_on": "2026-11-19",
                                  "notes": "line\nbreak", "url": "https://example.com/x", "updated_at": "t"}])
        self.assertTrue(text.startswith("﻿"))
        self.assertIn("'=cmd", text)
        self.assertIn('"Analyst, Data"', text)

    def test_csv_neutralises_formulas_after_separators(self):
        rows = [{"job_key": "k", "company": 'Acme;=HYPERLINK("http://x")', "title": "A, +cmd", "status": "applied",
                 "applied_on": "", "follow_up_on": "", "notes": "x\n@SUM(1)\t=1", "url": "\t=1", "updated_at": "t"}]
        text = applications_csv(rows)
        self.assertIn("Acme;'=HYPERLINK", text)
        self.assertIn(",' +cmd", text)
        self.assertIn("\n'@SUM", text)
        self.assertIn("\t'=1", text)
        for line in text.splitlines():
            for cell in line.replace(";", ",").split(","):
                self.assertFalse(cell.strip('" ').startswith(("=", "@")), cell)


if __name__ == "__main__":
    unittest.main()
