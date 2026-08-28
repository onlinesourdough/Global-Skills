from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTE_PATH = ROOT / "skills" / "route-models" / "scripts" / "route.py"
sys.dont_write_bytecode = True
SPEC = importlib.util.spec_from_file_location("route_models_helper", ROUTE_PATH)
assert SPEC and SPEC.loader
route = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(route)

FIXTURES = ROOT / "tests" / "fixtures" / "routing"
NOW = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def cached_roles() -> dict:
    return {
        "source": "fixture://cache",
        "validated": "2026-08-20T08:00:00Z",
        "expires": "2026-09-19T08:00:00Z",
        "roles": {
            "advisor": {"id": "fixture/fast", "name": "Fixture Fast", "context": 64000, "capabilities": ["text", "tools"], "cost": {"input": 1.0, "output": 1.0}},
            "default": {"id": "fixture/fast", "name": "Fixture Fast", "context": 64000, "capabilities": ["text", "tools"], "cost": {"input": 1.0, "output": 1.0}},
            "stronger": {"id": "fixture/strong", "name": "Fixture Strong", "context": 128000, "capabilities": ["text", "tools", "reasoning"], "cost": {"input": 3.0, "output": 5.0}},
        },
    }


class RoutingFixtureTests(unittest.TestCase):
    def test_current_metadata_selects_deterministic_default_and_roles(self) -> None:
        result = route.resolve_case({"metadata": load("current.json"), "available_models": ["fixture/fast", "fixture/strong"], "requested_role": "default"}, NOW)
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["role"], "default")
        self.assertEqual(result["selected"]["id"], "fixture/fast")
        self.assertFalse(result["decision_required"])
        self.assertIn("expires", result)

    def test_stale_metadata_is_visible_fallback(self) -> None:
        result = route.resolve_case({"metadata": load("stale.json"), "cache": cached_roles(), "available_models": ["fixture/fast", "fixture/strong"], "requested_role": "default"}, NOW)
        self.assertEqual(result["status"], "stale")
        self.assertEqual(result["fallback_used"], "validated-cache")
        self.assertTrue(result["stop_before_consequential_work"])
        self.assertTrue(result["limitations"])

    def test_missing_metadata_stops_with_native_default_fallback(self) -> None:
        result = route.resolve_case({"metadata": load("missing.json"), "requested_role": "default", "risk": "low"}, NOW)
        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["fallback_used"], "native-default-role")
        self.assertIsNone(result["selected"])
        self.assertTrue(result["decision_required"])

    def test_network_failure_uses_cache_with_warning(self) -> None:
        result = route.resolve_case({"fetch_error": "TimeoutError", "cache": cached_roles(), "available_models": ["fixture/fast", "fixture/strong"], "requested_role": "default"}, NOW)
        self.assertEqual(result["status"], "network-failed")
        self.assertEqual(result["fallback_used"], "validated-cache")
        self.assertEqual(result["selected"]["id"], "fixture/fast")
        self.assertTrue(result["stop_before_consequential_work"])

    def test_unavailable_selection_is_not_silent(self) -> None:
        result = route.resolve_case({"metadata": load("unavailable.json"), "available_models": ["fixture/text-only"], "requested_model": "fixture/vision", "risk": "high"}, NOW)
        self.assertEqual(result["status"], "selection-unavailable")
        self.assertIsNone(result["selected"])
        self.assertFalse(result["fallback_used"])
        self.assertTrue(result["decision_required"])

    def test_high_risk_requires_reasoning_capability(self) -> None:
        result = route.resolve_case({"metadata": load("current.json"), "available_models": ["fixture/fast", "fixture/strong"], "requested_role": "default", "risk": "high"}, NOW)
        self.assertEqual(result["status"], "current")
        self.assertEqual(result["selected"]["id"], "fixture/strong")

    def test_expired_live_metadata_without_cache_stops_without_selection(self) -> None:
        metadata = load("stale.json")
        metadata.pop("cache", None)
        result = route.resolve_case({"metadata": metadata, "available_models": ["fixture/cached"]}, NOW)
        self.assertEqual(result["status"], "missing")
        self.assertIsNone(result["selected"])
        self.assertIn("no valid cached", " ".join(result["limitations"]))

    def test_malformed_candidate_fields_are_not_usable(self) -> None:
        metadata = {
            "source": "fixture://models.dev/malformed",
            "observed": "2026-08-24T08:00:00Z",
            "expires": "2026-09-23T08:00:00Z",
            "fixture/bad-date": {
                "id": "fixture/bad-date",
                "name": "Bad date fixture",
                "limit": {"context": 32000},
                "modalities": {"input": ["text"], "output": ["text"]},
                "cost": {"input": 1.0, "output": 1.0},
                "last_updated": "not-a-date",
            },
            "fixture/partial-cost": {
                "id": "fixture/partial-cost",
                "name": "Partial cost fixture",
                "limit": {"context": 32000},
                "modalities": {"input": ["text"], "output": ["text"]},
                "cost": {"input": 1.0},
                "last_updated": "2026-08-20",
            },
        }
        result = route.resolve_case({"metadata": metadata, "available_models": ["fixture/bad-date", "fixture/partial-cost"]}, NOW)
        self.assertEqual(result["status"], "selection-unavailable")
        self.assertIsNone(result["selected"])
        self.assertTrue(result["decision_required"])

    def test_missing_inventory_cannot_emit_a_selection(self) -> None:
        result = route.resolve_case({"metadata": load("current.json"), "requested_role": "default"}, NOW)
        self.assertEqual(result["status"], "selection-unavailable")
        self.assertIsNone(result["selected"])
        self.assertTrue(result["decision_required"])

    def test_empty_inventory_cannot_emit_a_selection(self) -> None:
        result = route.resolve_case({"metadata": load("current.json"), "available_models": [], "requested_role": "default"}, NOW)
        self.assertEqual(result["status"], "selection-unavailable")
        self.assertIsNone(result["selected"])

    def test_missing_cost_evidence_cannot_emit_a_selection(self) -> None:
        metadata = load("current.json")
        for key, value in list(metadata.items()):
            if isinstance(value, dict) and "cost" in value:
                value.pop("cost")
        result = route.resolve_case({"metadata": metadata, "available_models": ["fixture/fast", "fixture/strong"]}, NOW)
        self.assertEqual(result["status"], "selection-unavailable")
        self.assertIsNone(result["selected"])
        self.assertIn("cost comparison is unknown", " ".join(result["limitations"]))

    def test_durable_skill_has_no_transient_model_selection(self) -> None:
        text = (ROOT / "skills" / "route-models" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("fixture/", text)
        self.assertNotIn("gpt-", text.lower())
        self.assertNotIn("claude-", text.lower())
        self.assertIn("models.dev/models.json", text)


if __name__ == "__main__":
    unittest.main()
