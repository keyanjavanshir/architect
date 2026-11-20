# Ideas for v0.2

Captured 2026-11-20 from the owner, with design notes. Nothing here is built yet.
Suggested order: **3 → 1 → 2** (smallest and most self-contained first).

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

**Done when** a request in a domain with no pack produces a draft pack with sources, the
interview visibly uses its questions, and its tool map drives the MCP suggestions.

---

## 3. Recommend models and effort, never decide

**Idea.** The architect recommends a model type and reasoning effort for each agent, but
leaves the decision to the user.

**Why.** Model choice is the biggest cost and quality lever in a parallel system (cost
multiplies by fan-out width), and the user knows their budget and plan. Today v0.1 takes
the tier from the blueprint and silently maps it to Codex effort, which mixes two decisions.

**Design sketch**
- During playback, show a table per agent: recommended tier and effort, a one-line reason,
  and the cost effect (e.g. "×5 instances per run").
- Heuristics live in a reference: mechanical or high-volume work → fast tier, low effort;
  judgement-heavy review or synthesis → strong tier, higher effort; a publisher behind a
  checkpoint → fast tier.
- Model lineups change quickly: look up the target harness's current models at design time
  instead of hard-coding names; date anything written down.
- Blueprint: add `effort` (`low | medium | high | max`) separate from `model`, and a
  `recommended: {model, effort, reason}` block that is kept even when the user picks
  something else. Defaults stay `inherit` until the user accepts.
- Rendering: Claude Code `effort` frontmatter; Codex `model_reasoning_effort` (drop the
  implicit tier→effort mapping); other harnesses note it in SETUP.md where unsupported.

**Done when** no rendered agent has a model or effort the user did not explicitly accept,
and `decisions.md` records each recommendation next to the choice.

---

## When building these

- Add each newly used project to `CREDITS.md` (diagram-design, interview-me).
- Each idea changes the blueprint schema or the phases: update `SKILL.md`,
  `references/blueprint.md`, the validator and the tests together.
