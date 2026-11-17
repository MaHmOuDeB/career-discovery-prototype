from datetime import datetime, timezone
import unittest

from career_discovery.analysis import MANDATORY, analyse_description, heading_kind, load_catalogue
from career_discovery.demo import load_demo
from career_discovery.eligibility import eligibility
from career_discovery.matching import assess
from career_discovery.models import Job, Requirement


class ParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()
        cls.profile = load_demo()[0][0]
        cls.now = datetime(2026, 11, 16, tzinfo=timezone.utc)

    def kinds(self, description):
        return [(row.kind, row.text) for row in analyse_description(description, self.catalogue)]

    def test_dash_headings_use_whichever_side_is_recognised(self):
        self.assertEqual(heading_kind("YOUR SKILLSET — WHAT YOU BRING TO THE TABLE"), "unclear")
        self.assertEqual(heading_kind("Brilliant people – what you bring"), "unclear")
        self.assertEqual(heading_kind("Aufgaben - Das erwartet dich"), "core")
        self.assertEqual(heading_kind("Requirements - what to expect"), "mandatory")
        self.assertIsNone(heading_kind("Our culture - how we work"))

    def test_new_heading_labels(self):
        expected = {
            "core": ["You will", "You'll", "Your role", "Deine Rolle", "Ihre Rolle", "Dein Verantwortungsbereich",
                     "Deine Verantwortung", "Deine Verantwortlichkeiten"],
            "unclear": ["Who you are", "You are", "You have", "Your experience", "Your skills", "Your skillset",
                        "What you bring to the table", "Das zeichnet dich aus", "Was dich auszeichnet",
                        "Deine Skills", "Deine Qualifikationen", "Ihre Qualifikationen"],
            "skip": ["You'll get", "What you'll get", "What you'll get in return", "Working conditions",
                     "Why join now", "Deine Benefits", "Wir bieten dir"],
        }
        for kind, labels in expected.items():
            for label in labels:
                with self.subTest(label=label):
                    self.assertEqual(heading_kind(label), kind)

    def test_sentence_starting_like_a_heading_is_not_a_heading(self):
        self.assertIsNone(heading_kind("You will work with the finance team on monthly reports"))
        text = "You will\n- Resolve escalated support cases for customers\n- Document runbooks for the team"
        self.assertEqual([kind for kind, _ in self.kinds(text)], ["core", "core"])
        self.assertEqual(self.kinds("You will work with the finance team on monthly reports"), [])

    def test_headings_open_sections_in_a_listing(self):
        text = ("Your role:\n- Resolve escalated support cases\n- Maintain the knowledge base\n"
                "Who you are\n- Curious and structured\n"
                "What you'll get\n- Maintain a great office dog")
        rows = self.kinds(text)
        self.assertEqual([kind for kind, _ in rows], ["core", "core", "unclear"])

    def test_qualification_lines_in_a_core_section_are_not_duties(self):
        text = ("Your tasks:\n"
                "- Resolve escalated support cases\n"
                "- Experience in customer support\n"
                "- 3+ years of experience with SQL is required\n"
                "- Strong knowledge of dashboards is a plus\n"
                "- Fluent in German (C2)\n"
                "- Verhandlungssicheres Deutsch\n"
                "- Abgeschlossenes Studium der Wirtschaft\n"
                "- Erfahrung in der Kundenbetreuung\n"
                "- Sprachkenntnisse in Englisch")
        rows = dict((text, kind) for kind, text in self.kinds(text))
        self.assertEqual(rows["Resolve escalated support cases"], "core")
        self.assertEqual(rows["Experience in customer support"], "unclear")
        self.assertEqual(rows["3+ years of experience with SQL is required"], "mandatory")
        self.assertEqual(rows["Strong knowledge of dashboards is a plus"], "preferred")
        self.assertEqual(rows["Fluent in German (C2)"], "mandatory")
        self.assertEqual(rows["Verhandlungssicheres Deutsch"], "unclear")
        self.assertEqual(rows["Abgeschlossenes Studium der Wirtschaft"], "unclear")
        self.assertEqual(rows["Erfahrung in der Kundenbetreuung"], "unclear")
        self.assertEqual(rows["Sprachkenntnisse in Englisch"], "unclear")

    def test_duties_that_mention_experience_later_stay_core(self):
        text = ("Your tasks:\n- Du nutzt Deine Erfahrung, um Kunden zu beraten\n"
                "- Use your expertise to advise customers\n"
                "- Apply your experience to coach new colleagues")
        self.assertEqual([kind for kind, _ in self.kinds(text)], ["core", "core", "core"])

    def test_mandatory_wording(self):
        for phrase in ("this is a hard requirement", "Python is a must", "a must", "essential skill",
                       "Führerschein ist Pflicht", "Voraussetzung ist ein Studium"):
            with self.subTest(phrase=phrase):
                self.assertTrue(MANDATORY.search(phrase))
        self.assertFalse(MANDATORY.search("Pflichten und Aufgaben"))
        for duty in ("Maintain essential reports for finance", "Erstellung essentieller Reports",
                     "Pflege der Pflichtfelder im CRM"):
            with self.subTest(duty=duty):
                self.assertFalse(MANDATORY.search(duty))

    def test_knowledge_base_duty_stays_a_duty(self):
        text = "Your responsibilities\n- Knowledge base: write and maintain help articles\n- Knowledge of SQL"
        self.assertEqual([kind for kind, _ in self.kinds(text)], ["core", "unclear"])

    def test_hard_requirement_language_conflicts_under_unrecognised_and_dash_headings(self):
        line = "German proficiency at C2 - this is a hard requirement"
        for prefix in ("Something unusual\n", "Our culture - how we work\n", ""):
            with self.subTest(prefix=prefix):
                job = Job("test", "board", "p1", "Example Care", "Care coordinator", "https://example.com/p1",
                          description=prefix + line, locations=("Berlin",))
                record = assess(job, self.profile, self.catalogue, self.now)
                self.assertIn(("language (de)", "conflict"),
                              {(finding.subject, finding.state) for finding in record.findings})

    def test_core_requirement_with_explicit_level_gets_language_findings(self):
        job = Job("test", "board", "p2", "Example Care", "Care coordinator", "https://example.com/p2",
                  locations=("Berlin",))
        core = (Requirement("r001", "core", "Communicate with residents in German at C2 level"),)
        findings = eligibility(job, self.profile, core, self.catalogue, today=self.now.date())
        self.assertIn(("language (de)", "unknown"), {(finding.subject, finding.state) for finding in findings})
        self.assertNotIn(("language (de)", "conflict"), {(f.subject, f.state) for f in findings})
        plain = (Requirement("r001", "core", "Resolve escalated support cases"),)
        self.assertNotIn("language (de)", {f.subject for f in eligibility(job, self.profile, plain, self.catalogue,
                                                                          today=self.now.date())})


if __name__ == "__main__":
    unittest.main()


class SectionDutyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()

    def kinds(self, description):
        return [row.kind for row in analyse_description(description, self.catalogue)]

    def test_plain_german_and_english_duty_lines_under_a_duties_heading(self):
        text = ("Deine Aufgaben\n"
                "Du analysierst Kennzahlen im Vertrieb und leitest Maßnahmen ab\n"
                "Sie erstellen wöchentliche Auswertungen für das Management\n"
                "Erstellung von Reports für die Geschäftsführung\n"
                "Pflege der Kundendaten im CRM\n"
                "Produce the weekly pipeline overview for the sales lead\n"
                "Du bist ein Organisationstalent\n"
                "Sie verfügen über gute Excel-Kenntnisse")
        self.assertEqual(self.kinds(text), ["core"] * 5)


class DutyShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()

    def rows(self, description):
        return [(row.kind, row.text) for row in analyse_description(description, self.catalogue)]

    def test_german_qualifications_are_not_duties_after_duty_headings(self):
        for line in ("Du kennst dich mit SQL aus", "Du beherrschst Excel und Python", "Du denkst analytisch",
                     "Du weißt, wie Daten fließen", "Berufserfahrung in der Analyse von Daten",
                     "Ausbildung oder Studium in der Wirtschaft", "Kenntnisse in der Datenanalyse"):
            with self.subTest(line=line):
                self.assertNotIn("core", [kind for kind, _ in self.rows(f"Deine Aufgaben\n{line}")], line)

    def test_german_duty_forms_stay_core(self):
        for line in ("Du analysierst Kennzahlen im Vertrieb", "Erstellung von Reports für die Geschäftsführung",
                     "Erfahrungsberichte erstellen und Dokumentation pflegen"):
            with self.subTest(line=line):
                self.assertEqual([kind for kind, _ in self.rows(f"Deine Aufgaben\n- {line}")], ["core"], line)

    def test_duties_starting_with_a_shape_word_stay_core(self):
        for line in ("Background checks on new vendors", "Knowledge transfer sessions for new hires",
                     "Experience reports are compiled for customers"):
            with self.subTest(line=line):
                self.assertEqual([kind for kind, _ in self.rows(f"Responsibilities\n- {line}")], ["core"], line)

    def test_real_qualification_lines_stay_unclear_in_core(self):
        for line in ("Experience with SQL", "5 years of experience in analytics", "3+ years experience",
                     "Knowledge of Python", "Degree in economics", "Background in finance",
                     "Berufserfahrung in der Datenanalyse", "Erfahrung mit SQL", "Strong experience, ideally in retail",
                     "Familiarity with dashboards"):
            with self.subTest(line=line):
                self.assertNotEqual([kind for kind, _ in self.rows(f"Responsibilities\n- {line}")], ["core"], line)
