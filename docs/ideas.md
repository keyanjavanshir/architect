# Ideas for v0.2

Captured 2026-11-20 from the owner, with design notes. Nothing here is built yet.
Suggested order: **1 → 2**. Idea 3 was dropped on 2026-11-20 (see below).

---

## 1. Show the design, then grill it, before generating

**Idea.** Before the system is generated, the architect draws the workflow and describes
its expected behaviour, then interviews the user on it — "is this what you intended?" —
in the spirit of Matt Pocock's grill-me and Addy Osmani's interview-me.

**Why.** A design table is easy to approve without really reading it. A picture of the flow
plus a concrete walk-through of one run exposes misunderstandings (wrong order, missing
checkpoint, an agent doing too much) while they are still cheap to fix.

**Design sketch**
- New phase between "write the blueprint" and "render": **design review**.
- `scripts/diagram.py` derives a graph from the blueprint (input → preparation → waves →
  checkpoints → output, with each agent's tools, MCP servers and owned files). Generated
  from the blueprint, so it can never drift from what gets rendered.
- Drawing: if Cathryn Lavery's
  [diagram-design](https://github.com/cathrynlavery/diagram-design) skill (MIT, works in
  the same harnesses) is installed, hand it the graph for an editorial HTML/SVG diagram.
  Otherwise fall back to Mermaid. Reference it as a recommended companion skill; do not
  vendor its files.
- **Expected-behaviour walk-through**: one realistic input traced step by step — who runs,
  in parallel with whom, what each returns, where the user is asked, what the final output
  looks like — plus 2–3 failure scenarios (a unit fails, input is huge, a checkpoint is
  declined).
- Then **grill the behaviour**: one question per step or scenario, each with a recommended
  answer. Changes go back into the blueprint, the diagram is regenerated, and the review
  repeats only for what changed.
- Save `design.html` (or `.md` with Mermaid) and `behavior.md` in
  `.agent-architect/<system>/`; record the sign-off in `decisions.md`.

**Open questions**
- Keep the interview built in (no dependency), or delegate to `interview-me` / `grill-me`
  when they are installed? Mixing two interview styles in one session may confuse the user.
- Should the walk-through be a real dry run (agents invoked with a "plan only, do not act"
  flag) or narrated by the architect? A real dry run is more honest but costs more.

**Done when** the user cannot reach `render.py` without having seen a diagram and a
walk-through of the current blueprint and answered yes.

---

## 2. Domain experts: knowing the industry, its tools and its habits

**Idea.** The architect knows what matters in different fields — software, business,
design, creative, and so on — so it understands the industry, its tool ecosystem and how
people work there. When no expert exists for a field, a separate skill researches the field
and generates one.

**Why.** The generic interview asks good structural questions but not domain ones. A
marketing workflow needs questions about brand voice, approval chains and channels; a
finance one about audit trails and period close. Knowing the domain's usual tools also makes
the MCP and skill recommendations far better.

**Design sketch — "domain packs"**
- One pack per domain, same shape every time:
  - `DOMAIN.md` (≤ 200 lines): typical workflows, roles, vocabulary, what "good" looks
    like, common risks and compliance concerns.
  - `references/tools.md`: the usual tools and SaaS, mapped to MCP servers, CLIs and auth
    patterns.
  - `references/questions.md`: domain-specific interview questions to add to the design tree.
  - `references/patterns.md`: agent teams that work well in this domain, and expert roles
    worth turning into agents (e.g. a brand-voice reviewer).
  - `sources.md` with links and a `checked:` date.
- Starter packs: software engineering, business operations (sales, support, finance),
  product and design, creative and marketing, research and analysis.
- In "take stock", the architect classifies the request and loads the matching pack(s); a
  workflow can span two domains (marketing + data).
- **`domain-scout` skill** for missing domains: researches the field (web, MCP registry,
  skill registries), writes a pack in the same format with sources, marks it
  `status: draft` until the user reviews it, and saves it to `.agent-architect/domains/`
  (project) or the user's skills folder. Reviewed packs can be contributed back by PR.

**Open questions**
- Packs as separate installable skills (`architect-domain-marketing`) or as references
  inside agent-architect? Separate skills install and update independently but add
  descriptions to every session; they would need `disable-model-invocation` or very narrow
  descriptions.
- How to keep packs fresh: re-scout when `checked:` is older than N months?
- Quality bar for generated packs: required source count, user review before first use,
  paraphrase only (no copied text).

**Decision (2026-11-20): separate repository** —
[keyanjavanshir/domain-scout](https://github.com/keyanjavanshir/domain-scout), started with a
`creative-direction-film` pack. Packs and `domain-scout` live in their own
repo; agent-architect fetches only the pack(s) a request needs and falls back to its generic
interview when offline. Packs then version, grow and take contributions independently.

**Prior art to draw ideas from (ideas only, no copied text; credit in CREDITS.md):**
- [anthropics/knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins)
  (Apache-2.0): one package per role, each bundling its connectors (`.mcp.json`) — a model
  for `tools.md` as ready connector config. "Generic until customized" suggests a
  project-level overlay (company terms, approval chains) on top of a shared pack. Its
  plugin-management plugin fills packs from a template, as domain-scout would.
- [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) (MIT):
  one repo with per-domain bundles installed separately — answers the "separate skills vs
  references" question without one repo per domain. Its interview question bank and sector
  playbooks match `questions.md` and `patterns.md`; `book-to-skill` suggests domain-scout
  should also ingest the user's own documents, not only the web.
- Awesome lists (e.g. VoltAgent/awesome-agent-skills): discovery sources for the scout, so a
  pack can list existing skills to `install:` instead of regenerating them.
- Research on skill generation (CoEvoSkills, SkillGen): pair the generator with a verifier,
  and test a pack by running the same interview with and without it — a pack earns its
  place only if the questions and tool suggestions get better.

The difference from all of these: they are experts that *do the work* in a domain; packs
here *inform the design* of a system for that domain. Nothing found does that.

**Done when** a request in a domain with no pack produces a draft pack with sources, the
interview visibly uses its questions, and its tool map drives the MCP suggestions.

---

## 3. Recommend models and effort — dropped

**Dropped 2026-11-20.** Recommending a model per agent means knowing which models each
user's harness and plan offer today, and that changes faster than the generator does. The
generator should outlive any model lineup, so it stays out of model choice. The existing
`model` tier and per-harness `models` override remain as they are.

---

## When building these

- Add each newly used project to `CREDITS.md` (diagram-design, interview-me).
- Each idea changes the blueprint schema or the phases: update `SKILL.md`,
  `references/blueprint.md`, the validator and the tests together.
