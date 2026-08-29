from __future__ import annotations

import hashlib
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BLOCKED_PRIVATE_INVENTORY_SHA256 = "5e73f79777725cea98698c251aab59ad5d812fde7f48a92f2b4337142585d659"
BLOCKED_PRIVATE_REPOSITORY_SHA256 = "23294037b9237da1e5d368f71d73c91061c2adc5bd2978a278f147406eb65682"


class SourceAuditTests(unittest.TestCase):
    def test_audit_records_history_secrets_assets_provenance_and_ship_boundary(self) -> None:
        text = (ROOT / "docs" / "source-audit.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for marker in [
            "private mode-700 recovery set",
            "all-ref mirror",
            "verified bundle",
            "`v0.2.0` remains an absent planned tag",
            "git rev-list",
            "every unique blob reachable",
            "values never printed",
            "reviewed parentless clean-root baseline",
            "ordinary reviewed single-parent commits",
            "zero blocked private repository identifiers",
            "Publication remains **BLOCKED**",
            "5b15a47f2d7150f545fbcacbfe381787fc0230dc",
            "f4c9452f5ca091f1be7064d9faab1b001ea21645",
            "435076e78988e1e6ec40d00b0b1d76bdbbc5419a",
            "MIT",
            "Apache-2.0",
            "local Git mirror",
            "post-Ship",
            "model-backed behavior",
        ]:
            self.assertIn(marker, normalized)

    def test_public_history_is_blocked_pending_support_after_authorized_sanitization(self) -> None:
        text = (ROOT / "docs" / "source-audit.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
        for marker in [
            "Authorized in-place sanitization and publication gate",
            "owner authorized only these r3 mutations",
            "refs/heads/main",
            "refs/heads/codex/issue-33-cross-harness-portability",
            "Delete the private `v0.1.0` GitHub release",
            "Skills issue metadata #1, #4, #5, #6, #7, and #8",
            "GitHub-managed pull refs #2 and #3",
            "GitHub Support",
            "no rename redirect",
            "Old clones",
            "private recovery set",
            "force-with-lease",
            "git for-each-ref",
            "git rev-list",
            "git cat-file",
            "bounded anonymous GitHub API reads",
            "force-fetch and cleanup guidance",
            "v0.1.0` must not be used or recreated",
            "later exact owner Ship authority",
        ]:
            self.assertIn(marker, normalized)
        self.assertEqual(release["history_visibility"]["status"], "PRIVATE_SUPPORT_PURGE_PENDING")
        self.assertFalse(release["history_visibility"]["visibility_change_legal"])
        gate = "\n".join(release["ship_gate"])
        self.assertIn("GitHub Support confirms purge", gate)
        self.assertIn("private-state re-audit reports zero blocked findings", gate)
        self.assertIn("remains private and the only canonical endpoint", gate)
        self.assertNotIn("historical names is acceptable", text)

    def test_current_public_docs_remove_private_pilot_and_consumer_inventory(self) -> None:
        current = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("README.md", "release.json", "docs/source-audit.md")
        )
        for stale in [
            "private immutable release source",
            "current release; the tag is unchanged",
        ]:
            self.assertNotIn(stale, current)

    def test_entire_current_tree_has_no_private_issue_url_or_inventory(self) -> None:
        private_issue_url = re.compile(
            r"https://github\.com/onlinesourdough/(?!Skills(?:-Atlas)?(?:/|$))[^/\s)]+/issues/\d+"
        )
        inventory_candidate = re.compile(
            r"\b[A-Z][A-Za-z0-9]*(?:,\s*[A-Z][A-Za-z0-9]*){4}\b"
        )
        repository_identifier = re.compile(r"\bonlinesourdough/[A-Za-z0-9_.-]+\b")
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            try:
                current = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            self.assertIsNone(private_issue_url.search(current), path)
            for candidate in repository_identifier.findall(current):
                digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
                self.assertNotEqual(digest, BLOCKED_PRIVATE_REPOSITORY_SHA256, path)
            for candidate in inventory_candidate.findall(current):
                digest = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
                self.assertNotEqual(digest, BLOCKED_PRIVATE_INVENTORY_SHA256, path)

    def test_fixture_is_explicitly_synthetic_and_current_tree_has_no_stale_assets(self) -> None:
        fixture = (ROOT / "tests" / "fixtures" / "shape-offer" / "usage.md").read_text(encoding="utf-8")
        self.assertIn("synthetic scenario", fixture)
        self.assertNotIn("Maja", fixture)
        self.assertNotIn("Aarhus", fixture)
        self.assertFalse((ROOT / "assets" / "skills-overview.png").exists())
        self.assertFalse((ROOT / "assets" / "skills-recipe-shelf.svg").exists())

    def test_secret_scanner_covers_worktree_and_all_reachable_blob_bytes(self) -> None:
        scanner = (ROOT / "scripts" / "secret_scan.py").read_text(encoding="utf-8")
        self.assertIn('git("rev-list", "--objects", "--all")', scanner)
        self.assertIn('git("cat-file", "blob", object_id)', scanner)
        self.assertIn("values never printed", scanner)
        self.assertNotIn("print(line)", scanner)

    def test_no_consumer_paths_are_packaged(self) -> None:
        paths = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts}
        self.assertFalse(any(path.startswith((".claude/", ".cursor/", ".agents/skills/")) for path in paths))
        self.assertEqual(paths.intersection({".agents/plugins/marketplace.json"}), {".agents/plugins/marketplace.json"})
        self.assertFalse(any(path.endswith("/manage-skills/SKILL.md") and not path.startswith("skills/") for path in paths))


if __name__ == "__main__":
    unittest.main()
