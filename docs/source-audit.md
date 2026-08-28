# Public release source and safety audit

Observation date: 2026-08-28. This is private pre-publication candidate
evidence, not a public-availability claim.

## Boundary and methods

The r2 candidate was built from the then-current private `origin/main`, passed
lead Review, and retained one canonical endpoint:
`https://github.com/onlinesourdough/Skills`. The owner then explicitly
authorized r3 in-place sanitization and selected **WITHHOLD/DELETE** for
historical `v0.1.0` continuity. No repository rename, archive, replacement,
duplicate, or endpoint move is permitted. `v0.2.0` remains an absent planned
tag and will be the first public release only after a later authorized Ship.

Before any rewrite or GitHub edit, the worker created a private mode-700
recovery set outside the canonical checkout. It contains an all-ref mirror, a
verified bundle, the complete reviewed r2 candidate tree and binary diff, and
mode-600 repository, branch, tag, release, issue, comment, event, and pull-
request metadata. Its manifest records byte sizes and SHA-256 hashes. Exact old
object IDs and private metadata remain in that recovery set rather than this
future-public tree.

The audit methods are:

- authenticated GitHub repository/ref/issue/release reads paired with bounded
  anonymous access checks;
- `git ls-remote`, `git for-each-ref`, `git rev-list`, `git cat-file`, bundle
  verification, mirror `git fsck`, and explicit force-with-lease boundaries;
- `python3 scripts/secret_scan.py`, which scans every current-tree file and
  every unique blob reachable from local refs as bytes, reports only signature
  kind/location/line, and never prints a matched value (values never printed);
- non-content-printing SHA-256 category checks for the blocked private
  repository identifier and five-name owner-project inventory, plus URL,
  filesystem path, local-network, generated-file, and object-size checks;
- focused JSON parsing, manifest/marketplace/release validation, full tests,
  pinned dependency/source metadata checks, license reads, and isolated local
  install fixtures; and
- exact private readback of every authorized GitHub mutation before handoff.

## Safety findings

- Before r3, eight unique historical blobs reachable from ordinary branches,
  the private `v0.1.0` tag, and two GitHub-managed pull refs contained direct
  issue URLs to a separate private owner repository or a five-name internal
  owner-project inventory. The known-secret scan found no credentials. Exact
  old refs, object IDs, metadata, and values are retained only in the private
  recovery set.
- The r3 future-public history is intentionally one reviewed clean-root commit
  with no parent. Both ordinary branch refs converge on that commit. This keeps
  the complete lead-reviewed five-skill candidate while excluding obsolete
  private history and generated residue.
- The clean-root tree and every blob reachable from the two future-public
  ordinary refs contain zero blocked private repository identifiers, zero
  blocked inventory occurrences, zero direct private issue URLs, and zero
  known-secret signature matches.
- Historical `v0.1.0` has no public continuity. Its private GitHub release and
  local/remote tag are deleted and must not be recreated. `v0.2.0` is not
  created in r3.
- GitHub-managed pull refs #2 and #3, unreachable old objects, cached diffs,
  and cached views remain a publication blocker until GitHub Support confirms
  purge. The repository stays private while that support action is pending.
- The six authorized Skills issues retain useful technical content while the
  blocked inventory, private owner/design-system issue references, and stale
  release-continuity claims are removed or genericized.
- No current file exceeds one megabyte. Obsolete visual assets and Python
  bytecode are absent from the release tree; ignore rules cover generated
  caches and lock files.
- Standard Git author metadata uses project-appropriate identities. No contact
  lists, phone numbers, customer records, credentials, private filesystem
  roots, live tokens, or captured model transcripts are packaged.

## Source, license, and dependency findings

The candidate is licensed under MIT. Its helper, validators, and tests import
only the Python standard library; the plugin has no runtime MCP, app, hook,
schedule, package-manager, telemetry, or service dependency.

Two skill designs retain limited mechanics from reviewed upstream material:

| Source | Pinned source and license | Retained boundary |
| --- | --- | --- |
| Matt Pocock `grilling/SKILL.md` | [`5b15a47f2d7150f545fbcacbfe381787fc0230dc`](https://github.com/mattpocock/skills/blob/5b15a47f2d7150f545fbcacbfe381787fc0230dc/skills/productivity/grilling/SKILL.md), MIT | Dependency-ordered frontier rounds, self-researched facts, recommendations, and an owner confirmation gate; no branding, relentless framing, or source text is redistributed. |
| Anthropic `eli5/SKILL.md` | [`f4c9452f5ca091f1be7064d9faab1b001ea21645`](https://github.com/anthropics/claude-plugins-community/blob/f4c9452f5ca091f1be7064d9faab1b001ea21645/eli5/skills/eli5/SKILL.md), Apache-2.0 | The idea of an optional named-audience HTML explanation with large visuals and few words; no plugin wrapper, name, or source text is redistributed. |

The implementations are original, substantially expanded paraphrases rather
than copied files. Normalized comparison found one shared nonblank line and a
longest contiguous match of three normalized tokens against `grilling`, and no
shared nonblank line with the same three-token maximum against `eli5`. There is
no material verbatim block requiring upstream license redistribution or NOTICE
treatment. The pins and full licenses were read from canonical GitHub commits.

The optional project adapter is `skills@1.5.23`. npm metadata reports the
Vercel repository, MIT license, and integrity
`sha512-+hMNBSi35yfX0sKD+ZcRm9y5or7u313OdkcvrRvJAsAzGCaA8wRTu2OmVdN0KRbk9ybqKby5dijkn6OVvNTUmw==`;
the pinned source `435076e78988e1e6ec40d00b0b1d76bdbbc5419a`
reports package version `1.5.23`, Node `>=22.20.0`, and MIT. This CLI is an
explicit installer/proof tool, not bundled runtime code.

## Skills Atlas relationship

GitHub remains canonical. After an authorized Ship makes this exact repository
public and verification passes, the public static Skills Atlas defaults to
bounded anonymous GitHub API reads from `onlinesourdough/Skills`, displays the
observed revision and access state, and remains read-only. An optional
authenticated self-hosted mode may propose exactly one validated skill edit on
a new branch and open a pull request; it never writes the default branch. This
candidate does not claim that the repository is public or that the live Atlas
integration works.

## Authorized in-place sanitization and publication gate

The owner authorized only these r3 mutations while the repository remains
private:

1. Force-update `refs/heads/main` and
   `refs/heads/codex/issue-33-cross-harness-portability` to the independently
   verified clean-root candidate, using the exact old identities as
   force-with-lease guards.
2. Delete the private `v0.1.0` GitHub release and local/remote tag. Do not
   recreate or retag it.
3. Sanitize only Skills issue metadata #1, #4, #5, #6, #7, and #8, preserving
   useful safe content and comments where possible.
4. Open a GitHub Support request covering unreachable old objects, cached
   diffs/views, and blocked content retained by GitHub-managed pull refs #2 and
   #3. Disclose only the minimum repository data Support requires.

This route preserves all canonical GitHub, clone, issue, and Atlas URLs; no
rename redirect is involved. A clean-root rewrite necessarily changes commit
identity. Old clones therefore retain obsolete private objects and diverge
from rewritten branches; their operators must reclone or follow explicit
force-fetch and cleanup guidance after publication.

Publication remains **BLOCKED**. GitHub Support must confirm purge, and a new
private-state audit must show zero blocked content across ordinary refs,
GitHub-managed refs, objects, issues, releases, cached diffs, and cached views.
Only a later exact owner Ship authority may then create `v0.2.0`, create its
GitHub release, change candidate metadata to released, or change visibility.

## Candidate proof versus post-Ship proof

During Build and private sanitization, Codex install/discovery uses only a
disposable local Git mirror and commit/ref fixture. The pinned Skills CLI uses
a disposable project and clean local commit fixture with telemetry disabled.
These checks do not publish, install globally, mutate a consumer, or claim a
public tag. Passing install/discovery, lock/ref, topology, and byte-hash checks
also do not prove model-backed behavior in a logged-out or untested Claude Code
or Cursor Agent runtime.

After a later explicitly authorized Ship, public proof must:

1. confirm GitHub Support purge and repeat zero-finding scans across every
   ordinary and managed ref, object, cached diff/view, issue, and release;
2. resolve public `refs/tags/v0.2.0^{}` to the reviewed release commit and
   confirm that no `v0.1.0` tag or release exists;
3. prove anonymous API/HTTP/Git access at the unchanged canonical endpoint and
   verify default branch plus observed revision/access display;
4. in a fresh Codex home, install the pinned `v0.2.0` plugin and compare all
   five skill hashes to the public tag;
5. in a fresh disposable project, repeat pinned Skills CLI discovery,
   install, list, lock/ref, topology, and byte-hash checks; and
6. verify public static Atlas reads the exact canonical repository and remains
   read-only.

## Limitations and recovery

R3 does not create `v0.2.0`, publish a GitHub release, change repository
visibility, touch Skills Atlas or DNS, or prove anonymous installation. GitHub-
managed pull refs and caches remain unverified until Support confirms purge.
External package metadata and source licenses were observed on 2026-08-28 and
can change after their pinned revisions.

The private recovery set can restore exact pre-action refs and metadata only
under a separately authorized rollback. Until public verification succeeds,
the repository remains private. Consumer recovery is to remove only this
plugin or its five named project skills. No public rollback release exists
before `v0.2.0`; `v0.1.0` must not be used or recreated.
