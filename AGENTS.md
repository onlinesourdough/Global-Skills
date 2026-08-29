# Skills repository

This repository is the canonical source for approved, cross-project skills.

- Keep each portable payload in `skills/<slug>/SKILL.md`; do not create
  Codex/Claude/Cursor copies of the instructions.
- Keep the root `.codex-plugin/plugin.json` thin: it exposes the same
  `skills/` directory and owns no context, memory, lifecycle, domain, audit,
  or run-history data.
- Treat `clarify`, `manage-skills`, `orchestrate-workers`, and `shape-offer` as
  optional global capabilities. System, Project, domain, lifecycle, and audit
  skills remain with their existing owners.
- Use the deterministic checks in `scripts/` and `tests/` before handoff.
- Preserve unrelated changes. Do not install globally, change personal
  configuration, edit consumer repositories, or publish from this repository
  during Build.
