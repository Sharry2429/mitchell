"""Mitchell Studio — Absolute Command Center.

Starlette-based application serving the Studio UI, WebSocket streaming,
and all API routes for the unified command surface.
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional


from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from mitchell.core.config import settings
from mitchell.core.cost import cost_tracker
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.core.providers import provider_registry
from mitchell.core.recovery import recovery_engine
from mitchell.hive.blackboard import blackboard
from mitchell.manager import Manager
from mitchell.memory.self_model import self_model
from mitchell.skills.library import skill_library
from mitchell.tools.registry import tool_registry


# ── Manager singleton ─────────────────────────────────────────────────────
_manager: Optional[Manager] = None


def get_manager() -> Manager:
    global _manager
    if _manager is None:
        _manager = Manager()
    return _manager


# ── WebSocket connection manager ──────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections for real-time streaming."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("Studio WebSocket connected. Active: {}", len(self.active_connections))

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info("Studio WebSocket disconnected. Active: {}", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        disconnected = []
        for conn in self.active_connections:
            try:
                await conn.send_json(message)
            except Exception:
                disconnected.append(conn)
        for conn in disconnected:
            self.disconnect(conn)

    async def send_to(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


ws_manager = ConnectionManager()


# ── Studio State Provider ─────────────────────────────────────────────────

class StudioStateProvider:
    """Aggregates live state across blackboard, costs, events, providers, and diagnostics."""

    def get_full_state(self) -> Dict[str, Any]:
        """Aggregate current snapshot of the Mitchell hive state."""
        state = {
            "blackboard": blackboard.dump_state(),
            "cost": cost_tracker.get_summary(),
            "recent_events": [e.model_dump(mode="json") for e in event_log.get_recent(n=25)],
            "providers": provider_registry.get_state(),
            "diagnostics": recovery_engine.run_diagnostics().model_dump(mode="json"),
        }
        return json.loads(json.dumps(state, default=str))


studio_state = StudioStateProvider()



# ── API Route Handlers ────────────────────────────────────────────────────

async def index(request: Request) -> HTMLResponse:
    """Serve the Studio command center UI."""
    studio_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "studio"
    index_file = studio_dir / "index.html"
    if index_file.exists():
        return HTMLResponse(index_file.read_text(encoding="utf-8"))
    # Fallback to legacy studio.html
    legacy = Path(__file__).resolve().parent.parent.parent / "docs" / "studio.html"
    if legacy.exists():
        return HTMLResponse(legacy.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Mitchell Studio</h1><p>Frontend not found.</p>", status_code=404)


async def api_state(request: Request) -> JSONResponse:
    """Full system state snapshot for Studio dashboard."""
    return JSONResponse(studio_state.get_full_state())


async def api_chat(request: Request) -> JSONResponse:
    """Process a chat message through the Manager."""
    body = await request.json()
    message = body.get("message", "")
    if not message:
        return JSONResponse({"error": "Missing 'message' field"}, status_code=400)

    manager = get_manager()

    # Broadcast thinking status
    await ws_manager.broadcast({"type": "status", "status": "thinking"})

    start = time.time()
    response = manager.receive(message)
    duration = round(time.time() - start, 2)

    # Broadcast response
    await ws_manager.broadcast({
        "type": "chat_response",
        "content": response,
        "duration": duration,
    })
    await ws_manager.broadcast({"type": "status", "status": "idle"})

    return JSONResponse({
        "message": message,
        "response": response,
        "duration": duration,
        "cost": cost_tracker.get_summary(),
    })


async def api_providers(request: Request) -> JSONResponse:
    """Provider management API."""
    if request.method == "GET":
        return JSONResponse(provider_registry.get_state())
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "")
        provider_name = body.get("provider", "")
        if action == "enable":
            provider_registry.enable_provider(provider_name)
        elif action == "disable":
            provider_registry.disable_provider(provider_name)
        elif action == "reset_health":
            provider_registry.reset_health(provider_name)
        return JSONResponse({"status": "ok", "providers": provider_registry.get_state()})
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_memory(request: Request) -> JSONResponse:
    """Memory browser API."""
    return JSONResponse({
        "self_model": self_model.get_full_state(),
        "cost": cost_tracker.get_summary(),
    })


async def api_tools(request: Request) -> JSONResponse:
    """List registered tools."""
    tools = tool_registry.list_tools()
    return JSONResponse({"tools": tools, "count": len(tools)})


async def api_skills(request: Request) -> JSONResponse:
    """List, install, or execute procedural skills."""
    from mitchell.skills.executor import skill_executor
    if request.method == "GET":
        skills = [s.model_dump(mode="json") for s in skill_library.list_skills()]
        return JSONResponse({"skills": skills, "count": len(skills)})
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "execute")
        if action == "execute":
            res = skill_executor.execute(body.get("name", ""), parameters=body.get("parameters", {}))
            return JSONResponse(res)
        elif action == "install_markdown":
            skill = skill_library.install_skill_markdown(body.get("markdown", ""), name=body.get("name"))
            return JSONResponse({"status": "success", "skill": skill.model_dump(mode="json")})
        elif action == "delete":
            deleted = skill_library.delete_skill(body.get("name", ""))
            return JSONResponse({"status": "deleted" if deleted else "not_found"})
        return JSONResponse({"error": f"Unknown skill action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_plugins(request: Request) -> JSONResponse:
    """Plugin and Marketplace catalog API."""
    from mitchell.plugins import plugin_installer, plugin_loader, plugin_marketplace
    if request.method == "GET":
        plugin_loader.discover_and_load_all()
        installed = plugin_loader.list_plugins()
        marketplace = [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "marketplace": p.marketplace,
                "category": p.category,
                "tags": p.tags,
                "has_mcp": p.has_mcp,
                "has_skills": p.has_skills,
                "installed": any(i["name"].lower() == p.name.lower() for i in installed),
            }
            for p in plugin_marketplace.search_catalog()
        ]
        return JSONResponse({
            "installed": installed,
            "marketplace": marketplace,
            "installed_count": len(installed),
            "marketplace_count": len(marketplace),
        })
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "install")
        target = body.get("plugin", body.get("source", ""))
        if not target:
            return JSONResponse({"error": "Missing plugin target"}, status_code=400)
        if action == "install":
            res = plugin_installer.install(target, marketplace=body.get("marketplace"))
            return JSONResponse(res)
        elif action == "uninstall":
            res = plugin_installer.uninstall(target)
            return JSONResponse(res)
        return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_mcp(request: Request) -> JSONResponse:
    """Model Context Protocol (MCP) server management API."""
    from mitchell.mcp_client.hub import mcp_hub
    if request.method == "GET":
        return JSONResponse({
            "servers": mcp_hub.list_servers(),
            "count": len(mcp_hub.clients),
        })
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "add")
        server_name = body.get("server_name", "")
        if action == "add":
            command = body.get("command", "")
            args = body.get("args", [])
            env = body.get("env", {})
            client = mcp_hub.add_stdio_server(server_name, command=command, args=args, env=env)
            return JSONResponse({
                "status": "connected" if client.is_connected else "failed",
                "server_name": server_name,
                "tools": client.list_remote_tools(),
            })
        elif action == "remove":
            res = mcp_hub.remove_server(server_name)
            return JSONResponse({"status": "removed" if res else "not_found"})
        elif action == "call":
            client = mcp_hub.get_client(server_name)
            if not client:
                return JSONResponse({"error": f"Server '{server_name}' not found"}, status_code=404)
            tool_name = body.get("tool_name", "")
            args = body.get("arguments", {})
            res = client.call_tool(tool_name, arguments=args)
            return JSONResponse(res)
        return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_agents(request: Request) -> JSONResponse:
    """List hive agents and task graph state."""
    from mitchell.hive.router import hive_router
    agents = hive_router.list_agents()
    return JSONResponse({
        "agents": agents,
        "blackboard": blackboard.dump_state(),
    })


async def api_diagnostics(request: Request) -> JSONResponse:
    """System diagnostics report."""
    report = recovery_engine.run_diagnostics()
    return JSONResponse(report.model_dump(mode="json"))


async def api_search(request: Request) -> JSONResponse:
    """Unified search across memory, tools, skills."""
    body = await request.json()
    query = body.get("query", "")
    if not query:
        return JSONResponse({"error": "Missing query"}, status_code=400)

    from mitchell.memory.long_term import long_term_memory
    mem_results = long_term_memory.search(query, top_k=5)
    skill_results = skill_library.search_skills(query, top_k=5)

    return JSONResponse({
        "query": query,
        "memory": mem_results,
        "skills": [{"name": s.name, "description": s.description} for s in skill_results],
    })


async def api_settings(request: Request) -> JSONResponse:
    """Settings read/write API with full API key persistence."""
    import os
    env_file = Path(__file__).resolve().parent.parent.parent / ".env"

    if request.method == "GET":
        return JSONResponse({
            "app_name": settings.app_name,
            "debug": settings.debug,
            "log_level": settings.log_level,
            "studio_port": settings.studio_port,
            "provider_cascade": settings.provider_cascade_list,
            "free_tier_first": settings.free_tier_first,
            "sync_enabled": settings.sync_enabled,
            "voice_wake_word": settings.voice_wake_word,
            "voice_stt_provider": settings.voice_stt_provider,
            "homeassistant_url": settings.homeassistant_url or os.environ.get("HOMEASSISTANT_URL", ""),
            "keys_configured": {
                "anthropic": bool(settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")),
                "openai": bool(settings.openai_api_key or os.environ.get("OPENAI_API_KEY")),
                "xai": bool(settings.xai_api_key or os.environ.get("XAI_API_KEY")),
                "gemini": bool(settings.gemini_api_key or os.environ.get("GEMINI_API_KEY")),
                "groq": bool(settings.groq_api_key or os.environ.get("GROQ_API_KEY")),
                "deepseek": bool(settings.deepseek_api_key or os.environ.get("DEEPSEEK_API_KEY")),
                "openrouter": bool(settings.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY")),
                "homeassistant": bool(settings.homeassistant_token or os.environ.get("HOMEASSISTANT_TOKEN")),
            },
        })
    elif request.method == "POST":
        body = await request.json()
        keys_map = {
            "anthropic_api_key": "ANTHROPIC_API_KEY",
            "openai_api_key": "OPENAI_API_KEY",
            "xai_api_key": "XAI_API_KEY",
            "gemini_api_key": "GEMINI_API_KEY",
            "groq_api_key": "GROQ_API_KEY",
            "deepseek_api_key": "DEEPSEEK_API_KEY",
            "openrouter_api_key": "OPENROUTER_API_KEY",
            "homeassistant_url": "HOMEASSISTANT_URL",
            "homeassistant_token": "HOMEASSISTANT_TOKEN",
        }

        env_lines = []
        if env_file.exists():
            env_lines = env_file.read_text(encoding="utf-8").splitlines()

        updated_keys = set()
        for field, env_var in keys_map.items():
            if field in body and body[field]:
                val = body[field].strip()
                os.environ[env_var] = val
                setattr(settings, field, val)
                updated_keys.add(env_var)
                # Replace or append in .env
                found = False
                for idx, line in enumerate(env_lines):
                    if line.startswith(f"{env_var}=") or line.startswith(f"MITCHELL_{env_var}="):
                        env_lines[idx] = f"{env_var}={val}"
                        found = True
                        break
                if not found:
                    env_lines.append(f"{env_var}={val}")

        if updated_keys:
            env_file.write_text("\n".join(env_lines) + "\n", encoding="utf-8")
            logger.info("Saved and updated {} configuration keys to .env", len(updated_keys))

        return JSONResponse({"status": "saved", "updated": list(updated_keys)})
    return JSONResponse({"error": "Method not allowed"}, status_code=405)



async def api_workspace(request: Request) -> JSONResponse:
    """Workspace items summary and listing."""
    from mitchell.workspace import workspace_manager, workspace_storage
    sub = request.query_params.get("section", "summary")
    if sub == "summary":
        return JSONResponse(workspace_manager.get_summary())
    elif sub == "documents":
        return JSONResponse({"documents": workspace_manager.documents.list_documents()})
    elif sub == "spreadsheets":
        return JSONResponse({"spreadsheets": workspace_storage.list_files(sub_dir="spreadsheets")})
    elif sub == "notes":
        return JSONResponse({"notes": workspace_manager.notes.list_notes(), "graph": workspace_manager.notes.get_knowledge_graph()})
    elif sub == "projects":
        return JSONResponse({"projects": workspace_manager.projects.list_boards()})
    elif sub == "mail":
        return JSONResponse({"mail": workspace_manager.mail.list_emails()})
    elif sub == "calendar":
        return JSONResponse({"events": workspace_manager.calendar.list_upcoming_events(days=14)})
    elif sub == "files":
        return JSONResponse({"files": workspace_storage.list_files()})
    return JSONResponse({"error": "Unknown workspace section"}, status_code=400)


async def api_ide(request: Request) -> JSONResponse:
    """Agentic IDE operations."""
    from mitchell.ide import code_editor, code_runner, git_manager, platform_bridges, project_scaffolder, terminal_manager
    if request.method == "GET":
        root = request.query_params.get("root", os.getcwd())
        return JSONResponse({
            "projects": project_scaffolder.list_projects(),
            "tools": [t.model_dump() for t in platform_bridges.scan_installed_tools()],
            "file_tree": project_scaffolder.get_directory_tree(root),
        })
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "")
        if action == "create_project":
            manifest = project_scaffolder.create_project(name=body.get("name", "app"), template=body.get("template", "python"))
            return JSONResponse(manifest.model_dump(mode="json"))
        elif action == "read_file":
            content = code_editor.read_file(body.get("path", ""))
            return JSONResponse({"content": content})
        elif action == "write_file":
            res = code_editor.write_file(body.get("path", ""), body.get("content", ""))
            return JSONResponse(res.model_dump(mode="json"))
        elif action == "run_command":
            res = terminal_manager.run_command(body.get("command", ""), cwd=body.get("cwd"))
            return JSONResponse(res.model_dump(mode="json"))
        elif action == "git_status":
            st = git_manager.status(body.get("cwd"))
            return JSONResponse(st.model_dump(mode="json"))
        elif action == "run_tests":
            res = code_runner.run_tests(cwd=body.get("cwd"), test_path=body.get("test_path"))
            return JSONResponse(res.model_dump(mode="json"))
        elif action == "file_tree":
            tree = project_scaffolder.get_directory_tree(body.get("root", os.getcwd()))
            return JSONResponse(tree)
        return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_harness(request: Request) -> JSONResponse:
    """Multi-Agent Coding Harness (Under One Roof) API."""
    from mitchell.ide.agent_harness import agent_harness
    if request.method == "GET":
        return JSONResponse({
            "supported_agents": agent_harness.get_supported_agents(),
            "active_sessions": [s.model_dump(mode="json") for s in agent_harness.list_sessions()],
        })
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "start")
        if action == "start":
            agent_id = body.get("agent_id", "claude")
            prompt = body.get("prompt", "")
            cwd = body.get("cwd")
            session = await agent_harness.start_agent_task(agent_id=agent_id, prompt=prompt, cwd=cwd)
            return JSONResponse(session.model_dump(mode="json"))
        elif action == "stop":
            session_id = body.get("session_id", "")
            stopped = await agent_harness.stop_session(session_id)
            return JSONResponse({"status": "stopped" if stopped else "not_found"})
        elif action == "get_session":
            session_id = body.get("session_id", "")
            sess = agent_harness.get_session(session_id)
            return JSONResponse(sess.model_dump(mode="json") if sess else {"error": "not_found"}, status_code=200 if sess else 404)
        return JSONResponse({"error": f"Unknown harness action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_documents(request: Request) -> JSONResponse:
    """Native Document Workspace API."""
    from mitchell.workspace.documents import document_engine
    if request.method == "GET":
        doc_id = request.query_params.get("id")
        if doc_id:
            doc = document_engine.load_document(doc_id)
            return JSONResponse(doc.model_dump(mode="json") if doc else {"error": "not_found"}, status_code=200 if doc else 404)
        return JSONResponse({"documents": document_engine.list_documents()})
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "save")
        if action == "save":
            from mitchell.workspace.documents import WorkspaceDocument
            doc = WorkspaceDocument(
                doc_id=body.get("doc_id", "doc"),
                title=body.get("title", "Untitled"),
                content=body.get("content", ""),
                author=body.get("author", "user"),
            )
            document_engine.save_document(doc, change_summary=body.get("change_summary", ""))
            return JSONResponse({"status": "saved", "doc_id": doc.doc_id})
        elif action == "generate_report":
            topic = body.get("topic", "System Report")
            content = body.get("content")
            doc = document_engine.generate_report(topic=topic, content_markdown=content)
            return JSONResponse({"status": "generated", "document": doc.model_dump(mode="json")})
        return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_research(request: Request) -> JSONResponse:
    """Perplexity-Style Deep Research API."""
    from mitchell.browser.deep_research import deep_research_engine
    if request.method == "GET":
        return JSONResponse({"history": [r.model_dump(mode="json") for r in deep_research_engine.history]})
    elif request.method == "POST":
        body = await request.json()
        query = body.get("query", "")
        if not query:
            return JSONResponse({"error": "Missing 'query' field"}, status_code=400)
        res = await deep_research_engine.execute_research(query=query, max_sources=body.get("max_sources", 5))
        return JSONResponse(res.model_dump(mode="json"))
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_iot(request: Request) -> JSONResponse:
    """Home Assistant & IoT API."""
    from mitchell.iot.homeassistant import homeassistant_client
    if request.method == "GET":
        states = await homeassistant_client.get_states()
        return JSONResponse({
            "configured": homeassistant_client.is_configured(),
            "entities": [s.model_dump(mode="json") for s in states],
        })
    elif request.method == "POST":
        body = await request.json()
        domain = body.get("domain", "light")
        service = body.get("service", "turn_on")
        entity_id = body.get("entity_id", "")
        data = body.get("service_data", {})
        res = await homeassistant_client.call_service(domain, service, entity_id, service_data=data)
        return JSONResponse(res)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_teaching(request: Request) -> JSONResponse:
    """Teaching & Skill Synthesis API."""
    from mitchell.teaching.recorder import ActionRecorder
    from mitchell.teaching.synthesizer import skill_synthesizer
    if request.method == "GET":
        return JSONResponse({"status": "ready"})
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "synthesize")
        if action == "synthesize":
            actions_data = body.get("actions", [])
            recorder = ActionRecorder()
            for a in actions_data:
                recorder.add_action(
                    action_type=a.get("action_type", "tool"),
                    target=a.get("target", ""),
                    params=a.get("params", {}),
                    timestamp=a.get("timestamp", time.time()),
                )
            name = body.get("name", "taught_skill")
            res = skill_synthesizer.synthesize_from_recorder(recorder, name=name, description=body.get("description", ""))
            return JSONResponse(res.model_dump(mode="json"))
        return JSONResponse({"error": f"Unknown teaching action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_takeover(request: Request) -> JSONResponse:
    """Task Takeover & Human Approval Gates API."""
    from mitchell.action.takeover import takeover_engine
    if request.method == "GET":
        session_id = request.query_params.get("session_id")
        if session_id:
            s = takeover_engine.get_session(session_id)
            return JSONResponse(s.model_dump(mode="json") if s else {"error": "not_found"}, status_code=200 if s else 404)
        return JSONResponse({"sessions": [s.model_dump(mode="json") for s in takeover_engine.list_sessions()]})
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "start")
        if action == "start":
            goal = body.get("goal", "")
            s = takeover_engine.start_takeover(goal=goal)
            return JSONResponse(s.model_dump(mode="json"))
        elif action == "advance":
            session_id = body.get("session_id", "")
            s = takeover_engine.advance_step(session_id, success=body.get("success", True), summary=body.get("summary", ""))
            return JSONResponse(s.model_dump(mode="json") if s else {"error": "not_found"})
        elif action == "approve_gate":
            session_id = body.get("session_id", "")
            s = takeover_engine.approve_gate(session_id)
            return JSONResponse(s.model_dump(mode="json") if s else {"error": "not_found"})
        return JSONResponse({"error": f"Unknown takeover action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


async def api_browser_real(request: Request) -> JSONResponse:
    """Real Browser Profile & CDP Attachment API."""
    from mitchell.browser.cdp_attach import real_browser_manager
    if request.method == "GET":
        profiles = real_browser_manager.find_user_profiles()
        page_info = await real_browser_manager.get_page_info()
        return JSONResponse({
            "profiles": [p.model_dump(mode="json") for p in profiles],
            "active_page": page_info,
        })
    elif request.method == "POST":
        body = await request.json()
        action = body.get("action", "attach")
        if action == "attach":
            res = await real_browser_manager.attach_real_profile(
                user_data_dir=body.get("user_data_dir"),
                profile_directory=body.get("profile_directory", "Default"),
                headless=body.get("headless", False),
            )
            return JSONResponse(res)
        elif action == "close":
            await real_browser_manager.close()
            return JSONResponse({"status": "closed"})
        return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
    return JSONResponse({"error": "Method not allowed"}, status_code=405)


# ── WebSocket Handler ─────────────────────────────────────────────────────

async def ws_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint for real-time Studio communication."""
    await ws_manager.connect(websocket)

    # Send initial state
    await ws_manager.send_to(websocket, {
        "type": "init",
        "status": "idle",
        "providers": provider_registry.get_state(),
        "cost": cost_tracker.get_summary(),
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "message":
                # Chat message
                content = data.get("content", "")
                await ws_manager.send_to(websocket, {"type": "status", "status": "thinking"})

                manager = get_manager()
                start = time.time()
                response = manager.receive(content)
                duration = round(time.time() - start, 2)

                await ws_manager.send_to(websocket, {
                    "type": "response",
                    "content": response,
                    "duration": duration,
                    "status": "idle",
                })

            elif msg_type == "get_state":
                await ws_manager.send_to(websocket, {
                    "type": "state",
                    "blackboard": blackboard.dump_state(),
                    "cost": cost_tracker.get_summary(),
                    "events": [e.model_dump(mode="json") for e in event_log.get_recent(10)],
                })

            elif msg_type == "get_events":
                await ws_manager.send_to(websocket, {
                    "type": "events",
                    "events": [e.model_dump(mode="json") for e in event_log.get_recent(20)],
                })

            elif msg_type == "ping":
                await ws_manager.send_to(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error("WebSocket error: {}", e)
        ws_manager.disconnect(websocket)


# ── Application Factory ──────────────────────────────────────────────────

def create_studio_app() -> Starlette:
    """Create the Studio Starlette application."""
    studio_static_dir = Path(__file__).resolve().parent.parent.parent / "docs" / "studio"
    studio_static_dir.mkdir(parents=True, exist_ok=True)

    routes = [
        Route("/", endpoint=index),
        Route("/studio", endpoint=index),

        # API routes
        Route("/api/state", endpoint=api_state),
        Route("/api/chat", endpoint=api_chat, methods=["POST"]),
        Route("/api/providers", endpoint=api_providers, methods=["GET", "POST"]),
        Route("/api/memory", endpoint=api_memory),
        Route("/api/tools", endpoint=api_tools),
        Route("/api/skills", endpoint=api_skills, methods=["GET", "POST"]),
        Route("/api/plugins", endpoint=api_plugins, methods=["GET", "POST"]),
        Route("/api/mcp", endpoint=api_mcp, methods=["GET", "POST"]),
        Route("/api/agents", endpoint=api_agents),
        Route("/api/diagnostics", endpoint=api_diagnostics),
        Route("/api/search", endpoint=api_search, methods=["POST"]),
        Route("/api/settings", endpoint=api_settings, methods=["GET", "POST"]),
        Route("/api/workspace", endpoint=api_workspace, methods=["GET"]),

        Route("/api/ide", endpoint=api_ide, methods=["GET", "POST"]),
        Route("/api/harness", endpoint=api_harness, methods=["GET", "POST"]),
        Route("/api/documents", endpoint=api_documents, methods=["GET", "POST"]),
        Route("/api/research", endpoint=api_research, methods=["GET", "POST"]),
        Route("/api/iot", endpoint=api_iot, methods=["GET", "POST"]),
        Route("/api/teaching", endpoint=api_teaching, methods=["GET", "POST"]),
        Route("/api/takeover", endpoint=api_takeover, methods=["GET", "POST"]),
        Route("/api/browser/real", endpoint=api_browser_real, methods=["GET", "POST"]),

        # WebSocket
        WebSocketRoute("/ws", endpoint=ws_endpoint),

        # Static files
        Mount("/css", app=StaticFiles(directory=str(studio_static_dir / "css"), check_dir=False), name="css"),
        Mount("/js", app=StaticFiles(directory=str(studio_static_dir / "js"), check_dir=False), name="js"),
        Mount("/static", app=StaticFiles(directory=str(studio_static_dir), check_dir=False), name="static"),
    ]

    app = Starlette(routes=routes, debug=settings.debug)


    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app



studio_app = create_studio_app()


class MitchellStudioServer:
    """Manages the Studio command center server lifecycle."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None) -> None:
        self.host = host or settings.studio_host
        self.port = port or settings.studio_port

    def start(self) -> None:
        """Start the Studio server with uvicorn."""
        import uvicorn
        logger.info("Mitchell Studio Command Center starting at http://{}:{}", self.host, self.port)
        uvicorn.run(studio_app, host=self.host, port=self.port, log_level="warning")


__all__ = [
    "MitchellStudioServer",
    "studio_app",
    "create_studio_app",
    "ws_manager",
    "StudioStateProvider",
    "studio_state",
]
