"""Orchestration for employer refresh, shortlist verification and supply snapshots."""

from collections import Counter
from datetime import datetime, timedelta

from .analysis import ANALYSER_VERSION, advert_language
from .matching import PARTIAL_FIT, SENIOR_TITLE, possible_duplicates, run_match
from .models import fingerprint
from .network import PublicHTTP
from .sources import automatic_apply_url, parse_board, verify_job
from .storage import CACHE_WINDOW, profile_data, utcnow

MAX_BOARDS = 20
MAX_VERIFY = 10


def refresh_boards(store, boards, *, client=None, max_boards=MAX_BOARDS, clock=utcnow, progress=None):
    client = client or PublicHTTP()
    if not boards:
        raise ValueError("No boards are enabled. Review the sources and use the local-use field in your board list.")
    results = []

    def add_result(entry):
        results.append(entry)
        if progress:
            progress(list(results), len(boards))

    # Consider all boards so additional batches can skip recently refreshed entries.
    attempted = 0
    for board in boards:
        started = clock()
        previous = store.board_last_success(board)
        name = {"ats": board.ats, "board": board.slug, "company": board.company}
        if previous and timedelta(0) <= started - previous < CACHE_WINDOW:
            add_result({**name, "status": "cached"})
            continue
        if attempted >= max_boards:
            add_result({**name, "status": "budget"})
            continue
        attempted += 1
        try:
            response = client.get(board.url)
            if response.status != 200:
                raise ValueError(f"Source returned HTTP {response.status}.")
            jobs = parse_board(response.body, board)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            note = str(exc)[:300]
            store.record_board(board, started, note=note)
            add_result({**name, "status": "unavailable", "reason": note})
        else:
            updated = store.record_board(board, started, jobs, "Complete public feed response.")
            add_result({**name, "status": "refreshed" if updated else "superseded", "count": len(jobs)})
    report = {"boards": results, "public_gets": client.calls, "paid_api_spend": 0}
    store.record_run(None, {**report, "command": "refresh"})
    return report


def recheck_shortlist(store, rows, *, client=None, max_checks=MAX_VERIFY, clock=utcnow):
    client = client or PublicHTTP(budget=30)
    changed = []
    seen = set()
    for row in rows:
        if len(seen) >= max_checks:
            break
        job = row.job
        if job.key in seen or job.availability == "closed" or not automatic_apply_url(job):
            continue
        now = clock()
        updated = verify_job(job, client, now, store.recent_listing(job, now))
        if updated == job:
            continue
        seen.add(job.key)
        if store.update_status(job, updated):
            changed.append({"job_key": job.key, "availability": updated.availability,
                            "reason": updated.verification_reason})
    return {"vacancies": changed, "public_gets": client.calls, "paid_api_spend": 0}


SUPPLY_POLICY_VERSION = 6


def supply_review_reasons(row):
    reasons = set()
    if not row.job.description:
        reasons.add("missing vacancy description")
    if not row.families or row.fit in {"insufficient evidence", PARTIAL_FIT}:
        reasons.add("insufficient task evidence")
    if SENIOR_TITLE.search(row.job.title):
        reasons.add("senior title signal")
    for item in row.findings:
        if item.state == "conflict":
            reasons.add(f"conflict — {item.subject}")
        elif item.state == "unknown" and item.subject in {
            "location", "language (de)", "language (en)", "responsibility coverage",
        }:
            reasons.add(f"needs review — {item.subject}")
    if advert_language(row.job.description) != "en" and not any(
        item.state == "met" and item.subject == "language (en)" for item in row.findings
    ):
        reasons.add("English working language unconfirmed")
    return sorted(reasons)


def capture_supply(store, profile, catalogue, *, clock=utcnow):
    """Count fresh, task-relevant listings without known language or location conflicts."""
    now = clock()
    source_scope = store.current_board_scope(now)
    active_sources = {tuple(item) for item in source_scope}
    jobs = []
    for job in store.jobs():
        if job.availability == "closed":
            continue
        if (job.source, job.board) in active_sources and store.recent_listing(job, now):
            jobs.append(job)
        elif job.source == "csv" and job.availability == "verified" and job.checked_at:
            checked = datetime.fromisoformat(job.checked_at.replace("Z", "+00:00"))
            if timedelta(0) <= now - checked <= CACHE_WINDOW:
                jobs.append(job)
    rows = run_match(jobs, profile, catalogue, now, analyser=lambda job: store.analyse(job, catalogue))
    flagged = [(row, supply_review_reasons(row)) for row in rows]
    counts = Counter(reason for _, reasons in flagged for reason in reasons)
    plausible = [row for row, reasons in flagged if not reasons]
    families = sorted({family for row in plausible for family in row.families})
    settings = fingerprint({
        "profile": profile_data(profile), "catalogue": catalogue.version, "analyser": ANALYSER_VERSION,
        "employer_boards": source_scope,
        "includes_checked_imports": any(job.source == "csv" for job in jobs),
    })
    history = store.supply_history()
    prior = [item for item in history
             if item.get("policy_version") == SUPPLY_POLICY_VERSION and item.get("settings") == settings]
    old = next((item for item in reversed(prior)
                if now - datetime.fromisoformat(item.get("observed_at", item["created_at"])) >= timedelta(days=6)), None)
    gate = (len(plausible) >= 10 and len({row.job.company for row in plausible}) >= 3
            and len(families) >= 2)
    current = {row.job.key for row in plausible}
    previous = set(old["keys"]) if old else set()
    snapshot = {
        "scenario": profile.id, "policy_version": SUPPLY_POLICY_VERSION, "observed_at": now.isoformat(),
        "settings": settings, "employer_boards": source_scope,
        "corpus_jobs": len(rows), "plausible": len(plausible),
        "review_reason_counts": dict(counts.most_common()),
        "actionable_count": sum(row.lane == "actionable" for row in plausible),
        "companies": sorted({row.job.company for row in plausible}), "families": families,
        "keys": sorted(current), "new_since_previous": len(current - previous),
        "repeat_since_previous": len(current & previous),
        "previous_snapshot": old["id"] if old else None,
        "previous_snapshot_at": old["created_at"] if old else None,
        "gate_met_this_snapshot": gate,
        "comparison_ready": old is not None,
        "both_snapshots_meet_gate": bool(gate and old["gate_met_this_snapshot"]) if old else None,
        "explicit_language_levels": sum(any(f.subject.startswith("language (") and f.state == "met"
                                           for f in row.findings) for row in plausible),
        "unknown_mandatory": sum(any(f.state == "unknown" and f.subject != "availability" for f in row.findings)
                                 for row in plausible),
        "possible_duplicate_groups": possible_duplicates([row.job for row in plausible]),
        "rows": [{"job_key": row.job.key, "title": row.job.title, "company": row.job.company, "url": row.job.url,
                  "families": row.families, "lane": row.lane} for row in plausible],
    }
    # Use fictional pilot scenarios for retained supply comparisons so no personal assessment is persisted.
    ident = store.record_supply(snapshot) if profile.fictional else None
    return {**snapshot, "id": ident, "observed_at": now.isoformat()}
