import unittest

from career_discovery.analysis import load_catalogue, task_tags

POSITIVE = {
    "troubleshoot": [
        "Resolve escalated customer cases within the agreed response times",
        "Investigate and fix integration errors reported by clients",
        "Diagnose production incidents and document the findings",
        "Perform root-cause analysis for recurring outages",
        "Debug problems in the billing workflow",
        "Solve technical issues raised by users",
        "Du analysierst und löst technische Probleme im Kundensupport",
        "Bearbeitung von Support-Tickets und Eskalationen",
        "Fehleranalyse bei Störungen im laufenden Betrieb",
        "Du behebst Fehler in der Datenübertragung",
    ],
    "triage": [
        "Prioritise incoming support tickets by severity and route them to the right team",
        "Escalate critical incidents to the on-call engineer",
        "Categorise inbound customer requests and assign owners",
        "Du priorisierst eingehende Tickets nach Dringlichkeit",
    ],
    "onboard": [
        "Guide new clients through the onboarding process",
        "Own customer onboarding for mid-market accounts",
        "Support the onboarding of new merchants",
        "Du begleitest neue Kunden durch den Onboarding-Prozess",
        "Durchführung des Kunden-Onboardings",
    ],
    "configuration": [
        "Configure customer accounts and permissions in the admin console",
        "Set up user environments for new tenants",
        "Handle system configuration requests from clients",
        "Du konfigurierst Kundensysteme nach den Anforderungen",
        "Einrichtung von Benutzerkonten und Berechtigungen",
    ],
    "systems_integration": [
        "Build and maintain API integrations between the CRM and billing tools",
        "Integrate with third-party services and legacy systems",
        "Fix data exchange problems between the ERP and the warehouse system",
        "Du entwickelst und pflegst Schnittstellen zwischen ERP und CRM",
        "Anbindung externer Systeme über APIs",
    ],
    "document_process": [
        "Write knowledge-base articles for common customer questions",
        "Maintain help centre articles and internal runbooks",
        "Document support processes and keep the documentation current",
        "Update process documentation after every release",
        "Du dokumentierst Prozesse und pflegst die Wissensdatenbank",
        "Dokumentation von Prozessen und Arbeitsanweisungen",
    ],
    "report_kpis": [
        "Report on key metrics to the operations team every week",
        "Prepare weekly KPI reports for management",
        "Track service-level metrics and flag deviations",
        "Maintain reporting that shows operational metrics",
        "Erstellung von Reports zu den wichtigsten Kennzahlen",
        "Du wertest Kennzahlen aus und berichtest an die Geschäftsführung",
        "Kennzahlen im Reporting überwachen",
    ],
    "dashboard": [
        "Build Looker dashboards for the support team",
        "Maintain Metabase reports for the finance team",
        "Create dashboards to visualise customer trends",
        "Aufbau von Dashboards in Power BI",
        "Du erstellst Dashboards für die Geschäftsleitung",
    ],
    "data_analysis": [
        "Analyse customer data to find patterns behind churn",
        "Interpret survey data and spot trends",
        "Analyse von Daten zur Ableitung von Maßnahmen",
        "Du analysierst Verkaufsdaten und erkennst Muster",
        "Du führst Datenanalysen durch",
    ],
    "data_quality": [
        "Clean and deduplicate CRM data on a regular basis",
        "Validate customer records before each import",
        "Ensure the accuracy of master data across systems",
        "Du pflegst Kundendaten im CRM",
        "Pflege der Kundendaten und Sicherstellung der Datenqualität",
    ],
    "teach": [
        "Deliver training sessions to new customers",
        "Run onboarding workshops for key users",
        "Facilitate weekly webinars for partners",
        "Conduct end-user training after each release",
        "Train new team members on the ticketing tool",
        "Durchführung von Schulungen für Kunden",
        "Du führst Schulungen und Workshops für Anwender durch",
        "Du schulst neue Mitarbeitende im Umgang mit dem System",
    ],
    "develop_learning": [
        "Create training materials for new hires",
        "Develop e-learning courses on the product",
        "Update customer training content after releases",
        "Du erstellst Schulungsunterlagen und E-Learning-Module",
        "Entwicklung von Trainingsmaterialien",
    ],
    "stakeholders": [
        "Coordinate with stakeholders across product and finance",
        "Align cross-functional teams on release dates",
        "Communicate project status to key stakeholders",
        "Abstimmung mit Stakeholdern und Fachbereichen",
        "Du koordinierst interne Abteilungen",
    ],
    "reconcile": [
        "Investigate discrepancies between payment records and invoices",
        "Resolve exceptions in the settlement report",
        "Du klärst Abweichungen zwischen Zahlungseingängen und Rechnungen",
        "Abgleich von Buchungen und Kontoauszügen",
    ],
    "automate": [
        "Automate repetitive reporting work with scripts",
        "Build automations that remove manual steps",
        "Automatisierung von Prozessen und Reports",
        "Du automatisierst manuelle Aufgaben",
    ],
}

NEGATIVE = [
    # Look-alikes found by the blind precision review of public duty lines (paraphrased).
    ("report_kpis", "Prepare detailed internal audit reports for the board"),
    ("report_kpis", "Own the HR system reporting layer, including standard and custom reports"),
    ("report_kpis", "Provide transparent status reporting on project risks"),
    ("report_kpis", "Erstellung von Prüfberichten für die Qualitätssicherung"),
    ("systems_integration", "Manage integrations and relationships with banking partners"),
    ("systems_integration", "Own media sponsorship integrations across channels"),
    ("configuration", "Validate software configurations during acceptance testing"),
    ("configuration", "Build AI tools that configure agents for customers"),
    ("troubleshoot", "Build AI tools that help diagnose issues for support teams"),
    ("document_process", "Keep accurate documentation of department inventory"),
    ("troubleshoot", "Answer customer inquiries by email and phone"),
    ("troubleshoot", "Respond to inquiries from partners within one day"),
    ("troubleshoot", "Beantworte Kundenanfragen per E-Mail und Telefon"),
    ("troubleshoot", "You will not resolve customer tickets because tier two handles them"),
    ("troubleshoot", "Du löst keine Probleme im Support, das übernimmt ein anderes Team"),
    ("troubleshoot", "Clients can resolve issues themselves in the portal"),
    ("troubleshoot", "Damit Kunden Probleme selbst lösen können, pflegst du das Portal"),
    ("troubleshoot", "Handle cases of annual leave and payroll"),
    ("stakeholders", "Work with the team to deliver the roadmap"),
    ("stakeholders", "Zusammenarbeit im Team"),
    ("teach", "Attend training sessions during the first week"),
    ("teach", "Receive training and mentoring from senior colleagues"),
    ("teach", "Run daily stand-up sessions with the team"),
    ("teach", "Teilnahme an Schulungen und Weiterbildungen"),
    ("onboard", "Support HR with employee onboarding and payroll administration"),
    ("systems_integration", "Support the integration of new colleagues into the team"),
    ("report_kpis", "Report to the Head of Operations"),
    ("report_kpis", "Create reports of site visits"),
    ("dashboard", "Check the dashboard of the delivery van"),
    ("data_analysis", "Analyse competitor pricing pages"),
    ("document_process", "Write unit tests for new features"),
    ("data_quality", "Keep a clean desk and tidy records room"),
    ("develop_learning", "Attend a course on negotiation"),
    ("troubleshoot", "Du verbesserst Problemlösungen im Team durch KI-Tools"),
    ("systems_integration", "Du vernetzt interne Teams und externe Partner"),
    ("systems_integration", "Lead the testing of integrated optical systems"),
    ("teach", "Build systems to quality-check data used to train AI agents"),
    ("teach", "Lead customer workshops and run stakeholder alignment sessions"),
    ("onboard", "Connect product, sales and onboarding data to find user friction"),
    ("data_quality", "Maintain customer data protections and permission boundaries"),
    ("document_process", "Identify where processes create unnecessary manual work"),
    ("automate", "Write production code for infrastructure automation"),
    ("automate", "Develop an automation roadmap for the team"),
    ("automate", "Automation is not part of this role"),
    ("automate", "Kein Interesse an Automatisierung von Prozessen"),
]


class VocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue = load_catalogue()

    def test_duty_lines_map_to_their_task(self):
        for task, lines in POSITIVE.items():
            for line in lines:
                with self.subTest(task=task, line=line):
                    self.assertIn(task, task_tags(line, self.catalogue))

    def test_look_alike_and_negated_lines_do_not_map(self):
        for task, line in NEGATIVE:
            with self.subTest(task=task, line=line):
                self.assertNotIn(task, task_tags(line, self.catalogue))

    def test_intent_only_evidence_does_not_map(self):
        for line in ("I want to learn to build dashboards", "Interested in resolving support tickets",
                     "Learning to automate reports", "Planned to run training sessions"):
            with self.subTest(line=line):
                self.assertEqual(task_tags(line, self.catalogue, evidence=True), ())

    def test_asserted_evidence_maps(self):
        self.assertIn("troubleshoot", task_tags("Resolved support tickets for customers", self.catalogue, evidence=True))
        self.assertIn("teach", task_tags("Delivered training sessions to staff", self.catalogue, evidence=True))


if __name__ == "__main__":
    unittest.main()
