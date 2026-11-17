"""Resolve only explicit conditions against information supplied by the candidate."""

from datetime import date
from dataclasses import replace
import re

from .analysis import NEGATION, NO_LANGUAGE, OPTIONAL, asserted_phrase, contains, normal
from .models import CEFR, Finding

LANGUAGES = {
    "de": ("german", "deutsch", "deutsche", "deutschen", "deutschkenntnisse"),
    "en": ("english", "englisch", "englische", "englischen", "englischkenntnisse"),
    "fr": ("french", "französisch", "französische"),
    "es": ("spanish", "spanisch", "spanische"),
}
LANGUAGE_TERMS = {word: code for code, names in LANGUAGES.items() for word in names}
LANGUAGE_RE = re.compile(r"\b(?:" + "|".join(LANGUAGE_TERMS) + r")\b", re.I)
LEVEL = re.compile(r"\b(?:[ABC][12])\b", re.I)
LANGUAGE_SIGNAL = re.compile(r"\b(?:fluen\w*|native|proficien\w*|language|speaking|"
                             r"verhandlungssicher\w*|muttersprach\w*|fließend\w*|kenntnisse|"
                             r"mindestens|level|niveau|sprachkenntnisse|\w+kenntnisse)\b", re.I)
SHARED_LEVEL = re.compile(r"-\s*(?:und|and|oder|or|/)\s*", re.I)
EACH_LEVEL = re.compile(r"\b(?:jeweils|each|both|beide|beides|respectively)\b", re.I)
YEARS = re.compile(r"\b(\d{1,2})\s*\+?\s*(?:(?:-|–|to|bis)\s*\d{1,2}\s*)?"
                   r"(?:years?|jahre[n]?)\b\s*(?:of |an )?(.{0,55}?)"
                   r"\b(?:experienc\w*|erfahrung|berufserfahrung)\b", re.I)
POST_TENURE_SCOPE = re.compile(r"^\s*(?:(?:[,:(]\s*)?(?:with|using|in|working with|working in|mit|im|in der)\s+"
                               r"|\s*\(\s*)(.+?)\s*$", re.I)
UNSCOPED_TENURE = {"", "relevant", "professional", "work", "relevant professional", "berufs"}
UPPER_TENURE = re.compile(r"\b(?:up to|at most|no more than|maximum(?: of)?|bis zu|höchstens)$", re.I)
TENURE_QUALIFIER = re.compile(r"\s+(?:(?:is|are)\s+)?(?:required|preferred|mandatory|"
                              r"(?:a\s+)?minimum|erforderlich|vorausgesetzt)\s*[.!]?$", re.I)
REQUIRED_JOIN = re.compile(r"(?<=\brequired)\s+with\s+|(?<=\bmandatory)\s+with\s+", re.I)
CLEARANCE = re.compile(r"\b(?:security clearance|background (?:check|screening)|"
                       r"sicherheitsüberprüfung|zuverlässigkeitsüberprüfung)\b", re.I)
ENROLMENT = re.compile(r"\b(?:enroll(?:ed|ment)|ein(?:ge)?schrieben|immatrikulier\w*|"
                       r"current student|student status)\b", re.I)
GRADUATE = re.compile(r"\b(?:recent graduate|new graduate|kürzlich.{0,15}abschluss|"
                       r"hochschulabsolvent)\w*\b", re.I)
NO_SPONSORSHIP = re.compile(r"\b(?:no (?:visa )?sponsorship|(?:cannot|can't|unable to|do not|will not)"
                            r".{0,22}sponsor|sponsorship.{0,18}(?:unavailable|not available))\b", re.I)
AUTH = re.compile(r"\b(?:work authori[sz]ation|right to work|work permit|arbeitserlaubnis|"
                  r"arbeitsgenehmigung|visa sponsorship|sponsorship)\b", re.I)
OPEN_POOL = re.compile(r"\b(?:talent pool|talent community|spontaneous application|"
                       r"general application|initiativbewerbung)\b", re.I)
OR = re.compile(r"\s+(?:or|oder)\s+(?!(?:higher|above|better|more|greater|höher|mehr|besser|darüber|[ABC][12])\b)", re.I)
AND = re.compile(r"(?<!-)\s+(?:and|und)\s+|,\s*(?=(?:German|English|Deutsch|Englisch)\b)", re.I)
BARE_LANGUAGE_END = re.compile(r"\b(?:" + "|".join(LANGUAGE_TERMS) + r")$", re.I)
LANGUAGE_START = re.compile(r"^(?:" + "|".join(LANGUAGE_TERMS) + r")\b", re.I)


def and_split(clause):
    """Split on and/und, but keep two bare language terms together so a level after the second is not lost."""
    parts = AND.split(clause)
    merged = [parts[0]]
    for part in parts[1:]:
        if BARE_LANGUAGE_END.search(merged[-1]) and LANGUAGE_START.match(part):
            merged[-1] = f"{merged[-1]} and {part}"
        else:
            merged.append(part)
    return merged
COUNTRY_ALIASES = {
    "germany": "de", "deutschland": "de", "de": "de", "european union": "eu", "eu": "eu",
    "usa": "us", "united states": "us", "us": "us", "united kingdom": "gb", "uk": "gb",
    "great britain": "gb", "gb": "gb", "austria": "at", "österreich": "at", "at": "at",
    "global": "global", "worldwide": "global",
}


def conjunction_state(findings):
    states = {finding.state for finding in findings}
    return "conflict" if "conflict" in states else "unknown" if "unknown" in states else "met"


def location_matches(raw, accepted):
    raw_key = normal(raw)
    parts = {COUNTRY_ALIASES.get(normal(part), normal(part)) for part in re.split(r"[,/|]", raw)}
    for value in accepted:
        key = normal(value)
        canonical = COUNTRY_ALIASES.get(key)
        if canonical in parts or key == raw_key or (not canonical and contains(raw, value)):
            return True
    return False


def location_finding(job, profile):
    if not profile.locations and not profile.remote_regions:
        return None
    if job.workplace == "remote":
        if not profile.remote_regions:
            return Finding("conflict", "location", "Remote role", "Profile does not include remote work.")
        if not job.remote_regions:
            return Finding("unknown", "location", "Remote role", "The eligible country or region is unstated.")
        stated = {COUNTRY_ALIASES.get(normal(region), normal(region)) for region in job.remote_regions}
        allowed = {COUNTRY_ALIASES.get(normal(region), normal(region)) for region in profile.remote_regions}
        match = bool(stated & allowed or "global" in stated or "eu" in stated and {"de", "at"} & allowed)
        return Finding("met" if match else "conflict", "location", ", ".join(job.remote_regions),
                       "The role's stated remote geography was compared with the profile.")
    if any(location_matches(place, profile.locations) for place in job.locations):
        return Finding("met", "location", ", ".join(job.locations), "Matches a location in the profile.")
    if not job.locations:
        return Finding("unknown", "location", "", "The listing does not identify a work location.")
    return Finding("conflict", "location", ", ".join(job.locations), "Outside the locations in the profile.")


def language_findings(text, profile):
    matches = list(LANGUAGE_RE.finditer(text))
    if not matches or not (LEVEL.search(text) or LANGUAGE_SIGNAL.search(text)):
        return []
    levels = list(LEVEL.finditer(text))
    assigned = {}
    for level in levels:
        language = min(matches, key=lambda m: abs((m.start() + m.end()) - (level.start() + level.end())))
        key = language.start()
        earlier = assigned.get(key)
        if earlier and re.fullmatch(r"\s*(?:/|–|-|or|oder|to|bis)\s*", text[earlier.end():level.start()], re.I):
            # A stated range allows the lower level. Keep its original span for the reason text.
            assigned[key] = min((earlier, level), key=lambda value: CEFR.index(value.group().upper()))
        else:
            assigned[key] = level
    for first, second in zip(matches, matches[1:]):
        # "Deutsch- und Englischkenntnisse C1": a shared level covers both coordinated languages.
        if (first.start() not in assigned and second.start() in assigned
                and SHARED_LEVEL.fullmatch(text[first.end():second.start()])):
            assigned[first.start()] = assigned[second.start()]
    if EACH_LEVEL.search(text) and len({level.group().upper() for level in levels}) == 1:
        # "Deutsch und Englisch (jeweils mindestens B2)": one stated level applies to every named language.
        for language in matches:
            assigned.setdefault(language.start(), levels[0])
    findings = []
    for language in matches:
        code = LANGUAGE_TERMS[language.group().casefold()]
        level = assigned.get(language.start())
        required = level.group().upper() if level else None
        actual = profile.languages.get(code)
        if required and actual:
            state = "met" if CEFR.index(actual) >= CEFR.index(required) else "conflict"
            reason = f"The profile lists {LANGUAGES[code][0].title()} at {actual.upper()}. The ad specifies {required}."
        else:
            state = "unknown"
            reason = f"Check the ad's exact {LANGUAGES[code][0].title()} requirement against your own level."
        findings.append(Finding(state, f"language ({code})", text, reason))
    return findings


def explicit_status(text, profile):
    findings = []
    if ENROLMENT.search(text) and not re.search(r"\b(?:no|not|without|kein\w*).{0,15}enroll", text, re.I):
        value = profile.enrolled
        state = "met" if value is True else "conflict" if value is False else "unknown"
        findings.append(Finding(state, "enrolment", text, "Compared with user-supplied enrolment status."))
    if GRADUATE.search(text):
        value = profile.recent_graduate
        has_window = re.search(r"\b(?:\d+\s*(?:months?|years?|monate|jahre)|20\d\d|within|seit)\b", text, re.I)
        state = "conflict" if value is False else "met" if value is True and not has_window else "unknown"
        findings.append(Finding(state, "graduate status", text, "Verify the employer's graduation window."))
    if NO_SPONSORSHIP.search(text):
        answer = profile.needs_sponsorship
        state = "conflict" if answer is True else "unknown" if answer is None else "met"
        findings.append(Finding(state, "sponsorship", text,
                                "Compared with the candidate's own answer about needing sponsorship."))
    elif AUTH.search(text):
        findings.append(Finding("unknown", "work authorisation", text,
                                "Confirm the employer's condition and your situation yourself."))
    return findings


def clause_findings(text, profile, catalogue):
    # An unnegated mention in the clause is needed before imposing a known gap.
    if any(asserted_phrase(text, gap) for gap in profile.known_gaps):
        return [Finding("conflict", "known gap", text, "The candidate records this as a known gap.")]
    findings = language_findings(text, profile) + explicit_status(text, profile)
    years = list(YEARS.finditer(text))
    for match in years:
        scope = normal(match.group(2))
        raw_tail = text[match.end():]
        post_scope = POST_TENURE_SCOPE.match(TENURE_QUALIFIER.sub("", raw_tail).strip())
        if post_scope:
            post = normal(post_scope.group(1))
            scope = post if scope in UNSCOPED_TENURE else f"{scope} with {post}"
        tail = normal(TENURE_QUALIFIER.sub("", raw_tail))
        if scope in UNSCOPED_TENURE and tail:
            scope = "unspecified scope"
        before = text[:match.start()].casefold().rstrip()
        if UPPER_TENURE.search(before):
            findings.append(Finding("unknown", "experience", text, "The stated duration is an upper bound. "
                                    "Verify how the employer interprets it."))
            continue
        key = "relevant" if scope in UNSCOPED_TENURE else next(
            (tool for tool, aliases in catalogue.tools.items() if scope in map(normal, aliases)), scope,
        )
        supplied = {normal(k): v for k, v in profile.experience_months.items()}
        months = supplied.get(key)
        required = int(match.group(1)) * 12
        state = "unknown" if months is None else "met" if months >= required else "conflict"
        findings.append(Finding(state, "experience", text,
                                f"Minimum of {required} months in {key} experience. "
                                + ("Comparable tenure is unconfirmed." if months is None
                                   else f"The user supplied {months} months.")))
    tools = [tool for tool, aliases in catalogue.tools.items() if any(contains(text, t) for t in aliases)]
    if not years and tools:
        for tool in tools:
            explicit = any(normal(tool) == normal(item) for item in profile.verified_requirements)
            evidence = any(any(asserted_phrase(item.text, term) for term in catalogue.tools[tool])
                           for item in profile.usable_evidence)
            scope_required = re.search(r"\b(?:professional|commercial|production|certif\w*|expert|advanced|"
                                       r"strong|hands[- ]on|complex|optimi[sz]\w*|independent\w*|ownership)\b",
                                       text, re.I)
            state = "met" if (explicit or evidence) and not scope_required else "unknown"
            findings.append(Finding(state, tool, text, "Tool evidence and any stated depth were checked."))
    if CLEARANCE.search(text):
        findings.append(Finding("unknown", "clearance", text, "Check the exact clearance or screening condition."))
    if re.search(r"\b(?:degree|bachelor|master'?s|abschluss|certification|licen[cs]e|approbation)\b", text, re.I):
        findings.append(Finding("unknown", "credential", text, "Confirm the exact credential and any equivalency."))
    if (any(normal(item) == normal(text) for item in profile.verified_requirements)
            and all(finding.state != "conflict" for finding in findings)):
        return [Finding("met", "confirmed requirement", text, "The candidate explicitly confirmed this line.")]
    return findings or [Finding("unknown", "requirement", text, "The available evidence does not resolve this condition.")]


def tenure_parts(text, catalogue):
    """Carry a shared duration only to a clearly named tool or candidate tenure scope."""
    scopes = {normal(alias) for values in catalogue.tools.values() for alias in values}
    found = YEARS.search(text)
    if found and not YEARS.search(text, found.end()):
        before = text[:found.start()]
        upper = UPPER_TENURE.search(before.rstrip())
        duration = text[found.start():found.start(2)]
        shared_duration = f"{upper.group()} {duration}" if upper else duration
        prefix_scope = found.group(2).strip()
        chunks = re.split(r"(\s+(?:and|or|und|oder)\s+)", prefix_scope, flags=re.I)
        if len(chunks) > 1 and all(normal(chunk) in scopes for chunk in chunks[::2]):
            expanded = [f"{duration if index == 0 else shared_duration}{chunk} experience"
                        for index, chunk in enumerate(chunks[::2])]
            return text[:found.start()] + "".join(
                part for pair in zip(expanded, [*chunks[1::2], ""]) for part in pair
            ) + text[found.end():]
        if POST_TENURE_SCOPE.match(text[found.end():]):
            suffix = re.split(r"(\s+(?:and|or|und|oder)\s+)", text[found.end():], flags=re.I)
            for index in range(2, len(suffix), 2):
                if normal(TENURE_QUALIFIER.sub("", suffix[index])) in scopes:
                    suffix[index] = f"{shared_duration}experience with {suffix[index]}"
            return text[:found.end()] + "".join(suffix)
    return text


def unclear_language_findings(text, profile):
    """An unclear line can still state a level. Optional wording keeps a mismatch open rather than excluding."""
    findings = language_findings(text, profile)
    if not OPTIONAL.search(text):
        return findings
    return [replace(item, state="unknown", reason=item.reason + " Optional wording makes the requirement unclear.")
            if item.state == "conflict" else item for item in findings]


def check_requirement(requirement, profile, catalogue):
    text = requirement.text
    if requirement.kind == "preferred":
        return (Finding("preferred", "preference", text, "Treated as preferred by the wording or section."),)
    confirmed = any(normal(item) == normal(text) for item in profile.verified_requirements)
    if requirement.kind == "unclear":
        if confirmed:
            return (Finding("met", "confirmed requirement", text, "The candidate explicitly confirmed this line."),)
        return (Finding("unknown", "requirement intent", text,
                        "Check what the employer means by this line."),
                *unclear_language_findings(text, profile))
    alternatives = OR.split(tenure_parts(text, catalogue))
    groups = [tuple(found for part in and_split(clause) for condition in REQUIRED_JOIN.split(part)
                    for found in clause_findings(condition, profile, catalogue))
              for clause in alternatives]
    if len(groups) > 1:
        ratings = [conjunction_state(group) for group in groups]
        state = ("met" if "met" in ratings else "unknown" if "unknown" in ratings else "conflict")
        if confirmed and state != "conflict":
            return (Finding("met", "confirmed requirement", text, "The candidate explicitly confirmed this line."),)
        return (Finding(state, "alternative paths", text, " ".join(
            f"Path {index}: {rating}. " + " ".join(item.reason for item in group)
            for index, (rating, group) in enumerate(zip(ratings, groups), 1)
        )),)
    if confirmed and all(finding.state != "conflict" for finding in groups[0]):
        return (Finding("met", "confirmed requirement", text, "The candidate explicitly confirmed this line."),)
    return groups[0]


def eligibility(job, profile, requirements, catalogue, today=None):
    today = today or date.today()
    findings = []
    if job.deadline and date.fromisoformat(job.deadline) < today:
        findings.append(Finding("conflict", "deadline", job.deadline, "The stated deadline has passed."))
    if job.availability == "closed":
        findings.append(Finding("conflict", "listing", "", "The source marked this vacancy closed."))
    if OPEN_POOL.search(job.title) and not re.search(r"\btalent (?:pool|community)\s+(?:manager|lead|specialist)\b",
                                                      job.title, re.I):
        findings.append(Finding("conflict", "listing", job.title, "This appears to be a general talent pool."))
    location = location_finding(job, profile)
    if location:
        findings.append(location)
    if profile.employment:
        if job.employment:
            state = "met" if job.employment in profile.employment else "conflict"
            findings.append(Finding(state, "employment", job.employment, "Compared with allowed employment types."))
        else:
            findings.append(Finding("unknown", "employment", "", "The source does not specify employment type."))
    if job.employment == "working_student" and profile.enrolled is not True:
        state = "conflict" if profile.enrolled is False else "unknown"
        findings.append(Finding(state, "enrolment", "Working student position", "Verify current student status."))
    for req in requirements:
        if req.kind != "core":
            findings.extend(check_requirement(req, profile, catalogue))
        else:
            if NO_SPONSORSHIP.search(req.text) or AUTH.search(req.text):
                findings.extend(explicit_status(req.text, profile))
            if LEVEL.search(req.text) and not (NEGATION.search(normal(req.text)) or NO_LANGUAGE.search(req.text)):
                findings.extend(replace(item, state="unknown", reason=item.reason + " The line describes a duty.")
                                if item.state == "conflict" else item
                                for item in language_findings(req.text, profile))
    return tuple(findings)
