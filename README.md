# Mitchell

<p align="center">
  <strong>Autonomous Multi-Agent Hive, Cross-Platform Automation & Task Orchestration Framework</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#quickstart">Quickstart</a> •
  <a href="#automation-pillars">Automation Pillars</a> •
  <a href="#memory--skills">Memory & Skills</a> •
  <a href="#cloud-routing--inr-cost-tracking">Cloud Router</a> •
  <a href="#mcp-server">MCP Server</a> •
  <a href="#rest-api">REST API</a> •
  <a href="#cli-reference">CLI Reference</a>
</p>

---

## 🌟 Overview

**Mitchell** is a production-grade autonomous agent framework and multi-agent hive orchestrator designed around **Karpathy Engineering Principles** (*Think Before Acting*, *Simplicity First*, *Surgical Changes*, *Goal-Driven Execution*). 

Mitchell unifies cross-platform automation (**Playwright Browser**, **Native Windows UIA**, and **Wireless Android ADB**) with human-like input physics, persistent semantic memory (SQLite + Vector RAG), multi-model cloud routing (Grok, DeepSeek, OpenAI, Gemini, Anthropic), real-time INR (₹) cost tracking, a floating Electron Orb shell, and a standard Model Context Protocol (MCP) server.

---

## 🏗️ Architecture

```mermaid
flowchart TD
    User([User / CLI / Orb UI / REST API / MCP Client]) --> Manager[Manager Decision Loop]
    Manager --> FastIntent[Fast Intent Shortcut]
    Manager --> MemoryTier[(SQLite + Vector RAG)]
    Manager --> GoalClassifier[Goal Classifier & Routing]
    GoalClassifier --> TaskPlanner[Task Graph Planner]
    TaskPlanner --> PlanCritic[Plan Critic & Safety Pass]
    PlanCritic --> LLMCouncil[Selective LLM Council]
    LLMCouncil --> TaskScheduler[Dynamic TaskGraph Scheduler]
    
    TaskScheduler --> SharedBlackboard[(Shared Hive Blackboard)]
    TaskScheduler --> TeamCoordinator[Team Coordinator]
    
    TeamCoordinator --> ResearchTeam[Research Team (Browser + Vision)]
    TeamCoordinator --> CrossDeviceTeam[Cross-Device Team (Windows + Android + Vision)]
    TeamCoordinator --> OptimizationTeam[Optimization Team (Autoresearch)]
    
    TeamCoordinator --> HiveRouter[Hive Message Router]
    HiveRouter --> BrowserWorker[Browser Worker (Playwright + Stealth + Human Mouse)]
    HiveRouter --> WindowsWorker[Windows Worker (pywinauto + Bezier Cursor)]
    HiveRouter --> AndroidWorker[Android Worker (Wireless ADB + Human Touch)]
    HiveRouter --> VisionWorker[Vision Worker (Screen Grounding)]
    HiveRouter --> EfficiencyWorker[Efficiency Worker (Prompt Compression)]
    HiveRouter --> EchoAgent[Echo Agent]
    
    Manager --> DeepResearcher[Autonomous Deep Web Researcher]
    Manager --> VisualGrounder[Visual Grounding Engine]
    Manager --> SkillExecutor[Skill Executor Engine]
    Manager --> SkillLearner[Search -> Learn -> Remember Pipeline]
    Manager --> TeachingWatcher[Interactive 'Watch Me' Mode]
    Manager --> CostTracker[INR Cost & Token Tracker]
    Manager --> RecoveryEngine[Checkpoint & Recovery Engine]
    Manager --> LockManager[Global Resource Lock Manager]
    Manager --> APIServer[Live REST API & Webhook Server]
    Manager --> MCPServer[Standard MCP Stdio Server]
```

---

## ✨ Features

- 🛸 **Floating Electron Orb UI**: Always-on-top, frameless glowing circular orb with live event logs drawer and glassmorphism chat panel connected via WebSocket bridge (`ws://127.0.0.1:8765`).
- 🌐 **Browser Pillar (Playwright)**: Multi-session persistent profile manager, human-like Cubic Bezier mouse curves with micro-jitter and dwell times, stealth evasions (`navigator.webdriver` masking), and heuristic Captcha detection (Cloudflare Turnstile, reCAPTCHA, hCaptcha, Geetest, AWS WAF).
- 🪟 **Windows Desktop Pillar**: Native desktop control via `pywinauto` (UIA + Win32 fallback), accessibility tree inspection, OS-level Bezier cursor driver, and window screenshot capture.
- 📱 **Android Mobile Pillar**: Automated one-time USB → Wireless TCP/IP setup (`adb tcpip 5555` + `adb connect <IP>:5555`), device registry (`data/devices.json`), human-like curved swipes, and UI hierarchy dumping.
- 🧠 **Full Memory & Introspective Self-Model**: 
  - Working, Long-Term (facts/preferences), and Episodic (full historic job logs) storage in SQLite (`data/memory.sqlite3`).
  - Local normalized semantic vector store with cosine similarity RAG search.
  - Self-Model tracking capability inventory, confidence ratings, success rate (%), latency, and known gaps.
- ⚡ **Procedural Skill System & Search-Learn-Remember Pipeline**:
  - Structured skill schema with parameter templating (`{{param}}`) and `on_fail` policies (`retry`, `fallback`, `abort`).
  - Search → Learn → Remember pipeline autonomously synthesizing and indexing new skills upon encountering capability gaps.
- 🤖 **Thinking Decision Loop & Selective LLM Council**:
  - Goal Classifier + Task Graph Planner + Safety Critic pass.
  - Selective LLM Council convening safety, architecture, and execution perspectives for high-stakes decisions.
- 💸 **Multi-Model Cloud Router & INR (₹) Cost Tracking**:
  - Grok (xAI) as primary manager with fallback to high-efficiency worker models (DeepSeek, GPT-4o-mini, Gemini-1.5-flash).
  - Real-time token accounting with live conversion to Indian Rupees (₹) and daily/monthly budget caps.
- 👁️ **Multimodal Vision & Screen Grounding**:
  - Screenshot parser extracting visual bounding boxes and grounding natural language descriptions to pixel coordinates.
- 📋 **Shared Blackboard & Dynamic TaskGraph Scheduler**:
  - Asynchronous pub/sub blackboard state and parallel DAG scheduling with dependency resolution.
- 🎓 **Interactive "Watch Me" Teaching Mode**:
  - Human demonstration recorder automatically generalizing inputs into reusable procedural skills.
- 🔌 **Model Context Protocol (MCP) Server**:
  - Standard JSON-RPC 2.0 stdio server (`mitchell-mcp`) exposing all tools and skills to Claude Desktop, Cursor, and Antigravity.
- 🌐 **Live REST API & Webhooks**:
  - Built-in multi-threaded HTTP server (`mitchell serve`) with `/health`, `/api/v1/goal`, `/api/v1/tools`, `/api/v1/skills`, `/api/v1/cost`, and webhook ingestion.

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Sharry2429/mitchell.git
cd mitchell

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate # Linux/macOS

# Install package in editable mode with development dependencies
pip install -e ".[dev]"

# Install Playwright browser binaries
playwright install chromium
```

### 2. Environment Configuration

```bash
cp .env.example .env
```

Configure your API keys in `.env`:

```ini
MITCHELL_APP_NAME=Mitchell
MITCHELL_LOG_LEVEL=INFO

# Cloud LLM API Keys
XAI_API_KEY=your_grok_api_key
OPENAI_API_KEY=your_openai_api_key
DEEPSEEK_API_KEY=your_deepseek_api_key

# Orb & Server Ports
MITCHELL_ORB_HOST=127.0.0.1
MITCHELL_ORB_PORT=8765
```

---

## 💻 Running Mitchell

### Interactive Terminal REPL

```bash
mitchell
```

### One-Shot Goal Execution

```bash
mitchell do "Research latest trends on news.ycombinator.com and summarize findings"
```

### Electron Orb Floating Shell

```bash
# Terminal 1: Launch Python WebSocket bridge
mitchell orb

# Terminal 2: Launch Electron Orb
cd electron-orb
npm install
npm start
```

### Launch REST API Server

```bash
mitchell serve --port 8000
```

### Launch MCP Stdio Server

```bash
mitchell-mcp
```

### Interactive "Watch Me" Teaching Session

```bash
mitchell teach my_new_workflow --description "Demonstrated workflow"
```

### Recovery & Health Watchdog

```bash
mitchell health
mitchell recover
mitchell cost
```

---

## 🛠️ CLI Command Reference

| Command | Description |
| :--- | :--- |
| `mitchell` | Launch interactive terminal REPL |
| `mitchell do "<goal>"` | Execute a one-shot autonomous goal |
| `mitchell orb` | Start the WebSocket bridge server for Electron Orb |
| `mitchell serve` | Start the REST API and Webhook server |
| `mitchell-mcp` | Start the Model Context Protocol stdio server |
| `mitchell research "<topic>"` | Run autonomous deep web research across live sources |
| `mitchell teach <name>` | Start interactive "Watch Me" demonstration recording |
| `mitchell health` | Run comprehensive system health inspection |
| `mitchell recover` | Audit Event Log for interrupted tasks and recovery checkpoints |
| `mitchell cost` | Display token usage and cost accounting in INR (₹) |
| `mitchell version` | Display Mitchell version |

---

## 🧪 Testing

Run the comprehensive test suite across all pillars and systems:

```bash
python -m pytest tests/test_full_system.py -v
```

Run pillar demonstration scripts:

```bash
python scripts/demo_phase0.py   # Foundation
python scripts/demo_phase1.py   # Browser & Human Mouse
python scripts/demo_phase2.py   # Windows & Android
python scripts/demo_phase3.py   # Memory & Skills
python scripts/demo_phase4.py   # Thinking Loop & Cost
python scripts/demo_phase5.py   # Reliability & Teaching
```

---

## 📄 License

MIT License. Developed with precision by the Mitchell Team.
