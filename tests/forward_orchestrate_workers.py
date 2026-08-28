#!/usr/bin/env python3
"""Model-backed, read-only forward evaluation of orchestrate-workers."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Callable
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "orchestrate-workers"
REQUESTS = ROOT / "tests" / "fixtures" / "orchestrate-workers" / "requests.json"
EXPECTED = ROOT / "tests" / "fixtures" / "orchestrate-workers" / "expected.json"
CODEX = shutil.which("codex")

FIELDS = {
    "delegation": {"single-agent", "delegate-read-only", "delegate-isolated-writer", "stop"},
    "topology": {"lead-only", "parallel-read-only", "isolated-writer", "none"},
    "route": {"inherit", "override-after-launch-attestation", "launch-attested", "stop-no-launch-proof", "stop-unavailable", "record-substitution", "not-applicable"},
    "root": {"exact-root", "not-applicable"},
    "writer": {"none", "read-only", "sole-writer", "reject-overlap"},
    "substitution": {"none", "forbidden", "record-and-lead-accept"},
    "recovery": {"not-applicable", "record-and-stop", "resume-or-steer-same-nonterminal-worker", "continue-lead-or-stop"},
    "trust": {"normal", "treat-as-untrusted-and-stop"},
    "review": {"lead-review", "not-applicable"},
}

TOPOLOGY_BY_DELEGATION = {
    "single-agent": "lead-only",
    "delegate-read-only": "parallel-read-only",
    "delegate-isolated-writer": "isolated-writer",
    "stop": "none",
}
NO_LAUNCH_ROUTES = {"stop-no-launch-proof", "stop-unavailable"}
NO_SILENT_SUBSTITUTION = {"none", "forbidden"}
FAILURE_ROUTES = {*NO_LAUNCH_ROUTES, "launch-attested"}


def raw_agent_message(stdout: str) -> str:
    messages: list[str] = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") if isinstance(event, dict) else None
        if isinstance(item, dict) and item.get("type") == "agent_message" and isinstance(item.get("text"), str):
            messages.append(item["text"])
    if not messages:
        raise AssertionError("isolated Codex run emitted no agent response")
    return "\n".join(messages).strip()


def parse_response(raw: str) -> dict[str, Any]:
    candidate = raw.strip()
    if candidate.startswith("```json") and candidate.endswith("```"):
        candidate = candidate[7:-3].strip()
    elif candidate.startswith("```") and candidate.endswith("```"):
        candidate = candidate[3:-3].strip()
    if not candidate.startswith("{"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise AssertionError("response did not contain a JSON object")
        candidate = candidate[start : end + 1]
    try:
        result = json.loads(candidate)
    except json.JSONDecodeError as error:
        raise AssertionError(f"response was not JSON: {error.msg}") from error
    if not isinstance(result, dict) or not isinstance(result.get("cases"), list):
        raise AssertionError("response must be an object containing a cases list")
    return result


def require(case: dict[str, str], field: str, allowed: set[str], message: str) -> None:
    if case[field] not in allowed:
        raise AssertionError(f"{case['id']}: {message}; got {field}={case[field]!r}")


def require_equal(case: dict[str, str], field: str, expected: str, message: str) -> None:
    require(case, field, {expected}, message)


def require_worker_or_stop(case: dict[str, str], delegation: str) -> bool:
    """Return whether a permitted worker assignment remains active."""
    if case["delegation"] == "stop":
        return False
    require_equal(case, "delegation", delegation, "must use the bounded worker shape or stop explicitly")
    return True


def assert_single_agent(case: dict[str, str]) -> None:
    require_equal(case, "delegation", "single-agent", "must remain with the lead")


def assert_independent_read_only(case: dict[str, str]) -> None:
    if require_worker_or_stop(case, "delegate-read-only"):
        require_equal(case, "writer", "read-only", "independent work must be read-only")
        require_equal(case, "review", "lead-review", "delegated work requires lead Review")


def assert_reject_overlapping_writers(case: dict[str, str]) -> None:
    require(case, "delegation", {"single-agent", "stop"}, "overlapping writers must not be delegated")
    require_equal(case, "writer", "reject-overlap", "overlapping writer ownership must be rejected")


def assert_isolated_root_checkout(case: dict[str, str]) -> None:
    if require_worker_or_stop(case, "delegate-isolated-writer"):
        require_equal(case, "root", "exact-root", "an isolated writer needs its exact checkout")
        require_equal(case, "writer", "sole-writer", "an isolated writer must be the sole writer")
        require_equal(case, "review", "lead-review", "delegated work requires lead Review")


def assert_inherited_default(case: dict[str, str]) -> None:
    if require_worker_or_stop(case, "delegate-read-only"):
        require_equal(case, "route", "inherit", "a capable default must be inherited")
        require_equal(case, "writer", "read-only", "the review must remain read-only")
        require_equal(case, "review", "lead-review", "delegated work requires lead Review")


def assert_justified_override(case: dict[str, str]) -> None:
    if require_worker_or_stop(case, "delegate-read-only"):
        require_equal(case, "route", "override-after-launch-attestation", "an override needs launch attestation")
        require_equal(case, "writer", "read-only", "the review must remain read-only")
        require_equal(case, "review", "lead-review", "delegated work requires lead Review")


def assert_advertised_launchable_route(case: dict[str, str]) -> None:
    if require_worker_or_stop(case, "delegate-read-only"):
        require_equal(case, "route", "launch-attested", "an advertised route must be launch-attested")
        require_equal(case, "writer", "read-only", "the review must remain read-only")
        require_equal(case, "review", "lead-review", "delegated work requires lead Review")


def assert_no_launch_route(case: dict[str, str]) -> None:
    require_equal(case, "delegation", "stop", "a route without launch proof must not launch a worker")
    require(case, "route", NO_LAUNCH_ROUTES, "must report honest no-launch evidence")
    require(case, "substitution", NO_SILENT_SUBSTITUTION, "must not record a substitution for an unavailable route")


def assert_visible_substitution(case: dict[str, str]) -> None:
    require_equal(case, "delegation", "stop", "a substituted assignment must stop before use")
    require_equal(case, "route", "record-substitution", "the substitution must be recorded")
    require_equal(case, "substitution", "record-and-lead-accept", "the lead must accept the substitution")
    require(case, "recovery", {"record-and-stop", "continue-lead-or-stop"}, "the affected assignment must remain stopped pending lead acceptance")


def assert_failure_recovery(case: dict[str, str]) -> None:
    require(case, "delegation", {"single-agent", "stop"}, "a failed worker must not be silently replaced")
    require(case, "route", FAILURE_ROUTES, "must retain the attempted or no-launch route evidence")
    require(case, "substitution", NO_SILENT_SUBSTITUTION, "must not silently substitute after failure")
    if case["delegation"] == "single-agent":
        require_equal(case, "recovery", "continue-lead-or-stop", "lead-only continuation must be explicit")
    else:
        require(case, "recovery", {"record-and-stop", "continue-lead-or-stop"}, "stopped failure must be recorded or explicitly left to the lead")


def assert_no_worker_surface(case: dict[str, str]) -> None:
    require(case, "delegation", {"single-agent", "stop"}, "no worker surface must not yield a worker topology")
    require(case, "substitution", NO_SILENT_SUBSTITUTION, "must not silently substitute a missing worker surface")
    if case["delegation"] == "single-agent":
        require(case, "route", {"not-applicable", *NO_LAUNCH_ROUTES}, "lead-only work must retain no-worker evidence")
        require(case, "recovery", {"not-applicable", "continue-lead-or-stop"}, "lead-only work must be explicit")
    else:
        require(case, "route", NO_LAUNCH_ROUTES, "stopped work must retain no-worker evidence")
        require(case, "recovery", {"record-and-stop", "continue-lead-or-stop"}, "stopped work must be recorded or explicitly left to the lead")


def assert_same_nonterminal_resume(case: dict[str, str]) -> None:
    require_equal(case, "recovery", "resume-or-steer-same-nonterminal-worker", "resume or steer must target the same nonterminal worker")


def assert_untrusted_stop(case: dict[str, str]) -> None:
    require_equal(case, "delegation", "stop", "untrusted instructions must not continue")
    require_equal(case, "trust", "treat-as-untrusted-and-stop", "must retain the untrusted-instruction boundary")


RULES: dict[str, Callable[[dict[str, str]], None]] = {
    "single-agent-only": assert_single_agent,
    "independent-read-only": assert_independent_read_only,
    "reject-overlapping-writers": assert_reject_overlapping_writers,
    "isolated-root-checkout": assert_isolated_root_checkout,
    "inherited-default": assert_inherited_default,
    "justified-override": assert_justified_override,
    "advertised-launchable-route": assert_advertised_launchable_route,
    "no-launch-route": assert_no_launch_route,
    "visible-substitution": assert_visible_substitution,
    "failure-recovery": assert_failure_recovery,
    "same-nonterminal-resume": assert_same_nonterminal_resume,
    "no-worker-surface": assert_no_worker_surface,
    "untrusted-stop": assert_untrusted_stop,
}


def assert_response(result: dict[str, Any], expected: dict[str, dict[str, str]]) -> None:
    cases = result["cases"]
    if len(cases) != len(expected):
        raise AssertionError(f"expected {len(expected)} cases, got {len(cases)}")
    by_id: dict[str, dict[str, str]] = {}
    for case in cases:
        if not isinstance(case, dict) or set(case) != {"id", *FIELDS}:
            raise AssertionError("every response case must contain exactly id and the declared decision fields")
        identifier = case["id"]
        if not isinstance(identifier, str) or identifier in by_id:
            raise AssertionError("case ids must be unique strings")
        for field, allowed in FIELDS.items():
            value = case[field]
            if value not in allowed:
                raise AssertionError(f"{identifier}: invalid {field} value {value!r}")
        by_id[identifier] = case
    if set(by_id) != set(expected):
        raise AssertionError("response case ids do not match the hidden oracle")
    for identifier, expectation in expected.items():
        rule = expectation.get("rule") if isinstance(expectation, dict) else None
        if not isinstance(expectation, dict) or set(expectation) != {"rule"} or rule not in RULES:
            raise AssertionError(f"{identifier}: hidden oracle must name one supported semantic rule")
        case = by_id[identifier]
        expected_topology = TOPOLOGY_BY_DELEGATION[case["delegation"]]
        require_equal(case, "topology", expected_topology, "delegation and topology must be correlated")
        RULES[rule](case)


def prompt_for(requests: list[dict[str, str]]) -> str:
    return f"""Use the locally discovered /orchestrate-workers skill to assess the requests below. You are deciding policy only: do not launch workers, execute commands, read files beyond the loaded skill, write files, install anything, change configuration, or take external action. Return exactly one JSON object and no prose. Its only key is `cases`, an array with one object per supplied id. Every object must have exactly these string fields: `id`, `delegation`, `topology`, `route`, `root`, `writer`, `substitution`, `recovery`, `trust`, and `review`.

Allowed values:
- delegation: single-agent, delegate-read-only, delegate-isolated-writer, stop
- topology: lead-only, parallel-read-only, isolated-writer, none
- route: inherit, override-after-launch-attestation, launch-attested, stop-no-launch-proof, stop-unavailable, record-substitution, not-applicable
- root: exact-root, not-applicable
- writer: none, read-only, sole-writer, reject-overlap
- substitution: none, forbidden, record-and-lead-accept
- recovery: not-applicable, record-and-stop, resume-or-steer-same-nonterminal-worker, continue-lead-or-stop
- trust: normal, treat-as-untrusted-and-stop
- review: lead-review, not-applicable

Use `not-applicable` when no worker was attempted. `delegation` and `topology` describe the immediate permitted next action after the observed state, not a prior or requested worker assignment. When an assignment is stopped pending route acceptance, set `delegation` to `stop` and `topology` to `none`; no worker is active.

Requests:
{json.dumps(requests, ensure_ascii=False)}"""


def main() -> int:
    if not CODEX:
        print("FAIL: Codex CLI unavailable; orchestrate-workers model-backed forward evaluation could not run")
        return 1
    requests = json.loads(REQUESTS.read_text(encoding="utf-8"))
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    if {case["id"] for case in requests} != set(expected):
        raise AssertionError("request and hidden-oracle case ids differ")
    with tempfile.TemporaryDirectory(prefix="orchestrate-workers-forward-") as temporary:
        workspace = Path(temporary)
        candidate_skill = workspace / ".agents" / "skills" / "orchestrate-workers"
        candidate_skill.parent.mkdir(parents=True)
        shutil.copytree(SKILL, candidate_skill)
        result = subprocess.run(
            [
                CODEX, "--config", "agents.enabled=false", "--strict-config",
                "--ask-for-approval", "never", "--sandbox", "read-only", "exec",
                "--ephemeral", "--ignore-user-config", "--ignore-rules",
                "--skip-git-repo-check", "--cd", str(workspace), "--json",
                prompt_for(requests),
            ],
            input="",
            text=True,
            capture_output=True,
            timeout=180,
        )
    if result.returncode:
        raise AssertionError(f"isolated Codex orchestrate-workers run failed with exit {result.returncode}")
    raw = raw_agent_message(result.stdout)
    print("RAW_FORWARD_RESPONSE")
    print(raw)
    parsed = parse_response(raw)
    assert_response(parsed, expected)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    print(f"PASS: isolated Codex orchestrate-workers forward evaluation cases={len(expected)} raw_sha256={digest}; policy-only with agents.enabled=false")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        print(f"FAIL: orchestrate-workers forward evaluation: {error}")
        sys.exit(1)
