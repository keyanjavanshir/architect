# Tools and MCP servers

## Step 1: map needs to capabilities

Built-in capabilities, mapped to each harness by the renderer:

| Capability | Covers |
|---|---|
| `read` | Read files in the workspace. |
| `search` | Find files and grep contents. |
| `edit` | Create and modify files (requires `owns`). |
| `shell` | Run commands: tests, linters, git, CLIs. |
| `web` | Search the web and fetch URLs. |
| `delegate` | Spawn other agents. Orchestrator-only by default. |

Prefer a built-in capability over an MCP server when it is enough: `shell` + the `gh` CLI
covers most GitHub reads, `web` covers public docs. Add MCP when the system needs
authenticated APIs, structured data, a browser, or write access that a CLI does not give.

## Step 2: find a server

```bash
python3 scripts/mcp_search.py "jira"            # top matches from the official registry
python3 scripts/mcp_search.py "jira" --yaml     # blueprint-ready mcp_servers entries
```

The script calls `https://registry.modelcontextprotocol.io/v0.1/servers?search=…`. Choose by:

1. Published by the vendor itself (namespace matches the vendor's domain or GitHub org).
2. A hosted remote (`transport: http`) over a local package when both exist: nothing to
   install, and OAuth is often handled by the harness.
3. Recent version, a linked repository, and documented environment variables.

If the registry has nothing, the network is blocked, or results look unmaintained, say so
and ask the user for the server they trust. Do not invent package names or URLs.

## Step 3: scope and credentials

- Attach each server only to the agents that need it (`mcp:` per agent).
- Prefer read-only tokens and read-only server modes for agents that only read.
- Write every secret as `${VAR}`; never copy a token into any file. SETUP.md lists the
  variables to export.
- Note OAuth-only servers in `why:` so SETUP.md tells the user to sign in first.

## Step 4: enabling — proposal, not action

Installing an MCP server runs third-party code with the user's credentials. So:

1. The renderer writes snippets for each target harness into SETUP.md. It does not touch
   any MCP config file.
2. Show the user the exact snippet and target file, e.g. `.mcp.json` (Claude Code,
   Copilot CLI), `.codex/config.toml`, `.gemini/settings.json`, `.cursor/mcp.json`,
   `opencode.json`.
3. Only after an explicit yes, merge the snippet into that file, preserving everything
   already there. Project files only, unless the user asks for user-level config.
4. Where the harness has a CLI for it (`claude mcp add`, `codex mcp add`,
   `gemini mcp add`, `opencode mcp add`), you may run that instead, still only after a yes.

## Plugins and existing skills

When an existing skill or plugin covers a capability, list it in the blueprint with
`install:` and its install command (`npx skills add owner/repo --skill name`,
`gh skill install …`, `claude plugin install …`). Running install commands is also
proposal-first.
