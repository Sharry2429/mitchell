# BRAIN.md — Mitchell Complete System Reference & Implementation Plan

**Purpose of this file**: this is the single source of truth for Mitchell — the plan to build it AND the complete structural/functional reference once built. Anyone (human or AI) should be able to read this file alone and understand the entire system without opening the codebase or any other document. When code changes, this file changes with it — it is not a one-time snapshot, it is the living map of the system.

**Package name**: `mitchell`
**Interface**: CLI, chat-style (`mitchell` → opens a REPL)
**Core identity**: a dynamic multi-agent orchestration runtime for Windows control, Android control, and Browser control. Nothing else.

## Repos

| Repo | Role |
| :--- | :--- |
| [github.com/Sharry2429/Mitchelassistant](https://github.com/Sharry2429/Mitchelassistant) | **Source repo.** The current full-featured build (voice, memory, coding worker, guardian, everything). Every file/function referenced in this plan lives here right now, verified by direct AST scan. |
| [github.com/Sharry2429/mitchell](https://github.com/Sharry2429/mitchell) | **Target repo.** The lean build described in this document gets built here. This is the new, permanent home for Mitchell going forward. |

> **Note**: Every function this plan says to keep, cut, or fix currently exists in `Mitchelassistant` at the exact file path named (e.g. `mitchell/android/adb.py`, `mitchell/windows/core/vdm.py`). Nothing in this document is hypothetical.

## TABLE OF CONTENTS

- Part 1 — Locked Scope (what's in, what's out)
- Part 2 — Architecture (package + MCP duality)
- Part 3 — Repo Structure (every folder, every file)
- Part 4 — Tool Registration Mechanism (how a function becomes callable)
- Part 5 — Multi-Agent Orchestration (dynamic shape selection)
- Part 6 — Multi-Provider Layer (switch mid-chat)
- Part 7 — The Execution Flow (what happens when you type something)
- Part 8 — Android Connection Flow (same-network auto-pair, no Tailscale)
- Part 9 — Self-Healing Layer
- Part 10 — Known Gaps Closed During the Port
- Part 11 — What Is Deliberately Not In This Repo
- Part 12 — Build Order
- Part 13 — Open Items For Next Session
- Part 14 — Maintenance Rule For This File

---

## PART 1 — LOCKED SCOPE

| In scope | Out of scope for v1 |
| :--- | :--- |
| Windows control (apps, files, UI automation, hardware, system, virtual desktops) | Voice (STT/TTS/diarization) |
| Android control (adb, apps, communication, hardware, system, same-network wireless pairing) | Coding worker (Hermes) |
| Browser control (navigate, click, type, extract, screenshot) | Memory / persistent context across sessions |
| Multi-agent orchestration (dynamic, task-decided) | Electron / mobile UI |
| Multi-provider LLM routing with live switching | Guardian diagnostics layer (superseded by `self_repair`/`watchdog`) |
| Self-healing (`watchdog`, `self_repair`, `butler`, `self_audit`) | Autopilot sessions, devops (git/PR), research, vision, prompt evolution, skill foundry |
| Same-network Android auto-pairing, no Tailscale | Tailscale as a dependency, anywhere |

- **Design principle**: every function under Windows/Android/Browser must be reachable as a tool call. Nothing sits in the codebase uncallable.
- **Stateless**: No memory across sessions. Each chat session is a clean slate — the conversation buffer lives only as long as the process runs.
- **CLI-only**: No Electron, no mobile app, no web UI. One interface: the terminal.

---

## PART 2 — ARCHITECTURE

### 2.1 Package-and-MCP duality

Mitchell ships as one Python package with two front doors:
- `mitchell` — chat REPL, the primary day-to-day interface
- `mitchell-mcp` — MCP server, same tools exposed to any external MCP client (Claude Desktop, Claude Code, etc.)

Both entry points import the same tool registry (`core/tool_registry.py`). A tool is defined once, and is simultaneously:
- callable directly from Python (`from mitchell.windows import apps; apps.open_app("chrome")`)
- callable by an agent inside the CLI chat loop
- callable by an external MCP client when run as `mitchell-mcp`

This is the same pattern the source repo already uses (`mcp_server.py` auto-registers modules via `inspect.getmembers`) — kept here, but with the module-allowlist gaps removed (see Part 4).

### 2.2 Entry points (`pyproject.toml`)

```toml
[project.scripts]
mitchell = "mitchell.cli:main"         # chat REPL — day-to-day driver
mitchell-mcp = "mitchell.mcp_server:main"  # MCP server — for external MCP clients
```

Running `mitchell` with no args opens the chat REPL. Running `mitchell-mcp` starts a stdio/SSE MCP server exposing every tool with zero difference in behavior underneath — same functions, same self-healing, same providers.

---

## PART 3 — REPO STRUCTURE

```text
mitchell/
├── __init__.py
├── cli.py                 # entrypoint: `mitchell` — chat REPL
├── mcp_server.py          # entrypoint: `mitchell-mcp` — MCP server
│
├── windows/               # PILLAR 1
│   ├── __init__.py
│   ├── apps.py            # window & file management
│   ├── config.py          # WinControlConfig
│   ├── hardware.py        # volume, display, network, wifi, firewall
│   ├── system.py          # power, process, registry, services, virtual desktops
│   ├── types.py           # Pydantic models (no logic)
│   ├── ui.py              # screen, mouse, keyboard, clipboard
│   └── core/              # low-level engine layer (not tools themselves)
│       ├── powershell.py
│       ├── screenshot.py
│       ├── tree.py
│       ├── uia.py
│       └── vdm.py
│
├── android/               # PILLAR 2
│   ├── __init__.py
│   ├── adb.py             # raw adb shell access
│   ├── apps.py            # launch/stop/install/uninstall/screen
│   ├── base.py            # internal guard helpers (not a tool file)
│   ├── communication.py   # calls, SMS, contacts, calendar
│   ├── connection.py      # THE connection manager — see Part 8
│   ├── hardware.py        # volume, wifi, airplane mode
│   ├── interaction.py     # tap, swipe, type, screen analysis
│   ├── notification.py    # (needs real implementation — see Part 10)
│   └── system.py          # process, storage, permissions, settings
│
├── browser/               # PILLAR 3
│   ├── __init__.py
│   ├── browser.py         # navigate, click, type, extract, screenshot
│   └── browser_mcp.py     # BrowserSession — underlying session object
│
├── agents/                # ORCHESTRATION (new code, not ported)
│   ├── __init__.py
│   └── orchestrator.py    # decides agent shape per task — see Part 5
│
├── providers/             # LLM PROVIDER LAYER (new code, generalized from source)
│   ├── __init__.py
│   ├── base.py            # Provider protocol
│   ├── groq.py
│   ├── aicredits.py
│   ├── openai_compat.py
│   └── registry.py        # load/switch/cascade logic
│
└── core/                  # EXECUTION ENGINE + SELF-HEALING
    ├── __init__.py
    ├── config.py          # SystemMCPConfig
    ├── errors.py          # exception hierarchy
    ├── result.py          # MCPResult
    ├── tokens.py          # token estimation, history compression
    ├── models.py          # model tiers, pricing table
    ├── executor.py        # THE execution loop — see Part 7
    ├── tasks.py           # Task/TaskStep/TaskState
    ├── planner.py         # multi-step decomposition
    ├── routing.py         # cascade routing — see Part 6/7
    ├── tool_provider.py   # ToolProvider abstraction — see Part 4
    ├── tool_registry.py   # MCP tool auto-registration — see Part 4
    ├── agent_pool.py      # step claiming, device locks
    ├── watchdog.py        # self-healing: resource monitoring
    ├── self_repair.py     # self-healing: detect/patch/verify/deploy
    ├── butler.py          # self-healing: background run loop
    ├── self_audit.py      # self-healing: pyflakes/tests/token audit
    └── budget.py          # spend cap tracking
```

---

## PART 4 — TOOL REGISTRATION MECHANISM (how a function becomes callable)

Every function in `windows/`, `android/`, `browser/` — and any deliberately-exposed `core/` modules — becomes an LLM-callable tool through one mechanism, defined in `core/tool_registry.py`:

1. `importlib.import_module()` loads each module file in a pillar directory
2. `inspect.getmembers(mod, inspect.isfunction)` walks every function defined in it
3. Skip if the name starts with `_` (private helper, not a tool)
4. Skip if `func.__module__ != mod.__name__` (this excludes functions merely imported into the module, e.g. `dataclasses.field` showing up as a false positive — a real bug that existed in the source repo and is fixed here)
5. Skip if the function has an `_mcp_exclude` attribute set (an explicit opt-out escape hatch)
6. Rename it to `{platform}_{module}_{funcname}` (e.g. `windows_system_shutdown`, `android_apps_launch`, `browser_navigate` for the browser pillar which keeps its natural `browser_*` names)
7. Register it on the `FastMCP` server instance via `mcp.add_tool(func)`

**Critical difference from the source repo**: the source repo used a hand-picked allowlist (`windows_modules = ["system", "hardware", "ui", "apps", "tts", "stt"]`, `android_modules = ["system", "hardware", "interaction", "apps", "communication"]`) which silently left files out (see Part 10 gap list). Mitchell (this repo) replaces the allowlist with full-directory auto-discovery — every `.py` file found in `windows/`, `android/`, `browser/` at import time gets scanned. Adding a new file to a pillar directory means it's automatically live as tools with zero registration code needed.

### The ToolProvider abstraction

The execution engine (`executor.py`) never talks to the MCP server object directly — it talks through a `ToolProvider` interface (`core/tool_provider.py`), which has two implementations:
- `MCPToolProvider` — production. Lazily imports `mcp_server.mcp`, calls `list_tools()` and `call_tool()` against the live registered tool set.
- `StaticToolProvider` — testing. In-process plain-callable dict, no `FastMCP` dependency, fully deterministic, used by the test suite.

This means the executor is swappable and testable without ever touching real Windows/Android/Browser state.

---

## PART 5 — MULTI-AGENT ORCHESTRATION (dynamic, not fixed)

No hardcoded topology. No permanent Windows-agent, Android-agent, or Browser-agent. The orchestrator decides shape per task, based on what's actually fastest for that request. Three shapes it can pick from, and it can mix them within one session:

| Shape | When picked |
| :--- | :--- |
| **Single agent, direct tool call** | Simple, single-pillar task ("mute my laptop", "open Chrome") — no planning overhead, straight to the tool. This is the fast path and majority case. |
| **Parallel workers, same toolset** | Task decomposes into independent sub-tasks with no ordering dependency ("check battery on phone AND laptop") — spun up concurrently, results merged. |
| **Specialist sub-agents under an orchestrator** | Task genuinely spans pillars with dependencies ("open this file on my PC, then send it to my phone, then confirm it arrived") — orchestrator plans the sequence, dispatches each step to whichever pillar's tools it needs. |

### 5.1 Decision logic (`agents/orchestrator.py`)

`agents/orchestrator.py` does a cheap classification pass before committing to a shape:
1. Parse task → does it name one pillar or multiple? (keyword/intent match against windows/android/browser tool namespaces)
2. **Single pillar, single action** → direct tool call, no agent loop at all. This is the fast path and should be the majority of requests.
3. **Single pillar, multi-step** → one agent, sequential tool calls, same pattern as the source `executor.py` loop.
4. **Multiple pillars, no dependency between them** → parallel dispatch (`asyncio.gather` over sub-agent instances), merge results.
5. **Multiple pillars, dependent steps** → planner produces an ordered step list (existing `planner.py` logic), orchestrator dispatches each step to the right pillar's tool surface in order.

This reuses the existing cascade philosophy from `routing.py` (cheap path first, escalate only when needed) but generalizes it from "which model" to "which agent shape" — same instinct, one layer up.

### 5.2 Speed discipline

- **Step 2** (direct tool call) must be the default outcome for the majority of everyday commands — no LLM planning round-trip for "lock my screen."
- **Parallel workers** (step 4) only spin up when sub-tasks are provably independent — no fan-out for tasks that could race or conflict (e.g. two workers touching the same file).
- Every agent shape shares one provider layer and one tool registry — no duplicate tool-loading cost per agent spawned.

---

## PART 6 — MULTI-PROVIDER LAYER (switch mid-chat)

Generalizes the source repo's `llm_client.py` (Groq-only) into a real provider abstraction.

### 6.1 Provider registry

```text
providers/
├── base.py            # Provider protocol: .call(messages, tools) -> LLMResult
├── groq.py
├── aicredits.py
├── openai_compat.py   # generic OpenAI-compatible endpoint (covers most providers)
└── registry.py        # load_providers(), active_provider(), set_active(), cascade_order()
```

Each provider config carries: name, base URL, model list, priority in the cascade, and env var for its key. Adding a new provider is a config entry, not new code, as long as it's OpenAI-tool-call compatible.

### 6.2 Switching mechanisms (both — manual and automatic)

**Manual — slash command in the chat REPL:**
```text
> /provider groq
> /provider aicredits
> /model llama-3.3-70b-versatile
> /providers # lists all configured providers + current active one
```
Switch takes effect on the next message — the orchestrator and any in-flight agent just pull `active_provider()` fresh each call, no restart needed.

**Automatic — cascade on failure, same escalation instinct as the source repo's `routing.py`:**
`gpt-oss-120b (Groq)` → `gpt-oss-20b (Groq)` → `llama-3.3-70b-versatile (Groq)` → `AiCredits net`

If the person manually pinned a provider with `/provider`, auto-cascade still activates on hard failure (rate limit, timeout, error) but returns to the pinned provider on the next fresh task rather than staying on the fallback — pin means "prefer," not "only ever."

### 6.3 Mid-chat state

The chat REPL keeps a lightweight session object (`cli.py::ChatSession`) holding: pinned provider (if any), conversation buffer, active task IDs. This is not memory across sessions — it's just live chat state, gone when the process exits, matching the stateless decision.

---

## PART 7 — THE EXECUTION FLOW (what actually happens when you type something)

### 7.1 Entry: chat REPL
You run `mitchell`. It opens a REPL (`cli.py`). You type a request. `cli.py` hands the raw text to the orchestrator (unless it's a slash command, handled first — see 7.7).

### 7.2 Orchestrator classification
See Part 5.1 for the full decision tree. Summary: single pillar + single action = direct tool call (fast path, no LLM round-trip); everything more complex escalates through single-agent-loop → parallel-workers → planned-sequence.

### 7.3 The agent tool-call loop (ported from source `executor.py::_llm_tool_loop`)
For any path that isn't a direct single-tool call, this is the loop that runs per step:
1. Build a prompt describing the step (description + target action namespace + any prior error)
2. Fetch the current tool list from the ToolProvider, in OpenAI function-calling schema
3. Call the LLM (via the active provider) with the prompt + tool list
4. If the LLM's response has no `tool_calls` → done, break out
5. If it has `tool_calls`: for each tool call:
   - parse the JSON arguments
   - invoke `tools.call_tool(name, args)` through the ToolProvider
   - append the tool's result (or error string) back into the message history
   → loop back to step 3, feeding the updated history back to the LLM
6. Repeat up to 10 turns max (hard cap, prevents runaway loops)

This is a standard ReAct-style tool loop: LLM proposes a tool call → tool executes → result feeds back → LLM decides next step or stops.

### 7.4 Verification gate (ported from source `executor.py::run_step`)
Every step runs through this wrapper, not just the raw loop:
```python
for attempt in [0, 1, 2]: # up to 2 retries, 3 total attempts
    # run the tool-call loop (7.3)
    # if it raised an exception → record the error, try again
    
    # verify_step(step, messages) # hard gate — checks the transcript actually 
                                  # accomplished what the step described
    # if verified → mark step complete, return success
    # else → record "verification failed", try again
# if all attempts exhausted → step marked failed
```
Verification failure is never silently treated as success. This is a hard gate — a step either produces a verifiably-completed transcript or it's retried, and if retries run out, it's marked failed and surfaced honestly, not swept under.

### 7.5 Multi-step task flow (ported from `executor.py::_process_task`)
When a request needs multiple ordered steps:
1. If the task has no steps yet → run the planner to decompose it into TaskSteps (planning failure → task marked FAILED immediately, not left stuck/unclaimable)
2. Loop: `claim_next_step()` pulls the next unclaimed, dependency-satisfied step
3. Run that step through the verification-gated loop (7.4)
4. Mark it completed or failed, log what happened
5. Repeat until no more claimable steps remain

### 7.6 Provider routing within the loop
Every LLM call in the loop above goes through the provider registry (Part 6), not directly to one hardcoded API. If a call fails, the registry automatically tries the next tier down the cascade for that call. Once the current task completes, the next fresh task returns to the pinned provider (or top of cascade if nothing's pinned) — a failure doesn't permanently downgrade the session.

### 7.7 Slash commands (chat REPL only, handled in `cli.py` before reaching the orchestrator)
- `/provider <name>` — pin a provider (`groq`, `aicredits`, ...)
- `/model <name>` — pin a specific model within the active provider
- `/providers` — list configured providers + show which is active

These mutate `cli.py::ChatSession` state — pinned provider, pinned model — read fresh by the provider registry on every subsequent call. No restart needed, takes effect on the next message.

---

## PART 8 — ANDROID CONNECTION FLOW (same-network auto-pair, no Tailscale)

This is the exact mechanism, ported and cleaned from the source repo's `android/connection.py`'s existing `get_active_serial()` logic — Tailscale is fully removed, not replaced with something new.

### 8.1 First-time pairing
1. User plugs phone into PC via USB, with USB debugging (developer mode) already enabled
2. First `android_*` tool call triggers `get_active_serial()`
3. `get_active_serial()` checks: is there a cached serial? No (first run).
4. Runs `adb devices` → finds the USB-connected serial (no `:` in the ID = local/USB)
5. Detects it's a raw USB serial (not already a network target, not an emulator)
6. Runs `adb -s <serial> shell ip route` → parses the `wlan0` line for the phone's local network IP (e.g. `192.168.1.55`)
7. Runs `adb -s <serial> tcpip 5555` → phone starts listening for adb over the network
8. Runs `adb connect <phone_ip>:5555` → connects over the same Wi-Fi/LAN
9. On success: saves the IP to `~/.mitchell_adb_wifi.json`, sets it as the active serial
10. User can now unplug the USB cable — Mitchell keeps talking to the phone wirelessly

### 8.2 Every subsequent session
1. `get_active_serial()` checks cached in-memory serial first (fast path, this session)
2. If not set: checks `adb devices` for anything already connected
3. If nothing: reads `~/.mitchell_adb_wifi.json` for the last known IP, tries `adb connect <saved_ip>:5555` directly — no USB replug needed if the phone is already awake and on the same network
4. If that also fails: raises a clear error — "no device found, plug in via USB once on the same network as this PC"

### 8.3 Repair flow — "tell Mitchell to repair the connection"
User: "the phone's not responding" / "reconnect my phone" / "repair the connection"
→ orchestrator routes this to `android_connection_reset_connection` (the `reset_connection()` function, registered as a tool)
→ this clears the cached serial and the cached uiautomator2 device handle
→ the NEXT android tool call automatically re-runs the full 8.1/8.2 flow from scratch — fresh device detection, fresh IP handshake

One clean tool call closes the loop: user reports a problem in plain language, orchestrator maps it to the repair tool, the repair tool resets state, the next real action re-establishes the connection properly.

### 8.4 What was removed and why
- `android/wireless.py` deleted — its `setup()` function depended on tailscale status to find the phone's IP; fully redundant with what `connection.py` already does over plain Wi-Fi, and it wasn't even wired into the real tool-call path in the source repo (dead code)
- `_connect_tailscale()` and `SYSTEM_MCP_TAILSCALE_HOST`/`SYSTEM_MCP_TAILSCALE_PORT` env var handling removed from `connection.py`
- Requirement: phone and PC must be on the same Wi-Fi/LAN network — this is the tradeoff for dropping Tailscale (no more cross-network/remote pairing), and it's a deliberately chosen tradeoff
- `core/adb_setup.py` and `core/setup_wizard.py` in the source repo also reference Tailscale (the wizard literally has a "Step 2: Tailscale Configuration" screen) — both files are already excluded from this build (Part 11), so there's no leftover Tailscale code path anywhere post-port

---

## PART 9 — SELF-HEALING LAYER (kept in full)

Runs independently of conversation state — this watches the process, not what was said.

- `watchdog.py` — periodically checks laptop/phone battery and other resource thresholds; fires a proactive alert if something crosses a danger line (e.g. low battery mid-task)
- `self_repair.py` — a detect → diagnose → patch-in-sandbox → verify-patch → deploy pipeline for the codebase itself if something in Mitchell's own execution breaks; patches are sandboxed and verified before being deployed, with a bounded escalation path if a fix can't be found automatically
- `butler.py` — registers Mitchell to run on system startup, runs a background loop for periodic upkeep tasks
- `self_audit.py` — runs pyflakes and the test suite, analyzes token usage patterns, generates follow-up audit tasks if something looks off
- `budget.py` — tracks real spend against the pricing table in `core/models.py` (per-model input/output token pricing), enforces a spend cap across whichever provider is active, provider-agnostic (the source repo's version was Groq-only)

Ported as-is from the source repo, stripped of anything referencing memory/voice/coding. Independent of the stateless decision — self-healing watches whether tool calls and the agent loop are healthy, not what was said last session.

---

## PART 10 — KNOWN GAPS CLOSED DURING THE PORT

Ported 1:1 from the audited inventory, with these fixes applied during the port so the "everything callable" rule actually holds:

| Function(s) | Source location | Problem in source repo | Fix applied here |
| :--- | :--- | :--- | :--- |
| `shell`, `run`, `run_background` | `android/adb.py` | Coded, never added to the tool registration allowlist | Now covered automatically by full-directory auto-discovery (Part 4) |
| `reset_connection` | `android/connection.py` | Existed but wasn't a registered tool | Registered as the repair tool (Part 8.3) |
| `get_active_notifications` | `android/notification.py` | Stub — always returns an empty list, regardless of real device notification state | Needs a real implementation (actual notification listener) before it's trustworthy as a tool. Tracked as an open item — do not register until fixed, a tool that silently lies is worse than no tool. |
| `switch_desktop`, `get_all_desktops`, `get_desktop_count`, `is_window_on_current_desktop`, `move_window_to_desktop`, `get_current_desktop` | `windows/core/vdm.py` | Fully coded, real logic, but zero wrapper anywhere — not called by `system.py` or `ui.py`, not registered, completely unreachable | Wrapped with a thin pass-through section added to `windows/system.py` so these get proper tool names and enter the registry |
| `speak`, `get_voices`, `listen_and_transcribe` | `windows/stt.py`, `windows/tts.py` | Voice functions were sitting inside the Windows pillar folder by accident, mixing scope | Removed entirely — voice is out of scope for this build |
| Module allowlists in `mcp_server.py` | `mcp_server.py` | Hand-picked lists (`windows_modules = [...]`, `android_modules = [...]`) silently exclude any file not explicitly named | Replaced with full-directory auto-discovery (Part 4) |
| Tailscale dependency | `android/wireless.py`, `android/connection.py`, `core/adb_setup.py`, `core/setup_wizard.py` | Primary/fallback pairing mechanism depended on an external VPN tool | Fully removed; same-network auto-pair is now the only path (Part 8) |
| Hardcoded auth token `zO89qjdJD2Vo` | 5 files across source repo (`launch.py`, both React `App.tsx` files, `shots_demo.py`, `dump_demo.py`) | Committed in plaintext to a public repo | Not carried over. New repo generates its own token at first run, stored in `.env`, `.env` is gitignored from day one |

Everything else in the Windows/Android/Browser inventory (~326 functions across the three pillars, per the full function audit) ports over unchanged — this is the bulk of the value and none of it needs redesign, only relocation.

---

## PART 11 — WHAT IS DELIBERATELY NOT IN THIS REPO

Stays in `Mitchelassistant` as historical/reference only, documented here so nobody re-adds it by accident later without a deliberate decision:

- **Voice** — STT, TTS, diarization, speaker enrollment, voice session management (13 files in source repo's `voice/`)
- **Coding worker** — the "Hermes" subprocess coding agent (`coding/` in source repo, 3 files)
- **Guardian** — diagnostics module, functionally superseded by `self_repair.py` + `watchdog.py`
- **Memory** — no persistent context, profile, or episodic logging across sessions (`memory.py`, `memory_store.py` in source repo)
- **Autonomy extras** — `autopilot_engine.py` (multi-session autonomous runs), `devops.py` (self-committing to git/opening PRs), `research.py` (web research), `review.py`, `vision.py` (vision-based UI navigation), `prompts.py` (self-evolving prompts), `unlocker.py` (credential/PIN storage), `notify_gateway.py`, `setup_wizard.py`, `supervisor_ipc.py`, `skills.py`, and the tool-writing-itself foundry pieces of `tool_registry.py` (`detect_gap`, `draft_tool`)
- **Electron desktop UI**, **Capacitor mobile app** (`mitchell-electron/`, `mitchell-mobile/`) — CLI only
- **WebSocket chat/voice server routes** (`server/ws_voice.py`, `server/ws_chat.py`) — no external server surface for v1, CLI talks to the package in-process
- **Root demo/proof scripts** — `dump_demo.py`, `shots_demo.py`, `scripts/prove_*.py`, `scripts/real_live_demo.py`, `scripts/run_autonomous.py`
- **Tailscale**, anywhere, for any purpose

---

## PART 12 — BUILD ORDER

1. **Scaffold** — create `Sharry2429/mitchell`, `pyproject.toml` with the two entry points, empty package skeleton per Part 3
2. **Port pillars** — copy `windows/`, `windows/core/`, `android/`, `browser/` from `Mitchelassistant` verbatim, apply Part 10 fixes
3. **Provider layer** — build `providers/` from scratch (generalizing `llm_client.py`), wire Groq + AiCredits first since those are proven
4. **Tool registry** — port `core/tool_registry.py`'s registration mechanism (not the self-writing-tool-foundry part), switch to full-directory auto-discovery
5. **Orchestrator** — build `agents/orchestrator.py` fresh per Part 5; start with the direct-tool-call fast path only, add parallel and specialist shapes once the fast path is solid
6. **Self-healing** — port `watchdog.py`, `self_repair.py`, `butler.py`, `self_audit.py`, `budget.py`, strip memory/voice references
7. **CLI** — build `cli.py` chat REPL with `/provider`, `/model`, `/providers` slash commands
8. **MCP entry point** — `mcp_server.py` reusing the same registry from step 4
9. **Test port** — bring over the non-voice, non-memory, non-coding tests from the existing `tests/` suite as a baseline safety net
10. **Security check** — confirm no hardcoded secrets anywhere before first public push (grep sweep + `.gitignore` for `.env`)
11. **Keep this file in sync** — update `BRAIN.md` as each build step lands; this file documents what exists, it doesn't get written ahead of the code and then left stale

---

## PART 13 — OPEN ITEMS FOR NEXT SESSION

- Exact provider config format (`providers.json` vs `.env`-driven vs both)
- Whether `windows/core/`, `android/`, `browser/` keep their current internal APIs or get touched during port (plan above assumes verbatim copy — no rewrite risk)
- Test coverage target before calling v1 "done"

---

## PART 14 — MAINTENANCE RULE FOR THIS FILE

This file must be updated whenever:
1. A new function is added to `windows/`, `android/`, or `browser/`
2. The orchestrator's decision logic changes
3. A provider is added or the cascade order changes
4. The Android connection/repair flow changes
5. Anything in Part 10's gap list gets closed or a new gap is found
6. Anything in Part 11's exclusion list gets reconsidered
7. Any build-order step in Part 12 completes or changes

If code and this file disagree, the code is correct and this file is stale — but a stale `BRAIN.md` is a bug to fix immediately, not a state to leave standing.
