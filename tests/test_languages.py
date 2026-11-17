import unittest

from career_discovery.analysis import LANGUAGE_TERM, analyse_description, load_catalogue
from career_discovery.eligibility import check_requirement
from career_discovery.models import Profile, Requirement


class LanguageRequirementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()
        cls.profile = Profile("p", True, True, (), languages={"de": "B1", "en": "C1"})

    def findings(self, text, kind="mandatory"):
        found = check_requirement(Requirement("r001", kind, text), self.profile, self.catalogue)
        return [(item.subject, item.state) for item in found]

    def kinds(self, description):
        return {row.text: row.kind for row in analyse_description(description, self.catalogue)}

    def test_or_better_is_a_floor_not_an_alternative(self):
        for text in ("German B2 or better", "Deutsch B2 oder besser", "German C1 or higher",
                     "Deutsch B2 oder höher", "Deutsch B2 oder darüber"):
            self.assertEqual(self.findings(text), [("language (de)", "conflict")], text)
        self.assertEqual(self.findings("English C1 or higher"), [("language (en)", "met")])

    def test_real_alternatives_stay_alternatives(self):
        self.assertEqual(self.findings("German B2 or English C1"), [("alternative paths", "met")])

    def test_plain_language_lines_outside_headed_sections_are_kept(self):
        for lead in ("Your profile:\n", "Dein Profil:\n", ""):
            rows = self.kinds(f"{lead}Deutsch C1\nFließend Deutsch")
            self.assertEqual(rows.get("Deutsch C1"), "mandatory", lead)
            self.assertEqual(rows.get("Fließend Deutsch"), "mandatory", lead)

    def test_optional_wording_keeps_such_lines_preferred(self):
        self.assertEqual(self.kinds("Fließend Deutsch wäre von Vorteil").get("Fließend Deutsch wäre von Vorteil"),
                         "preferred")

    def test_skip_and_preferred_sections_are_unchanged(self):
        self.assertNotIn("Deutsch C1", self.kinds("Benefits:\nDeutsch C1"))
        self.assertEqual(self.kinds("Nice to have:\nDeutsch C1").get("Deutsch C1"), "preferred")

    def test_qualifier_only_stays_unknown(self):
        for text in ("gute Deutschkenntnisse", "Fließend Deutsch", "Verhandlungssicheres Deutsch",
                     "Muttersprachliches Deutsch", "Fluent German"):
            self.assertEqual(self.findings(text), [("language (de)", "unknown")], text)

    def test_native_forms_are_qualifiers(self):
        for text in ("Native-level German", "German (native)", "native German speaker"):
            self.assertEqual(self.findings(text), [("language (de)", "unknown")], text)
            rows = self.kinds(f"Your profile:\n{text}")
            self.assertEqual(rows.get(text), "mandatory", text)

    def test_hyphenated_compounds_name_the_language(self):
        self.assertEqual(self.findings("Deutsch- und Englischkenntnisse"),
                         [("language (de)", "unknown"), ("language (en)", "unknown")])
        self.assertEqual(self.findings("Deutsch- und Englischkenntnisse C1"),
                         [("language (de)", "conflict"), ("language (en)", "met")])

    def test_deutschland_is_not_a_language(self):
        self.assertIsNone(LANGUAGE_TERM.search("Standort Deutschland"))
        self.assertTrue(LANGUAGE_TERM.search("Deutsch- und Englischkenntnisse"))
        self.assertFalse([s for s, _ in self.findings("Arbeiten in Deutschland") if s.startswith("language")])


if __name__ == "__main__":
    unittest.main()


class SharedAndUnclearLanguageTests(unittest.TestCase):
    def setUp(self):
        from career_discovery.demo import load_demo
        self.profile = next(p for p in load_demo()[0] if p.id == "technical-graduate")

    def test_shared_level_covers_both_coordinated_languages(self):
        from career_discovery.eligibility import language_findings
        states = {f.subject: f.state for f in language_findings("Deutsch- und Englischkenntnisse auf C1-Niveau",
                                                                 self.profile)}
        self.assertEqual(states, {"language (de)": "conflict", "language (en)": "met"})

    def test_unclear_bullet_still_gets_a_language_check(self):
        from career_discovery.analysis import load_catalogue
        from career_discovery.eligibility import check_requirement
        from career_discovery.models import Requirement
        findings = check_requirement(Requirement("r001", "unclear", "Deutsch auf C2-Niveau", ()), self.profile,
                                     load_catalogue())
        self.assertIn(("language (de)", "conflict"), {(f.subject, f.state) for f in findings})
        self.assertIn("requirement intent", {f.subject for f in findings})
