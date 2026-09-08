#!/usr/bin/env python3
"""A deliberately small PreToolUse guard for direct, destructive Bash calls.

It reads one JSON object from stdin and emits only the documented Codex denial
shape when it recognizes a covered command.  It never runs, expands, logs, or
returns the submitted command.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Iterable


MAX_INPUT_BYTES = 65_536
MAX_COMMAND_CHARS = 16_384
DENY_MALFORMED = "Agent guardrails denied malformed Bash hook input."


def deny(reason: str) -> None:
    """Emit a bounded PreToolUse denial without echoing untrusted input."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }, separators=(",", ":")))


@dataclass(frozen=True)
class Token:
    value: str
    separator: bool = False


def tokenize(command: str) -> list[Token]:
    """Lex a small shell subset without executing or expanding anything.

    The lexer retains whether separators were unquoted.  ``shlex`` discards
    that provenance, which would make a quoted semicolon look like a command
    separator and loses unquoted newline separators entirely.
    """
    tokens: list[Token] = []
    word: list[str] = []
    word_started = False
    quote: str | None = None
    comment = False
    index = 0

    def flush() -> None:
        nonlocal word_started
        if word_started:
            tokens.append(Token("".join(word)))
            word.clear()
            word_started = False

    while index < len(command):
        character = command[index]
        if comment:
            if character == "\n":
                tokens.append(Token(character, separator=True))
                comment = False
            index += 1
            continue
        if quote:
            if character == quote:
                quote = None
            elif character == "\\" and quote == '"' and index + 1 < len(command):
                index += 1
                word.append(command[index])
            else:
                word.append(character)
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            word_started = True
        elif character == "#" and not word_started:
            comment = True
        elif character == "\\":
            if index + 1 >= len(command):
                raise ValueError("trailing escape")
            index += 1
            if command[index] != "\n":
                word.append(command[index])
                word_started = True
        elif character in {";", "|", "&"}:
            flush()
            if character in {"|", "&"} and index + 1 < len(command) and command[index + 1] == character:
                character += command[index + 1]
                index += 1
            tokens.append(Token(character, separator=True))
        elif character == "\n":
            flush()
            tokens.append(Token(character, separator=True))
        elif character.isspace():
            flush()
        else:
            word.append(character)
            word_started = True
        index += 1
    if quote:
        raise ValueError("unterminated quote")
    flush()
    return tokens


def command_segments(tokens: Iterable[Token]) -> Iterable[list[str]]:
    """Return simple command segments split at shell control operators.

    This intentionally is not a shell parser.  It is enough to keep arguments
    to commands such as ``echo 'rm -rf /'`` from being treated as commands.
    Dynamic evaluation and interpreter payloads are outside this guard.
    """
    segment: list[str] = []
    for token in tokens:
        if token.separator:
            if segment:
                yield segment
                segment = []
        else:
            segment.append(token.value)
    if segment:
        yield segment


def executable_and_args(segment: list[str]) -> tuple[str, list[str]] | None:
    """Identify a direct program after a small set of non-evaluating wrappers."""
    index = 0
    while index < len(segment) and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", segment[index]):
        index += 1
    if index >= len(segment):
        return None

    program = segment[index]
    index += 1
    base = os.path.basename(program)
    if base == "env":
        index = skip_wrapper_options(
            segment, index, {"-u", "--unset", "-C", "--chdir"}, allow_assignments=True,
        )
        if index >= len(segment):
            return None
        program, base = segment[index], os.path.basename(segment[index])
        index += 1
    if base == "sudo":
        index = skip_wrapper_options(
            segment, index, {"-C", "-g", "-h", "-p", "-r", "-t", "-u", "--close-from", "--group", "--host", "--prompt", "--role", "--type", "--user"},
        )
        if index >= len(segment):
            return None
        program, base = segment[index], os.path.basename(segment[index])
        index += 1
    if base == "command":
        while index < len(segment) and segment[index].startswith("-"):
            index += 1
        if index >= len(segment):
            return None
        program, base = segment[index], os.path.basename(segment[index])
        index += 1
    if program.startswith(".") and not program.startswith("/"):
        return None
    return base, segment[index:]


def skip_wrapper_options(args: list[str], index: int, takes_value: set[str], *, allow_assignments: bool = False) -> int:
    """Skip a bounded set of ordinary wrapper options without evaluating them."""
    while index < len(args):
        value = args[index]
        if value == "--":
            return index + 1
        if allow_assignments and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", value):
            index += 1
            continue
        option, equals, _ = value.partition("=")
        if option in takes_value:
            index += 1 if equals else 2
            continue
        if value.startswith("-"):
            index += 1
            continue
        break
    return index


def risky_target(value: str) -> bool:
    """Return true only for plainly broad filesystem targets."""
    normalized = "/" if value and set(value) == {"/"} else os.path.normpath(value.rstrip("/") or "/")
    broad = {
        "/", "/*", "~", "~/*", "$HOME", "$HOME/*", "${HOME}", "${HOME}/*",
        ".", "..", "*", "./*", "../*",
    }
    home = os.environ.get("HOME")
    if not home or not os.path.isabs(home):
        return normalized in broad
    normalized_home = os.path.normpath(home)
    return normalized in broad or normalized in {normalized_home, f"{normalized_home}/*"}


def rm_is_destructive(args: list[str]) -> bool:
    recursive = False
    targets: list[str] = []
    options_done = False
    for value in args:
        if not options_done and value == "--":
            options_done = True
            continue
        if not options_done and value.startswith("--"):
            recursive = recursive or value == "--recursive"
            continue
        if not options_done and value.startswith("-") and value != "-":
            recursive = recursive or "r" in value[1:] or "R" in value[1:]
            continue
        targets.append(value)
    return recursive and any(risky_target(target) for target in targets)


def find_is_destructive(args: list[str]) -> bool:
    action_index = next((index for index, value in enumerate(args) if value == "-delete"), None)
    if action_index is None:
        return False
    roots: list[str] = []
    paths_open = True
    for value in args[:action_index]:
        if value == "--":
            continue
        if value.startswith("-") or value in {"(", ")", "!", ","}:
            if roots:
                paths_open = False
            continue
        if paths_open:
            roots.append(value)
    return any(risky_target(root) for root in (roots or ["."]))


def git_clean_is_destructive(args: list[str]) -> bool:
    index = skip_wrapper_options(
        args, 0, {"-C", "-c", "--config-env", "--exec-path", "--git-dir", "--namespace", "--super-prefix", "--work-tree"},
    )
    if index >= len(args) or args[index] != "clean":
        return False
    flags = "".join(value[1:] for value in args[index + 1:] if value.startswith("-") and not value.startswith("--"))
    long_flags = set(value for value in args[index + 1:] if value.startswith("--"))
    return "n" not in flags and "--dry-run" not in long_flags and "f" in flags and "d" in flags and ("x" in flags or "--ignored" in long_flags)


def dd_is_destructive(args: list[str]) -> bool:
    for index, value in enumerate(args):
        output = value[3:] if value.startswith("of=") else args[index + 1] if value == "of" and index + 1 < len(args) else None
        if output and output.startswith("/dev/") and output not in {"/dev/null", "/dev/zero", "/dev/full", "/dev/stdout", "/dev/stderr"}:
            return True
    return False


def direct_disk_tool_is_destructive(program: str, args: list[str]) -> bool:
    """Block only mutation forms, leaving explicit inspection/help forms alone."""
    if program.startswith("mkfs"):
        # Do not generalize short options across mkfs variants.  These forms
        # share mke2fs semantics: -n is no-create and -V exits after version.
        if program in {"mke2fs", "mkfs.ext2", "mkfs.ext3", "mkfs.ext4"}:
            return "-n" not in args and "-V" not in args
        return True
    if program == "wipefs":
        return "-n" not in args and "--no-act" not in args and ("-a" in args or "--all" in args)
    if program == "fdisk":
        return not any(value in {"-l", "--list", "-h", "--help", "-v", "--version"} for value in args) and any(value.startswith("/dev/") for value in args)
    if program == "parted":
        if any(value in {"-h", "--help", "-v", "--version"} for value in args):
            return False
        return any(value in {"mklabel", "mkpart", "rm", "resizepart", "set", "disk_set"} for value in args)
    return False


def diskutil_is_destructive(args: list[str]) -> bool:
    """Only an invoked destructive diskutil verb is covered."""
    return bool(args) and args[0] in {"eraseDisk", "partitionDisk"}


def blocked_reason(command: str) -> str | None:
    """Classify only direct, recognizable destructive command forms."""
    for segment in command_segments(tokenize(command)):
        parsed = executable_and_args(segment)
        if parsed is None:
            continue
        program, args = parsed
        if program == "rm" and rm_is_destructive(args):
            return "Blocked destructive recursive filesystem deletion."
        if program == "find" and find_is_destructive(args):
            return "Blocked destructive filesystem traversal deletion."
        if program == "git" and git_clean_is_destructive(args):
            return "Blocked destructive Git clean operation."
        if program in {"wipefs", "fdisk", "parted"} or program.startswith("mkfs"):
            if not direct_disk_tool_is_destructive(program, args):
                continue
            return "Blocked direct filesystem or partition destructive operation."
        if program == "diskutil" and diskutil_is_destructive(args):
            return "Blocked direct disk destructive operation."
        if program == "dd" and dd_is_destructive(args):
            return "Blocked direct-device overwrite operation."
    return None


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            deny(DENY_MALFORMED)
            return 0
        event = json.loads(raw.decode("utf-8"))
        if not isinstance(event, dict) or event.get("hook_event_name") != "PreToolUse" or event.get("tool_name") != "Bash":
            deny(DENY_MALFORMED)
            return 0
        tool_input = event.get("tool_input")
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        if not isinstance(command, str) or len(command) > MAX_COMMAND_CHARS:
            deny(DENY_MALFORMED)
            return 0
        reason = blocked_reason(command)
        if reason:
            deny(reason)
        return 0
    except Exception:
        deny(DENY_MALFORMED)
        return 0


if __name__ == "__main__":
    sys.exit(main())
