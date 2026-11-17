"""Extract task and requirement candidates while retaining the employer's wording."""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

from .models import Requirement, fingerprint

ANALYSER_VERSION = 11

SECTIONS = {
    "core": (
        "responsibilities", "your responsibilities", "what you'll do", "what you will do", "your tasks",
        "your mission", "what you do", "key responsibilities", "your impact", "how you'll make an impact",
        "how you'll make an impact here", "here's how you'll make an impact",
        "your responsibilities include but are not limited to",
        "what you'll be doing", "your day to day", "your daily business", "your main tasks",
        "what your work will look like", "what you'll work on", "what you'll own", "what you'll build",
        "in this role you will", "in this role you ll", "what you will be doing", "your day to day responsibilities",
        "aufgaben", "deine aufgaben", "ihre aufgaben", "das erwartet dich", "das sind deine aufgaben",
        "dein aufgabenbereich", "was du bei uns machst", "das erwartet dich bei uns",
    ),
    "mandatory": (
        "requirements", "required qualifications", "minimum qualifications", "must have",
        "mandatory requirements", "must-haves", "must haves", "essential requirements",
        "what we're looking for", "what we are looking for", "what we expect",
        "what you need to be successful", "what you'll need to be successful", "minimum requirements",
        "mindestanforderungen", "voraussetzungen", "das bringst du mit", "was du mitbringst",
        "was du dafür mitbringst", "das erwarten wir",
    ),
    "unclear": ("qualifications", "about you", "what you bring", "your profile", "what makes you a fit",
                "about the role", "the role", "dein profil", "ihr profil"),
    "preferred": ("preferred qualifications", "nice to have", "nice-to-have", "nice-to-haves",
                  "bonus points", "bonus", "wünschenswert", "von vorteil", "pluspunkte", "wäre von vorteil",
                  "damit punktest du zusätzlich"),
    "additional": ("additional information", "weitere informationen", "zusätzliche informationen"),
    "skip": (
        "benefits", "what we offer", "about us", "compensation", "how to apply", "why join us",
        "why us", "what's in it for you", "equal opportunity", "interview process",
        "was wir bieten", "das bieten wir", "das bieten wir dir", "über uns", "unsere benefits",
        "bewerbungsprozess", "so geht es für dich weiter", "where you belong",
    ),
}
OPTIONAL = re.compile(r"\b(?:preferred|nice to have|a (?:(?:strong|big|significant) )?(?:plus|bonus|advantage)|"
                      r"desirable|optional|wünschenswert|"
                      r"von vorteil|von vorteil wäre|idealerweise|ideally|not required|nicht erforderlich)\b", re.I)
MANDATORY = re.compile(r"\b(?:mandatory|required|must (?:have|be|hold|possess)|minimum|zwingend|"
                       r"erforderlich|vorausgesetzt|mindestens|unbedingt)\b", re.I)
NO_LANGUAGE = re.compile(r"^(?:no |kein(?:e|er)? ).{0,45}(?:required|erforderlich)\b|"
                         r"\b(?:german|english|deutsch|englisch) (?:is )?not required\b", re.I)
NEGATION = re.compile(r"\b(?:no|not|never|without|lack(?:ed|ing|s)?|didn t|haven t|hasn t|kein(?:e|en|er)?|nicht|ohne)\b", re.I)
BULLET = re.compile(r"^\s*(?:[•·▪*–—-]|\d{1,2}[.)])\s*")
WORD = re.compile(r"[\w+/#-]+", re.UNICODE)


@dataclass(frozen=True)
class Catalogue:
    data: dict

    @property
    def version(self):
        return fingerprint(self.data)

    @property
    def tasks(self):
        return self.data["tasks"]

    @property
    def transfers(self):
        return self.data["transfers"]

    @property
    def families(self):
        return self.data["families"]

    @property
    def tools(self):
        return self.data["tools"]


def load_catalogue(path=None):
    file = Path(path) if path else Path(__file__).with_name("catalog.json")
    data = json.loads(file.read_text(encoding="utf-8"))
    tasks = set(data["tasks"])
    if any(set(family["tasks"]) - tasks for family in data["families"].values()):
        raise ValueError("A role family names an unknown task.")
    if any(target not in tasks or set(origins) - tasks for target, origins in data["transfers"].items()):
        raise ValueError("A transfer names an unknown task.")
    return Catalogue(data)


def normal(value):
    return " ".join(WORD.findall(unicodedata.normalize("NFKC", value).casefold()))


HEADING = {normal(label): kind for kind, labels in SECTIONS.items() for label in labels}
ROLE_VERB = re.compile(
    r"^(?:you (?:will |can )?|we expect you to |you'll )?(?:"
    r"analyse|analyze|assess|audit|automate|build|collect|coordinate|create|deliver|design|develop|"
    r"document|drive|enable|evaluate|execute|facilitate|forecast|handle|implement|investigate|lead|"
    r"maintain|manage|monitor|onboard|operate|orchestrate|own|plan|prepare|process|prospect|reconcile|"
    r"report|resolve|review|run|support|test|track|train|triage|troubleshoot|work|write|"
    r"analysiere|arbeite|baue|betreue|entwickle|erstelle|koordiniere|pflege|plane|unterstütze)\w*\b", re.I
)
BOILERPLATE = re.compile(r"\b(?:equal opportunity employer|regardless of (?:race|gender)|"
                         r"interested even if|don't meet all the requirements|accommodations during)\b", re.I)
REQUIRED_QUALIFICATION = re.compile(r"\b(?:\d{1,2}\s*\+?\s*(?:years?|jahre)\s+(?:of\s+)?"
                                   r"experience|[ABC][12]|work authori[sz]ation|sponsorship)\b", re.I)


def heading_kind(text):
    key = normal(text.strip("# ").replace("’", "'"))
    if key in HEADING:
        return HEADING[key]
    for delimiter in (" – ", " — ", " - "):
        prefix = normal(text.split(delimiter, 1)[0])
        if prefix in HEADING:
            return HEADING[prefix]
    return None


@lru_cache(maxsize=512)
def phrase_pattern(term):
    return re.compile(r"(?<![\w/])" + re.escape(normal(term)) + r"(?![\w/])")


def contains(text, term):
    return bool(term and phrase_pattern(term).search(normal(text)))


def asserted_phrase(text, term):
    """Reject local negations and future-learning phrases before crediting evidence."""
    return asserted_normal_phrase(normal(text), term)


def asserted_normal_phrase(normalized, term, *, evidence=True):
    return any(task_is_asserted(normalized, hit, evidence=evidence)
               for hit in phrase_pattern(term).finditer(normalized))


# An action and its object can be separated by qualifiers in an ad or CV.
# The short window and clause boundary keep an unrelated mention from becoming evidence.
ACTION_OBJECTS = {
    "experiment": (
        r"run|runs|running|ran|design(?:s|ed|ing)?|conduct(?:s|ed|ing)?|"
        r"execut(?:e|es|ed|ing)|analys(?:e|es|ed|ing)|analyz(?:e|es|ed|ing)|evaluat(?:e|es|ed|ing)",
        r"experiments?|a/b(?:[- ]tests?| testing)?|ab[- ]tests?|split tests?|controlled trials?",
    ),
    "data_analysis": (
        r"analys(?:e|es|ed|ing)|analyz(?:e|es|ed|ing)|explor(?:e|es|ed|ing)|"
        r"investigat(?:e|es|ed|ing)|profil(?:e|es|ed|ing)",
        r"datasets?|data|patterns in (?:the )?data",
    ),
    "report_kpis": (
        r"report(?:s|ed|ing)?|track(?:s|ed|ing)?|monitor(?:s|ed|ing)?|"
        r"summari[sz](?:e|es|ed|ing)|communicat(?:e|es|ed|ing)",
        r"kpis?|key performance indicators?|(?:operational|product|success|business|performance) metrics",
    ),
    "metric_design": (
        r"defin(?:e|es|ed|ing)|select(?:s|ed|ing)?|establish(?:es|ed|ing)?|"
        r"design(?:s|ed|ing)?|operationali[sz](?:e|es|ed|ing)",
        r"kpis?|key performance indicators?|success metrics|guardrail metrics|performance measures",
    ),
    "dashboard": (
        r"build(?:s|ing)?|built|creat(?:e|es|ed|ing)|develop(?:s|ed|ing)?|"
        r"design(?:s|ed|ing)?|maintain(?:s|ed|ing)?|rebuild(?:s|ing)?|rebuilt",
        r"dashboards?|data visuali[sz]ations?",
    ),
    "data_quality": (
        r"validat(?:e|es|ed|ing)|check(?:s|ed|ing)?|audit(?:s|ed|ing)?|"
        r"monitor(?:s|ed|ing)?|clean(?:s|ed|ing)?",
        r"datasets?|data quality|data for errors|records for (?:errors|duplicates)",
    ),
    "automate": (
        r"automat(?:e|es|ed|ing)",
        r"workflows?|reports?|reporting|processes|process|routines?|routine tasks|manual tasks",
    ),
    "evaluate_systems": (
        r"evaluat(?:e|es|ed|ing)|benchmark(?:s|ed|ing)?|assess(?:es|ed|ing)?|"
        r"compar(?:e|es|ed|ing)|measur(?:e|es|ed|ing)",
        r"model outputs?|system performance|model performance|response quality|workflow outputs?",
    ),
    "document_process": (
        r"document(?:s|ed|ing)?|record(?:s|ed|ing)?|"
        r"writ(?:e|es|ing)|wrote",
        r"procedures?|runbooks?|workflows?|process steps|data definitions",
    ),
}
TASK_PATTERNS = {
    task: re.compile(r"\b(?:" + actions + r")\b\s+(?:(?:[\w/#-]+)\s+){0,5}(?:"
                     + objects + r")\b")
    for task, (actions, objects) in ACTION_OBJECTS.items()
}
INTENT_ONLY = re.compile(r"\b(?:learn(?:ing)? (?:to|about)|plans? to|planned to|want to|interested in|"
                         r"exposure to|read about|watched|observed)\b", re.I)


TASK_EXCLUSION = re.compile(r"\b(?:rather than|instead of|excluding|don t|doesn t|won t)\b", re.I)
POST_EXCLUSION = re.compile(r"^(?:is|are|was|were)?\s*(?:not in scope|not required|out of scope)\b", re.I)


OTHER_ACTOR = re.compile(r"\b(?:who|whose|whoever|whether|in case|so (?:that )?(?:they|others)|"
                         r"as (?:they|others)|(?:vendors?|suppliers?|agencies|contractors?|teams?|teammates?|colleagues?) "
                         r"(?:that|which)|(?:they|others|colleagues|teammates|clients|students|staff|vendors) "
                         r"(?:can|could|would|to|will))\b")
EVIDENCE_SCOPE = re.compile(r"\b(?:if|would|could|aimed to|hop(?:e|ed) to|"
                            r"tasked with|asked to|responsible for learning|"
                            r"(?:proposals?|options?|requests?|plans?|recommendations?|ideas?) (?:to|for))\b")


def task_is_asserted(clause, hit, *, evidence):
    prefix = clause[:hit.start()].rstrip()
    before = " ".join(prefix.split()[-5:])
    context = f"{before} {hit.group()}"
    after = " ".join(clause[hit.end():].split()[:5])
    actor_context = f"{prefix} {hit.group()}"
    return not (OTHER_ACTOR.search(actor_context) or NEGATION.search(context) or TASK_EXCLUSION.search(context) or POST_EXCLUSION.search(after)
                or (evidence and (INTENT_ONLY.search(actor_context) or EVIDENCE_SCOPE.search(actor_context)
                                  or before.endswith(" learning")
                                  or before == "learning")))


def pattern_tasks(text, *, evidence):
    supported = set()
    for raw in re.split(r"[.;,\n!?]+", text):
        clause = normal(raw)
        for task, pattern in TASK_PATTERNS.items():
            if task not in supported and any(task_is_asserted(clause, hit, evidence=evidence)
                                             for hit in pattern.finditer(clause)):
                supported.add(task)
    return supported


def task_tags(text, catalogue, evidence=False):
    spans = re.split(r"[.;!?\n]+|,\s*(?=(?:and )?then\b)", text, flags=re.I)
    clauses = [normal(span) for span in spans]
    matched_patterns = pattern_tasks(text, evidence=evidence)
    return tuple(task for task, aliases in catalogue.tasks.items()
                 if task in matched_patterns or any(asserted_normal_phrase(clause, alias, evidence=evidence)
                                                    for clause in clauses for alias in aliases))


AD_LANGUAGE_WORDS = {
    "en": {"the", "and", "you", "your", "with", "will", "our", "this", "for", "who", "what", "we", "are"},
    "de": {"die", "der", "das", "du", "dich", "dein", "deine", "mit", "und", "wir", "für", "sowie", "bei"},
}


def advert_language(description):
    """A display and pilot signal inferred from text, independent of job requirements."""
    words = set(normal(description).split())
    scores = {code: len(words & markers) for code, markers in AD_LANGUAGE_WORDS.items()}
    primary, second = sorted(scores, key=scores.get, reverse=True)
    return primary if scores[primary] >= 5 and scores[primary] - scores[second] >= 3 else ""


LANGUAGE_TERM = re.compile(r"\b(?:german|english|french|spanish|deutsch\w*|englisch\w*|"
                           r"französisch\w*|spanisch\w*)\b", re.I)
LANGUAGE_LEVEL = re.compile(r"\b[ABC][12]\b", re.I)
PERSONAL_CONDITION = re.compile(r"\b(?:work authori[sz]ation|right to work|visa sponsorship|arbeitserlaubnis|"
                                r"immatrikulier\w*|enroll(?:ed|ment)|current student|"
                                r"security clearance|background check|sicherheitsüberprüfung|"
                                r"credentials?|certifications?|licen[cs]es?|degree|travel|reisebereitschaft|"
                                r"years? of .*experience|jahre\w* .*erfahrung)\b", re.I)
CANDIDATE_CONDITION = re.compile(r"^(?:applicants?|candidates?|you|bewerber\w*)\b.{0,50}"
                                 r"\b(?:must|müssen|required)\b|"
                                 r"\b(?:is|are) (?:required|mandatory)\s*[.!]?$", re.I)
LANGUAGE_QUALIFIER = re.compile(r"\b(?:fluency|fluent|proficien\w*|native|language skills|"
                                r"sprachkenntnisse|verhandlungssicher\w*|fließend\w*)\b", re.I)
# The second, comma-separated level is optional in phrases such as "German B2, C1 preferred".
LANGUAGE_ASIDE = re.compile(
    r"(?:,\s*(?:with\s+)?|\s+\(\s*|\s+(?:but|however|aber|jedoch)\s+)"
    r"(?=(?:(?:English|German|French|Spanish|Englisch\w*|Deutsch\w*)\s+)?"
    r"(?:[ABC][12](?:\s+is)?\s+(?:preferred|desirable|optional|wünschenswert|von Vorteil|"
    r"(?:is\s+)?a (?:plus|bonus)|not required)|(?:ideally|idealerweise)\b))", re.I,
)


def split_preferences(text):
    language = LANGUAGE_TERM.search(text)
    if language:
        parts = LANGUAGE_ASIDE.split(text)
        if len(parts) > 1:
            return parts
    parts = re.split(r",\s*|\s+(?:and|but|und|aber)\s+", text, maxsplit=1, flags=re.I)
    if len(parts) == 2 and MANDATORY.search(parts[0]):
        left, right = parts
        # Each side has its own explicit wording. Keep general comma lists intact.
        if ((not OPTIONAL.search(left) and OPTIONAL.search(right))
                or (NO_LANGUAGE.search(left) and MANDATORY.search(right))):
            return [left, right]
    return [text]


def ambiguous_language_preference(text):
    languages = list(LANGUAGE_TERM.finditer(text))
    if not languages or not OPTIONAL.search(text):
        return False
    levels = list(LANGUAGE_LEVEL.finditer(text))
    if len(levels) > 1:
        separator = text[levels[0].end():levels[1].start()].strip()
        if separator not in {"/", "-", "–"}:
            return True
    return len(languages) > 1 and bool(LANGUAGE_LEVEL.search(text[:languages[-1].start()])
                                      or LANGUAGE_QUALIFIER.search(text[:languages[-1].start()]))


def split_duties(text, catalogue, tags):
    # Split coordinated, recognised actions. Leave alternatives, subordinate clauses
    # and shared qualification or ownership wording attached to the original line.
    if (NEGATION.search(normal(text)) or OTHER_ACTOR.search(normal(text))
            or re.search(r"\b(?:or|oder|own|lead|manage|independently|eigenverantwortlich)\b", text, re.I)):
        return [(text, tags)]
    parts = re.split(r"\s+(?:and|und)\s+", text, flags=re.I)
    if len(parts) > 1 and all(ROLE_VERB.search(part) for part in parts):
        mapped = [(part, task_tags(part, catalogue)) for part in parts]
        if all(tags for _, tags in mapped):
            return mapped
    return [(text, tags)]


def requirement_chunks(description):
    """Yield bounded lines, including headings followed by content on the same line."""
    for raw in description.splitlines():
        bullet = bool(BULLET.match(raw))
        line = BULLET.sub("", raw.strip()).strip()
        if not line:
            continue
        heading, separator, remainder = line.partition(":")
        if (kind := heading_kind(heading)) and not bullet:
            yield kind, "", False
            line = remainder.strip() if separator else ""
        elif not bullet and line.endswith(":") and 1 <= len(line.split()) <= 8:
            # Subheadings such as "People Leadership" can sit inside responsibilities.
            continue
        if line:
            spans = re.split(
                r"(?<=[.!?])\s+(?=[A-ZÄÖÜ])|;\s+|,\s*(?=(?i:ideally|idealerweise)\b)|"
                r",\s*(?i:as well as|sowie)\s+(?=(?i:English|German|Englisch|Deutsch)\w*)",
                line,
            )
            for span in spans:
                for part in split_preferences(span):
                    for offset in range(0, len(part), 800):
                        yield None, part[offset:offset + 800].strip(), bullet


def analyse_description(description, catalogue):
    section = ""
    rows = []
    seen = set()
    for heading, text, bullet in requirement_chunks(description):
        if heading is not None:
            section = heading
            continue
        if section == "skip" or not text or BOILERPLATE.search(text):
            continue
        explicit_language = LANGUAGE_TERM.search(text) and (LANGUAGE_LEVEL.search(text)
                                                           or LANGUAGE_QUALIFIER.search(text))
        if section == "additional" and not (CANDIDATE_CONDITION.search(text)
                or ((explicit_language or PERSONAL_CONDITION.search(text))
                    and (MANDATORY.search(text) or OPTIONAL.search(text)))):
            continue
        if (not bullet and len(text.split()) < 3 and section not in {"mandatory", "preferred"}
                and not (MANDATORY.search(text) or OPTIONAL.search(text))):
            continue
        tags = task_tags(text, catalogue)
        if NO_LANGUAGE.search(text) and not re.search(r"\b(?:but|however|aber|jedoch)\b", text, re.I):
            kind = "preferred"
        elif OPTIONAL.search(text) and MANDATORY.search(text) and section != "preferred" and not re.search(
            r"\b(?:not required|nicht erforderlich)\b", text, re.I
        ):
            kind = "unclear"
        elif section != "preferred" and ambiguous_language_preference(text):
            kind = "unclear"
        elif OPTIONAL.search(text) or section == "preferred":
            kind = "preferred"
        elif (MANDATORY.search(text) or section == "mandatory"
              or section == "additional" and CANDIDATE_CONDITION.search(text)
              or section == "unclear" and REQUIRED_QUALIFICATION.search(text)):
            kind = "mandatory"
        elif section == "unclear" and (bullet or re.match(r"^(?:experience|proficien|strong|knowledge|you have)", text, re.I)):
            kind = "unclear"
        elif (section == "core" and (bullet or ROLE_VERB.search(text))) or (tags and ROLE_VERB.search(text)):
            kind = "core"
        else:
            continue
        duties = split_duties(text, catalogue, tags) if kind == "core" else [(text, tags)]
        for span, span_tags in duties:
            key = (kind, normal(span))
            if key in seen:
                continue
            seen.add(key)
            rows.append(Requirement(f"r{len(rows) + 1:03}", kind, span, span_tags))
            if len(rows) >= 100:
                return tuple(rows)
    return tuple(rows)
