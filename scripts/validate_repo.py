#!/usr/bin/env python3
"""Validate the portable source, distribution metadata, and release boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILLS = {"clarify", "setup-guardrails", "shape-offer"}
RETIRED_SKILL = "route-models"
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RELEASE_VERSION = "0.4.0"
RELEASE_TAG = f"v{RELEASE_VERSION}"
PREVIOUS_TAG = "v0.1.0"
BASELINE_REF = "refs/heads/codex/issue-33-cross-harness-portability"
MAIN_REF = "refs/heads/main"
CANONICAL_REPOSITORY = "https://github.com/onlinesourdough/Global-Skills"
OFFICIAL_CLI_PACKAGE = "skills@1.5.23"
OFFICIAL_CLI_REPOSITORY = "https://github.com/vercel-labs/skills"
OFFICIAL_CLI_COMMIT = "435076e78988e1e6ec40d00b0b1d76bdbbc5419a"
OFFICIAL_CLI_INTEGRITY = "sha512-+hMNBSi35yfX0sKD+ZcRm9y5or7u313OdkcvrRvJAsAzGCaA8wRTu2OmVdN0KRbk9ybqKby5dijkn6OVvNTUmw=="
BLOCKED_PRIVATE_INVENTORY_SHA256 = "5e73f79777725cea98698c251aab59ad5d812fde7f48a92f2b4337142585d659"
BLOCKED_PRIVATE_REPOSITORY_SHA256 = "23294037b9237da1e5d368f71d73c91061c2adc5bd2978a278f147406eb65682"
PRIVATE_ISSUE_URL = re.compile(
    r"https://github\.com/onlinesourdough/(?!Global-Skills(?:/|$)|Skills(?:-Atlas)?(?:/|$))[^/\s)]+/issues/\d+"
)
INVENTORY = re.compile(r"\b[A-Z][A-Za-z0-9]*(?:,\s*[A-Z][A-Za-z0-9]*){4}\b")
REPOSITORY = re.compile(r"\bonlinesourdough/[A-Za-z0-9_.-]+\b")

CODEX_MARKETPLACE_ADD = f"codex plugin marketplace add onlinesourdough/Global-Skills --ref {RELEASE_TAG}"
CODEX_LIST = "codex plugin list --available --json"
CODEX_INSTALL = "codex plugin add onlinesourdough-skills@onlinesourdough-skills"
SKILLS_DISCOVER = f"npx {OFFICIAL_CLI_PACKAGE} add onlinesourdough/Global-Skills#{RELEASE_TAG} --list"
SKILLS_INSTALL = f"npx {OFFICIAL_CLI_PACKAGE} add onlinesourdough/Global-Skills#{RELEASE_TAG} --skill clarify setup-guardrails shape-offer --agent claude-code cursor -y"
SKILLS_LIST = f"npx {OFFICIAL_CLI_PACKAGE} list --agent claude-code cursor"


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


def parse_string(raw: str, *, quoted: bool = False) -> str:
    """Parse the documented one-line string subset; reject YAML indicators."""
    raw = raw.strip()
    if raw.startswith('"'):
        value = json.loads(raw)
        if not isinstance(value, str):
            raise ValueError("not a string")
        return value
    if raw.startswith("'"):
        if not re.fullmatch(r"'(?:[^']|'')*'", raw):
            raise ValueError("invalid quoted string")
        return raw[1:-1].replace("''", "'")
    if quoted or not raw or not raw[0].isalpha() or raw[0] in "[{]}>,|*&!%@`#" or re.match(r"[-?:](?:\s|$)", raw):
        raise ValueError("use a valid quoted string")
    if raw.lower() in {"null", "~", "true", "false", "yes", "no", "on", "off"} or re.fullmatch(r"[-+]?\d+(?:\.\d+)?", raw) or re.search(r":(?:\s|$)|\s#", raw):
        raise ValueError("quote YAML special values")
    return raw


def parse_frontmatter(path: Path, errors: list[str], *, source: str | None = None) -> tuple[dict, str]:
    text = source if source is not None else path.read_text(encoding="utf-8")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        fail(errors, f"{path.relative_to(ROOT)}: invalid frontmatter")
        return {}, text
    marker = text.find("\n---\n", 4)
    values: dict = {}
    metadata = None
    for line in text[4:marker].splitlines():
        if not line.strip():
            continue
        if line.startswith("  ") and metadata is not None:
            match = re.fullmatch(r"  ([a-z][a-z0-9_-]*):\s+(.+)", line)
            if not match or match[1] in metadata:
                fail(errors, f"{path.relative_to(ROOT)}: invalid or duplicate metadata field")
                continue
            try:
                metadata[match[1]] = parse_string(match[2], quoted=True)
            except ValueError:
                fail(errors, f"{path.relative_to(ROOT)}: metadata values must be valid quoted strings")
            continue
        metadata = None
        if ":" not in line or line[:1].isspace():
            fail(errors, f"{path.relative_to(ROOT)}: invalid frontmatter line")
            continue
        key, value = line.split(":", 1)
        if key in values:
            fail(errors, f"{path.relative_to(ROOT)}: duplicate frontmatter field {key}")
            continue
        if key == "metadata" and not value.strip():
            metadata = {}
            values[key] = metadata
            continue
        try:
            values[key.strip()] = parse_string(value)
        except ValueError:
            fail(errors, f"{path.relative_to(ROOT)}: invalid frontmatter string {key}")
    return values, text[marker + 5 :]


def validate_skill(path: Path, errors: list[str]) -> None:
    slug = path.parent.name
    values, body = parse_frontmatter(path, errors)
    if not SLUG.fullmatch(slug):
        fail(errors, f"{path.relative_to(ROOT)}: invalid skill slug")
    if set(values) != {"name", "description", "metadata"} or values.get("name") != slug:
        fail(errors, f"{path.relative_to(ROOT)}: frontmatter name/keys mismatch")
    if not values.get("description") or not body.strip():
        fail(errors, f"{path.relative_to(ROOT)}: description and body are required")
    metadata = values.get("metadata")
    version = metadata.get("version", "") if isinstance(metadata, dict) else ""
    if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", version):
        fail(errors, f"{path.relative_to(ROOT)}: metadata.version must be MAJOR.MINOR.PATCH")
    if "[TODO" in path.read_text(encoding="utf-8"):
        fail(errors, f"{path.relative_to(ROOT)}: TODO placeholder remains")
    for child in path.parent.iterdir():
        if child.name in {"README.md", "CHANGELOG.md", "INSTALLATION_GUIDE.md"}:
            fail(errors, f"{child.relative_to(ROOT)}: auxiliary skill documentation is not allowed")
        if child.name == "agents" or child.is_symlink():
            fail(errors, f"{child.relative_to(ROOT)}: harness-specific or symlinked payload is not portable")
    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
        target = link.split("#", 1)[0]
        if target and not target.startswith(("http://", "https://", "mailto:")) and not (path.parent / target).exists():
            fail(errors, f"{path.relative_to(ROOT)}: referenced resource does not exist: {target}")
    for resource in path.parent.rglob("*"):
        if resource.is_file() and resource.name != "SKILL.md" and resource.name not in body:
            fail(errors, f"{resource.relative_to(ROOT)}: resource is not referenced by SKILL.md")


def validate_structure(errors: list[str]) -> None:
    required = {
        "AGENTS.md", "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
        "SUPPORT.md", "LICENSE", ".gitignore", ".codex-plugin/plugin.json", "package.json",
        ".agents/plugins/marketplace.json", "release.json", "docs/source-audit.md",
    }
    for relative in sorted(required):
        if not (ROOT / relative).is_file():
            fail(errors, f"missing required file: {relative}")

    skills_root = ROOT / "skills"
    actual = {path.name for path in skills_root.iterdir() if path.is_dir()} if skills_root.is_dir() else set()
    if actual != EXPECTED_SKILLS:
        fail(errors, f"skills/: expected {sorted(EXPECTED_SKILLS)}, found {sorted(actual)}")
    for slug in sorted(actual):
        skill_file = skills_root / slug / "SKILL.md"
        if not skill_file.is_file():
            fail(errors, f"missing canonical source: {skill_file.relative_to(ROOT)}")
        else:
            validate_skill(skill_file, errors)

    for path in ROOT.rglob("SKILL.md"):
        if ".git" not in path.parts and path.parent.parent != skills_root:
            fail(errors, f"duplicate payload outside skills/: {path.relative_to(ROOT)}")
    for forbidden in (".claude", ".cursor", ".agents/skills", ".mcp.json", "hooks", "apps", "__pycache__"):
        if (ROOT / forbidden).exists():
            fail(errors, f"harness/generated surface must not be packaged: {forbidden}")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            fail(errors, f"generated Python artifact is packaged: {path.relative_to(ROOT)}")
        if path.stat().st_size > 1_000_000:
            if path.relative_to(ROOT).as_posix() != "assets/branding/skills-banner.png" or hashlib.sha256(path.read_bytes()).hexdigest() != "1f078680bf93ad817b7bbb3a7036025ac50aec58b01a9ef1f1cde4d45e86113e":
                fail(errors, f"release-tree file exceeds 1 MB: {path.relative_to(ROOT)}")
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for marker in ("__pycache__/", "*.py[cod]", "skills-lock.json"):
        if marker not in ignore:
            fail(errors, f".gitignore: missing generated-file rule {marker}")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    if not license_text.startswith("MIT License\n") or "onlinesourdough contributors" not in license_text:
        fail(errors, "LICENSE: expected complete MIT license and project copyright")


def validate_json_files(errors: list[str]) -> None:
    manifest = load_json(ROOT / ".codex-plugin/plugin.json", errors)
    package = load_json(ROOT / "package.json", errors)
    marketplace = load_json(ROOT / ".agents/plugins/marketplace.json", errors)
    release = load_json(ROOT / "release.json", errors)

    if manifest.get("name") != "onlinesourdough-skills" or manifest.get("version") != RELEASE_VERSION or manifest.get("skills") != "./skills/" or manifest.get("license") != "MIT" or manifest.get("repository") != CANONICAL_REPOSITORY:
        fail(errors, "plugin.json: name/version/skills/license mismatch")
    interface = manifest.get("interface", {})
    if set(interface.get("capabilities", [])) != {"Visual explanation", "Offer shaping", "Local safety guardrails"}:
        fail(errors, "plugin.json: capability inventory mismatch")
    if any(key in manifest for key in ("apps", "hooks", "mcpServers", "mcp", "schedules")):
        fail(errors, "plugin.json: unsupported runtime surface added")

    if package.get("name") != manifest.get("name") or package.get("version") != RELEASE_VERSION or package.get("private") is not True or package.get("license") != "MIT":
        fail(errors, "package.json: private Pi package identity mismatch")
    if package.get("keywords") != ["pi-package"] or package.get("files") != ["skills", "README.md", "LICENSE"] or package.get("pi") != {"skills": ["./skills"]}:
        fail(errors, "package.json: Pi route/files mismatch")

    entries = marketplace.get("plugins", [])
    if marketplace.get("name") != manifest.get("name") or not isinstance(entries, list) or len(entries) != 1:
        fail(errors, "marketplace: root or plugin count mismatch")
    elif entries[0].get("name") != manifest.get("name") or entries[0].get("category") != "Productivity" or entries[0].get("source") != {"source": "url", "url": CANONICAL_REPOSITORY, "ref": RELEASE_TAG} or entries[0].get("policy") != {"installation": "AVAILABLE", "authentication": "ON_INSTALL"}:
        fail(errors, "marketplace: source or authentication policy mismatch")

    if release.get("schema_version") != 3 or release.get("name") != manifest.get("name") or release.get("version") != RELEASE_VERSION:
        fail(errors, "release.json: identity mismatch")
    if release.get("status") != "candidate" or release.get("released") is not False or release.get("release_date") is not None:
        fail(errors, "release.json: candidate must remain undated and unreleased")
    if release.get("included_skills") != sorted(EXPECTED_SKILLS) or release.get("source_of_truth") != "skills/<slug>/SKILL.md":
        fail(errors, "release.json: source inventory mismatch")
    boundary = release.get("source_boundary", {})
    if not all(phrase in boundary.get("candidate_state", "") for phrase in ("unreleased source candidate", "source-only synchronization", "no public tag or release")):
        fail(errors, "release.json: source/release boundary is incomplete")
    atlas = release.get("atlas", {})
    if atlas.get("canonical_repository") != CANONICAL_REPOSITORY or not all(phrase in atlas.get("candidate_boundary", "") for phrase in ("source candidate remains unreleased", "source-only synchronization", "does not create public release availability")):
        fail(errors, "release.json: Atlas/source boundary is incomplete")
    history = release.get("history_visibility", {})
    if history.get("status") != "PRIVATE_SUPPORT_PURGE_PENDING" or history.get("visibility_change_legal") is not False:
        fail(errors, "release.json: unresolved history gate must remain explicit")
    if release.get("release_notes") != "CHANGELOG.md#040-release-candidate":
        fail(errors, "release.json: release notes must target 0.4.0")

    planned = release.get("marketplace", {})
    if planned.get("source") != {"source": "url", "url": CANONICAL_REPOSITORY, "ref": RELEASE_TAG} or planned.get("tag_exists_at_build") is not False:
        fail(errors, "release.json: planned tag/source mismatch")
    if not all(phrase in planned.get("ship_requirement", "") for phrase in ("source-only synchronization", "GitHub Support confirms purge", "public release availability")):
        fail(errors, "release.json: Ship/recovery boundary missing")
    distribution = release.get("distribution", {})
    codex = distribution.get("codex", {})
    cli = distribution.get("skills_cli", {})
    if (codex.get("marketplace_add"), codex.get("list"), codex.get("install")) != (CODEX_MARKETPLACE_ADD, CODEX_LIST, CODEX_INSTALL):
        fail(errors, "release.json: Codex commands mismatch")
    if (cli.get("package"), cli.get("repository"), cli.get("source_commit"), cli.get("npm_integrity"), cli.get("discover"), cli.get("install"), cli.get("list")) != (OFFICIAL_CLI_PACKAGE, OFFICIAL_CLI_REPOSITORY, OFFICIAL_CLI_COMMIT, OFFICIAL_CLI_INTEGRITY, SKILLS_DISCOVER, SKILLS_INSTALL, SKILLS_LIST):
        fail(errors, "release.json: Skills CLI pin/commands mismatch")
    if "does not claim model-backed behavior" not in distribution.get("model_execution_boundary", ""):
        fail(errors, "release.json: model-execution limitation missing")
    evidence = release.get("build_evidence", {})
    if evidence.get("required_checks") != ["python3 scripts/validate_repo.py", "python3 scripts/secret_scan.py", "python3 tests/run_all.py"] or evidence.get("candidate_only") is not True:
        fail(errors, "release.json: required checks mismatch")
    gate = "\n".join(release.get("ship_gate", []))
    for marker in ("v0.1.0", "GitHub Support confirms purge", "private-state re-audit", "later exact Ship authority"):
        if marker not in gate:
            fail(errors, f"release.json: Ship gate is missing {marker}")


def git_output(*arguments: str) -> str | None:
    result = subprocess.run(["git", *arguments], cwd=ROOT, text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def validate_versions_against(base: str, errors: list[str]) -> None:
    """Require an increased skill version when any of its shipped files changes."""
    revision = git_output("rev-parse", "--verify", "--end-of-options", f"{base}^{{commit}}")
    if not revision:
        fail(errors, "skill versions: baseline must resolve to a local commit")
        return
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        relative = skill.parent.relative_to(ROOT).as_posix()
        before = git_output("show", f"{revision}:{relative}/SKILL.md")
        values, _ = parse_frontmatter(skill, errors)
        metadata = values.get("metadata")
        version = metadata.get("version", "") if isinstance(metadata, dict) else ""
        prior_errors = len(errors)
        old_fields, _ = parse_frontmatter(skill, errors, source=before) if before is not None else ({}, "")
        if len(errors) != prior_errors:
            fail(errors, f"{relative}: cannot assess malformed baseline frontmatter")
            continue
        old_metadata = old_fields.get("metadata", {})
        if not isinstance(old_metadata, dict):
            fail(errors, f"{relative}: malformed baseline metadata")
            continue
        old = old_metadata.get("version")
        if old is None:
            if version != "1.0.0":
                fail(errors, f"{relative}: first individually tracked version must be 1.0.0")
            continue
        if not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", old):
            fail(errors, f"{relative}: malformed baseline metadata.version")
            continue
        try:
            current_version = tuple(int(n) for n in version.split("."))
            old_version = tuple(int(n) for n in old.split("."))
        except ValueError:
            fail(errors, f"{relative}: version components cannot be compared on this runtime")
            continue
        if current_version < old_version:
            fail(errors, f"{relative}: skill version cannot decrease")
        old_files = set((git_output("ls-tree", "-r", "--name-only", revision, "--", relative) or "").splitlines())
        current_files = {p.relative_to(ROOT).as_posix() for p in skill.parent.rglob("*") if p.is_file()}
        changed = old_files != current_files
        for name in old_files & current_files:
            blob = subprocess.run(["git", "show", f"{revision}:{name}"], cwd=ROOT, capture_output=True)
            changed = changed or blob.returncode != 0 or blob.stdout != (ROOT / name).read_bytes()
        if changed and current_version <= old_version:
            fail(errors, f"{relative}: changed payload requires an increased metadata.version")


def validate_git_candidate(errors: list[str]) -> None:
    if git_output("rev-parse", "--verify", f"refs/tags/{PREVIOUS_TAG}^{{commit}}") is not None:
        fail(errors, f"Git: withheld historical tag {PREVIOUS_TAG} must be absent")
    if git_output("rev-parse", "--verify", f"refs/tags/{RELEASE_TAG}^{{commit}}") is not None:
        fail(errors, f"Git: candidate contract must not claim absent tag while {RELEASE_TAG} exists")
    head, main, baseline = git_output("rev-parse", "HEAD"), git_output("rev-parse", MAIN_REF), git_output("rev-parse", BASELINE_REF)
    if not head or not main or not baseline:
        fail(errors, "Git: HEAD, main, and the retained clean-root baseline branch must all resolve")
        return
    if head != main:
        fail(errors, "Git: HEAD must equal main for candidate validation")
    if git_output("rev-list", "--parents", "-n", "1", baseline) != baseline:
        fail(errors, "Git: retained candidate branch must point to a parentless clean-root baseline")
    roots = git_output("rev-list", "--max-parents=0", MAIN_REF, BASELINE_REF)
    if roots != baseline:
        fail(errors, "Git: main and the retained candidate branch must share exactly one clean-root baseline")
    if git_output("merge-base", "--is-ancestor", baseline, main) is None:
        fail(errors, "Git: main must descend from the retained clean-root baseline")
    divergence = git_output("rev-list", "--left-right", "--count", f"{baseline}...{main}")
    try:
        baseline_only, _ = (int(value) for value in (divergence or "").split())
    except ValueError:
        fail(errors, "Git: baseline/main divergence could not be determined")
    else:
        if baseline_only != 0:
            fail(errors, "Git: retained baseline branch must not diverge from main")
    lineage = git_output("rev-list", "--parents", f"{baseline}..{main}")
    if lineage is None or any(len(record.split()) != 2 for record in lineage.splitlines()):
        fail(errors, "Git: main may advance from the baseline only through ordinary single-parent commits")


def validate_docs_and_privacy(errors: list[str]) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    audit = (ROOT / "docs/source-audit.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    normalized_docs = " ".join((readme + "\n" + audit + "\n" + changelog).split())
    for slug in sorted(EXPECTED_SKILLS):
        if f"skills/{slug}/SKILL.md" not in readme:
            fail(errors, f"README.md: missing skill index entry {slug}")
    for marker in ("canonical payload", "Codex plugin", "Skills CLI", "Pi package", "source-only synchronization", "does not create public release availability", "Publication remains **BLOCKED**", "GitHub Support", "MIT License"):
        if marker.lower() not in normalized_docs.lower():
            fail(errors, f"docs: missing boundary or usage marker {marker}")
    for stale in ("private immutable release source", "three actual skills", "current release; the tag is unchanged"):
        if stale in readme.lower():
            fail(errors, f"README.md: stale wording remains: {stale}")
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    support = (ROOT / "SUPPORT.md").read_text(encoding="utf-8")
    for command in ("python3 scripts/validate_repo.py", "python3 scripts/secret_scan.py", "python3 tests/run_all.py"):
        if command not in contributing:
            fail(errors, f"CONTRIBUTING.md: missing validation command {command}")
    if "Report a vulnerability" not in security or "do not disclose" not in security.lower():
        fail(errors, "SECURITY.md: private reporting guidance is incomplete")
    if f"{CANONICAL_REPOSITORY}/issues" not in support:
        fail(errors, "SUPPORT.md: public issue boundary is incomplete")
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PRIVATE_ISSUE_URL.search(text):
            fail(errors, f"{path.relative_to(ROOT)}: direct private issue URL remains")
        for candidate in REPOSITORY.findall(text):
            if hashlib.sha256(candidate.encode()).hexdigest() == BLOCKED_PRIVATE_REPOSITORY_SHA256:
                fail(errors, f"{path.relative_to(ROOT)}: blocked private repository identifier remains")
        for candidate in INVENTORY.findall(text):
            if hashlib.sha256(candidate.encode()).hexdigest() == BLOCKED_PRIVATE_INVENTORY_SHA256:
                fail(errors, f"{path.relative_to(ROOT)}: blocked private project inventory remains")
    for markdown in ("README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "docs/source-audit.md"):
        path = ROOT / markdown
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = link.split("#", 1)[0]
            if target and not target.startswith(("http://", "https://", "mailto:")) and not (path.parent / target).exists():
                fail(errors, f"{markdown}: broken relative link {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="local reviewed commit for per-skill version progression")
    args = parser.parse_args()
    errors: list[str] = []
    validate_structure(errors)
    validate_json_files(errors)
    validate_git_candidate(errors)
    if args.base:
        validate_versions_against(args.base, errors)
    validate_docs_and_privacy(errors)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print("PASS source structure, three-skill inventory, metadata, safety boundaries, and Git lineage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
