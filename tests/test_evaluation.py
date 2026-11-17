from copy import deepcopy
from dataclasses import replace
import unittest

from career_discovery.analysis import load_catalogue
from career_discovery.demo import load_demo
from career_discovery.evaluation import demo_comparison, pilot_metrics
from career_discovery.matching import run_match
from career_discovery.pilot import prepare_review
from career_discovery.semantic import accepted_by_profile, brief, validated_proposals


def fictional_proposal():
    profiles, jobs, _ = load_demo()
    request = brief(profiles, jobs, load_catalogue())
    pair = next(row for row in request["pairs"] if row["profile"] == "teacher" and row["job_key"].endswith('"12"]'))
    req = next(item for item in pair["requirements"] if "handbooks" in item["excerpt"])
    evidence = next(item for item in pair["evidence"] if item["id"] == "school-2")
    item = {"profile": "teacher", "job_key": pair["job_key"], "requirement_id": req["id"],
            "task_id": "", "evidence_id": evidence["id"], "requirement_excerpt": req["excerpt"],
            "evidence_excerpt": evidence["excerpt"],
            "reason": "Guide-writing transfers to documenting recurring procedures. Operator exceptions are a new context."}
    return request, {"version": 1, "brief_id": request["brief_id"], "proposals": [item]}


class EvaluationTests(unittest.TestCase):
    def test_semantic_proposals_stay_in_original_profile_and_need_review(self):
        request, proposal = fictional_proposal()
        self.assertEqual(len(validated_proposals(request, proposal)), 1)
        with self.assertRaisesRegex(ValueError, "reviewed"):
            accepted_by_profile(request, proposal)
        reviewed = accepted_by_profile(request, {**proposal, "accepted": [1]})
        self.assertEqual(set(reviewed), {"teacher"})
        profiles, jobs, labels = load_demo()
        report = demo_comparison(profiles, jobs, labels, load_catalogue(), semantic=reviewed)
        teacher = report["profiles"][1]
        first, = [row for row in teacher["hybrid"]["jobs"] if row["title"] == "Enablement Coordinator"]
        self.assertTrue(any(link["evidence_id"] == "school-2" and "Operator exceptions" in link["rationale"]
                            for link in first["evidence_links"]))
        tampered = deepcopy(proposal)
        tampered["proposals"][0]["evidence_excerpt"] = "Claim not present in the source."
        with self.assertRaisesRegex(ValueError, "preserve"):
            accepted_by_profile(request, {**tampered, "accepted": [1]})

    def test_semantic_brief_rejects_real_profile_and_real_vacancies(self):
        profiles, jobs, _ = load_demo()
        with self.assertRaisesRegex(ValueError, "fictional"):
            brief([replace(profiles[0], fictional=False)], jobs, load_catalogue())
        with self.assertRaisesRegex(ValueError, "fictional"):
            brief(profiles, [replace(jobs[0], source="csv")], load_catalogue())

    def test_blind_deck_keeps_candidate_evidence_and_method_labels_out(self):
        profiles, jobs, _ = load_demo()
        rows = run_match(jobs, profiles[0], load_catalogue())
        deck, key = prepare_review(rows, "participant-01")
        self.assertEqual(deck, prepare_review(list(reversed(rows)), "participant-01")[0])
        self.assertNotIn("baseline", str(deck))
        self.assertNotIn(profiles[0].evidence[0].text, str(deck))
        ids = {row["job_id"] for row in deck["vacancies"]}
        for result in key["participants"][0]["methods"].values():
            self.assertTrue(set(result["actionable_ids"]).issubset(ids))

    def test_deck_selects_baseline_review_results_even_without_actionable_jobs(self):
        profiles, jobs, _ = load_demo()
        catalogue = load_catalogue()
        listing = replace(jobs[0], title="Data Analyst", availability="unverified",
                          description="Responsibilities:\n- Develop a contact strategy.\n- Review inventory.")
        row, = run_match([listing], profiles[0], catalogue)
        self.assertGreater(row.baseline, 0)
        self.assertEqual(row.fit, "insufficient evidence")
        deck, key = prepare_review([row], "participant-01", audit_sample=0, full_corpus=True)
        judgement, = deck["judgements"]
        methods = key["participants"][0]["methods"]
        self.assertEqual(methods["baseline"]["review_first_ids"], [judgement["job_id"]])
        self.assertEqual(methods["task"]["review_first_ids"], [])
        self.assertFalse(methods["baseline"]["actionable_ids"] or methods["task"]["actionable_ids"])
        incomplete = pilot_metrics(key)["participants"][0]
        baseline = incomplete["methods"]["baseline"]["verify_first"]
        self.assertEqual(baseline["label_status"], "incomplete")
        self.assertEqual(baseline["label_coverage"]["relevance"]["rate"], 0)
        self.assertIsNone(baseline["precision"]["rate"])
        self.assertIsNone(baseline["verified_link_rate"]["rate"])
        self.assertIsNone(incomplete["methods"]["task"]["missed_relevant_ids"])
        judgement.update(relevant=True, realistic=True, open=True, hard_conflict=False)
        complete = pilot_metrics(key)["participants"][0]
        self.assertTrue(complete["complete_corpus_relevance_labels"])
        self.assertEqual(complete["methods"]["baseline"]["verify_first"]["relevant_coverage"]["rate"], 1)
        self.assertEqual(complete["methods"]["task"]["missed_relevant_ids"], [judgement["job_id"]])

    def test_human_evaluation_reports_numerators_and_uncompleted_sessions(self):
        input_data = {"participants": [{
            "id": "sample-01", "would_reuse": True, "ran_again": False, "onboarding_minutes": 7,
            "judgements": [
                {"job_id": "new", "relevant": True, "realistic": True, "hard_conflict": False, "open": True,
                 "adjacent": True, "previously_known": False, "would_consider": True},
                {"job_id": "old", "relevant": True, "realistic": True, "hard_conflict": False, "open": True},
                {"job_id": "bad", "relevant": False, "realistic": False, "hard_conflict": None, "open": None},
            ],
            "methods": {
                "baseline": {"actionable_ids": ["old", "bad"], "completed_searches": 1},
                "task": {"actionable_ids": ["old", "new"], "completed_searches": 1, "minutes_to_three": None,
                         "claims_audited": 3, "claims_supported": 2, "fabricated_claims": 0},
                "manual": {"actionable_ids": ["old"], "minutes_to_three": None},
            },
        }]}
        report = pilot_metrics(input_data)
        self.assertEqual(report["methods"]["baseline"]["false_positive_rate"]["rate"], 1)
        self.assertEqual(report["methods"]["task"]["precision"]["rate"], 1)
        self.assertEqual(report["methods"]["task"]["explanation_accuracy"]["denominator"], 3)
        self.assertEqual(report["methods"]["task"]["usd_per_search"], 0)
        self.assertEqual(report["participants_with_task_discovery"]["numerator"], 1)
        self.assertIsNone(report["median_paired_minutes_saved"])
        self.assertEqual(report["ran_again"]["numerator"], 0)


if __name__ == "__main__":
    unittest.main()
