from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from career_discovery.analysis import load_catalogue
from career_discovery.demo import load_demo
from career_discovery.diagnostics import coverage_report, heldout_report

PROJECT = Path(__file__).resolve().parent.parent
NOW = datetime(2026, 11, 16, tzinfo=timezone.utc)
AD = """Responsibilities
- Resolve escalated customer support cases and write the root-cause analysis
- Prepare monthly KPI dashboards for the management team
Requirements
- Fluent German at C2 is a hard requirement
- Experience with SQL
Benefits
- Free coffee
"""


class DiagnosticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()
        profiles, cls.jobs, _ = load_demo()
        cls.profile = profiles[0]

    def labelled(self, **changes):
        item = {"id": "h01", "language": "en", "company": "Example GmbH", "title": "Support Analyst",
                "locations": ["Berlin"], "employment": "full_time", "description": AD,
                "duties": [{"text": "Resolve escalated customer support cases", "tasks": ["troubleshoot"]},
                          {"text": "Prepare monthly KPI dashboards", "tasks": ["report_kpis"]}],
                "qualifications": [{"text": "Experience with SQL", "kind": "mandatory"},
                                   {"text": "Fluent German at C2", "kind": "mandatory"}],
                "language_requirements": [{"language": "de", "level": "C2", "mandatory": True}]}
        item.update(changes)
        return item

    def write(self, items):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "heldout.json"
        path.write_text(json.dumps(items))
        return path

    def test_coverage_on_demo_jobs_is_aggregate_only(self):
        report = coverage_report(self.jobs, self.profile, self.catalogue, NOW)
        self.assertEqual(report["jobs"], len(self.jobs))
        self.assertGreater(report["duty_lines"], 0)
        self.assertLessEqual(report["mapped_duty_lines"], report["duty_lines"])
        self.assertEqual(report["mapped_rate"], round(report["mapped_duty_lines"] / report["duty_lines"], 3))
        self.assertEqual(sum(report["fit_counts"].values()), report["jobs"])
        self.assertEqual(sum(report["lane_counts"].values()), report["jobs"])
        self.assertLessEqual(report["plausible"], report["jobs"])
        text = json.dumps(report)
        for job in self.jobs:
            self.assertNotIn(job.title, text)
            self.assertNotIn(job.description[:40], text)

    def test_coverage_title_filter_and_closed_jobs(self):
        every = coverage_report(self.jobs, self.profile, self.catalogue, NOW)
        none = coverage_report(self.jobs, self.profile, self.catalogue, NOW, title_pattern="^zzz-no-title$")
        self.assertEqual(none["jobs"], 0)
        self.assertEqual(none["mapped_rate"], 0.0)
        title = self.jobs[0].title
        some = coverage_report(self.jobs, self.profile, self.catalogue, NOW, title_pattern=f"^{title}$")
        self.assertTrue(0 < some["jobs"] < every["jobs"] or some["jobs"] == every["jobs"])
        from dataclasses import replace
        closed = [replace(job, availability="closed") for job in self.jobs]
        self.assertEqual(coverage_report(closed, self.profile, self.catalogue, NOW)["jobs"], 0)

    def test_coverage_uses_supplied_analyser(self):
        report = coverage_report(self.jobs, self.profile, self.catalogue, NOW, analyser=lambda job: ())
        self.assertEqual(report["zero_duty_jobs"], report["jobs"])
        self.assertEqual(report["duty_lines"], 0)

    def test_heldout_metrics_on_a_tiny_labelled_file(self):
        report = heldout_report(self.write([self.labelled()]), self.profile, self.catalogue, NOW)
        self.assertEqual(report["vacancies"], 1)
        self.assertEqual(report["duties_total"], 2)
        self.assertEqual(report["qualifications_total"], 2)
        self.assertEqual(report["language_conflicts_expected"], 1)
        self.assertEqual(report["language_conflicts_detected"], 1)
        overall = report["tasks"]["overall"]
        for key in ("precision", "recall", "f1"):
            self.assertTrue(0.0 <= overall[key] <= 1.0)
        self.assertGreaterEqual(report["duties_detected"], 1)
        self.assertEqual(set(report["tasks"]["per_task"]), {"troubleshoot", "report_kpis"})

    def test_heldout_misses_and_leaks(self):
        item = self.labelled(duties=[{"text": "Cook the weekly team lunch", "tasks": ["teach"]}])
        report = heldout_report(self.write([item]), self.profile, self.catalogue, NOW)
        self.assertEqual(report["duties_detected"], 0)
        self.assertEqual(report["tasks"]["overall"]["recall"], 0.0)
        miss = next(row for row in report["misses"] if row["text"] == "Cook the weekly team lunch")
        self.assertEqual((miss["id"], miss["expected"]["tasks"], miss["got"]["tasks"]), ("h01", ["teach"], []))

    def test_heldout_qualification_leak_counts(self):
        item = self.labelled(qualifications=[{"text": "Resolve escalated customer support cases",
                                              "kind": "mandatory"}])
        report = heldout_report(self.write([item]), self.profile, self.catalogue, NOW)
        self.assertEqual(report["qualification_leaks"], 1)

    def test_cli_heldout_and_coverage_are_read_only(self):
        path = self.write([self.labelled()])
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        state = Path(temp.name) / "state"

        def run(*args):
            proc = subprocess.run([sys.executable, "-B", "-m", "career_discovery", "--state", str(state), *args],
                                  cwd=PROJECT, capture_output=True, text=True, timeout=20)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)

        self.assertEqual(run("heldout", str(path), "--at", "2026-11-16T00:00:00+00:00")["vacancies"], 1)
        self.assertEqual(run("coverage", "--at", "2026-11-16T00:00:00+00:00")["jobs"], 0)
        self.assertFalse((state / "vacancies.sqlite").exists())


if __name__ == "__main__":
    unittest.main()
