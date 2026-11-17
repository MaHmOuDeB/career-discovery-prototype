"""Application tracker rules: statuses, follow-up dates and spreadsheet-safe export."""

import csv
from datetime import date, timedelta
from io import StringIO

STATUSES = ("saved", "applied", "interview", "offer", "rejected", "withdrawn")
FOLLOW_UP_WORKING_DAYS = 7
NOTES_LIMIT = 2000
COLUMNS = ("company", "title", "status", "applied_on", "follow_up_on", "notes", "url", "updated_at")


class FieldErrors(ValueError):
    def __init__(self, fields):
        super().__init__("; ".join(fields.values()))
        self.fields = fields


def add_working_days(start, days):
    """Monday to Friday only. Public holidays are not known to the app."""
    current = start
    while days:
        current += timedelta(days=1)
        days -= current.weekday() < 5
    return current


def parse_day(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Use a date written as YYYY-MM-DD.")
    return date.fromisoformat(value)


def normalise_application(data, existing, today):
    """Validate a tracker update against the stored row. Follow-up defaults to 7 working days after applying."""
    errors = {}
    base = existing or {}
    status = data.get("status", base.get("status"))
    if status not in STATUSES:
        errors["status"] = "Choose one of: " + ", ".join(STATUSES) + "."
    days = {}
    for field in ("applied_on", "follow_up_on"):
        value = data.get(field, base.get(field))
        if value in (None, ""):
            days[field] = None
            continue
        try:
            parse_day(value)
            days[field] = value
        except ValueError:
            errors[field] = "Use a date written as YYYY-MM-DD."
    notes = data.get("notes", base.get("notes", ""))
    if not isinstance(notes, str) or len(notes) > NOTES_LIMIT:
        errors["notes"] = f"Notes can have at most {NOTES_LIMIT} characters."
    if errors:
        raise FieldErrors(errors)
    applied = days["applied_on"]
    if status in {"applied", "interview", "offer"} and not applied:
        applied = today.isoformat()
    follow = days["follow_up_on"]
    previous_default = (base.get("applied_on") and
                        add_working_days(date.fromisoformat(base["applied_on"]), FOLLOW_UP_WORKING_DAYS).isoformat())
    if applied and "follow_up_on" not in data and (not follow or follow == previous_default):
        follow = add_working_days(date.fromisoformat(applied), FOLLOW_UP_WORKING_DAYS).isoformat()
    return {"job_key": data.get("job_key", base.get("job_key")), "status": status, "applied_on": applied,
            "follow_up_on": follow, "notes": notes.strip()}


def spreadsheet_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in {"=", "+", "-", "@", "\t", "\r"} else text


def applications_csv(rows):
    out = StringIO(newline="")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(COLUMNS)
    for row in rows:
        writer.writerow([spreadsheet_cell(row.get(name)) for name in COLUMNS])
    return "﻿" + out.getvalue()
