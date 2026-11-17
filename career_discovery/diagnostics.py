"""Read-only coverage and held-out diagnostics. Reports carry counts, never vacancy text from real listings."""

from collections import Counter
import json
from pathlib import Path
import re

from .analysis import analyse_description, normal
from .matching import run_match
from .models import CEFR, Job
from .sourcing import supply_review_reasons

LANGUAGE_SUBJECT = re.compile(r"^language \(\w+\)$")


def rate(numerator, denominator):
    return round(numerator / denominator, 3) if denominator else 0.0


def coverage_report(jobs, profile, catalogue, now, analyser=None, title_pattern=None):
    try:
        pattern = re.compile(title_pattern, re.I) if title_pattern else None
    except re.error as exc:
        raise ValueError(f"Invalid --titles regular expression: {exc}") from exc
    chosen = [job for job in jobs if job.availability != "closed" and (not pattern or pattern.search(job.title))]
    analyser = analyser or (lambda job: analyse_description(job.description, catalogue))
    rows = run_match(chosen, profile, catalogue, now, analyser=analyser)
    duties = [[req for req in row.requirements if req.kind == "core"] for row in rows]
    flagged = [(row, supply_review_reasons(row)) for row in rows]
    plausible = [row for row, reasons in flagged if not reasons]
    lines = sum(len(group) for group in duties)
    mapped = sum(1 for group in duties for req in group if req.tasks)
    return {
        "jobs": len(rows),
        "zero_duty_jobs": sum(len(group) == 0 for group in duties),
        "one_duty_jobs": sum(len(group) == 1 for group in duties),
        "duty_lines": lines,
        "mapped_duty_lines": mapped,
        "mapped_rate": rate(mapped, lines),
        "task_counts": dict(Counter(task for group in duties for req in group for task in req.tasks).most_common()),
        "fit_counts": dict(Counter(row.fit for row in rows).most_common()),
        "lane_counts": dict(Counter(row.lane for row in rows).most_common()),
        "review_reason_counts": dict(Counter(reason for _, reasons in flagged for reason in reasons).most_common()),
        "plausible": len(plausible),
        "plausible_companies": len({row.job.company for row in plausible}),
        "language_conflicts": sum(any(f.state == "conflict" and LANGUAGE_SUBJECT.match(f.subject)
                                      for f in row.findings) for row in rows),
    }


def fictional_job(item):
    return Job.load({
        "source": "fictional", "board": "heldout", "external_id": item["id"], "company": item["company"],
        "title": item["title"], "url": f"https://vacancies.example/heldout/{item['id']}",
        "description": item["description"], "locations": item.get("locations", []),
        "employment": item.get("employment", ""), "availability": "fixture_open",
    })


def matching_requirements(text, requirements):
    needle = normal(text)
    if not needle:
        return []
    return [req for req in requirements if normal(req.text) and (needle in normal(req.text) or normal(req.text) in needle)]


def prf(true_positive, predicted, expected):
    precision, recall = rate(true_positive, predicted), rate(true_positive, expected)
    f1 = round(2 * precision * recall / (precision + recall), 3) if precision + recall else 0.0
    return {"precision": precision, "recall": recall, "f1": f1,
            "true_positive": true_positive, "predicted": predicted, "expected": expected}


def kind_of(matches):
    kinds = {req.kind for req in matches}
    return "core" if "core" in kinds else next(iter(sorted(kinds)), None)


def heldout_report(path, profile, catalogue, now):
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    duties_total = duties_detected = qualifications_total = leaks = 0
    expected_conflicts = detected_conflicts = unexpected_conflicts = 0
    counts = Counter()
    misses = []
    for item in items:
        job = fictional_job(item)
        row = run_match([job], profile, catalogue, now,
                        analyser=lambda current: analyse_description(current.description, catalogue))[0]
        for duty in item.get("duties", []):
            duties_total += 1
            matches = matching_requirements(duty["text"], row.requirements)
            expected = set(duty.get("tasks", []))
            got = {task for req in matches for task in req.tasks}
            core = any(req.kind == "core" for req in matches)
            duties_detected += core
            for task in expected | got:
                counts[task, "predicted"] += task in got
                counts[task, "expected"] += task in expected
                counts[task, "true_positive"] += task in got and task in expected
            if not core or got != expected:
                misses.append({"id": item["id"], "text": duty["text"],
                               "expected": {"kind": "core", "tasks": sorted(expected)},
                               "got": {"kind": kind_of(matches), "tasks": sorted(got)}})
        for qualification in item.get("qualifications", []):
            qualifications_total += 1
            matches = matching_requirements(qualification["text"], row.requirements)
            if any(req.kind == "core" for req in matches):
                leaks += 1
                misses.append({"id": item["id"], "text": qualification["text"],
                               "expected": {"kind": qualification["kind"], "tasks": []},
                               "got": {"kind": "core", "tasks": sorted({t for r in matches for t in r.tasks})}})
        conflicts = {f.subject for f in row.findings if f.state == "conflict" and LANGUAGE_SUBJECT.match(f.subject)}
        expected_subjects = set()
        for need in item.get("language_requirements", []):
            actual = profile.languages.get(need["language"])
            if need.get("mandatory") and actual and CEFR.index(need["level"].upper()) > CEFR.index(actual):
                expected_subjects.add(f"language ({need['language']})")
        expected_conflicts += len(expected_subjects)
        detected_conflicts += len(expected_subjects & conflicts)
        unexpected_conflicts += len(conflicts - expected_subjects)
    tasks = sorted({task for task, _ in counts})
    per_task = {task: prf(counts[task, "true_positive"], counts[task, "predicted"], counts[task, "expected"])
                for task in tasks}
    totals = [sum(counts[task, key] for task in tasks) for key in ("true_positive", "predicted", "expected")]
    return {
        "vacancies": len(items),
        "duties_total": duties_total,
        "duties_detected": duties_detected,
        "qualifications_total": qualifications_total,
        "qualification_leaks": leaks,
        "tasks": {"overall": prf(*totals), "per_task": per_task},
        "language_conflicts_expected": expected_conflicts,
        "language_conflicts_detected": detected_conflicts,
        "language_conflicts_unexpected": unexpected_conflicts,
        "misses": misses,
    }
