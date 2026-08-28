---
name: route-models
description: Select advisor, default, and stronger model roles from fresh keyless metadata using stable capability, expected-total-cost, and risk policy. Use when choosing or refreshing a model/reasoning route, checking stale or missing metadata, or explaining an offline fallback; never hardcode a transient model selection.
---

# Route Models

Choose a model role from current evidence while keeping policy stable across
model releases, providers, and harnesses. This skill advises a route; it does
not silently change the active harness, launch contract, or owner authority.

## Gather evidence

1. Inspect the current harness's native model, reasoning, session, and
   cross-harness availability using its documented local path. Do not inspect
   credentials and do not require an API key. Pass the resulting available
   model IDs or harness inventory to the bundled helper; metadata alone never
   proves that this harness can launch a model.
2. Fetch keyless metadata from
   `https://models.dev/models.json` with a normal web or file tool. Record the
   exact source URL, observation time, metadata `last_updated` values when
   present, calculated expiry, schema/version assumptions, harness scope, and
   limitations. Never claim that a route is current without this evidence.
3. Validate each candidate before using it: stable identifier, nonempty name,
   capability modalities, tool support, context limit, both input/output cost
   fields, reasoning information when relevant, and a usable last-updated or
   observation date. Missing or malformed fields make that candidate
   unavailable for the affected decision.

For deterministic local parsing or fixture checks, run the bundled
`scripts/route.py` from this skill directory. It accepts the keyless source
URL or a local metadata fixture plus one or more `--available-model` values or
`--harness-inventory-file`. It emits the route state, role, selected evidence,
source/date/expiry, availability inventory, limitations, and stop/fallback
decision as JSON. Without an explicit inventory it must emit no selection.

## Apply stable policy

Classify the work by required capability, context size, tool/reasoning needs,
risk, latency, and expected total cost. Prefer the lowest expected total cost
that can reliably satisfy the capability and risk requirement. Expected total
cost includes subscription limits, retries, latency, failure risk, and review
rework, not only token price.

Maintain three role labels:

- **advisor**: the least-cost capable route for researching the decision and
  exposing uncertainty;
- **default**: the lowest expected-total-cost route that can complete the
  bounded work reliably;
- **stronger**: a higher-quality or higher-reliability route justified by high
  risk, ambiguity, context, repeated loops, or failed review.

Select candidates by capability first, then filter to the caller-supplied
harness inventory, then risk fit, expected total cost, freshness, and a stable
lexical identifier as the final tie-break. Keep actual
model IDs and reasoning levels in the ephemeral launch/Spec record only; do
not put transient selections in this skill, durable policy, memory, or a
package owner context.

For high-risk work, require a reasoning-capable candidate in addition to the
requested capabilities. If the caller's inventory or metadata cannot prove
that fit, stop for an owner decision instead of silently downgrading to a
cheaper role.

## Freshness and deterministic fallback

Use these explicit states in the route result:

- **current**: live metadata is fetched, schema-valid, within its calculated
  expiry, cost-ranked, capability-eligible, and the selected role is present
  in the caller-supplied harness inventory.
- **stale**: the cached role map exists but its expiry has passed. Use it only
  for reversible, low-risk work with a visible stale warning; require an owner
  decision before high-risk or consequential work. Refresh before the next
  relevant handoff.
- **network-failed**: the live fetch failed. Use a valid cached role map with
  an offline warning; if no cache exists, apply the missing-metadata state.
- **missing**: there is no valid live or cached metadata. Return
  `needs-decision`, state the uncertainty, and use only the harness's explicit
  native-default role for low-risk exploratory work. Do not call that route
  current and do not proceed with consequential work.
- **unavailable-selection**: the requested role or candidate cannot satisfy
  the validated capability, cost evidence, or caller-supplied availability.
  Return no selection and `needs-decision`; obtain an owner decision rather
  than silently substituting a model. Never call an unusable selection
  current or best.

Always return the state, role, selected evidence, source/date/expiry,
availability evidence, limitations, confidence, invalidation signals, and
whether owner confirmation is required. Treat missing, empty, stale, or
unavailable harness inventory as a visible stop. Stop and report a launch
failure when the required route is unavailable or a harness would silently
substitute another model.

## Refresh and hand off

Refresh on an explicit audit, when the brief is older than 30 days, when it
expires, when a selection is unavailable, or when the source/method changes.
Do not combine incompatible benchmarks into a universal score. Preserve the
prior usable brief as stale when fresh research fails, and report the exact
later consumer migration needed to replace local routing copies. Return the
role recommendation and evidence to the owner; do not launch implementation
or mutate a consumer repository from this skill.

For deterministic local checks or an explicitly supplied metadata fixture, use
the bundled `scripts/route.py`. It emits an ephemeral route record and never
writes a cache or configuration unless a caller provides its own storage step.
