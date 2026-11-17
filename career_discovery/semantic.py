"""A provider-neutral, review-required exchange for fictional semantic experiments."""

from pathlib import Path

from .analysis import normal
from .matching import run_match
from .models import clean_text, fingerprint
from .storage import profile_data, read_json, write_private_json

VERSION = 1
MAX_PAIRS = 10
MAX_REQUIREMENTS = 40
MAX_PROPOSALS = 30


def brief(profiles, jobs, catalogue):
    if any(not profile.fictional or not profile.confirmed for profile in profiles):
        raise ValueError("Semantic briefs can only be created from reviewed fictional material.")
    if any(job.source != "fictional" for job in jobs):
        raise ValueError("Only fictional jobs can be included in a semantic brief.")
    pairs = []
    for profile in profiles:
        ranked = sorted(
            (row for row in run_match(jobs, profile, catalogue)
             if row.lane != "excluded" and (row.rank > 0 or row.baseline > 0)),
            key=lambda row: (-max(row.rank, 0) - row.baseline / 20, row.job.key),
        )
        for row in ranked[:MAX_PAIRS]:
            unresolved = {link.requirement_id for link in row.links if link.kind == "unverified"}
            requirements = [
                {"id": req.id, "excerpt": req.text, "candidate_task_ids": req.tasks or ("",)}
                for req in row.requirements if req.id in unresolved
            ][:MAX_REQUIREMENTS]
            if requirements:
                pairs.append({
                    "profile": profile.id, "profile_revision": fingerprint(profile_data(profile)),
                    "job_key": row.job.key, "job_revision": fingerprint(row.job.description),
                    "requirements": requirements,
                    "evidence": [{"id": e.id, "excerpt": e.text, "scope": e.scope}
                                 for e in profile.usable_evidence],
                })
    payload = {"version": VERSION, "catalogue_revision": catalogue.version, "pairs": pairs}
    return {**payload, "brief_id": fingerprint(payload)}


def validated_proposals(brief_data, response):
    if response.get("version") != VERSION or response.get("brief_id") != brief_data["brief_id"]:
        raise ValueError("Proposal file does not match the current fictional brief.")
    pairs = {(row["profile"], row["job_key"]): row for row in brief_data["pairs"]}
    proposals = response.get("proposals")
    if not isinstance(proposals, list) or len(proposals) > MAX_PROPOSALS:
        raise ValueError(f"Use at most {MAX_PROPOSALS} semantic proposals.")
    validated = []
    seen = set()
    for item in proposals:
        pair = pairs.get((item["profile"], item["job_key"]))
        if not pair:
            raise ValueError("Proposal refers outside the brief.")
        req = next((row for row in pair["requirements"] if row["id"] == item["requirement_id"]), None)
        evidence = next((e for e in pair["evidence"] if e["id"] == item["evidence_id"]), None)
        if (not req or not evidence or item["task_id"] not in req["candidate_task_ids"]
                or item.get("requirement_excerpt") != req["excerpt"]
                or item.get("evidence_excerpt") != evidence["excerpt"]):
            raise ValueError("A semantic proposal does not preserve the requirement and evidence references.")
        reason = clean_text(item.get("reason", ""), "Transfer rationale", 280, required=True)
        if normal(reason) == normal(evidence["excerpt"]):
            raise ValueError("Give a task analogy and explain its limits.")
        key = (item["profile"], item["job_key"], item["requirement_id"], item["task_id"])
        if key in seen:
            raise ValueError("Duplicate proposals for this requirement and task.")
        seen.add(key)
        validated.append({"profile": key[0], "job_key": key[1], "requirement_id": key[2], "task_id": key[3],
                          "evidence_id": evidence["id"], "reason": reason, "requirement_excerpt": req["excerpt"],
                          "evidence_excerpt": evidence["excerpt"]})
    return validated


def accepted_by_profile(brief_data, response):
    proposals = validated_proposals(brief_data, response)
    accepted = response.get("accepted")
    if not isinstance(accepted, list) or any(type(ix) is not int or not 1 <= ix <= len(proposals) for ix in accepted):
        raise ValueError("Supply the 1-based indices of manually reviewed and accepted proposals.")
    result = {}
    for index in set(accepted):
        proposal = proposals[index - 1]
        by_job = result.setdefault(proposal["profile"], {})
        by_requirement = by_job.setdefault(proposal["job_key"], {})
        by_requirement[(proposal["requirement_id"], proposal["task_id"])] = proposal
    return result


def save_review(path, brief_data, proposal_file, accepted):
    response = read_json(proposal_file)
    approved = {**response, "accepted": accepted}
    accepted_by_profile(brief_data, approved)
    write_private_json(Path(path), approved)
