var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// server.ts
var import_express = __toESM(require("express"), 1);
var import_path = __toESM(require("path"), 1);
var import_vite = require("vite");
var PORT = 3e3;
var PROVIDERS = [
  {
    id: "omniroute",
    label: "Omniroute (local)",
    baseUrl: process.env.OMNIROUTE_BASE_URL || "http://localhost:20128/v1",
    apiKey: void 0,
    optional: true,
    models: [
      "gemini-3.7-flash",
      "gemini-3.5-flash-thinking",
      "gemini-3.1-pro"
    ]
  },
  {
    id: "gemini_local",
    label: "Custom Gemini (local)",
    baseUrl: process.env.GEMINI_LOCAL_BASE_URL || "http://localhost:8081/v1",
    apiKey: void 0,
    optional: true,
    models: ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-pro"]
  },
  {
    id: "nvidia",
    label: "NVIDIA (Heavy)",
    baseUrl: "https://integrate.api.nvidia.com/v1",
    apiKey: process.env.NVIDIA_API_KEY,
    optional: false,
    models: ["nvidia/nemotron-3-ultra-550b-a55b", "nvidia/llama-3.3-nemotron-super-49b-v1.5", "nvidia/llama-3.1-nemotron-nano-8b-v1"]
  },
  {
    id: "groq",
    label: "Groq (Fast)",
    baseUrl: "https://api.groq.com/openai/v1",
    apiKey: process.env.GROQ_API_KEY,
    optional: false,
    models: ["qwen/qwen3.6-27b", "groq/compound-mini"]
  },
  {
    id: "openrouter",
    label: "OpenRouter (Free)",
    baseUrl: "https://openrouter.ai/api/v1",
    apiKey: process.env.OPENROUTER_API_KEY,
    optional: false,
    models: ["deepseek/deepseek-v4-pro-0813-free:free", "qwen/qwen3.8-max-free:free"]
  }
];
var COOLDOWN_MS = 6e4;
var modelState = {};
var providerHealth = {};
var tokenUsage = {};
function getKey(providerId, model) {
  return `${providerId}::${model}`;
}
function markFail(providerId, model, errorMsg) {
  const k = getKey(providerId, model);
  if (!modelState[k]) {
    modelState[k] = { cooldownUntil: 0, lastError: null, okCount: 0, failCount: 0 };
  }
  modelState[k].cooldownUntil = Date.now() + COOLDOWN_MS;
  modelState[k].lastError = errorMsg;
  modelState[k].failCount++;
}
function markOk(providerId, model) {
  const k = getKey(providerId, model);
  if (!modelState[k]) {
    modelState[k] = { cooldownUntil: 0, lastError: null, okCount: 0, failCount: 0 };
  }
  modelState[k].okCount++;
}
function isCoolingDown(providerId, model) {
  const entry = modelState[getKey(providerId, model)];
  if (!entry) return false;
  return Date.now() < entry.cooldownUntil;
}
function trackTokens(providerId, model, promptTokens, completionTokens) {
  const k = getKey(providerId, model);
  if (!tokenUsage[k]) {
    tokenUsage[k] = { promptTokens: 0, completionTokens: 0, totalCalls: 0 };
  }
  tokenUsage[k].promptTokens += promptTokens;
  tokenUsage[k].completionTokens += completionTokens;
  tokenUsage[k].totalCalls++;
}
async function startServer() {
  const app = (0, import_express.default)();
  app.use(import_express.default.json());
  PROVIDERS.forEach((p) => {
    providerHealth[p.id] = {
      reachable: p.optional ? false : !!p.apiKey,
      lastChecked: Date.now()
    };
  });
  app.get("/v1/models", (req, res) => {
    const out = [];
    PROVIDERS.forEach((p) => {
      const health = providerHealth[p.id];
      p.models.forEach((model) => {
        const state = modelState[getKey(p.id, model)] || {};
        out.push({
          provider: p.id,
          provider_label: p.label,
          model,
          provider_reachable: health?.reachable,
          cooling_down: isCoolingDown(p.id, model),
          ok_count: state.okCount || 0,
          fail_count: state.failCount || 0,
          last_error: state.lastError || null
        });
      });
    });
    res.json({ providers: PROVIDERS.map((p) => p.id), models: out });
  });
  app.get("/v1/token-usage", (req, res) => {
    res.json(tokenUsage);
  });
  app.post("/v1/providers", (req, res) => {
    const { id, label, baseUrl, apiKey, models } = req.body;
    if (!id || !baseUrl || !models) {
      return res.status(400).json({ error: "Missing required fields" });
    }
    const newProvider = {
      id,
      label: label || id,
      baseUrl,
      apiKey,
      optional: true,
      models: Array.isArray(models) ? models : models.split(",").map((m) => m.trim())
    };
    PROVIDERS.push(newProvider);
    providerHealth[id] = { reachable: true, lastChecked: Date.now() };
    res.json({ success: true, provider: newProvider });
  });
  app.post("/v1/chat/completions", async (req, res) => {
    console.log(`
[API REQUEST] POST /v1/chat/completions`);
    console.log(`[REQUEST BODY]`, JSON.stringify(req.body, null, 2));
    const { messages, model_preference, ...extraParams } = req.body;
    const trace = [];
    let preferredModels = [];
    let defaultModels = [];
    PROVIDERS.forEach((provider) => {
      provider.models.forEach((model) => {
        defaultModels.push({ provider, model });
      });
    });
    if (model_preference && Array.isArray(model_preference)) {
      model_preference.forEach((prefModel) => {
        const found = defaultModels.filter((m) => m.model === prefModel);
        preferredModels.push(...found);
      });
      defaultModels = defaultModels.filter((m) => !model_preference.includes(m.model));
    }
    const cascadeOrder = [...preferredModels, ...defaultModels];
    let success = false;
    let finalResponse = null;
    let usedProvider = null;
    let usedModel = null;
    for (const { provider, model } of cascadeOrder) {
      const health = providerHealth[provider.id] || {};
      if (provider.optional && health.reachable === false) {
        trace.push({ provider: provider.id, model, skipped: "offline" });
        continue;
      }
      if (!provider.optional && !provider.apiKey) {
        trace.push({ provider: provider.id, model, skipped: "no_api_key" });
        continue;
      }
      if (isCoolingDown(provider.id, model)) {
        trace.push({ provider: provider.id, model, skipped: "cooldown" });
        continue;
      }
      const url = provider.baseUrl.replace(/\/$/, "") + "/chat/completions";
      const payload = { model, messages, ...extraParams };
      const headers = { "Content-Type": "application/json" };
      if (provider.apiKey) headers["Authorization"] = `Bearer ${provider.apiKey}`;
      const startTime = Date.now();
      try {
        console.log(`[CASCADE] Trying ${provider.id} :: ${model}`);
        const response = await fetch(url, {
          method: "POST",
          headers,
          body: JSON.stringify(payload)
          // Abort signal could be added here for timeouts
        });
        const latency = Date.now() - startTime;
        if (response.ok) {
          const data = await response.json();
          markOk(provider.id, model);
          let promptTokens = data.usage?.prompt_tokens || 0;
          let completionTokens = data.usage?.completion_tokens || 0;
          trackTokens(provider.id, model, promptTokens, completionTokens);
          console.log(`[SUCCESS] ${provider.id} :: ${model} | Latency: ${latency}ms | Tokens: ${promptTokens} prompt, ${completionTokens} completion`);
          trace.push({ provider: provider.id, model, ok: true });
          success = true;
          finalResponse = data;
          usedProvider = provider.id;
          usedModel = model;
          break;
        } else {
          const errText = await response.text();
          const errMessage = `HTTP ${response.status}: ${errText.substring(0, 200)}`;
          markFail(provider.id, model, errMessage);
          console.error(`[ERROR] ${provider.id} :: ${model} | ${errMessage}`);
          trace.push({ provider: provider.id, model, ok: false, error: errMessage });
        }
      } catch (e) {
        const latency = Date.now() - startTime;
        const errMessage = String(e.message || e).substring(0, 200);
        markFail(provider.id, model, errMessage);
        console.error(`[ERROR] ${provider.id} :: ${model} | Latency: ${latency}ms | Exception: ${errMessage}`);
        trace.push({ provider: provider.id, model, ok: false, error: errMessage });
      }
    }
    if (success) {
      res.json({
        provider_used: usedProvider,
        model_used: usedModel,
        response: finalResponse,
        trace
      });
    } else {
      console.warn(`[WARNING] All cascade providers exhausted/failed.`);
      res.status(502).json({
        error: "All providers/models exhausted",
        trace
      });
    }
  });
  if (process.env.NODE_ENV !== "production") {
    const vite = await (0, import_vite.createServer)({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = import_path.default.join(process.cwd(), "dist");
    app.use(import_express.default.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(import_path.default.join(distPath, "index.html"));
    });
  }
  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
  });
}
startServer();
//# sourceMappingURL=server.cjs.map
