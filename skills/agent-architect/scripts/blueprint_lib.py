"""Shared blueprint loading, normalisation and checks for agent-architect scripts."""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HARNESSES = ["claude-code", "copilot-cli", "codex", "gemini-cli", "cursor", "opencode"]
CAPABILITIES = ["read", "search", "edit", "shell", "web", "delegate"]
TIERS = ["inherit", "fast", "balanced", "strong"]
ON_FAILURE = ["retry-once", "skip-and-report", "stop"]

LIMITS = {
    "description_chars": 1024,
    "skill_body_lines": 200,
    "skill_body_lines_hard": 500,
    "agent_prompt_lines": 80,
    "agent_body_chars_hard": 30000,
    "reference_lines": 300,
}

VAR_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
SECRET_KEY_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|PRIVATE|CREDENTIAL|PAT)\b", re.I)
LITERAL_SECRET_RES = [
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


class BlueprintError(Exception):
    pass


def load_blueprint(path: str | Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise BlueprintError(
                "PyYAML is not installed. Run `pip install pyyaml` or write the blueprint as JSON."
            ) from exc
    if not isinstance(data, dict):
        raise BlueprintError("Blueprint must be a mapping at the top level.")
    return normalize(data)


def normalize(bp: dict) -> dict:
    bp.setdefault("version", 1)
    bp.setdefault("system", {})
    bp["system"].setdefault("harnesses", list(HARNESSES))
    bp.setdefault("agents", [])
    bp.setdefault("skills", [])
    bp.setdefault("mcp_servers", [])
    for agent in bp["agents"]:
        agent.setdefault("capabilities", ["read", "search"])
        agent.setdefault("mcp", [])
        agent.setdefault("skills", [])
        agent.setdefault("owns", [])
        agent.setdefault("model", "inherit")
        agent.setdefault("models", {})
    for skill in bp["skills"]:
        skill.setdefault("references", [])
        skill.setdefault("scripts", [])
    for server in bp["mcp_servers"]:
        server.setdefault("transport", "stdio" if server.get("command") else "http")
        server.setdefault("args", [])
        server.setdefault("env", {})
        server.setdefault("headers", {})
    orch = bp.get("orchestrator")
    if orch:
        orch.setdefault("waves", [])
        orch.setdefault("checkpoints", [])
        orch.setdefault("on_failure", "retry-once")
        orch.setdefault("manual_only", bool(orch["checkpoints"]))
    return bp


def _lines(text: str | None) -> int:
    return len((text or "").rstrip("\n").splitlines())


def _check_name(kind: str, name, errors: list) -> None:
    if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
        errors.append(f"{kind} name {name!r} must be kebab-case (a-z, 0-9, hyphens), max 64 chars.")


def _check_description(kind: str, name: str, desc, errors: list, warnings: list) -> None:
    if not isinstance(desc, str) or not desc.strip():
        errors.append(f"{kind} '{name}': description is required.")
        return
    if len(desc) > LIMITS["description_chars"]:
        errors.append(f"{kind} '{name}': description is {len(desc)} chars (max 1024).")
    if not re.search(r"\b(use|when|whenever|for)\b", desc, re.I):
        warnings.append(f"{kind} '{name}': description should say when to use it ('Use when ...').")


def find_literal_secrets(value) -> list[str]:
    hits = []
    texts = []
    if isinstance(value, str):
        texts = [value]
    elif isinstance(value, dict):
        texts = [str(v) for v in value.values()]
    elif isinstance(value, list):
        texts = [str(v) for v in value]
    for text in texts:
        for rx in LITERAL_SECRET_RES:
            if rx.search(text):
                hits.append(text[:12] + "...")
    return hits


def _norm_glob(pattern: str) -> str:
    return pattern.strip().lstrip("./")


def patterns_overlap(a: str, b: str) -> bool:
    a, b = _norm_glob(a), _norm_glob(b)
    if a == b or fnmatch.fnmatch(a, b) or fnmatch.fnmatch(b, a):
        return True
    a_base = a.split("*", 1)[0].rstrip("/")
    b_base = b.split("*", 1)[0].rstrip("/")
    a_dir = "*" in a or a.endswith("/")
    b_dir = "*" in b or b.endswith("/")
    if a_dir and (b == a_base or b.startswith(a_base + "/")):
        return True
    if b_dir and (a == b_base or a.startswith(b_base + "/")):
        return True
    return False


def check_blueprint(bp: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if bp.get("version") != 1:
        errors.append("version must be 1.")
    system = bp.get("system", {})
    _check_name("system", system.get("name"), errors)
    if not system.get("description"):
        errors.append("system.description is required.")
    reqs = system.get("requirements", [])
    if not isinstance(reqs, list) or not all(isinstance(r, str) and r.strip() for r in reqs):
        errors.append("system.requirements must be a list of non-empty strings.")
    for h in system.get("harnesses", []):
        if h not in HARNESSES:
            errors.append(f"Unknown harness '{h}'. Valid: {', '.join(HARNESSES)}.")

    agents = {a.get("name"): a for a in bp["agents"]}
    skills = {s.get("name"): s for s in bp["skills"]}
    servers = {m.get("name"): m for m in bp["mcp_servers"]}
    orch = bp.get("orchestrator")

    seen: dict[str, str] = {}
    all_names = [("agent", n) for n in agents] + [("skill", n) for n in skills]
    if orch:
        all_names.append(("orchestrator", orch.get("name")))
    for kind, name in all_names:
        _check_name(kind, name, errors)
        if name in seen:
            errors.append(f"Name '{name}' is used by both a {seen[name]} and a {kind}.")
        seen[name] = kind
    if len(agents) != len(bp["agents"]) or len(skills) != len(bp["skills"]):
        errors.append("Agent and skill names must be unique.")

    # Agents
    for name, a in agents.items():
        _check_description("agent", name, a.get("description"), errors, warnings)
        if not (a.get("prompt") or "").strip():
            errors.append(f"agent '{name}': prompt is required.")
        elif _lines(a["prompt"]) > LIMITS["agent_prompt_lines"]:
            errors.append(
                f"agent '{name}': prompt is {_lines(a['prompt'])} lines (max 80). "
                "Move knowledge into a skill."
            )
        if not (a.get("returns") or "").strip():
            errors.append(f"agent '{name}': returns (output contract) is required.")
        caps = a["capabilities"]
        for c in caps:
            if c not in CAPABILITIES:
                errors.append(f"agent '{name}': unknown capability '{c}'.")
        if "edit" in caps and not a["owns"]:
            errors.append(f"agent '{name}': has 'edit' but no 'owns' paths.")
        if a["owns"] and "edit" not in caps:
            warnings.append(f"agent '{name}': declares 'owns' but lacks the 'edit' capability.")
        if "delegate" in caps:
            warnings.append(
                f"agent '{name}': 'delegate' makes it spawn agents; Gemini CLI does not support "
                "nested agents and it will be dropped there."
            )
        for m in a["mcp"]:
            if m not in servers:
                errors.append(f"agent '{name}': mcp server '{m}' is not defined in mcp_servers.")
        for s in a["skills"]:
            if s not in skills:
                errors.append(f"agent '{name}': skill '{s}' is not defined in skills.")
        if a["model"] not in TIERS:
            errors.append(f"agent '{name}': model must be one of {', '.join(TIERS)}.")
        for h in a["models"]:
            if h not in HARNESSES:
                errors.append(f"agent '{name}': models has unknown harness '{h}'.")

    # Skills
    for name, s in skills.items():
        _check_description("skill", name, s.get("description"), errors, warnings)
        if s.get("install"):
            if s.get("body"):
                warnings.append(f"skill '{name}': has both install and body; body is ignored.")
            continue
        if not (s.get("body") or "").strip():
            errors.append(f"skill '{name}': needs a body (or install: to reuse an existing skill).")
        elif _lines(s["body"]) > LIMITS["skill_body_lines"]:
            errors.append(
                f"skill '{name}': body is {_lines(s['body'])} lines (max 200). Move detail to references."
            )
        for ref in s["references"]:
            p = ref.get("path", "")
            if "/" in p or "\\" in p or not p.endswith(".md"):
                errors.append(f"skill '{name}': reference path '{p}' must be a plain .md filename.")
            content = ref.get("content", "")
            if _lines(content) > LIMITS["reference_lines"] and "contents" not in content[:500].lower():
                warnings.append(
                    f"skill '{name}': reference '{p}' is over 300 lines; add a Contents list at the top."
                )
            if re.search(r"\]\((?!https?:)[^)]+\.md\)", content):
                warnings.append(f"skill '{name}': reference '{p}' links to another file; keep references one level deep.")
        for sc in s["scripts"]:
            p = sc.get("path", "")
            if "/" in p or "\\" in p or not p:
                errors.append(f"skill '{name}': script path '{p}' must be a plain filename.")

    # MCP servers
    for name, m in servers.items():
        _check_name("mcp server", name, errors)
        if not m.get("why"):
            warnings.append(f"mcp server '{name}': add 'why' so the user knows what they approve.")
        t = m["transport"]
        if t == "stdio" and not m.get("command"):
            errors.append(f"mcp server '{name}': stdio transport needs 'command'.")
        elif t == "http" and not m.get("url"):
            errors.append(f"mcp server '{name}': http transport needs 'url'.")
        elif t not in ("stdio", "http"):
            errors.append(f"mcp server '{name}': transport must be stdio or http.")
        for field in ("env", "headers", "args", "url"):
            for hit in find_literal_secrets(m.get(field)):
                errors.append(f"mcp server '{name}': {field} contains what looks like a literal secret ({hit}). Use ${{VAR}}.")
        for key, val in {**m["env"], **m["headers"]}.items():
            if SECRET_KEY_RE.search(key) and not VAR_REF_RE.search(str(val)):
                errors.append(f"mcp server '{name}': '{key}' must be an env reference like ${{{key.upper()}}}.")
        if not any(name in a["mcp"] for a in agents.values()):
            warnings.append(f"mcp server '{name}' is not used by any agent.")

    orch_text = json.dumps(orch) if orch else ""
    for name in skills:
        used = any(name in a["skills"] for a in agents.values()) or name in orch_text
        if not used:
            warnings.append(f"skill '{name}' is not used by any agent or by the orchestrator.")

    # Orchestrator
    if orch:
        _check_description("orchestrator", orch.get("name"), orch.get("description"), errors, warnings)
        if not orch.get("output"):
            errors.append("orchestrator: output is required.")
        if orch["on_failure"] not in ON_FAILURE:
            errors.append(f"orchestrator: on_failure must be one of {', '.join(ON_FAILURE)}.")
        waves = orch["waves"]
        if not waves:
            errors.append("orchestrator: at least one wave is required.")
        wave_names = []
        used_agents = set()
        for i, w in enumerate(waves):
            wname = w.get("name") or f"wave-{i + 1}"
            _check_name("wave", wname, errors)
            if wname in wave_names:
                errors.append(f"orchestrator: duplicate wave name '{wname}'.")
            wave_names.append(wname)
            members = w.get("agents") or []
            run = w.get("run")
            if run is not None:
                if members:
                    errors.append(f"wave '{wname}': use either 'agents' or 'run', not both.")
                if not isinstance(run, str) or not run.strip():
                    errors.append(f"wave '{wname}': 'run' must be a non-empty command.")
                if w.get("for_each"):
                    errors.append(f"wave '{wname}': a 'run' wave cannot use for_each; let the script loop.")
                if isinstance(run, str) and find_literal_secrets(run):
                    errors.append(f"wave '{wname}': 'run' contains what looks like a literal secret. Use ${{VAR}}.")
                continue
            if not members:
                errors.append(f"wave '{wname}': lists no agents (or give a 'run' command).")
            for an in members:
                if an not in agents:
                    errors.append(f"wave '{wname}': agent '{an}' is not defined.")
                used_agents.add(an)
            # file ownership inside the wave
            members = [agents[an] for an in members if an in agents]
            for x in range(len(members)):
                for y in range(x + 1, len(members)):
                    for pa in members[x]["owns"]:
                        for pb in members[y]["owns"]:
                            if patterns_overlap(pa, pb):
                                errors.append(
                                    f"wave '{wname}': '{members[x]['name']}' and '{members[y]['name']}' "
                                    f"both may write '{pa}' / '{pb}'. Parallel writers must not overlap."
                                )
            if w.get("for_each") and w.get("max_parallel", 2) != 1:
                for a in members:
                    if "edit" in a["capabilities"] and any("{item}" not in p for p in a["owns"]):
                        errors.append(
                            f"wave '{wname}': '{a['name']}' runs once per item but owns paths without "
                            "'{item}'; instances would overwrite each other."
                        )
        for cp in orch["checkpoints"]:
            ref = cp.get("after") or cp.get("before")
            if ref not in wave_names:
                errors.append(f"checkpoint refers to unknown wave '{ref}'.")
            if not cp.get("ask"):
                errors.append(f"checkpoint at '{ref}': 'ask' is required.")
        for name in agents:
            if name not in used_agents:
                warnings.append(f"agent '{name}' is not used in any wave.")

    return errors, warnings


def summary(bp: dict) -> str:
    out = [f"System: {bp['system'].get('name')} — {bp['system'].get('description', '').strip()}"]
    out.append(f"Targets: {', '.join(bp['system'].get('harnesses', []))}")
    orch = bp.get("orchestrator")
    if orch:
        out.append(f"\nOrchestrator skill: /{orch.get('name')}  (manual only: {orch.get('manual_only')})")
        for i, w in enumerate(orch.get("waves", []), 1):
            fe = f", one per {w['for_each']}" if w.get("for_each") else ""
            who = f"script: {w['run'].strip()}" if w.get("run") else ", ".join(w.get("agents", []))
            out.append(f"  Wave {i} {w.get('name')}: {who}{fe}")
        for cp in orch.get("checkpoints", []):
            where = f"after {cp['after']}" if cp.get("after") else f"before {cp.get('before')}"
            out.append(f"  Checkpoint {where}: {cp.get('ask')}")
    out.append("\nAgents:")
    rows = [("name", "capabilities", "mcp", "owns", "model")]
    for a in bp["agents"]:
        rows.append((
            a.get("name", "?"),
            ",".join(a["capabilities"]),
            ",".join(a["mcp"]) or "-",
            ",".join(a["owns"]) or "-",
            a["model"],
        ))
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    for r in rows:
        out.append("  " + "  ".join(c.ljust(widths[i]) for i, c in enumerate(r)))
    if bp["skills"]:
        out.append("\nSkills:")
        for s in bp["skills"]:
            how = f"install: {s['install']}" if s.get("install") else f"generate ({len(s['references'])} refs)"
            out.append(f"  {s.get('name')}: {how}")
    if bp["mcp_servers"]:
        out.append("\nMCP servers (proposed, not installed):")
        for m in bp["mcp_servers"]:
            refs = sorted(set(VAR_REF_RE.findall(json.dumps(m))))
            out.append(f"  {m.get('name')} [{m['transport']}] secrets: {', '.join(refs) or 'none'} — {m.get('why', '')}")
    return "\n".join(out)
