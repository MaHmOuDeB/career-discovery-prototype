"""Plain terminal output with control codes removed from imported text."""

import json
import unicodedata


def safe_text(text):
    return "".join(c for c in str(text) if c in "\n\t" or not unicodedata.category(c).startswith("C"))


def json_output(value):
    # Escaped ASCII prevents hostile format or terminal control characters from being emitted.
    return json.dumps(value, ensure_ascii=True, indent=2)


def short_list(records):
    lines = []
    for index, record in enumerate(records, 1):
        line = ", ".join(record["locations"] or record["remote_regions"])
        where = f" ({line})" if line else ""
        lines.extend([f"{index}. {record['title']} — {record['company']}{where} [{record['fit']}]",
                      f"   {record['apply_url']}",
                      f"   Availability: {record['availability']}"
                      + (f" at {record['checked_at']}" if record["checked_at"] else "")])
        source = record["source"]
        if record["date"]:
            source += f" · {record['date_kind'].replace('_', ' ')} {record['date']}"
        lines.append(f"   Source: {source}")
        for found in record["findings"]:
            if found["state"] in {"unknown", "conflict"}:
                lines.append(f"   {found['state'].capitalize()} — {found['subject']}. {found['reason']}")
                if found["excerpt"]:
                    lines.append(f"     Employer/source text: {found['excerpt']}")
        checked = [found["subject"] for found in record["findings"] if found["state"] == "met"]
        if checked:
            lines.append("   Conditions matched: " + ", ".join(dict.fromkeys(checked)))
        optional = [found["excerpt"] for found in record["findings"] if found["state"] == "preferred"]
        if optional:
            lines.append("   Preferred (up to three shown): " + " / ".join(optional[:3]))
        by_id = {req["id"]: req for req in record["requirements"]}
        for link in record["evidence_links"]:
            lines.append(f"   {link['kind'].replace('_', ' ').capitalize()} — {by_id[link['requirement_id']]['text']}")
            if "evidence" in link:
                item = link["evidence"]
                lines.append(f"     {item['id']} ({item['locator']}): {item['text']}")
            lines.append(f"     {link['rationale']}")
        if record["growth"]:
            lines.append(f"   {record['growth']}")
    return safe_text("\n".join(lines))


def demo_text(data, details=False):
    lines = ["Fictional comparison. These listings are synthetic and the results describe this fixture set."]
    for row in data["profiles"]:
        lines.append(f"\n{row['profile']}")
        for mode in ("baseline", "task", "hybrid"):
            if mode not in row:
                continue
            measured = row[mode]
            precision = measured["precision"]
            lines.append(f"  {mode}: {precision['numerator']}/{precision['denominator']} rated relevant")
            if measured.get("scenario_discoveries"):
                lines.append("  Additional adjacent roles: " + ", ".join(measured["scenario_discoveries"]))
            if details:
                lines.append(short_list(measured["jobs"]))
    return safe_text("\n".join(lines))
