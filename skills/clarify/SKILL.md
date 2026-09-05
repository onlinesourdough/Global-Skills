---
name: clarify
description: Resolve material uncertainty in a request or decision into a bounded Spec before dependent work proceeds.
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
- For a clarification-only request, stop at the Spec; do not infer permission
  to implement or take external action.
- Within an already-authorized implementation request, return the resolved
  Spec to the caller and continue the authorized work under the caller's
  lifecycle. Clarification does not require a second implementation approval.
  Ask only for missing authority or unresolved material decisions; existing
  authorization does not expand scope or permit additional external actions.

## Choose a bounded mode

Use **small mode** for one local decision with a short dependency chain. Ask
one frontier round with no more than three material questions. Resolve facts
first and state a recommendation in the Spec.

Use **complex mode** for a branched decision, several owners, or a meaningful
reversibility/risk boundary. Build a dependency tree and work in frontier
rounds: ask all currently answerable owner decisions together, then recompute
the frontier after the answers. Use at most three rounds or ten material
questions by default. If the cap is reached, return the partial Spec with
unresolved decisions explicitly marked; do not continue interviewing forever.

If the owner does not answer, stop and report what is blocked. Do not infer an
owner decision from silence.

## Resolve and record

Use available context to identify the smallest missing decision affecting the
outcome, audience, constraints, or expected proof. Preserve conflicting and
unknown evidence. Ask a question only when its prerequisites are settled;
group independent decisions and remove settled questions after each answer.

Keep the Spec proportional to the decision. Include selected decisions,
facts and citations, assumptions, non-goals, acceptance checks, relevant risks,
dependencies, rollback or stop conditions, and unresolved decisions. Label it
`decision-ready` only when all material owner decisions are answered;
otherwise use `needs-owner-decision` and stop dependent work.

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

## Handoff

Return the Spec, decision status, evidence/sources, and next action within the
existing authority. For clarification-only work, state that implementation has
not started. For a larger authorized task, the caller's lifecycle owns
continued execution and any remaining gates.
