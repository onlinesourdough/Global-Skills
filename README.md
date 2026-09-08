![Online Sourdough Skills banner](assets/branding/skills-banner.png)

<a href="assets/branding/skills-icon.png"><img src="assets/branding/skills-icon.png" alt="Online Sourdough Skills icon" width="48" height="48"></a>

# Online Sourdough Skills

Three small, reviewed methods for agent workflows, distributed from one
harness-neutral source. The canonical payload is always
`skills/<slug>/SKILL.md`; the root Codex plugin, Pi package, and other
installers discover that same payload instead of maintaining copies.

The current source candidate is `0.3.1`. Any existing `0.2.0` installation is
legacy content; this candidate uses the distinct `v0.3.1` identity. After lead
Review, its reviewed source may be synchronized to the verified canonical
`main`; that source-only synchronization does not create a public release. Its
public install commands are valid only after the immutable `v0.3.1` tag is
visible on GitHub. Build and Review evidence uses local commit/ref fixtures and
does not claim that the tag already exists.

## Included skills

| Skill | Use it for | Returns |
| --- | --- | --- |
| [`clarify`](skills/clarify/SKILL.md) | Explain one topic or decision for a named audience | One accessible, self-contained visual HTML artifact |
| [`shape-offer`](skills/shape-offer/SKILL.md) | Shape a trust-based offer from customer, delivery, economics, evidence, and owner constraints | A concise Offer Brief and smallest validation |
| [`setup-guardrails`](skills/setup-guardrails/SKILL.md) | Set up or assess a bounded project-local Codex shell safety guard | Readback of configured state, limitations, and recovery |

Skill installation, update, removal, and rollback remain owner-authorized
operations. The management workflow is owned by the AIOS owner route or a
native standalone workflow; it is not an active Global Skills payload. Worker
orchestration is owned by the AIOS plugin route `aios-orchestrate-workers`.
Neither capability is required to discover or use these portable skills.

## Source and scope

This repository owns reusable cross-project methods only. It does not own a
consumer's lifecycle, domain rules, credentials, context, memory, audit, or run
history. The plugin adds no MCP server, app, hook, schedule, telemetry, or
background service.

The root [plugin manifest](.codex-plugin/plugin.json) is intentionally thin: it
points Codex at `./skills/`. The root [Pi package](package.json) points Pi at
the same `./skills` directory. Repository marketplace metadata lives in
[`.agents/plugins/marketplace.json`](.agents/plugins/marketplace.json). There
are no Claude, Cursor, or other copied payload trees in this repository.

## Install a pinned release

Review the tag and [release notes](CHANGELOG.md) before installing. Run
project-local commands inside the project that should discover the skills; do
not switch to global scope unless that wider scope is intentional.

### Codex plugin

With a Codex CLI that supports `codex plugin`, add the repository marketplace
at the immutable release tag, inspect it, and install the plugin:

```sh
codex plugin marketplace add onlinesourdough/Global-Skills --ref v0.3.1
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
npx skills@1.5.23 add onlinesourdough/Global-Skills#v0.3.1 --list
```

Install all three skills for Claude Code and Cursor in the current project, then
inspect discovery and the generated `skills-lock.json`:

```sh
npx skills@1.5.23 add onlinesourdough/Global-Skills#v0.3.1 --skill clarify setup-guardrails shape-offer --agent claude-code cursor -y
npx skills@1.5.23 list --agent claude-code cursor
```

This adapter normally keeps one project copy under
`.agents/skills/<slug>/SKILL.md` and links Claude Code to it. Installation,
listing, lock/ref, and byte-hash evidence do not by themselves prove
model-backed behavior in Claude Code or Cursor Agent.

### Pi package

The root `package.json` exposes the same canonical `./skills` directory to Pi.
Pi's `-l` flag keeps package settings project-local in `.pi/settings.json`.
Because `v0.3.1` is still an unreleased candidate, do not run the pinned
install until that immutable tag exists and has passed Ship verification. In a
disposable project after publication:

```sh
pi install git:github.com/onlinesourdough/Global-Skills@v0.3.1 -l
pi list
```

`pi update --extensions` only reconciles installed packages to their existing
pinned refs. To move this package to a later reviewed ref, install that exact
ref with `-l`; to roll back, install the prior exact ref again:

```sh
pi install git:github.com/onlinesourdough/Global-Skills@<reviewed-ref> -l
```

To remove the current candidate from the same project, use its exact source:

```sh
pi remove git:github.com/onlinesourdough/Global-Skills@v0.3.1 -l
```

These commands are documented usage guidance; this source cleanup does not
install Pi or change project settings. Omit `-l` only when a wider user scope is
intentional.

## Update and rollback

Treat an update as a new pinned-source review: inspect the release diff, record
the prior ref and hashes, install from the new immutable tag, and verify
discovery plus representative behavior. Do not use a mutable branch as a
release ref.

The verified `onlinesourdough/Global-Skills` repository is the current
canonical endpoint and is observed public. The `0.3.1` source candidate remains
unreleased; source-only synchronization to canonical `main` does not create
public release availability, which remains held pending the recorded GitHub
Support purge and private-state re-audit. The owner selected no
historical `v0.1.0` continuity: its private tag and release are removed during
the r3 sanitization and must not be recreated. Until the release gate is
satisfied, the safe recovery is to remove this plugin and its marketplace
snapshot:

```sh
codex plugin remove onlinesourdough-skills@onlinesourdough-skills
codex plugin marketplace remove onlinesourdough-skills
```

For the Skills CLI project adapter, remove only this repository's three skill
names:

```sh
npx skills@1.5.23 remove --skill clarify setup-guardrails shape-offer --agent claude-code cursor -y
npx skills@1.5.23 list --agent claude-code cursor
```

After publication, reinstall only a public rollback ref whose sanitized bytes,
inventory, and unchanged canonical endpoint have passed post-Ship proof. No
public install or rollback command may point to `v0.1.0`. The consumer project
remains usable without these skills, and rollback never creates another
canonical payload or repository.

## Relation to Skills Atlas

[Online Sourdough Skills Atlas](https://github.com/onlinesourdough/Skills-Atlas)
is a separate map and library interface; GitHub remains the canonical source.
After an authorized release and its required verification pass, the public
static Atlas is intended to default to bounded anonymous GitHub API reads from
`onlinesourdough/Global-Skills`, display its observed revision and access state,
and remain read-only. This exact existing repository stays canonical; it is
not renamed, archived, replaced, or duplicated for publication.

An optional authenticated, self-hosted Atlas may propose exactly one validated
skill edit on a new branch and open a pull request. It never writes the default
branch. The repository is currently observed public, but this Build candidate
does not claim that the live Atlas integration works or that an unreleased
`v0.3.1` release is publicly available; both require post-Ship verification.

## Validate a checkout

The repository requires Python 3 and uses only the standard library for its
local scripts and skill helper:

```sh
python3 scripts/validate_repo.py
python3 scripts/secret_scan.py
python3 tests/run_all.py
```

The default suite is local and does not require a model-backed forward run.
For an optional behavior spot-check, run `python3 tests/forward_clarify.py` in
an isolated environment. Candidate/public-source distinctions, provenance,
history findings, and post-Ship verification are recorded in
[`docs/source-audit.md`](docs/source-audit.md) and [`release.json`](release.json).

See [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change,
[SECURITY.md](SECURITY.md) for private vulnerability reporting, and
[SUPPORT.md](SUPPORT.md) for public questions and issues. The repository is
licensed under the [MIT License](LICENSE).
