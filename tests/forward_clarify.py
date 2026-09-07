#!/usr/bin/env python3
"""Forward-test clarify through one isolated, read-only first-class Codex run."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEX = shutil.which("codex")


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.attrs: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attrs.append((tag, {key: value or "" for key, value in attrs}))


def run_codex(prompt: str, fixture: Path) -> tuple[str, str]:
    if not CODEX:
        raise RuntimeError("Codex CLI unavailable; clarify forward run is unverified")
    result = subprocess.run(
        [
            CODEX,
            "--ask-for-approval", "never",
            "--sandbox", "read-only",
            "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
            "--skip-git-repo-check", "--cd", str(fixture), "--json", prompt,
        ],
        input="", text=True, capture_output=True, timeout=180,
    )
    if result.returncode:
        raise AssertionError(f"isolated Codex clarify run failed with exit {result.returncode}")
    messages: list[str] = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if isinstance(item, dict) and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            messages.append(item["text"])
    if not messages:
        raise AssertionError("isolated Codex clarify run emitted no agent response")
    return "\n".join(messages), result.stdout


def assert_skill_discovered(raw_trace: str) -> None:
    for line in raw_trace.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if not isinstance(item, dict) or item.get("type") != "command_execution" or item.get("exit_code") != 0:
            continue
        command = str(item.get("command", "")).lower()
        returned = str(item.get("aggregated_output", "")).lower()
        if (
            (".agents/skills/clarify" in command or "skills/clarify/skill.md" in command)
            and "name: clarify" in returned
            and "description:" in returned
            and "# clarify" in returned
        ):
            return
    assert False, "raw trace contains no completed successful read of the discovered clarify skill"


def assert_visual(text: str) -> None:
    lowered = text.lower()
    start = lowered.find("<!doctype html>")
    if start < 0:
        start = lowered.find("<html")
    candidate = text[start:]
    parser = ArtifactParser()
    parser.feed(candidate)
    assert candidate.lower().startswith(("<!doctype html>", "<html")), "visual output is not standalone HTML"
    html_attrs = next(attrs for tag, attrs in parser.attrs if tag == "html")
    assert html_attrs.get("lang"), "visual output has no language attribute"
    for tag in ("title", "main", "h1", "h2", "style"):
        assert tag in parser.tags, f"visual output missing {tag}"
    assert (
        any(tag in parser.tags for tag in ("svg", "figure", "table"))
        or any(marker in candidate.lower() for marker in ('role="img"', "class=\"diagram", "class=\"flow", "display: grid", "grid-template"))
    ), "visual output has no local visual"
    assert (
        any(word in candidate.lower() for word in ("text-fallback", "text fallback", "text-only explanation", "text alternative", "plain-language", "plain language"))
        or ("accessible" in candidate.lower() and "<section" in candidate.lower())
    ), "visual output missing a labelled text alternative"
    assert any(word in candidate.lower() for word in ("source", "fact-check", "kilde", "fakta", "faktatjek", "reference", "uncertainty")), "visual output missing sources"
    assert ":focus-visible" in candidate, "visual output missing focus styling"
    assert "aria-" in candidate, "visual output missing accessible labelling"
    assert "<script" not in candidate.lower(), "visual output contains a script"
    assert "<link" not in candidate.lower(), "visual output contains an external link"
    assert "<img" not in candidate.lower(), "visual output contains an image dependency"
    assert "src=\"http" not in candidate.lower(), "visual output contains a remote source"
    assert "url(" not in candidate.lower(), "visual output contains a remote CSS asset"
    assert "@import" not in candidate.lower(), "visual output imports a stylesheet"
    assert not re.search(r"(?i)\banimation\s*:\s*(?!none\b)[^;}]+", candidate), "visual output contains active animation"
    assert not re.search(r"(?i)\btransition\s*:\s*(?!none\b)[^;}]+", candidate), "visual output contains active transition"


def main() -> int:
    if not CODEX:
        print("UNVERIFIED: Codex CLI unavailable; no independent clarify forward run was possible")
        return 0
    temporary = tempfile.mkdtemp(prefix="clarify-forward-")
    fixture = Path(temporary)
    skill_link = fixture / ".agents" / "skills" / "clarify"
    skill_link.parent.mkdir(parents=True)
    skill_link.symlink_to(ROOT / "skills" / "clarify", target_is_directory=True)
    visual, raw_trace = run_codex(
        """Use the locally discovered /clarify skill for this request. Busy engineering managers need a short explanation of why a deployment decision should be recorded before the next rollout. Use only this supplied context, make the explanation usable when visuals are unavailable, distinguish checked claims from uncertainty, and return one useful self-contained HTML explanation in your response. Do not publish anything or modify the project.""",
        fixture,
    )
    artifact = fixture / "clarify-output.html"
    trace = fixture / "clarify-trace.jsonl"
    start = visual.lower().find("<!doctype html>")
    artifact.write_text(visual[start:] if start >= 0 else visual, encoding="utf-8")
    trace.write_text(raw_trace, encoding="utf-8")
    try:
        assert_skill_discovered(raw_trace)
        assert_visual(visual)
    except AssertionError as error:
        raise AssertionError(f"visual case: {error}; artifact retained at {artifact}; trace retained at {trace}") from error
    print(f"PASS: independent clarify visual forward run evaluated from raw Codex response; artifact retained at {artifact}; trace retained at {trace}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, RuntimeError, StopIteration) as error:
        print(f"FAIL: clarify forward run: {error}")
        sys.exit(1)
