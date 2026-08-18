#!/usr/bin/env python3
"""
Mitchell API - Single-file cascade router service.

Setup + run in one command:
    python mitchell/api.py

Cascade Modes:
    ⚡ Fast          - lowest latency, good-enough quality
    🧠 Intelligent   - best reasoning quality, latency secondary
    🛡️ Never-Fails   - always returns something, free-tier safety net

Auto-routing:
    When mode=auto (default), Mitchell infers the best mode from message
    length/complexity. The caller can always override with mode=fast|intelligent|never_fails.

Load balancing:
    - Per-provider sliding-window request counter (60s window)
    - Adaptive cooldown scaled by HTTP status (429→5s, 5xx→2s, other→0.5s)
    - Preemptive skip when provider is near estimated rate limit

Env vars expected (create a .env file next to this script, or set them in your shell):
    NVIDIA_API_KEY
    GROQ_API_KEY
    OPENROUTER_API_KEY
    GEMINI_LOCAL_BASE_URL      (default: http://localhost:8081/v1)
    OMNIROUTE_BASE_URL         (default: http://localhost:20128/v1)
    MITCHELL_API_PORT          (default: 7000)
"""

import os
import sys
import json
import time
import math
import shutil
import subprocess
import threading
import collections
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency bootstrap - install missing python packages automatically
# ---------------------------------------------------------------------------
REQUIRED_PIP_PACKAGES = ["fastapi", "uvicorn", "httpx", "python-dotenv", "python-multipart"]


def ensure_pip_packages():
    missing = []
    for pkg in REQUIRED_PIP_PACKAGES:
        mod_name = pkg.replace("-", "_")
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[setup] Installing missing Python packages: {', '.join(missing)}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--break-system-packages", *missing],
            check=False,
        )


ensure_pip_packages()

import httpx  # noqa: E402
import asyncio
from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse  # noqa: E402
from fastapi import UploadFile, File, Form  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
PORT = int(os.environ.get("MITCHELL_API_PORT", "7000"))
GEMINI_LOCAL_BASE_URL = os.environ.get("GEMINI_LOCAL_BASE_URL", "http://localhost:8081/v1")
OMNIROUTE_BASE_URL = os.environ.get("OMNIROUTE_BASE_URL", "http://localhost:20128/v1")

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ---------------------------------------------------------------------------
# Provider registry (inventory — used for model discovery + /v1/models)
# ---------------------------------------------------------------------------
PROVIDERS = [
    {
        "id": "omniroute",
        "label": "Omniroute (local)",
        "model_class": "Worker",
        "base_url": OMNIROUTE_BASE_URL,
        "api_key": "sk-e8d31cbd165e1ed3-d118ac-a9fc3170",
        "optional": True,
        "rate_limit_rps": 50,
        "models": [
            "auto/best-coding", "auto/best-reasoning", "auto/best-fast",
            "auto/best-chat", "auto/best-vision",
            "auto/pro-coding", "auto/pro-reasoning", "auto/pro-chat",
            "auto/coding:fast", "auto/coding:cheap", "auto/coding:free",
            "auto/cheap", "auto/offline", "auto/smart",
            "auto/claude-opus", "auto/claude-sonnet",
            "antigravity/gemini-3.6-flash-high",
            "antigravity/gemini-3.6-flash-medium",
            "antigravity/gemini-3.6-flash-low",
            "antigravity/gemini-pro-agent",
            "antigravity/gemini-3.1-pro-low",
            "antigravity/gemini-3-flash-agent",
            "antigravity/gemini-3.5-flash-low",
            "antigravity/gemini-2.5-flash-thinking",
            "antigravity/gemini-2.5-flash",
        ],
    },
    {
        "id": "gemini_local",
        "label": "Custom Gemini (local)",
        "model_class": "Worker",
        "base_url": GEMINI_LOCAL_BASE_URL,
        "api_key": None,
        "optional": True,
        "rate_limit_rps": 10,
        "models": [
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.1-pro",
        ],
    },
    {
        "id": "nvidia",
        "label": "NVIDIA (planner / heavy)",
        "model_class": "Planner",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": NVIDIA_API_KEY,
        "optional": False,
        "rate_limit_rps": 10,
        "models": [
            "nvidia/llama-3.1-nemotron-ultra-253b-v1",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/llama-3_3-nemotron-super-49b-v1.5",
            "mistralai/mistral-large-2-instruct",
            "meta/llama-3_3-70b-instruct",
            "nvidia/llama-3_1-nemotron-safety-guard-8b-v3",
            "nvidia/nvidia-nemotron-nano-9b-v2",
            "nvidia/nemotron-3.5-lightning-30b-a3b",
            "meta/muse-glimmer-30b",
            "nvidia/nemotron-3-nano-30b-a3b",
        ],
    },
    {
        "id": "groq",
        "label": "Groq (fast + STT)",
        "model_class": "Fast",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": GROQ_API_KEY,
        "optional": False,
        "rate_limit_rps": 30,
        "models": [
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "openai/gpt-oss-safeguard-20b",
            "groq/compound", "groq/compound-mini",
            "whisper-large-v3", "whisper-large-v3-turbo",
            "canopylabs/orpheus-v1-english",
            "canopylabs/orpheus-arabic-saudi",
            "allam-2-7b",
            "meta-llama/llama-prompt-guard-2-22m",
            "meta-llama/llama-prompt-guard-2-86m",
        ],
    },
    {
        "id": "openrouter",
        "label": "OpenRouter (free tier)",
        "model_class": "Fallback",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": OPENROUTER_API_KEY,
        "optional": False,
        "rate_limit_rps": 20,
        "models": [
            "z-ai/glm-5.2",
            "nvidia/nemotron-3-super-120b-a12b",
            "nvidia/nemotron-3-nano-30b-a3b",
            "google/gemma-4-31b-it",
            "openai/gpt-oss-20b",
            "nvidia/nemotron-3.5-lightning",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "nvidia/nemotron-nano-9b-v2",
            "google/gemma-4-26b-a4b-it",
            "cohere/north-mini-code",
            "poolside/laguna-s-2.1",
            "poolside/laguna-xs-2.1",
            "deepseek/deepseek-v4-pro-0813",
            "qwen/qwen3.8-max",
        ],
    },
]

_provider_by_id = {p["id"]: p for p in PROVIDERS}

# ---------------------------------------------------------------------------
# Cascade Mode Definitions
# ---------------------------------------------------------------------------
CASCADE_MODES = {
    "fast": [
        ("groq", "openai/gpt-oss-20b"),
        ("omniroute", "auto/best-fast"),
        ("nvidia", "nvidia/nvidia-nemotron-nano-9b-v2"),
        ("openrouter", "nvidia/nemotron-3-nano-30b-a3b"),
    ],
    "intelligent": [
        ("groq", "qwen/qwen3.6-27b"),
        ("omniroute", "auto/best-reasoning"),
        ("nvidia", "nvidia/llama-3.1-nemotron-ultra-253b-v1"),
        ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b"),
        ("openrouter", "nvidia/nemotron-3-super-120b-a12b"),
    ],
    "never_fails": [
        ("groq", "openai/gpt-oss-120b"),
        ("omniroute", "auto/best-chat"),
        ("nvidia", "mistralai/mistral-large-2-instruct"),
        ("nvidia", "meta/llama-3_3-70b-instruct"),
        ("openrouter", "z-ai/glm-5.2"),
        ("openrouter", "google/gemma-4-31b-it"),
    ],
}

# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------
_state_lock = threading.Lock()
model_state = {}
token_usage = {}
provider_health = {p["id"]: {"reachable": None, "last_checked": None} for p in PROVIDERS}
_provider_request_log = {p["id"]: collections.deque() for p in PROVIDERS}
_request_history = collections.deque(maxlen=200)
_latency_log = {}


def _key(provider_id, model):
    return f"{provider_id}::{model}"


def _record_provider_request(provider_id):
    now = time.time()
    log = _provider_request_log.get(provider_id)
    if log is not None:
        log.append(now)
        while log and log[0] < now - 60:
            log.popleft()


def _provider_rps(provider_id):
    log = _provider_request_log.get(provider_id)
    if not log:
        return 0.0
    now = time.time()
    while log and log[0] < now - 60:
        log.popleft()
    return len(log) / 60.0


def _is_provider_near_limit(provider_id):
    provider = _provider_by_id.get(provider_id)
    if not provider:
        return False
    limit = provider.get("rate_limit_rps", 100)
    current_rps = _provider_rps(provider_id)
    return current_rps > limit * 0.8


def mark_fail(provider_id, model, error_msg, status_code=None):
    with _state_lock:
        k = _key(provider_id, model)
        entry = model_state.setdefault(k, {
            "cooldown_until": 0, "last_error": None,
            "ok_count": 0, "fail_count": 0, "consecutive_429": 0
        })
        entry["last_error"] = error_msg
        entry["fail_count"] += 1
        if status_code == 429:
            entry["consecutive_429"] = entry.get("consecutive_429", 0) + 1
            backoff = min(5.0 * (2 ** (entry["consecutive_429"] - 1)), 30.0)
            entry["cooldown_until"] = time.time() + backoff
        elif status_code and status_code >= 500:
            entry["cooldown_until"] = time.time() + 2.0
            entry["consecutive_429"] = 0
        else:
            entry["cooldown_until"] = time.time() + 0.5
            entry["consecutive_429"] = 0


def mark_ok(provider_id, model):
    with _state_lock:
        k = _key(provider_id, model)
        entry = model_state.setdefault(k, {
            "cooldown_until": 0, "last_error": None,
            "ok_count": 0, "fail_count": 0, "consecutive_429": 0
        })
        entry["ok_count"] += 1
        entry["consecutive_429"] = 0


def track_tokens(provider_id, model, prompt_tokens, completion_tokens):
    with _state_lock:
        k = _key(provider_id, model)
        entry = token_usage.setdefault(k, {"promptTokens": 0, "completionTokens": 0, "totalCalls": 0})
        entry["promptTokens"] += prompt_tokens
        entry["completionTokens"] += completion_tokens
        entry["totalCalls"] += 1


def track_latency(provider_id, model, latency_ms):
    with _state_lock:
        k = _key(provider_id, model)
        if k not in _latency_log:
            _latency_log[k] = collections.deque(maxlen=100)
        _latency_log[k].append((time.time(), latency_ms))


def record_request(mode, provider_id, model, latency_ms, tokens, status, error=None):
    _request_history.append({
        "timestamp": time.time(),
        "mode": mode,
        "provider": provider_id,
        "model": model,
        "latency_ms": latency_ms,
        "tokens": tokens,
        "status": status,
        "error": error,
    })


def is_cooling_down(provider_id, model):
    with _state_lock:
        entry = model_state.get(_key(provider_id, model))
        if not entry:
            return False
        return time.time() < entry["cooldown_until"]


def get_cooldown_remaining(provider_id, model):
    with _state_lock:
        entry = model_state.get(_key(provider_id, model))
        if not entry:
            return 0
        return max(0, entry["cooldown_until"] - time.time())


# ---------------------------------------------------------------------------
# Mode auto-detection
# ---------------------------------------------------------------------------
INTELLIGENT_KEYWORDS = [
    "plan", "analyze", "reason", "explain in detail", "compare",
    "architecture", "design", "strategy", "evaluate", "critique",
    "write a", "implement", "debug", "refactor", "review",
]


def detect_mode(messages):
    if not messages:
        return "never_fails"
    user_msgs = [m for m in messages if m.get("role") == "user"]
    if not user_msgs:
        return "never_fails"
    last_content = user_msgs[-1].get("content", "")
    total_turns = len(messages)
    content_len = len(last_content)
    lower_content = last_content.lower()
    has_complex_keywords = any(kw in lower_content for kw in INTELLIGENT_KEYWORDS)
    if total_turns <= 3 and content_len < 200 and not has_complex_keywords:
        return "fast"
    if total_turns > 6 or content_len > 500 or has_complex_keywords:
        return "intelligent"
    return "never_fails"


# ---------------------------------------------------------------------------
# Setup steps
# ---------------------------------------------------------------------------
def check_node_npm():
    node_path = shutil.which("node")
    npm_path = shutil.which("npm")
    if not node_path or not npm_path:
        print("[setup] WARNING: Node.js/npm not found on PATH.")
        return False
    print(f"[setup] Found node ({node_path}) and npm ({npm_path}).")
    return True


def ensure_omniroute_installed():
    omniroute_path = shutil.which("omniroute")
    if omniroute_path:
        print(f"[setup] Omniroute already installed ({omniroute_path}).")
        return True
    print("[setup] Omniroute not found. Installing globally: npm install -g omniroute")
    try:
        result = subprocess.run(["npm", "install", "-g", "omniroute"], capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            print(f"[setup] WARNING: omniroute install failed:\n{result.stderr}")
            return False
        print("[setup] Omniroute installed successfully.")
        return True
    except Exception as e:
        print(f"[setup] WARNING: omniroute install error: {e}")
        return False


_omniroute_process = None


def start_omniroute_background():
    global _omniroute_process
    omniroute_path = shutil.which("omniroute")
    if not omniroute_path:
        print("[setup] Skipping Omniroute start (not installed).")
        return
    try:
        print("[setup] Starting Omniroute in background...")
        _omniroute_process = subprocess.Popen(
            [omniroute_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
        )
        print(f"[setup] Omniroute started (pid {_omniroute_process.pid}).")
    except Exception as e:
        print(f"[setup] WARNING: Could not start Omniroute: {e}")


def probe_url_sync(url, timeout=1.5):
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url)
            return r.status_code < 500
    except Exception:
        return False


def probe_local_providers():
    for p in PROVIDERS:
        if p["id"] in ("omniroute", "gemini_local"):
            reachable = probe_url_sync(p["base_url"].replace("/v1", "") or p["base_url"])
            provider_health[p["id"]] = {"reachable": reachable, "last_checked": time.time()}


def fetch_provider_models(p):
    url = p["base_url"].rstrip("/") + "/models"
    headers = {"Content-Type": "application/json"}
    if p.get("api_key"):
        headers["Authorization"] = f"Bearer {p['api_key']}"
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                models = []
                for m in data.get("data", []):
                    if "id" in m:
                        mid = m["id"]
                        if p["id"] == "openrouter":
                            if ":free" in mid:
                                models.append(mid.replace(":free", ""))
                        else:
                            models.append(mid)
                if models:
                    p["models"] = models
                    print(f"[autofetch] Updated {p['label']} with {len(models)} models.")
            else:
                print(f"[autofetch] Failed to fetch models for {p['label']}: HTTP {resp.status_code}")
    except Exception as e:
        print(f"[autofetch] Error fetching models for {p['label']}: {e}")


def _background_model_fetch():
    time.sleep(2.0)
    for p in PROVIDERS:
        fetch_provider_models(p)


def _background_omniroute_setup():
    has_node = check_node_npm()
    if has_node:
        ensure_omniroute_installed()
        start_omniroute_background()
        time.sleep(1.5)
    probe_local_providers()
    status = provider_health.get("omniroute", {}).get("reachable")
    print(f"[setup] Omniroute background setup complete. Reachable: {status}")


def run_setup():
    print("=" * 60)
    print("Mitchell API - setup")
    print("=" * 60)
    t = threading.Thread(target=_background_omniroute_setup, daemon=True)
    t.start()
    t2 = threading.Thread(target=_background_model_fetch, daemon=True)
    t2.start()
    reachable = probe_url_sync(GEMINI_LOCAL_BASE_URL.replace("/v1", ""))
    provider_health["gemini_local"] = {"reachable": reachable, "last_checked": time.time()}
    print(f"[setup] Custom Gemini (local): {'reachable' if reachable else 'offline (will be skipped, no error)'}")
    provider_health["omniroute"] = {"reachable": None, "last_checked": time.time()}
    print("[setup] Omniroute (local): checking in background...")
    for p in PROVIDERS:
        if p["id"] in ("omniroute", "gemini_local"):
            continue
        has_key = bool(p["api_key"])
        provider_health[p["id"]] = {"reachable": has_key, "last_checked": time.time()}
        print(f"[setup] {p['label']}: {'API key set' if has_key else 'NO API KEY SET'}")
    print("=" * 60)
    print(f"[setup] Starting Mitchell API now on http://localhost:{PORT}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# Cascade execution
# ---------------------------------------------------------------------------
def build_headers(provider):
    headers = {"Content-Type": "application/json"}
    if provider["api_key"]:
        headers["Authorization"] = f"Bearer {provider['api_key']}"
    return headers


async def try_provider_model(client, provider, model, messages, extra_params):
    url = provider["base_url"].rstrip("/") + "/chat/completions"
    upstream_model = model
    if provider["id"] == "openrouter" and not upstream_model.endswith(":free"):
        upstream_model += ":free"
    payload = {"model": upstream_model, "messages": messages}
    payload.update(extra_params)
    payload["stream"] = False
    headers = build_headers(provider)
    _record_provider_request(provider["id"])
    start_time = time.time()
    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
        latency_ms = int((time.time() - start_time) * 1000)
        track_latency(provider["id"], model, latency_ms)
        if resp.status_code == 200:
            data = resp.json()
            mark_ok(provider["id"], model)
            usage_data = data.get("usage", {})
            pt = usage_data.get("prompt_tokens", 0)
            ct = usage_data.get("completion_tokens", 0)
            track_tokens(provider["id"], model, pt, ct)
            return True, data, None, 200, latency_ms
        else:
            err = f"HTTP {resp.status_code}: {resp.text[:200]}"
            mark_fail(provider["id"], model, err, status_code=resp.status_code)
            return False, None, err, resp.status_code, latency_ms
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        err = str(e)[:200]
        mark_fail(provider["id"], model, err)
        return False, None, err, None, latency_ms


def _can_use_provider(provider):
    health = provider_health.get(provider["id"], {})
    if provider.get("optional") and health.get("reachable") is False:
        reachable = probe_url_sync(provider["base_url"].replace("/v1", "") or provider["base_url"])
        provider_health[provider["id"]] = {"reachable": reachable, "last_checked": time.time()}
        if not reachable:
            return False, "offline"
    if not provider.get("optional") and not provider["api_key"]:
        return False, "no_api_key"
    return True, None


async def run_cascade(messages, extra_params, requested_model=None, mode="auto"):
    if mode == "auto":
        effective_mode = detect_mode(messages)
    else:
        effective_mode = mode

    trace = []
    request_start = time.time()

    async with httpx.AsyncClient() as client:
        # Priority: explicit model routing
        if requested_model:
            for provider in PROVIDERS:
                if requested_model in provider["models"]:
                    usable, skip_reason = _can_use_provider(provider)
                    if not usable:
                        trace.append({"provider": provider["id"], "model": requested_model, "skipped": skip_reason})
                        continue
                    if is_cooling_down(provider["id"], requested_model):
                        trace.append({"provider": provider["id"], "model": requested_model, "skipped": "cooldown"})
                        continue
                    ok, data, err, status, latency = await try_provider_model(
                        client, provider, requested_model, messages, extra_params
                    )
                    trace.append({
                        "provider": provider["id"], "model": requested_model,
                        "ok": ok, "error": err, "latency_ms": latency,
                        "note": "explicit model requested"
                    })
                    if ok:
                        total_latency = int((time.time() - request_start) * 1000)
                        usage = data.get("usage", {})
                        record_request(effective_mode, provider["id"], requested_model, total_latency,
                                       usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0), "success")
                        return {
                            "provider_used": provider["id"], "model_used": requested_model,
                            "mode_used": effective_mode, "latency_ms": total_latency, "response": data,
                        }, trace
            trace.append({"note": f"Requested model {requested_model} failed; falling back to {effective_mode} cascade."})

        # Mode-based cascade
        chain = list(CASCADE_MODES.get(effective_mode, CASCADE_MODES["never_fails"]))
        # Priority-0: prepend Custom Gemini if online
        gemini_health = provider_health.get("gemini_local", {})
        if gemini_health.get("reachable"):
            chain.insert(0, ("gemini_local", "gemini-3.7-flash"))

        for provider_id, model in chain:
            provider = _provider_by_id.get(provider_id)
            if not provider:
                trace.append({"provider": provider_id, "model": model, "skipped": "provider_not_found"})
                continue
            usable, skip_reason = _can_use_provider(provider)
            if not usable:
                trace.append({"provider": provider_id, "model": model, "skipped": skip_reason})
                continue
            if is_cooling_down(provider_id, model):
                cd = round(get_cooldown_remaining(provider_id, model), 1)
                trace.append({"provider": provider_id, "model": model, "skipped": f"cooldown ({cd}s remaining)"})
                continue
            if _is_provider_near_limit(provider_id):
                trace.append({"provider": provider_id, "model": model, "skipped": "rate_limit_prevention"})
                continue

            ok, data, err, status, latency = await try_provider_model(client, provider, model, messages, extra_params)
            trace.append({
                "provider": provider_id, "model": model,
                "ok": ok, "error": err, "latency_ms": latency, "status_code": status,
            })
            if ok:
                total_latency = int((time.time() - request_start) * 1000)
                usage = data.get("usage", {})
                record_request(effective_mode, provider_id, model, total_latency,
                               usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0), "success")
                
                if isinstance(data, dict):
                    data["_mitchell"] = {
                        "provider_used": provider_id,
                        "model_used": model,
                        "mode_used": effective_mode,
                        "latency_ms": total_latency,
                    }
                return data, trace
    total_latency = int((time.time() - request_start) * 1000)
    record_request(effective_mode, "none", "none", total_latency, 0, "exhausted")
    return None, trace


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Mitchell API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    requested_model = body.get("model")
    mode = body.get("mode", "auto")
    extra_params = {k: v for k, v in body.items() if k not in ("messages", "model", "mode")}

    result, trace = await run_cascade(messages, extra_params, requested_model=requested_model, mode=mode)
    if result is None:
        return JSONResponse(
            status_code=502,
            content={
                "error": {
                    "message": "All providers/models exhausted",
                    "type": "server_error",
                    "param": None,
                    "code": 502
                },
                "_mitchell": {
                    "trace": trace,
                    "mode_used": mode
                }
            },
        )
    if isinstance(result, dict) and "_mitchell" in result:
        result["_mitchell"]["trace"] = trace
    return JSONResponse(content=result)


async def _run_audio_cascade(provider_models, endpoint_path, method, kwargs_factory, extract_func):
    trace = []
    request_start = time.time()
    async with httpx.AsyncClient() as client:
        for provider_id, model in provider_models:
            provider = _provider_by_id.get(provider_id)
            if not provider:
                continue
            usable, skip_reason = _can_use_provider(provider)
            if not usable:
                trace.append({"provider": provider_id, "model": model, "skipped": skip_reason})
                continue
            if is_cooling_down(provider_id, model):
                trace.append({"provider": provider_id, "model": model, "skipped": "cooldown"})
                continue
            
            # rate limit skip
            rps = sum(provider["rps_window"])
            if rps > provider["rps_limit"] * 0.8:
                trace.append({"provider": provider_id, "model": model, "skipped": "rate_limit_near"})
                continue
            
            start_time = time.time()
            headers = {"Authorization": f"Bearer {provider['api_key']}"} if provider["api_key"] else {}
            kwargs = kwargs_factory(model)
            url = f"{provider['base_url'].replace('/v1', '')}{endpoint_path}"
            
            try:
                if method == "POST":
                    resp = await client.post(url, headers=headers, timeout=30.0, **kwargs)
                else:
                    resp = await client.request(method, url, headers=headers, timeout=30.0, **kwargs)
                    
                latency_ms = int((time.time() - start_time) * 1000)
                
                if resp.status_code == 200:
                    mark_success(provider_id, model)
                    trace.append({
                        "provider": provider_id, "model": model,
                        "ok": True, "error": None, "latency_ms": latency_ms, "status_code": 200,
                    })
                    total_latency = int((time.time() - request_start) * 1000)
                    record_request("audio", provider_id, model, total_latency, 0, "success")
                    return True, extract_func(resp), provider_id, model, trace, total_latency
                else:
                    err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    mark_fail(provider_id, model, err, status_code=resp.status_code)
                    trace.append({
                        "provider": provider_id, "model": model,
                        "ok": False, "error": err, "latency_ms": latency_ms, "status_code": resp.status_code,
                    })
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                err = str(e)[:200]
                mark_fail(provider_id, model, err)
                trace.append({
                    "provider": provider_id, "model": model,
                    "ok": False, "error": err, "latency_ms": latency_ms, "status_code": None,
                })
                
    total_latency = int((time.time() - request_start) * 1000)
    record_request("audio", "none", "none", total_latency, 0, "exhausted")
    return False, None, None, None, trace, total_latency

@app.post("/v1/audio/transcriptions")
async def audio_transcriptions(file: UploadFile = File(...), model: str = Form("whisper-large-v3-turbo")):
    # Cascade: turbo -> large-v3
    chain = [
        ("groq", "whisper-large-v3-turbo"),
        ("groq", "whisper-large-v3")
    ]
    
    file_bytes = await file.read()
    
    def kwargs_factory(model_name):
        return {
            "data": {"model": model_name},
            "files": {"file": (file.filename, file_bytes, file.content_type)}
        }
        
    def extract_func(resp):
        return resp.json()
        
    ok, data, provider_used, model_used, trace, latency = await _run_audio_cascade(
        chain, "/openai/v1/audio/transcriptions", "POST", kwargs_factory, extract_func
    )
    
    if not ok:
        return JSONResponse(status_code=502, content={"error": "All providers/models exhausted", "trace": trace})
        
    return JSONResponse(content={
        "provider_used": provider_used,
        "model_used": model_used,
        "latency_ms": latency,
        "trace": trace,
        "response": data
    })

@app.post("/v1/audio/speech")
async def audio_speech(request: Request):
    body = await request.json()
    # Spec: no fallback for TTS currently
    chain = [
        ("groq", "canopylabs/orpheus-v1-english")
    ]
    
    def kwargs_factory(model_name):
        return {
            "json": {
                "model": model_name,
                "input": body.get("input"),
                "voice": body.get("voice", "nova")
            }
        }
        
    def extract_func(resp):
        return resp.content
        
    ok, audio_bytes, provider_used, model_used, trace, latency = await _run_audio_cascade(
        chain, "/openai/v1/audio/speech", "POST", kwargs_factory, extract_func
    )
    
    if not ok:
        return JSONResponse(status_code=502, content={"error": "All providers/models exhausted", "trace": trace})
        
    # We return the raw audio bytes as StreamingResponse, but we want to include trace info if possible.
    # Standard OpenAI returns raw audio, so we'll do the same but put trace in headers.
    import json
    headers = {
        "X-Cascade-Provider": provider_used,
        "X-Cascade-Model": model_used,
        "X-Cascade-Latency": str(latency),
        "X-Cascade-Trace": json.dumps(trace)
    }
    return StreamingResponse(iter([audio_bytes]), media_type="audio/mpeg", headers=headers)


@app.get("/v1/models")
async def list_models():
    probe_local_providers()
    out = []
    for p in PROVIDERS:
        health = provider_health.get(p["id"], {})
        for model in p["models"]:
            k = _key(p["id"], model)
            state = model_state.get(k, {})
            out.append({
                "provider": p["id"],
                "provider_label": p["label"],
                "model_class": p.get("model_class", "Unknown"),
                "model": model,
                "provider_reachable": health.get("reachable"),
                "cooling_down": is_cooling_down(p["id"], model),
                "cooldown_remaining": round(get_cooldown_remaining(p["id"], model), 1),
                "ok_count": state.get("ok_count", 0),
                "fail_count": state.get("fail_count", 0),
                "last_error": state.get("last_error"),
            })
    return {"providers": [p["id"] for p in PROVIDERS], "models": out}


@app.get("/v1/health")
async def health():
    return {"status": "ok", "providers": provider_health, "time": time.time()}


@app.get("/v1/cascade-modes")
async def cascade_modes():
    modes = {}
    for mode_name, chain in CASCADE_MODES.items():
        steps = []
        for provider_id, model in chain:
            provider = _provider_by_id.get(provider_id, {})
            steps.append({
                "provider_id": provider_id,
                "provider_label": provider.get("label", provider_id),
                "model": model,
                "provider_reachable": provider_health.get(provider_id, {}).get("reachable"),
            })
        modes[mode_name] = {
            "chain": steps,
            "description": {
                "fast": "Lowest latency, good-enough quality. Used for quick replies and tool-loop steps.",
                "intelligent": "Best reasoning quality, latency secondary. Used for planning and complex analysis.",
                "never_fails": "Always returns something. Every provider gets a shot, ends on free tier.",
            }.get(mode_name, ""),
            "emoji": {"fast": "\u26a1", "intelligent": "\U0001f9e0", "never_fails": "\U0001f6e1\ufe0f"}.get(mode_name, ""),
        }
    return {"modes": modes}


@app.get("/v1/request-stats")
async def request_stats():
    now = time.time()
    provider_stats = {}
    for p in PROVIDERS:
        pid = p["id"]
        log = _provider_request_log.get(pid, collections.deque())
        reqs_60s = sum(1 for t in log if t > now - 60)
        reqs_5m = sum(1 for t in log if t > now - 300)
        reqs_30m = sum(1 for t in log if t > now - 1800)
        provider_stats[pid] = {
            "label": p["label"],
            "reachable": provider_health.get(pid, {}).get("reachable"),
            "rate_limit_rps": p.get("rate_limit_rps", 0),
            "current_rps": round(_provider_rps(pid), 2),
            "near_limit": _is_provider_near_limit(pid),
            "requests_60s": reqs_60s,
            "requests_5m": reqs_5m,
            "requests_30m": reqs_30m,
        }

    model_stats = {}
    for k, state in model_state.items():
        latencies = _latency_log.get(k, collections.deque())
        recent_latencies = [lat for ts, lat in latencies if ts > now - 300]
        avg_latency = round(sum(recent_latencies) / len(recent_latencies), 1) if recent_latencies else 0
        usage = token_usage.get(k, {})
        pid, mid = k.split("::", 1)
        model_stats[k] = {
            "ok_count": state.get("ok_count", 0),
            "fail_count": state.get("fail_count", 0),
            "success_rate": round(state.get("ok_count", 0) / max(state.get("ok_count", 0) + state.get("fail_count", 0), 1) * 100, 1),
            "avg_latency_ms": avg_latency,
            "cooling_down": is_cooling_down(pid, mid),
            "cooldown_remaining": round(get_cooldown_remaining(pid, mid), 1),
            "total_tokens": usage.get("promptTokens", 0) + usage.get("completionTokens", 0),
            "total_calls": usage.get("totalCalls", 0),
        }

    history = list(_request_history)[-50:]
    return {"provider_stats": provider_stats, "model_stats": model_stats, "request_history": history}


@app.post("/v1/system/restart")
async def system_restart():
    def _restart():
        time.sleep(0.5)
        os.execv(sys.executable, ['python'] + sys.argv)
    threading.Thread(target=_restart, daemon=True).start()
    return {"status": "restarting"}


@app.post("/v1/system/stop")
async def system_stop():
    from urllib.parse import urlparse
    def _kill_cluster():
        time.sleep(0.5)
        kill_port(PORT)
        try:
            op = urlparse(OMNIROUTE_BASE_URL).port
            if op: kill_port(op)
        except Exception:
            pass
        try:
            gp = urlparse(GEMINI_LOCAL_BASE_URL).port
            if gp: kill_port(gp)
        except Exception:
            pass
    threading.Thread(target=_kill_cluster, daemon=True).start()
    return {"status": "shutting_down"}


@app.get("/v1/token-usage")
async def token_usage_endpoint():
    return token_usage


@app.get("/v1/stress-test")
async def stress_test_endpoint(concurrency: int = 2, count: int = 10, target: str = "cascade", mode: str = "auto"):
    q = asyncio.Queue()

    async def worker(req_id: int):
        start_time = time.time()
        messages = [{"role": "user", "content": "Explain quantum computing in 20 words."}]
        try:
            if target == "cascade":
                result, trace = await run_cascade(messages, {}, mode=mode)
            else:
                result, trace = await run_cascade(messages, {}, requested_model=target, mode=mode)
            latency = int((time.time() - start_time) * 1000)
            if result:
                usage = result.get("response", {}).get("usage", {})
                pt = usage.get("prompt_tokens", 10)
                ct = usage.get("completion_tokens", 20)
                tps = ct / max((latency / 1000.0), 0.001)
                await q.put({'id': req_id, 'status': 'success', 'model': result.get('model_used'),
                             'provider': result.get('provider_used'), 'mode': result.get('mode_used'),
                             'latency': latency, 'promptTokens': pt, 'completionTokens': ct,
                             'tps': round(tps, 1), 'trace': trace})
            else:
                await q.put({'id': req_id, 'status': 'error', 'model': target, 'latency': latency,
                             'errorMsg': 'All providers exhausted', 'trace': trace})
        except Exception as e:
            latency = int((time.time() - start_time) * 1000)
            await q.put({'id': req_id, 'status': 'error', 'model': target, 'latency': latency, 'errorMsg': str(e)})

    async def runner():
        sem = asyncio.Semaphore(concurrency)
        async def sem_worker(req_id):
            async with sem:
                await worker(req_id)
        tasks = [asyncio.create_task(sem_worker(i)) for i in range(count)]
        await asyncio.gather(*tasks)
        await q.put(None)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'init', 'concurrency': concurrency, 'count': count, 'target': target, 'mode': mode})}\n\n"
        asyncio.create_task(runner())
        completed = 0
        while True:
            item = await q.get()
            if item is None:
                break
            completed += 1
            yield f"data: {json.dumps(item)}\n\n"
            yield f"data: {json.dumps({'type': 'progress', 'completed': completed, 'total': count})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


from fastapi.staticfiles import StaticFiles

ui_dist_path = os.path.join(os.path.dirname(__file__), "ui_dist")
if os.path.isdir(ui_dist_path):
    app.mount("/", StaticFiles(directory=ui_dist_path, html=True), name="ui")
else:
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        return "<h1>Mitchell API</h1><p>UI is missing. Build ui/ to mitchell/ui_dist.</p>"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def kill_port(port: int):
    if sys.platform == "win32":
        cmd = f'netstat -ano | findstr LISTENING | findstr ":{port} "'
        try:
            output = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode()
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) > 4:
                    pid = parts[-1]
                    if pid != "0":
                        print(f"Killing process {pid} on port {port}...")
                        subprocess.run(f"taskkill /PID {pid} /F", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def main():
    import uvicorn
    import argparse
    from urllib.parse import urlparse

    parser = argparse.ArgumentParser(description="Mitchell API CLI")
    parser.add_argument("command", nargs="?", default="start", choices=["start", "stop"])
    args = parser.parse_args()

    if args.command == "stop":
        print("Stopping Mitchell API, Omniroute, and Gemini servers...")
        kill_port(PORT)
        try:
            op = urlparse(OMNIROUTE_BASE_URL).port
            if op: kill_port(op)
        except Exception:
            pass
        try:
            gp = urlparse(GEMINI_LOCAL_BASE_URL).port
            if gp: kill_port(gp)
        except Exception:
            pass
        print("Servers stopped.")
        sys.exit(0)

    run_setup()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
