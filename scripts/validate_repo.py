#!/usr/bin/env python3
"""Validate the canonical Skills public-release candidate without network."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {
    "clarify",
    "manage-skills",
    "orchestrate-workers",
    "shape-offer",
}
RETIRED_SKILL = "route-models"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RELEASE_VERSION = "0.2.0"
RELEASE_TAG = f"v{RELEASE_VERSION}"
PREVIOUS_TAG = "v0.1.0"
BASELINE_REF = "refs/heads/codex/issue-33-cross-harness-portability"
MAIN_REF = "refs/heads/main"
OFFICIAL_CLI_PACKAGE = "skills@1.5.23"
OFFICIAL_CLI_REPOSITORY = "https://github.com/vercel-labs/skills"
OFFICIAL_CLI_COMMIT = "435076e78988e1e6ec40d00b0b1d76bdbbc5419a"
OFFICIAL_CLI_INTEGRITY = "sha512-+hMNBSi35yfX0sKD+ZcRm9y5or7u313OdkcvrRvJAsAzGCaA8wRTu2OmVdN0KRbk9ybqKby5dijkn6OVvNTUmw=="
BLOCKED_PRIVATE_INVENTORY_SHA256 = "5e73f79777725cea98698c251aab59ad5d812fde7f48a92f2b4337142585d659"
BLOCKED_PRIVATE_REPOSITORY_SHA256 = "23294037b9237da1e5d368f71d73c91061c2adc5bd2978a278f147406eb65682"
CODEX_MARKETPLACE_ADD = "codex plugin marketplace add onlinesourdough/Skills --ref v0.2.0"
CODEX_LIST = "codex plugin list --available --json"
CODEX_INSTALL = "codex plugin add onlinesourdough-skills@onlinesourdough-skills"
SKILLS_DISCOVER = "npx skills@1.5.23 add onlinesourdough/Skills#v0.2.0 --list"
SKILLS_INSTALL = (
    "npx skills@1.5.23 add onlinesourdough/Skills#v0.2.0 "
    "--skill clarify manage-skills orchestrate-workers shape-offer "
    "--agent claude-code cursor -y"
)
SKILLS_LIST = "npx skills@1.5.23 list --agent claude-code cursor"


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - diagnostic path
        fail(errors, f"{path.relative_to(ROOT)}: invalid JSON ({exc})")
        return {}
    if not isinstance(value, dict):
        fail(errors, f"{path.relative_to(ROOT)}: root must be an object")
        return {}
    return value


def frontmatter(path: Path, errors: list[str]) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(errors, f"{path.relative_to(ROOT)}: frontmatter must start with ---")
        return {}, text
    marker = text.find("\n---\n", 4)
    if marker < 0:
        fail(errors, f"{path.relative_to(ROOT)}: frontmatter closing marker missing")
        return {}, text
    values: dict[str, str] = {}
    for line in text[4:marker].splitlines():
        if not line.strip():
            continue
        if ":" not in line or line[:1].isspace():
            fail(errors, f"{path.relative_to(ROOT)}: invalid frontmatter line")
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values, text[marker + 5 :]


def validate_skill(path: Path, errors: list[str]) -> None:
    slug = path.parent.name
    if not SLUG.fullmatch(slug):
        fail(errors, f"{path.relative_to(ROOT)}: invalid skill slug")
    values, body = frontmatter(path, errors)
    if set(values) != {"name", "description"}:
        fail(errors, f"{path.relative_to(ROOT)}: frontmatter keys must be exactly name and description")
    if values.get("name") != slug:
        fail(errors, f"{path.relative_to(ROOT)}: frontmatter name does not match directory")
    if not values.get("description") or not body.strip():
        fail(errors, f"{path.relative_to(ROOT)}: description and body are required")
    if len(path.read_text(encoding="utf-8").splitlines()) > 500:
        fail(errors, f"{path.relative_to(ROOT)}: exceeds 500 lines")
    if "[TODO" in path.read_text(encoding="utf-8"):
        fail(errors, f"{path.relative_to(ROOT)}: TODO placeholder remains")
    for child in path.parent.iterdir():
        if child.name in {"README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}:
            fail(errors, f"{child.relative_to(ROOT)}: auxiliary skill documentation is not allowed")
        if child.name == "agents":
            fail(errors, f"{child.relative_to(ROOT)}: harness-specific UI payload is not portable source")
        if child.is_symlink():
            fail(errors, f"{child.relative_to(ROOT)}: canonical payload must not contain symlinks")
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
        target = link.split("#", 1)[0]
        if not target or target.startswith(("http://", "https://", "mailto:")):
            continue
        if not (path.parent / target).exists():
            fail(errors, f"{path.relative_to(ROOT)}: referenced resource does not exist: {target}")
    for resource in path.parent.rglob("*"):
        if "__pycache__" in resource.parts or resource.suffix == ".pyc":
            continue
        if resource.is_file() and resource.name != "SKILL.md" and resource.name not in body:
            fail(errors, f"{resource.relative_to(ROOT)}: resource is not referenced by its SKILL.md")


def validate_structure(errors: list[str]) -> None:
    required = {
        "AGENTS.md",
        "README.md",
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "SUPPORT.md",
        "LICENSE",
        ".gitignore",
        ".codex-plugin/plugin.json",
        ".agents/plugins/marketplace.json",
        "release.json",
        "docs/source-audit.md",
    }
    for relative in sorted(required):
        if not (ROOT / relative).is_file():
            fail(errors, f"missing required file: {relative}")

    skills_root = ROOT / "skills"
    actual = {path.name for path in skills_root.iterdir() if path.is_dir()} if skills_root.is_dir() else set()
    if actual != EXPECTED_SKILLS:
        fail(errors, f"skills/: expected {sorted(EXPECTED_SKILLS)}, found {sorted(actual)}")

    retired_paths = {
        ROOT / "skills" / RETIRED_SKILL,
        ROOT / "tests" / "fixtures" / "routing",
        ROOT / "tests" / "test_route_models.py",
        ROOT / "tests" / "test_routing.py",
    }
    for retired in sorted(retired_paths):
        if retired.exists():
            fail(errors, f"retired router surface remains: {retired.relative_to(ROOT)}")

    retired_literal_allowlist = {
        Path("CHANGELOG.md"),
        Path("scripts/validate_repo.py"),
        Path("tests/test_orchestrate_workers.py"),
        Path("tests/test_portability_contract.py"),
    }
    for candidate in ROOT.rglob("*"):
        if not candidate.is_file() or ".git" in candidate.parts:
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        relative = candidate.relative_to(ROOT)
        if RETIRED_SKILL in text and relative not in retired_literal_allowlist:
            fail(errors, f"active retired-router reference remains: {relative}")

    for slug in sorted(actual):
        skill_file = skills_root / slug / "SKILL.md"
        if not skill_file.is_file():
            fail(errors, f"missing canonical source: {skill_file.relative_to(ROOT)}")
        else:
            validate_skill(skill_file, errors)

    duplicate_payloads = [
        path for path in ROOT.rglob("SKILL.md")
        if ".git" not in path.parts and path.parent.parent != skills_root
    ]
    for path in duplicate_payloads:
        fail(errors, f"duplicate payload outside skills/: {path.relative_to(ROOT)}")
    for forbidden in [".claude", ".cursor", ".agents/skills", ".mcp.json", "hooks", "apps", "__pycache__"]:
        if (ROOT / forbidden).exists():
            fail(errors, f"harness/generated surface must not be packaged: {forbidden}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            fail(errors, f"generated Python artifact is packaged: {path.relative_to(ROOT)}")
        if path.stat().st_size > 1_000_000:
            fail(errors, f"release-tree file exceeds 1 MB: {path.relative_to(ROOT)}")

    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8") if (ROOT / ".gitignore").is_file() else ""
    for marker in ("__pycache__/", "*.py[cod]", "skills-lock.json"):
        if marker not in ignore:
            fail(errors, f".gitignore: missing generated-file rule {marker}")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8") if (ROOT / "LICENSE").is_file() else ""
    if not license_text.startswith("MIT License\n") or "onlinesourdough contributors" not in license_text:
        fail(errors, "LICENSE: expected complete MIT license and project copyright")


def validate_json_files(errors: list[str]) -> None:
    manifest_path = ROOT / ".codex-plugin" / "plugin.json"
    marketplace_path = ROOT / ".agents" / "plugins" / "marketplace.json"
    release_path = ROOT / "release.json"
    manifest = load_json(manifest_path, errors)
    marketplace = load_json(marketplace_path, errors)
    release = load_json(release_path, errors)

    expected_manifest_keys = {
        "name", "version", "description", "author", "homepage", "repository",
        "license", "skills", "interface",
    }
    if set(manifest) != expected_manifest_keys:
        fail(errors, ".codex-plugin/plugin.json: unsupported or missing wrapper metadata")
    if manifest.get("name") != "onlinesourdough-skills" or manifest.get("version") != RELEASE_VERSION:
        fail(errors, ".codex-plugin/plugin.json: name/version mismatch")
    if manifest.get("skills") != "./skills/" or manifest.get("license") != "MIT":
        fail(errors, ".codex-plugin/plugin.json: skills/license mismatch")
    if manifest.get("repository") != "https://github.com/onlinesourdough/Skills":
        fail(errors, ".codex-plugin/plugin.json: canonical repository is missing")
    if not isinstance(manifest.get("author"), dict) or not manifest["author"].get("name"):
        fail(errors, ".codex-plugin/plugin.json: author.name is required")
    interface = manifest.get("interface")
    if not isinstance(interface, dict) or not interface.get("displayName") or not interface.get("defaultPrompt"):
        fail(errors, ".codex-plugin/plugin.json: interface metadata is required")
    if isinstance(interface, dict) and set(interface.get("capabilities", [])) != {
        "Clarification", "Skill management", "Worker orchestration", "Offer shaping"
    }:
        fail(errors, ".codex-plugin/plugin.json: capability inventory must match all four skills")
    if {"apps", "hooks", "mcpServers", "mcp", "schedules"}.intersection(manifest):
        fail(errors, ".codex-plugin/plugin.json: unsupported surface added")

    if set(marketplace) != {"name", "interface", "plugins"}:
        fail(errors, ".agents/plugins/marketplace.json: root metadata mismatch")
    if marketplace.get("name") != "onlinesourdough-skills":
        fail(errors, ".agents/plugins/marketplace.json: unexpected marketplace name")
    if not isinstance(marketplace.get("interface"), dict) or marketplace["interface"].get("displayName") != "onlinesourdough Skills":
        fail(errors, ".agents/plugins/marketplace.json: interface.displayName mismatch")
    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        fail(errors, ".agents/plugins/marketplace.json: exactly one plugin entry is required")
    else:
        entry = plugins[0]
        if set(entry) != {"name", "source", "policy", "category"}:
            fail(errors, ".agents/plugins/marketplace.json: plugin entry shape mismatch")
        expected_source = {
            "source": "url",
            "url": "https://github.com/onlinesourdough/Skills",
            "ref": RELEASE_TAG,
        }
        if entry.get("name") != manifest.get("name") or entry.get("source") != expected_source:
            fail(errors, f".agents/plugins/marketplace.json: source must plan immutable {RELEASE_TAG}")
        if entry.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
            fail(errors, ".agents/plugins/marketplace.json: authentication policy must remain ON_INSTALL")
        if entry.get("category") != "Productivity":
            fail(errors, ".agents/plugins/marketplace.json: category mismatch")

    expected_release_keys = {
        "schema_version", "name", "version", "status", "release_date", "released",
        "source_of_truth", "license", "included_skills", "source_boundary",
        "atlas", "history_visibility", "marketplace", "distribution",
        "historical_release", "release_notes", "build_evidence", "ship_gate",
    }
    if set(release) != expected_release_keys:
        fail(errors, "release.json: release contract keys mismatch")
    if release.get("schema_version") != 3 or release.get("name") != manifest.get("name"):
        fail(errors, "release.json: schema/name mismatch")
    if release.get("version") != RELEASE_VERSION or release.get("version") != manifest.get("version"):
        fail(errors, "release.json: version mismatch")
    if release.get("status") != "candidate" or release.get("released") is not False or release.get("release_date") is not None:
        fail(errors, "release.json: Build must remain an undated, unreleased candidate")
    if release.get("source_of_truth") != "skills/<slug>/SKILL.md" or release.get("license") != "MIT":
        fail(errors, "release.json: source/license mismatch")
    if release.get("included_skills") != sorted(EXPECTED_SKILLS):
        fail(errors, "release.json: included_skills must be exactly the four current skills")
    if release.get("source_boundary") != {
        "reviewed_candidate": "issue #9 lead-reviewed four-skill tree",
        "history_strategy": "one publish-safe parentless clean-root baseline followed by ordinary reviewed linear commits on main",
        "candidate_state": "committed private pre-publication candidate",
    }:
        fail(errors, "release.json: clean-root baseline/linear-history boundary mismatch")

    expected_atlas = {
        "canonical_repository": "https://github.com/onlinesourdough/Skills",
        "endpoint_continuity": "The existing onlinesourdough/Skills repository remains canonical; publication does not rename, archive, replace, or duplicate it.",
        "candidate_boundary": "The repository remains private and Build does not claim that the live Atlas integration works; both public access and Atlas behavior require post-Ship verification.",
        "public_static_mode": {
            "source": "bounded anonymous GitHub API reads",
            "default_repository": "onlinesourdough/Skills",
            "display": "observed revision and access state",
            "write_policy": "read-only",
        },
        "authenticated_self_hosted_mode": {
            "proposal_limit": "exactly one validated skill edit",
            "delivery": "new branch and pull request",
            "default_branch_write": False,
        },
    }
    if release.get("atlas") != expected_atlas:
        fail(errors, "release.json: Skills Atlas source/access/write boundary mismatch")

    expected_history_visibility = {
        "status": "PRIVATE_SUPPORT_PURGE_PENDING",
        "visibility_change_legal": False,
        "ordinary_refs": "refs/heads/codex/issue-33-cross-harness-portability retains the verified clean-root baseline; refs/heads/main descends linearly from it through ordinary reviewed commits",
        "historical_release": "v0.1.0 release and tag are withheld/deleted and must not be recreated",
        "github_managed_residue": "refs/pull/2/head and refs/pull/3/head plus unreachable old objects and cached diffs/views remain blocked pending GitHub Support purge confirmation",
        "canonical_endpoint_action": "Keep the existing onlinesourdough/Skills repository private and in place; do not rename, archive, replace, duplicate, or move it.",
        "support_gate": "No visibility change, v0.2.0 tag, or GitHub release is legal until GitHub Support confirms purge and the private-state re-audit passes.",
        "decision_record": "docs/source-audit.md#authorized-in-place-sanitization-and-publication-gate",
    }
    if release.get("history_visibility") != expected_history_visibility:
        fail(errors, "release.json: blocked current-history remediation contract mismatch")

    release_marketplace = release.get("marketplace")
    if not isinstance(release_marketplace, dict):
        fail(errors, "release.json: marketplace contract missing")
        release_marketplace = {}
    expected_source = {"source": "url", "url": "https://github.com/onlinesourdough/Skills", "ref": RELEASE_TAG}
    if release_marketplace.get("path") != ".agents/plugins/marketplace.json" or release_marketplace.get("source") != expected_source:
        fail(errors, "release.json: marketplace path/source mismatch")
    if release_marketplace.get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        fail(errors, "release.json: marketplace policy mismatch")
    if release_marketplace.get("source_ref_kind") != "planned-immutable-tag" or release_marketplace.get("release_tag") != RELEASE_TAG:
        fail(errors, "release.json: planned immutable tag contract missing")
    if release_marketplace.get("tag_exists_at_build") is not False:
        fail(errors, "release.json: candidate must not claim that v0.2.0 exists")
    if not release_marketplace.get("recovery") or "GitHub Support confirms purge" not in release_marketplace.get("ship_requirement", ""):
        fail(errors, "release.json: Ship/recovery boundary missing")

    distribution = release.get("distribution")
    if not isinstance(distribution, dict):
        fail(errors, "release.json: distribution contract missing")
        distribution = {}
    codex = distribution.get("codex") if isinstance(distribution.get("codex"), dict) else {}
    if codex.get("marketplace_add") != CODEX_MARKETPLACE_ADD or codex.get("list") != CODEX_LIST or codex.get("install") != CODEX_INSTALL:
        fail(errors, "release.json: Codex public install commands mismatch")
    if "local Git commit/ref fixture only" not in codex.get("candidate_proof", ""):
        fail(errors, "release.json: Codex candidate proof boundary missing")
    cli = distribution.get("skills_cli") if isinstance(distribution.get("skills_cli"), dict) else {}
    expected_cli = {
        "package": OFFICIAL_CLI_PACKAGE,
        "repository": OFFICIAL_CLI_REPOSITORY,
        "source_commit": OFFICIAL_CLI_COMMIT,
        "license": "MIT",
        "npm_integrity": OFFICIAL_CLI_INTEGRITY,
        "discover": SKILLS_DISCOVER,
        "install": SKILLS_INSTALL,
        "list": SKILLS_LIST,
        "candidate_proof": "disposable project and local clean-commit fixture with telemetry disabled; no global or consumer-repository write",
    }
    if cli != expected_cli:
        fail(errors, "release.json: Skills CLI pin/commands/candidate proof mismatch")
    boundary = distribution.get("model_execution_boundary", "")
    if "does not claim model-backed behavior" not in boundary or "Claude Code" not in boundary or "Cursor Agent" not in boundary:
        fail(errors, "release.json: model-execution limitation missing")

    historical = release.get("historical_release")
    if historical != {
        "version": "0.1.0",
        "public_continuity": "WITHHELD",
        "tag_exists_after_private_sanitization": False,
        "release_exists_after_private_sanitization": False,
        "recreate": False,
        "first_public_release": "v0.2.0",
    }:
        fail(errors, "release.json: withheld v0.1.0 contract mismatch")
    evidence = release.get("build_evidence")
    if not isinstance(evidence, dict) or evidence.get("required_checks") != [
        "python3 scripts/validate_repo.py",
        "python3 scripts/secret_scan.py",
        "python3 tests/run_all.py",
    ] or evidence.get("candidate_only") is not True:
        fail(errors, "release.json: required Build evidence mismatch")
    ship_gate = release.get("ship_gate")
    if not isinstance(ship_gate, list):
        fail(errors, "release.json: Ship gate must be a list")
    else:
        joined_gate = "\n".join(ship_gate)
        for marker in [
            "owner authorized the exact r3 in-place sanitization",
            "retained candidate branch resolves to the independently verified clean-root baseline and main descends linearly from it",
            "v0.1.0 GitHub release and local/remote tag are absent",
            "Skills issue metadata #1, #4, #5, #6, #7, and #8",
            "GitHub Support confirms purge of refs/pull/2/head, refs/pull/3/head",
            "private-state re-audit reports zero blocked findings",
            "remains private and the only canonical endpoint",
            "later exact Ship authority",
        ]:
            if marker not in joined_gate:
                fail(errors, f"release.json: Ship gate is missing blocked-history marker {marker}")


def git_output(*arguments: str) -> str | None:
    result = subprocess.run(["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def validate_git_candidate(errors: list[str]) -> None:
    previous = git_output("rev-parse", "--verify", f"refs/tags/{PREVIOUS_TAG}^{{commit}}")
    if previous is not None:
        fail(errors, f"Git: withheld historical tag {PREVIOUS_TAG} must be absent")
    current_tag = git_output("rev-parse", "--verify", f"refs/tags/{RELEASE_TAG}^{{commit}}")
    if current_tag is not None:
        fail(errors, f"Git: candidate contract must not claim absent tag while {RELEASE_TAG} exists")
    head = git_output("rev-parse", "HEAD")
    main = git_output("rev-parse", MAIN_REF)
    baseline = git_output("rev-parse", BASELINE_REF)
    if not head or not main or not baseline:
        fail(errors, "Git: HEAD, main, and the retained clean-root baseline branch must all resolve")
        return
    if head != main:
        fail(errors, "Git: HEAD must equal main for candidate validation")

    baseline_record = git_output("rev-list", "--parents", "-n", "1", baseline)
    if not baseline_record or baseline_record.split() != [baseline]:
        fail(errors, "Git: retained candidate branch must point to a parentless clean-root baseline")

    roots = git_output("rev-list", "--max-parents=0", MAIN_REF, BASELINE_REF)
    if roots is None or roots.splitlines() != [baseline]:
        fail(errors, "Git: main and the retained candidate branch must share exactly one clean-root baseline")

    if git_output("merge-base", "--is-ancestor", baseline, main) is None:
        fail(errors, "Git: main must descend from the retained clean-root baseline")

    divergence = git_output("rev-list", "--left-right", "--count", f"{baseline}...{main}")
    try:
        baseline_only, _main_only = (int(value) for value in (divergence or "").split())
    except ValueError:
        fail(errors, "Git: baseline/main divergence could not be determined")
    else:
        if baseline_only != 0:
            fail(errors, "Git: retained baseline branch must not diverge from main")

    lineage = git_output("rev-list", "--parents", f"{baseline}..{main}")
    if lineage is None:
        fail(errors, "Git: baseline-to-main lineage could not be read")
    elif any(len(record.split()) != 2 for record in lineage.splitlines()):
        fail(errors, "Git: main may advance from the baseline only through ordinary single-parent commits")


def validate_public_docs(errors: list[str]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs" / "source-audit.md").read_text(encoding="utf-8")
    combined = "\n".join((readme, changelog, audit, (ROOT / "release.json").read_text(encoding="utf-8")))
    normalized_readme = " ".join(readme.split())
    normalized_combined = " ".join(combined.split())
    for slug in sorted(EXPECTED_SKILLS):
        if f"skills/{slug}/SKILL.md" not in readme:
            fail(errors, f"README.md: missing skill index entry {slug}")
    for marker in [
        "canonical payload", "Codex plugin", "Skills CLI", "pinned release",
        "Update and rollback", "Relation to Skills Atlas", "Source and scope",
        "v0.2.0", "does not claim that the tag already exists", CODEX_MARKETPLACE_ADD,
        CODEX_INSTALL, SKILLS_DISCOVER, SKILLS_INSTALL, "ON_INSTALL", "MIT License",
        "bounded anonymous GitHub API reads", "observed revision and access state",
        "remain read-only", "exactly one validated skill edit", "new branch",
        "open a pull request", "never writes the default branch",
        "does not claim that the Skills repository is public",
        "live Atlas integration works",
    ]:
        if marker.lower() not in normalized_readme.lower():
            fail(errors, f"README.md: missing public release topic/command {marker}")
    for stale in [
        "private immutable release source",
        "three actual skills",
        "not part of immutable v0.1.0",
        "current release; the tag is unchanged",
    ]:
        if stale.lower() in readme.lower():
            fail(errors, f"README.md: stale private/unreleased language remains: {stale}")

    required_public = [
        OFFICIAL_CLI_PACKAGE, OFFICIAL_CLI_REPOSITORY, OFFICIAL_CLI_COMMIT,
        OFFICIAL_CLI_INTEGRITY, "planned-immutable-tag", "tag_exists_at_build",
        "local Git commit/ref fixture only", "After a later explicitly authorized Ship, public proof must",
        "does not claim model-backed behavior", "Publication remains **BLOCKED**",
        "only canonical endpoint", "parentless clean-root baseline",
        "ordinary reviewed linear commits",
        "refs/heads/main", "refs/heads/codex/issue-33-cross-harness-portability",
        "refs/pull/2/head", "refs/pull/3/head", "GitHub Support",
        "Skills issue metadata #1, #4, #5, #6, #7, and #8",
        "WITHHOLD/DELETE", "first public release", "no rename redirect",
        "Old clones", "verified bundle", "private recovery set",
        "force-with-lease", "git for-each-ref", "git rev-list", "git cat-file",
        "bounded anonymous GitHub API reads", "force-fetch and cleanup guidance",
        "v0.1.0 must not be recreated", "no public `v0.1.0` tag or release",
        "values never printed",
    ]
    for marker in required_public:
        if marker not in normalized_combined:
            fail(errors, f"public release contract: missing evidence marker {marker}")
    unsupported_execution = re.compile(
        r"(?:Claude Code|Cursor Agent)[^.\n]{0,180}(?:model-backed|forward behavior)[^.\n]{0,120}\b(?:verified|passed|successful|succeeded)\b",
        flags=re.IGNORECASE,
    )
    if unsupported_execution.search(combined):
        fail(errors, "public release contract: unsupported model-execution claim")
    for forbidden in [
        "lead confirms that historical private project-name and issue-path references are acceptable",
        "Ship must explicitly confirm that exposing those historical names is acceptable",
        "Historical private project-name references require lead acceptance",
    ]:
        if forbidden.lower() in normalized_combined.lower():
            fail(errors, f"public release contract: forbidden private-history acceptance option remains: {forbidden}")

    private_issue_url = re.compile(
        r"https://github\.com/onlinesourdough/(?!Skills(?:-Atlas)?(?:/|$))[^/\s)]+/issues/\d+"
    )
    inventory_candidate = re.compile(
        r"\b[A-Z][A-Za-z0-9]*(?:,\s*[A-Z][A-Za-z0-9]*){4}\b"
    )
    repository_identifier = re.compile(r"\bonlinesourdough/[A-Za-z0-9_.-]+\b")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            current = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if private_issue_url.search(current):
            fail(errors, f"{path.relative_to(ROOT)}: current tree contains a direct issue URL outside the public repository boundary")
        for candidate in repository_identifier.findall(current):
            if hashlib.sha256(candidate.encode("utf-8")).hexdigest() == BLOCKED_PRIVATE_REPOSITORY_SHA256:
                fail(errors, f"{path.relative_to(ROOT)}: current tree contains blocked private repository identifier")
        for candidate in inventory_candidate.findall(current):
            if hashlib.sha256(candidate.encode("utf-8")).hexdigest() == BLOCKED_PRIVATE_INVENTORY_SHA256:
                fail(errors, f"{path.relative_to(ROOT)}: current tree contains blocked private project inventory")

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    for command in ("python3 scripts/validate_repo.py", "python3 scripts/secret_scan.py", "python3 tests/run_all.py"):
        if command not in contributing:
            fail(errors, f"CONTRIBUTING.md: missing validation command {command}")
    if "Report a vulnerability" not in security or "do not disclose" not in security.lower():
        fail(errors, "SECURITY.md: private reporting guidance is incomplete")
    if "https://github.com/onlinesourdough/Skills/issues" not in support or "best-effort" not in support:
        fail(errors, "SUPPORT.md: public issue/support boundary is incomplete")

    for markdown in [
        ROOT / "README.md",
        ROOT / "CHANGELOG.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
        ROOT / "SUPPORT.md",
        ROOT / "docs" / "source-audit.md",
    ]:
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
            target = link.split("#", 1)[0]
            if not target or target.startswith(("http://", "https://", "mailto:")):
                continue
            if not (markdown.parent / target).exists():
                fail(errors, f"{markdown.relative_to(ROOT)}: broken relative link {target}")


def main() -> int:
    errors: list[str] = []
    validate_structure(errors)
    validate_json_files(errors)
    validate_git_candidate(errors)
    validate_public_docs(errors)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(
        "PASS repository structure, four-skill inventory, v0.2.0 candidate metadata, "
        "marketplace policy, clean-root baseline and linear history, withheld v0.1.0, public docs, and ownership boundaries"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
