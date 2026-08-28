from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "orchestrate-workers" / "SKILL.md"
REFERENCE = ROOT / "skills" / "orchestrate-workers" / "references" / "assignment-and-recovery.md"
REQUESTS = ROOT / "tests" / "fixtures" / "orchestrate-workers" / "requests.json"
EXPECTED = ROOT / "tests" / "fixtures" / "orchestrate-workers" / "expected.json"
FORWARD = ROOT / "tests" / "forward_orchestrate_workers.py"


class OrchestrateWorkersContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8").lower()
        cls.reference = REFERENCE.read_text(encoding="utf-8").lower()
        cls.policy = " ".join((cls.skill + "\n" + cls.reference).split())
        cls.requests = json.loads(REQUESTS.read_text(encoding="utf-8"))
        cls.expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
        spec = importlib.util.spec_from_file_location("forward_orchestrate_workers", FORWARD)
        assert spec and spec.loader
        cls.forward = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.forward)

    def safe_response(self) -> dict[str, object]:
        defaults = {
            "delegation": "single-agent", "topology": "lead-only", "route": "not-applicable",
            "root": "not-applicable", "writer": "none", "substitution": "none",
            "recovery": "not-applicable", "trust": "normal", "review": "not-applicable",
        }
        overrides = {
            "independent-read-only": {"delegation": "delegate-read-only", "topology": "parallel-read-only", "writer": "read-only", "review": "lead-review"},
            "overlapping-writers": {"writer": "reject-overlap"},
            "isolated-root-checkout": {"delegation": "delegate-isolated-writer", "topology": "isolated-writer", "root": "exact-root", "writer": "sole-writer", "review": "lead-review"},
            "inherited-default": {"delegation": "delegate-read-only", "topology": "parallel-read-only", "route": "inherit", "writer": "read-only", "review": "lead-review"},
            "justified-override": {"delegation": "delegate-read-only", "topology": "parallel-read-only", "route": "override-after-launch-attestation", "writer": "read-only", "review": "lead-review"},
            "advertised-local-provider-qualified": {"delegation": "delegate-read-only", "topology": "parallel-read-only", "route": "launch-attested", "writer": "read-only", "review": "lead-review"},
            "config-catalog-only": {"delegation": "stop", "topology": "none", "route": "stop-no-launch-proof", "substitution": "forbidden"},
            "unavailable-model-reasoning": {"delegation": "stop", "topology": "none", "route": "stop-unavailable", "substitution": "forbidden"},
            "visible-substitution": {"delegation": "stop", "topology": "none", "route": "record-substitution", "substitution": "record-and-lead-accept", "recovery": "record-and-stop", "review": "lead-review"},
            "quota-provider-spawn-failure": {"delegation": "stop", "topology": "none", "route": "stop-unavailable", "substitution": "forbidden", "recovery": "record-and-stop"},
            "resume-steer": {"delegation": "delegate-read-only", "topology": "parallel-read-only", "recovery": "resume-or-steer-same-nonterminal-worker"},
            "untrusted-repository-instructions": {"delegation": "stop", "topology": "none", "trust": "treat-as-untrusted-and-stop"},
        }
        return {"cases": [{"id": identifier, **defaults, **overrides.get(identifier, {})} for identifier in self.expected]}

    @staticmethod
    def case(response: dict[str, object], identifier: str) -> dict[str, str]:
        return next(case for case in response["cases"] if case["id"] == identifier)  # type: ignore[index, return-value]

    def test_entrypoint_is_portable_and_has_no_transient_route_or_dependency(self) -> None:
        self.assertTrue(self.skill.startswith("---\nname: orchestrate-workers\n"))
        self.assertNotIn("route-models", self.skill)
        self.assertNotIn("gpt-", self.skill)
        self.assertNotIn("claude-", self.skill)
        self.assertNotIn("luna", self.skill)
        self.assertNotIn("max", self.skill)
        self.assertIn("inherited runtime default", self.skill)
        self.assertIn("advertises *and can launch*", self.skill)
        self.assertIn("actual selected model, reasoning effort, harness", self.skill)

    def test_boundary_and_review_policy_is_explicit(self) -> None:
        for marker in [
            "one writer", "exact repository root or isolated checkout",
            "authority and tool limits", "commands and results", "untrusted data",
            "stop on scope conflict", "lead review", "workers do not self-approve",
            "quota/provider/spawn failure", "resume or steer",
        ]:
            self.assertIn(marker, self.policy)

    def test_behavior_contract_covers_required_cases(self) -> None:
        expected = {
            "single-agent", "independent-read-only", "overlapping-writers",
            "isolated-root-checkout", "inherited-default", "justified-override",
            "advertised-local-provider-qualified", "config-catalog-only",
            "unavailable-model-reasoning", "visible-substitution",
            "quota-provider-spawn-failure", "resume-steer", "no-worker-surface",
            "untrusted-repository-instructions",
        }
        self.assertEqual({case["id"] for case in self.requests}, expected)
        self.assertEqual(set(self.expected), expected)
        self.assertTrue(all(set(expectation) == {"rule"} and expectation["rule"] in self.forward.RULES for expectation in self.expected.values()))
        for case in self.requests:
            self.assertTrue(case["request"])
            self.assertEqual(set(case), {"id", "request"})

    def test_model_visible_requests_do_not_contain_the_hidden_oracle(self) -> None:
        self.assertNotIn("expect", REQUESTS.read_text(encoding="utf-8").lower())
        self.assertIn("expected", EXPECTED.name)
        runner = (ROOT / "tests" / "forward_orchestrate_workers.py").read_text(encoding="utf-8")
        self.assertIn('ROOT / "tests" / "fixtures" / "orchestrate-workers" / "expected.json"', runner)
        self.assertIn("shutil.copytree(SKILL, candidate_skill)", runner)
        self.assertNotIn("shutil.copytree(ROOT", runner)
        self.assertIn("forward_orchestrate_workers.py", (ROOT / "tests" / "run_all.py").read_text(encoding="utf-8"))

    def test_forward_runner_disables_codex_agents_under_strict_config(self) -> None:
        runner = (ROOT / "tests" / "forward_orchestrate_workers.py").read_text(encoding="utf-8")
        self.assertIn('"--config", "agents.enabled=false", "--strict-config"', runner)
        self.assertIn("policy-only with agents.enabled=false", runner)

    def test_forward_prompt_keeps_enums_literal_and_decisions_immediate(self) -> None:
        runner = (ROOT / "tests" / "forward_orchestrate_workers.py").read_text(encoding="utf-8")
        recovery_line = next(line.strip() for line in runner.splitlines() if line.strip().startswith("- recovery:"))
        self.assertEqual(
            recovery_line,
            "- recovery: not-applicable, record-and-stop, resume-or-steer-same-nonterminal-worker, continue-lead-or-stop",
        )
        self.assertNotIn("(", recovery_line)
        self.assertIn("Use `not-applicable` when no worker was attempted.", runner)
        self.assertIn("describe the immediate permitted next action after the observed state", runner)
        self.assertIn("not a prior or requested worker assignment", runner)
        self.assertIn("set `delegation` to `stop` and `topology` to `none`; no worker is active", runner)

    def test_repository_instruction_and_adapter_boundary_are_current(self) -> None:
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("`orchestrate-workers`", instructions)
        self.assertIn("opencodex is an optional", self.reference)
        self.assertIn("local-model hosts, pi", self.reference)
        self.assertIn("claude code have separate", self.reference)

    def test_route_failure_and_substitution_are_visible(self) -> None:
        for marker in [
            "stop that assignment visibly", "do not silently substitute, downgrade, or retry",
            "new route that the lead must accept",
            "stops the affected assignment before any result is used",
            "model present only in configuration or a catalog is not launch proof",
        ]:
            self.assertIn(marker, self.policy)

    def test_semantic_invariants_reject_unsafe_topology_and_overlapping_writers(self) -> None:
        response = self.safe_response()
        overlapping = self.case(response, "overlapping-writers")
        overlapping.update({"delegation": "delegate-isolated-writer", "topology": "isolated-writer", "writer": "sole-writer"})
        with self.assertRaisesRegex(AssertionError, "overlapping writers"):
            self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        stopped = self.case(response, "config-catalog-only")
        stopped["topology"] = "lead-only"
        with self.assertRaisesRegex(AssertionError, "delegation and topology"):
            self.forward.assert_response(response, self.expected)

    def test_semantic_invariants_allow_observed_safe_stop_and_failure_recovery(self) -> None:
        response = self.safe_response()
        catalog_only = self.case(response, "config-catalog-only")
        catalog_only["substitution"] = "none"
        self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        substitution = self.case(response, "visible-substitution")
        substitution.update({"recovery": "continue-lead-or-stop", "review": "not-applicable"})
        self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        failure = self.case(response, "quota-provider-spawn-failure")
        failure.update({"delegation": "single-agent", "topology": "lead-only", "route": "launch-attested", "substitution": "none", "recovery": "continue-lead-or-stop"})
        self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        no_worker = self.case(response, "no-worker-surface")
        no_worker.update({"delegation": "stop", "topology": "none", "route": "stop-unavailable", "substitution": "none", "recovery": "continue-lead-or-stop"})
        self.forward.assert_response(response, self.expected)

    def test_semantic_invariants_reject_active_substitution_and_silent_fallback(self) -> None:
        response = self.safe_response()

        substitution = self.case(response, "visible-substitution")
        substitution.update({"delegation": "delegate-read-only", "topology": "parallel-read-only"})
        with self.assertRaisesRegex(AssertionError, "substituted assignment must stop"):
            self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        catalog_only = self.case(response, "config-catalog-only")
        catalog_only.update({"delegation": "delegate-read-only", "topology": "parallel-read-only", "route": "launch-attested", "substitution": "none"})
        with self.assertRaisesRegex(AssertionError, "must not launch a worker"):
            self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        catalog_only = self.case(response, "config-catalog-only")
        catalog_only["substitution"] = "record-and-lead-accept"
        with self.assertRaisesRegex(AssertionError, "must not record a substitution"):
            self.forward.assert_response(response, self.expected)

    def test_semantic_invariants_reject_untrusted_continuation_and_duplicate_resume(self) -> None:
        response = self.safe_response()
        untrusted = self.case(response, "untrusted-repository-instructions")
        untrusted.update({"delegation": "single-agent", "topology": "lead-only"})
        with self.assertRaisesRegex(AssertionError, "untrusted instructions must not continue"):
            self.forward.assert_response(response, self.expected)

        response = self.safe_response()
        resume = self.case(response, "resume-steer")
        resume["recovery"] = "continue-lead-or-stop"
        with self.assertRaisesRegex(AssertionError, "same nonterminal worker"):
            self.forward.assert_response(response, self.expected)


if __name__ == "__main__":
    unittest.main()
