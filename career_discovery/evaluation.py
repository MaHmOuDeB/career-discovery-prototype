"""Offline comparison and pilot scoring with explicit denominators."""

from datetime import datetime, timezone
from statistics import median

from .analysis import contains
from .matching import as_record, run_match, split_ranked
from .models import identifier


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "rate": round(numerator / denominator, 4) if denominator else None}


def demo_comparison(profiles, jobs, labels, catalogue, limit=5, semantic=None):
    results = []
    # A fixed clock makes fixture results reproducible.
    now = datetime(2026, 11, 16, tzinfo=timezone.utc)
    for profile in profiles:
        assessments = run_match(jobs, profile, catalogue, now)
        positive = set(labels[profile.id])
        modes = ["baseline", "task"]
        enriched = run_match(jobs, profile, catalogue, now, semantic=semantic.get(profile.id, {})) if semantic is not None else None
        if enriched is not None:
            modes.append("hybrid")
        row = {"profile": profile.id, "judged_pairs": len(assessments)}
        for mode in modes:
            ranking = split_ranked(enriched if mode == "hybrid" else assessments, mode)
            selected = ranking["actionable"][:limit]
            identifiers = [item.job.external_id for item in selected]
            row[mode] = {
                "jobs": [as_record(item, profile, baseline=mode == "baseline") for item in selected],
                "precision": ratio(sum(job in positive for job in identifiers), len(identifiers)),
                "false_positive_rate": ratio(sum(job not in positive for job in identifiers),
                                             len(assessments) - len(positive)),
                "verify_first": len(ranking["verify first"]),
                "excluded": len(ranking["excluded"]),
            }
            if mode != "baseline":
                already = {item["job_key"] for item in row["baseline"]["jobs"]}
                row[mode]["scenario_discoveries"] = [
                    item.job.title for item in selected
                    if item.job.external_id in positive and item.job.key not in already
                    and not any(contains(item.job.title, title) for title in profile.search_titles)
                ]
        results.append(row)
    totals = {}
    for mode in ("baseline", "task", "hybrid"):
        if any(mode in row for row in results):
            values = [row[mode]["precision"] for row in results if mode in row]
            totals[mode] = ratio(sum(value["numerator"] for value in values),
                                 sum(value["denominator"] for value in values))
    return {"kind": "fictional scenario comparison", "shortlist_size": limit,
            "profiles": results, "pooled_precision": totals}


def _count(field, data):
    value = data.get(field, 0)
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be a nonnegative integer.")
    return value


def _int_or_none(field, data):
    return _count(field, data) if data.get(field) is not None else None


def _is_relevant(row):
    return row.get("relevant") is True and row.get("realistic") is True


def _is_negative(row):
    return row.get("relevant") is False or row.get("realistic") is False


def _bool_or_unknown(data, fields):
    if any(data.get(field) is not None and type(data[field]) is not bool for field in fields):
        raise ValueError("Judgement flags must be true, false or null.")


def lane_metrics(rows):
    relevant = sum(_is_relevant(row) for row in rows)
    relevance_labelled = sum(_is_relevant(row) or _is_negative(row) for row in rows)
    conflict_labelled = sum(row.get("hard_conflict") is not None for row in rows)
    open_labelled = sum(row.get("open") is not None for row in rows)
    slots = len(rows)
    return {
        "filled_slots": slots,
        "label_status": ("empty" if not slots else "complete"
                         if relevance_labelled == conflict_labelled == open_labelled == slots else "incomplete"),
        "label_coverage": {
            "relevance": ratio(relevance_labelled, slots),
            "eligibility": ratio(conflict_labelled, slots),
            "links": ratio(open_labelled, slots),
        },
        "precision": ratio(relevant, relevance_labelled),
        "hard_conflict_rate": ratio(sum(row.get("hard_conflict") is True for row in rows), conflict_labelled),
        "verified_link_rate": ratio(sum(row.get("open") is True for row in rows), open_labelled),
    }


def ranked_ids(method, field, judgements):
    ids = method.get(field, [])
    if (not isinstance(ids, list) or len(ids) > 5 or any(not isinstance(key, str) for key in ids)
            or len(ids) != len(set(ids))):
        raise ValueError(f"Use up to five distinct vacancy IDs in {field}.")
    if not set(ids).issubset(judgements):
        raise ValueError("Every displayed vacancy requires a judgement record.")
    return ids


def pilot_metrics(data):
    """Read anonymous human judgements. Empty metrics remain undefined."""
    participants = data.get("participants")
    if not isinstance(participants, list) or len(participants) > 100:
        raise ValueError("Use a participants array with at most 100 anonymous records.")
    ids = set()
    pooled = {}
    by_participant = []
    reuse = []
    ran_again = []
    time_savings = []
    onboarding_minutes = []
    for participant in participants:
        ident = identifier(participant["id"])
        if ident in ids:
            raise ValueError("Participant IDs must be unique.")
        ids.add(ident)
        _bool_or_unknown(participant, ("would_reuse", "ran_again"))
        if participant.get("would_reuse") is not None:
            reuse.append(participant["would_reuse"])
        if participant.get("ran_again") is not None:
            ran_again.append(participant["ran_again"])
        if (onboarding := _int_or_none("onboarding_minutes", participant)) is not None:
            onboarding_minutes.append(onboarding)
        judgements = {}
        for row in participant.get("judgements", []):
            key = row["job_id"]
            if not isinstance(key, str) or not key or key in judgements:
                raise ValueError("Each participant needs one judgement per nonempty vacancy ID.")
            _bool_or_unknown(row, ("relevant", "realistic", "hard_conflict", "open", "adjacent",
                                   "previously_known", "would_consider"))
            judgements[key] = row
        methods = participant.get("methods", {})
        if not {"baseline", "task"}.issubset(methods):
            raise ValueError("Each participant requires baseline and task results.")
        negative_count = sum(_is_negative(row) for row in judgements.values())
        corpus_ids = participant.get("corpus_ids")
        if corpus_ids is not None and (not isinstance(corpus_ids, list)
                or any(not isinstance(key, str) for key in corpus_ids)
                or len(corpus_ids) != len(judgements) or set(corpus_ids) != judgements.keys()):
            raise ValueError("Full-corpus IDs must correspond one-to-one with judgement rows.")
        complete_corpus = corpus_ids is not None and all(
            _is_relevant(row) or _is_negative(row) for row in judgements.values()
        )
        positives = {key for key, row in judgements.items() if _is_relevant(row)}
        discovery = []
        participant_report = {
            "id": ident, "labelled_negatives": negative_count, "methods": {},
            "complete_corpus_relevance_labels": complete_corpus,
            "relevance_label_coverage": ratio(len(positives) + negative_count, len(judgements)),
        }
        for method_name, method in methods.items():
            if method_name not in {"baseline", "task", "hybrid", "manual", "competitor"}:
                raise ValueError("Unknown pilot method.")
            shown = ranked_ids(method, "actionable_ids", judgements)
            verify_first = ranked_ids(method, "review_first_ids", judgements)
            if set(shown).intersection(verify_first):
                raise ValueError("A vacancy can enter only one lane per method.")
            reviewed = [judgements[key] for key in shown]
            review_stats = lane_metrics([judgements[key] for key in verify_first])
            if complete_corpus:
                review_stats["relevant_coverage"] = ratio(len(positives.intersection(verify_first)), len(positives))
            claims = _count("claims_audited", method)
            supported = _count("claims_supported", method)
            fabricated = _count("fabricated_claims", method)
            if supported + fabricated > claims:
                raise ValueError("Claim counts exceed the number of audited claims.")
            memberships = {
                **lane_metrics(reviewed),
                "false_positive_rate": ratio(sum(_is_negative(row) for row in reviewed), negative_count),
                "explanation_accuracy": ratio(supported, claims),
            }
            candidates = [
                key for key in shown
                if key not in methods["baseline"].get("actionable_ids", [])
                and _is_relevant(judgements[key])
                and judgements[key].get("hard_conflict") is False
                and all(judgements[key].get(flag) is True for flag in ("open", "adjacent", "would_consider"))
                and judgements[key].get("previously_known") is False
            ]
            if method_name == "task":
                discovery = candidates
            participant_report["methods"][method_name] = {
                **memberships, "verify_first": review_stats, "useful_discoveries": candidates,
                "actionable_relevant_coverage": ratio(len(positives.intersection(shown)), len(positives))
                if complete_corpus else None,
                "missed_relevant_ids": sorted(positives.difference(shown, verify_first)) if complete_corpus else None,
                "unresolved_eligibility": sum(row.get("hard_conflict") is None for row in reviewed),
                "unverified_links": sum(row.get("open") is None for row in reviewed),
                "fabricated_claims": fabricated, "paid_spend_usd_micros": _count("paid_spend_usd_micros", method),
                "completed_searches": _count("completed_searches", method),
                "minutes_to_three": _int_or_none("minutes_to_three", method),
            }
            pooled.setdefault(method_name, []).append(participant_report["methods"][method_name])
        manual_time = participant_report["methods"].get("manual", {}).get("minutes_to_three")
        task_time = participant_report["methods"]["task"]["minutes_to_three"]
        if manual_time is not None and task_time is not None:
            time_savings.append(manual_time - task_time)
        participant_report["task_useful_discoveries"] = discovery
        by_participant.append(participant_report)
    joined = {}
    for name, rows in pooled.items():
        metrics = {metric: ratio(sum(row[metric]["numerator"] for row in rows),
                                 sum(row[metric]["denominator"] for row in rows)) for metric in
                   ("precision", "hard_conflict_rate", "false_positive_rate", "verified_link_rate",
                    "explanation_accuracy")}
        spend = sum(row["paid_spend_usd_micros"] for row in rows)
        completed = sum(row["completed_searches"] for row in rows)
        joined[name] = {
            **metrics, "spend_usd_micros": spend, "completed_searches": completed,
            "actionable_label_coverage": {
                label: ratio(sum(row["label_coverage"][label]["numerator"] for row in rows),
                             sum(row["label_coverage"][label]["denominator"] for row in rows))
                for label in ("relevance", "eligibility", "links")
            },
            "verify_first_filled_slots": sum(row["verify_first"]["filled_slots"] for row in rows),
            "usd_per_search": round(spend / 1_000_000 / completed, 6) if completed else None,
            "fabricated_claims": sum(row["fabricated_claims"] for row in rows),
            "unresolved_eligibility": sum(row["unresolved_eligibility"] for row in rows),
            "participants_with_three_links": sum(row["minutes_to_three"] is not None for row in rows),
            "participants": len(rows),
        }
    return {
        "kind": "human pilot summary", "participants": by_participant, "methods": joined,
        "participants_with_task_discovery": ratio(sum(bool(row["task_useful_discoveries"]) for row in by_participant),
                                                  len(by_participant)),
        "median_paired_minutes_saved": median(time_savings) if time_savings else None,
        "paired_time_sessions": len(time_savings),
        "median_onboarding_minutes": median(onboarding_minutes) if onboarding_minutes else None,
        "would_reuse": ratio(sum(reuse), len(reuse)),
        "ran_again": ratio(sum(ran_again), len(ran_again)),
    }
