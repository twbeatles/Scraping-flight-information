"""Validate encoding for tracked text files in the repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".spec",
    ".txt",
    ".json",
    ".toml",
    ".yml",
    ".yaml",
    ".ini",
    ".cfg",
}
TEXT_FILENAMES = {
    ".editorconfig",
    ".gitattributes",
    ".gitignore",
}


def tracked_text_files(repo_root: Path) -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    tracked_paths = completed.stdout.decode("utf-8").split("\0")
    files: list[Path] = []
    for rel_path in tracked_paths:
        if not rel_path:
            continue
        path = repo_root / rel_path
        if not path.is_file():
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in TEXT_FILENAMES:
            files.append(path)
    return files


def validate_file(path: Path, repo_root: Path, *, check_lf: bool) -> list[str]:
    data = path.read_bytes()
    rel_path = path.relative_to(repo_root)
    issues: list[str] = []

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        issues.append(f"{rel_path}: not valid UTF-8 ({exc})")
        return issues

    if "\ufffd" in text:
        issues.append(f"{rel_path}: contains replacement character U+FFFD")

    if check_lf and b"\r\n" in data:
        issues.append(f"{rel_path}: contains CRLF line endings")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-lf",
        action="store_true",
        help="fail if tracked text files contain CRLF line endings",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    files = tracked_text_files(repo_root)
    issues: list[str] = []
    for path in files:
        issues.extend(validate_file(path, repo_root, check_lf=args.check_lf))

    if issues:
        print("Tracked text validation failed:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    print(f"Checked {len(files)} tracked text files: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
