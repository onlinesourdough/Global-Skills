from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "setup-guardrails"
GUARD = SKILL / "guardrails.py"
INSTALLER = SKILL / "install_guardrails.py"
INSTALLER_SPEC = importlib.util.spec_from_file_location("agent_guardrails_installer", INSTALLER)
assert INSTALLER_SPEC and INSTALLER_SPEC.loader
INSTALLER_MODULE = importlib.util.module_from_spec(INSTALLER_SPEC)
INSTALLER_SPEC.loader.exec_module(INSTALLER_MODULE)


def event(command: object) -> bytes:
    return json.dumps({
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }).encode("utf-8")


def run_guard(payload: bytes, *, home: str | None = None) -> tuple[int, dict[str, object] | None]:
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if home is not None:
        environment["HOME"] = home
    result = subprocess.run(["python3", str(GUARD)], input=payload, capture_output=True, timeout=10, env=environment)
    output = json.loads(result.stdout) if result.stdout else None
    return result.returncode, output


def denial(payload: bytes) -> str:
    code, output = run_guard(payload)
    if code != 0 or not output:
        raise AssertionError((code, output))
    return output["hookSpecificOutput"]["permissionDecisionReason"]  # type: ignore[index]


class GuardHookTests(unittest.TestCase):
    def test_direct_destructive_forms_are_denied_without_execution(self) -> None:
        commands = [
            "rm -rf /",
            "rm -rf //",
            '"/bin/rm" --recursive --force -- "$HOME"',
            "sudo -u root /bin/rm -r ../",
            "env -u X command /bin/rm -r .",
            "echo harmless; /bin/rm -rf /",
            "echo harmless\n/bin/rm -rf /",
            'find "/" -delete',
            "find -delete",
            "git -C /tmp clean -fdx",
            "/sbin/mkfs.ext4 /dev/synthetic-device",
            "dd if=/dev/zero of=/dev/synthetic-device",
            "diskutil eraseDisk APFS fixture /dev/synthetic-device",
        ]
        for command in commands:
            with self.subTest(command=command):
                reason = denial(event(command))
                self.assertTrue(reason.startswith("Blocked "))

        for command in ("rm -rf /home/synthetic", "rm -rf /home/synthetic/*", "rm -rf /home/synthetic/../synthetic", "rm -rf /.."):
            with self.subTest(command=command):
                code, output = run_guard(event(command), home="/home/synthetic")
                self.assertEqual(code, 0)
                self.assertTrue(output["hookSpecificOutput"]["permissionDecisionReason"].startswith("Blocked "))  # type: ignore[index]

    def test_safe_and_harmless_arguments_are_allowed(self) -> None:
        commands = [
            "pwd",
            "rm -rf ./scratch",
            "rm --recursive work",
            "dd if=input of=/tmp/output",
            "dd if=input of=/dev/null",
            "git clean -nfdx",
            "git -C /tmp clean --dry-run -fdx",
            "fdisk -l /dev/synthetic-device",
            "parted --help",
            "mkfs.ext4 -n /dev/synthetic-device",
            "mkfs.ext4 -V /dev/synthetic-device",
            "echo 'rm -rf /'",
            "echo ';' rm -rf /",
            "echo ok # ; rm -rf /",
            'find ./scratch -name "*" -delete',
            "'' rm -rf /",
            'printf "%s\\n" "git clean -fdx"',
        ]
        for command in commands:
            with self.subTest(command=command):
                code, output = run_guard(event(command))
                self.assertEqual(code, 0)
                self.assertIsNone(output)

    def test_verbose_ext4_format_is_not_mistaken_for_a_no_op(self) -> None:
        reason = denial(event("mkfs.ext4 -v /dev/synthetic-device"))
        self.assertTrue(reason.startswith("Blocked "))

    def test_malformed_input_denies_with_bounded_output(self) -> None:
        malformed = [b"{", event(["not", "a", "command"]), event('rm -rf "unterminated')]
        for payload in malformed:
            with self.subTest(payload=payload[:12]):
                reason = denial(payload)
                self.assertEqual(reason, "Agent guardrails denied malformed Bash hook input.")
                self.assertNotIn("unterminated", reason)


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="agent-guardrails-")
        self.project = Path(self.temporary.name) / "project"
        self.scope = self.project / ".codex"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_unrelated_config(self) -> dict[str, object]:
        config: dict[str, object] = {
            "description": "fixture hooks",
            "hooks": {
                "PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo unrelated"}]}],
                "PreToolUse": [{"matcher": "apply_patch", "hooks": [{"type": "command", "command": "echo patch"}]}],
            },
        }
        self.scope.mkdir(parents=True)
        (self.scope / "hooks.json").write_text(json.dumps(config), encoding="utf-8")
        return config

    def test_install_is_replay_safe_and_preserves_unrelated_configuration(self) -> None:
        before = self.write_unrelated_config()
        first = INSTALLER_MODULE.install(self.scope)
        second = INSTALLER_MODULE.install(self.scope)
        after = json.loads((self.scope / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(first["result"], "configured")
        self.assertEqual(second["result"], "already-configured")
        self.assertEqual(after["description"], before["description"])
        self.assertEqual(after["hooks"]["PostToolUse"], before["hooks"]["PostToolUse"])
        self.assertEqual(after["hooks"]["PreToolUse"][0], before["hooks"]["PreToolUse"][0])
        self.assertEqual(len(after["hooks"]["PreToolUse"]), 2)
        self.assertEqual(INSTALLER_MODULE.check_state(self.scope)["state"], "configured")

    def test_failure_after_copy_rolls_back_new_artifact_and_preserves_config(self) -> None:
        before = self.write_unrelated_config()
        with mock.patch.object(INSTALLER_MODULE, "write_config", side_effect=OSError("synthetic write failure")):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
                INSTALLER_MODULE.install(self.scope)
        after = json.loads((self.scope / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(after, before)
        self.assertFalse((self.scope / "hooks" / "agent_guardrails.py").exists())

    def test_removal_only_touches_verified_owned_artifacts(self) -> None:
        before = self.write_unrelated_config()
        INSTALLER_MODULE.install(self.scope)
        removed = INSTALLER_MODULE.remove(self.scope)
        after = json.loads((self.scope / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(removed["result"], "removed")
        self.assertEqual(after, before)
        self.assertFalse((self.scope / "hooks" / "agent_guardrails.py").exists())
        self.assertEqual(INSTALLER_MODULE.remove(self.scope)["result"], "already-absent")

    def test_removal_preserves_preexisting_empty_groups(self) -> None:
        before = self.write_unrelated_config()
        before["hooks"]["PreToolUse"].insert(0, {"matcher": "mcp__fixture__.*", "hooks": []})  # type: ignore[index]
        (self.scope / "hooks.json").write_text(json.dumps(before), encoding="utf-8")
        INSTALLER_MODULE.install(self.scope)
        INSTALLER_MODULE.remove(self.scope)
        after = json.loads((self.scope / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(after, before)

    def test_removal_keeps_unrelated_hook_artifacts(self) -> None:
        INSTALLER_MODULE.install(self.scope)
        unrelated = self.scope / "hooks" / "unrelated.py"
        unrelated.write_text("fixture\n", encoding="utf-8")
        result = INSTALLER_MODULE.remove(self.scope)
        self.assertEqual(result["result"], "removed")
        self.assertFalse((self.scope / "hooks" / "agent_guardrails.py").exists())
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "fixture\n")

    def test_changed_artifact_and_malformed_or_inline_config_are_no_change_collisions(self) -> None:
        INSTALLER_MODULE.install(self.scope)
        guard = self.scope / "hooks" / "agent_guardrails.py"
        guard.write_text("changed fixture\n", encoding="utf-8")
        config_before = (self.scope / "hooks.json").read_bytes()
        self.assertEqual(INSTALLER_MODULE.check_state(self.scope)["state"], "drifted")
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(self.scope)
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.remove(self.scope)
        self.assertEqual((self.scope / "hooks.json").read_bytes(), config_before)

        other_scope = self.project / "other" / ".codex"
        other_scope.mkdir(parents=True)
        (other_scope / "hooks.json").write_text("{", encoding="utf-8")
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(other_scope)
        self.assertFalse((other_scope / "hooks" / "agent_guardrails.py").exists())

        inline_scope = self.project / "inline" / ".codex"
        inline_scope.mkdir(parents=True)
        (inline_scope / "config.toml").write_text("[hooks]\n", encoding="utf-8")
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(inline_scope)
        self.assertFalse((inline_scope / "hooks.json").exists())

    def test_symlinked_hook_paths_are_rejected_without_following_them(self) -> None:
        self.scope.mkdir(parents=True)
        outside = self.project / "outside"
        outside.mkdir()
        (self.scope / "hooks").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(self.scope)
        self.assertEqual(list(outside.iterdir()), [])

    def test_active_global_codex_home_is_rejected_without_inspection(self) -> None:
        global_scope = self.project / "global" / ".codex"
        project_scope = self.project / "project-local" / ".codex"
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(global_scope)}):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
                INSTALLER_MODULE.resolve_scope(str(global_scope))
            self.assertEqual(INSTALLER_MODULE.resolve_scope(str(project_scope)), project_scope.resolve())
        self.assertFalse(global_scope.exists())

    def test_missing_hooks_object_is_added_without_replacing_other_config(self) -> None:
        self.scope.mkdir(parents=True)
        (self.scope / "hooks.json").write_text(json.dumps({"description": "preserve me"}), encoding="utf-8")
        result = INSTALLER_MODULE.install(self.scope)
        config = json.loads((self.scope / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(result["result"], "configured")
        self.assertEqual(config["description"], "preserve me")
        self.assertIn("PreToolUse", config["hooks"])

    def test_unknown_marker_collision_does_not_overwrite_existing_hook(self) -> None:
        self.scope.mkdir(parents=True)
        config = {
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "echo foreign", "timeout": 2, "statusMessage": INSTALLER_MODULE.MARKER}],
                }],
            },
        }
        hooks_file = self.scope / "hooks.json"
        hooks_file.write_text(json.dumps(config), encoding="utf-8")
        before = hooks_file.read_bytes()
        self.assertEqual(INSTALLER_MODULE.check_state(self.scope)["state"], "ownership-collision")
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(self.scope)
        self.assertEqual(hooks_file.read_bytes(), before)
        self.assertFalse((self.scope / "hooks" / "agent_guardrails.py").exists())

    def test_toml_forms_and_malformed_pretool_groups_refuse_without_replacement(self) -> None:
        for name, content in {
            "array": "[[hooks.PreToolUse]]\nmatcher = 'Bash'\n",
            "inline": "hooks = {}\n",
            "quoted": '["hooks"]\n',
        }.items():
            with self.subTest(name=name):
                scope = self.project / name / ".codex"
                scope.mkdir(parents=True)
                (scope / "config.toml").write_text(content, encoding="utf-8")
                self.assertTrue(INSTALLER_MODULE.inline_hooks_present(scope))
                with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
                    INSTALLER_MODULE.install(scope)
                self.assertFalse((scope / "hooks.json").exists())

        malformed_scope = self.project / "malformed" / ".codex"
        malformed_scope.mkdir(parents=True)
        (malformed_scope / "config.toml").write_text("[hooks\n", encoding="utf-8")
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(malformed_scope)

        groups_scope = self.project / "groups" / ".codex"
        groups_scope.mkdir(parents=True)
        hooks_file = groups_scope / "hooks.json"
        hooks_file.write_text(json.dumps({"hooks": {"PreToolUse": [{}]}}), encoding="utf-8")
        before = hooks_file.read_bytes()
        with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
            INSTALLER_MODULE.install(groups_scope)
        self.assertEqual(hooks_file.read_bytes(), before)

    def test_compare_before_replace_and_new_artifact_creation_refuse_later_edits(self) -> None:
        self.write_unrelated_config()
        original_write_config = INSTALLER_MODULE.write_config

        def concurrent_config_edit(path: Path, config: dict[str, object], expected: bytes | None) -> None:
            path.write_text(json.dumps({"description": "later edit", "hooks": {}}), encoding="utf-8")
            original_write_config(path, config, expected)

        with mock.patch.object(INSTALLER_MODULE, "write_config", side_effect=concurrent_config_edit):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
                INSTALLER_MODULE.install(self.scope)
        self.assertEqual(json.loads((self.scope / "hooks.json").read_text(encoding="utf-8"))["description"], "later edit")
        self.assertFalse((self.scope / "hooks" / "agent_guardrails.py").exists())

        artifact_scope = self.project / "artifact" / ".codex"
        artifact_scope.mkdir(parents=True)
        original_write_new_guard = INSTALLER_MODULE.write_new_guard

        def later_artifact(path: Path) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("later artifact\n", encoding="utf-8")
            original_write_new_guard(path)

        with mock.patch.object(INSTALLER_MODULE, "write_new_guard", side_effect=later_artifact):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsError):
                INSTALLER_MODULE.install(artifact_scope)
        self.assertEqual((artifact_scope / "hooks" / "agent_guardrails.py").read_text(encoding="utf-8"), "later artifact\n")
        self.assertFalse((artifact_scope / "hooks.json").exists())

    def test_partial_removal_reports_guard_residue_and_can_be_retried(self) -> None:
        INSTALLER_MODULE.install(self.scope)
        with mock.patch.object(Path, "unlink", side_effect=OSError("synthetic unlink failure")):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsPartialError) as raised:
                INSTALLER_MODULE.remove(self.scope)
        self.assertEqual(raised.exception.state["state"], "guard-residue")
        self.assertEqual(INSTALLER_MODULE.check_state(self.scope)["state"], "not-configured")
        self.assertEqual(INSTALLER_MODULE.remove(self.scope)["result"], "removed-residue")

    def test_removal_preserves_a_guard_edited_after_config_replacement(self) -> None:
        INSTALLER_MODULE.install(self.scope)
        guard = self.scope / "hooks" / "agent_guardrails.py"
        original_write_config = INSTALLER_MODULE.write_config

        def edit_guard_after_config(path: Path, config: dict[str, object], expected: bytes | None) -> None:
            original_write_config(path, config, expected)
            guard.write_text("later independent edit\n", encoding="utf-8")

        with mock.patch.object(INSTALLER_MODULE, "write_config", side_effect=edit_guard_after_config):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsPartialError) as raised:
                INSTALLER_MODULE.remove(self.scope)
        self.assertEqual(raised.exception.state["guard_integrity"], "changed")
        self.assertEqual(guard.read_text(encoding="utf-8"), "later independent edit\n")
        self.assertEqual(INSTALLER_MODULE.check_state(self.scope)["state"], "not-configured")

    def test_post_write_readback_failures_are_recovery_required(self) -> None:
        original_check_state = INSTALLER_MODULE.check_state
        install_calls = 0

        def fail_install_readback(scope: Path) -> dict[str, object]:
            nonlocal install_calls
            install_calls += 1
            if install_calls == 2:
                raise INSTALLER_MODULE.GuardrailsError("synthetic readback failure")
            return original_check_state(scope)

        with mock.patch.object(INSTALLER_MODULE, "check_state", side_effect=fail_install_readback):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsPartialError) as raised:
                INSTALLER_MODULE.install(self.scope)
        self.assertEqual(raised.exception.state["state"], "verification-required")
        self.assertIsNone(raised.exception.state["configured"])
        self.assertTrue((self.scope / "hooks" / "agent_guardrails.py").exists())

        remove_calls = 0

        def fail_remove_readback(scope: Path) -> dict[str, object]:
            nonlocal remove_calls
            remove_calls += 1
            if remove_calls == 2:
                raise INSTALLER_MODULE.GuardrailsError("synthetic readback failure")
            return original_check_state(scope)

        with mock.patch.object(INSTALLER_MODULE, "check_state", side_effect=fail_remove_readback):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsPartialError) as raised:
                INSTALLER_MODULE.remove(self.scope)
        self.assertEqual(raised.exception.state["state"], "verification-required")
        self.assertFalse((self.scope / "hooks" / "agent_guardrails.py").exists())

    def test_residue_readback_and_os_errors_are_recovery_required(self) -> None:
        INSTALLER_MODULE.install(self.scope)
        hooks_file, _, guard = INSTALLER_MODULE.paths(self.scope)
        config, _, _ = INSTALLER_MODULE.read_config(hooks_file)
        expected = INSTALLER_MODULE.handler_for(guard)
        config["hooks"]["PreToolUse"] = [
            {**group, "hooks": [handler for handler in group["hooks"] if handler != expected]}
            for group in config["hooks"]["PreToolUse"]
        ]
        config["hooks"].pop("PreToolUse")
        hooks_file.write_text(json.dumps(config), encoding="utf-8")
        original_check_state = INSTALLER_MODULE.check_state
        calls = 0

        def fail_residue_readback(scope: Path) -> dict[str, object]:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("synthetic filesystem read failure")
            return original_check_state(scope)

        with mock.patch.object(INSTALLER_MODULE, "check_state", side_effect=fail_residue_readback):
            with self.assertRaises(INSTALLER_MODULE.GuardrailsPartialError) as raised:
                INSTALLER_MODULE.remove(self.scope)
        self.assertEqual(raised.exception.state["state"], "verification-required")
        self.assertIsNone(raised.exception.state["configured"])
        self.assertFalse(guard.exists())

    def test_cli_status_install_and_remove_stay_inside_disposable_scope(self) -> None:
        commands = ("status", "install", "status", "remove")
        results = []
        for action in commands:
            result = subprocess.run(
                ["python3", str(INSTALLER), action, "--codex-dir", str(self.scope)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            results.append(json.loads(result.stdout))
        self.assertEqual(results[0]["state"], "absent")
        self.assertEqual(results[1]["result"], "configured")
        self.assertEqual(results[2]["state"], "configured")
        self.assertEqual(results[3]["result"], "removed")


if __name__ == "__main__":
    unittest.main()
