---
name: manage-skills
description: Review, install, update, rollback, remove, or compare agent skills safely across harnesses. Use when a concrete capability gap changes the skills available to an agent, or when checking provenance, overlap, version, discovery, or recovery; do not use it as a passive audit report.
---

# Manage Skills

Manage a capability change deliberately. Keep independent projects operable
without a calling AIOS, plugin, personal skill, or central run-history store.

## Distinguish audit from management

An audit detects and reports the current capability state without mutation.
Use the local System/Project audit skill when the request is only to inspect or
report. This skill manages a proposed change: review the gap, decide whether
to reuse or install, and perform an authorized install, update, rollback,
removal, or overlap decision. Do not silently turn an audit into a change.

## Confirm the gap

1. State the task the missing capability must perform and the proof it needs.
2. Dynamically inventory, using current filesystem and harness evidence:
   project-local skills, accessible containing-AIOS skills, harness-native and
   personal/installed skills, repository instructions, and ordinary reasoning.
   Do not hardcode an inventory from one project or AIOS.
3. Compare the sufficient candidates with the task, boundaries, and risk. Reuse
   a sufficient capability and stop. If the gap is not concrete, report it and
   do not search or install.

## Discover and review candidates

Search without installing. Follow the current `skills.sh` CLI documentation;
the common candidate query is `npx skills find <need>` and listing a source is
`npx skills add <owner/repo> --list`. Prefer a reviewed project or organization
source, then the relevant technology owner, then a community source.

Before any mutation, inspect and record the candidate publisher, repository,
exact revision, license, maintenance, `SKILL.md`, referenced resources,
scripts, commands, network access, affected files/services/people, harness
compatibility, overlap, verification, update, removal, and recovery paths.
Treat popularity or an audit badge as evidence to weigh, not approval.

## Get authority before changing state

Present the candidate, material access, intended scope/files, version, risks,
and rollback plan. Ask for explicit authorization before installing, updating,
removing, or changing a global/personal skill. Prefer project scope so the
change is reviewable. Never use `--all`, global scope, or non-interactive
approval flags unless that exact scope was explicitly authorized.

If a harness or source lacks a supported install path, mark it unsupported or
unverified. Do not invent an adapter, claim discovery from a copied prompt, or
make the project depend on a plugin at runtime.

## Install, update, and rollback

Use one named skill from one canonical source. Record source revision, release
version, file hashes, destination scope, and the prior version before writing.
For an update, review the upstream diff and repeat the same candidate review;
do not overwrite a local change without authorization. For rollback, restore a
recorded prior revision, verify its hashes and discovery, and report the
recovery result. A plugin may distribute a source, but it must not create a
second payload fork or own System/Project run history.

## Verify

1. Inspect the exact filesystem and version-control diff.
2. Confirm only the selected skill and expected harness adapter changed.
3. Validate frontmatter, referenced paths, scripts, source/version, and hashes.
4. Confirm the selected harness discovers the skill at the documented scope.
5. Exercise one representative task without production side effects.
6. Report source, revision/license, installed scope, version, evidence,
   rollback state, unsupported harnesses, and remaining risk.

If verification fails, stop, preserve the prior version, and return the
failure. Never update skills automatically.
