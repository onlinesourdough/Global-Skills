from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_metadata_validator", ROOT / "scripts" / "validate_repo.py")
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SkillMetadataTests(unittest.TestCase):
    def check(self, metadata: str, description: str = "Edit supplied prose.") -> list[str]:
        with tempfile.TemporaryDirectory(prefix="skill-metadata-") as temporary:
            fixture = Path(temporary)
            skill = fixture / "sample" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_text("---\nname: sample\ndescription: " + description + "\n" + metadata + "---\n\n# Sample\n\nPreserve facts.\n")
            original = VALIDATOR.ROOT
            VALIDATOR.ROOT = fixture
            try:
                errors: list[str] = []
                VALIDATOR.validate_skill(skill, errors)
                return errors
            finally:
                VALIDATOR.ROOT = original

    def test_portable_metadata_accepts_independent_semver_and_other_metadata(self) -> None:
        self.assertEqual(self.check('metadata:\n  version: "2.10.3"\n  author: "Example"\n'), [])

    def test_plain_yaml_indicators_fail_and_quoted_equivalents_pass(self) -> None:
        for value in ("- item", "? key", "# comment", "] item", "1e3", "2026-09-12", "on", "Task:", "true ", "null "):
            with self.subTest(value=value):
                self.assertTrue(self.check('metadata:\n  version: "1.0.0"\n', value))
                self.assertEqual(self.check('metadata:\n  version: "1.0.0"\n', '"' + value + '"'), [])

    def test_missing_malformed_and_duplicate_versions_fail(self) -> None:
        for metadata in ("", 'version: "1.0.0"\n', 'metadata:\n  version: "01.0.0"\n',
                         'metadata:\n  version: "1.0"\n', 'metadata:\n  version: "next"\n',
                         'metadata:\n  version: 1.0.0\n', 'metadata:\n  version: "1.0.0\n',
                         "metadata:\n  version: '1.0.0\"\n",
                         'metadata:\n  version: "1.0.0"\n  version: "2.0.0"\n'):
            with self.subTest(metadata=metadata):
                self.assertTrue(self.check(metadata))


class SkillVersionProgressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="skill-version-")
        self.fixture = Path(self.temporary.name)
        self.original = VALIDATOR.ROOT
        VALIDATOR.ROOT = self.fixture
        self.skill = self.fixture / "skills" / "sample" / "SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.skill.write_text('---\nname: sample\ndescription: Edit text.\nmetadata:\n  version: "1.0.0"\n---\n\nPreserve facts.\n')
        self.resource = self.skill.parent / "example.txt"
        self.resource.write_text("Original example.\n")
        for args in (("init", "-q"), ("config", "user.name", "Fixture"),
                     ("config", "user.email", "fixture@example.invalid"), ("add", "."),
                     ("commit", "-qm", "Initial skill")):
            subprocess.run(["git", *args], cwd=self.fixture, check=True, capture_output=True)

    def tearDown(self) -> None:
        VALIDATOR.ROOT = self.original
        self.temporary.cleanup()

    def errors(self) -> list[str]:
        errors: list[str] = []
        VALIDATOR.validate_versions_against("HEAD", errors)
        return errors

    def test_unchanged_payload_and_repository_only_change_pass(self) -> None:
        self.assertEqual(self.errors(), [])
        (self.fixture / "README.md").write_text("Repository documentation.\n")
        self.assertEqual(self.errors(), [])

    def test_changed_or_removed_resource_requires_bump(self) -> None:
        self.resource.write_text("Changed example.\n")
        self.assertTrue(self.errors())
        self.skill.write_text(self.skill.read_text().replace('"1.0.0"', '"1.0.1"'))
        self.assertEqual(self.errors(), [])
        self.skill.write_text(self.skill.read_text().replace('"1.0.1"', '"1.0.0"'))
        self.resource.unlink()
        self.assertTrue(self.errors())

    def test_version_regression_fails(self) -> None:
        self.skill.write_text(self.skill.read_text().replace('"1.0.0"', '"0.9.0"'))
        self.assertTrue(self.errors())

    def test_unrepresentable_baseline_integer_cannot_skip_progression(self) -> None:
        huge = "9" * 4301 + ".0.0"
        self.skill.write_text(self.skill.read_text().replace('"1.0.0"', '"' + huge + '"'))
        subprocess.run(["git", "add", "."], cwd=self.fixture, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "Large SemVer baseline"], cwd=self.fixture, check=True, capture_output=True)
        self.skill.write_text(self.skill.read_text().replace('"' + huge + '"', '"1.0.0"'))
        self.assertTrue(self.errors())

    def test_baseline_whitespace_cannot_hide_a_regression(self) -> None:
        self.skill.write_text(self.skill.read_text().replace('version: "1.0.0"', 'version:  "2.0.0"'))
        subprocess.run(["git", "add", "."], cwd=self.fixture, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "Versioned baseline with whitespace"], cwd=self.fixture, check=True, capture_output=True)
        self.skill.write_text(self.skill.read_text().replace('version:  "2.0.0"', 'version: "1.0.0"') + "Changed.\n")
        self.assertTrue(self.errors())


if __name__ == "__main__":
    unittest.main()
