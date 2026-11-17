from io import BytesIO
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest import mock
from zipfile import ZipFile

from career_discovery.analysis import load_catalogue
from career_discovery import documents
from career_discovery.documents import docx_segments, document_data, extract_profile, pdf_segments

DOCUMENT_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def docx_fixture(paragraphs):
    from xml.sax.saxutils import escape

    body = "".join(f"<w:p><w:r><w:t>{escape(line)}</w:t></w:r></w:p>" for line in paragraphs)
    return docx_archive(f'<w:document xmlns:w="{DOCUMENT_NS}"><w:body>{body}</w:body></w:document>')


def docx_archive(content):
    data = BytesIO()
    with ZipFile(data, "w") as package:
        package.writestr("[Content_Types].xml", """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
            <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
            <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
            </Types>""")
        package.writestr("_rels/.rels", """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
            <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
            </Relationships>""")
        package.writestr("word/document.xml", content)
    return data.getvalue()


def pdf_fixture():
    text = b"BT /F1 12 Tf 72 750 Td (Projects) Tj 0 -18 Td (Built dashboards from a fictional case.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(text)} >>\nstream\n".encode() + text + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    file = b"%PDF-1.4\n"
    offsets = []
    for index, item in enumerate(objects, 1):
        offsets.append(len(file))
        file += f"{index} 0 obj\n".encode() + item + b"\nendobj\n"
    xref = len(file)
    file += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    file += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
    return file + f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


class DocumentsTests(unittest.TestCase):
    def test_docx_draft_keeps_source_context_and_ignores_contact_profile_lines(self):
        cv = docx_fixture(["Fictional Person", "user@sample.example", "Nationality: hidden",
                           "Projects", "Built dashboards from fictional tickets.",
                           "Skills", "Excel, SQL, Power BI"])
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "fictional.docx"
            file.write_bytes(cv)
            data, digest = document_data(file)
        profile = extract_profile("synthetic", ".docx", data, digest, load_catalogue())
        self.assertFalse(profile.confirmed)
        self.assertEqual([item.state for item in profile.evidence], ["cv_stated", "inferred"])
        self.assertEqual(profile.evidence[0].locator, "DOCX paragraph 5")
        self.assertEqual(profile.evidence[0].context, "project")
        self.assertNotIn("sample.example", str(profile))

    def test_action_based_import_keeps_scope_and_source_reference(self):
        cv = docx_fixture(["Projects", "Optimised a queue in a classroom exercise.",
                           "Integrated APIs in a fictional demo."])
        profile = extract_profile("synthetic", ".docx", cv, "a" * 64, load_catalogue())
        self.assertEqual([e.state for e in profile.evidence], ["cv_stated", "cv_stated"])
        self.assertEqual([e.locator for e in profile.evidence], ["DOCX paragraph 2", "DOCX paragraph 3"])
        self.assertEqual(profile.evidence[0].text, "Optimised a queue in a classroom exercise.")

    def test_docx_does_not_resolve_entities_or_external_parts(self):
        xml = f'<!DOCTYPE x [<!ENTITY bomb "unexpected">]><w:document xmlns:w="{DOCUMENT_NS}"><w:body/></w:document>'
        with self.assertRaisesRegex(ValueError, "unsupported"):
            list(docx_segments(docx_archive(xml)))

    def test_docx_rejects_non_archive_and_scan_fallback_has_message(self):
        with self.assertRaisesRegex(ValueError, "DOCX"):
            list(docx_segments(b"broken"))
        with self.assertRaisesRegex(ValueError, "manual profile"):
            extract_profile("synthetic", ".docx", docx_fixture(["Nothing recognisable"]), "a" * 64, load_catalogue())

    @unittest.skipUnless(shutil.which("pdftotext"), "Poppler executable not installed")
    def test_text_based_pdf_preserves_page_and_line(self):
        data = pdf_fixture()
        self.assertIn(("PDF page 1, extracted line 2", "Built dashboards from a fictional case."),
                      list(pdf_segments(data)))
        profile = extract_profile("synthetic", ".pdf", data, "b" * 64, load_catalogue())
        self.assertEqual(profile.evidence[0].context, "project")
        self.assertEqual(profile.evidence[0].locator, "PDF page 1, extracted line 2")


if __name__ == "__main__":
    unittest.main()


class FakeProcess:
    def __init__(self, output, returncode=0, block=False):
        self.stdout = FakeStream(output, self, block)
        self.returncode = None
        self.final = returncode
        self.killed = threading.Event()

    def kill(self):
        self.killed.set()
        if self.returncode is None:
            self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = self.final
        return self.returncode


class FakeStream:
    def __init__(self, output, process, block):
        self.data = BytesIO(output)
        self.process = process
        self.block = block
        self.closed = False

    def read(self, size):
        if self.block:
            self.process.killed.wait(5)
            return b""
        return self.data.read(size)

    def close(self):
        self.closed = True


class PdfLimitTests(unittest.TestCase):
    def run_pdf(self, process, seconds=None):
        paths = []

        def popen(command, **kwargs):
            paths.append(Path(command[-2]))
            self.assertTrue(paths[0].is_file())
            self.assertEqual(Path(paths[0]).read_bytes(), b"%PDF-1.4 fake")
            self.assertIs(kwargs["stdout"], subprocess.PIPE)
            return process

        patches = [mock.patch.object(documents.shutil, "which", return_value="pdftotext"),
                   mock.patch.object(documents.subprocess, "Popen", side_effect=popen)]
        if seconds is not None:
            patches.append(mock.patch.object(documents, "PDF_SECONDS", seconds))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        try:
            return list(pdf_segments(b"%PDF-1.4 fake"))
        finally:
            self.assertFalse(paths[0].exists())

    def test_temp_copy_is_removed_when_the_process_raises(self):
        with mock.patch.object(documents.shutil, "which", return_value="pdftotext"), \
                mock.patch.object(documents.subprocess, "Popen", side_effect=RuntimeError("boom")):
            before = set(Path(tempfile.gettempdir()).glob("cd-*.pdf"))
            with self.assertRaises(RuntimeError):
                list(pdf_segments(b"%PDF-1.4 fake"))
            self.assertEqual(set(Path(tempfile.gettempdir()).glob("cd-*.pdf")), before)

    def test_stale_named_temp_copies_are_cleaned_up(self):
        import os, time
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(tempfile, "tempdir", folder):
            old, fresh, other = (Path(folder) / n for n in ("cd-old.pdf", "cd-new.pdf", "keep.pdf"))
            for path in (old, fresh, other):
                path.write_bytes(b"x")
            os.utime(old, (time.time() - 7200, time.time() - 7200))
            documents.remove_stale_temp_copies()
            self.assertEqual((old.exists(), fresh.exists(), other.exists()), (False, True, True))

    def test_pdf_copy_uses_the_cd_prefix(self):
        names = []
        real = tempfile.mkstemp

        def spy(*a, **k):
            result = real(*a, **k)
            names.append(Path(result[1]).name)
            return result

        with mock.patch.object(documents.shutil, "which", return_value="pdftotext"), \
                mock.patch.object(documents.tempfile, "mkstemp", side_effect=spy), \
                mock.patch.object(documents.subprocess, "Popen", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                list(pdf_segments(b"%PDF-1.4 fake"))
        self.assertTrue(names[0].startswith("cd-") and names[0].endswith(".pdf"))

    def test_normal_output_is_split_into_pages_and_lines(self):
        process = FakeProcess(b"Built dashboards.\nUsed SQL.\fSecond page")
        self.assertEqual(self.run_pdf(process), [
            ("PDF page 1, extracted line 1", "Built dashboards."),
            ("PDF page 1, extracted line 2", "Used SQL."),
            ("PDF page 2, extracted line 1", "Second page"),
        ])

    def test_output_over_the_cap_is_killed_and_rejected(self):
        process = FakeProcess(b"a" * (documents.MAX_TEXT + 1))
        with self.assertRaisesRegex(ValueError, "within the limits"):
            self.run_pdf(process)
        self.assertTrue(process.killed.is_set())

    def test_output_exactly_at_the_cap_is_accepted(self):
        process = FakeProcess(b"a" * documents.MAX_TEXT)
        self.assertEqual(len(self.run_pdf(process)), 1)

    def test_timeout_kills_the_process_and_reports_incomplete_extraction(self):
        process = FakeProcess(b"", block=True)
        with self.assertRaisesRegex(ValueError, "did not complete"):
            self.run_pdf(process, seconds=0.05)
        self.assertTrue(process.killed.is_set())

    def test_failing_extractor_is_reported(self):
        with self.assertRaisesRegex(ValueError, "within the limits"):
            self.run_pdf(FakeProcess(b"", returncode=1))

    def test_missing_poppler_is_reported(self):
        with mock.patch.object(documents.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "Poppler"):
                list(pdf_segments(b"%PDF-1.4 fake"))

