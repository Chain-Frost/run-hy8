"""Select the explicit release opt-out for a verified pull-request merge."""

import json
import re
import sys

_SKIP_MARKER = re.compile(r"\[skip release\]", re.IGNORECASE)


def should_skip_release(labels: list[str], commit_message: str) -> bool:
    """Match the exact PR label or the immutable merge commit keyword."""
    return "skip-release" in {label.casefold() for label in labels} or bool(
        _SKIP_MARKER.search(commit_message)
    )


def main() -> int:
    """Return skip/publish on stdout, failing closed for invalid input."""
    record = json.load(sys.stdin)
    if not isinstance(record, dict):
        raise TypeError("Expected a JSON object.")
    labels = record.get("labels")
    message = record.get("commit_message")
    if not isinstance(labels, list) or any(not isinstance(label, str) for label in labels):
        raise TypeError("labels must be list[str].")
    if not isinstance(message, str):
        raise TypeError("commit_message must be a string.")
    print("skip" if should_skip_release(labels, message) else "publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
