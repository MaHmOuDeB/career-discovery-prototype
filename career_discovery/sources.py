"""Normalise CSV rows and documented Greenhouse and Ashby public responses."""

import csv
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from html import unescape
from html.parser import HTMLParser
from io import StringIO
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

from .analysis import normal
from .models import Job, canonical_url, employer_position_type, fingerprint
from .network import ATS_HOSTS, API_HOSTS, NetworkUnavailable
from .storage import CACHE_WINDOW
from .storage_limits import read_bytes

ATS = {"greenhouse", "ashby"}
CSV_MAX_ROWS = 2000
CLOSED = re.compile(r"\b(?:no longer accepting applications|this (?:position|job|posting) "
                    r"(?:has been filled|is closed|is no longer available|was not found)|"
                    r"applications (?:are|have been) (?:now )?closed|"
                    r"applications are no longer being accepted|"
                    r"this (?:vacancy|listing|posting) has (?:now )?(?:expired|closed)|"
                    r"(?:diese (?:stelle|position) ist|dieses stellenangebot ist) nicht mehr verfügbar)\b", re.I)
BLOCKED = re.compile(r"\b(?:verify you are human|access denied|enable javascript and cookies to continue)\b", re.I)
APPLY_ACTION = re.compile(r"\b(?:apply for this (?:job|role|position)|apply now|submit application|"
                          r"bewerbung einreichen|jetzt bewerben|für diese stelle bewerben)\b", re.I)
REMOTE_PATTERNS = {
    "de": r"\b(?:Germany|Deutschland|DE)\b",
    "eu": r"\bEU\b|\bEuropean Union\b",
    "us": r"\bUnited States\b|\bUS\b|\bUSA\b",
    "gb": r"\bUnited Kingdom\b|\bUK\b",
    "at": r"\bAustria\b|\bÖsterreich\b",
    "global": r"\bworldwide\b|\banywhere in the world\b",
}
EMPLOYMENT_TAG = {
    "fulltime": "full_time", "parttime": "part_time", "intern": "internship", "internship": "internship",
    "contract": "contract", "temporary": "temporary", "freelance": "freelance", "workingstudent": "working_student",
    "werkstudent": "working_student", "trainee": "trainee", "vollzeit": "full_time", "teilzeit": "part_time",
}


@dataclass(frozen=True)
class Board:
    ats: str
    slug: str
    company: str

    @property
    def url(self):
        if self.ats == "greenhouse":
            return f"https://boards-api.greenhouse.io/v1/boards/{self.slug}/jobs?content=true"
        return f"https://api.ashbyhq.com/posting-api/job-board/{self.slug}"


def load_boards(path):
    data = json.loads(read_bytes(Path(path), 200_000))
    if not isinstance(data, list) or len(data) > 40:
        raise ValueError("Use a board list with up to 40 entries.")
    seen = set()
    result = []
    for item in data:
        if item.get("ats") not in ATS or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", item.get("slug", "")):
            raise ValueError("A board must have a supported ATS and a public board slug.")
        board = Board(item["ats"], item["slug"], item["company"].strip())
        key = (board.ats, board.slug.casefold())
        if key in seen or not board.company:
            raise ValueError("Board slugs must be unique and company names are required.")
        seen.add(key)
        if item.get("local_use_reviewed") is True:
            result.append(board)
    return result


class VisibleText(HTMLParser):
    BREAKS = {"p", "div", "li", "br", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "section", "tr", "article"}
    EXCLUDED = {"script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.EXCLUDED:
            self.hidden += 1
        if self.hidden == 0 and tag in self.BREAKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.EXCLUDED and self.hidden:
            self.hidden -= 1
        if self.hidden == 0 and tag in self.BREAKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if self.hidden == 0:
            self.parts.append(data)


def html_text(fragment):
    parser = VisibleText()
    parser.feed(unescape(fragment))
    parser.close()
    return "\n".join(clean for line in "".join(parser.parts).splitlines()
                     if (clean := re.sub(r"[ \t\u00a0]+", " ", line).strip()))


def employment_type(value, title, description):
    specific = employer_position_type(title)
    if specific is not None:
        return specific
    source_type = EMPLOYMENT_TAG.get(re.sub("[^a-z]", "", value.casefold()), "")
    if source_type:
        return source_type
    match = re.search(r"\b(?:employment type|employment|anstellungsart)\s*:\s*"
                      r"(full[- ]time|part[- ]time|internship|freelance|vollzeit|teilzeit)\b", description, re.I)
    return EMPLOYMENT_TAG.get(re.sub("[^a-z]", "", match.group(1).casefold()), "") if match else ""


def remote_regions(text):
    regions = tuple(key for key, pattern in REMOTE_PATTERNS.items() if re.search(pattern, text, re.I))
    # A country mentioned in an exception or a negated policy needs reading by the candidate.
    return () if re.search(r"\b(?:except|excluding|only outside|not available|ausgenommen)\b", text, re.I) else regions


def infer_workplace(locations):
    labels = " ".join(locations)
    if re.search(r"\bhybrid\b", labels, re.I):
        return "hybrid"
    if re.search(r"\b(?:remote|homeoffice)\b", labels, re.I):
        return "remote"
    if re.search(r"\bon[- ]?site\b|\bvor ort\b", labels, re.I):
        return "onsite"
    return ""


def feed_date(raw, kind):
    return (raw[:10], kind) if isinstance(raw, str) and raw else (None, "")


def greenhouse_job(row, board):
    title = row["title"]
    description = html_text(row.get("content") or "")[:100_000]
    place = (row.get("location") or {}).get("name")
    locations = [place] if place else []
    workplace = infer_workplace(locations)
    listed_date, date_kind = feed_date(row.get("updated_at"), "updated")
    metadata_types = {"employment type", "employment", "job type", "contract type", "anstellungsart"}
    source_type = next((str(field.get("value") or "") for field in row.get("metadata") or []
                        if str(field.get("name") or "").strip().casefold() in metadata_types), "")
    return Job.load({"source": board.ats, "board": board.slug, "external_id": str(row["id"]),
                     "company": board.company, "title": title, "url": row["absolute_url"],
                     "apply_url": row["absolute_url"], "description": description,
                     "locations": locations, "workplace": workplace,
                     "remote_regions": list(remote_regions(" ".join(locations))) if workplace == "remote" else [],
                     "employment": employment_type(source_type, title, description),
                     "listed_date": listed_date, "date_kind": date_kind, "availability": "listed"})


def ashby_location(name, address):
    address = (address or {}).get("postalAddress", address) or {}
    country = address.get("addressCountry")
    if name and country and not re.search(r"\b" + re.escape(country) + r"\b", name, re.I):
        return f"{name}, {country}"
    return name or country or ""


def ashby_job(row, board):
    description = (row.get("descriptionPlain") or html_text(row.get("descriptionHtml") or ""))[:100_000]
    workplace = str(row.get("workplaceType") or "").casefold()
    places = [ashby_location(row.get("location"), row.get("address"))]
    secondary_locations = row.get("secondaryLocations") or []
    places.extend(ashby_location(place.get("location"), place.get("address")) for place in secondary_locations)
    locations = list(dict.fromkeys(place for place in places if place))
    if workplace not in {"onsite", "remote", "hybrid"}:
        workplace = infer_workplace(locations)
    listed_date, date_kind = feed_date(row.get("publishedAt"), "last_published")
    url = canonical_url(row["jobUrl"])
    external_id = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
    if not external_id:
        raise ValueError("Ashby record has no job ID in its URL.")
    return Job.load({"source": board.ats, "board": board.slug, "external_id": external_id,
                     "company": board.company, "title": row["title"], "url": url,
                     "apply_url": row.get("applyUrl") or "", "workplace": workplace,
                     "locations": locations, "description": description,
                     "remote_regions": list(remote_regions(" ".join(locations))) if workplace == "remote" else [],
                     "employment": employment_type(row.get("employmentType") or "", row["title"], description),
                     "listed_date": listed_date, "date_kind": date_kind, "availability": "listed"})


def parse_board(body, board):
    data = json.loads(body)
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("Feed response did not contain the documented jobs array.")
    records = {}
    for item in data["jobs"]:
        if board.ats == "ashby":
            if type(item.get("isListed")) is not bool:
                raise ValueError("Ashby did not return a valid public-listing flag.")
            if not item["isListed"]:
                continue
            job = ashby_job(item, board)
        else:
            job = greenhouse_job(item, board)
        if job.key in records and job != records[job.key]:
            raise ValueError("Source returned conflicting entries for a vacancy ID.")
        records[job.key] = job
    return list(records.values())


def load_csv(path, *, keep_description):
    data = read_bytes(Path(path), 12 * 1024 * 1024).decode("utf-8-sig")
    reader = csv.DictReader(StringIO(data, newline=""))
    if not {"company", "title", "url"}.issubset(reader.fieldnames or []):
        raise ValueError("CSV needs company, title and url columns.")
    result = {}
    for index, row in enumerate(reader, 2):
        if index - 1 > CSV_MAX_ROWS:
            raise ValueError(f"CSV exceeds {CSV_MAX_ROWS} data rows.")
        if None in row:
            raise ValueError(f"CSV row {index} has too many fields.")
        try:
            def get(key):
                return (row.get(key) or "").strip()

            url = canonical_url(get("url"))
            job = Job.load({"source": "csv", "board": "import", "external_id": get("external_id") or fingerprint(url),
                            "company": get("company"), "title": get("title"), "url": url,
                            "apply_url": get("apply_url"), "description": get("description") if keep_description else "",
                            "locations": [part.strip() for part in get("locations").split("|") if part.strip()],
                            "workplace": get("workplace"),
                            "remote_regions": [part.strip() for part in get("remote_regions").split("|") if part.strip()],
                            "employment": get("employment"), "listed_date": get("listed_date") or None,
                            "date_kind": get("date_kind"), "deadline": get("deadline") or None})
            if job.key in result and result[job.key] != job:
                raise ValueError("Conflicting rows share the same external ID.")
            result[job.key] = job
        except (TypeError, ValueError) as exc:
            raise ValueError(f"CSV row {index}: {exc}") from exc
    return list(result.values())


def automatic_apply_url(job):
    target = job.apply_url or job.url
    if job.source not in ATS:
        return None
    parts = urlsplit(target)
    id_present = job.external_id in parts.path.split("/") or job.external_id in parse_qs(parts.query).get("gh_jid", [])
    if parts.hostname in ATS_HOSTS - API_HOSTS and id_present:
        return target
    return None


class ApplicationPage(VisibleText):
    HEADINGS = {"h1", "h2", "h3"}
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
            "meta", "param", "source", "track", "wbr"}
    FORM_ANCHORS = {"application", "application-form", "app"}
    HIDDEN_STYLE = re.compile(r"\b(?:display\s*:\s*none|visibility\s*:\s*hidden)\b", re.I)

    def __init__(self, job, target):
        super().__init__()
        self.job = job
        self.target = target
        self.hidden_tags = []
        self.heading = None
        self.control = None
        self.title_matches = False
        self.enabled_button = False
        self.apply_link = False
        self.named_forms = set()
        self.linked_forms = set()

    @property
    def enabled_action(self):
        return self.enabled_button or self.apply_link or bool(self.named_forms & self.linked_forms)

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        hidden = (tag in self.EXCLUDED or "hidden" in fields or fields.get("aria-hidden") == "true"
                  or self.HIDDEN_STYLE.search(fields.get("style") or ""))
        if self.hidden_tags or hidden or (tag == "fieldset" and "disabled" in fields):
            if tag not in self.VOID:
                self.hidden_tags.append(tag)
            return
        super().handle_starttag(tag, attrs)
        if tag in self.HEADINGS:
            self.heading = (tag, [])
        if tag == "form" and fields.get("id") in self.FORM_ANCHORS:
            self.named_forms.add(fields["id"])
        if (tag in {"a", "button"} and "disabled" not in fields
                and fields.get("aria-disabled") != "true"):
            self.control = (tag, fields.get("href"), [])

    def handle_data(self, data):
        if self.hidden_tags:
            return
        super().handle_data(data)
        if self.heading is not None:
            self.heading[1].append(data)
        if self.control is not None:
            self.control[2].append(data)

    def handle_endtag(self, tag):
        if self.hidden_tags:
            if tag in self.hidden_tags:
                while self.hidden_tags.pop() != tag:
                    pass
            return
        super().handle_endtag(tag)
        if self.heading is not None and self.heading[0] == tag:
            self.title_matches |= normal(" ".join(self.heading[1])) == normal(self.job.title)
            self.heading = None
        if self.control is not None and self.control[0] == tag:
            _, href, parts = self.control
            label = " ".join(parts).strip()
            if APPLY_ACTION.search(label) or label.casefold() == "apply":
                if tag == "button":
                    self.enabled_button = True
                elif href and href.startswith("#"):
                    self.linked_forms.add(href[1:])
                else:
                    self.apply_link |= self.same_application_link(href)
            self.control = None

    def same_application_link(self, href):
        if not href:
            return False
        try:
            resolved = urljoin(self.target, href)
            address = canonical_url(resolved)
        except ValueError:
            return False
        listing = canonical_url(self.job.url)
        ashby_application = self.job.source == "ashby" and address == listing + "/application"
        return address != self.target and (ashby_application or address == self.job.apply_url)


def verify_job(job, client, now: datetime, listed_at=None):
    if job.manually_checked and (job.availability == "closed" or (
        job.availability == "verified" and job.checked_at
        and timedelta(0) <= now - datetime.fromisoformat(job.checked_at) <= CACHE_WINDOW
    )):
        return job
    target = automatic_apply_url(job)
    if not target:
        return job if job.manually_checked else replace(
            job, availability="unverified", checked_at=None,
            verification_reason="Open the employer link manually and record its status.",
        )
    try:
        response = client.get(target, max_bytes=2 * 1024 * 1024)
    except (NetworkUnavailable, ValueError) as exc:
        return replace(job, availability="unverified", checked_at=now.isoformat(), verification_reason=str(exc))
    page = ApplicationPage(job, target)
    page.feed(response.body.decode("utf-8", errors="replace"))
    page.close()
    visible = re.sub(r"\s+", " ", "".join(page.parts))
    current_feed = listed_at is not None and timedelta(0) <= now - listed_at <= CACHE_WINDOW
    exact_url = response.url == canonical_url(target)
    corroborated = page.title_matches and page.enabled_action and not BLOCKED.search(visible)
    if exact_url and (response.status in {404, 410} or (response.status == 200 and CLOSED.search(visible))):
        status, reason = "closed", "The official page returned an explicit closure signal."
    elif exact_url and response.status == 200 and current_feed and corroborated:
        status, reason = "verified", "Recent employer listing and matching job page with an enabled application control."
    else:
        status, reason = "unverified", f"Could not corroborate a current apply path (HTTP {response.status})."
    return replace(job, availability=status, checked_at=now.isoformat(), verification_reason=reason)
