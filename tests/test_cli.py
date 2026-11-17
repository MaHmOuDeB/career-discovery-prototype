import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_documents import docx_fixture


PROJECT = Path(__file__).resolve().parent.parent


class CLITests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        self.state = self.tmp / "state"

    def cli(self, *args, code=0):
        proc = subprocess.run([sys.executable, "-B", "-m", "career_discovery", "--state", str(self.state), *args],
                              cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=10)
        self.assertEqual(proc.returncode, code, proc.stderr + proc.stdout)
        return proc.stdout if code == 0 else proc.stderr

    @unittest.skipIf(os.name == "nt", "POSIX permission bits do not exist on Windows")
    def test_private_files_and_directories_are_owner_only(self):
        from career_discovery.storage import Storage, write_private_json

        target = self.tmp / "private" / "record.json"
        write_private_json(target, {"ok": True})
        self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.parent.stat().st_mode & 0o777, 0o700)
        store = Storage(self.state)
        self.addCleanup(store.close)
        store.connection()
        self.assertEqual(self.state.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.state / "vacancies.sqlite").stat().st_mode & 0o777, 0o600)

    def test_write_private_json_replaces_an_existing_file_and_leaves_no_temporary(self):
        from career_discovery.storage import write_private_json

        target = self.tmp / "out" / "record.json"
        write_private_json(target, {"n": 1})
        write_private_json(target, {"n": 2})
        self.assertEqual(json.loads(target.read_bytes()), {"n": 2})
        self.assertEqual([item.name for item in target.parent.iterdir()], ["record.json"])

    def test_full_local_profile_vacancy_and_feedback_flow(self):
        cv = self.tmp / "fictional.docx"
        cv.write_bytes(docx_fixture(["Projects", "Built dashboards for a classroom project.",
                                     "Used SQL to join tables and automated workflows."]))
        self.cli("profile", "import", "alexa", str(cv))
        self.assertIn("confirm", self.cli("search", "--profile", "alexa", code=2))
        draft = self.state / "profiles" / "alexa.json"
        profile = json.loads(draft.read_bytes())
        profile.update({"locations": ["Berlin"], "remote_regions": ["DE"], "languages": {"en": "C1"},
                        "employment": ["full_time"], "search_titles": ["Data Analyst"], "keywords": ["sql"]})
        draft.write_text(json.dumps(profile), encoding="utf-8")
        self.cli("profile", "confirm", "alexa")
        self.cli("profile", "import", "alexa", str(cv))
        record = json.loads(self.cli("profile", "show", "alexa"))
        self.assertTrue(record["confirmed"])
        self.assertEqual(record["locations"], ["Berlin"])

        file = self.tmp / "jobs.csv"
        url = "https://career.example/listing/234"
        with file.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["company", "title", "url", "locations", "employment", "description"])
            writer.writerow(["Imaginary Tools", "Workflow Associate", url, "Berlin, Germany", "full_time",
                             "WHAT YOU’LL DO\n- Build dashboards.\n- Automate workflows.\n"
                             "WHAT WE’RE LOOKING FOR\n- English C1."])
        self.cli("import-jobs", str(file), "--keep-description")
        output = json.loads(self.cli("search", "--profile", "alexa", "--mode", "both", "--json"))
        self.assertEqual(len(output["jobs"]["task"]["actionable"]), 0)
        self.assertEqual(len(output["jobs"]["task"]["verify first"]), 1)
        self.assertEqual(output["verification"]["public_gets"], 0)

        self.cli("check-job", url, "open")
        output = json.loads(self.cli("search", "--profile", "alexa", "--mode", "both", "--json"))
        result, = output["jobs"]["task"]["actionable"]
        self.assertEqual(result["fit"], "strong fit")
        self.assertEqual(result["apply_url"], url)
        self.assertTrue(any(item["evidence"]["locator"].startswith("DOCX paragraph")
                            for item in result["evidence_links"]))
        self.assertFalse(output["jobs"]["baseline"]["actionable"])
        packet = self.tmp / "packet"
        self.cli("pilot-pack", "--profile", "alexa", "--participant", "p01",
                 "--output-dir", str(packet), "--full-corpus")
        review = json.loads((packet / "review-deck.json").read_bytes())
        key = packet / "scoring-key.json"
        self.assertEqual(review["vacancies"][0]["link"], url)
        metrics = json.loads(self.cli("evaluate", str(key)))
        self.assertFalse(metrics["participants"][0]["complete_corpus_relevance_labels"])
        self.assertIsNone(metrics["methods"]["task"]["precision"]["rate"])
        self.cli("feedback", "--profile", "alexa", "--job", url, "--relevance", "yes",
                 "--would-consider", "yes", "--new-to-me", "yes")
        export = self.tmp / "export.json"
        self.cli("profile", "export", "alexa", str(export))
        exported = json.loads(export.read_bytes())
        self.assertEqual(exported["feedback"][0]["would_consider"], "yes")
        if os.name != "nt":
            self.assertEqual(export.stat().st_mode & 0o777, 0o600)
        self.cli("profile", "delete", "alexa", "--yes")
        self.assertFalse(draft.exists())

        from career_discovery.storage import Storage

        store = Storage(self.state)
        self.addCleanup(store.close)
        self.assertEqual(store.feedback_for("alexa"), [])
        self.assertEqual(store.connection().execute("SELECT count(*) FROM run WHERE profile='alexa'").fetchone()[0], 0)
        self.assertTrue(cv.exists())

    def test_demo_does_not_create_state(self):
        value = json.loads(self.cli("demo", "--json"))
        self.assertEqual(len(value["profiles"]), 4)
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
