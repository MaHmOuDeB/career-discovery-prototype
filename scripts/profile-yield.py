"""Compare supply yield for fictional profiles on the frozen pilot pool. Offline; aggregate counts only.

Run from the project root:  python3 -B scripts/profile-yield.py [--state .state/pilot] [--at ISO8601]
It works on a temporary copy of the state folder, so the dated supply history and analysis cache stay untouched.
Profiles: the demo scenario graduate plus every profile in fixtures/supply-profiles.json.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from career_discovery.analysis import ANALYSER_VERSION, load_catalogue  # noqa: E402
from career_discovery.demo import load_demo  # noqa: E402
from career_discovery.matching import evidence_tags, run_match  # noqa: E402
from career_discovery.models import Profile  # noqa: E402
from career_discovery.sourcing import supply_review_reasons  # noqa: E402
from career_discovery.storage import Storage  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default=str(ROOT / ".state" / "pilot"))
    parser.add_argument("--at", default="2026-11-16T22:52:55+00:00")
    args = parser.parse_args()
    now = datetime.fromisoformat(args.at)
    catalogue = load_catalogue()
    extra = json.loads((ROOT / "fixtures" / "supply-profiles.json").read_text("utf-8"))
    profiles = [load_demo()[0][0], *(Profile.load(item) for item in extra)]
    with tempfile.TemporaryDirectory(prefix="cd-yield-") as folder:
        copy = Path(folder) / "state"
        shutil.copytree(args.state, copy)
        store = Storage(str(copy))
        try:
            scope = {tuple(item) for item in store.current_board_scope(now)}
            jobs = [job for job in store.jobs() if job.availability != "closed"
                    and (job.source, job.board) in scope and store.recent_listing(job, now)]
            report = {"at": now.isoformat(), "analyser": ANALYSER_VERSION, "catalogue": catalogue.version,
                      "jobs": len(jobs), "profiles": []}
            for profile in profiles:
                rows = run_match(jobs, profile, catalogue, now, analyser=lambda job: store.analyse(job, catalogue))
                reasons = [supply_review_reasons(row) for row in rows]
                clear = [row for row in rows if not any(item.state == "conflict" for item in row.findings)]
                report["profiles"].append({
                    "id": profile.id, "evidence_items": len(profile.usable_evidence),
                    "evidence_tasks": sorted({tag for tags in evidence_tags(profile, catalogue).values() for tag in tags}),
                    "plausible": sum(not item for item in reasons),
                    "no_hard_conflict": len(clear),
                    "fit_without_hard_conflict": dict(Counter(row.fit for row in clear).most_common()),
                    "held_back": dict(Counter(reason for item in reasons for reason in item).most_common(8)),
                })
        finally:
            close = getattr(store, "close", None)
            if close:
                close()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
