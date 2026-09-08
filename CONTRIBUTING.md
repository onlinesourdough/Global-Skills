# Contributing

Thanks for helping improve Online Sourdough Skills. Open a public issue before
a substantial change so scope and evidence can be agreed without duplicating
work. Do not include credentials, private repository content, client data, or
material you cannot license for redistribution.

Keep each portable payload in `skills/<slug>/SKILL.md` with only the resources
it actually references. Do not add harness-specific copies, personal
configuration, generated caches, or consumer lifecycle/context/history data.
Changes should preserve explicit authority, stop, proof, and rollback
boundaries.

The current Global Skills inventory is `clarify`, `shape-offer`, and
`setup-guardrails`. Skill
management is owned by the AIOS owner route or a native standalone workflow.
Worker orchestration is owned by the AIOS plugin route
`aios-orchestrate-workers`; do not add management or orchestration payloads
here or make these portable methods depend on those routes.

Before opening a pull request, run:

```sh
python3 scripts/validate_repo.py
python3 scripts/secret_scan.py
python3 tests/run_all.py
```

For an optional model-backed Clarify spot-check, run
`python3 tests/forward_clarify.py` separately in an isolated environment; it is
not part of the default suite. Describe the problem, changed behavior,
source/license provenance, tests, and remaining limitations. By contributing,
you agree that your contribution is provided under this repository's MIT
License and that you have the right to submit it.
