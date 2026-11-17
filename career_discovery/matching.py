"""Rank comparable tasks and render a traceable, deterministic recommendation record."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta, timezone
from math import ceil
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .analysis import advert_language, analyse_description, contains, normal, task_tags
from .eligibility import eligibility
from .models import SUPERSEDED_AUTO_VERIFICATIONS, EvidenceLink, Finding, Job, Profile, Requirement

SENIOR_TITLE = re.compile(
    r"\b(?:senior|sr\.?|staff (?:engineer|analyst)|principal|director|head of|vice president|"
    r"lead (?:data|engineer|analyst)|engineering manager|team lead|founding engineer|teamleitung)\b", re.I,
)
EARLY_STAGE = re.compile(r"\b(?:early[- ]career|entry[- ]level|junior|graduate)\b", re.I)
VERIFICATION_TTL = timedelta(hours=24)
PARTIAL_FIT = "partial task evidence"
LEADERSHIP = re.compile(r"\b(?:own independently|own the|lead a team|manage direct reports|"
                        r"independently lead|eigenverantwortlich|personalverantwortung)\b", re.I)
OWNERSHIP = re.compile(r"\b(?:owned|led a team|managed direct reports|independently led|"
                       r"eigenverantwortlich|personalverantwortung)\b", re.I)


@dataclass
class Assessment:
    job: Job
    requirements: tuple[Requirement, ...]
    findings: tuple[Finding, ...]
    links: tuple[EvidenceLink, ...]
    families: tuple[str, ...]
    fit: str
    lane: str
    rank: float
    baseline: float
    growth: str = ""


def available(job, now):
    if job.availability == "fixture_open":
        return job.source == "fictional"
    if (job.availability != "verified" or not job.checked_at
            or job.verification_reason in SUPERSEDED_AUTO_VERIFICATIONS):
        return False
    checked = datetime.fromisoformat(job.checked_at.replace("Z", "+00:00"))
    return timedelta(0) <= now - checked <= VERIFICATION_TTL


def evidence_tags(profile, catalogue):
    return {e.id: task_tags(e.text, catalogue, evidence=True) for e in profile.usable_evidence}


def discover_families(profile, catalogue, tags=None):
    evidence = tags if tags is not None else evidence_tags(profile, catalogue)
    direct = {tag for tags in evidence.values() for tag in tags}
    family_rows = []
    for key, family in catalogue.families.items():
        matches = {task: [ident for ident, values in evidence.items() if task in values]
                   for task in family["tasks"] if task in direct}
        transfers = {
            task: [ident for ident, values in evidence.items()
                   if set(values) & catalogue.transfers.get(task, {}).keys()]
            for task in family["tasks"] if task not in matches
        }
        transfers = {task: ids for task, ids in transfers.items() if ids}
        if matches or transfers:
            family_rows.append({"id": key, "label": family["label"], "direct": matches,
                                "transferable": transfers,
                                "aliases": family["aliases"],
                                "open_tasks": [t for t in family["tasks"]
                                               if t not in matches and t not in transfers]})
    return sorted(family_rows, key=lambda row: (
        -len(row["direct"]), -len(row["transferable"]), row["id"] not in profile.interests, row["id"],
    ))


def job_families(job, requirements, catalogue):
    job_tasks = {task for req in requirements if req.kind == "core" for task in req.tasks}
    scores = {key: len(job_tasks.intersection(family["tasks"])) for key, family in catalogue.families.items()}
    best = max(scores.values(), default=0)
    if best:
        return tuple(key for key, score in scores.items() if score == best)
    return tuple(key for key, family in catalogue.families.items()
                 if any(contains(job.title, alias) for alias in family["aliases"]))


def links_for(requirement, profile, tags, catalogue, semantic):
    if not requirement.tasks and (pair := semantic.get((requirement.id, ""))):
        return [EvidenceLink(requirement.id, "transferable", pair["evidence_id"], pair["reason"])]
    if not requirement.tasks:
        return [EvidenceLink(requirement.id, "unverified", None, "No task mapping has been established.")]
    links = []
    for task in requirement.tasks:
        explicit_gap = any(normal(gap) == normal(task.replace("_", " "))
                           or any(contains(gap, alias) or contains(alias, gap)
                                  for alias in catalogue.tasks[task]) for gap in profile.known_gaps)
        if explicit_gap:
            links.append(EvidenceLink(requirement.id, "known_gap", None, f"Candidate-confirmed gap for {task}.", task))
            continue
        candidate_items = [e for e in profile.usable_evidence if task in tags[e.id]]
        high_scope = LEADERSHIP.search(requirement.text)
        direct_item = next((e for e in candidate_items if not high_scope
                            or OWNERSHIP.search(e.text + " " + e.scope)), None)
        if direct_item:
            links.append(EvidenceLink(requirement.id, "direct", direct_item.id,
                                      f"Evidence names the same task, {task.replace('_', ' ')}. "
                                      "Compare scope and context with the employer's wording.", task))
            continue
        if candidate_items:
            links.append(EvidenceLink(requirement.id, "partial", candidate_items[0].id,
                                      "Related task evidence. The stated ownership scope is unverified.", task))
            continue
        transfers = catalogue.transfers.get(task, {})
        analogue = next(((e, origin) for e in profile.usable_evidence for origin in tags[e.id]
                         if origin in transfers), None)
        if analogue:
            e, origin = analogue
            kind = "partial" if high_scope else "transferable"
            links.append(EvidenceLink(requirement.id, kind, e.id, transfers[origin], task))
        elif (pair := semantic.get((requirement.id, task))) and not high_scope:
            links.append(EvidenceLink(requirement.id, "transferable", pair["evidence_id"], pair["reason"], task))
        else:
            links.append(EvidenceLink(requirement.id, "unverified", None,
                                      f"Evidence for {task.replace('_', ' ')} was not found in the reviewed profile.", task))
    return links


def has_partial_coverage(links):
    supported = [link for link in links if link.task_id and link.kind in {"direct", "transferable"}]
    return (len({link.task_id for link in supported}) >= 2
            and len({link.requirement_id for link in supported}) >= 2
            and any(link.kind == "direct" for link in supported))


def _last_sunday(year, month):
    day = datetime(year, month, 31, 1, tzinfo=timezone.utc)
    return day - timedelta(days=(day.weekday() + 1) % 7)


def berlin_date(moment):
    """The calendar date in Berlin. Windows ships no time-zone database, so fall back to the EU rule:
    summer time (UTC+2) from 01:00 UTC on the last Sunday of March to 01:00 UTC on the last Sunday of October."""
    try:
        return moment.astimezone(ZoneInfo("Europe/Berlin")).date()
    except ZoneInfoNotFoundError:
        utc = moment.astimezone(timezone.utc)
        summer = _last_sunday(utc.year, 3) <= utc < _last_sunday(utc.year, 10)
        return (utc + timedelta(hours=2 if summer else 1)).date()


def assess(job, profile, catalogue, now, requirements=None, tags=None, semantic=None):
    requirements = analyse_description(job.description, catalogue) if requirements is None else requirements
    tags = evidence_tags(profile, catalogue) if tags is None else tags
    findings = list(eligibility(job, profile, requirements, catalogue, today=berlin_date(now)))
    if not available(job, now) and job.availability != "closed":
        findings.append(Finding("unknown", "availability", job.verification_reason,
                                "Confirm the official apply path before applying."))
    if not job.description:
        findings.append(Finding("unknown", "description", "", "A description is needed to assess fit."))
    families = job_families(job, requirements, catalogue)
    core = [requirement for requirement in requirements if requirement.kind == "core"]
    if len(core) < 2 and job.description:
        findings.append(Finding("unknown", "responsibility coverage", "",
                                "Too few distinct responsibilities were identified. Read the full description."))
    links = []
    units = []
    for req in core:
        mapped = links_for(req, profile, tags, catalogue, semantic or {})
        links.extend(mapped)
        kinds = {link.kind for link in mapped}
        if kinds == {"direct"}:
            units.append("direct")
        elif kinds <= {"direct", "transferable"}:
            units.append("transferable")
        elif kinds & {"direct", "transferable", "partial"}:
            units.append("partial")
        else:
            units.append("gap")
    direct = units.count("direct")
    transferred = units.count("transferable")
    partial = units.count("partial")
    matched = direct + transferred
    direct_capabilities = {link.task_id for link in links if link.task_id and link.kind == "direct"}
    supported_capabilities = {link.task_id for link in links if link.task_id
                              and link.kind in {"direct", "transferable"}}
    scope_confirmation = f"Seniority and ownership: {job.url}"
    if (EARLY_STAGE.search(profile.stage) and SENIOR_TITLE.search(job.title)
            and scope_confirmation not in profile.verified_requirements):
        findings.append(Finding("unknown", "seniority and ownership", job.title,
                                "Check the expected seniority and ownership with the employer."))
    if len(core) > 1 and matched > 1 and supported_capabilities and len(supported_capabilities) < 2:
        findings.append(Finding("unknown", "responsibility coverage", "",
                                "Several duties point to the same supported capability. Check the remaining scope."))
    if not core:
        fit = "insufficient evidence"
    elif len(direct_capabilities) >= 2 and direct >= len(core) - 1 and matched == len(core):
        fit = "strong fit"
    elif transferred and matched >= max(2, ceil(len(core) / 2)):
        fit = "transferable opportunity"
    elif matched and matched + partial >= ceil(len(core) / 2):
        fit = "stretch opportunity"
    elif has_partial_coverage(links):
        fit = PARTIAL_FIT
    else:
        fit = "insufficient evidence"
    title_hits = sum(1 for title in profile.search_titles if contains(job.title, title))
    keyword_hits = sum(1 for kw in profile.keywords if contains(f"{job.title}\n{job.description}", kw))
    baseline = 4 * title_hits + keyword_hits
    interest = any(key in profile.interests for key in families)
    rank = (3 * direct + 2 * transferred + partial - units.count("gap")) / max(1, len(core))
    rank += 0.15 * bool(interest)
    if any(result.state == "conflict" for result in findings):
        lane = "excluded"
    elif any(result.state == "unknown" for result in findings):
        lane = "verify first"
    else:
        lane = "actionable"
    growth = ""
    for req, unit in zip(core, units):
        if len(units) > 1 and (matched or partial) and unit in {"gap", "partial"}:
            growth = "Potential development area from the listed responsibilities — " + req.text
            break
    return Assessment(job, requirements, tuple(findings), tuple(links), families, fit, lane, rank, baseline, growth)


def deduplicate(jobs):
    """Use exact vacancy URLs. Keep different requisitions with the same title."""
    groups = {}
    for job in jobs:
        groups.setdefault(job.url, []).append(job)
    for duplicates in groups.values():
        yield sorted(duplicates, key=lambda job: (
            job.source not in {"greenhouse", "ashby"},
            job.availability == "unverified",
            not bool(job.description),
            job.key,
        ))[0]


def possible_duplicates(jobs):
    groups = {}
    for job in jobs:
        key = (normal(job.company), normal(job.title), tuple(sorted(map(normal, job.locations))))
        groups.setdefault(key, []).append(job)
    return [[job.key for job in variants] for variants in groups.values() if len(variants) > 1]


def split_ranked(assessments, mode):
    if mode == "baseline":
        ranked = sorted((row for row in assessments if row.baseline > 0),
                        key=lambda row: (-row.baseline, row.job.key))
    else:
        ranked = []
        for row in assessments:
            if row.fit == "insufficient evidence":
                continue
            if row.fit == PARTIAL_FIT and row.lane != "excluded":
                scope = Finding("unknown", "task coverage", "",
                                "Some responsibilities have evidence. The overall task coverage needs review.")
                row = replace(row, lane="verify first", findings=(*row.findings, scope))
            ranked.append(row)
        ranked.sort(key=lambda row: (row.fit == PARTIAL_FIT, -row.rank, row.job.key))
    return {lane: [row for row in ranked if row.lane == lane]
            for lane in ("actionable", "verify first", "excluded")}


def run_match(jobs, profile: Profile, catalogue, now=None, analyser=None, semantic=None):
    if not profile.confirmed:
        raise ValueError("Review and confirm the candidate profile before matching.")
    now = now or datetime.now(timezone.utc)
    tags = evidence_tags(profile, catalogue)
    return [assess(job, profile, catalogue, now,
                   requirements=analyser(job) if analyser else None,
                   tags=tags, semantic=(semantic or {}).get(job.key))
            for job in deduplicate(jobs)]


def as_record(row, profile, *, baseline=False):
    evidence = {e.id: e for e in profile.usable_evidence}
    explanations = []
    for link in row.links if not baseline else ():
        data = asdict(link)
        if link.evidence_id:
            data["evidence"] = asdict(evidence[link.evidence_id])
        explanations.append(data)
    return {
        "job_key": row.job.key, "company": row.job.company, "title": row.job.title,
        "url": row.job.url, "apply_url": row.job.apply_url or row.job.url,
        "source": row.job.source, "locations": row.job.locations,
        "remote_regions": row.job.remote_regions, "workplace": row.job.workplace,
        "employment": row.job.employment, "date": row.job.listed_date, "date_kind": row.job.date_kind,
        "apparent_ad_language": advert_language(row.job.description),
        "availability": row.job.availability, "checked_at": row.job.checked_at,
        "verification_reason": row.job.verification_reason,
        "lane": row.lane, "fit": "title and keyword match" if baseline else row.fit,
        "families": row.families, "findings": [asdict(item) for item in row.findings],
        "requirements": [asdict(req) for req in row.requirements], "evidence_links": explanations,
        "growth": "" if baseline else row.growth,
    }
