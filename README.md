# Online Sourdough Skills

Four small, reviewed methods for agent workflows, distributed from one
harness-neutral source. The canonical payload is always
`skills/<slug>/SKILL.md`; the root Codex plugin and other installers discover
that same payload instead of maintaining copies.

The current release candidate is `0.2.0`. Its public install commands are
valid only after the immutable `v0.2.0` tag is visible on GitHub. Build and
Review evidence uses local commit/ref fixtures and does not claim that the tag already exists.

## Included skills

| Skill | Use it for | Stops at |
| --- | --- | --- |
| [`clarify`](skills/clarify/SKILL.md) | Resolve material facts and owner decisions before implementation | A decision-ready or explicitly blocked Spec |
| [`manage-skills`](skills/manage-skills/SKILL.md) | Review provenance, overlap, installation, updates, removal, and rollback | Verified, authorized capability state |
| [`orchestrate-workers`](skills/orchestrate-workers/SKILL.md) | Assign independent worker tasks with route, root, writer, recovery, and lead-Review boundaries | A bounded delegation result and lead Review |
| [`shape-offer`](skills/shape-offer/SKILL.md) | Shape a trust-based offer from customer, delivery, economics, evidence, and owner constraints | A concise Offer Brief and smallest validation |

## Source and scope

This repository owns reusable cross-project methods only. It does not own a
consumer's lifecycle, domain rules, credentials, context, memory, audit, or run
history. The plugin adds no MCP server, app, hook, schedule, telemetry, or
background service. Some skills can recommend commands or external actions,
but their own authorization and stop boundaries still apply.

The root [plugin manifest](.codex-plugin/plugin.json) is intentionally thin:
it points Codex at `./skills/`. Repository marketplace metadata lives in
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). There
are no Claude, Cursor, or other copied payload trees in this repository.

## Install a pinned release

Review the tag and [release notes](CHANGELOG.md) before installing. Run project-local commands
inside the project that should discover the skills; do not switch to global
scope unless that wider scope is intentional.

### Codex plugin

With a Codex CLI that supports `codex plugin`, add the repository marketplace
at the immutable release tag, inspect it, and install the plugin:

```sh
codex plugin marketplace add onlinesourdough/Skills --ref v0.2.0
codex plugin list --available --json
codex plugin add onlinesourdough-skills@onlinesourdough-skills
```

The marketplace intentionally keeps
`policy.authentication: "ON_INSTALL"`. Public Git access does not imply a
different marketplace authentication policy.

### Skills CLI

The optional project-local adapter is pinned to `skills@1.5.23`. Discover the
source without installing:

```sh
npx skills@1.5.23 add onlinesourdough/Skills#v0.2.0 --list
```

Install all four skills for Claude Code and Cursor in the current project, then
inspect discovery and the generated `skills-lock.json`:

```sh
npx skills@1.5.23 add onlinesourdough/Skills#v0.2.0 --skill clarify manage-skills orchestrate-workers shape-offer --agent claude-code cursor -y
npx skills@1.5.23 list --agent claude-code cursor
```

This adapter normally keeps one project copy under
`.agents/skills/<slug>/SKILL.md` and links Claude Code to it. Installation,
listing, lock/ref, and byte-hash evidence do not by themselves prove
model-backed behavior in Claude Code or Cursor Agent.

## Update and rollback

Treat an update as a new pinned-source review: inspect the release diff, record
the prior ref and hashes, install from the new immutable tag, and verify
discovery plus representative behavior. Do not use a mutable branch as a
release ref.

The existing `onlinesourdough/Skills` repository remains the canonical
endpoint and may be published only in place. The owner selected no historical
`v0.1.0` continuity: its private tag and release are removed during the r3
sanitization and must not be recreated. `v0.2.0` will be the first public
release. The repository remains private until GitHub Support confirms that old
objects and cached pull-request views have been purged and the private-state
re-audit passes. Until then, the safe recovery is to remove this plugin and its
marketplace snapshot:

```sh
codex plugin remove onlinesourdough-skills@onlinesourdough-skills
codex plugin marketplace remove onlinesourdough-skills
```

For the Skills CLI project adapter, remove only this repository's four skill
names:

```sh
npx skills@1.5.23 remove --skill clarify manage-skills orchestrate-workers shape-offer --agent claude-code cursor -y
npx skills@1.5.23 list --agent claude-code cursor
```

After publication, reinstall only a public rollback ref whose sanitized bytes,
inventory, and unchanged canonical endpoint have passed post-action proof. No
public install or rollback command may point to `v0.1.0`. The consumer project
remains usable without these skills, and rollback never creates another
canonical payload or repository.

## Relation to Skills Atlas

[Online Sourdough Skills Atlas](https://github.com/onlinesourdough/Skills-Atlas)
is a separate map and library interface; GitHub remains the canonical source.
After an authorized Ship makes this repository public and verification passes,
the public static Atlas is intended to default to bounded anonymous GitHub API
reads from `onlinesourdough/Skills`, display its observed revision and access
state, and remain read-only. This exact existing repository stays canonical; it
is not renamed, archived, replaced, or duplicated for publication.

An optional authenticated, self-hosted Atlas may propose exactly one validated
skill edit on a new branch and open a pull request. It never writes the default
branch. This Build candidate does not claim that the Skills repository is
public or that the live Atlas integration works; both require post-Ship
verification.

## Validate a checkout

The repository requires Python 3 and uses only the standard library for its
local scripts and skill helper:

```sh
python3 scripts/validate_repo.py
python3 scripts/secret_scan.py
python3 tests/run_all.py
```

The full suite includes isolated Codex forward checks and can take several
minutes. Candidate/public-source distinctions, provenance, history findings,
and post-Ship verification are recorded in
[`docs/source-audit.md`](docs/source-audit.md) and [`release.json`](release.json).

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change,
[SECURITY.md](SECURITY.md) for private vulnerability reporting, and
[SUPPORT.md](SUPPORT.md) for public questions and issues. The repository is
licensed under the [MIT License](LICENSE).
