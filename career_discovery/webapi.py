"""Application logic behind the local web app. Nothing here speaks HTTP."""

from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import threading

from . import __version__
from .analysis import ANALYSER_VERSION, load_catalogue, task_tags
from .documents import EXTRACTOR_VERSION, MAX_DOCUMENT, extract_profile, remove_stale_temp_copies
from .eligibility import language_findings
from .matching import as_record, berlin_date, discover_families, run_match, split_ranked
from .models import Evidence, Profile, clean_text
from .network import PublicHTTP
from .rendering import safe_text
from .salary import extract_salary
from .sourcing import refresh_boards, supply_review_reasons
from .sources import load_boards, load_csv, verify_job
from .storage import Storage, profile_data, utcnow
from .tracker import FieldErrors, applications_csv, normalise_application

PROFILE_ID = "me"
DETAIL_FIELDS = ("languages", "locations", "remote_regions", "employment", "search_titles", "keywords",
                 "interests", "known_gaps", "verified_requirements", "stage", "enrolled", "recent_graduate",
                 "needs_sponsorship", "experience_months")
MODES = {"task": ["task"], "title": ["title"], "both": ["task", "title"]}
LANES = ("actionable", "verify first", "excluded")
VERDICTS = {
    "useful": {"relevance": "yes", "would_consider": "yes", "new_to_me": "uncertain"},
    "not_for_me": {"relevance": "no", "would_consider": "no", "new_to_me": "uncertain"},
    "new_to_me": {"relevance": "uncertain", "would_consider": "uncertain", "new_to_me": "yes"},
}
ANSWERS = ("yes", "no", "uncertain")
STATE_RANK = {"met": 0, "unknown": 1, "conflict": 2}
ALL_LEVELS = {code: "A1" for code in ("de", "en", "fr", "es")}
ASKED_LEVEL = re.compile(r"The ad specifies ([ABC][12])")



def mentions(job, terms):
    """Every filter word appears in the title, company or places (case-insensitive)."""
    text = " ".join([job.title, job.company, *job.locations, *job.remote_regions]).casefold()
    return all(term in text for term in terms)

def duty_excerpt(requirements, terms, tasks):
    if terms:
        for req in requirements:
            if req.kind == "core" and (all(word in req.text.casefold() for word in terms)
                                       or tasks and tasks.issubset(req.tasks)):
                return req.text
    return None


def trial_yield(rows, trial_boards, base_boards):
    baseline = set()
    extra = {}
    for row in rows:
        job = row.job
        if job.availability == "closed":
            continue
        board = (job.source, job.board)
        key = job.url
        if board in base_boards:
            baseline.add(key)
        elif board in trial_boards:
            extra[key] = extra.get(key, False) or not supply_review_reasons(row)
    unique = extra.keys() - baseline
    return {"unique": len(unique), "plausible": sum(extra[key] for key in unique)}


class ApiError(Exception):
    def __init__(self, status, code, message, fields=None):
        super().__init__(message)
        self.status, self.code, self.message, self.fields = status, code, message, fields


class AppService:
    def __init__(self, root, *, catalogue=None, boards_path=None, client_factory=PublicHTTP, clock=utcnow):
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name == "posix":
            try:
                if root.stat().st_uid == os.getuid():
                    os.chmod(root, 0o700)
            except OSError:
                pass
        remove_stale_temp_copies()
        self.root = root.resolve()
        self.catalogue = catalogue or load_catalogue()
        self.boards_path = Path(boards_path) if boards_path else Path(__file__).with_name("boards.json")
        self.client_factory = client_factory
        self.clock = clock
        self.lock = threading.RLock()
        self.refresh_lock = threading.RLock()
        self.refresh_thread = None
        self.refresh = {"status": "idle", "total": 0, "done": 0, "boards": [], "started_at": None,
                        "finished_at": None, "public_gets": 0, "error": None}

    @contextmanager
    def open_store(self):
        store = Storage(self.root)
        try:
            yield store
        finally:
            store.close()

    def today(self):
        return berlin_date(self.clock())

    # profile -----------------------------------------------------------------------------------

    def _profile(self, store, confirmed=False):
        path = store.profile_path(PROFILE_ID)
        if not path.is_file():
            if confirmed:
                raise ApiError(409, "profile_not_ready", "Add your CV or details and confirm them first.")
            raise ApiError(404, "no_profile", "There is no profile yet. Upload your CV or start without one.")
        profile = store.profile(PROFILE_ID)
        if confirmed and not profile.confirmed:
            raise ApiError(409, "profile_not_ready", "Review and confirm your profile first.")
        return profile

    def _view(self, profile):
        return {"profile": {**profile_data(profile), "evidence_usable": len(profile.usable_evidence)},
                "cv": self._cv_info()}

    def _cv_info(self):
        path = self.root / "cv-cache" / "info.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _cache_cv(self, filename, suffix, data):
        folder = self.root / "cv-cache"
        folder.mkdir(mode=0o700, exist_ok=True)
        for name, payload in ((f"last-cv{suffix}", data),
                              ("info.json", json.dumps({"name": safe_text(Path(filename).name)[:120],
                                                        "uploaded_at": self.clock().isoformat()}).encode())):
            fd = os.open(folder / name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)

    def profile_from_cv(self, filename, data):
        suffix = Path(filename or "").suffix.casefold()
        if suffix not in {".docx", ".pdf"}:
            raise ValueError("Upload a text-based PDF or DOCX, or start without a CV.")
        if len(data) > MAX_DOCUMENT:
            raise ValueError("That file is larger than 12 MB.")
        digest = sha256(EXTRACTOR_VERSION + data).hexdigest()
        with self.lock, self.open_store() as store:
            existing = store.profile(PROFILE_ID) if store.profile_path(PROFILE_ID).is_file() else None
            if existing and existing.document_hash == digest:
                return self._view(existing)
            profile = extract_profile(PROFILE_ID, suffix, data, digest, self.catalogue, existing)
            store.save_profile(profile)
            self._cache_cv(filename, suffix, data)
            return self._view(profile)

    def new_profile(self, replace_existing=False):
        with self.lock, self.open_store() as store:
            if store.profile_path(PROFILE_ID).is_file() and not replace_existing:
                raise ApiError(409, "profile_exists", "A profile already exists. Replace it to start again.")
            profile = Profile(PROFILE_ID, False, False, ())
            store.save_profile(profile)
            return self._view(profile)

    def get_profile(self):
        with self.open_store() as store:
            return self._view(self._profile(store))

    def update_details(self, body):
        with self.lock, self.open_store() as store:
            profile = self._profile(store)
            base = profile_data(profile)
            errors = {key: "This field cannot be changed here." for key in body if key not in DETAIL_FIELDS}
            for key in (k for k in body if k in DETAIL_FIELDS):
                try:
                    if key == "languages" and not body[key]:
                        raise ValueError("Add at least one language with its level.")
                    Profile.load({**base, key: body[key]})
                except (ValueError, TypeError, KeyError, AttributeError) as exc:
                    errors[key] = safe_text(str(exc)) if isinstance(exc, ValueError) else "This value is not valid."
            if errors:
                raise ApiError(422, "invalid", "Some details need fixing before they can be saved.", errors)
            updated = Profile.load({**base, **body})
            store.save_profile(updated)
            return self._view(updated)

    def change_evidence(self, body):
        action = body.get("action")
        with self.lock, self.open_store() as store:
            profile = self._profile(store)
            items = list(profile.evidence)
            index = next((i for i, e in enumerate(items) if e.id == body.get("id")), None)
            if action in {"keep", "edit", "remove"} and index is None:
                raise ApiError(404, "not_found", "That item is no longer in your profile.")
            if action == "remove":
                del items[index]
            elif action == "keep":
                if items[index].state == "inferred":
                    items[index] = replace(items[index], state="user_confirmed")
            elif action == "edit":
                data = {**items[index].__dict__, "text": body.get("text", ""), "state": "user_confirmed"}
                if "scope" in body:
                    data["scope"] = body["scope"]
                items[index] = Evidence.load(data)
            elif action == "add":
                taken = {e.id for e in items}
                number = next(n for n in range(1, 1000) if f"me-{n:03}" not in taken)
                items.append(Evidence.load({"id": f"me-{number:03}", "text": body.get("text", ""),
                                            "locator": "Added by you", "state": "user_confirmed",
                                            "context": body.get("context", ""), "scope": body.get("scope", "")}))
            else:
                raise ApiError(422, "invalid", "The action must be keep, edit, remove or add.")
            updated = Profile.load(profile_data(replace(profile, evidence=tuple(items))))
            store.save_profile(updated)
            return self._view(updated)

    def confirm_profile(self):
        with self.lock, self.open_store() as store:
            profile = replace(self._profile(store), confirmed=True)
            if not profile.usable_evidence:
                raise ApiError(422, "invalid", "Keep at least one item from your CV, or add one, before confirming.")
            store.save_profile(profile)
            return self._view(profile)

    def families(self):
        with self.open_store() as store:
            return {"families": discover_families(self._profile(store, confirmed=True), self.catalogue)}

    # jobs --------------------------------------------------------------------------------------

    def start_refresh(self, group="standard"):
        boards = load_boards(self.boards_path)
        if group not in ("standard", "expanded"):
            raise ValueError("Unknown board group.")
        if group == "expanded":
            boards += load_boards(Path(__file__).with_name("trial-boards.json"))
        with self.refresh_lock:
            if self.refresh["status"] == "running":
                raise ApiError(409, "refresh_running", "The job boards are already being read.")
            self.refresh = {"status": "running", "total": len(boards), "done": 0, "boards": [],
                            "started_at": self.clock().isoformat(), "finished_at": None, "public_gets": 0,
                            "error": None}
            self.refresh_thread = threading.Thread(target=self._refresh_worker, args=(boards, group), daemon=True)
            self.refresh_thread.start()
            return self.refresh_status()

    def _progress(self, results, total):
        with self.refresh_lock:
            self.refresh.update(boards=results, done=len(results), total=total)

    def _refresh_worker(self, boards, group):
        outcome = {}
        try:
            with self.open_store() as store:
                client = self.client_factory()
                report = refresh_boards(store, boards, client=client, clock=self.clock, progress=self._progress)
                measurement = {}
                if group == "expanded":
                    complete = all(b["status"] in {"refreshed", "cached"} for b in report["boards"])
                    measurement["comparison_complete"] = complete
                    if complete:
                        try:
                            profile = self._profile(store, confirmed=True)
                        except ApiError:
                            profile = None
                        if profile:
                            base = {(b.ats, b.slug) for b in load_boards(self.boards_path)}
                            trial = {(b.ats, b.slug) for b in boards} - base
                            now = self.clock()
                            jobs = [j for j in store.jobs() if j.availability != "closed"
                                    and (j.source, j.board) in base | trial and store.recent_listing(j, now)]
                            # Compare sources before the matcher collapses identical employer URLs.
                            base_urls = {j.url for j in jobs if (j.source, j.board) in base}
                            additional = [j for j in jobs if j.url not in base_urls]
                            rows = run_match(additional, profile, self.catalogue, now,
                                             analyser=lambda job: store.analyse(job, self.catalogue))
                            measurement["trial"] = trial_yield(rows, trial, base)
            outcome = {"status": "done", "boards": report["boards"], "public_gets": report["public_gets"], **measurement}
        except ValueError as exc:
            outcome = {"status": "error", "error": safe_text(str(exc))}
        except Exception:
            outcome = {"status": "error", "error": "Reading the job boards stopped unexpectedly. Try again later."}
        with self.refresh_lock:
            self.refresh.update(outcome, finished_at=self.clock().isoformat())
            self.refresh["done"] = len(self.refresh["boards"])

    def refresh_status(self):
        with self.refresh_lock:
            return json.loads(json.dumps(self.refresh))

    def join_refresh(self, timeout=None):
        thread = self.refresh_thread
        if thread:
            thread.join(timeout)

    def import_csv(self, data, keep_description=False):
        with tempfile.NamedTemporaryFile(dir=self.root, suffix=".csv", delete=False) as stream:
            stream.write(data)
        try:
            jobs = load_csv(stream.name, keep_description=keep_description)
        finally:
            Path(stream.name).unlink(missing_ok=True)
        with self.open_store() as store:
            store.import_jobs(jobs)
        return {"imported": len(jobs), "kept_description_fields": keep_description}

    # matches -----------------------------------------------------------------------------------

    def _match(self, store, profile, now):
        return run_match(store.jobs(), profile, self.catalogue, now,
                         analyser=lambda job: store.analyse(job, self.catalogue))

    def _decorate(self, row, profile, baseline, today, applications):
        record = as_record(row, profile, baseline=baseline)
        listed = row.job.listed_date
        record.update(
            salary=extract_salary(row.job.description),
            age_days=max(0, (today - date.fromisoformat(listed)).days) if listed else None,
            deadline=row.job.deadline,
            language_summary=language_summary(row, profile),
            wording=wording(record),
            application=applications.get(row.job.key),
        )
        return record

    def matches(self, mode="task", limit=50, excluded=False, hide_language_conflicts=False, query="", duties=False):
        if mode not in MODES:
            raise ApiError(422, "invalid", "The mode must be task, title or both.")
        if not 1 <= limit <= 200:
            raise ApiError(422, "invalid", "The limit must be between 1 and 200.")
        query = " ".join(str(query or "").split())
        if len(query) > 100:
            raise ApiError(422, "invalid", "Use at most 100 characters in the filter.")
        terms = query.casefold().split()
        tasks = set(task_tags(query, self.catalogue)) if duties and terms else set()
        now = self.clock()
        with self.open_store() as store:
            profile = self._profile(store, confirmed=True)
            rows = self._match(store, profile, now)
            applications = {a["job_key"]: a["status"] for a in store.applications()}
            results, counts, shown = {}, {}, {}
            for name in MODES[mode]:
                ranked = split_ranked(rows, "baseline" if name == "title" else "task")
                counts[name] = {lane: len(found) for lane, found in ranked.items()}
                results[name], shown[name] = {}, {}
                for lane in LANES:
                    if lane == "excluded" and not excluded:
                        continue
                    records = []
                    for row in ranked[lane]:
                        excerpt = duty_excerpt(row.requirements, terms, tasks) if duties else None
                        if excerpt is None and not mentions(row.job, terms):
                            continue
                        record = self._decorate(row, profile, name == "title", berlin_date(now), applications)
                        if excerpt:
                            record["search_excerpt"] = excerpt
                        records.append(record)
                    if hide_language_conflicts:
                        records = [r for r in records if not r["language_summary"]["conflict"]]
                    shown[name][lane] = len(records)
                    results[name][lane] = records[:limit]
            return {"mode": mode, "corpus_vacancies": len(rows), "counts": counts, "shown": shown, "query": query,
                    "results": results, "generated_at": now.isoformat()}

    def recheck(self, key):
        with self.lock, self.open_store() as store:
            job = store.job(key)
            if job.availability == "closed" or job.source not in {"ashby", "greenhouse"}:
                raise ValueError("Only listed vacancies from the employer boards can be rechecked here. "
                                 "Open the employer link yourself instead.")
            now = self.clock()
            listed_at = store.recent_listing(job, now)
        client = self.client_factory(budget=8)
        reviewed = verify_job(job, client, now, listed_at)
        with self.lock, self.open_store() as store:
            if not store.update_status(job, reviewed):
                raise ApiError(409, "changed", "The listing changed while it was checked. Try again.")
            result = {"job_key": key, "availability": reviewed.availability, "checked_at": reviewed.checked_at,
                      "reason": reviewed.verification_reason, "public_gets": client.calls, "paid_api_spend": 0}
            store.record_run(None, {**result, "command": "verify-job"})
            return result

    def add_feedback(self, body):
        verdict = body.get("verdict")
        if verdict is not None and verdict not in VERDICTS:
            raise ApiError(422, "invalid", "The verdict must be useful, not_for_me or new_to_me.")
        answer = {"relevance": "uncertain", "would_consider": "uncertain", "new_to_me": "uncertain",
                  **VERDICTS.get(verdict, {})}
        errors = {}
        for field in ("relevance", "would_consider", "new_to_me"):
            if field in body:
                if body[field] in ANSWERS:
                    answer[field] = body[field]
                else:
                    errors[field] = "Use yes, no or uncertain."
        if errors:
            raise ApiError(422, "invalid", "Some answers are not valid.", errors)
        answer["correction"] = clean_text(body.get("reason", body.get("correction", "")), "Reason", 1000)
        with self.open_store() as store:
            self._profile(store, confirmed=True)
            store.add_feedback(PROFILE_ID, body.get("job_key", ""), answer)
        return {"saved": True}

    def list_feedback(self):
        with self.open_store() as store:
            return {"items": store.feedback_for(PROFILE_ID)}

    # tracker -----------------------------------------------------------------------------------

    def list_applications(self):
        today = self.today().isoformat()
        with self.open_store() as store:
            rows = store.applications()
        return {"items": [{**r, "follow_up_due": bool(r["follow_up_on"] and r["follow_up_on"] <= today
                                                       and r["status"] in {"applied", "interview"})}
                          for r in rows]}

    def save_application(self, body):
        key = body.get("job_key")
        if not isinstance(key, str) or not key:
            raise ApiError(422, "invalid", "Say which vacancy this is for.", {"job_key": "Required."})
        with self.lock, self.open_store() as store:
            existing = next((r for r in store.applications() if r["job_key"] == key), None)
            row = normalise_application(body, existing, self.today())
            store.put_application(row, self.clock().isoformat())
            saved = next(r for r in store.applications() if r["job_key"] == key)
        return {"application": saved}

    def remove_application(self, key):
        with self.open_store() as store:
            if not store.delete_application(key):
                raise ApiError(404, "not_found", "That vacancy is not in your applications.")
        return {"deleted": True}

    def applications_csv(self):
        with self.open_store() as store:
            return applications_csv(store.applications()).encode("utf-8")

    def summary(self):
        today = self.today()
        week_start = today - timedelta(days=today.weekday())
        with self.open_store() as store:
            apps = store.applications()
            applied = [a for a in apps if a["status"] != "saved" and a["applied_on"]
                       and week_start <= date.fromisoformat(a["applied_on"]) <= today]
            due = [a for a in apps if a["status"] in {"applied", "interview"} and a["follow_up_on"]
                   and a["follow_up_on"] <= today.isoformat()]
            keys = self._current_match_keys(store)
            seen = set(store.meta("seen_keys", []))
            last_visit = store.meta("last_visit")
        return {"today": today.isoformat(), "week_start": week_start.isoformat(),
                "applied_this_week": len(applied), "follow_ups_due": due,
                "interviews": [a for a in apps if a["status"] == "interview"],
                "new_matches": len([k for k in keys if k not in seen]), "last_visit": last_visit,
                "first_visit": last_visit is None,
                "counts": {s: sum(a["status"] == s for a in apps) for s in sorted({a["status"] for a in apps})}}

    def _current_match_keys(self, store):
        path = store.profile_path(PROFILE_ID)
        if not path.is_file() or not store.profile(PROFILE_ID).confirmed:
            return []
        profile = store.profile(PROFILE_ID)
        ranked = split_ranked(self._match(store, profile, self.clock()), "task")
        return [row.job.key for lane in ("actionable", "verify first") for row in ranked[lane]]

    def mark_seen(self):
        with self.open_store() as store:
            store.set_meta("seen_keys", self._current_match_keys(store))
            store.set_meta("last_visit", self.clock().isoformat())
        return {"saved": True}

    # state and data ----------------------------------------------------------------------------

    def state(self):
        with self.open_store() as store:
            has_profile = store.profile_path(PROFILE_ID).is_file()
            profile = store.profile(PROFILE_ID) if has_profile else None
            payloads = [json.loads(r["payload"]) for r in store.connection().execute("SELECT payload FROM job")]
            stored = len(payloads)
            open_jobs = sum(p.get("availability") != "closed" for p in payloads)
            last = store.last_board_success()
            applications = len(store.applications())
        if not profile or not profile.evidence:
            step = "cv"
        elif not profile.confirmed or not profile.languages:
            step = "details"
        elif not stored:
            step = "jobs"
        else:
            step = "matches"
        return {
            "app_version": __version__, "analyser_version": ANALYSER_VERSION, "data_dir": str(self.root),
            "profile": {"exists": has_profile, "confirmed": bool(profile and profile.confirmed),
                        "evidence_total": len(profile.evidence) if profile else 0,
                        "evidence_usable": len(profile.usable_evidence) if profile else 0,
                        "has_languages": bool(profile and profile.languages)},
            "jobs": {"stored": stored, "open": open_jobs, "last_fetched": last},
            "refresh": self.refresh_status(), "applications": applications, "step": step, "cv": self._cv_info(),
        }

    def export_all(self):
        with self.open_store() as store:
            has_profile = store.profile_path(PROFILE_ID).is_file()
            return {"exported_at": self.clock().isoformat(), "app_version": __version__,
                    "profile": profile_data(store.profile(PROFILE_ID)) if has_profile else None,
                    "cv": self._cv_info(), "feedback": store.all_feedback(),
                    "applications": store.applications(), "last_visit": store.meta("last_visit")}

    def delete_all(self, confirm):
        if confirm != "DELETE":
            raise ApiError(422, "invalid", 'Type DELETE in capital letters to confirm.', {"confirm": "Type DELETE."})
        with self.lock, self.open_store() as store:
            store.profile_path(PROFILE_ID).unlink(missing_ok=True)
            store.delete_user_data()
        shutil.rmtree(self.root / "cv-cache", ignore_errors=True)
        return {"deleted": True}


def language_summary(row, profile):
    """The level the ad asks for next to the user's, for each language the ad names."""
    languages = {}
    probe = replace(profile, languages=ALL_LEVELS)
    for finding in row.findings:
        match = re.fullmatch(r"language \((\w+)\)", finding.subject)
        if not match:
            continue
        code = match.group(1)
        asked = next((ASKED_LEVEL.search(f.reason) for f in language_findings(finding.excerpt, probe)
                      if f.subject == finding.subject), None)
        entry = {"asked": asked.group(1) if asked else None, "yours": profile.languages.get(code),
                 "state": finding.state}
        if code not in languages or STATE_RANK[entry["state"]] > STATE_RANK[languages[code]["state"]]:
            languages[code] = entry
    return {"languages": languages, "conflict": any(e["state"] == "conflict" for e in languages.values())}


def wording(record):
    """Ad duties the CV backs with its own line, and ad duties it does not show yet. No text is generated."""
    duties = {r["id"]: r["text"] for r in record["requirements"] if r["kind"] == "core"}
    supported, missing, seen = [], [], set()
    for link in record["evidence_links"]:
        ad = duties.get(link["requirement_id"])
        if ad is None or (ad, link["task_id"], link["kind"]) in seen:
            continue
        seen.add((ad, link["task_id"], link["kind"]))
        if link["kind"] in {"direct", "transferable"} and link.get("evidence"):
            supported.append({"ad": ad, "cv": link["evidence"]["text"], "task": link["task_id"], "kind": link["kind"]})
        else:
            missing.append({"ad": ad, "task": link["task_id"], "kind": link["kind"]})
    return {"supported": supported, "missing": missing}
