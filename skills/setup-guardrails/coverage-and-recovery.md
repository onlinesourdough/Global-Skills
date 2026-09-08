# Coverage and recovery

This payload is a deliberately narrow Codex `PreToolUse` guard for the `Bash`
matcher. It recognizes direct shell invocations of recursive deletion against
plainly broad targets, `find ... -delete` on those targets, non-dry-run
`git clean -fdx`, explicit filesystem/partition mutations, and `dd` directed
at a `/dev/` device other than null-like sinks. Explicit read-only/help forms
such as `git clean -nfdx`, `fdisk -l`, `parted --help`, and ext2/3/4
`mkfs -n` or `-V` are allowed. Short options are not generalized between
formatting programs.
It recognizes bare or absolute program paths, normal option forms, quoting,
and the small `env`, `sudo`, and `command` wrappers. Broad deletion targets
include the hook process's normalized absolute `HOME` path without printing or
expanding it, plus lexical root aliases such as `/..`. It does not infer or
protect an arbitrary event `cwd` or project root. It only lexes supplied text;
it neither executes it nor expands variables, globs, or substitutions.

It intentionally does not cover hosted tools, input sent through an existing
`write_stdin` session, specialized/unsupported tool paths, arbitrary
interpreter programs or nested shell payloads, browser UI or connector
semantics, network/database effects, secrets, or adversarial tampering. A
different tool family needs its own documented matcher, schema, and proof.

Codex loads matching hook sources together and requires review/trust for a
non-managed hook; changed hook definitions are skipped pending review. Codex
trust applies to the hook definition, while the copied script's byte integrity
is checked separately by this helper. Therefore a configured file and a
successful local subprocess test do not prove native interception. Do not use
a trust-bypass flag. Confirm the exact hook in `/hooks`, then use the helper's
`status` result as installation evidence only. The active trust and actual
interception evidence remain separate.

The helper changes only an explicit project `.codex/hooks.json` and its
verified `.codex/hooks/agent_guardrails.py` artifact. It rejects malformed
JSON or TOML, inline hook configuration in the same layer, symlinks, duplicate
or changed artifacts, and ownership collisions. It compares `hooks.json`
again immediately before replacement and creates its guard file without
overwriting an existing path. It also rechecks the guard bytes immediately
before deletion, preserving a later edit as recovery-required residue. Re-run
`status` before an update or removal. With
exact authority to remove that project-local guard, run `remove`; it removes
only one verified handler and an unchanged guard file. If it reports drift,
collision, or partial recovery, stop and review that exact state rather than
forcing a replacement. A failed or inconsistent post-write readback is likewise
reported as `verification-required`, never as a no-change result.

It requires Python 3.11+ for the standard `tomllib` parser and rejects the
active global Codex home (`CODEX_HOME`, or the default user `.codex` path). It
does not inspect or modify that global location.

The hook output uses the current documented `permissionDecision: "deny"`
shape for supported `PreToolUse` calls. `continue: false` and `ask` are not
denial mechanisms for this event. Runtime startup failures or a missing Python
interpreter are not guaranteed to fail closed by Codex and must be reported as
coverage gaps.

Source: [OpenAI Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks)
(checked 2026-09-08): hook locations/configuration, trust behavior, tool
coverage, and `PreToolUse` output contract.
