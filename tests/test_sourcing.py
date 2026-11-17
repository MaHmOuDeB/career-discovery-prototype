from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from career_discovery.analysis import load_catalogue
from career_discovery.demo import load_demo
from career_discovery.models import MANUAL_VERIFICATION_PREFIX, SUPERSEDED_AUTO_VERIFICATIONS, Job
from career_discovery.network import NetworkUnavailable, PublicHTTP, Response
from career_discovery.sources import Board, load_boards, load_csv, parse_board, verify_job
from career_discovery.sourcing import capture_supply, recheck_shortlist, refresh_boards
from career_discovery.storage import Storage


GH = Board("greenhouse", "fictional", "Fictional Lab")
ASHBY = Board("ashby", "fictional", "Fictional Works")
GH_LINK = "https://job-boards.greenhouse.io/fictional/jobs/42"
ASHBY_LINK = "https://jobs.ashbyhq.com/fictional/e427/"
APPLICATION_HTML = b"<h1>Workflow Specialist</h1><button>Apply for this job</button>"
CENTRAL_TIME = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)


def greenhouse_payload():
    return {"jobs": [{
        "id": 42, "title": "Workflow Specialist", "absolute_url": GH_LINK,
        "content": "&lt;h2&gt;Responsibilities&lt;/h2&gt;&lt;li&gt;Build dashboards.&lt;/li&gt;"
                   "<script>Closing signal: no longer accepting applications</script>",
        "location": {"name": "Berlin, Germany"}, "updated_at": "2026-11-04T22:04:00Z",
        "metadata": [{"name": "Employment Type", "value": "Full-time"}],
    }]}


def ashby_payload():
    public = {
        "title": "Customer Onboarding Associate", "location": "Germany",
        "secondaryLocations": [{"location": "Vienna", "address": {"addressCountry": "Austria"}}],
        "jobUrl": ASHBY_LINK, "applyUrl": ASHBY_LINK + "application",
        "publishedAt": "2026-11-10T10:11:00.000+00:00",
        "descriptionPlain": "Responsibilities:\nTroubleshoot failed imports and onboard small teams.",
        "workplaceType": "Remote", "employmentType": "FullTime", "isListed": True,
    }
    return {"jobs": [public, {**public, "jobUrl": ASHBY_LINK + "-private", "isListed": False}]}


class Stub:
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def get(self, url, **_):
        self.calls += 1
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


class SimulatedHTTP(PublicHTTP):
    def __init__(self, responses):
        super().__init__()
        self.responses = responses
        self.visited = []

    def _once(self, url, max_bytes):
        self.visited.append(url)
        return self.responses[url]


class AdapterTests(unittest.TestCase):
    def test_greenhouse_normalisation_and_visible_text(self):
        job, = parse_board(json.dumps(greenhouse_payload()), GH)
        self.assertEqual(job.external_id, "42")
        self.assertEqual(job.description, "Responsibilities\nBuild dashboards.")
        self.assertEqual(job.listed_date, "2026-11-04")
        self.assertEqual(job.date_kind, "updated")
        self.assertEqual(job.employment, "full_time")
        self.assertEqual(job.availability, "listed")

    def test_ashby_keeps_apply_url_and_remote_geography(self):
        job, = parse_board(json.dumps(ashby_payload()), ASHBY)
        self.assertEqual(job.apply_url, ASHBY_LINK + "application")
        self.assertEqual(job.locations, ("Germany", "Vienna, Austria"))
        self.assertEqual(job.remote_regions, ("de", "at"))
        self.assertEqual(job.date_kind, "last_published")

    def test_ashby_missing_visibility_is_not_a_complete_snapshot(self):
        payload = ashby_payload()
        del payload["jobs"][0]["isListed"]
        with self.assertRaisesRegex(ValueError, "flag"):
            parse_board(json.dumps(payload), ASHBY)

    def test_dotted_board_and_internship_classification_for_existing_data(self):
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "boards.json"
            config.write_text(json.dumps([{"ats": "ashby", "slug": "company.example", "company": "Test",
                                           "local_use_reviewed": True}]))
            board, = load_boards(config)
            self.assertTrue(board.url.endswith("/company.example"))
        payload = ashby_payload()
        payload["jobs"][0]["title"] = "Revenue Operations Intern"
        job, = parse_board(json.dumps(payload), ASHBY)
        self.assertEqual(job.employment, "internship")
        legacy = json.loads(json.dumps(asdict(job)))
        legacy["employment"] = "full_time"
        self.assertEqual(Job.load(legacy).employment, "internship")
        legacy["title"] = "Internship Program Manager"
        self.assertEqual(Job.load(legacy).employment, "full_time")

    def test_import_needs_description_rights_and_parses_wrapped_text(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "source.csv"
            file.write_text('company,title,url,description\nFiction,Associate,https://employer.example/job,'
                            '"Responsibilities:\nTroubleshoot errors."\n')
            private_job, = load_csv(file, keep_description=False)
            job, = load_csv(file, keep_description=True)
            self.assertFalse(private_job.description)
            self.assertIn("\n", job.description)
            self.assertEqual(job.availability, "unverified")

    def test_rechecks_require_both_specific_apply_path_and_fresh_feed(self):
        job, = parse_board(json.dumps(greenhouse_payload()), GH)

        def check(status, body=b"", url=GH_LINK, listed=CENTRAL_TIME):
            stub = Stub(Response(status, url, body))
            return verify_job(job, stub, CENTRAL_TIME, listed).availability

        self.assertEqual(check(200, APPLICATION_HTML), "verified")
        self.assertEqual(check(200, APPLICATION_HTML, listed=None), "unverified")
        self.assertEqual(check(200, APPLICATION_HTML, listed=CENTRAL_TIME - timedelta(days=2)), "unverified")
        self.assertEqual(check(200, b"<h1>Employer home</h1>"), "unverified")
        self.assertEqual(check(200, b"<h1>Employer home</h1><p>Workflow Specialist. Apply now.</p>"), "unverified")
        self.assertEqual(check(200, b"<h1>Workflow Specialist</h1>"), "unverified")
        for soft_failure in (
            b"<p>Apply now</p>", b"<button disabled>Apply now</button>",
            b'<button aria-disabled="true">Apply now</button>',
            b'<div hidden><button>Apply now</button></div>',
            b'<div style="display: none"><button>Apply now</button></div>',
            b"<script><button>Apply now</button></script>",
        ):
            self.assertEqual(check(200, b"<h1>Workflow Specialist</h1>" + soft_failure), "unverified")
        self.assertEqual(check(200, b"<template><h1>Workflow Specialist</h1></template>"
                               b"<button>Apply now</button>"), "unverified")
        self.assertEqual(check(200, b"<h1>Workflow Specialist</h1><p>Applications are closed.</p>"
                               b"<button disabled>Apply now</button>"), "closed")
        self.assertEqual(check(200, APPLICATION_HTML + b"<p>Applications are now closed.</p>"), "closed")
        self.assertEqual(check(200, url="https://job-boards.greenhouse.io/fictional"), "unverified")
        self.assertEqual(check(200, b"Verify you are human"), "unverified")
        self.assertEqual(check(200, b"This job is no longer available"), "closed")
        self.assertEqual(check(200, b"This vacancy has now expired"), "closed")
        self.assertEqual(check(404), "closed")
        self.assertEqual(check(403), "unverified")

    def test_european_greenhouse_application_host_is_supported(self):
        job, = parse_board(json.dumps(greenhouse_payload()), GH)
        path = "https://job-boards.eu.greenhouse.io/fictional/jobs/42"
        regional = replace(job, url=path, apply_url=path)
        client = Stub(Response(200, path, APPLICATION_HTML))
        self.assertEqual(verify_job(regional, client, CENTRAL_TIME, CENTRAL_TIME).availability, "verified")

    def test_non_ats_import_is_never_auto_fetched(self):
        job, = parse_board(json.dumps(greenhouse_payload()), GH)
        client = Stub(AssertionError("unexpected fetch"))
        manual = replace(job, source="csv")
        self.assertEqual(verify_job(manual, client, CENTRAL_TIME).availability, "unverified")
        self.assertEqual(client.calls, 0)

    def test_robots_applies_to_job_and_redirect_destination(self):
        a = "https://boards-api.greenhouse.io/robots.txt"
        b = GH.url
        public = SimulatedHTTP({
            a: Response(200, a, b"User-agent: *\nDisallow: /v1/"),
        })
        with self.assertRaisesRegex(NetworkUnavailable, "Robots"):
            public.get(b)
        self.assertEqual(public.visited, [a])
        public = SimulatedHTTP({
            a: Response(200, a, b"User-agent: *\nDisallow: /embed/"),
            b: Response(302, b, b"", "https://internal.example/job"),
        })
        with self.assertRaisesRegex(NetworkUnavailable, "outside"):
            public.get(b)
        self.assertEqual(public.visited, [a, b])

    def test_ashby_robots_401_only_permits_documented_public_api(self):
        a = "https://api.ashbyhq.com/robots.txt"
        b = ASHBY.url
        client = SimulatedHTTP({a: Response(401, a, b""), b: Response(200, b, b"{}")})
        self.assertEqual(client.get(b).status, 200)
        with self.assertRaisesRegex(NetworkUnavailable, "Robots"):
            client.get("https://api.ashbyhq.com/candidates")


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.store = Storage(self.folder.name)
        self.addCleanup(self.store.close)
        self.job, = parse_board(json.dumps(greenhouse_payload()), GH)
        self.now = CENTRAL_TIME

    def test_failure_does_not_close_and_complete_snapshot_closes_missing_job(self):
        self.store.record_board(GH, self.now, [self.job])
        later = self.now + timedelta(days=1)
        self.store.record_board(GH, later, note="HTTP 403")
        self.assertEqual(self.store.job(self.job.key).availability, "listed")
        self.store.record_board(GH, later + timedelta(seconds=1), [])
        self.assertEqual(self.store.job(self.job.key).availability, "closed")

    def test_out_of_order_snapshot_does_not_overwrite_newer_state(self):
        self.store.record_board(GH, self.now, [self.job])
        self.assertFalse(self.store.record_board(GH, self.now - timedelta(hours=1), []))
        self.assertEqual(self.store.job(self.job.key).availability, "listed")

    def test_status_write_rejects_concurrent_vacancy_changes(self):
        self.store.record_board(GH, self.now, [self.job])
        self.store.record_board(GH, self.now + timedelta(hours=1), [replace(self.job, description="Changed")])
        opened = replace(self.job, availability="verified", checked_at=self.now.isoformat())
        self.assertFalse(self.store.update_status(self.job, opened))

    def test_unsupported_links_do_not_erase_manual_checks_or_consume_cap(self):
        custom = replace(self.job, external_id="new", url="https://employer.example/jobs/new",
                         apply_url="https://employer.example/jobs/new")
        self.store.record_board(GH, self.now, [custom, self.job])
        manual = replace(custom, availability="verified", checked_at=self.now.isoformat(),
                         verification_reason=f"{MANUAL_VERIFICATION_PREFIX}open.")
        self.assertTrue(self.store.update_status(custom, manual))
        client = Stub(Response(200, GH_LINK, APPLICATION_HTML))
        rows = [SimpleNamespace(job=manual), SimpleNamespace(job=self.job)]
        report = recheck_shortlist(self.store, rows, client=client, max_checks=1, clock=lambda: self.now)
        self.assertEqual([row["job_key"] for row in report["vacancies"]], [self.job.key])
        self.assertEqual(self.store.job(custom.key), manual)
        self.assertEqual(self.store.job(self.job.key).availability, "verified")
        self.assertEqual(verify_job(manual, client, self.now, self.now), manual)
        self.assertEqual(client.calls, 1)

    def test_manual_closure_survives_refresh_and_feed_reappearance(self):
        self.store.record_board(GH, self.now, [self.job])
        closed = replace(self.job, availability="closed", checked_at=self.now.isoformat(),
                         verification_reason=f"{MANUAL_VERIFICATION_PREFIX}closed.")
        self.assertTrue(self.store.update_status(self.job, closed))
        for hours, jobs in ((1, [self.job]), (2, []), (25, [self.job])):
            self.store.record_board(GH, self.now + timedelta(hours=hours), jobs)
            self.assertEqual(self.store.job(self.job.key), closed)

    def test_legacy_url_only_check_is_downgraded_when_loading(self):
        for reason in SUPERSEDED_AUTO_VERIFICATIONS:
            older = replace(self.job, availability="verified", checked_at=self.now.isoformat(),
                            verification_reason=reason)
            self.assertEqual(Job.load(json.loads(json.dumps(asdict(older)))).availability, "unverified")

    def test_supply_requires_elapsed_time_and_comparable_boards_and_profiles(self):
        profile = load_demo()[0][0]
        catalogue = load_catalogue()
        self.store.record_board(GH, self.now, [self.job])
        capture_supply(self.store, profile, catalogue, clock=lambda: self.now)
        self.assertFalse(capture_supply(self.store, profile, catalogue, clock=lambda: self.now)["comparison_ready"])
        later = self.now + timedelta(days=7)
        self.store.record_board(GH, later, [self.job])
        self.assertTrue(capture_supply(self.store, profile, catalogue, clock=lambda: later)["comparison_ready"])
        outsider = replace(profile, locations=["Hamburg"])
        self.assertFalse(capture_supply(self.store, outsider, catalogue, clock=lambda: later)["comparison_ready"])
        self.store.record_board(ASHBY, later, [])
        self.assertFalse(capture_supply(self.store, profile, catalogue, clock=lambda: later)["comparison_ready"])

    def test_refresh_cache_and_failed_board_reporting(self):
        good = Stub(Response(200, GH.url, json.dumps(greenhouse_payload()).encode()))
        report = refresh_boards(self.store, [GH], client=good, clock=lambda: self.now)
        self.assertEqual(report["boards"][0]["count"], 1)
        self.assertEqual(good.calls, 1)
        bad = Stub(Response(403, GH.url, b""))
        report = refresh_boards(self.store, [GH], client=bad, clock=lambda: self.now)
        self.assertEqual(report["boards"][0]["status"], "cached")
        self.assertEqual(bad.calls, 0)
        report = refresh_boards(self.store, [GH], client=bad, clock=lambda: self.now + timedelta(days=1))
        self.assertEqual(report["boards"][0]["status"], "unavailable")
        self.assertEqual(self.store.job(self.job.key).availability, "listed")


if __name__ == "__main__":
    unittest.main()
