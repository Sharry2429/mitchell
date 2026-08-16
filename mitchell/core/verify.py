"""
mitchell.core.verify
====================
Verification gate for steps.
"""

def verify_step(step, messages: list[dict]) -> bool:
    """
    Verify if a step has been completed successfully based on the LLM transcript.
    In v1, this is a simple gate that looks for completion signals or tool successes.
    """
    if not messages:
        return False
        
    # Check if the last tool execution was successful
    for msg in reversed(messages):
        if msg.get("role") == "tool":
            content = str(msg.get("content", "")).lower()
            if "error" in content or "fail" in content:
                return False
            return True
            
    # If no tool was called, assume success if the LLM thinks it's done
    return True
