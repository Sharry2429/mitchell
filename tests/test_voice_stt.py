import pytest
pytest.importorskip('numpy')
import numpy as np
import pytest
import requests

from mitchell.voice.stt import transcribe, TranscriptResult

def test_groq_success(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test_groq_key')
    
    class MockResponse:
        status_code = 200
        def json(self):
            return {'text': 'hello world', 'language': 'en'}
            
    def mock_post(*args, **kwargs):
        assert kwargs['timeout'] == 8.0
        return MockResponse()
        
    monkeypatch.setattr(requests, 'post', mock_post)
    
    audio = np.zeros(100, dtype=np.float32)
    res = transcribe(audio, 16000)
    
    assert res.source == 'groq'
    assert res.text == 'hello world'
    assert res.language_guess == 'en'
    # latency is wall-clock; on Windows time.monotonic() has ~15.6ms resolution,
    # so a pure-mock round-trip can measure 0.0 — don't assert > 0 (timing flake).
    assert res.latency_ms >= 0

def test_groq_fallback_aicredits(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test_groq_key')
    monkeypatch.setenv('AICREDITS_API_KEY', 'test_ai_key')
    
    class MockGroqResponse:
        status_code = 429
        text = "Too many requests"
        
    class MockAiCreditsResponse:
        status_code = 200
        def json(self):
            return {'text': 'fallback success'}
            
    call_count = 0
    models_seen = []
    def mock_post(url, *args, **kwargs):
        nonlocal call_count
        call_count += 1
        if 'groq.com' in url:
            models_seen.append(kwargs['data']['model'])
            return MockGroqResponse()
        return MockAiCreditsResponse()
        
    monkeypatch.setattr(requests, 'post', mock_post)
    
    audio = np.zeros(100, dtype=np.float32)
    res = transcribe(audio, 16000)
    
    # Chain: Whisper v3 Turbo -> v3 non-turbo -> aicredits (model-routing plan)
    assert call_count == 3
    assert models_seen == ['whisper-large-v3-turbo', 'whisper-large-v3']
    assert res.source == 'aicredits'
    assert res.text == 'fallback success'
    assert res.language_guess is None

def test_groq_timeout_fallback(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test_groq_key')
    monkeypatch.setenv('AICREDITS_API_KEY', 'test_ai_key')
    
    class MockAiCreditsResponse:
        status_code = 200
        def json(self):
            return {'text': 'fallback success'}
            
    def mock_post(url, *args, **kwargs):
        if 'groq.com' in url:
            raise requests.exceptions.Timeout("timeout")
        return MockAiCreditsResponse()
        
    monkeypatch.setattr(requests, 'post', mock_post)
    
    audio = np.zeros(100, dtype=np.float32)
    res = transcribe(audio, 16000)
    
    assert res.source == 'aicredits'
    assert res.text == 'fallback success'

def test_both_failing(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test_groq_key')
    monkeypatch.setenv('AICREDITS_API_KEY', 'test_ai_key')
    
    def mock_post(url, *args, **kwargs):
        raise requests.exceptions.ConnectionError("connection failed")
        
    monkeypatch.setattr(requests, 'post', mock_post)
    
    audio = np.zeros(100, dtype=np.float32)
    res = transcribe(audio, 16000)
    
    assert res.source == 'failed'
    assert res.text == ''
    assert res.latency_ms >= 0  # see timing-flake note in test_groq_success
