"""Prepare a blind, anonymous reviewer deck and a separate method key."""

from .matching import split_ranked
from .models import fingerprint, identifier

REVIEW_FIELDS = (
    "relevant", "realistic", "hard_conflict", "open", "adjacent", "previously_known", "would_consider",
)
REVIEW_LANES = {"actionable_ids": "actionable", "review_first_ids": "verify first"}
FULL_CORPUS_LIMIT = 100


def prepare_review(rows, participant, *, limit=5, audit_sample=3, full_corpus=False):
    participant = identifier(participant)
    if full_corpus and len(rows) > FULL_CORPUS_LIMIT:
        raise ValueError(f"Use at most {FULL_CORPUS_LIMIT} vacancies for a full-corpus review.")
    rankings = {mode: split_ranked(rows, mode) for mode in ("baseline", "task")}
    selected = {mode: {key: ranking[lane][:limit] for key, lane in REVIEW_LANES.items()}
                for mode, ranking in rankings.items()}
    union = {row.job.key: row.job for lanes in selected.values() for results in lanes.values() for row in results}
    remaining = [row for row in rows if row.job.key not in union]
    seed = fingerprint([participant, sorted((row.job.key, fingerprint(row.job.description),
                                             row.job.availability, row.job.checked_at) for row in rows)])
    remaining.sort(key=lambda row: fingerprint([seed, row.job.key]))
    for row in remaining if full_corpus else remaining[:audit_sample]:
        union[row.job.key] = row.job
    ordered = sorted(union.values(), key=lambda job: fingerprint([seed, job.key]))
    ids = {job.key: f"j{index:03}" for index, job in enumerate(ordered, 1)}

    vacancies = [{"job_id": ids[job.key], "title": job.title, "company": job.company,
                  "locations": list(job.locations), "link": job.url, "apply_link": job.apply_url or job.url}
                 for job in ordered]
    judgements = [{"job_id": entry["job_id"], **dict.fromkeys(REVIEW_FIELDS)} for entry in vacancies]
    private_key = {
        "fixture": bool(rows and all(row.job.source == "fictional" for row in rows)),
        "corpus_size": len(rows), "snapshot": seed,
        "method_counts": {mode: {lane: len(ranks[lane]) for lane in REVIEW_LANES.values()}
                          for mode, ranks in rankings.items()},
        "participants": [{
            "id": participant, "would_reuse": None, "ran_again": None, "onboarding_minutes": None,
            "corpus_ids": list(ids.values()) if len(ids) == len(rows) else None,
            "methods": {mode: {**{key: [ids[row.job.key] for row in results] for key, results in lanes.items()},
                               "completed_searches": 1, "minutes_to_three": None}
                        for mode, lanes in selected.items()},
            "judgements": judgements,
        }],
    }
    return {"participant": participant, "vacancies": vacancies, "judgements": judgements}, private_key
