# Harness reference

What the renderer writes for each harness, and the quirks behind its choices.
Formats change; when a harness behaves differently from this table, trust its current docs
and open an issue on this repo.

## Paths

| Harness | Agents | Skills read from | MCP config (project) |
|---|---|---|---|
| `claude-code` | `.claude/agents/<n>.md` | `.claude/skills/` | `.mcp.json` (`mcpServers`) |
| `copilot-cli` | `.github/agents/<n>.agent.md` | `.agents/skills/`, `.github/skills/`, `.claude/skills/` | `.mcp.json` (`mcpServers`); user: `~/.copilot/mcp-config.json` |
| `codex` | `.codex/agents/<n>.toml` | `.agents/skills/` | `.codex/config.toml` (`[mcp_servers.<n>]`) |
| `gemini-cli` | `.gemini/agents/<n>.md` | `.agents/skills/`, `.gemini/skills/` | `.gemini/settings.json` (`mcpServers`) |
| `cursor` | `.cursor/agents/<n>.md` | `.agents/skills/`, `.cursor/skills/`, `.claude/skills/` | `.cursor/mcp.json` (`mcpServers`) |
| `opencode` | `.opencode/agents/<n>.md` | `.agents/skills/`, `.opencode/skills/`, `.claude/skills/` | `opencode.json` (`mcp.servers`) |

**Skill layout.** Skills are written once to `.agents/skills/`. Claude Code is the only
target that does not read it, so when Claude Code is targeted the renderer adds relative
symlinks in `.claude/skills/` (or copies with `--no-symlinks`, e.g. on Windows without
developer mode). Harnesses that read both folders see the same files.

## Capability mapping

| Capability | Claude Code | Copilot CLI | Gemini CLI | Codex | Cursor | OpenCode |
|---|---|---|---|---|---|---|
| read | `Read` | `read` | `read_file`, `read_many_files`, `list_directory` | always on | always on | always on |
| search | `Grep`, `Glob` | `search` | `glob`, `grep_search` | always on | always on | always on |
| edit | `Edit`, `Write`, `NotebookEdit` | `edit` | `write_file`, `replace` | prompt rule only | `readonly` if absent | `permission.edit` |
| shell | `Bash` | `execute` | `run_shell_command` | `features.shell_tool` | `readonly` if absent | `permission.bash` |
| web | `WebSearch`, `WebFetch` | `web` | `web_fetch`, `google_web_search` | inherited | inherited | `permission.webfetch` |
| delegate | `Agent` | `agent` | not supported | inherited | inherited | `permission.task` |
| MCP server `x` | `mcpServers: [x]` | `x/*` in `tools` | `mcp_x_*` in `tools` | inherited from session | inherited | inherited |

## Per-harness notes

**Claude Code** — Fields: `name`, `description`, `tools` *or* `disallowedTools`, `model`,
`skills` (preloaded), `mcpServers`, `maxTurns`. Agents without MCP get a `tools` allowlist;
agents with MCP get a `disallowedTools` denylist so MCP tools stay available, plus
`mcpServers` to scope servers. Model tiers map to `haiku`/`sonnet`/`opus`.

**Copilot CLI** — `.agent.md` with `name`, `description`, `tools`, optional `model`.
Prompt body max 30,000 chars. Run the orchestrator under `/fleet` for parallel work. Tiers
are not mapped (model ids vary by plan); set `models: {copilot-cli: …}` to pin one. The
GitHub MCP server is built in (no config needed). Project `.mcp.json` servers load only
after the user trusts the folder.

**Codex** — TOML with required `name`, `description`, `developer_instructions`. Agent files
cannot override sandbox, approvals or MCP servers; those come from the parent session, so
read-only intent is stated in the instructions and `shell` is disabled with
`[features] shell_tool = false`. Tiers map to `model_reasoning_effort` low/medium/high.

**Gemini CLI** — Fields: `name`, `description`, `tools`, `model`, `max_turns`. Sub-agents
cannot call other sub-agents, so `delegate` is dropped with a warning. Tool names beyond
`read_file`, `grep_search` and `run_shell_command` come from Gemini CLI's built-in tool
list; check with `/tools` if an agent reports a missing tool.

**Cursor** — Fields: `name`, `description`, `model`, `readonly`. Cursor also reads
`.claude/agents/` and `.codex/agents/`; `.cursor/agents/` wins on name clashes, so
rendering several harnesses is safe. A file with an empty body is ignored, and Markdown
files nested under `agents/` are picked up as agents.

**OpenCode** — Markdown agents with `description`, `mode: subagent`, optional `model`
(`provider/model`), `permission` map. Uses the v1 `permission` fields, which OpenCode v2
still reads. Tiers are not mapped; set `models: {opencode: …}`.

## Model tiers

| Tier | Claude Code | Codex effort | Others |
|---|---|---|---|
| `inherit` | `inherit` | (unset) | (unset) |
| `fast` | `haiku` | `low` | unset unless `models:` given |
| `balanced` | `sonnet` | `medium` | unset unless `models:` given |
| `strong` | `opus` | `high` | unset unless `models:` given |
