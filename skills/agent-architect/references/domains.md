# Domain packs

A domain pack tells you how a field works — roles, workflows, vocabulary, tools, risks —
and which questions an expert in it would ask. Packs come from the domain-scout project
(github.com/keyanjavanshir/domain-scout). Use one whenever the request belongs to a field
with a pack; it is the difference between a generic design and one a practitioner trusts.

## Contents
- Finding a pack
- Loading it
- Using it in each phase
- When there is no pack

## Finding a pack

Packs live in, in priority order:

1. `.agent-architect/domains/<name>/` in the user's project — project packs and overlays.
2. `.agent-architect/domain-scout/domains/` — a local clone of domain-scout.

If neither exists, offer to clone domain-scout into the project. Ask first; it downloads
from GitHub and adds a folder:

```bash
git clone --depth 1 https://github.com/keyanjavanshir/domain-scout .agent-architect/domain-scout
```

Suggest adding `.agent-architect/domain-scout/` to `.gitignore`. Then match the request,
in the user's own words:

```bash
python3 scripts/find_pack.py "<the user's request>"
```

It ranks packs by keyword hits and shows each pack's status, date and overlay. Load the top
pack; load a second only if it scores close and covers a different side of the work (e.g.
film and marketing). Tell the user which pack you loaded, and if it is a `draft` or its
`checked` date is over 180 days old, say so.

## Loading it

Read, in this order: the pack's `DOMAIN.md`, then the project's `OVERLAY.md` for that pack
if there is one. Read the pack's references when their phase comes:
`references/questions.md` in the interview, `references/tools.md` when reusing before
building, `references/patterns.md` when writing the blueprint.

**The overlay wins.** Where the overlay and the pack disagree, the overlay describes how
this team actually works.

## Using it in each phase

**Take stock.** Use the pack's vocabulary from here on. Treat every fact in the overlay as
already answered: state it as an assumption instead of asking.

**Smallest-system test.** The pack's patterns name a level for each team. Use it as your
first recommendation, but still apply the test to this user's request.

**Interview.** Merge the pack's questions into the design tree, branch by branch. For each
one: skip it if the overlay or an earlier answer settles it; otherwise ask it, with the
pack's recommendation adjusted to what you know about this user. Pack questions come before
generic ones in the same branch; they are more specific.

**Reuse before you build.** Start from the pack's `tools.md`. Use its official MCP servers
first, re-check anything older than its `Checked` date with `scripts/mcp_search.py`, and
treat "none found" as a cue for an API or file export, not as a gap to fill.

**Blueprint.** Shape agents after the pack's teams and expert roles; avoid its
anti-patterns. Every irreversible action the pack names becomes a checkpoint, and every
"never" becomes a rule in the relevant agent briefs.

**Playback.** Add one line: which pack and overlay shaped the design.

**Decision log.** Record the pack name and its `checked` date in `decisions.md`.

## When there is no pack

Continue with the generic interview. If the domain-scout skill is installed, offer it: it
interviews the user about their field and writes a pack, which you can then load. Do not
write a pack yourself inside agent-architect.
