from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "shape-offer" / "SKILL.md"
FIXTURE = ROOT / "tests" / "fixtures" / "shape-offer" / "usage.md"


class ShapeOfferContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.fixture = FIXTURE.read_text(encoding="utf-8")

    def test_skill_has_portable_frontmatter_and_required_offer_contract(self) -> None:
        self.assertTrue(self.skill.startswith("---\nname: shape-offer\n"))
        self.assertIn("description:", self.skill.split("\n---\n", 1)[0])
        for phrase in [
            "Known fact",
            "Assumption",
            "Unknown",
            "Customer and real problem",
            "Desired outcome and evidence",
            "Scope and delivery",
            "Price logic and economics",
            "Owner burden and constraints",
            "Boundaries and unsupported promises",
            "Smallest next validation",
            "needs-one-material-decision",
            "Do not add direct-response funnels",
        ]:
            self.assertIn(phrase, self.skill)

    def test_realistic_fixture_contains_context_but_no_leaked_answer(self) -> None:
        for phrase in [
            "synthetic scenario",
            "An instructor teaches sourdough",
            "850 DKK",
            "four hours each week",
            "Ingredient costs are small but not recorded",
        ]:
            self.assertIn(phrase, self.fixture)
        self.assertNotRegex(self.fixture, re.compile(r"(?im)^expected (?:answer|output):"))
        self.assertNotIn("Offer Brief — decision-ready", self.fixture)
        self.assertNotIn("Recommended offer:", self.fixture)

    def test_skill_does_not_smuggle_fixture_specific_evidence(self) -> None:
        skill_lower = self.skill.lower()
        for phrase in ["instructor", "850 dkk", "sourdough"]:
            self.assertNotIn(phrase, skill_lower)


if __name__ == "__main__":
    unittest.main()
