"""Local vacancy cache and run records. Candidate evidence is kept in separate JSON files."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
from tempfile import NamedTemporaryFile
from uuid import uuid4

from .analysis import ANALYSER_VERSION, analyse_description
from .models import FEED_REMOVAL, Job, Profile, Requirement, fingerprint, identifier
from .storage_limits import read_bytes

CACHE_WINDOW = timedelta(hours=24)


def utcnow():
    return datetime.now(timezone.utc)


def read_json(path, limit=2_000_000):
    return json.loads(read_bytes(Path(path), limit))


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def write_private_json(path: Path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            stream.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def profile_data(profile):
    return {"schema_version": 1, **asdict(profile)}


def same_listing(old, new):
    return (old.url, old.apply_url, old.description, old.deadline) == (
        new.url, new.apply_url, new.description, new.deadline,
    )


class Storage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = None

    def close(self):
        if self.db is not None:
            self.db.close()
            self.db = None

    def connection(self):
        if self.db is None:
            path = self.root / "vacancies.sqlite"
            # Pre-create with a private mode. The containing state directory is also private.
            fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
            os.close(fd)
            self.db = sqlite3.connect(path, timeout=15.0)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA secure_delete=ON")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS job (
                    key TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    board TEXT NOT NULL,
                    listed_at TEXT,
                    payload TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS job_board ON job(source, board);
                CREATE TABLE IF NOT EXISTS board_run (
                    source TEXT NOT NULL,
                    board TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    count INTEGER,
                    note TEXT NOT NULL,
                    PRIMARY KEY (source, board, observed_at)
                );
                CREATE TABLE IF NOT EXISTS job_analysis (
                    digest TEXT PRIMARY KEY,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL,
                    job TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run (
                    id TEXT PRIMARY KEY,
                    profile TEXT,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS application (
                    job_key TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    applied_on TEXT,
                    follow_up_on TEXT,
                    notes TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS supply (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
            """)
        return self.db

    def profile_path(self, profile_id):
        return self.root / "profiles" / f"{identifier(profile_id)}.json"

    def profile(self, profile_id):
        item = Profile.load(read_json(self.profile_path(profile_id)))
        if item.id != profile_id:
            raise ValueError("Profile ID does not match its filename.")
        return item

    def save_profile(self, profile):
        path = self.profile_path(profile.id)
        write_private_json(path, profile_data(profile))
        return path

    def delete_profile(self, profile_id):
        path = self.profile_path(profile_id)
        if not path.is_file():
            raise ValueError("Profile does not exist.")
        db = self.connection()
        with db:
            db.execute("DELETE FROM feedback WHERE profile=?", (profile_id,))
            db.execute("DELETE FROM run WHERE profile=?", (profile_id,))
        path.unlink()

    def export_profile(self, profile_id, destination):
        write_private_json(Path(destination), {
            "profile": profile_data(self.profile(profile_id)),
            "feedback": self.feedback_for(profile_id),
        })

    def jobs(self):
        db = self.connection()
        return [Job.load(json.loads(row["payload"])) for row in db.execute("SELECT payload FROM job ORDER BY key")]

    def job(self, key):
        row = self.connection().execute("SELECT payload FROM job WHERE key=?", (key,)).fetchone()
        if row is None:
            raise ValueError("Vacancy key was not found.")
        return Job.load(json.loads(row["payload"]))

    @staticmethod
    def _put_job(db, job, listed_at=None):
        db.execute(
            "INSERT INTO job VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET listed_at=excluded.listed_at, payload=excluded.payload",
            (job.key, job.source, job.board, listed_at, encoded(asdict(job))),
        )

    def import_jobs(self, jobs):
        db = self.connection()
        with db:
            db.execute("BEGIN IMMEDIATE")
            for job in jobs:
                old = db.execute("SELECT payload FROM job WHERE key=?", (job.key,)).fetchone()
                if old:
                    previous = Job.load(json.loads(old["payload"]))
                    # Keep a previously permissible local description if the new row has link metadata only.
                    if not job.description and job.url == previous.url:
                        job = replace(job, description=previous.description)
                    if same_listing(previous, job):
                        job = replace(job, availability=previous.availability, checked_at=previous.checked_at,
                                      verification_reason=previous.verification_reason)
                self._put_job(db, job)

    def board_last_success(self, board):
        row = self.connection().execute(
            "SELECT observed_at FROM board_run WHERE source=? AND board=? AND success=1 "
            "ORDER BY observed_at DESC LIMIT 1", (board.ats, board.slug),
        ).fetchone()
        return datetime.fromisoformat(row["observed_at"]) if row else None

    def current_board_scope(self, now):
        rows = self.connection().execute(
            "SELECT source, board, MAX(observed_at) AS recent FROM board_run "
            "WHERE success=1 GROUP BY source, board ORDER BY source, board"
        )
        scope = []
        for row in rows:
            observed = datetime.fromisoformat(row["recent"])
            if timedelta(0) <= now - observed <= CACHE_WINDOW:
                scope.append([row["source"], row["board"]])
        return scope

    def record_board(self, board, now, jobs=None, note=""):
        """Apply only complete, successful snapshots. A failed fetch cannot close vacancies."""
        db = self.connection()
        observed_at = now.isoformat()
        with db:
            db.execute("BEGIN IMMEDIATE")
            previous_at = self.board_last_success(board)
            if jobs is not None and previous_at is not None and previous_at >= now:
                return False
            db.execute("INSERT INTO board_run VALUES (?, ?, ?, ?, ?, ?)",
                       (board.ats, board.slug, observed_at, int(jobs is not None),
                        len(jobs) if jobs is not None else None, note[:300]))
            if jobs is None:
                return True
            current = {job.key: job for job in jobs}
            rows = db.execute("SELECT key, payload FROM job WHERE source=? AND board=?",
                              (board.ats, board.slug)).fetchall()
            for row in rows:
                old = Job.load(json.loads(row["payload"]))
                if row["key"] in current:
                    fresh = current[row["key"]]
                    closed_page = (old.availability == "closed" and old.verification_reason != FEED_REMOVAL
                                   and (old.url, old.apply_url) == (fresh.url, fresh.apply_url))
                    verified_recently = (old.availability == "verified" and old.checked_at
                                         and timedelta(0) <= now - datetime.fromisoformat(old.checked_at) <= CACHE_WINDOW
                                         and same_listing(old, fresh))
                    if closed_page or verified_recently:
                        current[row["key"]] = replace(fresh, availability=old.availability, checked_at=old.checked_at,
                                                      verification_reason=old.verification_reason)
                elif old.availability == "closed" and old.verification_reason != FEED_REMOVAL:
                    self._put_job(db, old)
                else:
                    self._put_job(db, replace(
                        old, availability="closed", checked_at=observed_at, verification_reason=FEED_REMOVAL,
                    ))
            for job in current.values():
                self._put_job(db, job, listed_at=observed_at)
        return True

    def recent_listing(self, job, now):
        row = self.connection().execute("SELECT listed_at FROM job WHERE key=?", (job.key,)).fetchone()
        if not row or not row["listed_at"]:
            return None
        observed = datetime.fromisoformat(row["listed_at"])
        return observed if timedelta(0) <= now - observed <= CACHE_WINDOW else None

    def update_status(self, before, after):
        db = self.connection()
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload, listed_at FROM job WHERE key=?", (before.key,)).fetchone()
            if not row or Job.load(json.loads(row["payload"])) != before:
                return False
            self._put_job(db, after, row["listed_at"])
        return True

    def analyse(self, job, catalogue):
        digest = fingerprint([job.description, catalogue.version, ANALYSER_VERSION])
        db = self.connection()
        row = db.execute("SELECT payload FROM job_analysis WHERE digest=?", (digest,)).fetchone()
        if row:
            return tuple(Requirement(**{**item, "tasks": tuple(item["tasks"])}) for item in json.loads(row["payload"]))
        requirements = analyse_description(job.description, catalogue)
        with db:
            db.execute("INSERT OR IGNORE INTO job_analysis VALUES (?, ?)",
                       (digest, encoded([asdict(req) for req in requirements])))
        return requirements

    def feedback_for(self, profile):
        rows = self.connection().execute(
            "SELECT job, created_at, payload FROM feedback WHERE profile=? ORDER BY created_at", (profile,),
        )
        return [{**json.loads(row["payload"]), "job_key": row["job"], "recorded_at": row["created_at"]}
                for row in rows]

    def add_feedback(self, profile, key, answer):
        db = self.connection()
        self.profile(profile)
        self.job(key)
        with db:
            db.execute("INSERT INTO feedback VALUES (?, ?, ?, ?, ?)",
                       (uuid4().hex, profile, key, utcnow().isoformat(), encoded(answer)))

    def record_run(self, profile, report):
        ident = uuid4().hex
        db = self.connection()
        with db:
            db.execute("INSERT INTO run VALUES (?, ?, ?, ?)",
                       (ident, profile, utcnow().isoformat(), encoded(report)))
        return ident

    def record_supply(self, snapshot):
        ident = uuid4().hex
        db = self.connection()
        with db:
            db.execute("INSERT INTO supply VALUES (?, ?, ?)", (ident, utcnow().isoformat(), encoded(snapshot)))
        return ident

    def supply_history(self):
        rows = self.connection().execute("SELECT * FROM supply ORDER BY created_at")
        return [{**json.loads(row["payload"]), "id": row["id"], "created_at": row["created_at"]}
                for row in rows]

    def applications(self):
        rows = self.connection().execute(
            "SELECT a.*, j.payload FROM application a LEFT JOIN job j ON j.key = a.job_key "
            "ORDER BY a.updated_at DESC, a.job_key")
        result = []
        for row in rows:
            job = json.loads(row["payload"]) if row["payload"] else {}
            result.append({"job_key": row["job_key"], "company": job.get("company", ""), "title": job.get("title", ""),
                           "url": job.get("url", ""), "status": row["status"], "applied_on": row["applied_on"],
                           "follow_up_on": row["follow_up_on"], "notes": row["notes"],
                           "updated_at": row["updated_at"]})
        return result

    def put_application(self, row, updated_at):
        db = self.connection()
        self.job(row["job_key"])
        with db:
            db.execute(
                "INSERT INTO application VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(job_key) DO UPDATE SET "
                "status=excluded.status, applied_on=excluded.applied_on, follow_up_on=excluded.follow_up_on, "
                "notes=excluded.notes, updated_at=excluded.updated_at",
                (row["job_key"], row["status"], row["applied_on"], row["follow_up_on"], row["notes"], updated_at))

    def delete_application(self, key):
        db = self.connection()
        with db:
            return db.execute("DELETE FROM application WHERE job_key=?", (key,)).rowcount > 0

    def meta(self, key, default=None):
        row = self.connection().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_meta(self, key, value):
        db = self.connection()
        with db:
            db.execute("INSERT INTO meta VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (key, encoded(value)))

    def last_board_success(self):
        row = self.connection().execute("SELECT MAX(observed_at) AS latest FROM board_run WHERE success=1").fetchone()
        return row["latest"]

    def all_feedback(self):
        rows = self.connection().execute("SELECT profile, job, created_at, payload FROM feedback ORDER BY created_at")
        return [{**json.loads(row["payload"]), "job_key": row["job"], "recorded_at": row["created_at"]}
                for row in rows]

    def delete_user_data(self):
        """Remove feedback, applications, search logs, visit markers and CSV-imported jobs. Board listings stay."""
        db = self.connection()
        with db:
            for table in ("feedback", "application", "run", "meta"):
                db.execute(f"DELETE FROM {table}")
            db.execute("DELETE FROM job WHERE source='csv'")
