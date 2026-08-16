# MITCHELL_TEAM.md — Mitchell's Team: Multi-Agent Harness Layer

**Purpose**: single source of truth for the team layer — the thing Mitchell (the butler, see `MITCHELL_CORE.md`) reaches for when a task is bigger than one pillar can handle fast, or genuinely needs parallel/independent workers. This is not a second Mitchell. It's a roster of scoped teammates that Mitchell spawns, messages, and dismisses.

**Built from two sources, credited explicitly:**
- **Coordination substrate pattern** — adapted from `chaitanyagiri/munder-difflin`'s hive design (mailbox/blackboard/event-log, single-committer git, GOD-orchestrator-escalates-only-critical-items).
- **Role & tool prompt text** — adapted from `Piebald-AI/claude-code-system-prompts`, specifically: `TeammateTool`, `SendMessageTool` (agent-teams version), `System Reminder: Team Coordination` / `Team Shutdown`, `Agent Prompt: Worker fork`, `System Prompt: Subagent delegation examples`, `System Prompt: Fork usage guidelines`, `System Prompt: Writing subagent prompts`.

**Core constraint carried over from MITCHELL_CORE.md Part 0: dispatch must feel instant. A cold-started subprocess per task is not acceptable — see Part 4 (warm pool).**

---

## PART 1 — WHAT A "TEAMMATE" IS

A teammate is **not** another instance of Mitchell. It is a scoped worker with:

- A **role** (one of a fixed roster, Part 2)
- A **narrow tool surface** (only the tool namespace its role needs — e.g. a `windows_worker` only ever sees `windows_*` tools)
- A **role prompt** (adapted from Piebald's Worker Fork prompt, specialized per role)
- A **lifecycle**: spawned → working → reporting → dismissed. No teammate persists across tasks by default; the pool (Part 4) keeps *processes* warm, not *task state*.

This mirrors Mitchell's own "everything callable, nothing sits unreachable" principle, inverted for safety: a teammate can reach *less* than Mitchell can, on purpose.

---

## PART 2 — THE ROSTER

| Role | Tool scope | Backing implementation | Notes |
|---|---|---|---|
| `windows_worker` | `windows_*` only | Mitchell's own provider layer + tool registry, filtered | Default choice for Windows-pillar sub-tasks |
| `android_worker` | `android_*` only | same | Default for Android-pillar sub-tasks |
| `browser_worker` | `browser_*` only | same | Default for Browser-pillar sub-tasks |
| `coder` | filesystem + shell, no OS-control pillars | **optionally** PTY-wraps a real coding CLI (Claude Code, etc.), Munder-Difflin-style | Only spawned when a task is genuinely "write/modify code," not part of the fast pillar rotation |
| `researcher` | web search/fetch only | Mitchell's provider layer, no pillar tools at all | For "find out X" sub-tasks that don't touch the device |

Each role's prompt file lives at `agents/roles/{role}.md`, starting from Piebald's Worker Fork prompt structure:
- Identity: "you are a forked worker executing one directive from Mitchell, report back concisely"
- Scope: explicit list of tools available, explicit instruction not to attempt anything outside scope
- Reporting format: structured result Mitchell's router can parse without another LLM call (see Part 5)
- Honesty guardrail, adapted from Piebald's Fork Usage Guidelines: never fabricate a result, never claim completion without verification

---

## PART 3 — MITCHELL'S TEAM TOOL (`agents/team.py`)

This is Mitchell's own `TeammateTool`, adapted from Piebald's extracted description. Exposed to Mitchell's own orchestrator as regular tools:

```python
team_spawn(role, task, priority="normal") -> agent_id
team_message(agent_id, content) -> None          # SendMessageTool equivalent
team_status(agent_id=None) -> dict                # None = whole roster
team_dismiss(agent_id) -> None
```

**Spawn is the critical-path call.** Its target latency is **< 1s to worker acknowledgment**, achieved entirely through Part 4's warm pool — `team_spawn` for a warm role never cold-starts a process, it claims an already-running idle worker and hands it the task.

**Speed-relevant behavior:**
- `team_spawn` returns immediately once the worker has *accepted* the task (ack), not once it's *finished*. Mitchell reports back to you ("on it — Browser's checking flight prices") and continues its own conversation loop while the worker runs.
- Mitchell polls or subscribes to the hive event log (Part 5) for completion, not by blocking.

---

## PART 4 — WARM POOL (the actual speed mechanism)

This is the piece that makes "spawn a teammate" fast instead of the usual cold-subprocess-start tax.

- At Mitchell startup, `core/warm_pool.py` pre-spawns **one idle instance of each roster role** (Part 2) that doesn't require heavy external state (i.e. `windows_worker`, `android_worker`, `browser_worker`, `researcher` — not `coder`, since PTY-wrapping a coding CLI is heavier and spawned on-demand).
- Idle workers sit in a wait state, tool registry already loaded, provider connection already warm (same trick as MITCHELL_CORE.md Part 6's provider ping, applied per worker).
- `team_spawn(role, task)` claims the idle instance, hands it the task via the hive mailbox, and **immediately spins up a fresh idle replacement in the background** so the pool never runs dry.
- If demand exceeds the warm pool (e.g. three simultaneous `browser_worker` tasks), only the *overflow* pays a cold-start cost — the common case (one task at a time per role) never does.
- `watchdog.py` (MITCHELL_CORE.md Part 9) checks pool health on an interval and respawns any dead idle workers, so the pool self-heals without you noticing a slowdown.

**Numbers this is designed against**: cold subprocess spawn + tool registry load + provider connection setup realistically costs 1–3 seconds. Claiming a warm idle worker costs the time to write one mailbox message — target **under 100ms**, well inside the `team_spawn` < 1s budget with headroom for hive routing overhead.

---

## PART 5 — THE HIVE (coordination substrate)

Adapted from Munder Difflin's `hive.ts` design, ported to Mitchell's Python stack as `agents/hive.py` + `agents/hive_client.py`.

- **On-disk, plain files, single-committer git** — same rationale as the original: no agent ever touches git directly, avoiding `index.lock` corruption when multiple workers write concurrently.
- Each teammate has an `outbox/` it writes to; the hive's router delivers into recipients' `inbox/` (in practice, mostly `mitchell → worker` and `worker → mitchell`, since workers don't typically need to talk to each other — see Part 6 for when they do).
- A shared **blackboard** for state visible to the whole team (e.g. "phone is currently locked," written by `android_worker`, readable by anyone).
- An **append-only event log** — this is what `team_status()` and Mitchell's completion-polling read from, so status checks never block on asking a worker directly.
- **Speed note**: the hive is file-based for durability and debuggability (you can literally read what happened), but the *hot path* (spawn → ack) does not wait on a git commit. Git commits happen on a short async batch interval (e.g. every 2s or on a graceful checkpoint), not synchronously per message — synchronous git commits per message would blow the latency budget.

---

## PART 6 — MESSAGE ROUTING & CROSS-PILLAR TASKS

For genuinely dependent, cross-pillar tasks (Mitchell's own orchestrator's "specialist sub-agents" shape, MITCHELL_CORE.md Part 5) — e.g. "open this file on my PC, then send it to my phone, then confirm it arrived":

1. Mitchell's orchestrator (not the team layer) still owns sequencing — it does not hand a whole multi-step plan to the team and walk away, because that reintroduces the coordination-overhead cost this design is trying to avoid.
2. Instead: Mitchell spawns `windows_worker` for step 1, waits on the hive event log for completion, then spawns (or reuses, if still warm and idle) `android_worker` for step 2 with step 1's result passed as task context, and so on.
3. Workers themselves stay dumb and scoped — they don't message each other directly by default. Direct worker-to-worker messaging is available (`SendMessageTool` pattern, same field shape as Piebald's) but reserved for cases where Mitchell has explicitly delegated coordination of a sub-plan to one worker (rare, and always logged to the blackboard so it's visible).

---

## PART 7 — SYSTEM REMINDERS (Piebald-adapted)

Injected into Mitchell's own context, not the workers':

- **Team Coordination reminder** — active whenever `team_status()` shows ≥1 non-idle teammate. Reminds Mitchell (the model) to track outstanding work, not lose thread of what's been delegated, and report status accurately rather than guessing.
- **Team Shutdown reminder** — fires when a session is ending or a `team_dismiss` sweep is triggered. Ensures in-flight work is either completed, explicitly handed off, or clearly reported as abandoned — never silently dropped.

Both adapted near-verbatim from Piebald's extracted text, since the underlying problem (a coordinator losing track of delegated work) is identical regardless of domain.

---

## PART 8 — HONESTY & VERIFICATION (Fork Usage Guidelines, adapted)

Non-negotiable, carried from Piebald's Fork Usage Guidelines:

- Mitchell never reports a worker's task as complete without the worker's own structured completion report from the hive event log — no assuming success because "it's probably fine."
- Workers never fabricate a result if a step fails; the honest failure path (report failure to the hive, let Mitchell decide retry/escalate/inform-you) is always faster to recover from than a plausible-sounding lie, and this rule is treated as inviolable, not a style preference.

---

## PART 9 — BUILD ORDER

1. `agents/roles/*.md` — write the three pillar-worker role prompts first (adapted from Worker Fork), since everything else depends on them existing
2. `agents/hive.py` — mailbox/blackboard/event-log, async-batched git commits
3. `agents/team.py` — `team_spawn`/`team_message`/`team_status`/`team_dismiss`, wired to the hive
4. `core/warm_pool.py` — pre-spawn + auto-replenish, wired into Mitchell startup sequence (MITCHELL_CORE.md Part 10 step 8)
5. `core/team_reminders.py` — Team Coordination / Shutdown text
6. Wire `team_spawn` etc. into Mitchell's orchestrator as callable tools (MITCHELL_CORE.md Part 5's "hand off to the team" shape)
7. `coder` role — on-demand, PTY-wrapped, built last since it's not on the hot/warm path
8. Load-test the warm pool under concurrent multi-role dispatch, confirm the < 1s spawn budget holds under real conditions, not just idle-pool best case

---

## PART 10 — MAINTENANCE RULE

Same as MITCHELL_CORE.md: code is truth, this doc follows it, staleness is a bug. Additionally: **any change to the roster, hive schema, or warm-pool sizing must restate its effect on the `team_spawn` < 1s budget** — this doc exists specifically to keep speed a first-class, checked property of the design, not an afterthought.
