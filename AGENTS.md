# Skills repository

This repository is the canonical source for approved, cross-project skills.

- Keep each portable payload in `skills/<slug>/SKILL.md`; do not create
  Codex/Claude/Cursor copies of the instructions.
- Keep the root `.codex-plugin/plugin.json` thin: it exposes the same
  `skills/` directory and owns no context, memory, lifecycle, domain, audit,
  or run-history data.
- Treat `clarify`, `shape-offer`, and `setup-guardrails` as optional
  global capabilities. Skill
  management belongs to the AIOS owner route or a native standalone workflow.
  Worker orchestration belongs to the AIOS plugin route
  `aios-orchestrate-workers`; neither is a Global Skills payload. System,
  Project, domain, lifecycle, and audit skills remain with their existing
  owners.
- For payload or distribution changes, use `python3 tests/run_all.py`; it
  includes source validation and secret scanning. Its fixtures are disposable
  and have no production access. Fix in-scope failures and rerun affected checks
  without asking again. A prose-only correction needs a diff/link inspection.
- Preserve unrelated changes. Do not install globally, change personal
  configuration, edit consumer repositories, or publish from this repository
  during Build.

Keep skill descriptions short enough to distinguish the actual task. Read a
supporting resource only when its condition applies; preserve fragile helper
and recovery requirements. Each skill has an independent `metadata.version`
in quoted SemVer; see CONTRIBUTING.md when changing a payload.

The user's explicit task instructions govern local workflow preferences, within
the active harness's rules. Carry existing authorization through implementation,
verification, fixes and review. Finish that result before asking about an
additional action. Ask only for a material missing decision or permission;
identify the exact source and requirement if it prevents completion. Publication
and native adoption use their recorded destination-specific boundaries.
