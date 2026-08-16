from mitchell.core.tokens import analyze_prompt, compress_history, estimate_tokens


def test_estimate_tokens():
    text = "This is a simple sentence."
    # 5 words * 1.3 = 6.5 -> int(6)
    assert estimate_tokens(text) == 6

def test_analyze_prompt_simple():
    # Should not need full context
    assert not analyze_prompt("hello")
    assert not analyze_prompt("  Thanks ")
    assert not analyze_prompt("okay")

def test_analyze_prompt_complex():
    # Action verbs or long queries should trigger full context
    assert analyze_prompt("can you create a new file?")
    assert analyze_prompt("fix the python script")
    assert analyze_prompt("tell me about the architectural differences between microservices and monoliths")

def test_compress_history_under_threshold():
    history = [{"role": "user", "content": "hello"}]
    # Threshold 10, shouldn't compress
    compressed = compress_history(history, threshold=10)
    assert len(compressed) == 1
    assert compressed[0]["content"] == "hello"

def test_compress_history_over_threshold():
    # 10 messages
    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"} for i in range(11)]
    
    # Threshold 10, should compress
    # Keep last 5 messages, first 6 compressed into 1 system message
    compressed = compress_history(history, threshold=10)
    assert len(compressed) == 6
    assert compressed[0]["role"] == "system"
    assert "[Summary of previous conversation]" in compressed[0]["content"]
    assert "User: Message 0" in compressed[0]["content"]
    
    # Last message should be untouched
    assert compressed[-1]["content"] == "Message 10"
