# CLAUDE.md

@AGENTS.md

## What this project is

agent-architect is an Agent Skill (`skills/agent-architect/`) that interviews a user about
a workflow in depth, then generates the multi-agent system to run it: worker agents, the
skills they need, an orchestrator skill that dispatches them in parallel, and MCP setup.
One harness-neutral blueprint (`.agent-architect/<system>/blueprint.yaml`) is rendered by
`scripts/render.py` into files for Claude Code, Copilot CLI (`/fleet`), Codex, Gemini CLI,
Cursor and OpenCode, and checked by `scripts/validate.py`.

It was designed and built in a claude.ai chat on 2026-11-20 (v0.1). This file carries that
conversation's context; read it before changing the design.

## Why it is built this way

- **Interview before generating.** Adapted from Matt Pocock's grill-me: one question at a
  time, a recommended answer for each, explore the repo instead of asking. Plus a
  "smallest-system test": often one skill, `/batch` or `/fleet` is enough.
- **Blueprint + deterministic renderer**, not the model writing per-harness files. Every
  harness has its own agent format; a script gets formats right every time and makes
  adding a harness a code change, not a prompt change.
- **Orchestrator is a skill run by the main session, workers are agents.** The main
  session is the only place every harness can spawn sub-agents (Gemini CLI sub-agents can't
  spawn others; Claude Code caps nesting depth).
- **Skills written once to `.agents/skills/`**, symlinked into `.claude/skills/` for Claude
  Code (the only target that doesn't read `.agents/skills/`). Same convention as
  vercel-labs/skills. Avoids duplicate-skill conflicts in harnesses that read both.
- **Claude Code agents with MCP use `disallowedTools`** (denylist) so MCP tools stay
  available; agents without MCP get a `tools` allowlist.
- **MCP is proposal-only.** `render.py` writes snippets into SETUP.md and never touches
  MCP config. The user approves each change. Secrets are only `${VAR}` references; the
  validator rejects literal tokens.
- **Size limits are enforced by the validator**, not left to the model: generated SKILL.md
  ≤ 200 lines, agent prompts ≤ 80 lines, references one level deep, ≤ 300 lines or with a
  Contents list. Copilot's hard limit is 30,000 chars per agent body.
- **Parallel agents never write the same file.** The validator rejects `owns` overlaps
  inside a wave and `for_each` writers without `{item}` in their paths.
- **No copied text** from the projects we drew on (see CREDITS.md); ideas only.

## Harness facts (checked against vendor docs, November 2026)

Full table: `skills/agent-architect/references/harnesses.md`. Points that drove code:

- Copilot CLI: `.github/agents/*.agent.md`; tool aliases `read, search, edit, execute, web,
  agent`; MCP tools as `server/*`; reads project `.mcp.json` only after folder trust; GitHub
  MCP server is built in.
- Codex: `.codex/agents/*.toml` with required `name`, `description`,
  `developer_instructions`. Agent files can NOT override sandbox, approvals or MCP servers.
- Gemini CLI: `.gemini/agents/*.md`; MCP tools `mcp_<server>_*`; no nested sub-agents.
- Cursor: `.cursor/agents/*.md` (`readonly` field); also reads `.claude/agents` and
  `.codex/agents`; ignores agents with empty bodies; loads nested .md under agents/ as agents.
- OpenCode: `.opencode/agents/*.md` with `mode: subagent`; we emit v1 `permission` fields
  (v2 still reads them); v2 MCP config is `mcp.servers`.
- MCP registry API: `https://registry.modelcontextprotocol.io/v0.1/servers?search=` (v0 fallback).

## Known gaps — the next work, in priority order

1. **No end-to-end run yet in any harness.** Render `examples/pr-review` into a scratch
   repo and run `/review-pr` in Claude Code, then `/fleet` in Copilot CLI, then the rest.
   Fix whatever the real harness disagrees with; record findings in harnesses.md.
2. `mcp_search.py` ran against the live registry on 2026-11-20 and works. Finding: the
   registry lacks some vendors' official servers (Frame.io's is only in its own docs), so a
   "No servers found" result should send the architect to the vendor's docs.
3. Unverified details: Gemini tool names beyond `read_file`/`grep_search`/
   `run_shell_command`; Codex `bearer_token_env_var`, `env_http_headers`, `env_vars`.
4. Model tiers map only for Claude Code (aliases) and Codex (reasoning effort).
5. Ideas deferred from v0.1: packaging as Claude Code / Copilot plugins, evals for
   generated systems, an "extend existing system" flow with diff preview.
6. Owner's v0.2 ideas — design review with diagrams before generating, and domain expert
   packs plus a domain-scout skill (now github.com/keyanjavanshir/domain-scout). Model/effort
   recommendations were considered and dropped. Design notes in [docs/ideas.md](docs/ideas.md).
   Domain packs are wired in: `references/domains.md` (where packs live, how each phase uses
   them; overlay wins over pack) and `scripts/find_pack.py` (keyword match, plurals folded).
   First live test: designing a system for the owner's `creative-direction-event-film` pack.

## Owner

Keyan Javanshir — github.com/keyanjavanshir/architect
