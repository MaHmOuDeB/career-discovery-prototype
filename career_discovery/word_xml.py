"""Parse the bounded, entity-free main XML part of a Word document."""

import json
import sys
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def segments(text):
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise ValueError("Could not parse the DOCX body.") from exc
    body = root.find(f"{W}body")
    if body is None:
        raise ValueError("DOCX has no supported main body.")
    output = []
    for index, paragraph in enumerate(body.iter(f"{W}p"), 1):
        parts = []
        for child in paragraph:
            runs = child.findall(f"./{W}r") if child.tag == f"{W}hyperlink" else [child]
            for run in runs:
                if run.tag != f"{W}r" or run.find(f"./{W}rPr/{W}vanish") is not None:
                    continue
                for token in run:
                    if token.tag == f"{W}t":
                        parts.append(token.text or "")
                    elif token.tag in {f"{W}tab", f"{W}br"}:
                        parts.append(" ")
        if parts:
            output.append((f"DOCX paragraph {index}", "".join(parts)))
    return output


if __name__ == "__main__":
    try:
        print(json.dumps(segments(sys.stdin.buffer.read().decode("utf-8"))))
    except ValueError:
        sys.exit(2)
