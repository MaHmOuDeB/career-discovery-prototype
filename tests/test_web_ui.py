import json
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "career_discovery" / "web"
I18N_ATTRS = ("data-i18n", "data-i18n-aria-label", "data-i18n-title", "data-i18n-placeholder")
JS_KEY = re.compile(r"""(?<![\w.$])t\(\s*(['"])([A-Za-z0-9_.\-]+)\1""")
JS_DYNAMIC = re.compile(r"""(?<![\w.$])t\(\s*[`A-Za-z]""")
URL = re.compile(r"https?://", re.I)
IMPORT = re.compile(r"""(?:from|import)\s*\(?\s*['"](\.{1,2}/[^'"]+)['"]""")


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.keys, self.refs, self.inline_scripts, self.style_attrs, self.handlers = set(), [], 0, 0, 0
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for name in I18N_ATTRS:
            if a.get(name):
                self.keys.add(a[name])
        if "style" in a:
            self.style_attrs += 1
        self.handlers += sum(1 for k in a if k.startswith("on"))
        if tag == "script":
            if a.get("src"):
                self.refs.append(a["src"])
            else:
                self.in_script = True
        if tag == "style":
            self.style_attrs += 1
        if tag == "link" and a.get("href"):
            self.refs.append(a["href"])
        if tag in {"img", "source", "iframe"} and a.get("src"):
            self.refs.append(a["src"])

    def handle_data(self, data):
        if self.in_script and data.strip():
            self.inline_scripts += 1

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False


def page():
    parser = Page()
    parser.feed((WEB / "index.html").read_text("utf-8"))
    return parser


def js_files():
    return sorted(WEB.rglob("*.js"))


def catalog(lang):
    return json.loads((WEB / "i18n" / f"{lang}.json").read_text("utf-8"))


class WebUiTests(unittest.TestCase):
    def test_catalogues_have_identical_keys_and_placeholders(self):
        en, de = catalog("en"), catalog("de")
        self.assertEqual(set(en), set(de))
        for key in en:
            self.assertEqual(set(re.findall(r"\{(\w+)\}", en[key])), set(re.findall(r"\{(\w+)\}", de[key])), key)
            self.assertTrue(en[key].strip() and de[key].strip(), key)

    def test_every_key_used_exists_in_both_files(self):
        used = set(page().keys)
        for path in js_files():
            text = path.read_text("utf-8")
            self.assertIsNone(JS_DYNAMIC.search(text), f"{path.name}: use literal keys in t()")
            used |= {m.group(2) for m in JS_KEY.finditer(text)}
        self.assertTrue(used)
        for lang in ("en", "de"):
            self.assertEqual(sorted(used - set(catalog(lang))), [], lang)

    def test_page_has_no_external_urls_inline_script_or_style(self):
        parser = page()
        self.assertEqual((parser.inline_scripts, parser.style_attrs, parser.handlers), (0, 0, 0))
        for path in [WEB / "index.html", *WEB.rglob("*.css"), *js_files()]:
            self.assertIsNone(URL.search(path.read_text("utf-8")), path.name)

    def test_referenced_assets_exist(self):
        refs = page().refs
        self.assertTrue(refs)
        for ref in refs:
            self.assertTrue((WEB / ref.lstrip("/")).is_file(), ref)
        for path in js_files():
            for ref in IMPORT.findall(path.read_text("utf-8")):
                self.assertTrue((path.parent / ref).resolve().is_file(), f"{path.name}: {ref}")

    def test_token_meta_and_no_style_attribute_in_js(self):
        self.assertIn('name="cd-token"', (WEB / "index.html").read_text("utf-8"))
        for path in js_files():
            text = path.read_text("utf-8")
            self.assertNotRegex(text, r"setAttribute\(\s*['\"]style|\beval\(|new Function|\.style\.")


if __name__ == "__main__":
    unittest.main()
