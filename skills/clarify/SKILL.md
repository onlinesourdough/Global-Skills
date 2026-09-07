---
name: clarify
description: Explain a topic or decision for a named audience in one accessible self-contained visual HTML artifact.
---

# Clarify

Turn a topic, process, or decision into one concise visual explanation for a
named audience. This is an ordinary, discoverable explainer skill: use it when
an explanation would help a reader understand what changes, why it matters, or
what to do next. It is not a mandatory interview or implementation workflow,
and it does not create a second approval gate.

## Understand before drawing

- Identify the audience, their likely context, and the one question the
  explanation should answer.
- Separate checked facts, supplied facts, assumptions, recommendations, and
  unresolved uncertainty. Research material or time-sensitive claims with
  available primary sources when research is needed, and record the source,
  URL, and observation date.
- Keep the scope to one topic and one useful takeaway. Do not invent evidence,
  audience needs, outcomes, or decisions.
- If the audience or topic is materially missing, make the smallest reasonable
  assumption and label it; ask one concise question only when proceeding would
  change the explanation materially.

## Produce one artifact

Return exactly one self-contained `.html` artifact. The artifact must work
offline and contain all CSS and visuals inline. Do not use remote assets,
scripts, fonts, embeds, network calls, tracking, or generated companion files.

Include:

- `<!doctype html>`, `<html lang="...">`, a useful `<title>`, semantic
  headings, `<main>`, and sections with readable focus states;
- sufficient color contrast, visible labels, and meaningful `aria-*`
  attributes for interactive or visual elements;
- one large inline SVG or equivalent local visual with a title/description and
  adjacent explanatory text. Use visible equivalents for information conveyed
  by color, position, icons, or arrows;
- few words per visual, a concise summary, and a clearly labelled text-only
  fallback in the audience's language that remains useful when visuals do not
  render; and
- a sources/fact-check section in the audience's language listing checked
  claims, URLs, observation dates, supplied facts, and unresolved uncertainty.
  If no external research was needed, say so explicitly.

Prefer one clear visual relationship—flow, comparison, timeline, hierarchy,
or before/after—over decoration. Keep the explanation readable on a small
screen and usable with keyboard navigation. At narrow widths, reflow or
simplify the visual, shorten labels, or pair it with adjacent text so labels
remain readable; do not squeeze a desktop diagram into a tiny viewport. Test a
representative narrow rendering rather than relying on a fixed pixel rule.
Respect reduced-motion preferences and do not add animation, transition, or
other effects that distract from the explanation.

## Handoff

Return the artifact and a short note naming the audience, takeaway, sources,
and any assumption or uncertainty. If the artifact cannot be produced safely,
return a concise text explanation with the limitation; do not fabricate facts
or create additional files. When the caller asks for an HTML explanation in a
local workspace, that ordinary request authorizes the normal local artifact;
use a path within the intended workspace, avoid overwriting unrelated files,
and do not require separate approval of an exact filename. Publishing or other
external actions remain separate authority.
