from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {"clarify", "setup-guardrails", "shape-offer"}
RELEASE_TAG = "v0.4.0"
RETIRED = "route-models"
VALIDATOR_SPEC = importlib.util.spec_from_file_location("validate_repo_lineage", ROOT / "scripts" / "validate_repo.py")
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


class PortabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))
        cls.marketplace = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))

    def test_candidate_metadata_and_distribution_refs_are_consistent(self) -> None:
        self.assertEqual(self.release["version"], "0.4.0")
        self.assertEqual(self.release["status"], "candidate")
        self.assertFalse(self.release["released"])
        self.assertIsNone(self.release["release_date"])
        self.assertEqual(set(self.release["included_skills"]), SKILLS)
        self.assertEqual(self.manifest["version"], self.release["version"])
        self.assertEqual(set(self.manifest["interface"]["capabilities"]), {"Visual explanation", "Offer shaping", "Local safety guardrails"})
        entry = self.marketplace["plugins"][0]
        self.assertEqual(entry["source"]["url"], "https://github.com/onlinesourdough/Global-Skills")
        self.assertEqual(entry["source"]["ref"], RELEASE_TAG)
        self.assertEqual(entry["policy"], {"installation": "AVAILABLE", "authentication": "ON_INSTALL"})
        self.assertFalse(self.release["marketplace"]["tag_exists_at_build"])
        self.assertEqual(self.release["release_notes"], "CHANGELOG.md#040-release-candidate")

    def test_release_and_source_sync_boundaries_are_explicit(self) -> None:
        boundary = self.release["atlas"]["candidate_boundary"]
        self.assertIn("source-only synchronization", boundary)
        self.assertIn("does not create public release availability", boundary)
        self.assertIn("GitHub Support purge", boundary)
        self.assertIn("private-state re-audit", boundary)
        self.assertEqual(self.release["history_visibility"]["status"], "PRIVATE_SUPPORT_PURGE_PENDING")
        self.assertFalse(self.release["history_visibility"]["visibility_change_legal"])
        gate = "\n".join(self.release["ship_gate"])
        for marker in ("v0.1.0", "GitHub Support confirms purge", "private-state re-audit", "later exact Ship authority"):
            self.assertIn(marker, gate)

    def test_historical_and_candidate_tags_are_absent(self) -> None:
        for tag in ("v0.1.0", RELEASE_TAG):
            result = subprocess.run(["git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}"], cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, tag)
        self.assertIn("does not claim that the tag already exists", self.readme)

    def test_one_canonical_payload_root_and_owner_boundaries(self) -> None:
        payloads = [path for path in ROOT.rglob("SKILL.md") if ".git" not in path.parts]
        self.assertEqual({path.parent.parent.name for path in payloads}, {"skills"})
        self.assertEqual({path.parent.name for path in payloads}, SKILLS)
        self.assertFalse((ROOT / ".claude").exists())
        self.assertFalse((ROOT / ".cursor").exists())
        self.assertFalse((ROOT / ".agents" / "skills").exists())
        current = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in ("AGENTS.md", "README.md", "CONTRIBUTING.md", "CHANGELOG.md", "release.json"))
        self.assertIn("aios-orchestrate-workers", current)
        self.assertNotIn("skills/orchestrate-workers/SKILL.md", current)
        self.assertNotIn(RETIRED, (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8"))


class GitLineageFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="skills-lineage-")
        self.repo = Path(self.temporary.name)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "baseline.txt").write_text("baseline\n", encoding="utf-8")
        self.git("add", "baseline.txt")
        self.git("commit", "-qm", "clean root baseline")
        self.baseline = self.git("rev-parse", "HEAD")
        self.git("branch", "codex/issue-33-cross-harness-portability", self.baseline)
        (self.repo / "reviewed.txt").write_text("reviewed\n", encoding="utf-8")
        self.git("add", "reviewed.txt")
        self.git("commit", "-qm", "ordinary reviewed commit")
        self.original_root = VALIDATOR.ROOT
        VALIDATOR.ROOT = self.repo

    def tearDown(self) -> None:
        VALIDATOR.ROOT = self.original_root
        self.temporary.cleanup()

    def git(self, *arguments: str) -> str:
        result = subprocess.run(["git", *arguments], cwd=self.repo, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def validate(self) -> list[str]:
        errors: list[str] = []
        VALIDATOR.validate_git_candidate(errors)
        return errors

    def test_clean_root_and_linear_commits_pass(self) -> None:
        self.assertEqual(self.validate(), [])

    def test_merge_commit_is_rejected(self) -> None:
        self.git("switch", "-qc", "side", self.baseline)
        (self.repo / "side.txt").write_text("side\n", encoding="utf-8")
        self.git("add", "side.txt")
        self.git("commit", "-qm", "side commit")
        self.git("switch", "-q", "main")
        self.git("merge", "--no-ff", "-qm", "merge side", "side")
        self.assertTrue(any("single-parent commits" in error for error in self.validate()))

    def test_second_root_is_rejected(self) -> None:
        self.git("switch", "--orphan", "diverged")
        (self.repo / "diverged.txt").write_text("diverged\n", encoding="utf-8")
        self.git("add", "diverged.txt")
        self.git("commit", "-qm", "second root")
        self.git("branch", "-D", "main")
        self.git("branch", "-m", "main")
        errors = self.validate()
        self.assertTrue(any("exactly one clean-root baseline" in error for error in errors))
        self.assertTrue(any("must descend" in error for error in errors))

    def test_baseline_branch_divergence_is_rejected(self) -> None:
        self.git("switch", "-qc", "diverged", self.baseline)
        (self.repo / "diverged.txt").write_text("diverged\n", encoding="utf-8")
        self.git("add", "diverged.txt")
        self.git("commit", "-qm", "diverged commit")
        self.git("switch", "-q", "main")
        self.git("branch", "-f", "codex/issue-33-cross-harness-portability", "diverged")
        self.assertTrue(any("must not diverge" in error for error in self.validate()))


if __name__ == "__main__":
    unittest.main()
