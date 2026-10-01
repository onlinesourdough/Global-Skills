# Online Sourdough Skills — archive

**Archived on 1 October 2026.** This repository preserves the former standalone
Global Skills shelf. It is no longer maintained or recommended as a separate
plugin installation.

[AIOS](https://github.com/onlinesourdough/AIOS-Plugin) is the maintained source
for shared Online Sourdough skills. From
[AIOS 0.16.0](https://github.com/onlinesourdough/AIOS-Plugin/releases/tag/v0.16.0),
Clarify is an independently selectable explanation skill with concrete examples
and visuals when they help. Its former mandatory HTML output has been adapted.

## Preserved methods

| Method | Status |
| --- | --- |
| [Clarify](skills/clarify/SKILL.md) | Historical version; maintained continuation lives in AIOS |
| [Shape Offer](skills/shape-offer/SKILL.md) | Preserved here; not adopted into AIOS |
| [Setup Guardrails](skills/setup-guardrails/SKILL.md) | Preserved code and coverage notes; not adopted into AIOS |

The `0.4.0` package remains an unreleased candidate. Archiving does not create a
release or resolve the historical publication/privacy prerequisites recorded in
[the source audit](docs/source-audit.md) and [release metadata](release.json).
The pinned candidate installation instructions are retired.

Removing the old plugin does not remove guardrail hooks previously installed
in individual projects. Their scoped recovery procedure is retained in
[coverage and recovery](skills/setup-guardrails/coverage-and-recovery.md).

Source history, licences and attribution remain available. See
[the changelog](CHANGELOG.md) and [MIT licence](LICENSE).
