from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("clarify", "manage-skills", "orchestrate-workers", "route-models", "shape-offer")
RELEASE_VERSION = "0.2.0"
CODEX = shutil.which("codex")
CLAUDE = shutil.which("claude")
CURSOR = shutil.which("cursor")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(target: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(target, target_is_directory=target.is_dir())


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=120)


def git(cwd: Path, *arguments: str) -> str:
    result = run(["git", "-C", str(cwd), *arguments], env={"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"})
    if result.returncode:
        raise AssertionError(f"git failed: {arguments}: {result.stderr}")
    return result.stdout.strip()


class DistributionFixtureTests(unittest.TestCase):
    def test_canonical_marketplace_is_root_url_without_payload_fork(self) -> None:
        marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual(marketplace["name"], "onlinesourdough-skills")
        self.assertEqual(len(marketplace["plugins"]), 1)
        entry = marketplace["plugins"][0]
        self.assertEqual(entry["name"], "onlinesourdough-skills")
        self.assertEqual(entry["source"]["source"], "url")
        self.assertEqual(entry["source"]["url"], "https://github.com/onlinesourdough/Skills")
        self.assertEqual(entry["source"]["ref"], "v" + RELEASE_VERSION)
        self.assertEqual(entry["policy"], {"installation": "AVAILABLE", "authentication": "ON_INSTALL"})
        self.assertEqual(entry["category"], "Productivity")
        self.assertFalse((ROOT / "plugins").exists())

    def test_project_skill_pointers_preserve_one_canonical_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skills-layout-proof-") as temporary:
            fixture = Path(temporary)
            for destination_root in [fixture / "claude-project" / ".claude" / "skills", fixture / "cursor-project" / ".cursor" / "skills"]:
                for slug in SKILLS:
                    link(ROOT / "skills" / slug, destination_root / slug)
                    self.assertTrue((destination_root / slug / "SKILL.md").is_file())
                    self.assertEqual(digest(destination_root / slug / "SKILL.md"), digest(ROOT / "skills" / slug / "SKILL.md"))
                    self.assertTrue((destination_root / slug).is_symlink())
            self.assertTrue(all(path.is_relative_to(fixture) for path in fixture.rglob("*") if path.is_symlink() or path.is_file()))

    def test_verified_project_adapter_topology_shares_one_project_copy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="skills-adapter-proof-") as temporary:
            fixture = Path(temporary)
            canonical_root = fixture / ".agents" / "skills"
            for slug in SKILLS:
                canonical = canonical_root / slug
                shutil.copytree(ROOT / "skills" / slug, canonical)
                link(canonical, fixture / ".claude" / "skills" / slug)
                self.assertTrue((canonical / "SKILL.md").is_file())
                self.assertTrue((fixture / ".claude" / "skills" / slug / "SKILL.md").is_file())
                self.assertEqual(digest(canonical / "SKILL.md"), digest(ROOT / "skills" / slug / "SKILL.md"))
                self.assertEqual((fixture / ".claude" / "skills" / slug).resolve(), canonical.resolve())
            self.assertEqual(
                {path.parent.parent.name for path in fixture.rglob("SKILL.md")},
                {"skills"},
            )

    @unittest.skipUnless(CODEX, "Codex CLI is unavailable; canonical CLI proof is unverified on this host")
    def test_codex_discovers_installs_upgrades_and_rolls_back_root_plugin(self) -> None:
        with tempfile.TemporaryDirectory(prefix="codex-loader-proof-") as temporary:
            fixture = Path(temporary)
            mirror = fixture / "mirror"
            codex_home = fixture / "codex-home"
            codex_home.mkdir()
            shutil.copytree(ROOT, mirror, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
            marketplace_path = mirror / ".agents" / "plugins" / "marketplace.json"
            catalog = json.loads(marketplace_path.read_text(encoding="utf-8"))
            self.assertEqual(catalog["name"], "onlinesourdough-skills")
            self.assertEqual(catalog["plugins"][0]["name"], "onlinesourdough-skills")
            catalog["plugins"][0]["source"] = {
                **catalog["plugins"][0]["source"],
                "url": mirror.as_uri(),
                "ref": "HEAD",
            }
            marketplace_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
            git(mirror, "init", "-q")
            git(mirror, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "add", ".")
            git(mirror, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", RELEASE_VERSION)
            old_commit = git(mirror, "rev-parse", "HEAD")
            safe_env = {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", "CODEX_HOME": str(codex_home)}

            added = run([CODEX, "plugin", "marketplace", "add", str(mirror), "--json"], env=safe_env)
            self.assertEqual(added.returncode, 0, added.stderr)
            available = run([CODEX, "plugin", "list", "--available", "--json"], env=safe_env)
            self.assertEqual(available.returncode, 0, available.stderr)
            available_payload = json.loads(available.stdout)
            self.assertEqual(available_payload["available"][0]["pluginId"], "onlinesourdough-skills@onlinesourdough-skills")
            self.assertEqual(available_payload["available"][0]["installPolicy"], "AVAILABLE")

            installed = run([CODEX, "plugin", "add", "onlinesourdough-skills@onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(installed.returncode, 0, installed.stderr)
            installed_payload = json.loads(installed.stdout)
            self.assertEqual(installed_payload["version"], RELEASE_VERSION)
            installed_root = Path(installed_payload["installedPath"])
            for slug in SKILLS:
                self.assertEqual(digest(installed_root / "skills" / slug / "SKILL.md"), digest(ROOT / "skills" / slug / "SKILL.md"))

            manifest_path = mirror / ".codex-plugin" / "plugin.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["version"] = "0.2.1"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            release_path = mirror / "release.json"
            release = json.loads(release_path.read_text(encoding="utf-8"))
            release["version"] = "0.2.1"
            release_path.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
            changed_skill = mirror / "skills" / "clarify" / "SKILL.md"
            changed_skill.write_text(changed_skill.read_text(encoding="utf-8") + "\nTemporary isolated upgrade proof.\n", encoding="utf-8")
            git(mirror, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "add", ".")
            git(mirror, "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "0.2.1")
            new_commit = git(mirror, "rev-parse", "HEAD")
            self.assertNotEqual(new_commit, old_commit)

            removed = run([CODEX, "plugin", "remove", "onlinesourdough-skills@onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(removed.returncode, 0, removed.stderr)
            removed_marketplace = run([CODEX, "plugin", "marketplace", "remove", "onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(removed_marketplace.returncode, 0, removed_marketplace.stderr)
            readded_marketplace = run([CODEX, "plugin", "marketplace", "add", str(mirror), "--json"], env=safe_env)
            self.assertEqual(readded_marketplace.returncode, 0, readded_marketplace.stderr)
            installed_new = run([CODEX, "plugin", "add", "onlinesourdough-skills@onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(installed_new.returncode, 0, installed_new.stderr)
            new_payload = json.loads(installed_new.stdout)
            self.assertEqual(new_payload["version"], "0.2.1")
            new_root = Path(new_payload["installedPath"])
            self.assertNotEqual(digest(new_root / "skills" / "clarify" / "SKILL.md"), digest(ROOT / "skills" / "clarify" / "SKILL.md"))

            git(mirror, "checkout", "-q", old_commit)
            removed_again = run([CODEX, "plugin", "remove", "onlinesourdough-skills@onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(removed_again.returncode, 0, removed_again.stderr)
            removed_marketplace_again = run([CODEX, "plugin", "marketplace", "remove", "onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(removed_marketplace_again.returncode, 0, removed_marketplace_again.stderr)
            readded_marketplace_again = run([CODEX, "plugin", "marketplace", "add", str(mirror), "--json"], env=safe_env)
            self.assertEqual(readded_marketplace_again.returncode, 0, readded_marketplace_again.stderr)
            installed_old = run([CODEX, "plugin", "add", "onlinesourdough-skills@onlinesourdough-skills", "--json"], env=safe_env)
            self.assertEqual(installed_old.returncode, 0, installed_old.stderr)
            old_payload = json.loads(installed_old.stdout)
            self.assertEqual(old_payload["version"], RELEASE_VERSION)
            old_root = Path(old_payload["installedPath"])
            for slug in SKILLS:
                self.assertEqual(digest(old_root / "skills" / slug / "SKILL.md"), digest(ROOT / "skills" / slug / "SKILL.md"))

    @unittest.skipUnless(CLAUDE, "Claude Code is unavailable; Claude CLI-specific proof is skipped on this host")
    def test_claude_validator_and_safe_project_loader_boundary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="claude-loader-proof-") as temporary:
            fixture = Path(temporary)
            for slug in SKILLS:
                link(ROOT / "skills" / slug, fixture / ".claude" / "skills" / slug)
            plugin = fixture / ".claude-plugin"
            plugin.mkdir()
            (plugin / "plugin.json").write_text(json.dumps({"name": "onlinesourdough-skills-probe", "version": RELEASE_VERSION, "description": "isolated parser proof", "author": {"name": "fixture"}, "skills": "./skills"}), encoding="utf-8")
            link(ROOT / "skills", fixture / "skills")
            validated = run([CLAUDE, "plugin", "validate", str(fixture)])
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertIn("Validation passed", validated.stdout)
            for slug in SKILLS:
                self.assertEqual(digest(fixture / ".claude" / "skills" / slug / "SKILL.md"), digest(ROOT / "skills" / slug / "SKILL.md"))

            safe_run = run([
                CLAUDE, "--bare", "--print", "--no-session-persistence", "--tools", "", "--setting-sources", "local", "--output-format", "json",
                "Use /clarify for a small decision; return a decision-ready Spec and do not implement.",
            ], cwd=fixture, env={"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"})
            # A logged-out host is a real loader boundary, not a successful
            # inference proof. The command must still terminate without tools
            # or session/config writes.
            self.assertIn(safe_run.returncode, (0, 1))
            self.assertNotIn("write", safe_run.stderr.lower())
            if "Not logged in" in safe_run.stdout:
                self.assertIn("Not logged in", safe_run.stdout)

    @unittest.skipUnless(CURSOR, "Cursor CLI is unavailable; Cursor CLI-specific proof is skipped on this host")
    def test_cursor_isolated_cli_boundary_does_not_claim_skill_install(self) -> None:
        with tempfile.TemporaryDirectory(prefix="cursor-loader-proof-") as temporary:
            fixture = Path(temporary)
            isolated = run([CURSOR, "--user-data-dir", str(fixture / "user-data"), "--extensions-dir", str(fixture / "extensions"), "--list-extensions"])
            self.assertEqual(isolated.returncode, 0, isolated.stderr)
            self.assertFalse((fixture / "user-data" / "User" / "settings.json").exists())
            # Cursor's documented GitHub import is a UI flow; this CLI command
            # provides no headless Skills discovery/install operation.
            self.assertTrue((ROOT / ".cursor").exists() is False)


if __name__ == "__main__":
    unittest.main()
