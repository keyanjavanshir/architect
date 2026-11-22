#!/usr/bin/env python3
"""Render an agent-architect blueprint into harness-specific agent, skill and setup files.

Usage:
  python3 render.py BLUEPRINT --out PROJECT_DIR [--harness all|h1,h2] [--dry-run] [--force]
                    [--no-symlinks]

Skills go once to .agents/skills/ (symlinked into .claude/skills/ for Claude Code).
Agents go to each harness's own folder. SETUP.md and a manifest go to
.agent-architect/<system>/. MCP config files are never modified.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blueprint_lib import (  # noqa: E402
    HARNESSES,
    VAR_REF_RE,
    BlueprintError,
    check_blueprint,
    load_blueprint,
)

GENERATOR = "agent-architect"

# --------------------------------------------------------------------------- YAML/TOML output

_PLAIN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./()+-]*$")
_YAML_WORDS = {"yes", "no", "true", "false", "on", "off", "null", "~", "y", "n"}


def yscalar(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    if _PLAIN_RE.match(s) and s.lower() not in _YAML_WORDS and not s.endswith(" ") and not re.match(r"^[\d.+-]+$", s):
        return s
    return json.dumps(s, ensure_ascii=False)


def yaml_block(data: dict, indent: int = 0) -> str:
    pad = " " * indent
    lines = []
    for key, value in data.items():
        if value is None or value == [] or value == {}:
            continue
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(yaml_block(value, indent + 2))
        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            lines.extend(f"{pad}  - {yscalar(v)}" for v in value)
        else:
            lines.append(f"{pad}{key}: {yscalar(value)}")
    return "\n".join(lines)


def frontmatter(data: dict, body: str) -> str:
    return f"---\n{yaml_block(data)}\n---\n\n{body.strip()}\n"


def tstr(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def tmultiline(s: str) -> str:
    s = s.strip("\n")
    if "'''" not in s:
        return "'''\n" + s + "\n'''"
    return tstr(s)


def tinline(d: dict) -> str:
    return "{ " + ", ".join(f"{tstr(k)} = {tstr(str(v))}" for k, v in d.items()) + " }"


# --------------------------------------------------------------------------- capability maps

CLAUDE_TOOLS = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "Write", "NotebookEdit"],
    "shell": ["Bash"],
    "web": ["WebSearch", "WebFetch"],
    "delegate": ["Agent"],
}
COPILOT_TOOLS = {"read": "read", "search": "search", "edit": "edit", "shell": "execute", "web": "web", "delegate": "agent"}
GEMINI_TOOLS = {
    "read": ["read_file", "read_many_files", "list_directory"],
    "search": ["glob", "grep_search"],
    "edit": ["write_file", "replace"],
    "shell": ["run_shell_command"],
    "web": ["web_fetch", "google_web_search"],
}
CLAUDE_TIERS = {"fast": "haiku", "balanced": "sonnet", "strong": "opus", "inherit": "inherit"}
CODEX_EFFORT = {"fast": "low", "balanced": "medium", "strong": "high"}


def title(name: str) -> str:
    return name.replace("-", " ").capitalize()


# --------------------------------------------------------------------------- bodies

def agent_body(agent: dict, harness: str) -> str:
    parts = [agent["prompt"].strip()]
    scope = []
    caps = agent["capabilities"]
    if "edit" in caps:
        owned = ", ".join(f"`{p}`" for p in agent["owns"])
        scope.append(
            f"- Write only to: {owned}. Other agents may be working in parallel; never modify other files."
        )
    else:
        scope.append("- Read-only: do not create, modify or delete files.")
    if "shell" not in caps:
        scope.append("- Do not run shell commands.")
    if "web" not in caps and not agent["mcp"]:
        scope.append("- Do not access the network.")
    if agent["mcp"]:
        scope.append("- External systems: " + ", ".join(f"the `{m}` MCP server" for m in agent["mcp"]) + ".")
    scope.append("- Everything you need is in your brief. If something essential is missing, say so in your result instead of guessing.")
    parts.append("## Scope\n\n" + "\n".join(scope))
    if agent["skills"]:
        verb = "These skills are preloaded" if harness == "claude-code" else "Load these skills before you start"
        parts.append("## Skills\n\n" + f"{verb}: " + ", ".join(f"`{s}`" for s in agent["skills"]) + ".")
    parts.append("## Return\n\n" + agent["returns"].strip())
    return "\n\n".join(parts)


FAILURE_TEXT = {
    "retry-once": "If a unit fails, re-dispatch it once with the error added to its brief. If it fails again, continue and list it under **Failed** in the output.",
    "skip-and-report": "If a unit fails, do not retry. Continue and list it under **Skipped** in the output with the reason.",
    "stop": "If any unit fails, stop dispatching, and report what finished and what failed.",
}


def orchestrator_body(bp: dict) -> str:
    orch = bp["orchestrator"]
    agents = {a["name"]: a for a in bp["agents"]}
    lines = [f"# /{orch['name']}", ""]
    lines.append(
        f"You coordinate the **{bp['system']['name']}** system. Do preparation and synthesis yourself; "
        "delegate each unit of work to the named sub-agent. Start every agent in a wave at the same time "
        "when your harness can run sub-agents in parallel, and finish a wave before starting the next."
    )
    if orch.get("argument_hint"):
        lines += ["", f"**Input:** {orch['argument_hint']}. If it is missing, ask for it before doing anything else."]
    if (orch.get("instructions") or "").strip():
        lines += ["", "## Preparation", "", orch["instructions"].strip()]
    lines += ["", "## Waves"]
    cps_after = {c["after"]: c for c in orch["checkpoints"] if c.get("after")}
    cps_before = {c["before"]: c for c in orch["checkpoints"] if c.get("before")}
    for i, w in enumerate(orch["waves"], 1):
        wname = w.get("name") or f"wave-{i}"
        if wname in cps_before:
            lines += ["", f"**Checkpoint:** stop and ask the user: \"{cps_before[wname]['ask']}\" Continue only on an explicit yes."]
        members = w.get("agents", [])
        if w.get("run"):
            lines += ["", f"### {i}. {title(wname)} (script, no agent)", ""]
            lines.append(f"- Run this command yourself from the project root: `{w['run'].strip()}`")
            if w.get("pass"):
                lines.append(f"- {w['pass'].strip()}")
            lines.append("- Report only its summary lines. If it fails, show the error and stop; do not redo the script's work by hand or with an agent.")
            if wname in cps_after:
                lines += ["", f"**Checkpoint:** stop and ask the user: \"{cps_after[wname]['ask']}\" Continue only on an explicit yes."]
            continue
        mode = "in parallel" if len(members) > 1 or w.get("for_each") else "one agent"
        head = f"### {i}. {title(wname)} ({mode})"
        lines += ["", head, ""]
        if w.get("for_each"):
            cap = f", at most {w['max_parallel']} at a time" if w.get("max_parallel") else ""
            lines.append(f"- Run one instance of each agent per **{w['for_each']}**{cap}. Replace `{{item}}` in owned paths with a short slug for the item.")
        lines.append("- Agents: " + ", ".join(f"`{m}`" for m in members))
        if w.get("pass"):
            lines.append(f"- Each brief must include: {w['pass'].strip()}")
        if i > 1:
            lines.append("- Include the relevant results of the previous wave in each brief; the agents cannot see them otherwise.")
        if wname in cps_after:
            lines += ["", f"**Checkpoint:** stop and ask the user: \"{cps_after[wname]['ask']}\" Continue only on an explicit yes."]
    lines += [
        "",
        "## Writing a brief",
        "",
        "Sub-agents start with no memory of this conversation. Every brief contains:",
        "",
        "1. **Goal** — one sentence and how success is judged.",
        "2. **Inputs** — the content itself, or exact paths, URLs or IDs.",
        "3. **Scope** — the files it owns for this run and anything off limits.",
        "4. **Context** — decisions already made that constrain the work.",
        "5. **Return** — the format the agent's definition asks for, in at most five lines plus file paths; details belong in files, not in this conversation.",
        "",
        "Start a fresh agent for follow-up work instead of resuming one that has been idle for more than a few minutes; give it only the files it needs.",
        "",
        "## Failures",
        "",
        FAILURE_TEXT[orch["on_failure"]],
        "",
        "## Output",
        "",
        orch["output"].strip(),
        "",
        "## Agents",
        "",
        "| Agent | Use for | May write |",
        "|---|---|---|",
    ]
    for w in orch["waves"]:
        for m in w.get("agents", []):
            a = agents.get(m)
            if a and f"| `{m}` |" not in "\n".join(lines):
                desc = a["description"].split(". ")[0].rstrip(".")
                owns = ", ".join(f"`{p}`" for p in a["owns"]) or "nothing"
                lines.append(f"| `{m}` | {desc} | {owns} |")
    lines += [
        "",
        "## Running sub-agents",
        "",
        "- Copilot CLI: this skill works best under `/fleet`, which runs the agents in parallel.",
        "- Claude Code, Codex, Gemini CLI, Cursor, OpenCode: spawn each agent by its exact name.",
        "- If your harness cannot spawn sub-agents, do each unit yourself in order, following that agent's definition.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- per-harness agents

def render_agent(agent: dict, harness: str, servers: dict, warnings: list) -> tuple[str, str]:
    name = agent["name"]
    caps = agent["capabilities"]
    tier = agent["model"]
    override = agent["models"].get(harness)
    body = agent_body(agent, harness)

    if harness == "claude-code":
        fm = {"name": name, "description": agent["description"]}
        if agent["mcp"]:
            denied = [t for c, tools in CLAUDE_TOOLS.items() if c not in caps for t in tools]
            fm["disallowedTools"] = ", ".join(denied) if denied else None
            fm["mcpServers"] = agent["mcp"]
        else:
            fm["tools"] = ", ".join(t for c in caps for t in CLAUDE_TOOLS[c])
        model = override or CLAUDE_TIERS[tier]
        if model != "inherit":
            fm["model"] = model
        fm["skills"] = agent["skills"]
        fm["maxTurns"] = agent.get("max_turns")
        return f".claude/agents/{name}.md", frontmatter(fm, body)

    if harness == "copilot-cli":
        tools = [COPILOT_TOOLS[c] for c in caps]
        tools += [f"{m}/*" for m in agent["mcp"]]
        fm = {"name": name, "description": agent["description"], "tools": tools}
        if override:
            fm["model"] = override
        return f".github/agents/{name}.agent.md", frontmatter(fm, body)

    if harness == "codex":
        if "edit" not in caps:
            warnings.append(f"codex: '{name}' is read-only by instruction only; Codex agent files cannot set the sandbox.")
        lines = [
            f"# Generated by {GENERATOR}. Edit the blueprint, not this file.",
            f"name = {tstr(name)}",
            f"description = {tstr(agent['description'])}",
        ]
        if override:
            lines.append(f"model = {tstr(override)}")
        if tier in CODEX_EFFORT:
            lines.append(f"model_reasoning_effort = {tstr(CODEX_EFFORT[tier])}")
        lines.append(f"developer_instructions = {tmultiline(body)}")
        if "shell" not in caps:
            lines += ["", "[features]", "shell_tool = false"]
        return f".codex/agents/{name}.toml", "\n".join(lines) + "\n"

    if harness == "gemini-cli":
        tools = [t for c in caps if c in GEMINI_TOOLS for t in GEMINI_TOOLS[c]]
        if "delegate" in caps:
            warnings.append(f"gemini-cli: '{name}' drops 'delegate'; Gemini CLI sub-agents cannot call other agents.")
        tools += [f"mcp_{m}_*" for m in agent["mcp"]]
        fm = {"name": name, "description": agent["description"], "tools": tools}
        if override:
            fm["model"] = override
        fm["max_turns"] = agent.get("max_turns")
        return f".gemini/agents/{name}.md", frontmatter(fm, body)

    if harness == "cursor":
        fm = {"name": name, "description": agent["description"]}
        if override:
            fm["model"] = override
        if "edit" not in caps and "shell" not in caps:
            fm["readonly"] = True
        return f".cursor/agents/{name}.md", frontmatter(fm, body)

    if harness == "opencode":
        perm = {}
        if "edit" not in caps:
            perm["edit"] = "deny"
        if "shell" not in caps:
            perm["bash"] = "deny"
        if "web" not in caps:
            perm["webfetch"] = "deny"
        if "delegate" not in caps:
            perm["task"] = "deny"
        fm = {"description": agent["description"], "mode": "subagent"}
        if override:
            fm["model"] = override
        fm["permission"] = perm
        return f".opencode/agents/{name}.md", frontmatter(fm, body)

    raise ValueError(harness)


# --------------------------------------------------------------------------- skills

def render_skill(skill: dict) -> dict[str, str]:
    base = f".agents/skills/{skill['name']}"
    body = skill["body"].strip()
    refs = skill["references"]
    missing = [r for r in refs if f"references/{r['path']}" not in body]
    if missing:
        body += "\n\n## References\n\n" + "\n".join(
            f"- [references/{r['path']}](references/{r['path']}) — {r.get('when', 'read when you need the details')}"
            for r in missing
        )
    fm = {"name": skill["name"], "description": skill["description"], "metadata": {"generated-by": GENERATOR}}
    files = {f"{base}/SKILL.md": frontmatter(fm, body)}
    for r in refs:
        files[f"{base}/references/{r['path']}"] = r["content"].rstrip() + "\n"
    for sc in skill["scripts"]:
        files[f"{base}/scripts/{sc['path']}"] = sc["content"].rstrip() + "\n"
    return files


def render_orchestrator(bp: dict) -> dict[str, str]:
    orch = bp["orchestrator"]
    fm = {"name": orch["name"], "description": orch["description"]}
    if orch.get("argument_hint"):
        fm["argument-hint"] = orch["argument_hint"]
    if orch["manual_only"]:
        fm["disable-model-invocation"] = True
    fm["metadata"] = {"generated-by": GENERATOR, "role": "orchestrator"}
    return {f".agents/skills/{orch['name']}/SKILL.md": frontmatter(fm, orchestrator_body(bp))}


# --------------------------------------------------------------------------- MCP snippets

def _swap_refs(value, fmt: str):
    if isinstance(value, str):
        return VAR_REF_RE.sub(lambda m: fmt.format(m.group(1)), value)
    if isinstance(value, list):
        return [_swap_refs(v, fmt) for v in value]
    if isinstance(value, dict):
        return {k: _swap_refs(v, fmt) for k, v in value.items()}
    return value


def mcp_snippets(servers: list, harness: str) -> tuple[str, str, str]:
    """Return (target file, language, snippet) for one harness."""
    if harness in ("claude-code", "copilot-cli"):
        conf = {}
        for m in servers:
            if m["transport"] == "http":
                conf[m["name"]] = {"type": "http", "url": m["url"], "headers": m["headers"] or None}
            else:
                conf[m["name"]] = {"command": m["command"], "args": m["args"], "env": m["env"] or None}
        conf = {k: {kk: vv for kk, vv in v.items() if vv is not None} for k, v in conf.items()}
        return ".mcp.json", "json", json.dumps({"mcpServers": conf}, indent=2)
    if harness == "gemini-cli":
        conf = {}
        for m in servers:
            if m["transport"] == "http":
                conf[m["name"]] = {"httpUrl": m["url"], **({"headers": m["headers"]} if m["headers"] else {})}
            else:
                conf[m["name"]] = {"command": m["command"], "args": m["args"], **({"env": m["env"]} if m["env"] else {})}
        return ".gemini/settings.json", "json", json.dumps({"mcpServers": conf}, indent=2)
    if harness == "cursor":
        conf = {}
        for m in servers:
            if m["transport"] == "http":
                conf[m["name"]] = {"url": m["url"], **({"headers": m["headers"]} if m["headers"] else {})}
            else:
                conf[m["name"]] = {"command": m["command"], "args": m["args"], **({"env": m["env"]} if m["env"] else {})}
        return ".cursor/mcp.json", "json", json.dumps({"mcpServers": _swap_refs(conf, "${{env:{}}}")}, indent=2)
    if harness == "opencode":
        conf = {}
        for m in servers:
            if m["transport"] == "http":
                conf[m["name"]] = {"type": "remote", "url": m["url"], **({"headers": m["headers"]} if m["headers"] else {})}
            else:
                conf[m["name"]] = {
                    "type": "local",
                    "command": [m["command"], *m["args"]],
                    **({"environment": m["env"]} if m["env"] else {}),
                }
        snippet = {"$schema": "https://opencode.ai/config.json", "mcp": {"servers": _swap_refs(conf, "{{env:{}}}")}}
        return "opencode.json", "json", json.dumps(snippet, indent=2)
    if harness == "codex":
        out = []
        for m in servers:
            out.append(f"[mcp_servers.{m['name']}]")
            if m["transport"] == "http":
                out.append(f"url = {tstr(m['url'])}")
                plain, from_env = {}, {}
                for k, v in m["headers"].items():
                    bearer = re.fullmatch(r"Bearer \$\{([A-Za-z_][A-Za-z0-9_]*)\}", str(v))
                    whole = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", str(v))
                    if k.lower() == "authorization" and bearer:
                        out.append(f"bearer_token_env_var = {tstr(bearer.group(1))}")
                    elif whole:
                        from_env[k] = whole.group(1)
                    else:
                        plain[k] = v
                if from_env:
                    out.append(f"env_http_headers = {tinline(from_env)}")
                if plain:
                    out.append(f"http_headers = {tinline(plain)}")
            else:
                out.append(f"command = {tstr(m['command'])}")
                out.append("args = [" + ", ".join(tstr(a) for a in m["args"]) + "]")
                passthrough = [k for k, v in m["env"].items() if str(v) == f"${{{k}}}"]
                literal = {k: v for k, v in m["env"].items() if k not in passthrough}
                if passthrough:
                    out.append("env_vars = [" + ", ".join(tstr(k) for k in passthrough) + "]")
                if literal:
                    out.append(f"env = {tinline(literal)}")
            out.append("")
        return ".codex/config.toml", "toml", "\n".join(out).rstrip()
    raise ValueError(harness)


# --------------------------------------------------------------------------- SETUP.md

RUN_HINTS = {
    "claude-code": "In Claude Code: `/{o} {arg}`",
    "copilot-cli": "In Copilot CLI: `/fleet Use the /{o} skill with {arg}` (fleet runs the agents in parallel)",
    "codex": "In Codex: `${o} {arg}`, or ask Codex to use the {o} skill",
    "gemini-cli": "In Gemini CLI: ask Gemini to use the `{o}` skill with {arg}",
    "cursor": "In Cursor: `/{o} {arg}` in Agent chat",
    "opencode": "In OpenCode: ask the agent to use the `{o}` skill with {arg}",
}


def setup_md(bp: dict, harnesses: list, files: list, links: list, copies: bool = False) -> str:
    sysname = bp["system"]["name"]
    out = [f"# Setup: {sysname}", "", bp["system"]["description"].strip(), ""]
    out += [f"Generated by {GENERATOR} for: {', '.join(harnesses)}.", "Edit `blueprint.yaml` and re-render instead of editing generated files.", ""]
    out += ["## Files written", ""]
    out += [f"- `{f}`" for f in sorted(files)]
    if copies:
        out += [f"- `{src}` (copy of `{dst.replace('../../', '')}`; re-render after changes)" for src, dst in links]
    else:
        out += [f"- `{src}` → `{dst}` (symlink)" for src, dst in links]
    requirements = bp["system"].get("requirements") or []
    if requirements:
        out += ["", "## Before you start", "", "Install or prepare these once:", ""]
        out += [f"- {r}" for r in requirements]
    reused = [s for s in bp["skills"] if s.get("install")]
    if reused:
        out += ["", "## Skills to install (reused, not generated)", "", "Review each before installing; skills can run code.", ""]
        for s in reused:
            out += [f"- **{s['name']}** — {s['description']}", f"  ```bash\n  {s['install']}\n  ```"]
    servers = bp["mcp_servers"]
    if servers:
        out += ["", "## MCP servers", "", "Nothing below has been installed. Approve each server, then merge the snippet for your harness into the named file (keep existing entries).", ""]
        for m in servers:
            refs = sorted(set(VAR_REF_RE.findall(json.dumps(m))))
            line = f"- **{m['name']}** ({m['transport']}) — {m.get('why', '')}"
            if m.get("docs"):
                line += f" Docs: {m['docs']}"
            out.append(line)
            if refs:
                out.append(f"  Needs: {', '.join(f'`{r}`' for r in refs)}")
        secrets = sorted({r for m in servers for r in VAR_REF_RE.findall(json.dumps(m))})
        if secrets:
            out += ["", "Export these in your shell or secret manager; never paste values into config files:", "", "```bash"]
            out += [f"export {s}=..." for s in secrets]
            out += ["```"]
        seen_targets = set()
        for h in harnesses:
            target, lang, snippet = mcp_snippets(servers, h)
            key = (target, snippet)
            if key in seen_targets:
                continue
            seen_targets.add(key)
            users = [x for x in harnesses if mcp_snippets(servers, x)[:1] == (target,)]
            out += ["", f"### {', '.join(users)} → `{target}`", "", f"```{lang}", snippet, "```"]
        if "opencode" in harnesses:
            out += ["", "OpenCode v1 configs put servers directly under `mcp` (no `servers` level)."]
        if "codex" in harnesses and any(m["transport"] == "stdio" and m["env"] for m in servers):
            out += ["", "Codex: `env_vars` forwards variables from your shell; check `codex mcp --help` if your version differs."]
    orch = bp.get("orchestrator")
    if orch:
        arg = orch.get("argument_hint") or "<input>"
        out += ["", "## Run it", ""]
        out += ["- " + RUN_HINTS[h].format(o=orch["name"], arg=arg) for h in harnesses]
        out += ["", "Start small: one input and a single wave, check the output, then scale up."]
    out += ["", "Restart the harness (or reload skills/agents) after rendering so it picks up new files."]
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("blueprint")
    ap.add_argument("--out", required=True, help="Project root to write into.")
    ap.add_argument("--harness", help="'all' or comma-separated list. Default: system.harnesses.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Overwrite files not created by a previous render.")
    ap.add_argument("--no-symlinks", action="store_true", help="Copy skills into .claude/skills instead of symlinking.")
    args = ap.parse_args(argv)

    try:
        bp = load_blueprint(args.blueprint)
    except (BlueprintError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    errors, warnings = check_blueprint(bp)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print("Blueprint has errors; nothing rendered.", file=sys.stderr)
        return 1

    if args.harness in (None, ""):
        harnesses = bp["system"]["harnesses"]
    elif args.harness == "all":
        harnesses = list(HARNESSES)
    else:
        harnesses = [h.strip() for h in args.harness.split(",") if h.strip()]
    bad = [h for h in harnesses if h not in HARNESSES]
    if bad:
        print(f"error: unknown harness {', '.join(bad)}", file=sys.stderr)
        return 2

    servers = {m["name"]: m for m in bp["mcp_servers"]}
    files: dict[str, str] = {}
    render_warnings: list[str] = []
    generated_skills = [s for s in bp["skills"] if not s.get("install")]
    for s in generated_skills:
        files.update(render_skill(s))
    if bp.get("orchestrator"):
        files.update(render_orchestrator(bp))
    for h in harnesses:
        for a in bp["agents"]:
            path, content = render_agent(a, h, servers, render_warnings)
            files[path] = content

    skill_names = [s["name"] for s in generated_skills] + ([bp["orchestrator"]["name"]] if bp.get("orchestrator") else [])
    links = []
    if "claude-code" in harnesses:
        for n in skill_names:
            links.append((f".claude/skills/{n}", f"../../.agents/skills/{n}"))

    sysdir = f".agent-architect/{bp['system']['name']}"
    setup_path = f"{sysdir}/SETUP.md"
    files[setup_path] = setup_md(bp, harnesses, list(files), links, copies=args.no_symlinks)

    out = Path(args.out).resolve()
    manifest_path = out / sysdir / "manifest.json"
    previous = set()
    if manifest_path.exists():
        previous = set(json.loads(manifest_path.read_text(encoding="utf-8")).get("files", []))

    managed = set(files) | {src for src, _ in links}
    conflicts = []
    for rel in managed:
        p = out / rel
        if (p.exists() or p.is_symlink()) and rel not in previous:
            if p.is_symlink() and rel in dict(links) and Path(os.readlink(p)) == Path(dict(links)[rel]):
                continue
            if p.is_file() and rel in files and p.read_text(encoding="utf-8", errors="replace") == files[rel]:
                continue
            conflicts.append(rel)
    if conflicts and not args.force:
        print("error: these files exist and were not created by this system's previous render:", file=sys.stderr)
        for c in sorted(conflicts):
            print(f"  {c}", file=sys.stderr)
        print("Move them, rename the agent/skill, or re-run with --force after checking.", file=sys.stderr)
        return 1

    stale = sorted(previous - managed)
    for w in render_warnings:
        print(f"note: {w}", file=sys.stderr)

    if args.dry_run:
        for rel in sorted(files):
            print(f"would write {rel}")
        for src, dst in links:
            print(f"would link  {src} -> {dst}")
        for rel in stale:
            print(f"would remove {rel} (no longer in blueprint)")
        return 0

    for rel in stale:
        p = out / rel
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        print(f"removed {rel}")

    for rel, content in sorted(files.items()):
        p = out / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_symlink():
            p.unlink()
        p.write_text(content, encoding="utf-8")
        if p.suffix in (".py", ".sh"):
            p.chmod(0o755)
        print(f"wrote {rel}")

    for src, dst in links:
        p = out / src
        p.parent.mkdir(parents=True, exist_ok=True)
        if p.is_symlink() or p.is_file():
            p.unlink()
        elif p.is_dir():
            shutil.rmtree(p)
        target = (p.parent / dst).resolve()
        if args.no_symlinks:
            shutil.copytree(target, p)
            print(f"copied {src}")
            continue
        try:
            p.symlink_to(Path(dst), target_is_directory=True)
            print(f"linked {src} -> {dst}")
        except OSError:
            shutil.copytree(target, p)
            print(f"copied {src} (symlinks unavailable)")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"generator": GENERATOR, "harnesses": harnesses, "files": sorted(managed)}, indent=2) + "\n", encoding="utf-8")
    print(f"\nDone. Next: python3 {Path(__file__).parent / 'validate.py'} --out {args.out}")
    print(f"Then review {setup_path} with the user before enabling any MCP server.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
