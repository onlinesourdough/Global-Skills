# Decision-ready Spec

Status: decision-ready
Mode: complex

## Round 1 frontier

Decision: Who owns the portable capability?

Choices: one project | several projects

Recommendation: several projects only when the same behavior and proof recur.

Consequence: A shared owner requires versioning and rollback; a local owner
keeps the change smaller.

Evidence: The sanitized release-planning fixture assigns global ownership only
to cross-project skills. Candidate decision record observed 2026-08-24.

## Round 2 frontier

Decision: Which output is needed?

Choices: text Spec | optional visual HTML

Recommendation: text Spec by default; add one visual artifact only for a named
audience that benefits from it.

Consequence: Text is cheaper to review; HTML adds accessibility and fact-check
proof but no implementation dependency.

Evidence: The visual output is optional and must be self-contained. Sanitized
candidate decision record observed 2026-08-24.

## Round 3 frontier

Decision: What is the implementation gate?

Choices: start now | wait for explicit authorization

Recommendation: wait for explicit authorization.

Consequence: Waiting preserves owner control; starting would violate the
clarification boundary.

Evidence: Clarification ends at a decision-ready Spec. Sanitized candidate
decision record observed 2026-08-24.

Implementation status: not started; wait for owner authorization.
