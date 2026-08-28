#!/usr/bin/env python3
"""Scan the working tree and reachable Git blobs without printing values."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    "openai-token-prefix": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}"),
    "github-token-prefix": re.compile(rb"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_-]{20,}"),
    "aws-access-key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "slack-token-prefix": re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}"),
    "bearer-token": re.compile(rb"\bBearer[ \t]+[A-Za-z0-9._~+/=-]{24,}"),
    "credential-assignment": re.compile(
        rb"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password)"
        rb"[ \t]{0,8}(?::|=)[ \t]{0,8}['\"]?[A-Za-z0-9._~+/=-]{16,}"
    ),
}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__"}


def git(*arguments: str, input_data: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        input=input_data,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        diagnostic = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {diagnostic}")
    return result.stdout


def working_tree_files() -> Iterable[tuple[str, bytes]]:
    for path in ROOT.rglob("*"):
        if not path.is_file() or SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            continue
        try:
            yield str(path.relative_to(ROOT)), path.read_bytes()
        except OSError:
            continue


def reachable_blobs() -> tuple[int, list[tuple[str, bytes]]]:
    commits = [line for line in git("rev-list", "--all").splitlines() if line]
    objects = git("rev-list", "--objects", "--all").splitlines()
    paths_by_object: dict[str, set[str]] = {}
    for raw in objects:
        object_id, separator, raw_path = raw.partition(b" ")
        if not object_id:
            continue
        key = object_id.decode("ascii")
        path = raw_path.decode("utf-8", errors="replace") if separator else "<no-path>"
        paths_by_object.setdefault(key, set()).add(path)

    blobs: list[tuple[str, bytes]] = []
    for object_id, paths in paths_by_object.items():
        if git("cat-file", "-t", object_id).strip() != b"blob":
            continue
        label = f"{object_id[:12]}:{'|'.join(sorted(paths))}"
        blobs.append((label, git("cat-file", "blob", object_id)))
    return len(commits), blobs


def scan(scope: str, items: Iterable[tuple[str, bytes]]) -> tuple[int, list[tuple[str, str, str, int]]]:
    count = 0
    matches: list[tuple[str, str, str, int]] = []
    for label, data in items:
        count += 1
        for line_number, line in enumerate(data.splitlines(), 1):
            for kind, pattern in PATTERNS.items():
                if pattern.search(line):
                    matches.append((scope, kind, label, line_number))
    return count, matches


def main() -> int:
    try:
        file_count, worktree_matches = scan("worktree", working_tree_files())
        commit_count, blobs = reachable_blobs()
        blob_count, history_matches = scan("history", blobs)
    except RuntimeError as error:
        print(f"FAIL secret scan infrastructure: {error}")
        return 1

    matches = worktree_matches + history_matches
    if matches:
        for scope, kind, label, line in matches:
            print(f"MATCH scope={scope} kind={kind} location={label} line={line}")
        print(f"FAIL secret marker count={len(matches)} (values withheld)")
        return 1

    print(
        "PASS secret scan: "
        f"worktree_files={file_count} reachable_commits={commit_count} "
        f"unique_history_blobs={blob_count} signatures={len(PATTERNS)} "
        "matches=0 (values never printed)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
