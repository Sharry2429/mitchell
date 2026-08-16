import json
import os
import time
from pathlib import Path


def estimate_tokens(text: str) -> int:
    """Lightweight heuristic to estimate tokens (approx 1.3 tokens per word)."""
    return int(len(text.split()) * 1.3)

def log_token_usage(caller: str, query: str, estimated_tokens: int):
    """Log token usage for self-audit analysis."""
    p = Path(os.path.expanduser("~/.system-mcp/tokens.jsonl"))
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.time(),
        "caller": caller,
        "query_length": len(query),
        "estimated_tokens": estimated_tokens
    }
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def analyze_prompt(user_input: str) -> bool:
    """
    Analyze the user prompt to determine if full context (index.md) is needed.
    Returns True if full context is needed, False otherwise.
    """
    query = user_input.lower().strip()
    simple_greetings = ["hello", "hi", "hey", "thanks", "thank you", "ok", "okay", "exit", "quit"]
    if query in simple_greetings:
        return False
    # If query is very short and doesn't contain action verbs, likely no context needed
    if len(query.split()) < 4 and not any(verb in query for verb in ["do", "run", "make", "create", "fix", "search", "find"]):
        return False
        
    return True

def compress_history(history: list[dict[str, str]], threshold: int = 10) -> list[dict[str, str]]:
    """
    Compress older messages into a summary if history exceeds the threshold.
    Returns a new history list.
    """
    if len(history) <= threshold:
        return history
        
    # We want to keep the last `threshold // 2` messages intact.
    keep_count = threshold // 2
    to_compress = history[:-keep_count]
    kept = history[-keep_count:]
    
    # Create a dense summary of compressed messages
    # In a fully LLM-driven architecture, we might call the LLM to summarize this.
    # For token efficiency, we'll extract just the first few words or action items.
    summary_lines = []
    for msg in to_compress:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        # Truncate content to first 100 chars
        trunc = content[:100] + "..." if len(content) > 100 else content
        summary_lines.append(f"{role.capitalize()}: {trunc}")
        
    summary_text = "[Summary of previous conversation]\n" + "\n".join(summary_lines)
    
    compressed_history = [{"role": "system", "content": summary_text}] + kept
    return compressed_history
