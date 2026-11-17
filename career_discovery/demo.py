"""Reproducible offline scenario. All people and vacancies are fictional."""

from pathlib import Path
import json

from .models import Job, Profile

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def load_demo():
    profiles = [Profile.load(data) for data in json.loads((FIXTURES / "profiles.json").read_text())]
    jobs = []
    for index, company, title, location, employment, description, *options in json.loads(
        (FIXTURES / "vacancies.json").read_text()
    ):
        jobs.append(Job.load({
            "source": "fictional", "board": "demo", "external_id": index, "company": company,
            "title": title, "url": f"https://vacancies.example/{index}", "description": description,
            "locations": [location] if location else [], "employment": employment,
            "availability": "fixture_open", **(options[0] if options else {}),
        }))
    labels = json.loads((FIXTURES / "labels.json").read_text())
    return profiles, jobs, labels
