# Interview method

## Contents
- How to ask
- The smallest-system test
- The design tree
- Playback and sign-off

## How to ask

- **One question per turn.** Use the harness's multiple-choice question tool if it has one;
  otherwise number the options in plain text.
- **Lead with your recommendation.** Format: question, 2–4 options, your pick marked
  "(recommended)" with a one-line reason. The user can always answer in their own words.
- **Look before you ask.** If the answer is in the repo, the docs, or a quick search, find it
  and state it as an assumption ("I see you deploy with GitHub Actions, so I'll assume…").
- **Ask for decisions, not essays.** "Should the reviewer be able to edit files?" beats
  "Tell me about your review process."
- **Follow the branch.** Each answer opens or closes sub-questions. Resolve the ones it opens
  before moving to a sibling branch.
- **Keep a decision log** in `.agent-architect/<system>/decisions.md`: one line per decision,
  with the reason. It survives context compaction and explains the design later.
- **Push back** on scope creep and on agents that exist only because they sound good. Every
  agent must own a distinct unit of work or a distinct permission boundary.
- **No question cap**, but if the tree keeps growing after ~25 decisions, the scope is too
  big: propose splitting into two systems and grill one at a time.

## The smallest-system test

Ask early, before you design agents. Climb only as far as the work requires:

0. **No agent.** A script, a local model or a tool the user already has does the job:
   sorting, measuring, converting, matching, building a page. Many "agent" steps are this.
1. **One skill.** The work is sequential and fits in one context → a single skill.
2. **Built-in fan-out.** One large mechanical change across many files → Claude Code
   `/batch` or Copilot CLI `/fleet` with a good plan. Nothing to generate except perhaps a
   skill holding the conventions.
3. **Orchestrator + parallel workers.** Independent units with the same shape (review each
   package, research each competitor) → one orchestrator skill, one worker agent, fan-out.
4. **Pipeline / waves.** Different kinds of work with dependencies (research → draft →
   review) → orchestrator, several agents, waves.

Say which level you recommend and why. Most requests land on 1 or 3.

Then choose the **engine for each step**, cheapest that does the job well:

| The step needs… | Engine |
|---|---|
| A fixed procedure (split, convert, list, build a page) | Script |
| A measurement (sharpness, loudness, tempo, counts) | Script |
| Sorting things into known categories, or "find the one like this" | Local model (e.g. an image or text embedding model), if the user's machine can run it |
| Summaries of many items | Script, or a small model, on files — not a cloud agent reading everything |
| Judgement, taste, writing, choices with trade-offs | Cloud agent, with a compact input |

Ask what hardware the user has (GPU, memory) before ruling local models in or out. A
cloud agent that looks at hundreds of images or reads raw logs is a design smell.

## The design tree

Cover every branch that applies. Skip branches the smallest-system test ruled out.

**Outcome**
- What exists when the run is done (file, PR, report, message, updated ticket)?
- Who consumes it, and how will they judge it good? Get one concrete acceptance check.

**Trigger and inputs**
- On demand, scheduled, or on an event? What does the user type to start it?
- What inputs vary per run (PR number, list of URLs, a folder)? Where do they come from?

**Decomposition**
- What is one unit of work? How many per run (typical and maximum)?
- Which units are independent? Which depend on others' output? → waves.
- Is there a final synthesis step, and who does it (orchestrator or a dedicated agent)?

**Roles** (one pass per agent)
- What expertise or point of view does it need that the main agent lacks?
- Read-only or does it write? Exactly which files or systems does it write to?
- What does it return — format, length, required fields?
- Does it need a stronger or cheaper model than the default?

**Knowledge**
- What does the agent need to know that a capable model does not (conventions, checklists,
  APIs, house style)? Each body of knowledge becomes a skill or a reference file.
- Where does that knowledge live today (docs, wiki, URL, someone's head)?

**Tools and data**
- Which external systems are read or written (GitHub, Jira, Slack, a database, the web,
  a browser)? For each: read or write, and how does the user authenticate today?
- Map each to a capability or MCP server — see tools-and-mcp.md.

**Risk and permissions**
- Which actions are irreversible or visible to others? Each gets a human checkpoint unless
  the user waives it in writing.
- Anything that must never happen (touching prod, emailing customers)? Put it in the brief.

**Verification**
- How is each unit's output checked: tests, a linter, a schema, a reviewer agent, the user?
- What happens when a unit fails: retry once, skip and report, or stop the run?

**Environment**
- Which harnesses must run it? Project-scoped (committed) or personal (home directory)?
- Cost or time budget per run? It caps fan-out width and model choice.

## Playback and sign-off

When no branch is open, present:

1. One sentence: what the system does.
2. A table: agent | owns (files/systems) | reads | capabilities | model tier | returns.
3. Skills to create or install, and MCP servers needed with their credentials.
4. The dispatch plan: waves, checkpoints, failure policy.
5. Open risks or assumptions you made.

Ask for an explicit yes. Changes go back into the tree; re-play only what changed.
