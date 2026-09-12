---
name: setup-guardrails
description: Set up or assess a bounded project-local Codex guard against recognizable destructive shell commands.
metadata:
  version: "1.0.0"
---

# Set up guardrails

Use this skill when a user asks to add, inspect, update, or remove a practical
local accident guard for autonomous Codex work. It is a Codex-first seatbelt,
not complete enforcement. It is normally discoverable; do not make the user
invoke a special manual-only workflow.

## Establish the boundary first

Before changing anything, inspect the active harness/version, the selected
project's `.codex/hooks.json` and `.codex/config.toml`, and the requested
scope. Use existing explicit authority for the requested installation, update,
or removal scope; the request itself can supply it. Ask only if the intended
mutation exceeds that authority, and continue independent read-only work. Default only to the selected project-local `.codex` layer;
never replace a whole config file, alter a trust database or Codex
permission mode, or use a trust-bypass flag. This source package does not
activate a hook by itself.

Use [install_guardrails.py](install_guardrails.py) from this skill directory:

```sh
python3 install_guardrails.py status --codex-dir <project>/.codex
python3 install_guardrails.py install --codex-dir <project>/.codex
python3 install_guardrails.py remove --codex-dir <project>/.codex
```

The helper is intentionally scoped: it reads and changes only the explicit
`hooks.json` plus its own copied [guardrails.py](guardrails.py). It refuses
malformed configuration, inline hooks in that layer, symlinks, duplicate or
unknown ownership, and later edits instead of overwriting them. After a change,
read back `status`. If native trust for these exact bytes is absent, the user
must review and trust the hook in `/hooks`; finish configuration and available
checks before returning that concrete native step. Do not re-request existing
trust or claim trust for changed bytes. Report configuration, trust, and observed native interception as
separate evidence; the latter is **not verified** until independently observed.
It requires Python 3.11 or later to parse `config.toml` safely and refuses the
active global Codex home even when it is passed explicitly.

## What the guard does

For the `Bash` `PreToolUse` path only, the guard lexes but never executes or
expands the proposed command. It denies a small set of direct, recognizable
catastrophic forms: recursive deletion against plainly broad paths, broad
`find -delete`, non-dry-run `git clean -fdx`, explicit
formatting/partitioning mutations, and direct-device `dd` writes other than
null-like sinks. It uses the documented `permissionDecision: "deny"` response,
not unsupported `ask` or `continue: false` behavior.

Read [coverage-and-recovery.md](coverage-and-recovery.md) before presenting the
result. In particular, hosted tools, `write_stdin` input to an existing session,
unsupported paths, arbitrary interpreters, browser/connectors, remote effects,
and tampering are outside coverage. If the helper finds drift or a collision,
stop with that fact and give the bounded recovery path; do not force an update.
