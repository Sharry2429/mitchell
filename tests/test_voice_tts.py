import pytest
pytest.importorskip('sounddevice')
from unittest.mock import patch, MagicMock
from mitchell.core.result import MCPResult
from mitchell.voice.interrupt import InterruptToken
import os

def test_google_succeeds(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google_ai_pro")
    
    mock_google = MagicMock(return_value=MCPResult.success("google_success"))
    mock_edge = MagicMock(return_value=MCPResult.success("edge_success"))
    
    with patch("mitchell.voice.tts._PROVIDERS", {"google_ai_pro": mock_google, "edge_tts": mock_edge}), \
         patch("mitchell.voice.tts.resolve_output_device", return_value=1):
        
        from mitchell.voice.tts import speak
        result = speak("hello")
        
        assert result.ok
        assert result.data == "google_success"
        mock_google.assert_called_once()
        mock_edge.assert_not_called()

def test_google_raises_falls_through_to_edge(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google_ai_pro")
    
    mock_google = MagicMock(side_effect=Exception("google failed"))
    mock_edge = MagicMock(return_value=MCPResult.success("edge_success"))
    
    with patch("mitchell.voice.tts._PROVIDERS", {"google_ai_pro": mock_google, "edge_tts": mock_edge}), \
         patch("mitchell.voice.tts.resolve_output_device", return_value=1):
        
        from mitchell.voice.tts import speak
        result = speak("hello")
        
        assert result.ok
        assert result.data == "edge_success"
        mock_google.assert_called_once()
        mock_edge.assert_called_once()

def test_both_fail(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google_ai_pro")
    
    mock_google = MagicMock(side_effect=Exception("google failed"))
    mock_edge = MagicMock(return_value=MCPResult.fail("edge failed"))
    
    with patch("mitchell.voice.tts._PROVIDERS", {"google_ai_pro": mock_google, "edge_tts": mock_edge}), \
         patch("mitchell.voice.tts.resolve_output_device", return_value=1):
        
        from mitchell.voice.tts import speak
        result = speak("hello")
        
        assert not result.ok
        assert "failed" in result.error

def test_edge_provider_skips_google(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "edge_tts")
    
    mock_google = MagicMock()
    mock_edge = MagicMock(return_value=MCPResult.success("edge_success"))
    
    with patch("mitchell.voice.tts._PROVIDERS", {"google_ai_pro": mock_google, "edge_tts": mock_edge}), \
         patch("mitchell.voice.tts.resolve_output_device", return_value=1):
        
        from mitchell.voice.tts import speak
        result = speak("hello")
        
        assert result.ok
        mock_google.assert_not_called()
        mock_edge.assert_called_once()

def test_interrupt_token_cancelled(monkeypatch):
    monkeypatch.setenv("TTS_PROVIDER", "google_ai_pro")
    
    mock_google = MagicMock()
    mock_edge = MagicMock()
    
    token = InterruptToken()
    token.cancel()
    
    with patch("mitchell.voice.tts._PROVIDERS", {"google_ai_pro": mock_google, "edge_tts": mock_edge}), \
         patch("mitchell.voice.tts.resolve_output_device", return_value=1):
        
        from mitchell.voice.tts import speak
        result = speak("hello", interrupt_token=token)
        
        assert result.ok
        assert result.data == "interrupted"
        mock_google.assert_not_called()
        mock_edge.assert_not_called()
