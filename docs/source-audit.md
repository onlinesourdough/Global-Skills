# Public release source and safety audit

This record describes the current `0.3.0` source candidate. It is evidence for
source review, not proof that a public release, native installation, or runtime
integration is available.

## Current source boundary

The repository contains exactly two portable skills: `clarify` and
`shape-offer`. Each canonical payload lives at
`skills/<slug>/SKILL.md`; the Codex manifest, Pi package, and project adapters
must discover those same files. Skill management belongs to the AIOS owner
route or a native standalone workflow. Worker orchestration belongs to the
AIOS plugin route `aios-orchestrate-workers`.

The candidate is an unreleased source candidate. After lead Review, the
reviewed source may be synchronized to the verified canonical `main`; that
source-only synchronization does not create public release availability. The
`v0.3.0` tag, GitHub release, public install, native adoption, and runtime
acceptance remain separate Ship actions.

The verified canonical endpoint is
`https://github.com/onlinesourdough/Global-Skills`, currently observed public.
No rename, archive, replacement, duplicate repository, or Atlas write is part
of this source task. The root package remains private because it is a local
Pi-package declaration, not a claim of npm publication.

## Safety and provenance

- The current tree contains no direct issue URL outside the public
  `Global-Skills` or `Skills-Atlas` boundaries, no known secret signature, and
  no blocked private repository or project-inventory identifier.
- `scripts/secret_scan.py` scans current files and every blob reachable from
  local Git refs as bytes, reporting only match kind and location.
- The retained history starts at the reviewed parentless clean-root baseline;
  `main` descends from it through ordinary single-parent commits. Unreachable
  old objects may still exist locally and are not treated as publishable
  evidence.
- `clarify` retains the named-audience visual-explanation idea from the pinned
  Anthropic `eli5` revision
  `f4c9452f5ca091f1be7064d9faab1b001ea21645` (Apache-2.0), while
  `shape-offer` retains limited mechanics from the pinned Matt Pocock
  `grilling` revision `5b15a47f2d7150f545fbcacbfe381787fc0230dc` (MIT).
  No upstream payload or branding is copied into this repository.
- The optional Skills CLI proof uses the pinned `skills@1.5.23` source
  `435076e78988e1e6ec40d00b0b1d76bdbbc5419a` with the recorded npm integrity.
  Loader, lock, and byte-hash checks do not prove model behavior in an
  untested Claude Code or Cursor Agent runtime.

## Checks

The default local suite is intentionally small and does not launch a model:

```sh
python3 scripts/validate_repo.py
python3 scripts/secret_scan.py
python3 tests/run_all.py
```

The optional model-backed spot-check is separate:

```sh
python3 tests/forward_clarify.py
```

The handwritten inputs under `tests/fixtures/` are optional manual behavior-
review aids, not default test gates or runtime acceptance evidence.

The default checks cover structure, frontmatter, manifests, marketplace and
Pi routes, links, privacy boundaries, candidate state, Git lineage, and
isolated loader topology. The retained fixtures and optional forward script
are the behavior-review path for the two skills.

## Historical release and Ship gate

Historical `v0.1.0` continuity is withheld: its tag and release must not be
recreated. The old four-skill and three-skill release-preparation records are
historical context only; they do not change the current two-skill inventory.

The current history visibility status remains
`PRIVATE_SUPPORT_PURGE_PENDING`. GitHub-managed pull refs, cached diffs/views,
unreachable old objects, and the private-state proof from the historical
sanitization remain unresolved in this record. The repository is observed
public, but that observation does not waive the gate. Publication remains
**BLOCKED** until the Support purge and re-audit requirements below pass.

Before a public `v0.3.0` release or public availability claim, a later exact
Ship authority must require all of the following:

1. GitHub Support confirms purge of the recorded managed refs, cached views,
   and blocked historical objects.
2. A new private-state re-audit finds zero blocked content across ordinary and
   managed refs, objects, issues, releases, and caches.
3. The reviewed source is synchronized to the unchanged canonical endpoint,
   then an immutable `v0.3.0` tag and release are created and read back.
4. Anonymous Git/HTTP/API, Codex, Skills CLI, Atlas, and any selected native
   runtime checks pass before installation is presented as available.

Until then, recovery from public release refs is limited to removing this plugin
or the two project-local skill names. No public rollback release is created
during source preparation.
