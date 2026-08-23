# 🤖 Mitchell AI — Autonomous Multi-Agent Hive & Living Operating System (2026 Peak)

<p align="center">
  <img src="https://img.shields.io/badge/Release-2026%20Peak%20Maximum-blueviolet?style=for-the-badge" alt="Release">
  <img src="https://img.shields.io/badge/Tests-43%2F43%20Passing%20(100%25)-brightgreen?style=for-the-badge" alt="Tests">
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/WhatsApp%20MCP-Integrated-25D366?style=for-the-badge&logo=whatsapp" alt="WhatsApp MCP">
  <img src="https://img.shields.io/badge/License-MIT-amber?style=for-the-badge" alt="License">
</p>

**Mitchell AI** is a self-hosted, self-extending, native-first personal AI operating system. Engineered with **Karpathy Principles of Rigor** (*Think Before Acting, Simplicity First, Surgical Changes, Goal-Driven Execution*), Mitchell seamlessly unifies your desktop, mobile, cloud models, native workspace, and home automation into one continuous machine.

---

## 🌟 Master Architecture

```mermaid
flowchart TB
    subgraph UI ["User Interfaces"]
        Studio["Mitchell Studio (Command Center · 16 Panels)"]
        Orb["The Orb v2 (7 State Living Interface)"]
        CLI["Mitchell CLI / Fast Intents / Daemon Butler"]
        WebDocs["Web Homepage & Interactive Docs"]
    end

    subgraph Intelligence ["Core Intelligence & Memory"]
        Prompts["Karpathy System Prompts & Dynamic Context Builder"]
        Router["ModelRouter (Claude 3.7 / Groq / OpenAI o3 / Gemini 2.0)"]
        SelfModel["SelfModel & UserModel (Preferences / Procedural / Semantic Graph)"]
        Consolidator["MemoryConsolidator & MediumTermMemory"]
        Recovery["RecoveryEngine & Novel Failure Handling"]
    end

    subgraph Hive ["Specialized Hive Worker Agents"]
        BrowserWorker["BrowserWorkerAgent (Playwright + Stealth)"]
        WindowsWorker["WindowsWorkerAgent (Desktop/Win32)"]
        AndroidWorker["AndroidWorkerAgent (ADB/scrcpy)"]
        WorkspaceWorker["WorkspaceWorkerAgent (Docs/Sheets/Notes/Kanban)"]
        IDEWorker["IDEWorkerAgent (Editor/Terminal/Git/Pytest)"]
        CommsWorker["CommsWorkerAgent (WhatsApp MCP/SMS/Calls)"]
        MediaWorker["MediaWorkerAgent (Spotify/Downloads/YouTube)"]
        CommerceWorker["CommerceWorkerAgent (Price Tracker/Deals)"]
        IoTWorker["IoTWorkerAgent (Home Assistant/Scenes)"]
    end

    subgraph Integrations ["Protocols & Bridges"]
        WhatsAppMCP["WhatsApp MCP Bridge (lharries/whatsapp-mcp)"]
        TelemetryEngine["Live Telemetry & Dynamic Briefing Engine"]
        MCPHub["Universal MCP Client Hub"]
    end

    UI <--> Intelligence
    Intelligence <--> Hive
    CommsWorker <--> WhatsAppMCP
    Intelligence <--> TelemetryEngine
    WhatsAppMCP <--> MCPHub
```

---

## ⚡ Key Capabilities (2026 Practical Maximum)

### 1. Mitchell Studio Command Center
- Full-screen dark glassmorphism dashboard with 16 panels:
  - **Live Chat** with streaming LLM response tokens and auto-fallback
  - **Native Workspace** (Docs, Spreadsheets, Linked Notes, Kanban Project Boards)
  - **Agentic IDE** with Monaco editor, syntax validation, diffs, and terminal execution
  - **WhatsApp MCP & Unified Comms** (WhatsApp, SMS, Email, Scheduled Messages)
  - **Media Center** (Spotify playback, IDM-style download manager, YouTube downloader)
  - **Commerce Hub** (Product comparison, price-drop alert tracker, coupon finder)
  - **Smart Home IoT** (Home Assistant integration, lights, climate, smart scenes)
  - **Memory Graph** (Episodic, Semantic Graph Triples, User Model Preferences)
  - **System Diagnostics & Telemetry**
- Launch instantly via: `python -m mitchell.cli studio` or `mitchell studio`

### 2. WhatsApp MCP Integration ([lharries/whatsapp-mcp](https://github.com/lharries/whatsapp-mcp))
- Native integration with the official `whatsapp-mcp` protocol:
  - `send_message(recipient, message)`
  - `list_messages(chat_jid, limit)`
  - `list_chats(limit)`
  - `search_contacts(query)`
  - `send_media(recipient, media_path, caption)`
  - `get_last_interaction(contact)`
- Unified inbox message recording and web intent fallback.

### 3. Dynamic System Telemetry & Executive Briefing Engine
- **Live Hardware Telemetry**: Real-time CPU, RAM, Disk storage, and Battery percentage metrics.
- **Executive Daily Briefing**: Synthesizes schedule, pending Kanban cards, unread WhatsApp messages, and hardware health into morning/evening briefings.
- **Executive Voice Persona**: Conversational speech acknowledgments and status reporting.

### 4. Claude Plugins & Autonomous MCP Subsystem ([claude-plugins-official](https://github.com/anthropics/claude-plugins-official))
- **Official Claude Marketplace Catalog**: Pre-seeded official plugins (`github`, `sqlite`, `postgresql`, `fetch`, `memory`, `docker`, `python-lsp`, `typescript-lsp`, `puppeteer`, `filesystem`).
- **Universal MCP Client Hub**: Real-time stdio JSON-RPC 2.0 subprocess manager bridging remote tools directly into Mitchell's ToolRegistry.
- **Procedural `SKILL.md` Engine**: Parses YAML frontmatter and markdown procedural steps with variable substitution and error fallback policies.
- **Autonomous AI Self-Extension**: Mitchell AI can autonomously install plugins, create procedural skills, and connect MCP servers via native tool calls (`plugin_install`, `skill_install`, `mcp_add_server`).

### 5. SOTA 2026 Model Cascade & Free-Tier First
- Live model switching across 8 LLM providers:
  - **Anthropic**: Claude 3.7 Sonnet (`claude-3-7-sonnet-20250219`, `claude-3-7-sonnet`), Claude 3.5 Sonnet, Claude 3.5 Haiku
  - **Groq (Free Tier)**: Llama 3.3 70B Versatile, Llama 3.1 8B Instant, Gemma 2 9B
  - **NVIDIA NIM (Free Tier)**: Llama 3.1 405B Instruct, Llama 3.1 70B
  - **OpenRouter (Free Tier)**: Qwen 2.5 72B Instruct, Llama 3.1 8B
  - **Google Gemini (Free Tier)**: Gemini 2.0 Flash, Gemini 1.5 Flash, Gemini 1.5 Pro
  - **OpenAI**: GPT-4o, GPT-4o-mini, o3-mini, o1
  - **xAI**: Grok-2, Grok-beta
  - **DeepSeek**: DeepSeek-V3 Chat, DeepSeek-R1 Reasoner

---

## 🚀 Quickstart & Usage

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Sharry2429/mitchell.git
cd mitchell

# Install dependencies in editable mode
pip install -e .
```

### 2. Launch Studio Command Center
```bash
python -m mitchell.cli studio
```
Opens the Studio UI in your browser at `http://localhost:8500`.

### 3. CLI Commands & Fast Intents
```bash
# Install an official Claude plugin
python -m mitchell.cli plugin install github

# List and run procedural skills
python -m mitchell.cli skill list
python -m mitchell.cli skill run web_research_and_snapshot --params '{"url": "https://news.ycombinator.com"}'

# Connect an external MCP server
python -m mitchell.cli mcp add sqlite npx -y @modelcontextprotocol/server-sqlite

# Send a WhatsApp message via WhatsApp MCP
python -m mitchell.cli goal "whatsapp +14155550000 Meeting starts in 10 minutes"

# Play Spotify music
python -m mitchell.cli goal "spotify lofi beats for focus"

# Generate executive daily briefing
python -m mitchell.cli goal "briefing"

# Check live system hardware telemetry
python -m mitchell.cli goal "telemetry"

# Run tests and verify code
python -m mitchell.cli goal "pytest"
```

### 4. 24/7 Butler Daemon Mode
```bash
python -m mitchell.cli butler
```

---

## 🧪 Verification & Testing

Run the complete test suite:
```bash
python -m pytest tests/ -v
```
```text
============================= 52 passed in 31.04s =============================
```
100% of all 52 tests pass across:
- `tests/test_full_system.py` (26 tests)
- `tests/test_peak_capabilities.py` (12 tests)
- `tests/test_plugins_and_mcp.py` (8 tests)
- `tests/test_whatsapp_mcp_and_refinements.py` (6 tests)

---

## 📄 License
MIT License. Created by Sharry2429.
