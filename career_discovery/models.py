"""Input contracts shared by the CLI, adapters and matcher."""

from dataclasses import dataclass, field
from datetime import date, datetime
import hashlib
import json
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SCHEMA_VERSION = 1
CEFR = ("A1", "A2", "B1", "B2", "C1", "C2")
EVIDENCE_STATES = {"cv_stated", "user_confirmed", "inferred", "missing"}
AVAILABILITY = {"fixture_open", "listed", "verified", "closed", "unverified"}
LEGACY_AUTO_VERIFICATION = "Present in a recent employer feed and the specific application URL responded."
HEADING_ONLY_VERIFICATION = "Recent employer listing and matching job page with an application action."
SUPERSEDED_AUTO_VERIFICATIONS = {LEGACY_AUTO_VERIFICATION, HEADING_ONLY_VERIFICATION}
MANUAL_VERIFICATION_PREFIX = "User recorded a manual check as "
FEED_REMOVAL = "No longer present in the last complete successful employer snapshot."
EMPLOYMENT = {
    "full_time", "part_time", "internship", "working_student", "freelance",
    "contract", "temporary", "trainee",
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
        raise ValueError("Identifiers must be 1–64 lowercase ASCII letters, digits, hyphens or underscores.")
    return value


def canonical_url(value):
    value = value.strip()
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
    except ValueError as exc:
        raise ValueError("Invalid listing URL.") from exc
    if (parts.scheme != "https" or not host or port not in (None, 443)
            or parts.username or parts.password or "\\" in value or any(c.isspace() for c in value)):
        raise ValueError("Listing URLs must be public HTTPS URLs without credentials or custom ports.")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host) or "." not in host:
        raise ValueError("Invalid listing hostname.")
    query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                   if not k.lower().startswith("utm_") and k.lower() not in {"gclid", "fbclid", "gh_src", "source"})
    return urlunsplit(("https", host, parts.path.rstrip("/") or "/", urlencode(query), ""))


def string_list(value, label):
    if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
        raise ValueError(f"{label} must be a list of nonempty strings.")
    return list(dict.fromkeys(s.strip() for s in value))


def clean_text(value, label, limit, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValueError(f"{label} must be text of at most {limit} characters.")
    return value.strip()


@dataclass(frozen=True)
class Evidence:
    id: str
    text: str
    locator: str
    state: str
    context: str = ""
    scope: str = ""

    @classmethod
    def load(cls, data):
        state = data["state"]
        if state not in EVIDENCE_STATES:
            raise ValueError(f"Unsupported evidence state: {state!r}.")
        return cls(identifier(data["id"]),
                   clean_text(data.get("text", ""), "Evidence text", 2000, state != "missing"),
                   clean_text(data.get("locator", ""), "Evidence locator", 200, state != "missing"),
                   state, clean_text(data.get("context", ""), "Context", 100),
                   clean_text(data.get("scope", ""), "Scope", 200))


@dataclass(frozen=True)
class Profile:
    id: str
    confirmed: bool
    fictional: bool
    evidence: tuple[Evidence, ...]
    search_titles: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    interests: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    remote_regions: list[str] = field(default_factory=list)
    employment: list[str] = field(default_factory=list)
    languages: dict[str, str] = field(default_factory=dict)
    experience_months: dict[str, int] = field(default_factory=dict)
    known_gaps: list[str] = field(default_factory=list)
    verified_requirements: list[str] = field(default_factory=list)
    stage: str = ""
    enrolled: bool | None = None
    recent_graduate: bool | None = None
    needs_sponsorship: bool | None = None
    document_hash: str | None = None

    @classmethod
    def load(cls, data):
        if data.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("Unsupported profile schema version.")
        for key in ("confirmed", "fictional"):
            if type(data.get(key, False)) is not bool:
                raise ValueError(f"{key} must be true or false.")
        evidence = tuple(Evidence.load(e) for e in data.get("evidence", []))
        if len(evidence) > 200 or len({e.id for e in evidence}) != len(evidence):
            raise ValueError("Use at most 200 evidence items with unique IDs.")
        languages = data.get("languages", {})
        if not isinstance(languages, dict) or any(
            not re.fullmatch(r"[a-z]{2,3}", k) or v not in CEFR for k, v in languages.items()
        ):
            raise ValueError("Use lowercase language codes and CEFR levels, for example de and B1.")
        experience = data.get("experience_months", {})
        if not isinstance(experience, dict) or any(
            not isinstance(k, str) or not k.strip() or type(v) is not int or not 0 <= v <= 960
            for k, v in experience.items()
        ):
            raise ValueError("Experience values must be user-supplied months between 0 and 960.")
        optional = {key: data.get(key) for key in ("enrolled", "recent_graduate", "needs_sponsorship")}
        if any(v is not None and type(v) is not bool for v in optional.values()):
            raise ValueError("Eligibility answers must be true, false or null.")
        lists = {key: string_list(data.get(key, []), key) for key in
                 ("search_titles", "keywords", "interests", "locations", "remote_regions",
                  "employment", "known_gaps", "verified_requirements")}
        if set(lists["employment"]) - EMPLOYMENT:
            raise ValueError(f"Employment choices: {', '.join(sorted(EMPLOYMENT))}.")
        if {x.casefold() for x in lists["known_gaps"]} & {x.casefold() for x in lists["verified_requirements"]}:
            raise ValueError("A requirement cannot be both confirmed and a known gap.")
        document_hash = data.get("document_hash")
        if document_hash is not None and not re.fullmatch(r"[a-f0-9]{64}", document_hash):
            raise ValueError("Invalid document fingerprint.")
        return cls(identifier(data["id"]), data.get("confirmed", False), data.get("fictional", False),
                   evidence, **lists, languages=languages, experience_months=experience,
                   stage=clean_text(data.get("stage", ""), "Stage", 80),
                   document_hash=document_hash, **optional)

    @property
    def usable_evidence(self):
        if not self.confirmed:
            return ()
        return tuple(e for e in self.evidence if e.state in {"cv_stated", "user_confirmed"})


def employer_position_type(title):
    """Distinguish an internship or traineeship from its full-time schedule."""
    programme_staff = re.search(r"\b(?:internship|intern|trainee)\s+(?:program(?:me)?|recruitment|coordinator|manager)\b",
                                title, re.I)
    internship = bool(re.search(r"\b(?:intern|internship|praktikum|praktikant\w*)\b", title, re.I))
    student = bool(re.search(r"\b(?:working student|werkstudent\w*)\b", title, re.I))
    if student and internship:
        return ""
    if student:
        return "working_student"
    if internship and not programme_staff:
        return "internship"
    if re.search(r"\btrainee\b", title, re.I) and not programme_staff:
        return "trainee"
    return None


@dataclass(frozen=True)
class Job:
    source: str
    board: str
    external_id: str
    company: str
    title: str
    url: str
    apply_url: str = ""
    description: str = ""
    locations: tuple[str, ...] = ()
    workplace: str = ""
    remote_regions: tuple[str, ...] = ()
    employment: str = ""
    listed_date: str | None = None
    date_kind: str = ""
    deadline: str | None = None
    availability: str = "unverified"
    checked_at: str | None = None
    verification_reason: str = ""

    @classmethod
    def load(cls, data):
        attrs = dict(data)
        attrs["url"] = canonical_url(attrs["url"])
        if attrs.get("apply_url"):
            attrs["apply_url"] = canonical_url(attrs["apply_url"])
        for label in ("source", "board", "external_id", "company", "title"):
            attrs[label] = clean_text(attrs[label], label, 250, required=True)
        attrs["description"] = clean_text(attrs.get("description", ""), "Description", 100_000)
        for label in ("locations", "remote_regions"):
            attrs[label] = tuple(string_list(attrs.get(label, []), label))
        if attrs.get("availability") == "verified" and attrs.get("verification_reason") in SUPERSEDED_AUTO_VERIFICATIONS:
            attrs["availability"] = "unverified"
            attrs["verification_reason"] = "Earlier automatic verification lacks a current application-control check. Recheck the apply path."
        if attrs.get("availability", "unverified") not in AVAILABILITY:
            raise ValueError("Invalid vacancy availability.")
        if attrs.get("workplace", "") not in {"", "remote", "hybrid", "onsite"}:
            raise ValueError("Invalid workplace type.")
        if attrs["source"] in {"ashby", "greenhouse"}:
            title_type = employer_position_type(attrs["title"])
            if title_type is not None:
                attrs["employment"] = title_type
        if attrs.get("employment", "") not in EMPLOYMENT | {""}:
            raise ValueError("Invalid employment type.")
        if attrs.get("date_kind", "") not in {"", "posted", "updated", "last_published"}:
            raise ValueError("Invalid vacancy date type.")
        if bool(attrs.get("date_kind")) != bool(attrs.get("listed_date")):
            raise ValueError("Supply the date and its meaning together.")
        for key in ("listed_date", "deadline", "checked_at"):
            value = attrs.get(key)
            if value:
                if key == "checked_at":
                    if datetime.fromisoformat(value.replace("Z", "+00:00")).utcoffset() is None:
                        raise ValueError("Verification timestamps must include a timezone.")
                elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                    raise ValueError("Vacancy dates must use YYYY-MM-DD.")
                else:
                    date.fromisoformat(value)
        return cls(**attrs)

    @property
    def manually_checked(self):
        return self.verification_reason.startswith(MANUAL_VERIFICATION_PREFIX)

    @property
    def key(self):
        return json.dumps([self.source, self.board, self.external_id], ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class Requirement:
    id: str
    kind: str
    text: str
    tasks: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    state: str
    subject: str
    excerpt: str
    reason: str


@dataclass(frozen=True)
class EvidenceLink:
    requirement_id: str
    kind: str
    evidence_id: str | None
    rationale: str
    task_id: str | None = None
