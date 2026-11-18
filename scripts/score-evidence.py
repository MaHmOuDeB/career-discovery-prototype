"""Score a labelled fictional CV-line JSON file with the current catalogue."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from career_discovery.analysis import load_catalogue
from career_discovery.diagnostics import evidence_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    rows = json.loads(parser.parse_args().path.read_text(encoding="utf-8"))
    print(json.dumps(evidence_report(rows, load_catalogue()), indent=2))
