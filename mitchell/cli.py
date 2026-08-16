"""
Mitchell CLI - Chat REPL
"""
import asyncio
import sys
from mitchell.providers import get_provider, active_provider, set_active, load_providers, cascade_order
from mitchell.agents.orchestrator import execute
from mitchell.core.tool_registry import get_registry

class ChatSession:
    def __init__(self):
        self.pinned_provider = None
        self.buffer = []

    def handle_command(self, cmd: str) -> bool:
        """Process slash commands. Returns True if handled."""
        if not cmd.startswith("/"):
            return False
            
        parts = cmd.strip().split()
        if not parts:
            return False
            
        action = parts[0].lower()
        if action == "/provider":
            if len(parts) < 2:
                print("Usage: /provider <name>")
                return True
            name = parts[1]
            if set_active(name):
                self.pinned_provider = name
                print(f"Provider pinned to: {name}")
            else:
                print(f"Provider not found: {name}")
            return True
            
        elif action == "/providers":
            print("Configured providers:")
            for p in cascade_order():
                active = "*" if getattr(active_provider(), "name", "") == p.name else " "
                print(f"[{active}] {p.name}")
            return True
            
        elif action == "/model":
            # Just a stub for model setting
            print("Model switching via CLI (to be implemented).")
            return True
            
        elif action in ["/quit", "/exit"]:
            sys.exit(0)
            
        return False

from mitchell.core.fast_intent import resolve_intent
from mitchell.core.warm_pool import pre_warm_pool
from mitchell.providers.registry import warm_ping

async def async_main():
    print("Initializing Mitchell...")
    load_providers()
    get_registry() # warm up registry
    
    # Pre-warm TLS and worker pool in the background
    asyncio.create_task(warm_ping())
    asyncio.create_task(pre_warm_pool())
    
    session = ChatSession()
    print("Mitchell CLI ready. Type /exit to quit.")
    
    while True:
        try:
            cmd = input("\n> ")
        except (EOFError, KeyboardInterrupt):
            break
            
        if not cmd.strip():
            continue
            
        if session.handle_command(cmd):
            continue
            
        try:
            # 1. Fast Path
            fast_match = await resolve_intent(cmd)
            if fast_match:
                tool_name, args = fast_match
                print(f"[Fast Path] Executing {tool_name}...")
                registry = get_registry()
                if tool_name in registry:
                    res = registry[tool_name](**args)
                    print(f"\n{res}")
                    continue
            
            # 2. Orchestrator Path
            print("Executing...")
            result = await execute(cmd)
            print(f"\n{result}")
        except Exception as e:
            print(f"\nError: {e}")

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
