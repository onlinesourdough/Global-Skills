#!/usr/bin/env python3
"""Forward-test clarify through an isolated, read-only first-class Codex run."""

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
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        self.attrs.append((tag, {key: value or "" for key, value in attrs}))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


def run_codex(prompt: str, fixture: Path) -> str:
    if not CODEX:
        raise RuntimeError("Codex CLI unavailable; clarify forward run is unverified")
    result = subprocess.run(
        [
            CODEX,
            "--ask-for-approval",
            "never",
            "--sandbox",
            "read-only",
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--cd",
            str(fixture),
            "--json",
            prompt,
        ],
        input="",
        text=True,
        capture_output=True,
        timeout=180,
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
    return "\n".join(messages)


def assert_spec(text: str, *, complex_mode: bool = False) -> None:
    lowered = text.lower()
    assert "spec" in lowered or "decision-ready" in lowered, "missing Spec boundary"
    assert "recommend" in lowered, "missing recommendation"
    assert "consequence" in lowered, "missing consequence"
    assert "source" in lowered or "evidence" in lowered or "fact-check" in lowered, "missing source/fact-check evidence"
    assert "implementation" in lowered and ("not started" in lowered or "not begun" in lowered or "no implementation" in lowered), "missing implementation stop"
    assert not re.search(r"\b(i|we)\s+(created|wrote|implemented|installed|modified|sent)\b", lowered), "response claims an implementation side effect"
    if complex_mode:
        assert lowered.count("round") <= 12, "complex mode exceeded bounded rounds"
        assert "decision" in lowered, "complex mode missing decision boundary"


def assert_visual(text: str) -> None:
    candidate = text[text.lower().find("<!doctype html>") :]
    if not candidate:
        candidate = text[text.lower().find("<html") :]
    parser = ArtifactParser()
    parser.feed(candidate)
    assert candidate.lower().startswith(("<!doctype html>", "<html")), "visual output is not standalone HTML"
    html_attrs = next(attrs for tag, attrs in parser.attrs if tag == "html")
    assert html_attrs.get("lang"), "visual output has no language attribute"
    for tag in ("title", "main", "h1", "h2", "svg", "style"):
        assert tag in parser.tags, f"visual output missing {tag}"
    assert "text-fallback" in candidate.lower() or "text fallback" in candidate.lower(), "visual output missing text fallback"
    assert "source" in candidate.lower() or "fact-check" in candidate.lower(), "visual output missing sources"
    assert ":focus-visible" in candidate, "visual output missing focus styling"
    assert "aria-" in candidate, "visual output missing accessible labelling"
    assert "<script" not in candidate.lower(), "visual output contains a script"
    assert "<link" not in candidate.lower(), "visual output contains an external link"
    assert "<img" not in candidate.lower(), "visual output contains an image dependency"


def main() -> int:
    if not CODEX:
        print("UNVERIFIED: Codex CLI unavailable; no independent clarify forward run was possible")
        return 0
    with tempfile.TemporaryDirectory(prefix="clarify-forward-") as temporary:
        fixture = Path(temporary)
        skill_link = fixture / ".agents" / "skills" / "clarify"
        skill_link.parent.mkdir(parents=True)
        skill_link.symlink_to(ROOT / "skills" / "clarify", target_is_directory=True)

        small = run_codex(
            """Use the locally discovered /clarify skill for this small decision. The owner must choose plain text or self-contained HTML for a one-page status note for busy engineering managers. No external research is needed: the audience and two choices are facts supplied in this prompt. Recommend one option, state consequences, include sources/fact-checks, return a decision-ready Spec, and explicitly state that implementation has not started. Do not implement, write files, use tools, or take any external action. Return only the Spec.""",
            fixture,
        )
        try:
            assert_spec(small)
        except AssertionError as error:
            raise AssertionError(f"small case: {error}") from error

        complex_result = run_codex(
            """Use the locally discovered /clarify skill in complex mode. Produce a decision-ready Spec for a team choosing a portable global skill distribution pilot. The settled owner constraints are: one canonical skills/ source; a thin Codex wrapper; no consumer-repository edits; no global install; and explicit rollback. The remaining branches are (A) local-only discovery, (B) a repository-owned marketplace plus project pointers, or (C) separate harness payloads. Recommend an option, state consequences for each branch, cite these supplied facts as the evidence, ask no more than the material decisions, and stop within three frontier rounds. Explicitly say implementation has not started. Do not implement, write files, use tools, or take any external action. Return only the Spec.""",
            fixture,
        )
        try:
            assert_spec(complex_result, complex_mode=True)
        except AssertionError as error:
            raise AssertionError(f"complex case: {error}") from error

        visual = run_codex(
            """Use the locally discovered /clarify skill's optional visual mode. For the named audience of busy engineering managers, explain the settled choice of a plain-text status note over self-contained HTML in exactly one self-contained accessible HTML artifact. Return HTML only, with <!doctype html>, lang, title, main, h1/h2, one large inline SVG with meaningful labels, concise visible text, a text-fallback section, a Sources and fact checks section, focus-visible styling, aria labels, and no scripts, external links, images, fonts, or other dependencies. Do not implement a product or write a file; return the artifact in your response.""",
            fixture,
        )
        try:
            assert_visual(visual)
        except AssertionError as error:
            raise AssertionError(f"visual case: {error}") from error

    print("PASS: independent clarify small, complex, and visual forward runs evaluated from raw Codex responses; no implementation or writes")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, RuntimeError, StopIteration) as error:
        print(f"FAIL: clarify forward run: {error}")
        sys.exit(1)
