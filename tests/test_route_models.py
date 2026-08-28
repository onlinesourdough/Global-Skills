#!/usr/bin/env python3
"""Exercise every deterministic route metadata state in isolated fixtures."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_PATH = ROOT / "skills/route-models/scripts/route.py"
SPEC = importlib.util.spec_from_file_location("route_policy", ROUTE_PATH)
assert SPEC and SPEC.loader
ROUTE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ROUTE)
FIXTURES = ROOT / "tests/fixtures/routing"
NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def run(name: str) -> dict:
    case = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return ROUTE.resolve_case(case, NOW)


def main() -> int:
    live_schema = run("live-schema")
    assert live_schema["status"] == "current"
    assert live_schema["selected"]["id"] == "fixture/live"

    current = run("current")
    assert current["status"] == "current"
    assert current["selected"]["id"] == "fixture/fast"
    assert current["fallback_used"] is False
    assert current["stop_before_consequential_work"] is False
    for role in ("advisor", "default", "stronger"):
        case = json.loads((FIXTURES / "current.json").read_text(encoding="utf-8"))
        case["requested_role"] = role
        role_result = ROUTE.resolve_case(case, NOW)
        assert role_result["status"] == "current"
        assert role_result["selected"]["id"]

    missing = run("missing")
    assert missing["status"] == "missing"
    assert missing["fallback_used"] == "native-default-role"
    assert missing["decision_required"] is True

    stale = run("stale")
    assert stale["status"] == "stale"
    assert stale["fallback_used"] == "validated-cache"
    assert "expired" in " ".join(stale["limitations"])

    offline = run("network-failed")
    assert offline["status"] == "network-failed"
    assert offline["fallback_used"] == "validated-cache"
    assert "failed" in " ".join(offline["limitations"])

    unavailable = run("unavailable-selection")
    assert unavailable["status"] == "selection-unavailable"
    assert unavailable["selected"] is None
    assert unavailable["fallback_used"] is False
    assert "requested model" in unavailable["reason"]

    empty = run("empty-allowlist")
    assert empty["status"] == "selection-unavailable"
    assert empty["selected"] is None
    assert empty["availability"]["supplied"] is True

    no_inventory = ROUTE.resolve_case({"metadata": json.loads((FIXTURES / "current.json").read_text(encoding="utf-8"))}, NOW)
    assert no_inventory["status"] == "selection-unavailable"
    assert no_inventory["selected"] is None
    assert no_inventory["decision_required"] is True

    skill = (ROOT / "skills/route-models/SKILL.md").read_text(encoding="utf-8").lower()
    for phrase in ("models.dev/models.json", "advisor", "default", "stronger", "stale", "network-failed", "missing", "unavailable-selection", "available-model", "never hardcode"):
        assert phrase in skill, phrase
    assert not any(token in skill for token in ("gpt-", "claude-", "gemini-"))
    print("PASS: route current, missing, stale, network-failed, and unavailable-selection fixtures")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, KeyError) as error:
        print(f"FAIL: route fixture test: {error}")
        sys.exit(1)
