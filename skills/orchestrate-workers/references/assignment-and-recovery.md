# Assignment and recovery

Read this reference only when work will be delegated, resumed, steered, or
adapted to a particular runtime.

## Assignment record

Give every worker a bounded record such as:

```text
Outcome and proof: <one independently checkable result>
Root/checkout: <absolute or harness-resolved root>; no access beyond it
Scope: <inputs and owned output paths>; read-only | sole writer
Authority/tools: <allowed actions and tools>; no external action unless named
Route: inherit | override <reason>; advertised-and-launchable evidence required
Attestation: actual worker identity, model/provider/reasoning when exposed,
             harness, root, permission surface, and substitution status
Return: <findings/diff>, commands/results, evidence, limitations, open risks
Stop: <scope conflict, missing authority, route mismatch, failed proof>
```

Do not assign two writers an overlapping repository outcome. If two changes
must eventually meet, use separate worktrees/checkouts and name a single lead
integrator, or make one assignment review-only.

## Runtime adapter boundary

Ask the active runtime for its own advertised and launchable inventory; do not
invent a universal worker API. A local, provider-qualified, or otherwise
advertised model is eligible only after a real launch attestation. A model
present only in configuration or a catalog is not launch proof.

As observed in the current [Codex subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents), Codex can orchestrate spawning,
follow-up instructions, waiting, and closing; it documents inherited model and
reasoning defaults and direct steering/stopping controls. Use those controls
only when available in the current Codex surface. OpenCodex is an optional
inventory adapter, not a harness or dependency. Local-model hosts, Pi
extensions, and Claude Code have separate inventory and control surfaces. They
are unverified by this source until local evidence exists, and this skill makes
no model-backed execution claim for them. Their current documentation is
[Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [Pi subagent extension](https://github.com/earendil-works/pi/tree/main/packages/coding-agent/examples/extensions/subagent), and [Pi custom models](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md).

## Recovery and steering

If a worker hits a quota/provider/spawn failure, an unavailable model or
reasoning level, a route mismatch, or no worker surface:

1. record the safe failure detail, root, scope, and any partial evidence;
2. do not silently reroute, duplicate the writer, or broaden authority;
   on a visible substitution, stop the affected assignment before using any
   result and wait for the lead to accept the recorded route;
3. when the same nonterminal worker's route and boundaries remain valid, resume
   or steer it with the missing clarification and record that continuation;
4. otherwise, the lead chooses an explicitly supported replacement route,
   continues alone, or stops for an owner decision.

Steering changes instructions, not ownership: retain the original root,
authority, writer status, proof, and stop condition unless the lead records a
new assignment. A completed worker remains evidence for Review, not a source
of approval.
