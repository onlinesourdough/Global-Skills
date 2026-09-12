# Contributing

Thanks for helping improve Online Sourdough Skills. For a substantial contribution, agree scope in an issue or an existing
maintainer request; an accepted request needs no second issue or approval. Do not include credentials, private repository content, client data, or
material you cannot license for redistribution.

Keep each portable payload in `skills/<slug>/SKILL.md` with only the resources
it actually references. Do not add harness-specific copies, personal
configuration, generated caches, or consumer lifecycle/context/history data.
Changes should preserve explicit authority, stop, proof, and rollback
boundaries.

The current Global Skills inventory is `clarify`, `shape-offer`, and `setup-guardrails`. Skill
management is owned by the AIOS owner route or a native standalone workflow.
Worker orchestration is owned by the AIOS plugin route
`aios-orchestrate-workers`; do not add management or orchestration payloads
here or make these portable methods depend on those routes.

## Skill versions and review

Each `SKILL.md` includes `metadata.version` as a quoted `MAJOR.MINOR.PATCH`
string. Start a newly tracked skill at `1.0.0`; this records a source contract,
not an assertion of native runtime certification. Keep skill versions independent
from the plugin/package version. Change the version of the affected skill when
its body, metadata, referenced instructions, scripts or assets change: patch for
a compatible correction, minor for an additive capability, major for incompatible
inputs, outputs or authority/side-effect expectations. Repository-only docs do
not require a payload bump. Use `python3 scripts/validate_repo.py --base <reviewed-commit>`
to catch changed skill resources without a version increase; the baseline is a
local Git ref and is never fetched automatically. Preserve any other supported metadata.

Use a short, discriminating description and include only guidance that changes
a relevant decision. Conditional resources need a visible use condition. An
instruction cleanup must preserve factual, authority and recovery boundaries.
Inspect a realistic output when behavior changes; parser checks alone do not
prove writing quality or workflow decisions.

Before opening a pull request, run the combined suite (it already executes the
first two checks, which are also available separately):

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

The author validator uses a conservative one-line YAML string profile. Unquoted
root values begin with a letter; quote numeric or indicator-leading strings.
Metadata values are quoted strings. Unsupported YAML is rejected, and native
loader validation remains separate.
