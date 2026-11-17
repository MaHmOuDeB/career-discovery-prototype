import unittest

from career_discovery.salary import extract_salary

POSITIVE = [
    ("Salary: €55,000 - €65,000 per year", "€55,000 - €65,000 per year"),
    ("The salary range is 60,000–70,000 EUR gross.", "60,000–70,000 EUR"),
    ("Compensation: $120k-$150k", "$120k-$150k"),
    ("We pay £45,000 per annum.", "£45,000 per annum"),
    ("Gehalt: 55.000 € bis 65.000 € brutto/Jahr", "55.000 € bis 65.000 €"),
    ("Wir bieten ein Jahresgehalt von 48.000 Euro.", "48.000 Euro"),
    ("Vergütung: ca. 3.500 € brutto monatlich", "3.500 €"),
    ("Base pay of $95,000 to $110,000 annually", "$95,000 to $110,000 annually"),
    ("Pay range: EUR 70.000 - 85.000", "EUR 70.000 - 85.000"),
    ("OTE €80k–€100k", "€80k–€100k"),
    ("Stundenlohn 15,50 €", "15,50 €"),
    ("We offer €22 per hour", "€22 per hour"),
    ("Zwischen 50.000 und 60.000 Euro Gehalt", "50.000 und 60.000 Euro"),
    ("Salary band 55-65k EUR", "55-65k EUR"),
    ("About us.\nGehalt: 52.000 € p.a.\nApply now.", "52.000 € p.a."),
]

NEGATIVE = [
    "We raised €50 million in Series B and our salary is competitive.",
    "Learning budget of €1,000 per year",
    "Salary: competitive, based on experience",
    "Attraktive Vergütung und 30 Tage Urlaub",
    "Referral bonus of €2,000",
    "Over 5,000 employees and revenue of $2bn",
    "Gehalt nach Vereinbarung",
    "Pay: not disclosed",
    "Home office allowance €50 per month",
    "Founded in 2015 with 200 people in Berlin",
    "Fluent English (C1) and 3-5 years of experience",
    "Relocation package up to €5,000",
    "Sign-on bonus €1,000; salary to be discussed",
    "Our budget is $10,000 and we pay attention to detail",
    "Salary:\nCompetitive.\nBenefits: €30 gym voucher",
    "",
    None,
]


class SalaryTests(unittest.TestCase):
    def test_amounts_next_to_a_pay_word_are_returned(self):
        for text, expected in POSITIVE:
            with self.subTest(text=text):
                self.assertEqual(extract_salary(text), expected)

    def test_everything_else_is_not_stated(self):
        for text in NEGATIVE:
            with self.subTest(text=text):
                self.assertIsNone(extract_salary(text))


if __name__ == "__main__":
    unittest.main()
