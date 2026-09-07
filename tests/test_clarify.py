from __future__ import annotations

import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "clarify" / "visual.html"


class ArtifactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {key: value or "" for key, value in attrs}))

    def handle_data(self, data: str) -> None:
        self.text.append(data)


class ClarifyContractTests(unittest.TestCase):
    def test_skill_contract_is_an_ordinary_visual_explainer(self) -> None:
        text = (ROOT / "skills" / "clarify" / "SKILL.md").read_text(encoding="utf-8")
        for phrase in ["ordinary, discoverable explainer", "one self-contained `.html` artifact", "text-only\n  fallback", "sources/fact-check section", "audience's language", "visible equivalents", "offline", "reflow or\nsimplify"]:
            self.assertIn(phrase, text)
        self.assertNotIn("must conduct an interview", text)
        self.assertNotIn("must request a second build permission", text)
        self.assertNotIn("Spec-first", text)

    def test_visual_artifact_is_accessible_and_self_contained(self) -> None:
        text = FIXTURE.read_text(encoding="utf-8")
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
        self.assertNotIn("<link", text.lower())
        self.assertNotIn("<img", text.lower())
        self.assertNotIn("@import", text.lower())
        self.assertNotIn("animation", text.lower())
        self.assertIn("prefers-reduced-motion", text)
        self.assertIn("<desc", text.lower())
        self.assertIn("@media (max-width", text)
        self.assertIn("mobile-steps", text)
        self.assertLess(len(" ".join(parser.text)), 3000)


if __name__ == "__main__":
    unittest.main()
