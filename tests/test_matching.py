from dataclasses import replace
from datetime import datetime, timezone
import unittest

from career_discovery.analysis import analyse_description, load_catalogue, task_tags
from career_discovery.demo import load_demo
from career_discovery.eligibility import check_requirement
from career_discovery.evaluation import demo_comparison
from career_discovery.matching import assess, deduplicate, possible_duplicates, run_match, split_ranked
from career_discovery.models import Evidence, Requirement, canonical_url


class MatcherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()
        cls.profiles, jobs, cls.labels = load_demo()
        cls.jobs = {job.external_id: job for job in jobs}
        cls.graduate, cls.teacher, cls.logistics, cls.health = cls.profiles
        cls.now = datetime(2026, 11, 16, tzinfo=timezone.utc)

    def findings(self, text, profile=None, kind="mandatory"):
        findings = check_requirement(Requirement("r001", kind, text), profile or self.graduate, self.catalogue)
        return [(found.subject, found.state) for found in findings]

    def assess(self, index, profile=None, **changes):
        return assess(replace(self.jobs[index], **changes), profile or self.graduate, self.catalogue, self.now)

    def test_guards_confirmed_profile_and_untrusted_evidence_states(self):
        with self.assertRaisesRegex(ValueError, "confirm"):
            run_match(self.jobs.values(), replace(self.graduate, confirmed=False), self.catalogue)
        self.assertNotIn("question-1", {item.id for item in self.graduate.usable_evidence})

    def test_c1_targets_the_stated_language(self):
        self.assertEqual(self.findings("English C1 required"), [("language (en)", "met")])
        self.assertEqual(self.findings("Deutsch C1 erforderlich"), [("language (de)", "conflict")])
        self.assertEqual(self.findings("English C1, German B2"), [
            ("language (en)", "met"), ("language (de)", "conflict"),
        ])

    def test_fluent_has_no_assumed_cefr_level(self):
        self.assertEqual(self.findings("Fluent German"), [("language (de)", "unknown")])
        self.assertEqual(self.findings("Native-level German and English proficiency at C1 level or higher"), [
            ("language (de)", "unknown"), ("language (en)", "met"),
        ])

    def test_preferred_skill_does_not_become_a_veto(self):
        record = self.assess("01")
        self.assertEqual(record.lane, "actionable")
        self.assertIn("preferred", {finding.state for finding in record.findings})
        self.assertTrue(any(link.kind == "transferable" for link in record.links))

    def test_different_task_does_not_match_despite_title(self):
        record = self.assess("03")
        self.assertGreater(record.baseline, 0)
        self.assertEqual(record.fit, "insufficient evidence")

    def test_explicit_known_gap_and_missing_evidence_differ(self):
        self.assertEqual(self.assess("16", self.logistics).lane, "excluded")
        self.assertEqual(self.findings("Python required", self.logistics), [("python", "unknown")])
        self.assertEqual(self.findings("German nursing licence required", self.health), [("known gap", "conflict")])

    def test_alternative_and_relevant_experience(self):
        self.assertEqual(self.findings("Currently enrolled or a recent graduate"), [("alternative paths", "met")])
        self.assertEqual(self.findings("3 years of SQL experience"), [("experience", "conflict")])
        self.assertEqual(self.findings("3 years of leadership experience"), [("experience", "unknown")])
        self.assertEqual(self.findings("Up to 2 years of experience"), [("experience", "unknown")])
        self.assertEqual(self.assess("14", self.logistics).lane, "actionable")

    def test_role_title_does_not_override_responsibilities(self):
        self.assertEqual(self.assess("04").fit, "strong fit")
        self.assertEqual(self.assess("04").baseline, 0)
        self.assertEqual(self.assess("02").lane, "excluded")

    def test_location_and_work_authorisation_uncertainty(self):
        self.assertEqual(self.assess("01", locations=()).lane, "verify first")
        self.assertEqual(self.assess("23", self.health).lane, "excluded")
        self.assertEqual(self.assess("23", self.health, remote_regions=()).lane, "verify first")
        self.assertEqual(self.assess("24", self.health).lane, "verify first")

    def test_closure_deadline_and_stale_verification(self):
        self.assertEqual(self.assess("01", availability="closed").lane, "excluded")
        self.assertEqual(self.assess("01", deadline="2026-11-15").lane, "excluded")
        row = self.assess("01", source="csv", availability="verified", checked_at="2026-11-01T00:00:00+00:00")
        self.assertEqual(row.lane, "verify first")

    def test_advertising_benefits_are_not_mandatory(self):
        rows = analyse_description("Requirements:\nGerman C1\nBenefits:\nExcel training\nFree lunches", self.catalogue)
        self.assertEqual([row.text for row in rows], ["German C1"])

    def test_same_title_distinct_requisitions_survive(self):
        records = [self.jobs["16"], self.jobs["17"]]
        self.assertEqual(len(list(deduplicate(records))), 2)
        same_location = replace(records[1], locations=records[0].locations)
        self.assertEqual(len(possible_duplicates([records[0], same_location])), 1)

    def test_url_tracking_and_requisition_id(self):
        self.assertEqual(canonical_url("https://employer.example/jobs?gh_jid=1&utm_source=a"),
                         "https://employer.example/jobs?gh_jid=1")
        with self.assertRaises(ValueError):
            canonical_url("https://username@employer.example/jobs")

    def test_negation_and_ownership(self):
        self.assertNotIn("sql", task_tags("I have never used SQL.", self.catalogue, evidence=True))
        scope = self.assess("04", description="Responsibilities:\n- Own the workflow and build dashboards independently.")
        self.assertEqual(scope.links[0].kind, "partial")

    def test_semantic_only_links_to_existing_evidence(self):
        source = self.assess("12", self.teacher)
        req = next(req for req in source.requirements if "handbooks" in req.text)
        row = assess(self.jobs["12"], self.teacher, self.catalogue, self.now,
                     semantic={(req.id, ""): {"evidence_id": "school-2", "reason": "Guide-writing supports this task."}})
        self.assertTrue(any(link.kind == "transferable" and link.evidence_id == "school-2" for link in row.links))

    def test_realistic_section_headings_keep_unknown_core_work(self):
        description = (
            "💡 Here's how you’ll make an impact:\n"
            "Team ownership:\n- Manage the accounting function.\n- Write runbooks for handovers.\n"
            "WHAT WE’RE LOOKING FOR\n- C1 German.\n- 5 years of accounting experience.\n"
            "NICE-TO-HAVES\n- Excel.\nWhy join us?\n- Support a growing team.\n"
        )
        rows = analyse_description(description, self.catalogue)
        self.assertEqual([row.kind for row in rows], ["core", "core", "mandatory", "mandatory", "preferred"])
        self.assertFalse(rows[0].tasks)
        row = self.assess("01", description=description)
        self.assertEqual(row.lane, "excluded")

    def test_unresolved_second_mandatory_condition_is_not_silently_ignored(self):
        self.assertEqual(self.findings("C1 English and leadership experience"), [
            ("language (en)", "met"), ("requirement", "unknown"),
        ])
        self.assertEqual(self.findings("Recent graduate within 12 months"), [("graduate status", "unknown")])
        self.assertEqual(self.findings("Strong SQL experience required"), [("sql", "unknown")])

    def test_incomplete_description_stays_in_review(self):
        row = self.assess("01", description="Responsibilities:\n- Troubleshoot complex issues.")
        self.assertEqual(row.lane, "verify first")
        self.assertTrue(any(item.subject == "responsibility coverage" for item in row.findings))

    def test_inline_mandatory_minimum_and_preferred_higher_german(self):
        text = ("DAS ERWARTET DICH BEI UNS:\n- Report KPIs.\n- Automate workflows.\n"
                "DAS BRINGST DU MIT:\n- Deutschkenntnisse mindestens B2, idealerweise C1, "
                "sowie Englischkenntnisse auf C1-Niveau.\n"
                "DAMIT PUNKTEST DU ZUSÄTZLICH\n- Reisebereitschaft.")
        rows = analyse_description(text, self.catalogue)
        self.assertEqual([row.kind for row in rows],
                         ["core", "core", "mandatory", "preferred", "mandatory", "preferred"])
        self.assertEqual(self.assess("01", description=text).lane, "excluded")
        self.assertEqual(self.findings("English C1/C2"), [("language (en)", "met")])

    def test_potential_transfer_from_realistic_english_headings(self):
        text = ("IN THIS ROLE, YOU WILL:\n- Resolve customer issues.\n- Assist with customer onboarding.\n"
                "WHAT YOU NEED TO BE SUCCESSFUL\n- English C1 is required; German is a strong advantage.")
        row = self.assess("01", description=text)
        self.assertEqual(row.fit, "transferable opportunity")
        self.assertEqual(row.lane, "actionable")

    def test_partial_task_evidence_only_affects_task_review_lane(self):
        text = ("Responsibilities:\n- Build dashboards.\n- Automate workflows with SQL.\n"
                "- Manage a calendar.\n- Deliver a legal review.\n- Schedule travel.")
        row = self.assess("01", description=text)
        self.assertEqual(row.fit, "partial task evidence")
        self.assertEqual(row.lane, "actionable")
        held, = split_ranked([row], "task")["verify first"]
        self.assertIn("task coverage", {finding.subject for finding in held.findings})
        self.assertEqual(split_ranked([row], "baseline")["actionable"], [row])

    def test_task_vocabulary_recognises_supported_forms_and_negation(self):
        catalogue = self.catalogue
        self.assertIn("experiment", task_tags("Ran A/B tests for a prototype.", catalogue, evidence=True))
        self.assertIn("data_quality", task_tags("Validated data before release.", catalogue, evidence=True))
        self.assertIn("systems_integration", task_tags("Integrated APIs for a demo.", catalogue, evidence=True))
        self.assertNotIn("systems_integration", task_tags("I never integrated APIs.", catalogue, evidence=True))

    def test_action_and_object_match_with_intervening_terms(self):
        examples = {
            "Ran two controlled online experiments.": "experiment",
            "Analysed weekly operational datasets.": "data_analysis",
            "Defined three quarterly success metrics.": "metric_design",
            "Reported on two operational metrics.": "report_kpis",
            "Built two internal performance dashboards.": "dashboard",
            "Validated two incoming datasets.": "data_quality",
            "Automated the internal review workflow.": "automate",
            "Compared several model outputs.": "evaluate_systems",
            "Documented several reconciliation procedures.": "document_process",
        }
        for text, task in examples.items():
            with self.subTest(task=task):
                self.assertIn(task, task_tags(text, self.catalogue, evidence=True))
        checks = [
            ("Observed staff as they ran two controlled online experiments.", "experiment"),
            ("Planned to automate the internal review workflow.", "automate"),
            ("Never compared any model outputs.", "evaluate_systems"),
            ("Streamlined the internal review workflow through manual changes.", "automate"),
            ("Investigated regional fashion trends.", "data_analysis"),
        ]
        for text, task in checks:
            with self.subTest(task=task):
                self.assertNotIn(task, task_tags(text, self.catalogue, evidence=True))

    def test_learning_material_is_evidence_while_learning_a_tool_is_not(self):
        tags = task_tags("Designed learning modules and designed assessments.", self.catalogue, evidence=True)
        self.assertIn("develop_learning", tags)
        self.assertNotIn("sql", task_tags("Learning SQL.", self.catalogue, evidence=True))

    def test_job_text_can_explicitly_exclude_a_task(self):
        text = "Build dashboards so others can track the product rather than running controlled experiments yourself."
        tags = task_tags(text, self.catalogue)
        self.assertIn("dashboard", tags)
        self.assertNotIn("experiment", tags)
        self.assertNotIn("experiment", task_tags("A/B testing is out of scope.", self.catalogue))

    def test_partial_linkage_requires_distinct_tasks_and_requirements(self):
        text = ("Responsibilities:\n- Build performance dashboards.\n- Report progress using KPIs.\n"
                "- Maintain inventory records.\n- Schedule delivery appointments.\n"
                "- Oversee trade documents.\n- Reconcile tax positions.")
        row = self.assess("01", description=text)
        self.assertEqual(row.fit, "partial task evidence")
        self.assertFalse(split_ranked([row], "task")["actionable"])
        similar = text.replace("Report progress using KPIs.", "Build weekly dashboards.")
        self.assertEqual(self.assess("01", description=similar).fit, "insufficient evidence")

    def test_mixed_language_conditions_and_additional_information(self):
        duties = "Responsibilities:\n- Report KPIs.\n- Automate workflows.\n"
        b2 = replace(self.graduate, languages={**self.graduate.languages, "de": "B2"})
        for conditions in ("Requirements: German B2, C1 preferred.",
                           "Requirements: German B2 (C1 preferred).",
                           "Requirements: German B2 but C1 preferred.",
                           "Requirements: German at least B2, with C1 preferred.",
                           "Requirements: German B2 required, English fluency is a plus.",
                           "Additional information:\nGerman B2 is required."):
            text = duties + conditions
            with self.subTest(conditions=conditions):
                self.assertEqual(self.assess("01", description=text).lane, "excluded")
                self.assertEqual(self.assess("01", b2, description=text).lane, "actionable")
        preferred = self.assess("01", b2, description=duties + "Requirements: German B2, C1 preferred.")
        self.assertIn(("C1 preferred.", "preferred"), [(item.text, item.kind) for item in preferred.requirements])
        benefits = self.assess("01", description=duties + "Benefits:\nGerman B2 is required.")
        self.assertEqual(benefits.lane, "actionable")
        ambiguous = self.assess("01", description=duties + "Requirements: German B2 and English C1 preferred.")
        self.assertEqual(ambiguous.lane, "verify first")

    def test_scope_specific_tenure_and_shared_tool_duration(self):
        months = {"relevant": 36, "sql": 0, "python": 26}
        profile = replace(self.graduate, experience_months=months)
        unknown = replace(profile, experience_months={"relevant": 36})
        for statement in ("Minimum 2 years of experience with SQL.", "Minimum 2 years of SQL experience.",
                          "2 years experience with SQL required"):
            self.assertEqual(self.findings(statement, profile), [("experience", "conflict")])
            self.assertEqual(self.findings(statement, unknown), [("experience", "unknown")])
        self.assertEqual(self.findings("2 years of experience required.", profile), [("experience", "met")])
        self.assertEqual(self.findings("2 years of work experience is a minimum.", profile), [("experience", "met")])
        for cap in ("Up to", "At most", "A maximum of"):
            for form in ("2 years of experience with SQL or Python", "2 years of SQL or Python experience"):
                self.assertEqual(self.findings(f"{cap} {form}", profile), [("alternative paths", "unknown")])
        self.assertEqual(self.findings("2 years of experience in payments.", profile), [("experience", "unknown")])
        for statement in ("2 years of SQL or Python experience", "2 years of experience with SQL or Python"):
            self.assertEqual(self.findings(statement, profile), [("alternative paths", "met")])
            self.assertEqual(self.findings(statement, unknown), [("alternative paths", "unknown")])
        self.assertEqual(self.findings("2 years of experience with SQL and Python", profile),
                         [("experience", "conflict"), ("experience", "met")])

    def test_clearance_and_other_residual_conditions_stay_in_review(self):
        duties = "Responsibilities:\n- Build dashboards.\n- Automate workflows.\n"
        conditions = ("Requirements: SQL required with active security clearance.",
                      "Additional information:\nA security clearance is required.",
                      "Additional information:\nA hydrogen handling certificate is required.")
        for condition in conditions:
            row = self.assess("01", description=duties + condition)
            self.assertEqual(row.lane, "verify first")
            requirement, = [req for req in row.requirements if req.kind == "mandatory"]
            confirmed = replace(self.graduate, verified_requirements=[requirement.text])
            self.assertEqual(self.assess("01", confirmed, description=duties + condition).lane, "actionable")
        gap = replace(self.graduate, known_gaps=["security clearance"])
        self.assertEqual(self.assess("01", gap, description=duties + conditions[0]).lane, "excluded")
        self.assertEqual(self.assess("01", description=duties + "Requirements: SQL required.").lane, "actionable")
        other = self.assess("01", description=duties + "Requirements: SQL required with weekend availability.")
        self.assertEqual(other.lane, "verify first")

    def test_direct_evidence_distinguishes_actor_and_hypothesis(self):
        for statement in ("Supported colleagues who built dashboards and analyzed data.",
                          "Observed several team members who then regularly ran controlled experiments.",
                          "Reviewed QA results to decide whether to run experiments.",
                          "I was asked to run experiments."):
            self.assertFalse({"dashboard", "data_analysis", "experiment"} &
                             set(task_tags(statement, self.catalogue, evidence=True)))
        self.assertIn("dashboard", task_tags("Built dashboards with colleagues.", self.catalogue, evidence=True))
        self.assertIn("experiment", task_tags("Ran experiments to test QA changes.", self.catalogue, evidence=True))
        self.assertIn("troubleshoot", task_tags("Helped troubleshoot errors.", self.catalogue, evidence=True))
        description = "Responsibilities:\n- Build dashboards.\n- Automate workflows."
        for statement in ("Managed a vendor that built dashboards and automated workflows.",
                          "Reviewed proposals to build dashboards and automate workflows."):
            profile = replace(self.graduate, evidence=(Evidence("case", statement, "test", "cv_stated"),))
            row = self.assess("01", profile, description=description)
            self.assertEqual(row.fit, "insufficient evidence")
            self.assertFalse(any(link.kind == "direct" for link in row.links))
        for statement, tasks in [
            ("Built dashboards with a vendor.", {"dashboard"}),
            ("Reviewed proposals, then built dashboards and automated workflows.", {"dashboard", "automate"}),
        ]:
            self.assertEqual(set(task_tags(statement, self.catalogue, evidence=True)), tasks)

    def test_coordinated_duties_and_repeated_task_coverage(self):
        evidence = Evidence("data", "Analysed sales data.", "test", "cv_stated")
        profile = replace(self.graduate, evidence=(*self.graduate.evidence, evidence))
        other = "\n- Publish press releases.\n- Manage a calendar.\n- Lead recruiting.\n- Prepare travel."
        combined = "Responsibilities:\n- Analyze sales data and build dashboards." + other
        separate = combined.replace(" and build", ".\n- Build")
        results = [self.assess("01", profile, description=text) for text in (combined, separate)]
        self.assertEqual([row.fit for row in results], ["partial task evidence"] * 2)
        self.assertEqual(results[0].rank, results[1].rank)
        self.assertTrue(all(split_ranked([row], "task")["verify first"] for row in results))
        repeated = self.assess("01", profile, description="Responsibilities:\n- Analyze sales data.\n- Analyze customer data.")
        self.assertNotEqual(repeated.fit, "strong fit")
        self.assertEqual(repeated.lane, "verify first")

    def test_requirement_and_seniority_review_exits_in_both_modes(self):
        text = "Responsibilities:\n- Build dashboards.\n- Automate workflows.\nYour profile:\nStrong communication skills."
        title = "Lead Analyst"
        profile = replace(self.graduate, search_titles=[title])
        initial = self.assess("01", profile, title=title, description=text)
        self.assertEqual(initial.lane, "verify first")
        self.assertEqual({item.subject for item in initial.findings if item.state == "unknown"},
                         {"requirement intent", "seniority and ownership"})
        confirmed = replace(profile, verified_requirements=["Strong communication skills.",
                            f"Seniority and ownership: {initial.job.url}"])
        complete = self.assess("01", confirmed, title=title, description=text)
        for mode in ("task", "baseline"):
            self.assertEqual(split_ranked([initial], mode)["verify first"], [initial])
            self.assertEqual(split_ranked([complete], mode)["actionable"], [complete])

    def test_demo_compares_all_pairs(self):
        result = demo_comparison(self.profiles, self.jobs.values(), self.labels, self.catalogue)
        self.assertEqual(sum(row["judged_pairs"] for row in result["profiles"]), 96)
        self.assertTrue(result["profiles"][0]["task"]["scenario_discoveries"])


if __name__ == "__main__":
    unittest.main()
