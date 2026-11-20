# Credits

agent-architect combines ideas from these projects and write-ups. No text or code was
copied from them; each idea was re-expressed for this project. Their licenses apply to
their own work. Please give them a star.

| Source | Idea used here |
|---|---|
| [mattpocock/skills — grill-me](https://github.com/mattpocock/skills) (MIT) | Interview the user relentlessly, walking the design tree branch by branch, giving a recommended answer for each question and exploring the codebase instead of asking. |
| [Anthropic — skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) and [anthropics/skills](https://github.com/anthropics/skills) | Progressive disclosure, short SKILL.md, references one level deep, scripts for deterministic work, descriptions that say what *and* when. |
| [Agent Skills specification](https://agentskills.io/specification) | The portable SKILL.md format and naming rules. |
| [GitHub — Run multiple agents at once with /fleet](https://github.blog/ai-and-ml/github-copilot/run-multiple-agents-at-once-with-fleet-in-copilot-cli/) | File ownership for parallel sub-agents, self-contained sub-agent prompts, dispatch in waves. |
| [alirezarezvani/claude-code-skill-factory](https://github.com/alirezarezvani/claude-code-skill-factory) | A guided "factory" that asks a few questions and generates agents and skills. |
| [lensetek/skillforge — agent-forge](https://www.skills.sh/lensetek/skillforge/agent-forge) | A meta-agent that interviews first, then designs sub-agents and their skills. |
| [bradygaster/squad — agentic-workflow-designer](https://tessl.io/registry/skills/github/bradygaster/squad/agentic-workflow-designer) | One-question-at-a-time interview that ends in a single workflow file. |
| [vercel-labs/skills](https://github.com/vercel-labs/skills) | `.agents/skills/` as the shared skill location, with symlinks for Claude Code. |
| [Model Context Protocol registry](https://registry.modelcontextprotocol.io) | Discovering MCP servers by keyword. |
| Claude Code, Copilot CLI, Codex, Gemini CLI, Cursor and OpenCode documentation | Agent, skill and MCP file formats per harness. |
