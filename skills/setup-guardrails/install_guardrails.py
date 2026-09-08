#!/usr/bin/env python3
"""Install or remove the bounded guard in one explicit project .codex layer.

This helper never reads a trust database or global configuration.  It modifies
only a JSON hooks file passed as an explicit ``--codex-dir`` target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ ships tomllib
    tomllib = None  # type: ignore[assignment]


MARKER = "Online Sourdough destructive-command guard"
GUARD_NAME = "agent_guardrails.py"


class GuardrailsError(Exception):
    pass


class GuardrailsPartialError(GuardrailsError):
    """A scoped change happened, but its companion artifact needs recovery."""

    def __init__(self, message: str, state: dict[str, Any]):
        super().__init__(message)
        self.state = state


def source_guard() -> Path:
    return Path(__file__).with_name("guardrails.py")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_scope(value: str) -> Path:
    supplied = Path(value).expanduser()
    if supplied.is_symlink():
        raise GuardrailsError("Refusing a symlinked .codex directory.")
    scope = supplied.resolve(strict=False)
    if scope.name != ".codex":
        raise GuardrailsError("The explicit target must be a project .codex directory.")
    active_global = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve(strict=False)
    if scope == active_global:
        raise GuardrailsError("Refusing the active global Codex home; select an explicit project .codex directory.")
    return scope


def paths(scope: Path) -> tuple[Path, Path, Path]:
    hooks_file = scope / "hooks.json"
    hooks_dir = scope / "hooks"
    guard = hooks_dir / GUARD_NAME
    return hooks_file, hooks_dir, guard


def handler_for(guard: Path) -> dict[str, Any]:
    command = f"{shlex.quote(str(Path(sys.executable).resolve()))} {shlex.quote(str(guard))}"
    return {"type": "command", "command": command, "timeout": 2, "statusMessage": MARKER}


def read_config(hooks_file: Path) -> tuple[dict[str, Any], bool, bytes | None]:
    if hooks_file.is_symlink():
        raise GuardrailsError("Refusing a symlinked hooks.json file.")
    if not hooks_file.exists():
        return {"description": "Project-local Codex hooks.", "hooks": {}}, False, None
    try:
        raw = hooks_file.read_bytes()
        config = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GuardrailsError("Existing hooks.json is malformed; no change was made.") from exc
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise GuardrailsError("Existing hooks.json has an unsupported hooks shape; no change was made.")
    config.setdefault("hooks", {})
    return config, True, raw


def inline_hooks_present(scope: Path) -> bool:
    config = scope / "config.toml"
    if config.is_symlink():
        raise GuardrailsError("Refusing a symlinked config.toml file.")
    if not config.exists():
        return False
    if tomllib is None:
        raise GuardrailsError("This installer needs Python 3.11+ to inspect config.toml safely; no change was made.")
    try:
        parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise GuardrailsError("Existing config.toml is malformed or unreadable; no change was made.") from exc
    return "hooks" in parsed


def pretool_groups(config: dict[str, Any]) -> list[dict[str, Any]]:
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        raise GuardrailsError("Existing hooks.json has an unsupported hooks shape; no change was made.")
    groups = hooks.get("PreToolUse", [])
    if not isinstance(groups, list) or any(
        not isinstance(group, dict) or "hooks" not in group or not isinstance(group["hooks"], list)
        for group in groups
    ):
        raise GuardrailsError("Existing PreToolUse hooks have an unsupported shape; no change was made.")
    return groups


def matching_handlers(groups: list[dict[str, Any]], expected: dict[str, Any], guard: Path) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], bool]:
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    collision = False
    expected_command = expected["command"]
    for group in groups:
        for handler in group["hooks"]:
            if not isinstance(handler, dict):
                raise GuardrailsError("Existing PreToolUse handler has an unsupported shape; no change was made.")
            command = handler.get("command")
            marker = handler.get("statusMessage")
            if command == expected_command and marker == MARKER:
                if handler == expected and group.get("matcher") == "Bash":
                    matches.append((group, handler))
                else:
                    collision = True
            elif command == expected_command or marker == MARKER or command == str(guard):
                collision = True
    return matches, collision


def check_state(scope: Path) -> dict[str, Any]:
    hooks_file, hooks_dir, guard = paths(scope)
    if hooks_dir.is_symlink() or guard.is_symlink():
        raise GuardrailsError("Refusing a symlinked guardrails artifact path.")
    config, config_exists, _ = read_config(hooks_file)
    if inline_hooks_present(scope):
        return {"state": "inline-hooks-present", "configured": False, "guard_integrity": "not-checked", "trust": "not-verified", "native_interception": "not-verified"}
    groups = pretool_groups(config)
    expected = handler_for(guard)
    matches, collision = matching_handlers(groups, expected, guard)
    guard_state = "missing"
    if guard.exists():
        if digest(guard) == digest(source_guard()):
            guard_state = "verified"
        else:
            guard_state = "changed"
    if len(matches) > 1:
        return {"state": "duplicate-handler", "configured": True, "guard_integrity": guard_state, "trust": "not-verified", "native_interception": "not-verified"}
    if collision:
        return {"state": "ownership-collision", "configured": bool(matches), "guard_integrity": guard_state, "trust": "not-verified", "native_interception": "not-verified"}
    if matches and guard_state == "verified":
        state = "configured"
    elif matches:
        state = "drifted"
    elif config_exists or guard.exists() or hooks_dir.exists():
        state = "not-configured"
    else:
        state = "absent"
    return {"state": state, "configured": bool(matches), "guard_integrity": guard_state, "trust": "not-verified", "native_interception": "not-verified"}


def atomic_write(path: Path, data: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def write_config(hooks_file: Path, config: dict[str, Any], expected: bytes | None) -> None:
    if hooks_file.is_symlink():
        raise GuardrailsError("Refusing a symlinked hooks.json file.")
    current = hooks_file.read_bytes() if hooks_file.exists() else None
    if current != expected:
        raise GuardrailsError("hooks.json changed after inspection; no replacement was made.")
    mode = stat.S_IMODE(hooks_file.stat().st_mode) if current is not None else 0o600
    atomic_write(hooks_file, (json.dumps(config, indent=2) + "\n").encode("utf-8"), mode)


def cleanup_new_guard(scope: Path, hooks_dir: Path, guard: Path) -> bool:
    if guard.exists() and not guard.is_symlink() and digest(guard) == digest(source_guard()):
        try:
            guard.unlink()
        except OSError:
            return False
    elif guard.exists():
        return False
    for directory in (hooks_dir, scope):
        try:
            directory.rmdir()
        except OSError:
            pass
    return not guard.exists()


def write_new_guard(guard: Path) -> None:
    guard.parent.mkdir(parents=True, exist_ok=True)
    if guard.parent.is_symlink() or guard.is_symlink():
        raise GuardrailsError("Refusing a symlinked guardrails artifact path.")
    descriptor = os.open(guard, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(source_guard().read_bytes())
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        try:
            guard.unlink()
        except OSError:
            pass
        raise


def unlink_verified_guard(guard: Path) -> bool:
    """Delete only bytes that still match this helper's reviewed source."""
    if not guard.exists():
        return False
    if guard.is_symlink() or digest(guard) != digest(source_guard()):
        raise GuardrailsPartialError(
            "Guard handler changed, but the guard artifact was edited before deletion and was preserved.",
            {"state": "guard-residue", "configured": False, "guard_integrity": "changed", "trust": "not-verified", "native_interception": "not-verified"},
        )
    guard.unlink()
    return True


def verification_required(message: str, result: dict[str, Any] | None = None) -> GuardrailsPartialError:
    state = {
        "state": "verification-required",
        "configured": None,
        "guard_integrity": "review-required",
        "trust": "not-verified",
        "native_interception": "not-verified",
    }
    if result is not None:
        state.update(result)
        state["state"] = "verification-required"
    return GuardrailsPartialError(message, state)


def install(scope: Path) -> dict[str, Any]:
    state = check_state(scope)
    if state["state"] == "configured":
        return {"result": "already-configured", **state}
    if state["state"] not in {"absent", "not-configured"}:
        raise GuardrailsError("Guardrails state is ambiguous or changed; no change was made.")

    hooks_file, hooks_dir, guard = paths(scope)
    config, _, expected_config = read_config(hooks_file)
    groups = pretool_groups(config)
    expected = handler_for(guard)
    matches, collision = matching_handlers(groups, expected, guard)
    if matches or collision or guard.exists():
        raise GuardrailsError("Guardrails ownership cannot be established; no change was made.")

    created_guard = False
    try:
        write_new_guard(guard)
        created_guard = True
        groups.append({"matcher": "Bash", "hooks": [expected]})
        config["hooks"]["PreToolUse"] = groups
        write_config(hooks_file, config, expected_config)
    except Exception as exc:
        if created_guard and not cleanup_new_guard(scope, hooks_dir, guard):
            raise GuardrailsPartialError(
                "Installation did not update hooks.json, but a guard artifact remains for recovery.",
                {"state": "guard-residue", "configured": False, "guard_integrity": "review-required", "trust": "not-verified", "native_interception": "not-verified"},
            ) from exc
        raise GuardrailsError("Installation failed before configuration; no hooks.json replacement was made.") from exc
    try:
        result = check_state(scope)
    except (GuardrailsError, OSError) as exc:
        raise verification_required("Installation wrote scoped artifacts, but readback failed; inspect recovery state.") from exc
    if result["state"] != "configured":
        raise verification_required("Installation wrote scoped artifacts, but readback did not verify the guard.", result)
    return {"result": "configured", **result}


def remove(scope: Path) -> dict[str, Any]:
    state = check_state(scope)
    if state["state"] == "absent" or (state["state"] == "not-configured" and state["guard_integrity"] == "missing"):
        return {"result": "already-absent", **state}
    if state["state"] == "not-configured" and state["guard_integrity"] == "verified":
        _, hooks_dir, guard = paths(scope)
        try:
            unlink_verified_guard(guard)
        except GuardrailsPartialError:
            raise
        except OSError as exc:
            raise GuardrailsPartialError(
                "Verified guard residue could not be removed; retry after reviewing that artifact.",
                {"state": "guard-residue", "configured": False, "guard_integrity": "verified", "trust": "not-verified", "native_interception": "not-verified"},
            ) from exc
        try:
            hooks_dir.rmdir()
        except OSError:
            pass
        try:
            result = check_state(scope)
        except (GuardrailsError, OSError) as exc:
            raise verification_required("Residue removal changed scoped artifacts, but readback failed; inspect recovery state.") from exc
        return {"result": "removed-residue", **result}
    if state["state"] != "configured":
        raise GuardrailsError("Guardrails ownership or integrity is not verified; no change was made.")
    hooks_file, hooks_dir, guard = paths(scope)
    config, _, expected_config = read_config(hooks_file)
    groups = pretool_groups(config)
    expected = handler_for(guard)
    updated: list[dict[str, Any]] = []
    removed = 0
    for group in groups:
        handlers = [handler for handler in group["hooks"] if handler != expected]
        removed += len(group["hooks"]) - len(handlers)
        if handlers or not group["hooks"]:
            group = {**group, "hooks": handlers}
            updated.append(group)
    if removed != 1:
        raise GuardrailsError("Expected one verified guard handler; no change was made.")
    config["hooks"]["PreToolUse"] = updated
    if not updated:
        config["hooks"].pop("PreToolUse")
    write_config(hooks_file, config, expected_config)
    try:
        unlink_verified_guard(guard)
    except GuardrailsPartialError:
        raise
    except OSError as exc:
        raise GuardrailsPartialError(
            "Guard handler was removed, but the verified guard file remains for recovery.",
            {"state": "guard-residue", "configured": False, "guard_integrity": "verified", "trust": "not-verified", "native_interception": "not-verified"},
        ) from exc
    try:
        hooks_dir.rmdir()
    except OSError:
        pass
    try:
        result = check_state(scope)
    except (GuardrailsError, OSError) as exc:
        raise verification_required("Removal changed scoped artifacts, but readback failed; inspect recovery state.") from exc
    return {"result": "removed", **result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage one project-local Codex guardrails hook.")
    parser.add_argument("action", choices=("status", "install", "remove"))
    parser.add_argument("--codex-dir", required=True, help="Explicit project .codex directory")
    arguments = parser.parse_args()
    try:
        scope = resolve_scope(arguments.codex_dir)
        result = {"scope": "project-local", **({"result": "status"} if arguments.action == "status" else {})}
        if arguments.action == "status":
            result.update(check_state(scope))
        elif arguments.action == "install":
            result.update(install(scope))
        else:
            result.update(remove(scope))
        print(json.dumps(result, sort_keys=True))
        return 0
    except GuardrailsPartialError as exc:
        print(json.dumps({"result": "partial-recovery-required", "reason": str(exc), **exc.state}, sort_keys=True))
        return 1
    except GuardrailsError as exc:
        print(json.dumps({"result": "no-change", "reason": str(exc), "trust": "not-verified", "native_interception": "not-verified"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
