"""Tests for the agent-architect scripts. Run: python3 -m unittest discover -s tests"""

from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import tomllib
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "agent-architect" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import blueprint_lib  # noqa: E402
import mcp_search  # noqa: E402
import render  # noqa: E402
import validate  # noqa: E402

EXAMPLES = sorted((ROOT / "examples").glob("*/blueprint.yaml"))


def run(fn, argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = fn(argv)
    return code, out.getvalue(), err.getvalue()


def load(path):
    return blueprint_lib.normalize(yaml.safe_load(Path(path).read_text()))


def write_bp(tmp: Path, bp: dict) -> Path:
    p = tmp / "blueprint.yaml"
    p.write_text(yaml.safe_dump(bp, sort_keys=False))
    return p


class ExampleBlueprints(unittest.TestCase):
    def test_examples_exist(self):
        self.assertGreaterEqual(len(EXAMPLES), 2)

    def test_examples_are_clean(self):
        for bp_path in EXAMPLES:
            errors, warnings = blueprint_lib.check_blueprint(load(bp_path))
            self.assertEqual(errors, [], bp_path)
            self.assertEqual(warnings, [], bp_path)

    def test_render_all_harnesses_and_validate(self):
        for bp_path in EXAMPLES:
            with tempfile.TemporaryDirectory() as tmp:
                code, _, err = run(render.main, [str(bp_path), "--out", tmp, "--harness", "all"])
                self.assertEqual(code, 0, err)
                code, out, _ = run(validate.main, ["--out", tmp, "--strict"])
                self.assertEqual(code, 0, out)
                self._parse_everything(Path(tmp))

    def _parse_everything(self, root: Path):
        for f in root.rglob("*.md"):
            if f.parent.name == "references" or ".agent-architect" in f.parts:
                continue
            fm, body, problem = validate.split_frontmatter(f.read_text())
            self.assertIsNone(problem, f)
            self.assertTrue(fm.get("description"), f)
            self.assertTrue(body.strip(), f)
        for f in root.rglob("*.toml"):
            data = tomllib.loads(f.read_text())
            for key in ("name", "description", "developer_instructions"):
                self.assertIn(key, data, f)

    def test_committed_renders_are_current(self):
        for bp_path in EXAMPLES:
            committed = bp_path.parent / "rendered"
            with tempfile.TemporaryDirectory() as tmp:
                run(render.main, [str(bp_path), "--out", tmp, "--harness", "all"])
                for f in Path(tmp).rglob("*"):
                    if f.is_file() and not f.is_symlink() and "/.claude/skills/" not in str(f):
                        rel = f.relative_to(tmp)
                        self.assertTrue((committed / rel).is_file(), f"missing {rel}; re-render examples")
                        self.assertEqual(f.read_text(), (committed / rel).read_text(), f"{rel} is stale; re-render examples")


class RenderBehaviour(unittest.TestCase):
    def setUp(self):
        self.bp = load(ROOT / "examples" / "pr-review" / "blueprint.yaml")

    def test_skills_written_once_and_linked_for_claude(self):
        with tempfile.TemporaryDirectory() as tmp:
            run(render.main, [str(EXAMPLES[1]), "--out", tmp, "--harness", "claude-code,codex"])
            root = Path(tmp)
            self.assertTrue((root / ".agents/skills/review-rubric/SKILL.md").is_file())
            link = root / ".claude/skills/review-rubric"
            self.assertTrue(link.is_symlink())
            self.assertTrue((link / "SKILL.md").is_file())
            self.assertFalse((root / ".gemini").exists())

    def test_no_claude_links_without_claude(self):
        with tempfile.TemporaryDirectory() as tmp:
            run(render.main, [str(EXAMPLES[1]), "--out", tmp, "--harness", "copilot-cli"])
            self.assertFalse((Path(tmp) / ".claude").exists())

    def test_rerender_is_idempotent_and_removes_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            bp_path = write_bp(t, copy.deepcopy(self.bp))
            out = t / "proj"
            self.assertEqual(run(render.main, [str(bp_path), "--out", str(out), "--harness", "all"])[0], 0)
            self.assertEqual(run(render.main, [str(bp_path), "--out", str(out), "--harness", "all"])[0], 0)
            bp = copy.deepcopy(self.bp)
            bp["agents"] = [a for a in bp["agents"] if a["name"] != "docs-reviewer"]
            bp["orchestrator"]["waves"][0]["agents"].remove("docs-reviewer")
            bp_path = write_bp(t, bp)
            code, out_text, err = run(render.main, [str(bp_path), "--out", str(out), "--harness", "all"])
            self.assertEqual(code, 0, err)
            self.assertFalse((out / ".claude/agents/docs-reviewer.md").exists())
            self.assertIn("removed .claude/agents/docs-reviewer.md", out_text)

    def test_refuses_to_overwrite_foreign_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = Path(tmp) / ".claude/agents/security-reviewer.md"
            agent.parent.mkdir(parents=True)
            agent.write_text("---\nname: security-reviewer\ndescription: mine\n---\nhand written\n")
            code, _, err = run(render.main, [str(EXAMPLES[1]), "--out", tmp, "--harness", "claude-code"])
            self.assertEqual(code, 1)
            self.assertIn("security-reviewer.md", err)
            self.assertIn("hand written", agent.read_text())

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = run(render.main, [str(EXAMPLES[1]), "--out", tmp, "--harness", "all", "--dry-run"])
            self.assertEqual(code, 0)
            self.assertIn("would write", out)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_claude_mcp_agent_uses_denylist(self):
        a = next(x for x in self.bp["agents"] if x["name"] == "review-publisher")
        _, text = render.render_agent(a, "claude-code", {}, [])
        fm, _, _ = validate.split_frontmatter(text)
        self.assertNotIn("tools", fm)
        self.assertIn("Bash", fm["disallowedTools"])
        self.assertEqual(fm["mcpServers"], ["github"])

    def test_capability_mapping(self):
        a = next(x for x in self.bp["agents"] if x["name"] == "test-reviewer")
        fm = validate.split_frontmatter(render.render_agent(a, "copilot-cli", {}, [])[1])[0]
        self.assertEqual(fm["tools"], ["read", "search", "execute"])
        fm = validate.split_frontmatter(render.render_agent(a, "claude-code", {}, [])[1])[0]
        self.assertEqual(fm["tools"], "Read, Grep, Glob, Bash")
        self.assertEqual(fm["model"], "sonnet")
        toml = tomllib.loads(render.render_agent(a, "codex", {}, [])[1])
        self.assertEqual(toml["model_reasoning_effort"], "medium")
        self.assertNotIn("features", toml)  # has shell
        docs = next(x for x in self.bp["agents"] if x["name"] == "docs-reviewer")
        toml = tomllib.loads(render.render_agent(docs, "codex", {}, [])[1])
        self.assertFalse(toml["features"]["shell_tool"])
        fm = validate.split_frontmatter(render.render_agent(docs, "cursor", {}, [])[1])[0]
        self.assertTrue(fm["readonly"])

    def test_yaml_scalars_round_trip(self):
        for value in ["plain text", "has: colon", "yes", "- dash", "#hash", "1.0", "quote \"x\"", "émoji ✓", "a, b"]:
            parsed = yaml.safe_load(f"k: {render.yscalar(value)}")
            self.assertEqual(parsed["k"], value)

    def test_toml_multiline_with_triple_quotes(self):
        s = "line\n'''tricky'''\n\"\"\""
        self.assertEqual(tomllib.loads("x = " + render.tmultiline(s))["x"], s)

    def test_mcp_snippets_parse(self):
        servers = self.bp["mcp_servers"] + [{
            "name": "browser", "transport": "stdio", "command": "npx",
            "args": ["-y", "@playwright/mcp@latest"], "env": {"API_KEY": "${API_KEY}"}, "headers": {},
        }]
        for h in blueprint_lib.HARNESSES:
            target, lang, snippet = render.mcp_snippets(servers, h)
            if lang == "json":
                json.loads(snippet)
            else:
                data = tomllib.loads(snippet)
                self.assertEqual(data["mcp_servers"]["github"]["bearer_token_env_var"], "GITHUB_TOKEN")
                self.assertEqual(data["mcp_servers"]["browser"]["env_vars"], ["API_KEY"])
        self.assertIn("${env:GITHUB_TOKEN}", render.mcp_snippets(servers, "cursor")[2])
        self.assertIn("{env:GITHUB_TOKEN}", render.mcp_snippets(servers, "opencode")[2])


class BlueprintChecks(unittest.TestCase):
    def setUp(self):
        self.bp = load(ROOT / "examples" / "pr-review" / "blueprint.yaml")

    def errors(self, bp):
        return blueprint_lib.check_blueprint(blueprint_lib.normalize(bp))[0]

    def test_overlapping_owners_in_one_wave(self):
        bp = copy.deepcopy(self.bp)
        for a in bp["agents"]:
            if a["name"] in ("security-reviewer", "test-reviewer"):
                a["capabilities"].append("edit")
                a["owns"] = [".review/*.md"] if a["name"] == "security-reviewer" else [".review/out.md"]
        self.assertTrue(any("must not overlap" in e for e in self.errors(bp)))

    def test_for_each_needs_item_placeholder(self):
        bp = load(ROOT / "examples" / "competitor-research" / "blueprint.yaml")
        bp["agents"][0]["owns"] = ["research/companies/all.md"]
        self.assertTrue(any("{item}" in e for e in self.errors(bp)))

    def test_literal_secret_rejected(self):
        bp = copy.deepcopy(self.bp)
        bp["mcp_servers"][0]["headers"]["Authorization"] = "Bearer ghp_" + "a" * 36
        self.assertTrue(any("literal secret" in e for e in self.errors(bp)))

    def test_secret_key_needs_reference(self):
        bp = copy.deepcopy(self.bp)
        bp["mcp_servers"][0]["env"] = {"API_TOKEN": "abc"}
        self.assertTrue(any("API_TOKEN" in e for e in self.errors(bp)))

    def test_edit_requires_owns(self):
        bp = copy.deepcopy(self.bp)
        bp["agents"][0]["capabilities"].append("edit")
        self.assertTrue(any("no 'owns'" in e for e in self.errors(bp)))

    def test_long_prompt_rejected(self):
        bp = copy.deepcopy(self.bp)
        bp["agents"][0]["prompt"] = "line\n" * 90
        self.assertTrue(any("max 80" in e for e in self.errors(bp)))

    def test_bad_names_and_refs(self):
        bp = copy.deepcopy(self.bp)
        bp["agents"][0]["name"] = "Security_Reviewer"
        bp["agents"][1]["mcp"] = ["jira"]
        errs = self.errors(bp)
        self.assertTrue(any("kebab-case" in e for e in errs))
        self.assertTrue(any("'jira'" in e for e in errs))

    def test_nested_reference_path_rejected(self):
        bp = copy.deepcopy(self.bp)
        bp["skills"][0]["references"][0]["path"] = "deep/x.md"
        self.assertTrue(any("plain .md filename" in e for e in self.errors(bp)))

    def test_patterns_overlap(self):
        po = blueprint_lib.patterns_overlap
        self.assertTrue(po("docs/", "docs/a.md"))
        self.assertTrue(po("src/**", "src/x/y.py"))
        self.assertTrue(po("./a.md", "a.md"))
        self.assertFalse(po("reports/a.md", "reports/b.md"))
        self.assertFalse(po("docs-old/x", "docs/"))


class ProjectValidation(unittest.TestCase):
    def test_audit_catches_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude/agents").mkdir(parents=True)
            (root / ".claude/agents/empty.md").write_text("---\nname: empty\ndescription: x\n---\n")
            sk = root / ".agents/skills/Bad_Name"
            sk.mkdir(parents=True)
            (sk / "SKILL.md").write_text("---\nname: Bad_Name\ndescription: d\n---\nSee [x](references/missing.md)\n")
            (root / ".codex/agents").mkdir(parents=True)
            (root / ".codex/agents/a.toml").write_text('name = "a"\n')
            code, out, _ = run(validate.main, ["--out", tmp])
            self.assertEqual(code, 1)
            self.assertIn("empty prompt body", out)
            self.assertIn("kebab-case", out)
            self.assertIn("missing file", out)
            self.assertIn("developer_instructions", out)


class McpSearch(unittest.TestCase):
    SAMPLE = {
        "servers": [
            {
                "server": {
                    "name": "io.github.github/github-mcp-server",
                    "description": "GitHub's official MCP server",
                    "version": "1.2.0",
                    "repository": {"url": "https://github.com/github/github-mcp-server", "source": "github"},
                    "remotes": [{"type": "streamable-http", "url": "https://api.githubcopilot.com/mcp/",
                                 "headers": [{"name": "Authorization", "isSecret": True}]}],
                },
                "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active", "isLatest": True}},
            },
            {
                "server": {
                    "name": "io.github.example/weather",
                    "version": "0.3.1",
                    "packages": [{"registryType": "npm", "identifier": "@example/weather-mcp", "version": "0.3.1",
                                  "transport": {"type": "stdio"},
                                  "environmentVariables": [{"name": "WEATHER_API_KEY", "isSecret": True}]}],
                },
                "_meta": {},
            },
            {"server": {"name": "io.github.old/gone"}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "deleted"}}},
        ],
        "metadata": {"count": 3},
    }

    def test_parse_and_entries_pass_blueprint_checks(self):
        results = mcp_search.parse(self.SAMPLE)
        self.assertEqual(len(results), 2)
        entries = [mcp_search.to_entry(r["server"]) for r in results]
        self.assertEqual(entries[0]["transport"], "http")
        self.assertEqual(entries[0]["name"], "github")
        self.assertEqual(entries[1]["args"], ["-y", "@example/weather-mcp@0.3.1"])
        self.assertEqual(entries[1]["env"], {"WEATHER_API_KEY": "${WEATHER_API_KEY}"})
        bp = load(ROOT / "examples" / "pr-review" / "blueprint.yaml")
        bp["mcp_servers"] = entries
        bp["agents"][-1]["mcp"] = [e["name"] for e in entries]
        errors = blueprint_lib.check_blueprint(blueprint_lib.normalize(bp))[0]
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
