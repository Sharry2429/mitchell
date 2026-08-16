# MITCHELL_CORE.md — Mitchell (the Butler): Complete System Plan

**Purpose**: single source of truth for the `mitchell` package itself — the thing you talk to. This is not the team/multi-agent layer (see `MITCHELL_TEAM.md`); this is Mitchell's own body: pillars, orchestrator, providers, self-healing. Every design decision here is made against one constraint: **the common case must be instant.**

**Package name**: `mitchell`
**Interface**: CLI chat REPL (`mitchell`) + MCP server (`mitchell-mcp`), one shared tool registry.
**Identity**: Mitchell is one persistent thing you talk to — not spawned per task, not cloned. It has a personality, a memory of *this session*, and a team it can call on (see MITCHELL_TEAM.md). It is your butler, not a tool invocation.

---

## PART 0 — THE SPEED CONTRACT

This is the section everything else is judged against.

| Task class | Target latency | How it's achieved |
|---|---|---|
| Single-pillar direct action ("mute my laptop") | **< 150ms** to tool execution start | No LLM round-trip at all — regex/intent match straight to tool call |
| Single-pillar action needing 1 LLM disambiguation | **< 800ms** to first tool call | Smallest/fastest model in the provider cascade, tools-only prompt, no history replay |
| Multi-step single-pillar task | Streaming, first tool call **< 800ms** | Same as above, loop continues without re-fetching tool schema each turn |
| Cross-pillar task (needs planning) | Plan visible **< 2s** | Planner runs on fast-tier model; execution starts on first resolved step, not after full plan |
| Task handed to the team | Acknowledgment **< 300ms**, worker starts **< 1s** | Workers are pre-warmed (Part 9), not cold-spawned per task |

Every part below states which speed tier it's optimized for. Nothing gets added to the hot path without an explicit latency budget.

---

## PART 1 — LOCKED SCOPE

| In scope | Out of scope for v1 |
|---|---|
| Windows / Android / Browser control | Voice, coding worker as *default* path |
| Fast in-process orchestration | Cross-network agent execution |
| Multi-provider LLM routing, live switching | Long-term persistent memory across days |
| Self-healing (`watchdog`, `self_repair`, `butler`, `self_audit`) | Autopilot, devops, research agents (these live in the team layer, not core) |
| Same-network Android auto-pair, no Tailscale | Electron / mobile UI |
| **Team dispatch tool** (`agents/team.py`) — the hook into MITCHELL_TEAM.md | The team's internal implementation (separate doc) |

- **Design principle**: every function under `windows/`, `android/`, `browser/` is reachable as a tool call with zero manual registration.
- **Stateless across sessions, hot within one.** No memory across restarts, but nothing gets re-initialized mid-session that doesn't have to be (see Part 9, warm state).
- **CLI-only**, one process, one identity.

---

## PART 2 — ARCHITECTURE

### 2.1 Package-and-MCP duality

Two front doors sharing one tool registry (`core/tool_registry.py`):

- `mitchell` — chat REPL, day-to-day driver, where "the butler" lives
- `mitchell-mcp` — MCP server, same tools exposed to external clients (Claude Code, Claude Desktop)

```toml
[project.scripts]
mitchell = "mitchell.cli:main"
mitchell-mcp = "mitchell.mcp_server:main"
```

### 2.2 Full-directory tool auto-discovery

`core/tool_registry.py`:
1. `importlib.import_module()` every file in `windows/`, `android/`, `browser/`
2. `inspect.getmembers(mod, inspect.isfunction)`
3. Skip `_private`, skip functions not owned by the module (fixes false-positive imports), skip `_mcp_exclude`
4. Register as `{pillar}_{module}_{func}`, e.g. `windows_system_shutdown`

**This runs once, at process start, and is cached in memory for the process lifetime.** No re-scanning per request — this is a startup cost, never a per-task cost. Startup target: **< 400ms** to full tool registry ready, including team roster load (Part 9 of MITCHELL_TEAM.md).

---

## PART 3 — REPO STRUCTURE

```text
mitchell/
├── __init__.py
├── cli.py                 # `mitchell` — chat REPL, the butler's face
├── mcp_server.py           # `mitchell-mcp`
│
├── windows/  android/  browser/     # PILLARS — unchanged from original plan
│   └── (apps, hardware, system, ui / adb, apps, communication, hardware,
│        interaction, system / browser, browser_mcp)
│
├── agents/                 # ORCHESTRATION — split fast-path vs team
│   ├── orchestrator.py     # in-process shape selection (Part 5)
│   ├── team.py             # NEW — the team dispatch tool, hooks to MITCHELL_TEAM.md
│   └── hive_client.py       # NEW — thin client into the hive substrate (defined in TEAM doc)
│
├── providers/               # unchanged — multi-provider, cascade routing
│
└── core/
    ├── tool_registry.py     # auto-discovery, cached at startup
    ├── executor.py           # tool-call loop, verification gate
    ├── routing.py             # provider + agent-shape cascade
    ├── fast_intent.py        # NEW — the zero-LLM direct-match layer (Part 4)
    ├── warm_pool.py           # NEW — pre-warmed team worker pool (see TEAM doc Part 4)
    ├── watchdog.py  self_repair.py  butler.py  self_audit.py  budget.py
    └── ...
```

---

## PART 4 — THE FAST PATH (`core/fast_intent.py`)

This is the single biggest speed lever and did not exist in the original plan explicitly — it's new.

**Problem**: even "single pillar, single action" tasks in the original orchestrator design (Part 5 of the old BRAIN.md) go through a classification pass and, per the design, potentially an LLM call to pick the tool and arguments. That's 500ms–2s of round-trip for "mute my laptop" — too slow for a butler.

**Fix — a two-tier match before any LLM is touched:**

1. **Tier 0 — exact/fuzzy phrase cache.** A small in-memory trie of previously-seen phrasings mapped directly to `(tool_name, args)`. Built from session history + a shipped seed set of common phrasings per tool. Hit → tool call fires in single-digit milliseconds, no LLM at all.
2. **Tier 1 — cheap intent classifier.** If Tier 0 misses: a tiny embedding-similarity or keyword-scored match against tool docstrings/descriptions (not an LLM call — a local, fast scorer). If confidence is high and the tool takes zero or trivially-parsed arguments (e.g. `windows_hardware_mute()`), fire immediately.
3. **Tier 2 — LLM disambiguation.** Only if Tier 0 and Tier 1 both fail or confidence is low. This is where the smallest/fastest provider-cascade model gets one tools-only call (no conversation history injected unless needed for the specific request).

Only Tier 2 touches the network. Tiers 0–1 are the default outcome for routine commands and should resolve **before the network round-trip Tier 2 would need even completes** — i.e., they're not a fallback for slow moments, they're the majority path.

---

## PART 5 — ORCHESTRATOR (in-process shape selection)

Unchanged in spirit from the original plan, but now sits *after* Part 4's fast path, not instead of it.

| Shape | When | Latency budget |
|---|---|---|
| Direct tool call (Part 4 handled it) | Simple, single-pillar | < 150ms |
| Single agent, sequential LLM+tool loop | Single-pillar, multi-step | first call < 800ms, then streaming |
| Parallel workers, same process | Independent sub-tasks, no ordering dependency | dispatched concurrently via `asyncio.gather`, no serial cost |
| Hand off to the team | Cross-pillar with real dependencies, or explicitly long-running | ack < 300ms, see MITCHELL_TEAM.md |

The orchestrator's only new job versus the original plan: recognize when a task should go to Part 4 (fast path), when it stays in-process (this part), and when it's actually team work — and make that decision fast (target: **< 50ms** classification, since it gates everything downstream).

---

## PART 6 — MULTI-PROVIDER LAYER

Same as the original plan (`providers/base.py`, `groq.py`, `aicredits.py`, `openai_compat.py`, `registry.py`), with one speed-relevant addition:

- **Provider warm ping.** At startup, and on an idle timer, Mitchell sends a trivial keep-alive to the top-of-cascade provider so the first real request of a session doesn't pay TLS/connection-setup cost. This is the same instinct as Part 9's worker pre-warming, applied to network connections instead of processes.
- Cascade order and manual `/provider` / `/model` switching: unchanged from the original plan.

---

## PART 7 — EXECUTION FLOW

1. **Fast path check** (Part 4) — majority of turns end here.
2. **Orchestrator classification** (Part 5) — if fast path missed.
3. **Tool-call loop** (`core/executor.py`) — ReAct-style, up to 10 turns, same as original plan.
4. **Verification gate** — up to 3 attempts, never silently treats failure as success.
5. **Team hand-off** — if the orchestrator decided this is team work, control passes to `agents/team.py` (see MITCHELL_TEAM.md Part 3) and Mitchell immediately returns an acknowledgment to you rather than blocking — you get "on it, I've got Android and Browser working on that" in under 300ms while the team runs.

---

## PART 8 — ANDROID CONNECTION FLOW

Unchanged from the original plan (same-network auto-pair, cached IP in `~/.mitchell_adb_wifi.json`, no Tailscale, `reset_connection` as the repair tool). Not a speed-critical path — this is connection setup, not a per-task cost, so it's optimized for reliability over latency.

---

## PART 9 — SELF-HEALING LAYER

Unchanged in function from the original plan (`watchdog`, `self_repair`, `butler`, `self_audit`, `budget`), with one addition relevant to speed:

- **`watchdog.py`** also now monitors team worker pool health (are pre-warmed workers still alive, is the hive substrate responsive) — because a stale warm pool silently turns "lightning fast" team dispatch back into cold-start-slow without anyone noticing.

---

## PART 10 — BUILD ORDER

1. Scaffold + pyproject entry points
2. Port pillars (windows/android/browser) verbatim from source repo
3. **Build `core/fast_intent.py` before the full orchestrator** — this is the highest-leverage speed piece and should exist even in a minimal first version
4. Tool registry (auto-discovery, cached at startup)
5. Orchestrator (fast-path-aware from day one, not bolted on later)
6. Provider layer + warm ping
7. Self-healing
8. `agents/team.py` + `hive_client.py` stubs (full implementation in MITCHELL_TEAM.md build order)
9. CLI + MCP entry points
10. Test port, security sweep, keep this file in sync

---

## PART 11 — MAINTENANCE RULE

Same rule as the original BRAIN.md: if code and this file disagree, the code is right and this file is stale — but a stale doc is a bug, fixed immediately, not left standing. Any change that adds latency to a path in Part 0's table requires either a justification written here or a fix.
