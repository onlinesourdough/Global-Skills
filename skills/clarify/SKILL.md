---
name: clarify
description: Turn an uncertain request, plan, or decision into a bounded, decision-ready Spec. Use when material owner choices, branching requirements, or fact-finding must be resolved before implementation; optionally produce one accessible self-contained visual HTML explanation for a named audience.
---

# Clarify

Turn uncertainty into a shared, decision-ready Spec. Use this skill before
implementation when a wrong assumption would materially change the result.
Do not use it to delay a clear, low-risk request.

## Keep the boundary

- Research verifiable facts yourself with available files, tools, and primary
  sources. Cite each material fact with its source and observation date.
- Separate facts, assumptions, recommendations, and owner decisions.
- Ask the owner only for decisions that cannot be established from evidence.
- Give a recommended option and the consequence of each material choice.
- Never begin implementation, create the requested deliverable, or take an
  external side effect automatically. Stop at the Spec and wait for explicit
  authorization to build.

## Choose a bounded mode

Use **small mode** for one local decision with a short dependency chain. Ask
one frontier round with no more than three material questions. Resolve facts
first, state a recommendation, and stop with the Spec.

Use **complex mode** for a branched decision, several owners, or a meaningful
reversibility/risk boundary. Build a dependency tree and work in frontier
rounds: ask all currently answerable owner decisions together, then recompute
the frontier after the answers. Use at most three rounds or ten material
questions by default. If the cap is reached, return the partial Spec with
unresolved decisions explicitly marked; do not continue interviewing forever.

If the owner does not answer, stop and report what is blocked. Do not infer an
owner decision from silence.

## Procedure

1. Restate the desired outcome, audience, authority, constraints, non-goals,
   reversibility, and expected proof. Identify the smallest missing decision.
2. Inventory available local context and research the facts that affect the
   decision. Prefer primary, current sources; record conflicting or unknown
   evidence instead of smoothing it over.
3. Map the decision tree. A question belongs in the current frontier only when
   its prerequisites are settled. Group independent questions in one round.
4. For each material owner decision, present:

   ```text
   Decision: <short title>
   Choices: A ... | B ... [| C ...]
   Recommendation: <choice and why>
   Consequence: <what changes if each choice is selected>
   Evidence: <facts and citations>
   ```

5. After each answer, update the tree and remove settled questions. Do not ask
   for facts the tools can verify, and do not ask preference questions that do
   not change the result.
6. End with a Spec containing the outcome, selected decisions, facts and
   citations, assumptions, non-goals, acceptance/evidence checks, risks,
   dependencies, rollback or stop conditions, and any unresolved decisions.
   Label the Spec `decision-ready` only when all material owner decisions are
   answered; otherwise label it `needs-owner-decision` and stop.

## Optional visual explanation

Create this mode only when the user asks for a visual explanation or names a
specific audience that benefits from one. It is an output companion, not a
requirement for ordinary clarification.

Produce exactly one self-contained `.html` artifact with:

- a language attribute, title, semantic headings, `main`, readable focus
  states, sufficient contrast, and visible text alternatives;
- large inline SVG/CSS or other local visuals with meaningful labels and
  adjacent explanatory text; no remote assets, scripts, fonts, or network
  dependencies;
- few words per visual, a concise summary, and a clearly labelled text fallback
  that remains useful if visuals do not render;
- a sources/fact-check section listing checked claims, URLs, observation dates,
  and unresolved uncertainty.

Keep the artifact about the named audience and the clarified decision. Do not
turn it into an implementation, dashboard, or multi-file website. If the
visual artifact cannot be produced safely, return the text Spec and explain
the limitation.

## Stop output

Return the Spec, the decision status, the evidence/sources, the recommended
next action, and the explicit implementation gate: **no implementation has
started; wait for owner authorization**.
