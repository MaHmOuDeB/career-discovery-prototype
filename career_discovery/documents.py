"""Local evidence extraction from untrusted text-based CV files."""

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from zipfile import BadZipFile, ZipFile

from .analysis import BULLET, normal, task_tags
from .models import Evidence, Profile, identifier
from .storage_limits import read_bytes
from .word_xml import segments as xml_segments

MAX_DOCUMENT = 12 * 1024 * 1024
MAX_XML = 2 * 1024 * 1024
MAX_TEXT = 512 * 1024
EXTRACTOR_VERSION = b"cv-text-v2:"
START_ACTION = re.compile(
    r"^(?:I\s+)?(?:analysed|analyzed|assessed|automated|built|collaborated|conducted|coordinated|created|"
    r"debugged|delivered|designed|developed|documented|evaluated|helped|implemented|integrated|"
    r"investigated|maintained|managed|mapped|measured|monitored|operated|optimised|optimized|"
    r"partnered|performed|planned|prepared|processed|queried|ran|reconciled|reported|resolved|"
    r"reviewed|supported|tested|trained|troubleshot|used|validated|verified|worked|wrote|"
    r"analysierte|entwickelte|erstellte|"
    r"führte|koordinierte|pflegte|unterstützte|wertete)\b", re.I,
)
CONTACT = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|https?://\S+", re.I)
PROTECTED_HEADER = re.compile(r"^\s*(?:nationality|sex|gender|religion|date of birth|"
                              r"nationalität|geschlecht|religion|geburtsdatum|familienstand)\b", re.I)
CONTEXTS = {
    "experience": "experience", "work experience": "experience", "professional experience": "experience",
    "employment": "experience", "berufserfahrung": "experience", "praktika": "internship",
    "education": "education", "ausbildung": "education", "studium": "education",
    "projects": "project", "personal projects": "project", "projekte": "project",
    "skills": "skills", "technical skills": "skills", "kenntnisse": "skills",
    "internships": "internship", "internship": "internship",
    "volunteering": "volunteering", "ehrenamt": "volunteering",
}


def document_data(path):
    path = Path(path)
    if path.suffix.casefold() not in {".docx", ".pdf"}:
        raise ValueError("Import a text-based PDF or DOCX, or start a manual profile.")
    data = read_bytes(path, MAX_DOCUMENT)
    return data, sha256(EXTRACTOR_VERSION + data).hexdigest()


def docx_segments(data):
    try:
        with ZipFile(BytesIO(data)) as package:
            member = package.getinfo("word/document.xml")
            if member.file_size > MAX_XML:
                raise ValueError("DOCX main document is too large.")
            with package.open(member) as stream:
                xml = stream.read(MAX_XML + 1)
    except (BadZipFile, KeyError, RuntimeError, NotImplementedError) as exc:
        raise ValueError("Could not extract the main text from this DOCX.") from exc
    # Remove encoding variability before detecting XML features that are unnecessary here.
    try:
        text = xml.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("DOCX main document must use UTF-8 XML.") from exc
    if len(xml) > MAX_XML or re.search(r"<!\s*(?:doctype|entity)\b", text, re.I):
        raise ValueError("DOCX XML uses unsupported features or exceeds the text limit.")
    try:
        yield from xml_segments(text)
    except ImportError as exc:
        # Some macOS Homebrew builds link pyexpat against an incompatible
        # system library. Use the already-installed macOS interpreter for XML only.
        fallback = Path("/usr/bin/python3")
        if sys.platform != "darwin" or not fallback.is_file():
            raise ValueError("Python's XML parser is unavailable. Use PDF or manual entry.") from exc
        try:
            result = subprocess.run(
                [str(fallback), "-I", "-B", str(Path(__file__).with_name("word_xml.py"))],
                input=text.encode("utf-8"), capture_output=True, timeout=8,
            )
        except (OSError, subprocess.SubprocessError) as failure:
            raise ValueError("The backup DOCX parser did not complete.") from failure
        if result.returncode:
            raise ValueError("Could not parse the DOCX body with the local XML parser.")
        yield from json.loads(result.stdout)


PDF_SECONDS = 12


def _run_pdftotext(program, path):
    process = subprocess.Popen(
        [program, "-f", "1", "-l", "12", "-q", "-layout", "-enc", "UTF-8", str(path), "-"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    expired = threading.Event()

    def expire():
        expired.set()
        process.kill()

    timer = threading.Timer(PDF_SECONDS, expire)
    timer.start()
    try:
        raw = process.stdout.read(MAX_TEXT + 1)
        if len(raw) > MAX_TEXT:
            process.kill()
            process.wait()
            raise ValueError("PDF text could not be extracted within the limits. Use manual entry or DOCX.")
        process.wait()
        if expired.is_set():
            raise subprocess.TimeoutExpired(program, PDF_SECONDS)
    finally:
        timer.cancel()
        process.kill()
        process.wait()
        process.stdout.close()
    if process.returncode:
        raise ValueError("PDF text could not be extracted within the limits. Use manual entry or DOCX.")
    return raw


def pdf_segments(data):
    if not data.startswith(b"%PDF-"):
        raise ValueError("The file does not have a supported PDF header.")
    program = shutil.which("pdftotext")
    if not program:
        raise ValueError("PDF extraction needs the local Poppler pdftotext tool. DOCX and manual entry also work.")
    handle, name = tempfile.mkstemp(suffix=".pdf")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        raw = _run_pdftotext(program, name)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError("PDF extraction did not complete. Copy the evidence into a manual profile.") from exc
    finally:
        Path(name).unlink(missing_ok=True)
    for page, content in enumerate(raw.decode("utf-8", errors="replace").split("\f"), 1):
        for line, part in enumerate(content.splitlines(), 1):
            yield f"PDF page {page}, extracted line {line}", part


def extract_profile(profile_id, suffix, data, digest, catalogue, existing=None):
    segments = docx_segments(data) if suffix.casefold() == ".docx" else pdf_segments(data)
    items = []
    context = ""
    for locator, raw in segments:
        text = BULLET.sub("", raw.strip())
        heading = normal(text.strip(":"))
        if heading in CONTEXTS:
            context = CONTEXTS[heading]
            continue
        text = CONTACT.sub("", text).strip()
        if not text or len(text) > 1600 or PROTECTED_HEADER.search(text):
            continue
        action = START_ACTION.search(text)
        tagged = task_tags(text, catalogue, evidence=True)
        if not action and not tagged:
            continue
        state = "cv_stated" if action and context != "skills" else "inferred"
        items.append(Evidence(f"cv-{len(items) + 1:03}", text, locator, state, context=context))
        if len(items) >= 150:
            break
    if not items:
        raise ValueError("No usable text evidence was extracted. This may be a scan. Start a manual profile.")
    profile = existing or Profile(identifier(profile_id), False, False, ())
    manual = tuple(e for e in profile.evidence if not e.id.startswith("cv-"))
    if len(items) + len(manual) > 200:
        raise ValueError("This revision would exceed the profile limit. Reduce the manually added entries first.")
    return replace(profile, confirmed=False, evidence=tuple(items) + manual, document_hash=digest)
