"""Bounded local reads for user-supplied files."""

from pathlib import Path


def read_bytes(path: Path, limit: int):
    if not path.is_file():
        raise ValueError(f"Expected a file: {path}.")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Input exceeds the {limit:,}-byte limit.")
    return data
