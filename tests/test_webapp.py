from datetime import datetime, timezone
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest

from career_discovery.analysis import load_catalogue
from career_discovery.demo import load_demo
from career_discovery.matching import as_record, run_match, split_ranked
from career_discovery.models import Job
from career_discovery.network import Response
from career_discovery.webapi import AppService
from career_discovery.webapp import make_server

from test_documents import docx_fixture
from test_sourcing import GH_LINK, greenhouse_payload

FIXED = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
CV_LINES = ["Experience",
            "Built dashboards and reported KPIs on ticket backlogs during an internship.",
            "Used SQL to join tables and automated workflows to refresh a weekly spreadsheet.",
            "Skills", "Excel, SQL, Power BI"]
DETAILS = {"languages": {"en": "C1", "de": "B1"}, "locations": ["Berlin"], "remote_regions": ["DE"],
           "employment": ["full_time"], "search_titles": ["Data Analyst"], "keywords": ["sql"]}
BOARDS = [{"ats": "greenhouse", "slug": "fictional", "company": "Fictional Lab", "local_use_reviewed": True}]
SALARY_JOB = {
    "source": "fictional", "board": "demo", "external_id": "pay-1", "company": "Pay Co", "title": "Reporting Analyst",
    "url": "https://vacancies.example/pay-1", "availability": "fixture_open", "locations": ["Berlin, Germany"],
    "employment": "full_time", "listed_date": "2026-11-06", "date_kind": "posted", "deadline": "2026-12-01",
    "description": "Responsibilities:\n- Build dashboards for team leads.\n- Report operational metrics each week.\n"
                   "- Automate workflows for routine handoffs.\nRequirements:\n- German B2.\n"
                   "Salary: €55,000 - €65,000 per year",
}


class FakeClient:
    calls = 0

    def __init__(self, status=200, body=None):
        self.status, self.body, self.visited = status, body, []

    def get(self, url, **_):
        self.calls += 1
        self.visited.append(url)
        body = self.body if self.body is not None else json.dumps(greenhouse_payload()).encode()
        return Response(self.status, url, body)


def multipart(name, filename, data, ctype="application/octet-stream"):
    boundary = "----cdtest"
    head = (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n").encode()
    return head + data + f"\r\n--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        boards = Path(self.folder.name) / "boards.json"
        boards.write_text(json.dumps(BOARDS), encoding="utf-8")
        self.client = FakeClient()
        self.service = AppService(Path(self.folder.name) / "state", boards_path=boards,
                                  client_factory=lambda **_: self.client, clock=lambda: FIXED)
        self.server = make_server(self.service, port=0)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def call(self, method, path, body=None, *, token=True, host=None, origin=None, ctype="application/json",
             raw=False, headers=None, cookie=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        self.addCleanup(conn.close)
        sent = {"Host": host or f"127.0.0.1:{self.port}", **(headers or {})}
        if cookie:
            sent["Cookie"] = f"cd_session={cookie if isinstance(cookie, str) else self.server.session}"
        if token:
            sent["X-CD-Token"] = token if isinstance(token, str) else self.server.token
        if origin:
            sent["Origin"] = origin
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            sent["Content-Type"] = ctype
        conn.request(method, path, data, sent, )
        response = conn.getresponse()
        payload = response.read()
        if raw:
            return response.status, response, payload
        try:
            return response.status, response, json.loads(payload)
        except ValueError:
            return response.status, response, payload

    def ok(self, method, path, body=None, **kw):
        status, _, data = self.call(method, path, body, **kw)
        self.assertEqual(status, 200, data)
        return data

    def make_profile(self, confirm=True):
        data, ctype = multipart("file", "cv.docx", docx_fixture(CV_LINES))
        self.ok("POST", "/api/profile/cv", data, ctype=ctype)
        self.ok("PUT", "/api/profile", DETAILS)
        if confirm:
            self.ok("POST", "/api/profile/confirm", {})

    def seed(self, jobs):
        with self.service.open_store() as store:
            store.import_jobs(jobs)


class SecurityTests(AppTestCase):
    def test_good_request_passes_and_index_carries_the_token(self):
        self.assertEqual(self.ok("GET", "/api/state")["profile"]["exists"], False)
        status, response, page = self.call("GET", "/", token=False, raw=True)
        self.assertEqual(status, 200)
        self.assertIn(f'<meta name="cd-token" content="{self.server.token}">'.encode(), page)
        self.assertIn("default-src 'self'", response.getheader("Content-Security-Policy"))
        self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.getheader("Referrer-Policy"), "no-referrer")

    def test_api_needs_the_launch_token(self):
        for token in (False, "wrong"):
            status, _, body = self.call("GET", "/api/state", token=token)
            self.assertEqual(status, 401)
            self.assertEqual(body["error"]["code"], "unauthorized")
        status, response, _ = self.call("GET", "/api/state")
        self.assertEqual(response.getheader("Cache-Control"), "no-store")

    def test_page_without_the_session_cookie_has_no_token(self):
        status, _, page = self.call("GET", "/", token=False, cookie=False, raw=True)
        self.assertEqual(status, 200)
        self.assertNotIn(self.server.token.encode(), page)
        self.assertNotIn(b"cd-token", page)
        self.assertIn(b"Open Career Discovery from its starter window", page)
        self.assertIn("Career Discovery".encode(), page)
        self.assertIn("Starterfenster".encode(), page)

    def test_launch_secret_sets_the_cookie_once(self):
        secret = self.server.launch_secret
        status, response, _ = self.call("GET", f"/?launch={secret}", token=False, cookie=False, raw=True)
        self.assertEqual(status, 303)
        self.assertEqual(response.getheader("Location"), "/")
        cookie = response.getheader("Set-Cookie")
        self.assertIn(f"cd_session={self.server.session}", cookie)
        for part in ("HttpOnly", "SameSite=Strict", "Path=/"):
            self.assertIn(part, cookie)
        status, _, page = self.call("GET", f"/?launch={secret}", token=False, cookie=False, raw=True)
        self.assertEqual(status, 200)
        self.assertNotIn(self.server.token.encode(), page)
        status, _, page = self.call("GET", "/?launch=wrong", token=False, cookie=False, raw=True)
        self.assertNotIn(self.server.token.encode(), page)

    def test_api_needs_the_session_cookie_even_with_the_token(self):
        for cookie in (False, "wrong"):
            status, _, body = self.call("GET", "/api/state", cookie=cookie)
            self.assertEqual(status, 401)
            self.assertEqual(body["error"]["code"], "unauthorized")
        status, _, _ = self.call("GET", "/api/export", cookie=False)
        self.assertEqual(status, 401)

    def test_idle_connections_are_dropped(self):
        import socket
        from career_discovery.webapp import Handler

        Handler.timeout = 0.3
        self.addCleanup(setattr, Handler, "timeout", 30)
        for head in (b"GET /api/sta", None):
            with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
                if head is None:
                    head = (f"POST /api/profile/new HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\n"
                            f"Cookie: cd_session={self.server.session}\r\nX-CD-Token: {self.server.token}\r\n"
                            "Content-Type: application/json\r\nContent-Length: 50\r\n\r\n").encode()
                sock.sendall(head)
                chunks = []
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    chunks.append(chunk)
            self.assertNotIn(b" 500 ", b"".join(chunks))

    def test_default_timeout_is_set(self):
        from career_discovery.webapp import Handler

        self.assertEqual(Handler.timeout, 30)

    def test_wrong_host_is_rejected_for_pages_and_api(self):
        for path in ("/", "/api/state"):
            status, _, body = self.call("GET", path, host="evil.example:80")
            self.assertEqual(status, 403, path)
        self.assertEqual(self.call("GET", "/api/state", host=f"localhost:{self.port}")[0], 200)
        self.assertEqual(self.call("GET", "/api/state", host=f"127.0.0.1:{self.port + 1}")[0], 403)

    def test_foreign_origin_is_rejected(self):
        self.assertEqual(self.call("GET", "/api/state", origin="https://evil.example")[0], 403)
        self.assertEqual(self.call("GET", "/api/state", origin="null")[0], 403)
        self.assertEqual(self.call("GET", "/api/state", origin=f"http://localhost:{self.port}")[0], 200)

    def test_oversize_and_unknown_content_types_are_rejected(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        self.addCleanup(conn.close)
        conn.putrequest("POST", "/api/profile/new")
        for name, value in (("X-CD-Token", self.server.token), ("Cookie", f"cd_session={self.server.session}"),
                            ("Content-Type", "application/json"),
                            ("Content-Length", str(10 * 1024 * 1024 + 1))):
            conn.putheader(name, value)
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 413)
        self.assertEqual(json.loads(response.read())["error"]["code"], "too_large")
        status, _, body = self.call("POST", "/api/profile/new", b"<x/>", ctype="text/xml")
        self.assertEqual(status, 415)

    def test_errors_are_plain_json_without_tracebacks(self):
        status, _, body = self.call("GET", "/api/nothing")
        self.assertEqual((status, body["error"]["code"]), (404, "not_found"))
        status, _, body = self.call("POST", "/api/profile/new", b"{broken")
        self.assertEqual((status, body["error"]["code"]), (400, "bad_json"))
        status, _, body = self.call("GET", "/api/matches")
        self.assertEqual(status, 409)
        self.assertNotIn("Traceback", json.dumps(body))
        self.assertEqual(self.call("GET", "/../etc/passwd", token=False)[0], 404)


class ProfileTests(AppTestCase):
    def test_cv_upload_lists_evidence_with_source_lines_and_removal_excludes_it(self):
        data, ctype = multipart("file", "cv.docx", docx_fixture(CV_LINES))
        profile = self.ok("POST", "/api/profile/cv", data, ctype=ctype)["profile"]
        items = profile["evidence"]
        self.assertEqual([i["state"] for i in items], ["cv_stated", "cv_stated", "inferred"])
        self.assertTrue(all(i["locator"].startswith("DOCX paragraph") for i in items))
        self.assertFalse(profile["confirmed"])
        self.ok("POST", "/api/profile/evidence", {"action": "remove", "id": items[2]["id"]})
        edited = self.ok("POST", "/api/profile/evidence",
                         {"action": "edit", "id": items[0]["id"], "text": "Built KPI dashboards."})["profile"]
        self.assertEqual(edited["evidence"][0]["state"], "user_confirmed")
        self.assertEqual(len(edited["evidence"]), 2)
        self.ok("PUT", "/api/profile", DETAILS)
        confirmed = self.ok("POST", "/api/profile/confirm", {})["profile"]
        self.assertTrue(confirmed["confirmed"])
        self.assertEqual(self.ok("GET", "/api/state")["profile"]["evidence_usable"], 2)

    def test_bad_upload_gives_a_plain_message(self):
        data, ctype = multipart("file", "cv.docx", b"not a zip")
        status, _, body = self.call("POST", "/api/profile/cv", data, ctype=ctype)
        self.assertEqual((status, body["error"]["code"]), (422, "invalid"))
        data, ctype = multipart("file", "cv.txt", b"x")
        self.assertEqual(self.call("POST", "/api/profile/cv", data, ctype=ctype)[0], 422)

    def test_details_are_validated_per_field_and_nothing_is_saved_until_valid(self):
        self.ok("POST", "/api/profile/new", {})
        status, _, body = self.call("PUT", "/api/profile", {"languages": {"de": "D9"}, "employment": ["pirate"]})
        self.assertEqual(status, 422)
        self.assertEqual(set(body["error"]["fields"]), {"languages", "employment"})
        status, _, body = self.call("PUT", "/api/profile", {"languages": {}})
        self.assertIn("languages", body["error"]["fields"])
        status, _, body = self.call("PUT", "/api/profile", {"confirmed": True})
        self.assertEqual(status, 422)
        self.assertEqual(self.ok("GET", "/api/profile")["profile"]["languages"], {})
        self.assertEqual(self.ok("PUT", "/api/profile", DETAILS)["profile"]["languages"], DETAILS["languages"])

    def test_confirm_needs_evidence_and_new_profile_does_not_overwrite(self):
        self.ok("POST", "/api/profile/new", {})
        self.assertEqual(self.call("POST", "/api/profile/confirm", {})[0], 422)
        self.assertEqual(self.call("POST", "/api/profile/new", {})[0], 409)
        added = self.ok("POST", "/api/profile/evidence", {"action": "add", "text": "Wrote weekly KPI reports."})
        self.assertEqual(added["profile"]["evidence"][0]["state"], "user_confirmed")
        self.assertTrue(self.ok("POST", "/api/profile/confirm", {})["profile"]["confirmed"])


class MatchTests(AppTestCase):
    def test_matches_equal_run_match_for_the_same_state_and_clock(self):
        profiles, jobs, _ = load_demo()
        self.seed(jobs)
        self.make_profile()
        result = self.ok("GET", "/api/matches?mode=both&limit=200&excluded=1")
        with self.service.open_store() as store:
            profile, catalogue = store.profile("me"), load_catalogue()
            rows = run_match(store.jobs(), profile, catalogue, FIXED, analyser=lambda j: store.analyse(j, catalogue))
        shown = 0
        for mode, name in (("baseline", "title"), ("task", "task")):
            for lane, ranked in split_ranked(rows, mode).items():
                expected = [json.loads(json.dumps(as_record(r, profile, baseline=mode == "baseline"))) for r in ranked]
                actual = result["results"][name][lane]
                self.assertEqual([r["job_key"] for r in actual], [e["job_key"] for e in expected], (name, lane))
                for got, want in zip(actual, expected):
                    self.assertEqual({k: got[k] for k in want}, want)
                    self.assertEqual(set(got) - set(want), {"salary", "age_days", "deadline", "language_summary",
                                                           "wording", "application"})
                shown += len(expected)
        self.assertGreater(shown, 3)
        self.assertEqual(self.call("GET", "/api/matches?mode=nonsense")[0], 422)

    def test_filter_by_words_in_title_company_or_place(self):
        _, jobs, _ = load_demo()
        self.seed(jobs)
        self.make_profile()
        everything = self.ok("GET", "/api/matches?mode=both&limit=200&excluded=1")
        titles = [r["title"] for lanes in everything["results"]["task"].values() for r in lanes]
        word = next(w for t in titles for w in t.split() if len(w) > 4)
        found = self.ok("GET", f"/api/matches?mode=both&limit=200&excluded=1&q={word.upper()}")
        self.assertEqual(found["query"], word.upper())
        for name in ("task", "title"):
            records = [r for lanes in found["results"][name].values() for r in lanes]
            self.assertTrue(records or name == "title", name)
            for record in records:
                text = " ".join([record["title"], record["company"], *map(str, record.get("locations") or [])])
                self.assertIn(word.casefold(), text.casefold())
            self.assertEqual(found["shown"][name], {lane: len(rows) for lane, rows in found["results"][name].items()})
        self.assertLess(sum(found["shown"]["task"].values()), len(titles))
        two = self.ok("GET", f"/api/matches?mode=task&excluded=1&q={word}%20zzzz-nothing")
        self.assertEqual(sum(two["shown"]["task"].values()), 0)
        self.assertEqual(everything["counts"], found["counts"])
        self.assertEqual(self.call("GET", "/api/matches?q=" + "x" * 101)[0], 422)

    def test_extra_fields_pay_age_deadline_languages_and_wording(self):
        self.seed([Job.load(SALARY_JOB)])
        self.make_profile()
        result = self.ok("GET", "/api/matches?mode=task&excluded=1")["results"]["task"]
        rows = [r for lane in result.values() for r in lane]
        record = next(r for r in rows if r["company"] == "Pay Co")
        self.assertEqual(record["salary"], "€55,000 - €65,000 per year")
        self.assertEqual(record["age_days"], 10)
        self.assertEqual(record["deadline"], "2026-12-01")
        self.assertEqual(record["language_summary"]["conflict"], True)
        self.assertEqual(record["language_summary"]["languages"]["de"], {"asked": "B2", "yours": "B1", "state": "conflict"})
        self.assertTrue(record["wording"]["supported"])
        first = record["wording"]["supported"][0]
        self.assertEqual(set(first) & {"ad", "cv", "task"}, {"ad", "cv", "task"})
        hidden = self.ok("GET", "/api/matches?mode=task&excluded=1&hide_language_conflicts=1")["results"]["task"]
        self.assertFalse([r for lane in hidden.values() for r in lane if r["company"] == "Pay Co"])

    def test_families_feedback_and_recheck(self):
        self.seed(load_demo()[1])
        self.make_profile()
        self.assertTrue(self.ok("GET", "/api/families")["families"])
        key = load_demo()[1][0].key
        self.ok("POST", "/api/feedback", {"job_key": key, "verdict": "not_for_me", "reason": "Too junior"})
        saved = self.ok("GET", "/api/feedback")["items"]
        self.assertEqual((saved[0]["relevance"], saved[0]["correction"]), ("no", "Too junior"))
        self.assertEqual(self.call("POST", "/api/feedback", {"job_key": "nope", "verdict": "useful"})[0], 422)
        self.assertEqual(self.client.calls, 0)

    def test_recheck_uses_the_bounded_verify_path_only_when_asked(self):
        self.seed(load_demo()[1])
        self.ok("POST", "/api/jobs/refresh", {})
        self.service.join_refresh(5)
        job = next(j for j in self.service_jobs() if j.source == "greenhouse")
        self.client.status, self.client.body = 404, b"gone"
        calls = self.client.calls
        result = self.ok("POST", "/api/matches/recheck", {"job_key": job.key})
        self.assertEqual(result["availability"], "closed")
        self.assertEqual(self.client.calls, calls + 1)
        self.assertEqual(self.call("POST", "/api/matches/recheck", {"job_key": load_demo()[1][0].key})[0], 422)

    def service_jobs(self):
        with self.service.open_store() as store:
            return store.jobs()


class JobsTests(AppTestCase):
    def test_refresh_reports_progress_uses_only_the_reviewed_list_and_keeps_bounds(self):
        self.assertEqual(self.ok("GET", "/api/jobs/refresh")["status"], "idle")
        self.assertEqual(self.ok("POST", "/api/jobs/refresh", {})["status"], "running")
        self.service.join_refresh(5)
        done = self.ok("GET", "/api/jobs/refresh")
        self.assertEqual((done["status"], done["done"], done["total"]), ("done", 1, 1))
        self.assertEqual(done["boards"][0]["status"], "refreshed")
        self.assertEqual(self.client.visited, ["https://boards-api.greenhouse.io/v1/boards/fictional/jobs?content=true"])
        state = self.ok("GET", "/api/state")
        self.assertEqual(state["jobs"]["stored"], 1)
        self.assertTrue(state["jobs"]["last_fetched"])

    def test_board_failure_is_reported_per_board(self):
        self.client.status = 503
        self.ok("POST", "/api/jobs/refresh", {})
        self.service.join_refresh(5)
        done = self.ok("GET", "/api/jobs/refresh")
        self.assertEqual(done["boards"][0]["status"], "unavailable")
        self.assertIn("503", done["boards"][0]["reason"])

    def test_shipped_board_list_is_reviewed_and_packaged(self):
        from career_discovery.sources import load_boards
        boards = load_boards(Path(__file__).resolve().parent.parent / "career_discovery" / "boards.json")
        self.assertEqual(len(boards), 12)

    def test_csv_import_by_multipart_and_json(self):
        text = "company,title,url\nAcme,Analyst,https://acme.example/jobs/1\n"
        data, ctype = multipart("file", "jobs.csv", text.encode(), "text/csv")
        self.assertEqual(self.ok("POST", "/api/jobs/import", data, ctype=ctype)["imported"], 1)
        text2 = "company,title,url\nAcme,Analyst,https://acme.example/jobs/2\n"
        self.assertEqual(self.ok("POST", "/api/jobs/import", {"csv": text2})["imported"], 1)
        self.assertEqual(self.ok("GET", "/api/state")["jobs"]["stored"], 2)
        self.assertEqual(self.call("POST", "/api/jobs/import", {"csv": "a,b\n1,2"})[0], 422)


class TrackerTests(AppTestCase):
    def test_tracker_list_upsert_csv_delete_and_weekly_summary(self):
        jobs = load_demo()[1]
        self.seed(jobs)
        key = jobs[0].key
        saved = self.ok("POST", "/api/applications", {"job_key": key, "status": "applied", "applied_on": "2026-11-03"})
        self.assertEqual(saved["application"]["follow_up_on"], "2026-11-12")
        self.ok("POST", "/api/applications", {"job_key": jobs[1].key, "status": "interview", "applied_on": "2026-11-16"})
        rows = self.ok("GET", "/api/applications")["items"]
        self.assertEqual({r["status"] for r in rows}, {"applied", "interview"})
        self.assertEqual(self.call("POST", "/api/applications", {"job_key": key, "status": "x"})[0], 422)
        summary = self.ok("GET", "/api/summary")
        self.assertEqual(summary["applied_this_week"], 1)
        self.assertEqual([r["job_key"] for r in summary["follow_ups_due"]], [key])
        self.assertEqual(len(summary["interviews"]), 1)
        self.assertEqual(summary["new_matches"], 0)
        status, response, csv_bytes = self.call("GET", "/api/applications/export.csv", raw=True)
        self.assertEqual(status, 200)
        self.assertIn("text/csv", response.getheader("Content-Type"))
        self.assertIn(jobs[0].company, csv_bytes.decode("utf-8-sig"))
        self.assertEqual(self.ok("GET", "/api/state")["applications"], 2)
        self.ok("DELETE", "/api/applications?job_key=" + __import__("urllib.parse").parse.quote(key))
        self.assertEqual(len(self.ok("GET", "/api/applications")["items"]), 1)

    def test_new_matches_since_last_visit(self):
        self.seed(load_demo()[1])
        self.make_profile()
        first = self.ok("GET", "/api/summary")
        self.assertGreater(first["new_matches"], 0)
        self.ok("POST", "/api/summary/seen", {})
        self.assertEqual(self.ok("GET", "/api/summary")["new_matches"], 0)


class DataTests(AppTestCase):
    def test_export_then_delete_removes_personal_data_but_keeps_cached_jobs(self):
        jobs = load_demo()[1]
        self.seed(jobs)
        self.make_profile()
        self.ok("POST", "/api/feedback", {"job_key": jobs[0].key, "verdict": "useful"})
        self.ok("POST", "/api/applications", {"job_key": jobs[0].key, "status": "saved"})
        status, response, body = self.call("GET", "/api/export", raw=True)
        self.assertIn("attachment", response.getheader("Content-Disposition"))
        export = json.loads(body)
        self.assertEqual(export["profile"]["id"], "me")
        self.assertEqual((len(export["feedback"]), len(export["applications"])), (1, 1))
        self.assertTrue((self.service.root / "cv-cache").exists())
        status, _, refusal = self.call("POST", "/api/data/delete", {"confirm": "delete"})
        self.assertEqual(status, 422)
        self.assertEqual(self.ok("POST", "/api/data/delete", {"confirm": "DELETE"})["deleted"], True)
        after = self.ok("GET", "/api/export")
        self.assertEqual((after["profile"], after["feedback"], after["applications"]), (None, [], []))
        self.assertFalse((self.service.root / "cv-cache").exists())
        self.assertFalse((self.service.root / "profiles" / "me.json").exists())
        self.assertEqual(self.ok("GET", "/api/state")["jobs"]["stored"], len(jobs))
        with self.service.open_store() as store:
            self.assertEqual(store.connection().execute("SELECT COUNT(*) FROM run").fetchone()[0], 0)

    def test_delete_all_also_removes_csv_imported_jobs_but_keeps_board_jobs(self):
        jobs = load_demo()[1]
        self.seed(jobs)
        self.ok("POST", "/api/jobs/import", {"csv": "company,title,url\nAcme,Analyst,https://vacancies.example/a1\n"})
        self.assertEqual(self.ok("GET", "/api/state")["jobs"]["stored"], len(jobs) + 1)
        self.ok("POST", "/api/data/delete", {"confirm": "DELETE"})
        self.assertEqual(self.ok("GET", "/api/state")["jobs"]["stored"], len(jobs))

    def test_existing_data_folder_is_made_owner_only_on_posix(self):
        import os
        if os.name != "posix":
            self.skipTest("POSIX permissions only")
        folder = Path(self.folder.name) / "shared"
        folder.mkdir(mode=0o755)
        os.chmod(folder, 0o755)
        AppService(folder)
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)

    def test_shutdown_stops_the_server(self):
        self.assertEqual(self.ok("POST", "/api/shutdown", {})["stopping"], True)
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())

    def test_state_reports_data_folder(self):
        self.assertEqual(self.ok("GET", "/api/state")["data_dir"], str(self.service.root))


class CommandTests(unittest.TestCase):
    def test_smoke_flag_starts_requests_and_exits(self):
        from contextlib import redirect_stdout
        from io import StringIO
        from career_discovery.__main__ import main

        out = StringIO()
        with redirect_stdout(out):
            main(["app", "--smoke", "--port", "0", "--no-browser"])
        self.assertEqual(out.getvalue().strip(), "OK")

    def test_default_data_folder_per_platform(self):
        from unittest import mock
        from career_discovery.webapp import default_data_dir

        with mock.patch("sys.platform", "darwin"):
            self.assertEqual(default_data_dir().parts[-3:], ("Library", "Application Support", "Career Discovery"))
        with mock.patch("sys.platform", "win32"), mock.patch.dict("os.environ", {"LOCALAPPDATA": "C:/L"}):
            self.assertEqual(default_data_dir().name, "Career Discovery")
        with mock.patch("sys.platform", "linux"), mock.patch.dict("os.environ", {"XDG_DATA_HOME": "/x"}):
            self.assertEqual(default_data_dir().name, "career-discovery")

    def test_busy_port_falls_through_to_the_next_free_one(self):
        from career_discovery.webapp import make_server

        with tempfile.TemporaryDirectory() as folder:
            service = AppService(folder)
            first = make_server(service, 0)
            self.addCleanup(first.server_close)
            taken = first.server_address[1]
            second = make_server(service, taken)
            self.addCleanup(second.server_close)
            self.assertGreater(second.server_address[1], taken)


if __name__ == "__main__":
    unittest.main()
