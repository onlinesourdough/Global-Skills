from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "clarify"


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {key: value or "" for key, value in attrs}))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


class ClarifyForwardTests(unittest.TestCase):
    def test_skill_contract_contains_bounded_no_implementation_and_visual_rules(self) -> None:
        text = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ["small mode", "complex mode", "at most three rounds", "Never begin implementation", "self-contained `.html`", "text fallback", "fact-check"]:
            self.assertIn(phrase, text)

    def test_optional_visual_artifact_is_accessible_and_self_contained(self) -> None:
        text = (FIXTURES / "visual.html").read_text(encoding="utf-8")
        parser = ArtifactParser()
        parser.feed(text)
        tags = {tag for tag, _ in parser.tags}
        attrs = {tag: attrs for tag, attrs in parser.tags}
        self.assertTrue(text.lower().startswith("<!doctype html>"))
        self.assertIn("html", tags)
        self.assertEqual(attrs["html"].get("lang"), "en")
        for tag in ["title", "main", "h1", "style", "svg", "section"]:
            self.assertIn(tag, tags)
        self.assertIn("text-fallback", text)
        self.assertIn("Audience:", text)
        self.assertIn("aria-labelledby", text)
        self.assertIn("https://", text)
        self.assertNotIn("<script", text.lower())
        self.assertLess(len(" ".join(parser.text)), 3000)


if __name__ == "__main__":
    unittest.main()
