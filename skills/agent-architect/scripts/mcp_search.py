#!/usr/bin/env python3
"""Search the official MCP registry and print candidates, optionally as blueprint entries.

Usage:
  python3 mcp_search.py KEYWORD [--limit 8] [--yaml] [--json] [--registry URL]

Reads https://registry.modelcontextprotocol.io/v0.1/servers?search=KEYWORD (falls back to /v0).
Respects HTTPS_PROXY and SSL_CERT_FILE. Nothing is installed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_REGISTRY = "https://registry.modelcontextprotocol.io"


def fetch(registry: str, query: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode({"search": query, "limit": limit, "version": "latest"})
    last_exc: Exception | None = None
    for api in ("v0.1", "v0"):
        url = f"{registry.rstrip('/')}/{api}/servers?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "agent-architect"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return parse(json.load(resp))
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code != 404:
                raise
    raise last_exc  # type: ignore[misc]


def parse(data: dict) -> list[dict]:
    """Accept both the wrapped ({server, _meta}) and flat response shapes."""
    items = data.get("servers", []) if isinstance(data, dict) else []
    out = []
    for item in items:
        server = item.get("server", item) if isinstance(item, dict) else {}
        meta = item.get("_meta", {}) if isinstance(item, dict) else {}
        official = meta.get("io.modelcontextprotocol.registry/official", {})
        if official.get("status") in ("deleted", "deprecated"):
            continue
        out.append({"server": server, "official": official})
    return out


def short_name(registry_name: str) -> str:
    tail = registry_name.split("/")[-1]
    tail = re.sub(r"[^a-z0-9]+", "-", tail.lower()).strip("-")
    tail = re.sub(r"-?(mcp|server|mcp-server)$", "", tail).strip("-")
    return tail or "server"


def to_entry(server: dict) -> dict:
    """Build a blueprint mcp_servers entry. Prefers a hosted remote over a local package."""
    name = server.get("name", "")
    entry: dict = {"name": short_name(name), "why": "TODO: say what the agents use it for.", "registry": name}
    repo = (server.get("repository") or {}).get("url")
    if repo or server.get("websiteUrl"):
        entry["docs"] = server.get("websiteUrl") or repo
    remotes = server.get("remotes") or []
    packages = server.get("packages") or []
    if remotes:
        r = remotes[0]
        entry["transport"] = "http"
        entry["url"] = r.get("url")
        headers = {}
        for h in r.get("headers") or []:
            var = re.sub(r"[^A-Z0-9]+", "_", h.get("name", "HEADER").upper()).strip("_")
            if h.get("name", "").lower() == "authorization":
                headers["Authorization"] = "Bearer ${" + short_name(name).upper().replace("-", "_") + "_TOKEN}"
            else:
                headers[h.get("name")] = "${" + var + "}"
        if headers:
            entry["headers"] = headers
        return entry
    if packages:
        p = packages[0]
        kind = (p.get("registryType") or p.get("registry_type") or "").lower()
        ident = p.get("identifier") or p.get("name") or ""
        ver = p.get("version")
        if kind == "npm":
            entry.update(command="npx", args=["-y", f"{ident}@{ver}" if ver else ident])
        elif kind == "pypi":
            entry.update(command="uvx", args=[f"{ident}=={ver}" if ver else ident])
        elif kind == "oci":
            entry.update(command="docker", args=["run", "-i", "--rm", ident])
        else:
            entry.update(command=ident, args=[])
        entry["transport"] = "stdio"
        env = {}
        for e in p.get("environmentVariables") or p.get("environment_variables") or []:
            n = e.get("name")
            if n:
                env[n] = "${" + n + "}"
        entry["env"] = env
        return entry
    entry["transport"] = "stdio"
    entry["command"] = "TODO"
    return entry


def describe(server: dict) -> str:
    kinds = []
    if server.get("remotes"):
        kinds.append("remote")
    for p in server.get("packages") or []:
        kinds.append((p.get("registryType") or p.get("registry_type") or "pkg").lower())
    return ",".join(kinds) or "?"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--yaml", action="store_true", help="Print blueprint mcp_servers entries.")
    ap.add_argument("--json", action="store_true", help="Print raw parsed results.")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    args = ap.parse_args(argv)
    try:
        results = fetch(args.registry, args.query, args.limit)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"error: could not reach the MCP registry ({exc}).", file=sys.stderr)
        print("Ask the user for the server's docs, or search https://registry.modelcontextprotocol.io in a browser.", file=sys.stderr)
        return 2
    if not results:
        print(f"No servers found for '{args.query}'. Try a broader keyword or the vendor name.")
        return 0
    if args.json:
        print(json.dumps(results, indent=2))
        return 0
    if args.yaml:
        try:
            import yaml
        except ImportError:
            print(json.dumps([to_entry(r["server"]) for r in results], indent=2))
            return 0
        print(yaml.safe_dump({"mcp_servers": [to_entry(r["server"]) for r in results]}, sort_keys=False, allow_unicode=True))
        return 0
    for r in results:
        s = r["server"]
        repo = (s.get("repository") or {}).get("url", "")
        print(f"- {s.get('name')}  v{s.get('version', '?')}  [{describe(s)}]")
        if s.get("description"):
            print(f"    {s['description'][:160]}")
        if repo:
            print(f"    repo: {repo}")
    print("\nPrefer servers published by the vendor itself. Add --yaml for blueprint entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
