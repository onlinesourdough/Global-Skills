from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PRIVATE_INVENTORY_SHA256 = "5e73f79777725cea98698c251aab59ad5d812fde7f48a92f2b4337142585d659"
BLOCKED_PRIVATE_REPOSITORY_SHA256 = "23294037b9237da1e5d368f71d73c91061c2adc5bd2978a278f147406eb65682"
PRIVATE_ISSUE_URL = re.compile(
    r"https://github\.com/onlinesourdough/(?!Global-Skills(?:/|$)|Skills(?:-Atlas)?(?:/|$))[^/\s)]+/issues/\d+"
)
INVENTORY = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:,\s*[A-Z][A-Za-z0-9]*){4}\b")
REPOSITORY = re.compile(r"\bonlinesourdough/[A-Za-z0-9_.-]+\b")


class SourceSafetyTests(unittest.TestCase):
    def test_release_is_unreleased_but_source_sync_is_distinct_from_ship(self) -> None:
        release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
        self.assertEqual(release["version"], "0.3.0")
        self.assertEqual(release["status"], "candidate")
        self.assertFalse(release["released"])
        self.assertIsNone(release["release_date"])
        self.assertIn("source-only synchronization", release["atlas"]["candidate_boundary"])
        self.assertIn("does not create public release availability", release["atlas"]["candidate_boundary"])
        self.assertEqual(release["release_notes"], "CHANGELOG.md#030-release-candidate")
        gate = "\n".join(release["ship_gate"])
        self.assertIn("GitHub Support confirms purge", gate)
        self.assertIn("private-state re-audit", gate)

    def test_current_tree_has_no_blocked_private_identifiers(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            self.assertIsNone(PRIVATE_ISSUE_URL.search(text), path)
            for candidate in REPOSITORY.findall(text):
                self.assertNotEqual(hashlib.sha256(candidate.encode()).hexdigest(), BLOCKED_PRIVATE_REPOSITORY_SHA256, path)
            for candidate in INVENTORY.findall(text):
                self.assertNotEqual(hashlib.sha256(candidate.encode()).hexdigest(), BLOCKED_PRIVATE_INVENTORY_SHA256, path)

    def test_fixture_and_assets_are_safe_and_intentional(self) -> None:
        fixture = (ROOT / "tests" / "fixtures" / "shape-offer" / "usage.md").read_text(encoding="utf-8")
        self.assertIn("synthetic scenario", fixture)
        self.assertNotIn("Maja", fixture)
        self.assertNotIn("Aarhus", fixture)
        self.assertEqual(
            {path.relative_to(ROOT / "assets").as_posix() for path in (ROOT / "assets").rglob("*") if path.is_file()},
            {"branding/skills-banner.png", "branding/skills-icon.png"},
        )

    def test_default_runner_is_local_and_forward_check_is_opt_in(self) -> None:
        runner = (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8")
        self.assertNotIn("forward_clarify.py", runner)
        self.assertIn("unittest.defaultTestLoader", runner)
        self.assertTrue((ROOT / "tests" / "forward_clarify.py").is_file())

    def test_no_consumer_payload_copies_are_packaged(self) -> None:
        paths = {
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts
        }
        self.assertFalse(any(path.startswith((".claude/", ".cursor/", ".agents/skills/")) for path in paths))
        self.assertFalse(any(path.endswith("/manage-skills/SKILL.md") for path in paths))


if __name__ == "__main__":
    unittest.main()
