from typing import Protocol, Any, List, Dict

class LLMResult:
    def __init__(self, content: str = "", tool_calls: List[Dict[str, Any]] = None, usage: Dict[str, int] = None):
        self.content = content
        self.tool_calls = tool_calls or []
        self.usage = usage or {"prompt_tokens": 0, "completion_tokens": 0}

class Provider(Protocol):
    @property
    def name(self) -> str:
        ...
        
    def call(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None, model: str = None) -> LLMResult:
        ...
        
    def warm_ping(self) -> bool:
        ...
