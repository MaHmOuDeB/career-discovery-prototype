"""The German UI swaps the matcher's English reason sentences for entries in web/i18n/reasons.de.json.

This mirrors reasonText() in web/js/util.js and fails when the code writes a reason sentence with no entry.
"""
import ast
import itertools
import json
from pathlib import Path
import re
import unittest

PACKAGE = Path(__file__).resolve().parents[1] / "career_discovery"
TABLE = json.loads((PACKAGE / "web" / "i18n" / "reasons.de.json").read_text("utf-8"))
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")
SLOT = re.compile(r"\{(\w+)\}")
SOURCES = ("eligibility.py", "matching.py", "sources.py", "network.py", "models.py")
# Call keywords and the positional index of the reason in Finding(state, subject, excerpt, reason).
REASON_KEYWORDS = {"reason", "verification_reason"}
REASON_CONSTANTS = {"FEED_REMOVAL", "MANUAL_VERIFICATION_PREFIX"}


def compile_entry(en):
    parts = re.split(r"(\{\w+\})", en)
    source = "".join("(.+?)" if SLOT.fullmatch(part) else re.escape(part) for part in parts)
    return re.compile(f"^{source}$"), SLOT.findall(en)


ENTRIES = [(*compile_entry(en), de) for en, de in TABLE["sentences"]]


def translate(text):
    out = []
    for sentence in SENTENCE.split(text):
        for pattern, names, de in ENTRIES:
            found = pattern.match(sentence)
            if found:
                values = dict(zip(names, found.groups()))
                out.append(SLOT.sub(lambda m: TABLE["values"].get(m.group(1), {}).get(values[m.group(1)],
                                                                                    values[m.group(1)]), de))
                break
        else:
            out.append(sentence)
    return " ".join(out)


def known(sentence):
    return any(pattern.match(sentence) for pattern, _, _ in ENTRIES)


def variants(node):
    """Every text a string expression can produce; unknown parts become a short placeholder word."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        pieces = [variants(v) if isinstance(v, ast.Constant) else ["x1"] for v in node.values]
        return ["".join(p) for p in itertools.product(*pieces)]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return [a + b for a in variants(node.left) for b in variants(node.right)]
    if isinstance(node, ast.IfExp):
        return variants(node.body) + variants(node.orelse)
    if isinstance(node, ast.Tuple):
        return [text for item in node.elts for text in variants(item)]
    return [""]


def reason_texts():
    found = []
    for name in SOURCES:
        tree = ast.parse((PACKAGE / name).read_text("utf-8"))
        for node in ast.walk(tree):
            nodes = []
            if isinstance(node, ast.Call):
                callee = getattr(node.func, "id", getattr(node.func, "attr", ""))
                if callee == "Finding" and len(node.args) >= 4:
                    nodes.append(node.args[3])
                if callee == "NetworkUnavailable" and node.args:
                    nodes.append(node.args[0])
                nodes += [kw.value for kw in node.keywords if kw.arg in REASON_KEYWORDS]
            elif isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if set(targets) & REASON_CONSTANTS:
                    nodes.append(node.value)
                for target in node.targets:
                    if isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                        for slot, value in zip(target.elts, node.value.elts):
                            if isinstance(slot, ast.Name) and slot.id == "reason":
                                nodes.append(value)
            for value in nodes:
                found += [(name, text) for text in variants(value)]
    return found


class ReasonTranslationTests(unittest.TestCase):
    def test_every_reason_sentence_in_the_code_has_a_german_entry(self):
        texts = reason_texts()
        self.assertGreater(len(texts), 50)
        missing = set()
        for name, text in texts:
            if text.startswith("User recorded a manual check as "):
                text += "x1."
            for sentence in SENTENCE.split(text.strip()):
                # A bare placeholder is text from elsewhere (an ad excerpt or a joined reason), not a sentence.
                if sentence and sentence != "x1" and not sentence.startswith("Public request failed for "):
                    if not known(sentence):
                        missing.add(f"{name}: {sentence}")
        self.assertEqual(sorted(missing), [])

    def test_entries_are_unique_and_keep_their_placeholders(self):
        english = [en for en, _ in TABLE["sentences"]]
        self.assertEqual(len(english), len(set(english)))
        for en, de in TABLE["sentences"]:
            self.assertEqual(sorted(SLOT.findall(en)), sorted(SLOT.findall(de)), en)
            self.assertTrue(de.strip() and de != en, en)

    def test_composed_reasons_translate_sentence_by_sentence(self):
        text = ("Path 1: conflict. The profile lists German at B1. The ad specifies C1. "
                "Path 2: unknown. Minimum of 24 months in sql experience. Comparable tenure is unconfirmed.")
        self.assertEqual(translate(text),
                         "Weg 1: Konflikt. Dein Profil nennt Deutsch auf Niveau B1. Die Anzeige verlangt C1. "
                         "Weg 2: offen. Mindestens 24 Monate Erfahrung (Bereich: sql). "
                         "Vergleichbare Erfahrungsdauer ist nicht bestätigt.")

    def test_an_unknown_sentence_stays_english(self):
        self.assertEqual(translate("Something new. Read the full description."),
                         "Something new. Lies die ganze Beschreibung.")

    def test_the_ui_uses_the_same_sentence_split(self):
        util = (PACKAGE / "web" / "js" / "util.js").read_text("utf-8")
        self.assertIn(r"const SENTENCE = /(?<=[.!?])\s+(?=[A-Z(])/;", util)


if __name__ == "__main__":
    unittest.main()
