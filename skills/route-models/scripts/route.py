#!/usr/bin/env python3
"""Deterministic, keyless model-role routing helper.

The skill owns the policy; this dependency-free helper makes metadata states
and explicit fallback behavior testable without credentials or provider IDs in
durable policy.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

ROLE_NAMES = ("advisor", "default", "stronger")
FRESHNESS_DAYS = 30


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def iso_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(float(value)) and value >= 0 else None


def capability_set(record: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    raw = record.get("capabilities")
    if isinstance(raw, str):
        if raw.strip():
            values.add(raw.strip().lower())
    elif isinstance(raw, list):
        values.update(item.strip().lower() for item in raw if isinstance(item, str) and item.strip())
    modalities = record.get("modalities")
    if isinstance(modalities, dict):
        for value in modalities.values():
            if isinstance(value, str):
                if value.strip():
                    values.add(value.strip().lower())
            elif isinstance(value, list):
                values.update(item.strip().lower() for item in value if isinstance(item, str) and item.strip())
    elif isinstance(modalities, list):
        values.update(item.strip().lower() for item in modalities if isinstance(item, str) and item.strip())
    if record.get("tool_call") is True:
        values.add("tools")
    if record.get("reasoning") is True:
        values.add("reasoning")
    return values


def context_limit(record: dict[str, Any]) -> int:
    value = record.get("context")
    if isinstance(record.get("limit"), dict):
        value = record["limit"].get("context")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return 0
    return int(value) if float(value).is_integer() else 0


def cost_total(record: dict[str, Any]) -> float | None:
    cost = record.get("cost")
    if not isinstance(cost, dict):
        return None
    input_cost = number(cost.get("input"))
    output_cost = number(cost.get("output"))
    if input_cost is None or output_cost is None:
        return None
    return input_cost + output_cost


def normalize(key: str, value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    model_id = value.get("id") or key
    name = value.get("name")
    context = context_limit(value)
    if (
        not isinstance(model_id, str)
        or not model_id.strip()
        or not isinstance(name, str)
        or not name.strip()
        or context <= 0
    ):
        return None
    capabilities = capability_set(value)
    if not capabilities:
        return None
    last_updated = value.get("last_updated")
    if last_updated is not None and parse_time(last_updated) is None:
        return None
    quality = number(value.get("quality")) or 0
    return {
        "id": model_id.strip(),
        "name": name.strip(),
        "context": context,
        "capabilities": sorted(capabilities),
        "cost_total": cost_total(value),
        "last_updated": last_updated,
        "quality": quality,
    }


def records(payload: Any, observed: datetime | None = None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw = payload.get("models") if isinstance(payload.get("models"), dict) else payload
    result: list[dict[str, Any]] = []
    for key, value in raw.items():
        if key in {"source", "source_url", "observed", "observed_at", "generated", "validated", "expires", "limitations", "scenario", "available_models", "harness_inventory"}:
            continue
        item = normalize(str(key), value)
        if item and (item["last_updated"] is not None or observed is not None):
            result.append(item)
    return result


def envelope(payload: Any, now: datetime, source_default: str = "fixture://metadata") -> tuple[list[dict[str, Any]], str, datetime, datetime, list[str]]:
    if not isinstance(payload, dict):
        return [], source_default, now, now, ["metadata is not an object"]
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else payload
    observed = parse_time(payload.get("observed") or payload.get("observed_at") or payload.get("generated"))
    observed = observed or parse_time(metadata.get("observed") or metadata.get("observed_at") or metadata.get("generated"))
    observed_for_validation = observed
    observed = observed or now
    expires = parse_time(payload.get("expires")) or parse_time(metadata.get("expires")) or observed + timedelta(days=FRESHNESS_DAYS)
    source = payload.get("source") or payload.get("source_url") or metadata.get("source") or metadata.get("source_url") or source_default
    limitations = payload.get("limitations") if isinstance(payload.get("limitations"), list) else metadata.get("limitations")
    limitations = limitations if isinstance(limitations, list) else []
    return records(metadata, observed_for_validation), str(source), observed, expires, [str(item) for item in limitations]


def eligible(record: dict[str, Any], requirements: dict[str, Any]) -> bool:
    minimum = requirements.get("min_context", 0)
    if isinstance(minimum, (int, float)) and record["context"] < minimum:
        return False
    required = requirements.get("capabilities", [])
    if isinstance(required, str):
        required = [required]
    if not isinstance(required, list):
        return False
    return all(str(item).lower() in set(record["capabilities"]) for item in required)


def risk_requirements(requirements: dict[str, Any], risk: str) -> dict[str, Any]:
    """Add a visible minimum for high-risk work; never silently downgrade."""
    result = dict(requirements)
    required = result.get("capabilities", [])
    if isinstance(required, str):
        required = [required]
    if not isinstance(required, list):
        required = []
    required = [str(item) for item in required]
    if risk == "high" and not any(item.lower() == "reasoning" for item in required):
        required.append("reasoning")
    result["capabilities"] = required
    return result


def role_map(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not candidates:
        return {}
    cheapest = sorted(
        candidates,
        key=lambda item: (item["cost_total"] is None, item["cost_total"] if item["cost_total"] is not None else math.inf, item["id"]),
    )[0]
    strongest = max(
        candidates,
        key=lambda item: ("reasoning" in item["capabilities"], item["context"], item["quality"], item["id"]),
    )
    return {"advisor": cheapest, "default": cheapest, "stronger": strongest}


def public(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if record is None:
        return None
    return {key: record[key] for key in ("id", "name", "context", "capabilities", "cost_total", "last_updated")}


def cached_roles(cache: Any, now: datetime) -> tuple[dict[str, dict[str, Any]], str, datetime, datetime, list[str]]:
    if not isinstance(cache, dict) or not isinstance(cache.get("roles"), dict):
        return {}, "fixture://cache", now, now, ["cache is missing"]
    observed = parse_time(cache.get("validated") or cache.get("observed"))
    if observed is None:
        return {}, str(cache.get("source") or "fixture://cache"), now, now, ["cache validation date is missing or invalid"]
    result: dict[str, dict[str, Any]] = {}
    for role in ROLE_NAMES:
        value = cache["roles"].get(role)
        item = normalize(str(value.get("id", role)), value) if isinstance(value, dict) else None
        if item:
            result[role] = item
    expires = parse_time(cache.get("expires")) or observed + timedelta(days=FRESHNESS_DAYS)
    source = str(cache.get("source") or "fixture://cache")
    limitations = cache.get("limitations") if isinstance(cache.get("limitations"), list) else []
    return result, source, observed, expires, [str(item) for item in limitations]


def availability(case: dict[str, Any]) -> tuple[set[str] | None, str, str | None]:
    """Return the caller's explicit harness/model inventory.

    ``None`` means that the caller supplied no inventory at all.  An empty set
    is meaningful: the caller supplied an inventory and no model is available.
    The route helper never treats metadata presence as proof that the current
    harness can launch a model.
    """
    source = "available_models"
    raw: Any
    if "available_models" in case:
        raw = case.get("available_models")
    elif "harness_inventory" in case:
        source = "harness_inventory"
        raw = case.get("harness_inventory")
        if isinstance(raw, dict):
            raw = raw.get("available_models", raw.get("models"))
    else:
        return None, "missing", "caller did not supply an available-model set or harness inventory"
    if not isinstance(raw, list):
        return set(), source, "available-model inventory must be a list"
    result: set[str] = set()
    for item in raw:
        if isinstance(item, str) and item.strip():
            result.add(item.strip())
        elif isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
            if item.get("available", True) is not False:
                result.add(item["id"].strip())
    return result, source, None


def output(
    status: str,
    role: str,
    selected: dict[str, Any] | None,
    source: str,
    observed: datetime,
    expires: datetime,
    limitations: list[str],
    fallback: str | bool,
    decision_required: bool,
    reason: str,
    available: set[str] | None = None,
    availability_source: str = "missing",
) -> dict[str, Any]:
    return {
        "status": status,
        "role": role,
        "selected": public(selected),
        "source": source,
        "observed": iso_time(observed) if observed else "",
        "expires": iso_time(expires) if expires else "",
        "limitations": limitations,
        "confidence": "high" if status == "current" and not any("unknown" in item for item in limitations) else "limited",
        "fallback_used": fallback,
        "decision_required": decision_required,
        "owner_confirmation_required": decision_required,
        "invalidation_signals": limitations,
        "stop_before_consequential_work": decision_required or status != "current",
        "availability": {
            "supplied": available is not None,
            "source": availability_source,
            "models": sorted(available) if available is not None else [],
        },
        "reason": reason,
    }


def missing(
    role: str,
    risk: str,
    reason: str,
    now: datetime,
    limitations: list[str] | None = None,
    available: set[str] | None = None,
    availability_source: str = "missing",
    source: str = "none",
    observed: datetime | None = None,
    expires: datetime | None = None,
) -> dict[str, Any]:
    return output(
        "missing",
        role,
        None,
        source,
        observed or now,
        expires or now,
        limitations or ["no valid live or cached metadata"],
        "native-default-role" if risk == "low" else False,
        True,
        reason,
        available,
        availability_source,
    )


def unavailable(
    role: str,
    source: str,
    observed: datetime,
    expires: datetime,
    limitations: list[str],
    reason: str,
    available: set[str] | None,
    availability_source: str,
) -> dict[str, Any]:
    return output(
        "selection-unavailable",
        role,
        None,
        source,
        observed,
        expires,
        limitations,
        False,
        True,
        reason,
        available,
        availability_source,
    )


def resolve_case(case: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    role = case.get("requested_role") if case.get("requested_role") in ROLE_NAMES else "default"
    risk = case.get("risk") if case.get("risk") in {"low", "high"} else "low"
    requirements = case.get("requirements") if isinstance(case.get("requirements"), dict) else {}
    requirements = dict(requirements)
    requirements.setdefault("capabilities", ["text"])
    requirements = risk_requirements(requirements, risk)
    available, availability_source, availability_error = availability(case)
    cached, cache_source, cache_observed, cache_expires, cache_limits = cached_roles(case.get("cache"), now)
    if case.get("fetch_error") or case.get("network_state") == "network-failed":
        cache_is_current = bool(cached) and cache_expires > now
        if role in cached and cache_is_current and eligible(cached[role], requirements) and cached[role]["cost_total"] is not None:
            if available is None:
                return unavailable(role, cache_source, cache_observed, cache_expires, cache_limits + ["live metadata fetch failed", availability_error or "availability inventory is missing"], "No cached selection may be emitted until the caller supplies the current harness/model inventory.", available, availability_source)
            if cached[role]["id"] not in available:
                return unavailable(role, cache_source, cache_observed, cache_expires, cache_limits + ["live metadata fetch failed", "cached role is not available in the supplied harness inventory"], "The cached role cannot be launched by the supplied harness inventory.", available, availability_source)
            return output("network-failed", role, cached[role], cache_source, cache_observed, cache_expires, cache_limits + ["live metadata fetch failed"], "validated-cache", risk != "low", "The live source failed; cached evidence is visible and not current evidence.", available, availability_source)
        offline_limits = ["live metadata fetch failed"]
        if not cached:
            offline_limits.append("no valid cached role is available")
        elif cache_expires <= now:
            offline_limits.append("cached role map is expired")
        else:
            offline_limits.append("cached role does not satisfy the requested capability or cost evidence")
        return missing(role, risk, "The live source failed and no valid cached selection is available.", now, offline_limits, available, availability_source, cache_source if cached else "none", cache_observed if cached else None, cache_expires if cached else None)

    payload = case
    live, source, observed, expires, limitations = envelope(payload, now)
    if not live:
        return missing(role, risk, "No valid metadata records are available.", now, limitations + ["no valid metadata records are available"], available, availability_source, source, observed, expires)
    if expires <= now:
        if available is None:
            return unavailable(role, source, observed, expires, limitations + ["live metadata is expired", availability_error or "availability inventory is missing"], "The stale route cannot be emitted until the caller supplies the current harness/model inventory.", available, availability_source)
        if not cached or cache_expires <= now:
            stale_limits = limitations + ["live metadata is expired", "no valid cached role map is available"]
            if cached and cache_expires <= now:
                stale_limits.append("cached role map is also expired")
            return missing(role, risk, "Live metadata is expired and no valid cached role is available.", now, stale_limits, available, availability_source, source, observed, expires)
        stale_selection = cached.get(role)
        if stale_selection is None or not eligible(stale_selection, requirements) or stale_selection["cost_total"] is None:
            return unavailable(role, cache_source, cache_observed, cache_expires, cache_limits + ["live metadata is expired", "cached role does not satisfy the requested capability or cost evidence"], "The stale cached role cannot satisfy the requested route.", available, availability_source)
        if stale_selection["id"] not in available:
            return unavailable(role, cache_source, cache_observed, cache_expires, cache_limits + ["live metadata is expired", "stale role is not available in the supplied harness inventory"], "The stale role cannot be launched by the supplied harness inventory.", available, availability_source)
        return output("stale", role, stale_selection, cache_source, cache_observed, cache_expires, cache_limits + ["live metadata is expired"], "validated-cache", True, "The live metadata is expired; cached evidence is visible and not current.", available, availability_source)
    if available is None:
        return unavailable(role, source, observed, expires, limitations + [availability_error or "availability inventory is missing"], "Fresh metadata is not enough to prove that the current harness can launch a model; supply an explicit available-model set.", available, availability_source)
    eligible_live = [item for item in live if eligible(item, requirements)]
    eligible_live = [item for item in eligible_live if item["id"] in available]
    if not eligible_live:
        return unavailable(role, source, observed, expires, limitations + ["no metadata candidate satisfies both the requested capability and supplied harness availability"], "No verified model satisfies the requested capability and current harness inventory.", available, availability_source)
    priced = [item for item in eligible_live if item["cost_total"] is not None]
    if eligible_live and not priced:
        return unavailable(role, source, observed, expires, limitations + ["input/output cost metadata is absent; cost comparison is unknown"], "No route is emitted because cost evidence is insufficient for stable cost/risk ranking.", available, availability_source)
    elif len(priced) < len(eligible_live):
        limitations = limitations + ["unpriced capability candidates were excluded from cost-aware ranking"]
    assignments = role_map(priced or eligible_live)
    requested_model = case.get("requested_model")
    if requested_model and not any(item["id"] == requested_model for item in priced):
        return unavailable(role, source, observed, expires, limitations + ["requested selection is unavailable in the supplied harness/cost/capability evidence"], "No verified selection satisfies the requested model; obtain an owner decision before consequential work.", available, availability_source)
    selected = assignments.get(role)
    if selected is None:
        return unavailable(role, source, observed, expires, limitations + ["requested role has no eligible record"], "The requested role has no eligible validated record.", available, availability_source)
    return output("current", role, selected, source, observed, expires, limitations, False, False, "Live metadata is valid, fresh, capability-eligible, cost-ranked, and available to the supplied harness.", available, availability_source)


def route_document(
    document: dict[str, Any],
    *,
    now: datetime,
    role: str = "default",
    need: set[str] | None = None,
    min_context: int = 0,
    network_state: str = "current",
    cached: dict[str, Any] | None = None,
    available_models: set[str] | None = None,
    source_url: str = "https://models.dev/models.json",
) -> dict[str, Any]:
    """Compatibility-shaped result for local fixture and harness adapters.

    The durable skill uses ``resolve_case``. This adapter keeps the result
    readable to existing local tests without adding a second policy or source.
    """
    if available_models is None:
        return {"state": "selection-unavailable", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": {"url": source_url, "observed_at": iso_time(now), "expires": iso_time(now)}, "limitations": ["caller did not supply an available-model set or harness inventory"]}

    if network_state == "network-failed":
        selection = cached.get("selection") if isinstance(cached, dict) else None
        if selection is None:
            return {"state": "missing", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": {"url": source_url, "observed_at": iso_time(now), "expires": iso_time(now)}, "limitations": ["live metadata fetch failed and no cache is available"]}
        if selection.get("id") not in available_models:
            return {"state": "unavailable-selection", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": {"url": source_url, "observed_at": iso_time(now), "expires": iso_time(now)}, "limitations": ["cached selection is unavailable in the supplied harness inventory"]}
        return {"state": "network-failed", "status": "fallback", "role": role, "selection": selection, "fallback": "cached-role", "owner_confirmation_required": True, "decision_required": True, "source": {"url": source_url, "observed_at": iso_time(now), "expires": iso_time(now)}, "limitations": ["live metadata fetch failed", "using cached role assignment"]}

    if not isinstance(document, dict) or not document:
        return {"state": "missing", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": {"url": source_url, "observed_at": iso_time(now), "expires": iso_time(now)}, "limitations": ["metadata is missing or invalid"]}

    metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else document
    observed = parse_time(document.get("observed_at") or document.get("observed")) or now
    source = str(document.get("source_url") or source_url)
    expires = parse_time(document.get("expires")) or observed + timedelta(days=FRESHNESS_DAYS)
    requirements = {"capabilities": sorted(need or {"text"}), "min_context": min_context}
    assignments = role_map([item for item in records(metadata, observed) if eligible(item, requirements) and item["id"] in available_models and item["cost_total"] is not None])
    source_info = {"url": source, "observed_at": iso_time(observed), "expires": iso_time(expires)}
    if not assignments:
        return {"state": "unavailable-selection", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": source_info, "limitations": ["no validated candidate satisfies the requested capability"]}
    selected = assignments.get(role)
    if expires <= now:
        cached_selection = cached.get("selection") if isinstance(cached, dict) else None
        if not isinstance(cached_selection, dict):
            return {"state": "missing", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": source_info, "limitations": ["metadata expiry has passed", "no validated cached role is available"]}
        if cached_selection.get("id") not in available_models:
            return {"state": "unavailable-selection", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": source_info, "limitations": ["metadata expiry has passed", "cached role is unavailable in the supplied harness inventory"]}
        return {"state": "stale", "status": "fallback", "role": role, "selection": cached_selection, "fallback": "cached-role", "owner_confirmation_required": True, "decision_required": True, "source": source_info, "limitations": ["metadata expiry has passed; using the validated cached role"]}
    if selected is None:
        return {"state": "unavailable-selection", "status": "needs-decision", "role": role, "selection": None, "fallback": "native-default", "owner_confirmation_required": True, "decision_required": True, "source": source_info, "limitations": ["requested role is unavailable"]}
    return {"state": "current", "status": "current", "role": role, "selection": public(selected), "fallback": None, "owner_confirmation_required": False, "decision_required": False, "source": source_info, "limitations": []}


def fetch(url: str) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "onlinesourdough-skills-route/0.1"})
    with urlopen(request, timeout=15) as response:  # nosec B310: URL is an explicit metadata source.
        return json.load(response)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://models.dev/models.json")
    parser.add_argument("--metadata-file")
    parser.add_argument("--cache-file")
    parser.add_argument("--requested-role", choices=ROLE_NAMES, default="default")
    parser.add_argument("--requested-model")
    parser.add_argument("--risk", choices=("low", "high"), default="low")
    parser.add_argument("--available-model", action="append", dest="available_models")
    parser.add_argument("--harness-inventory-file")
    parser.add_argument("--now")
    args = parser.parse_args(argv)
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)
    assert now is not None
    case: dict[str, Any] = {"requested_role": args.requested_role, "requested_model": args.requested_model, "risk": args.risk}
    if args.available_models is not None:
        case["available_models"] = args.available_models
    if args.harness_inventory_file:
        try:
            case["harness_inventory"] = json.loads(Path(args.harness_inventory_file).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            case["harness_inventory"] = []
    try:
        case["metadata"] = json.loads(Path(args.metadata_file).read_text(encoding="utf-8")) if args.metadata_file else fetch(args.url)
        if isinstance(case["metadata"], dict):
            case["metadata"] = dict(case["metadata"])
            case["metadata"].setdefault("source", args.url)
            case["metadata"].setdefault("observed", iso_time(now))
            case["metadata"].setdefault("expires", iso_time(now + timedelta(days=FRESHNESS_DAYS)))
    except (OSError, ValueError, URLError, TimeoutError) as error:
        case["fetch_error"] = type(error).__name__
    if args.cache_file:
        try:
            case["cache"] = json.loads(Path(args.cache_file).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            case["cache"] = None
    result = resolve_case(case, now)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "current" else 2 if result["decision_required"] else 0


if __name__ == "__main__":
    sys.exit(main())
