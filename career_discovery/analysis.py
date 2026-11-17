"""Extract task and requirement candidates while retaining the employer's wording."""

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import unicodedata

from .models import Requirement, fingerprint

ANALYSER_VERSION = 13

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
        "you will", "you ll", "your role", "deine rolle", "ihre rolle", "dein verantwortungsbereich",
        "deine verantwortung", "deine verantwortlichkeiten",
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
                "about the role", "the role", "dein profil", "ihr profil",
                "who you are", "you are", "you have", "your experience", "your skills", "your skillset",
                "what you bring to the table", "das zeichnet dich aus", "was dich auszeichnet",
                "deine skills", "deine qualifikationen", "ihre qualifikationen"),
    "preferred": ("preferred qualifications", "nice to have", "nice-to-have", "nice-to-haves",
                  "bonus points", "bonus", "wünschenswert", "von vorteil", "pluspunkte", "wäre von vorteil",
                  "damit punktest du zusätzlich"),
    "additional": ("additional information", "weitere informationen", "zusätzliche informationen"),
    "skip": (
        "benefits", "what we offer", "about us", "compensation", "how to apply", "why join us",
        "why us", "what's in it for you", "equal opportunity", "interview process",
        "was wir bieten", "das bieten wir", "das bieten wir dir", "über uns", "unsere benefits",
        "bewerbungsprozess", "so geht es für dich weiter", "where you belong",
        "you ll get", "what you ll get", "what you ll get in return", "working conditions",
        "why join now", "deine benefits", "wir bieten dir",
    ),
}
OPTIONAL = re.compile(r"\b(?:preferred|nice to have|a (?:(?:strong|big|significant) )?(?:plus|bonus|advantage)|"
                      r"desirable|optional|wünschenswert|"
                      r"von vorteil|von vorteil wäre|idealerweise|ideally|not required|nicht erforderlich)\b", re.I)
MANDATORY = re.compile(r"\b(?:mandatory|required|must (?:have|be|hold|possess)|minimum|zwingend|"
                       r"erforderlich|vorausgesetzt|mindestens|unbedingt|hard requirements?|a must(?:-have)?|"
                       r"(?:is|are) (?:absolutely )?essential|essential (?:requirements?|skills?|qualifications?)|"
                       r"(?:ist|sind) (?:eine? )?(?:pflicht|muss|voraussetzung)|pflichtvoraussetzung|"
                       r"grundvoraussetzung|voraussetzung (?:ist|sind))\b", re.I)
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
    r"^(?:you (?:will |can )?|we expect you to |you[’']ll )?(?:"
    r"analyse|analyze|assess|audit|automate|build|collect|coordinate|create|deliver|design|develop|"
    r"document|drive|enable|evaluate|execute|facilitate|forecast|handle|implement|investigate|lead|"
    r"maintain|manage|monitor|onboard|operate|orchestrate|own|plan|prepare|process|prospect|reconcile|"
    r"report|resolve|review|run|support|test|track|train|triage|troubleshoot|work|write|"
    r"analysiere|arbeite|baue|betreue|entwickle|erstelle|koordiniere|pflege|plane|unterstütze)\w*\b", re.I
)
# Inside a duties section, plain lines without bullets also read as duties when they open with an English action,
# a German second-person verb, or a German action noun ("Erstellung von Reports").
SECTION_DUTY = re.compile(
    r"^(?:you (?:will |can )?|you[’']ll )?(?:collaborate|communicate|conduct|configure|debug|diagnose|educate|ensure|"
    r"fix|guide|help|identify|improve|integrate|keep|liaise|match|optimi[sz]e|organi[sz]e|partner|produce|provide|"
    r"respond|schedule|set up|update)\w*\b"
    r"|^du (?!bist|hast|bringst|kannst|sprichst|verfügst|besitzt|möchtest|willst|überzeugst)\w+st\b"
    r"|^sie (?!sind|haben|bringen|können|sprechen|verfügen|besitzen|möchten|überzeugen)\w+en\b"
    r"|^(?:eigenständige |selbstständige |operative |kontinuierliche |enge |aktive )?"
    r"(?:\w+ung|analyse|pflege|aufbau|koordination|kommunikation|dokumentation|mitarbeit|mitwirkung|übernahme|"
    r"identifikation|implementierung|optimierung|moderation|konzeption|präsentation|kontrolle)(?:en)?\b"
    r"(?=.{0,40}\b(?:von|der|des|und|sowie|im|in|bei|mit|für|unserer|unseres|neuer)\b)", re.I
)
BOILERPLATE = re.compile(r"\b(?:equal opportunity employer|regardless of (?:race|gender)|"
                         r"interested even if|don't meet all the requirements|accommodations during)\b", re.I)
REQUIRED_QUALIFICATION = re.compile(r"\b(?:\d{1,2}\s*\+?\s*(?:years?|jahre)\s+(?:of\s+)?"
                                   r"experience|[ABC][12]|work authori[sz]ation|sponsorship)\b", re.I)


QUALIFICATION_LEAD = (r"^(?:(?:you (?:have|bring)|du (?:hast|bringst)|proven|solid|strong|hands-on|excellent|fluent|"
                      r"sehr gute|fundierte|gute|umfassende)\s+)*(?:an?\s+)?(?:\d{1,2}\s*\+?\s*)?")
QUALIFICATION_SHAPE = re.compile(QUALIFICATION_LEAD + r"(?:experience|years?|proficien\w*|knowledge(?![- ]?base)|degree|background|"
                                 r"familiarity|erfahrung\w*|kenntnisse|sprachkenntnisse|abgeschlossen\w* studium|"
                                 r"jahre\w*)\b", re.I)


def heading_kind(text):
    key = normal(text.strip("# ").replace("’", "'"))
    if key in HEADING:
        return HEADING[key]
    for delimiter in (" – ", " — ", " - "):
        if delimiter in text:
            for side in text.split(delimiter, 1):
                if (kind := HEADING.get(normal(side.strip("# ").replace("’", "'")))):
                    return kind
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
# Each task lists (actions, objects) pairs. A third item makes the object-first order valid as well,
# as German infinitives and separable verbs need. An actions value of None means the objects alone are the evidence.
def silent_e(*stems):
    return "|".join(f"{stem}(?:e|es|ed|ing)" for stem in stems)


def regular(*stems):
    return "|".join(f"{stem}(?:s|es|ed|ing)?" for stem in stems)


FIX_VERBS = (regular("fix", "debug", "troubleshoot") + "|" + silent_e("resolv", "diagnos", "investigat", "remediat")
             + r"|debugged|troubleshot|work(?:s|ed|ing)? through|track(?:s|ed|ing)? down")
MAKE_VERBS = (silent_e("creat", "updat", "produc", "prepar", "curat", "compil") + "|" + regular("develop", "build", "maintain",
              "draft", "publish", "own") + r"|built|writ(?:e|es|ing)|wrote|keep(?:s|ing)?|kept|set(?:s|ting)? up")
# "Resolve escalated cases": after a handling verb, "escalated" describes the case, not the role's action.
ADJECTIVAL_GUARD = "".join(f"(?<!{verb} )" for verb in (
    "resolve", "resolves", "resolving", "resolved", "handle", "handles", "handling", "handled", "own", "owns",
    "owning", "manage", "manages", "managing", "solve", "solves", "solving", "take", "takes", "taking", "work on"))
DOC_VERBS = (silent_e("creat", "updat", "produc", "prepar", "curat", "compil") + "|"
             + regular("develop", "build", "maintain", "draft", "publish") + r"|built|writ(?:e|es|ing)|wrote")
RUN_VERBS = (silent_e("facilitat", "moderat", "provid") + "|" + regular("conduct", "deliver", "host", "hold") +
             r"|run(?:s|ning)?|ran|giv(?:e|es|ing)|gave|held|carr(?:y|ies|ied|ying) out")
DE_MAKE_VERBS = (r"erstell\w*|entwickl\w*|bau(?:e|st|t|en)?|aufbau\w*|pfleg\w*|aktualisier\w*|konzipier\w*|implementier\w*|"
                 r"verantwort\w*|übernimm\w*|übernehm\w*|umsetz\w*|durchführ\w*|führ(?:e|st|t|en)|verfass\w*|erarbeit\w*|"
                 r"einricht\w*|verwalt\w*|etablier\w*|bereitstell\w*|erzeug\w*|überarbeit\w*|gestalt\w*")
ISSUE_TERMS = (r"issues?|problems?|tickets?|escalations?|errors?|incidents?|bugs?|defects?|faults?|outages?|failures?|"
               r"malfunctions?|(?:support|customer|service|escalated|client|user|technical) cases?")
TICKET_TERMS = (r"(?:technical|customer|user|client|support|production|service|escalated|operational|product|system|"
                r"software|platform|complex) (?:issues?|incidents?|cases?|errors?|escalations?)|"
                r"(?:technical|production|operational|software|system|platform|support|service) problems?|tickets?|"
                r"escalations?|incidents?")
MANAGED_TICKETS = (r"tickets?|incidents?|(?:support|customer|service|escalated|technical) (?:cases?|issues?|escalations?)")
DE_ISSUES = (r"probleme\w*|störung\w*|fehler\w*|tickets?|eskalation\w*|incidents?|vorfäll\w*|schwierigkeiten|ausfäll\w*|"
             r"bugs?|supportfäll\w*|reklamation\w*|mängel")
PEOPLE = (r"(?:new |existing |internal |external |junior )?(?:customers?|users?|clients?|staff|employees|"
          r"teammates|partners|team members|students|learners|participants|end[- ]users|hires)")
DE_PEOPLE = (r"kunden\w*|mitarbeit\w*|anwender\w*|nutzer\w*|partner\w*|kolleg\w*|teilnehmer\w*|studierende\w*|"
             r"auszubildende\w*|lehrkräfte|vertriebsmitarbeit\w*|berater\w*|key[- ]?user\w*")
TEACHING = (r"(?:training|enablement|onboarding|product|educational|learning|knowledge[- ]sharing|staff|hands-on|safety|"
            r"instructor[- ]led) "
            r"(?:trainings?|workshops?|sessions?|classes|courses?|webinars?|demos?)|"
            r"trainings?(?! (?:sets?|data|pipelines?|runs?|environments?|jobs?|infrastructure|loops?|plans?|records?|"
            r"ambassadors?|managers?|methods?))|webinars?|classes|seminars?|lessons|courses?(?!-)|bootcamps?|train-the-trainer")
LEARNING = (r"training (?:materials?|content|programs?|programmes?|courses?|curricul\w*|modules?|resources?|decks?|guides?|"
            r"sessions?|plans?|concepts?)|(?:learning|onboarding|e-learning|educational|teaching|course|workshop|"
            r"customer training) (?:materials?|content|resources?|modules?|paths?|programs?|programmes?|courses?)|"
            r"curricul\w*|courses?(?!-)|e-learning|trainings?(?! (?:sets?|data|pipelines?|runs?|environments?|jobs?|"
            r"infrastructure|loops?|records?|ambassadors?|managers?))|lesson plans?|learning modules?|quizzes|tutorials?|"
            r"learning (?:paths?|programs?|journeys?|experiences?)")
DOCUMENTS = (r"runbooks?|sops?|standard operating procedures?|work instructions?|process maps?|"
             r"(?:process|procedure|technical|operational|internal|product|user|customer|support|system|project|api|"
             r"training|onboarding|analytics)\w*[- ]documentation|documentation|knowledge[- ]?bases?(?: articles?| content)?|"
             r"knowledge articles?|(?:help|support|faq|how-to|internal|customer-facing|self-service) "
             r"(?:articles?|guides?|docs?|content|pages?|centre|center)|help[- ]?(?:centre|center)(?: articles?| content)?|"
             r"(?:user|operating|product|service|training|technical) manuals?|user guides?|wikis?|confluence pages?")
DE_DOCUMENTS = (r"\w*dokumentation\w*|arbeitsanweisung\w*|handbüch\w*|handbuch|wissensdatenbank\w*|"
                r"knowledge[- ]?base\w*|faqs?|anleitung\w*|sops?|verfahrensanweisung\w*|checklisten|"
                r"prozessbeschreibung\w*|wiki\w*|runbooks?|leitfäden|leitfaden")
METRICS = (r"kpis?|key performance indicators?|(?:\w+ )?metrics?|(?:performance|quality|business|sales|financial|operational) "
           r"(?:figures|numbers|indicators?|results)|(?:performance|operational|management|kpi|business|sales|"
           r"financial|metrics?) (?:reports?|reporting)")
DE_METRICS = (r"\w*kennzahl\w*|kpis?\w*|(?:kpi|performance|management|vertriebs|umsatz|monats|wochen|quartals|controlling)"
              r"[- ]?(?:reports?|reportings?|berichte?)\w*|reportings?|berichtswesen|metriken|performance[- ]?daten")
DATA = r"(?:\w+ )?data|datasets?|data sets?|big data|patterns in (?:the )?data|trends in (?:the )?(?:\w+ )?data"
ACTION_OBJECTS = {
    "experiment": ((
        r"run|runs|running|ran|design(?:s|ed|ing)?|conduct(?:s|ed|ing)?|"
        r"execut(?:e|es|ed|ing)|analys(?:e|es|ed|ing)|analyz(?:e|es|ed|ing)|evaluat(?:e|es|ed|ing)",
        r"experiments?|a/b(?:[- ]tests?| testing)?|ab[- ]tests?|split tests?|controlled trials?",
    ),),
    "data_analysis": ((
        r"analys(?:e|es|ed|ing)|analyz(?:e|es|ed|ing)|explor(?:e|es|ed|ing)|"
        r"investigat(?:e|es|ed|ing)|profil(?:e|es|ed|ing)",
        r"datasets?|data|patterns in (?:the )?data",
    ), (
        silent_e("analys", "analyz", "examin", "explor") + "|" + regular("interpret") + r"|dig(?:s|ging)? into",
        DATA,
    ), (
        silent_e("provid") + "|" + regular("perform", "conduct", "deliver") + r"|carr(?:y|ies|ied|ying) out|run(?:s|ning)?|ran|do(?:es|ing)?",
        r"(?:data|statistical|quantitative|exploratory|ad[- ]hoc|trend|variance|cohort|funnel|usage|sales|"
        r"financial|operational|business|kpi|metric) analys[ie]s|analyses of (?:\w+ )?data|data analytics",
    ), (
        r"analysier\w*|auswert\w*|untersuch\w*|wertest|wertet|analyse|analysen|auswertung\w*|aufbereit\w*",
        r"daten\w*|datensätze|\w*daten|zahlen|trends|\w*kennzahl\w*|datenbestände",
        "either",
    ), (
        r"durchführ\w*|führ(?:e|st|t|en)|erstell\w*|erarbeit\w*|verantwort\w*|übernimm\w*|übernehm\w*",
        r"datenanalys\w*|datenauswertung\w*|\w*daten\w*analyse\w*",
    )),
    "report_kpis": ((
        r"report(?:s|ed|ing)?|track(?:s|ed|ing)?|monitor(?:s|ed|ing)?|"
        r"summari[sz](?:e|es|ed|ing)|communicat(?:e|es|ed|ing)",
        r"kpis?|key performance indicators?|(?:operational|product|success|business|performance) metrics",
    ), (
        regular("report", "track", "monitor", "review", "present", "build", "maintain", "own", "publish", "deliver") + "|"
        + silent_e("measur", "manag", "analys", "analyz", "summari[sz]", "communicat", "prepar", "produc", "creat", "generat",
                   "provid", "compil", "updat") + r"|built",
        METRICS,
    ), (
        r"report(?:s|ed|ing)? on",
        r"performance|results|progress|status|the (?:team|business) numbers",
    ), (
        r"auswert\w*|berichtet\w*|überwach\w*|erstell\w*|analysier\w*|monitor\w*|steuer(?:e|st|t|n|ung)|track\w*|pfleg\w*|"
        r"aufbereit\w*|bereitstell\w*|verfolg\w*|durchführ\w*|aufbau\w*|bau(?:e|st|t|en)|etablier\w*|wertest|wertet|"
        r"entwickl\w*|analyse|erstellung|pflege|überwachung|bericht\w*",
        DE_METRICS,
        "either",
    )),
    "metric_design": ((
        r"defin(?:e|es|ed|ing)|select(?:s|ed|ing)?|establish(?:es|ed|ing)?|"
        r"design(?:s|ed|ing)?|operationali[sz](?:e|es|ed|ing)",
        r"kpis?|key performance indicators?|success metrics|guardrail metrics|performance measures",
    ),),
    "dashboard": ((
        r"build(?:s|ing)?|built|creat(?:e|es|ed|ing)|develop(?:s|ed|ing)?|"
        r"design(?:s|ed|ing)?|maintain(?:s|ed|ing)?|rebuild(?:s|ing)?|rebuilt",
        r"dashboards?|data visuali[sz]ations?",
    ), (
        silent_e("us", "utili[sz]", "leverag", "creat", "updat") + "|" + regular("build", "develop", "maintain", "own", "design")
        + r"|built|work(?:s|ed|ing)? (?:with|in)|set(?:s|ting)? up",
        r"looker(?: studio)?|metabase|grafana|qlik\w*|superset|redash|quicksight|data studio|power ?bi|tableau|"
        r"(?:bi|data) visuali[sz]ations?",
    ), (
        DE_MAKE_VERBS,
        r"\w*dashboards?\w*|visualisierung\w*|cockpits?|looker|metabase|power ?bi|tableau",
        "either",
    )),
    "data_quality": ((
        r"validat(?:e|es|ed|ing)|check(?:s|ed|ing)?|audit(?:s|ed|ing)?|"
        r"monitor(?:s|ed|ing)?|clean(?:s|ed|ing)?",
        r"datasets?|data quality|data for errors|records for (?:errors|duplicates)",
    ), (
        silent_e("validat", "updat", "ensur", "improv", "reconcil", "cleans", "manag") + "|" + regular(
            "correct", "enrich", "govern", "review", "safeguard", "check", "audit", "monitor", "clean", "maintain", "own") +
        r"|verif(?:y|ies|ied|ying)|dedup\w*",
        r"data (?:quality|integrity|accuracy|hygiene|governance)|(?:crm|customer|master|client|contact|product|account|"
        r"lead|supplier|vendor|company|candidate|contract|inventory|sales|accurate) (?:data|records?)"
        r"(?! (?:protections?|permissions?|privacy|security|processing|storage|retention|boundaries))|duplicates?|"
        r"data (?:entries|entry|records?)|(?:accuracy|quality|integrity|completeness|consistency) of (?:\w+ ){0,3}"
        r"(?:data|records)|(?:accurate|clean|correct|consistent|reliable|high[- ]quality|complete) (?:\w+ )?(?:data|records?)",
    ), (
        r"pfleg\w*|prüf\w*|bereinig\w*|validier\w*|kontrollier\w*|aktualisier\w*|sicherstell\w*|plausibilisier\w*|"
        r"korrigier\w*|pflege|prüfung|bereinigung|kontrolle|dublett\w*",
        r"daten\w*|\w*daten|datensätze|datenbestand\w*|stammdaten\w*|duplikate|datenqualität",
        "either",
    ), (
        None,
        r"datenqualität\w*|datenpflege|datenbereinigung|datenvalidierung|datenintegrität|stammdatenpflege|datenhygiene",
    )),
    "automate": ((
        r"automat(?:e|es|ed|ing)",
        r"workflows?|reports?|reporting|processes|process|routines?|routine tasks|manual tasks",
    ), (
        silent_e("automat") + r"|" + regular("script"),
        r"(?:manual|repetitive|tedious|recurring|routine|time[- ]consuming) \w+|tasks?|steps|checks|handoffs|operations|"
        r"data entry|work|follow[- ]ups?|invoic\w*",
    ), (
        silent_e("creat") + "|" + regular("implement", "design", "build", "develop", "maintain") + r"|built|writ(?:e|es|ing)|"
        r"wrote|set(?:s|ting)? up",
        r"(?<!infrastructure )(?<!design )(?<!deployment )(?<!test )automations?(?! (?:roadmap|strateg\w*|team|lead|manager|engineer\w*|platform|framework|capabilit\w*))|"
        r"automation (?:workflows?|scripts?|tools?|solutions?)|automated (?:workflows?|processes|reports?|solutions?)|"
        r"(?:rpa|no[- ]code|low[- ]code) (?:solutions?|bots?|workflows?|automations?)|n8n (?:workflows?|automations?)|"
        r"zapier (?:zaps?|workflows?)",
    ), (
        None,
        r"automatisier\w*|automatisierung\w*|prozessautomatisierung|workflow-?automatisierung",
    )),
    "evaluate_systems": ((
        r"evaluat(?:e|es|ed|ing)|benchmark(?:s|ed|ing)?|assess(?:es|ed|ing)?|"
        r"compar(?:e|es|ed|ing)|measur(?:e|es|ed|ing)",
        r"model outputs?|system performance|model performance|response quality|workflow outputs?",
    ),),
    "document_process": ((
        r"document(?:s|ed|ing)?|record(?:s|ed|ing)?|"
        r"writ(?:e|es|ing)|wrote",
        r"procedures?|runbooks?|workflows?|process steps|data definitions",
    ), (
        regular("document") + "|" + DOC_VERBS,
        DOCUMENTS,
    ), (
        r"document(?:s|ed|ing)?",
        r"(?:support|business|operational|internal|customer|standard|key) processes|processes|procedures|workflows",
    ), (
        r"dokumentier\w*|dokumentation|pfleg\w*|aktualisier\w*|erstell\w*|verfass\w*|schreib\w*|erarbeit\w*|"
        r"erstellung|pflege|führ(?:e|st|t|en)",
        DE_DOCUMENTS,
        "either",
    ), (
        r"dokumentier\w*|dokumentation",
        r"prozess\w*|abläufe|arbeitsschritte|arbeitsabläufe|verfahren|vorgehen\w*|richtlinien",
    )),
    "troubleshoot": ((
        FIX_VERBS,
        ISSUE_TERMS,
    ), (
        silent_e("solv", "handl") + r"|respond(?:s|ed|ing)? to",
        TICKET_TERMS,
    ), (
        silent_e("manag"),
        MANAGED_TICKETS,
    ), (
        silent_e("perform", "conduct", "drive") + r"|carr(?:y|ies|ied|ying) out|run(?:s|ning)?|ran|lead(?:s|ing)?|"
        r"do(?:es|ing)?|support(?:s|ed|ing)?|own(?:s|ed|ing)?|provid(?:e|es|ed|ing)|document(?:s|ed|ing)?|"
        r"writ(?:e|es|ing)|wrote",
        r"root[- ]cause (?:analys[ie]s|analyses|investigations?|reviews?|identification)|rca|post[- ]?mortems?",
    ), (
        r"lös(?:e|t|st|en)|löst|behe(?:b|bst|bt|ben)\w*|bearbeit\w*|analysier\w*|diagnostizier\w*|untersuch\w*|klär\w*|"
        r"bearbeitung|lösung|behebung|analyse|klärung|entstör\w*|beseitig\w*|eskalier\w*|nachverfolg\w*|reproduzier\w*|"
        r"korrigier\w*",
        DE_ISSUES,
        "either",
    ), (
        None,
        r"fehleranalyse\w*|fehlerbehebung\w*|fehlerdiagnose\w*|fehlersuche|störungsbehebung\w*|störungsanalyse\w*|"
        r"ursachenanalyse\w*|root[- ]cause[- ]analys[ie]s",
    )),
    "triage": ((
        silent_e("prioriti[sz]", "categori[sz]") + r"|escalat(?:e|es|ing)|" + ADJECTIVAL_GUARD + r"escalated|"
        r"rout(?:e|es|ing)|classif(?:y|ies|ied|ying)",
        r"incoming (?:\w+ )?(?:requests?|issues?|cases?|inquiries|queries|tickets?|emails?|incidents?|alerts?)|"
        r"inbound (?:\w+ )?(?:requests?|issues?|cases?|inquiries|queries|tickets?|emails?|incidents?)|"
        r"tickets?|incidents?|escalations?|alerts?|(?:support|service|production) (?:requests?|issues?|cases?|inquiries)",
    ), (
        r"priorisier\w*|kategorisier\w*|klassifizier\w*|eskalier\w*|weiterleit\w*|leit(?:e|est|et)|zuordn\w*|"
        r"priorisierung|kategorisierung",
        r"eingehende\w* (?:tickets?|anfragen|störungen|incidents?|meldungen|vorfälle|anliegen|fälle)|"
        r"tickets?|incidents?|störungsmeldungen|supportanfragen",
        "either",
    )),
    "onboard": ((
        None,
        r"onboard(?:s|ed|ing)? (?:(?:the|our|all|new|additional|existing|key|enterprise|incoming|your) )*"
        r"(?:customers?|clients?|merchants?|partners?|accounts?|sellers?|users?|kunden|neukunden)",
    ), (
        silent_e("guid", "manag", "handl", "coordinat", "improv", "driv") + "|" + regular(
            "own", "conduct", "deliver", "support", "lead", "help", "walk") + r"|oversee(?:s|ing)?|run(?:s|ning)?|ran|led",
        r"(?:customer|client|user|merchant|partner|seller|kunden|enterprise|implementation)[- ]onboarding|"
        r"onboarding (?:of|for) (?:new )?(?:customers?|clients?|users?|merchants?|partners?|accounts?|sellers?)|"
        r"(?:new )?(?:customers?|clients?|users?|merchants?|partners?|accounts?|sellers?) (?:through|during|into) "
        r"(?:the |their )?(?:onboarding|implementation|go[- ]live|setup)",
    ), (
        r"[\w-]*kunden|kundinnen|nutzer\w*|anwender\w*",
        r"onboarding\w*|(?:produkt)?einführung|inbetriebnahme",
    ), (
        None,
        r"(?:kunden|nutzer)[- ]?onboarding\w*",
    )),
    "configuration": ((
        r"configur(?:e|es|ed|ing)",
        r"[\w/#-]+",
    ), (
        r"set(?:s|ting)? up|setup|provision(?:s|ed|ing)?",
        r"(?:(?:customer|client|user|admin|test) accounts?|(?:\w+ )?(?:environments?|tenants?|workspaces?|"
        r"integrations?)|permissions|crm|erp|instances?)",
    ), (
        regular("own", "perform", "deliver", "support", "adjust", "maintain", "process") + "|" + silent_e("handl", "manag", "updat")
        + r"|do(?:es|ing)?|carr(?:y|ies|ied|ying) out",
        r"(?:system|software|product|account|user|platform|tenant|crm|erp|customer|client)(?: \w+)? (?:configurations?|"
        r"settings)|configurations?",
    ), (
        r"konfigurier\w*|konfiguration\w*|einricht\w*|einrichtung|parametrier\w*|customizing|aufsetz\w*|"
        r"richt(?:e|est|et)|provisionier\w*",
        r"systeme?\w*|software|konten|accounts?|\w*konten|plattform\w*|umgebung\w*|schnittstellen|"
        r"benutzer\w*|berechtigung\w*|crm\w*|erp\w*|\w*systeme?|anwendung\w*|parameter\w*|\w*einstellungen|"
        r"workflows?|nutzer\w*|zugänge|zugriffe|geräte|instanz\w*",
        "either",
    ), (
        None,
        r"konfigurier\w*|konfiguration\w*|parametrierung|systemkonfiguration\w*",
    )),
    "systems_integration": ((
        silent_e("integrat", "creat", "manag", "configur") + "|" + regular(
            "design", "implement", "extend", "monitor", "build", "develop", "maintain", "own", "support", "troubleshoot",
            "debug", "deliver", "fix", "lead") + r"|built|work(?:s|ed|ing)? on|set(?:s|ting)? up|led",
        r"(?:api|system|data|software|platform|third[- ]party|erp|crm|cloud|enterprise|saas|application|payment|hr|"
        r"backend) integrations?|api connections?|connectors?|webhooks?|middleware",
    ), (
        r"integrat(?:e|es|ing)|" + regular("sync", "connect", "link"),
        r"(?:\w+ )?(?:systems?|tools|apis?|platforms|services|applications|software|databases|data sources)|"
        r"erp|crm|apis?",
    ), (
        None,
        r"integrated (?:(?:the|our|their|several|multiple|various|customer|enterprise|external|third[- ]party|legacy|"
        r"partner|internal) )+(?:\w+ )?(?:systems?|tools|apis?|platforms|services|erp|crm)",
    ), (
        FIX_VERBS + "|" + regular("monitor"),
        r"data (?:exchange|flows?|feeds?|transfers?)|(?:api|integration) (?:errors?|failures?|issues?|problems?)|"
        r"integrations?",
    ), (
        r"entwickl\w*|bau(?:e|st|t|en)|anbind\w*|integrier\w*|pfleg\w*|implementier\w*|einricht\w*|verwalt\w*|"
        r"überwach\w*|konfigurier\w*|erstell\w*|verknüpf\w*|anbindung\w*|umsetz\w*|synchronisier\w*",
        r"schnittstellen?\w*|apis?|api-\w*|\w*anbindung\w*|drittsystem\w*|systemintegration\w*|"
        r"datenaustausch|datenflüsse|datenübertragung|integrationen|webhooks?|middleware",
        "either",
    ), (
        r"anbind\w*|integrier\w*|verknüpf\w*",
        r"systeme?|tools?|apps?|anwendungen|plattformen|software|drittsysteme?",
        "either",
    )),
    "teach": ((
        RUN_VERBS,
        TEACHING,
    ), (
        r"train(?:s|ed)?|teach(?:es|ing)?|taught|educat(?:e|es|ed)|instruct(?:s|ed)?|upskill(?:s|ed)?",
        PEOPLE,
    ), (
        None,
        r"training (?:new |junior |existing |internal |external )?(?:customers?|users?|clients?|staff|employees|"
        r"team members|partners|students|learners|participants|end[- ]users|hires)",
    ), (
        r"durchführ\w*|führ(?:e|st|t|en)|halt(?:e|est|et|en)|abhalt\w*|leit(?:e|est|et|en)|gestalt\w*|biet(?:e|est|et|en)|"
        r"geb(?:e|en|t)|gib(?:st)?|veranstalt\w*|organisier\w*|durchführung|planung|umsetzung|vermittl\w*|anbiet\w*",
        r"\w*schulungen?|trainings?|trainingseinheit\w*|webinar\w*|unterricht\w*|seminar\w*|einweisung\w*|kurse?|"
        r"lehrveranstaltung\w*|unterweisung\w*",
        "either",
    ), (
        r"schul(?:e|st|t|en)|trainier\w*|einweis\w*|unterricht\w*|unterweis\w*|ausbild\w*|anlern\w*|befähig\w*",
        DE_PEOPLE,
    )),
    "develop_learning": ((
        silent_e("creat", "updat", "produc", "prepar", "curat") + "|" + regular("develop", "design", "build", "draft",
                                                                              "maintain", "author") + r"|built|writ(?:e|es|ing)|wrote",
        LEARNING,
    ), (
        r"erstell\w*|entwickl\w*|konzipier\w*|pfleg\w*|aktualisier\w*|gestalt\w*|aufbau\w*|erarbeit\w*|entwurf|konzeption|"
        r"erstellung|entwicklung|bau(?:e|st|t|en)|überarbeit\w*|produzier\w*|aufbereit\w*",
        r"schulungsunterlagen|schulungsmaterial\w*|schulungskonzept\w*|schulungsinhalt\w*|trainingsmaterial\w*|"
        r"trainingsunterlagen|lerninhalt\w*|lernmaterial\w*|lernmodul\w*|curricul\w*|kurs\w*|e-learning\w*|lehrmaterial\w*|"
        r"lehrpläne?|schulungsprogramm\w*|trainingskonzept\w*|\w*schulungen|\w*trainings|"
        r"onboarding[- ]?(?:material|programm)\w*|lernpfad\w*|lernvideos?|tutorials?|schulungsvideos?",
        "either",
    )),
    "stakeholders": ((
        silent_e("coordinat", "liais", "involv", "influenc", "negotiat", "updat", "engag", "communicat", "collaborat", "manag")
        + "|" + regular("align", "consult", "partner", "interact", "present", "brief", "inform")
        + r"|work(?:s|ed|ing)? (?:closely |directly )?with",
        r"(?:\w+ )?stakeholders?|cross[- ]functional(?: \w+)?|(?:internal|external)(?: and (?:internal|external))? "
        r"(?:teams?|partners|departments|parties|customers|clients)|(?:other|multiple|various|all) "
        r"(?:departments|business units|functions)|business units",
    ), (
        r"abstimm\w*|koordinier\w*|kommunizier\w*|zusammenarbeit|arbeit(?:e|est|et|en) zusammen|austausch|"
        r"steuer(?:e|st|t|n)|beratung|koordination|einbind\w*|informier\w*",
        r"stakeholder\w*|fachbereich\w*|\w*abteilung\w*|\w*übergreifend\w*|interne?n? (?:und externe?n? )?(?:partner\w*|teams?)|"
        r"projektbeteiligte\w*|fachabteilung\w*|geschäftsbereich\w*|entscheidungsträger\w*",
        "either",
    )),
    "reconcile": ((
        silent_e("reconcil", "investigat", "resolv", "analys", "analyz", "handl", "compar") + "|" + regular(
            "clear", "correct", "match", "research", "flag", "audit") + r"|track(?:s|ed|ing)? down|"
            r"follow(?:s|ed|ing)? up on|identif(?:y|ies|ied|ying)",
        r"discrepanc\w*|exceptions?|variances?|mismatch\w*|unmatched \w+|open items|reconciliations?|"
        r"differences between \w+|unreconciled \w+",
    ), (
        r"abgleich\w*|abgleichen|abstimm\w*|klär\w*|prüf\w*|untersuch\w*|bearbeit\w*|beseitig\w*|identifizier\w*|"
        r"klärung|prüfung|bearbeitung",
        r"abweichung\w*|differenz\w*|diskrepanz\w*|klärfäll\w*|zahlungseingäng\w*|buchungen|offene posten|unstimmigkeit\w*|"
        r"fehlbuchung\w*|kontoauszüg\w*|zahlungen|rechnungen|belege|salden|kontenabstimmung\w*",
        "either",
    ), (
        None,
        r"reconciliations?|kontenabstimmung\w*|kontoabstimmung\w*|zahlungsabgleich\w*|kontenklärung\w*|bankabstimmung\w*",
    )),
}


def pair_pattern(actions, objects, either=False):
    if actions is None:
        return rf"\b(?:{objects})\b"
    window = r"\s+(?:[\w/#-]+\s+){0,5}"
    forward = rf"(?<![\w/#-])(?:{actions})\b{window}(?:{objects})\b"
    return rf"{forward}|\b(?:{objects})\b{window}(?<![\w/#-])(?:{actions})\b" if either else forward


TASK_PATTERNS = {
    task: re.compile("|".join(pair_pattern(*pair) for pair in pairs))
    for task, pairs in ACTION_OBJECTS.items()
}
INTENT_ONLY = re.compile(r"\b(?:learn(?:ing)? (?:to|about)|plans? to|planned to|want to|interested in|"
                         r"exposure to|read about|watched|observed)\b", re.I)


TASK_EXCLUSION = re.compile(r"\b(?:rather than|instead of|excluding|don t|doesn t|won t|statt|anstatt|anstelle von)\b", re.I)
POST_EXCLUSION = re.compile(r"^(?:is|are|was|were)?\s*(?:not in scope|not required|out of scope)\b", re.I)


OTHER_ACTOR = re.compile(r"\b(?:who|whose|whoever|whether|in case|so (?:that )?(?:they|others)|"
                         r"as (?:they|others)|damit|sodass|falls|sofern|(?:kunden|nutzer|anwender|kollegen|teams|mitarbeitende|partner) "
                         r"(?:können|sollen|werden|dürfen)|(?:vendors?|suppliers?|agencies|contractors?|teams?|teammates?|colleagues?) "
                         r"(?:that|which)|(?:tools?|systems?|agents?|bots?|models?|software|platforms?|automations?) (?:that|which)|"
                         r"(?:they|others|colleagues|teammates|clients|students|staff|vendors) "
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


LANGUAGE_TERM = re.compile(r"\b(?:german|english|french|spanish|deutsch(?!land)\w*|englisch\w*|"
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
                                r"sprachkenntnisse|verhandlungssicher\w*|fließend\w*|muttersprach\w*)\b", re.I)
STRONG_LANGUAGE = re.compile(r"\b(?:fluen\w*|native|verhandlungssicher\w*|fließend\w*|muttersprach\w*)\b", re.I)
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


def plain_language_line(text, bullet, section):
    return (not bullet and section in {"", "unclear"} and bool(LANGUAGE_TERM.search(text))
            and bool(LANGUAGE_LEVEL.search(text) or STRONG_LANGUAGE.search(text)))


def qualification_shaped(text):
    if QUALIFICATION_SHAPE.match(text):
        return True
    return bool(LANGUAGE_TERM.search(text) and (LANGUAGE_LEVEL.search(text) or LANGUAGE_QUALIFIER.search(text))
                and not ROLE_VERB.search(text))


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
        language_line = plain_language_line(text, bullet, section)
        if (not bullet and len(text.split()) < 3 and section not in {"mandatory", "preferred"}
                and not (MANDATORY.search(text) or OPTIONAL.search(text) or language_line)):
            continue
        tags = task_tags(text, catalogue)
        qualification = section == "core" and qualification_shaped(text)
        kind_section = "unclear" if qualification else section
        if NO_LANGUAGE.search(text) and not re.search(r"\b(?:but|however|aber|jedoch)\b", text, re.I):
            kind = "preferred"
        elif OPTIONAL.search(text) and MANDATORY.search(text) and kind_section != "preferred" and not re.search(
            r"\b(?:not required|nicht erforderlich)\b", text, re.I
        ):
            kind = "unclear"
        elif kind_section != "preferred" and ambiguous_language_preference(text):
            kind = "unclear"
        elif OPTIONAL.search(text) or kind_section == "preferred":
            kind = "preferred"
        elif (MANDATORY.search(text) or kind_section == "mandatory"
              or kind_section == "additional" and CANDIDATE_CONDITION.search(text)
              or kind_section == "unclear" and REQUIRED_QUALIFICATION.search(text)):
            kind = "mandatory"
        elif language_line:
            kind = "mandatory"
        elif kind_section == "unclear" and (qualification or bullet or re.match(r"^(?:experience|proficien|strong|knowledge|you have)", text, re.I)):
            kind = "unclear"
        elif ((section == "core" and (bullet or ROLE_VERB.search(text) or SECTION_DUTY.search(text)))
              or (tags and ROLE_VERB.search(text))):
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
