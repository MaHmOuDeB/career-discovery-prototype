"""Offline-first career discovery CLI. Public requests require an explicit command."""

import argparse
from dataclasses import replace
from itertools import zip_longest
from pathlib import Path
import sqlite3
import sys
from datetime import datetime, timezone
from time import monotonic

from .analysis import load_catalogue
from .demo import load_demo
from .diagnostics import coverage_report, heldout_report
from .documents import document_data, extract_profile
from .evaluation import demo_comparison, pilot_metrics
from .matching import as_record, discover_families, run_match, split_ranked
from .models import MANUAL_VERIFICATION_PREFIX, Profile, canonical_url, clean_text, identifier
from .rendering import demo_text, json_output, safe_text, short_list
from .semantic import accepted_by_profile, brief, save_review, validated_proposals
from .sourcing import MAX_BOARDS, capture_supply, recheck_shortlist, refresh_boards
from .sources import load_boards, load_csv, verify_job
from .network import PublicHTTP
from .pilot import prepare_review
from .storage import Storage, profile_data, read_json, utcnow, write_private_json


def profile_command(args, store, catalogue):
    key = identifier(args.id)
    path = store.profile_path(key)
    action = args.profile_command
    if action == "new":
        if path.exists():
            raise ValueError("This profile already exists.")
        store.save_profile(Profile(key, False, False, ()))
        return f"Manual draft created at {path}. Edit the JSON, then confirm it."
    if action == "import":
        existing = store.profile(key) if path.exists() else None
        data, digest = document_data(args.document)
        if existing and existing.document_hash == digest:
            return f"Using the existing profile at {path}. Its reviewed edits are retained."
        if existing and not args.replace:
            raise ValueError("A profile exists. Use --replace to review a changed CV or use a different ID.")
        profile = extract_profile(key, Path(args.document).suffix, data, digest, catalogue, existing)
        store.save_profile(profile)
        return f"Extracted {len(profile.evidence)} draft evidence items to {path}. Review the JSON, then confirm it."
    if action == "load":
        if path.exists() and not args.replace:
            raise ValueError("A profile exists. Use --replace to replace it.")
        profile = Profile.load(read_json(args.file))
        if profile.id != key:
            raise ValueError("The profile ID must match the supplied ID.")
        store.save_profile(replace(profile, confirmed=False))
        return f"Draft profile saved at {path}. Confirm after reviewing the JSON."
    if action == "show":
        return profile_data(store.profile(key))
    if action == "confirm":
        profile = replace(store.profile(key), confirmed=True)
        if not profile.usable_evidence:
            raise ValueError("Confirm at least one CV-stated or user-confirmed evidence item.")
        store.save_profile(profile)
        return f"Reviewed profile saved at {path}."
    if action == "export":
        if Path(args.output).exists():
            raise ValueError("Export destination already exists.")
        store.export_profile(key, args.output)
        return f"Profile and feedback exported to {args.output}."
    if action == "delete":
        store.delete_profile(key)
        return "The local profile, run records and feedback were deleted."
    raise ValueError("Unknown profile action.")


def find_job(store, label):
    if label.startswith("https://"):
        url = canonical_url(label)
        matches = [job for job in store.jobs() if url in {job.url, job.apply_url}]
        if len(matches) == 1:
            return matches[0]
        raise ValueError("URL did not identify exactly one stored vacancy. Use its job_key from jobs or search --json.")
    return store.job(label)


def prefer_rechecks(lists, limit):
    by_mode = []
    for ranking in lists:
        rows = [row for row in ranking["verify first"]
                if all(f.state != "unknown" or f.subject == "availability" for f in row.findings)]
        pending_requirements = [row for row in ranking["verify first"] if row not in rows]
        by_mode.append(rows[:limit] + ranking["actionable"][:limit] + pending_requirements[:limit])
    return [row for group in zip_longest(*by_mode) for row in group if row is not None]


def search_command(args, store, catalogue):
    started = monotonic()
    profile = store.profile(args.profile)
    jobs = store.jobs()
    analyser = lambda job: store.analyse(job, catalogue)
    modes = ["baseline", "task"] if args.mode == "both" else [args.mode]
    assessments = run_match(jobs, profile, catalogue, analyser=analyser)
    verification = {"vacancies": [], "public_gets": 0, "paid_api_spend": 0}
    if args.verify:
        order = prefer_rechecks([split_ranked(assessments, mode) for mode in modes], args.limit)
        verification = recheck_shortlist(store, order)
        assessments = run_match(store.jobs(), profile, catalogue, analyser=analyser)
    results = {}
    counts = {}
    for mode in modes:
        ranked = split_ranked(assessments, mode)
        results[mode] = {
            name: [as_record(row, profile, baseline=mode == "baseline") for row in rows[:args.limit]]
            for name, rows in ranked.items() if name != "excluded" or args.show_excluded
        }
        counts[mode] = {name: len(rows) for name, rows in ranked.items()}
    duration = round(monotonic() - started, 3)
    run_id = store.record_run(profile.id, {"command": "search", "counts": counts, "duration_seconds": duration,
                                         "public_gets": verification["public_gets"], "paid_api_spend": 0})
    output = {"run_id": run_id, "profile": profile.id, "corpus_vacancies": len(assessments),
              "catalogue_revision": catalogue.version, "mode": args.mode,
              "jobs": results, "counts": counts, "discovered_families": discover_families(profile, catalogue),
              "verification": verification, "duration_seconds": duration}
    if args.json:
        return output
    lines = [f"{len(assessments)} distinct vacancies assessed for {profile.id}."]
    families = output["discovered_families"]
    if families:
        lines.append("Role families to explore: " + ", ".join(row["label"] for row in families[:4]))
    for mode, categories in results.items():
        lines.append(f"\n{mode.capitalize()} ranking")
        for label, records in categories.items():
            if label == "excluded" and not records:
                continue
            lines.append(f"{label.capitalize()} ({len(records)} shown)")
            if records:
                lines.append(short_list(records))
    if args.verify:
        lines.append(f"Public HTTP requests: {verification['public_gets']}.")
    return "\n".join(lines)


def diagnostic_clock(value):
    if not value:
        return datetime.now(timezone.utc)
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def diagnostic_profile(profile_id, state):
    scenarios = load_demo()[0]
    if not profile_id:
        return scenarios[0]
    for profile in scenarios:
        if profile.id == profile_id:
            return profile
    if not (Path(state) / "profiles" / f"{identifier(profile_id)}.json").exists():
        raise ValueError("Unknown profile.")
    store = Storage(state)
    try:
        return store.profile(identifier(profile_id))
    finally:
        store.close()


def diagnostics_command(args, catalogue):
    profile = diagnostic_profile(args.profile, args.state)
    now = diagnostic_clock(args.at)
    if args.command == "heldout":
        return heldout_report(args.path, profile, catalogue, now)
    jobs = []
    if (Path(args.state) / "vacancies.sqlite").exists():
        store = Storage(args.state)
        try:
            jobs = store.jobs()
        finally:
            store.close()
    return coverage_report(jobs, profile, catalogue, now, title_pattern=args.titles)


def demo_command(args, catalogue):
    profiles, jobs, labels = load_demo()
    transfers = None
    if args.hybrid:
        transfers = accepted_by_profile(brief(profiles, jobs, catalogue), read_json(args.hybrid))
    if args.profile:
        profiles = [profile for profile in profiles if profile.id == args.profile]
        if not profiles:
            raise ValueError("Unknown fictional profile.")
    result = demo_comparison(profiles, jobs, labels, catalogue, args.limit, transfers)
    return result if args.json else demo_text(result, args.details)


def semantic_command(args, catalogue):
    profiles, jobs, _ = load_demo()
    request = brief(profiles, jobs, catalogue)
    if args.semantic_command == "prepare":
        if Path(args.output).exists():
            raise ValueError("Brief destination already exists.")
        write_private_json(Path(args.output), request)
        return f"Fictional evidence brief saved to {args.output}."
    if args.semantic_command == "inspect":
        response = read_json(args.proposals)
        return [{"number": ix, **row}
                for ix, row in enumerate(validated_proposals(request, response), 1)]
    if Path(args.output).exists():
        raise ValueError("Review destination already exists.")
    save_review(args.output, request, args.proposals, args.accept)
    return f"Reviewed fictional proposals saved to {args.output}."


def main_parser():
    parser = argparse.ArgumentParser(prog="python3 -m career_discovery")
    parser.add_argument("--state", default=".state", help="Local private data directory.")
    parser.add_argument("--catalogue", help="Use a different local task and role-family catalogue.")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Compare rankings over the labelled fictional fixtures.")
    demo.add_argument("--limit", type=int, choices=range(1, 6), default=5)
    demo.add_argument("--profile")
    demo.add_argument("--hybrid", help="Reviewed fictional semantic proposals.")
    demo.add_argument("--details", action="store_true")
    demo.add_argument("--json", action="store_true")
    profiles = commands.add_parser("profile", help="Create, review, export or delete a local profile.")
    actions = profiles.add_subparsers(dest="profile_command", required=True)
    for name in ("new", "import", "load", "show", "confirm", "export", "delete"):
        sub = actions.add_parser(name)
        sub.add_argument("id")
        if name in {"import", "load"}:
            sub.add_argument("document" if name == "import" else "file")
            sub.add_argument("--replace", action="store_true")
        if name == "export":
            sub.add_argument("output")
        if name == "delete":
            sub.add_argument("--yes", action="store_true", required=True)
    imp = commands.add_parser("import-jobs", help="Import a local vacancy CSV.")
    imp.add_argument("csv")
    imp.add_argument("--keep-description", action="store_true", help="Keep text you may store locally.")
    fresh = commands.add_parser("refresh", help="Read the selected public employer boards.")
    fresh.add_argument("boards")
    fresh.add_argument("--max-boards", type=int, choices=range(1, MAX_BOARDS + 1), default=MAX_BOARDS)
    listings = commands.add_parser("jobs", help="List stored vacancies and their source keys.")
    listings.add_argument("--all", action="store_true", help="Include records marked closed.")
    check = commands.add_parser("check-job", help="Record a manual check of the official application path.")
    check.add_argument("job", help="Canonical URL or exact job_key.")
    check.add_argument("status", choices=("open", "closed", "unverified"))
    verify = commands.add_parser("verify-job", help="Recheck a supported employer ATS application URL.")
    verify.add_argument("job", help="Canonical URL or exact job_key.")
    find = commands.add_parser("search", help="Rank the local vacancy corpus.")
    find.add_argument("--profile", required=True)
    find.add_argument("--mode", choices=("baseline", "task", "both"), default="task")
    find.add_argument("--limit", type=int, choices=range(1, 6), default=5)
    find.add_argument("--verify", action="store_true", help="Recheck eligible shortlists on supported ATS hosts.")
    find.add_argument("--show-excluded", action="store_true")
    find.add_argument("--json", action="store_true")
    discover = commands.add_parser("discover", help="Show task-backed role families from a reviewed profile.")
    discover.add_argument("--profile", required=True)
    feedback = commands.add_parser("feedback", help="Record a candidate's judgement locally.")
    feedback.add_argument("--profile", required=True)
    feedback.add_argument("--job", required=True, help="Canonical URL or exact job_key.")
    feedback.add_argument("--relevance", choices=("yes", "no", "uncertain"), required=True)
    feedback.add_argument("--would-consider", choices=("yes", "no", "uncertain"), required=True)
    feedback.add_argument("--new-to-me", choices=("yes", "no", "uncertain"), required=True)
    feedback.add_argument("--correction", default="")
    supply = commands.add_parser("supply", help="Capture or inspect fictional-scenario vacancy coverage.")
    supply.add_argument("--profile", help="Optional reviewed local profile for a one-off analysis.")
    supply.add_argument("--history", action="store_true")
    coverage = commands.add_parser("coverage", help="Aggregate duty and task coverage over the stored vacancies.")
    heldout = commands.add_parser("heldout", help="Score the parser against a labelled held-out vacancy file.")
    heldout.add_argument("path")
    for sub in (coverage, heldout):
        sub.add_argument("--profile", help="Fictional scenario or local profile ID. Defaults to the supply scenario.")
        sub.add_argument("--at", help="ISO 8601 clock for the assessment. Defaults to now.")
    coverage.add_argument("--titles", help="Only vacancies whose title matches this regular expression.")
    semantics = commands.add_parser("semantic", help="Exchange reviewed semantic proposals on fictional evidence.")
    semantics_commands = semantics.add_subparsers(dest="semantic_command", required=True)
    semantics_commands.add_parser("prepare").add_argument("output")
    semantics_commands.add_parser("inspect").add_argument("proposals")
    review = semantics_commands.add_parser("review")
    review.add_argument("proposals")
    review.add_argument("output")
    review.add_argument("--accept", type=int, nargs="*", required=True)
    pack = commands.add_parser("pilot-pack", help="Write an anonymous reviewer deck and a separate scoring key.")
    pack.add_argument("--profile", required=True)
    pack.add_argument("--participant", required=True)
    pack.add_argument("--output-dir", required=True)
    pack.add_argument("--limit", type=int, choices=range(1, 6), default=5)
    pack.add_argument("--full-corpus", action="store_true", help="Include every vacancy in a small frozen corpus.")
    app = commands.add_parser("app", help="Run the local web app on 127.0.0.1.")
    app.add_argument("--port", type=int, default=8765, help="First port to try. 0 lets the system choose.")
    app.add_argument("--no-browser", action="store_true", help="Do not open the browser.")
    app.add_argument("--state", dest="app_state", help="Data folder. Defaults to the per-user application folder.")
    app.add_argument("--smoke", action="store_true", help="Start, request the page once, print OK and exit.")
    evaluate = commands.add_parser("evaluate", help="Summarise locally collected, blind pilot judgements.")
    evaluate.add_argument("judgements")
    return parser


def state_command(args, store, catalogue):
    mode = args.command
    if mode == "profile":
        return profile_command(args, store, catalogue)
    if mode == "import-jobs":
        jobs = load_csv(args.csv, keep_description=args.keep_description)
        store.import_jobs(jobs)
        return {"imported": len(jobs), "kept_description_fields": args.keep_description}
    if mode == "refresh":
        report = refresh_boards(store, load_boards(args.boards), max_boards=args.max_boards)
        return report
    if mode == "jobs":
        return [{"job_key": job.key, "title": job.title, "company": job.company, "url": job.url,
                 "source": job.source, "availability": job.availability, "checked_at": job.checked_at}
                for job in store.jobs() if args.all or job.availability != "closed"]
    if mode == "check-job":
        job = find_job(store, args.job)
        status = "verified" if args.status == "open" else args.status
        updated = replace(job, availability=status, checked_at=utcnow().isoformat(),
                          verification_reason=f"{MANUAL_VERIFICATION_PREFIX}{args.status}.")
        if not store.update_status(job, updated):
            raise ValueError("The listing changed during verification. Recheck the current listing.")
        return {"job_key": job.key, "availability": status, "checked_at": updated.checked_at}
    if mode == "verify-job":
        job = find_job(store, args.job)
        if job.availability == "closed" or job.source not in {"ashby", "greenhouse"}:
            raise ValueError("Recheck a listed employer-feed vacancy or use check-job for a manual check.")
        client = PublicHTTP(budget=8)
        now = utcnow()
        reviewed = verify_job(job, client, now, store.recent_listing(job, now))
        if not store.update_status(job, reviewed):
            raise ValueError("The listing changed during verification. Recheck the current listing.")
        result = {"job_key": job.key, "availability": reviewed.availability, "checked_at": reviewed.checked_at,
                  "reason": reviewed.verification_reason, "public_gets": client.calls, "paid_api_spend": 0}
        store.record_run(None, {**result, "command": "verify-job"})
        return result
    if mode == "feedback":
        job = find_job(store, args.job)
        store.add_feedback(args.profile, job.key, {
            "relevance": args.relevance, "would_consider": args.would_consider, "new_to_me": args.new_to_me,
            "correction": clean_text(args.correction, "Correction", 1000),
        })
        return "Feedback saved locally."
    if mode == "search":
        return search_command(args, store, catalogue)
    if mode == "discover":
        profile = store.profile(args.profile)
        if not profile.confirmed:
            raise ValueError("Review and confirm the candidate profile before discovery.")
        return discover_families(profile, catalogue)
    if mode == "pilot-pack":
        profile = store.profile(args.profile)
        rows = run_match(store.jobs(), profile, catalogue, analyser=lambda job: store.analyse(job, catalogue))
        if not rows:
            raise ValueError("Add a vacancy corpus before preparing a review deck.")
        deck, key = prepare_review(rows, args.participant, limit=args.limit, full_corpus=args.full_corpus)
        target = Path(args.output_dir)
        target.mkdir(parents=True, mode=0o700, exist_ok=False)
        write_private_json(target / "review-deck.json", deck)
        write_private_json(target / "scoring-key.json", key)
        return f"Anonymous deck and separate scoring key saved to {target}."
    if mode == "supply":
        if args.history:
            return store.supply_history()
        scenario = store.profile(args.profile) if args.profile else load_demo()[0][0]
        return capture_supply(store, scenario, catalogue)
    raise ValueError("Unknown command.")


def main(arguments=None):
    parser = main_parser()
    args = parser.parse_args(arguments)
    store = None
    try:
        catalogue = load_catalogue(args.catalogue)
        if args.command == "demo":
            value = demo_command(args, catalogue)
        elif args.command == "semantic":
            value = semantic_command(args, catalogue)
        elif args.command in {"coverage", "heldout"}:
            value = diagnostics_command(args, catalogue)
        elif args.command == "app":
            from .webapp import run_app
            return run_app(args, args.catalogue)
        elif args.command == "evaluate":
            value = pilot_metrics(read_json(args.judgements))
        else:
            store = Storage(args.state)
            value = state_command(args, store, catalogue)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, sqlite3.Error) as exc:
        parser.exit(2, f"Error: {safe_text(str(exc))}\n")
    finally:
        if store:
            store.close()
    print(safe_text(value) if isinstance(value, str) else json_output(value))


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    main()
