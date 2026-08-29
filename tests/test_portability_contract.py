from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {"clarify", "manage-skills", "orchestrate-workers", "shape-offer"}
INSTALL = "npx skills@1.5.23 add onlinesourdough/Skills#v0.2.0 --skill clarify manage-skills orchestrate-workers shape-offer --agent claude-code cursor -y"
RETIRED_SKILL = "route-models"


class PortabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.audit = (ROOT / "docs" / "source-audit.md").read_text(encoding="utf-8")
        cls.release = json.loads((ROOT / "release.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        cls.marketplace = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))

    def test_candidate_version_inventory_and_refs_are_consistent(self) -> None:
        self.assertEqual(self.release["version"], "0.2.0")
        self.assertEqual(self.release["status"], "candidate")
        self.assertFalse(self.release["released"])
        self.assertIsNone(self.release["release_date"])
        self.assertEqual(set(self.release["included_skills"]), SKILLS)
        self.assertEqual(self.manifest["version"], "0.2.0")
        self.assertEqual(self.manifest["license"], "MIT")
        self.assertEqual(self.marketplace["plugins"][0]["source"]["ref"], "v0.2.0")
        self.assertEqual(self.release["marketplace"]["release_tag"], "v0.2.0")
        self.assertEqual(self.release["marketplace"]["source_ref_kind"], "planned-immutable-tag")
        self.assertFalse(self.release["marketplace"]["tag_exists_at_build"])

    def test_historical_release_is_withheld_and_candidate_tag_is_not_invented(self) -> None:
        previous = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/tags/v0.1.0^{commit}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(previous.returncode, 0)
        self.assertEqual(self.release["historical_release"], {
            "version": "0.1.0",
            "public_continuity": "WITHHELD",
            "tag_exists_after_private_sanitization": False,
            "release_exists_after_private_sanitization": False,
            "recreate": False,
            "first_public_release": "v0.2.0",
        })
        candidate = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/tags/v0.2.0^{commit}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(candidate.returncode, 0)
        self.assertIn("does not claim that the tag already exists", self.readme)
        self.assertIn("`v0.2.0` remains an absent planned tag", " ".join(self.audit.split()))

    def test_public_install_contract_is_pinned_and_candidate_bounded(self) -> None:
        text = "\n".join((self.readme, self.audit, json.dumps(self.release)))
        for marker in [
            INSTALL,
            "npx skills@1.5.23 add onlinesourdough/Skills#v0.2.0 --list",
            "codex plugin marketplace add onlinesourdough/Skills --ref v0.2.0",
            "codex plugin add onlinesourdough-skills@onlinesourdough-skills",
            "skills@1.5.23",
            "435076e78988e1e6ec40d00b0b1d76bdbbc5419a",
            "sha512-+hMNBSi35yfX0sKD+ZcRm9y5or7u313OdkcvrRvJAsAzGCaA8wRTu2OmVdN0KRbk9ybqKby5dijkn6OVvNTUmw==",
            "local Git commit/ref fixture only",
            "model-backed behavior",
            "Claude Code",
            "Cursor Agent",
        ]:
            self.assertIn(marker, text)

    def test_marketplace_authentication_policy_is_preserved(self) -> None:
        entry = self.marketplace["plugins"][0]
        self.assertEqual(entry["policy"], {"installation": "AVAILABLE", "authentication": "ON_INSTALL"})
        self.assertIn('policy.authentication: "ON_INSTALL"', self.readme)

    def test_atlas_contract_is_canonical_observed_and_branch_protected(self) -> None:
        atlas = self.release["atlas"]
        normalized_readme = " ".join(self.readme.split())
        self.assertEqual(atlas["canonical_repository"], "https://github.com/onlinesourdough/Skills")
        self.assertIn("remains canonical", atlas["endpoint_continuity"])
        self.assertIn("does not rename, archive, replace, or duplicate", atlas["endpoint_continuity"])
        self.assertEqual(atlas["public_static_mode"], {
            "source": "bounded anonymous GitHub API reads",
            "default_repository": "onlinesourdough/Skills",
            "display": "observed revision and access state",
            "write_policy": "read-only",
        })
        self.assertEqual(atlas["authenticated_self_hosted_mode"], {
            "proposal_limit": "exactly one validated skill edit",
            "delivery": "new branch and pull request",
            "default_branch_write": False,
        })
        for marker in [
            "GitHub remains the canonical source",
            "bounded anonymous GitHub API reads",
            "observed revision and access state",
            "remain read-only",
            "exactly one validated skill edit",
            "new branch and open a pull request",
            "never writes the default branch",
            "does not claim that the Skills repository is public",
            "live Atlas integration works",
        ]:
            self.assertIn(marker, normalized_readme)

    def test_current_history_visibility_is_blocked_pending_exact_owner_authority(self) -> None:
        history = self.release["history_visibility"]
        self.assertEqual(history["status"], "PRIVATE_SUPPORT_PURGE_PENDING")
        self.assertFalse(history["visibility_change_legal"])
        self.assertIn("converge on the verified clean-root candidate", history["ordinary_refs"])
        self.assertIn("withheld/deleted", history["historical_release"])
        self.assertIn("GitHub Support purge confirmation", history["github_managed_residue"])
        self.assertIn("Keep the existing onlinesourdough/Skills repository private and in place", history["canonical_endpoint_action"])
        gate = "\n".join(self.release["ship_gate"])
        for marker in [
            "owner authorized the exact r3 in-place sanitization",
            "both authorized ordinary branch refs",
            "v0.1.0 GitHub release and local/remote tag are absent",
            "Skills issue metadata #1, #4, #5, #6, #7, and #8",
            "GitHub Support confirms purge of refs/pull/2/head, refs/pull/3/head",
        ]:
            self.assertIn(marker, gate)
        normalized_readme = " ".join(self.readme.split())
        self.assertIn("selected no historical `v0.1.0` continuity", normalized_readme)
        self.assertIn("No public install or rollback command may point to `v0.1.0`", normalized_readme)

    def test_authorized_branches_converge_on_one_clean_root(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
        main = subprocess.run(["git", "rev-parse", "refs/heads/main"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
        feature = subprocess.run(
            ["git", "rev-parse", "refs/heads/codex/issue-33-cross-harness-portability"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        parents = subprocess.run(
            ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.split()
        self.assertEqual(main, head)
        self.assertEqual(feature, head)
        self.assertEqual(len(parents), 1)

    def test_repository_contains_one_canonical_payload_root(self) -> None:
        payloads = [path for path in ROOT.rglob("SKILL.md") if ".git" not in path.parts]
        self.assertEqual({path.parent.parent.name for path in payloads}, {"skills"})
        self.assertEqual({path.parent.name for path in payloads}, SKILLS)
        self.assertFalse((ROOT / ".claude").exists())
        self.assertFalse((ROOT / ".cursor").exists())
        self.assertFalse((ROOT / ".agents" / "skills").exists())
        self.assertFalse(any((ROOT / "assets").glob("*")))

    def test_retired_router_has_only_historical_or_denial_references(self) -> None:
        self.assertFalse((ROOT / "skills" / RETIRED_SKILL).exists())
        for retired in (
            ROOT / "tests" / "fixtures" / "routing",
            ROOT / "tests" / "test_route_models.py",
            ROOT / "tests" / "test_routing.py",
        ):
            self.assertFalse(retired.exists(), retired)
        for active in (
            ROOT / "AGENTS.md",
            ROOT / "README.md",
            ROOT / "release.json",
            ROOT / ".codex-plugin" / "plugin.json",
            ROOT / ".agents" / "plugins" / "marketplace.json",
            ROOT / "tests" / "run_all.py",
        ):
            self.assertNotIn(RETIRED_SKILL, active.read_text(encoding="utf-8"), active)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("separate router candidate was removed before the first public release", changelog)

    def test_public_community_files_are_present_and_linked(self) -> None:
        for name in ("LICENSE", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "CHANGELOG.md"):
            self.assertTrue((ROOT / name).is_file(), name)
            self.assertIn(name, self.readme)


if __name__ == "__main__":
    unittest.main()
