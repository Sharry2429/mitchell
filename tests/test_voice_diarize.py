import pytest
pytest.importorskip('numpy')
import os
import json
import pytest
import numpy as np
from unittest.mock import patch, MagicMock

import mitchell.voice.diarize as diarize

@pytest.fixture
def mock_voice_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(diarize, '_VOICE_DIR', tmp_path)
    monkeypatch.setattr(diarize, '_THRESHOLDS_PATH', tmp_path / 'thresholds.json')
    monkeypatch.setattr(diarize, '_OWNER_PATH', tmp_path / 'owner.npy')
    
    # clear buffer
    diarize._decision_buffer = []
    
    return tmp_path

def test_is_owner_match(mock_voice_dir):
    # Setup owner.npy
    owner_emb = np.array([1.0, 0.0, 0.0])
    np.save(mock_voice_dir / 'owner.npy', owner_emb)
    
    with patch('mitchell.voice.diarize.preprocess_wav', create=True, return_value=np.array([0.1])), \
         patch('mitchell.voice.diarize.VoiceEncoder', create=True) as MockEncoder:
        
        mock_encoder_instance = MockEncoder.return_value
        # Perfect match
        mock_encoder_instance.embed_utterance.return_value = np.array([1.0, 0.0, 0.0])
        
        is_owner_res, similarity, dec_id = diarize.is_owner(np.array([0.1]), 16000)
        
        assert is_owner_res is True
        assert similarity > 0.99
        assert isinstance(dec_id, str)
        assert len(diarize._decision_buffer) == 1

def test_is_owner_no_match(mock_voice_dir):
    owner_emb = np.array([1.0, 0.0, 0.0])
    np.save(mock_voice_dir / 'owner.npy', owner_emb)
    
    with patch('mitchell.voice.diarize.preprocess_wav', create=True, return_value=np.array([0.1])), \
         patch('mitchell.voice.diarize.VoiceEncoder', create=True) as MockEncoder:
        
        mock_encoder_instance = MockEncoder.return_value
        # Orthogonal
        mock_encoder_instance.embed_utterance.return_value = np.array([0.0, 1.0, 0.0])
        
        is_owner_res, similarity, dec_id = diarize.is_owner(np.array([0.1]), 16000)
        
        assert is_owner_res is False
        assert similarity < 0.1

def test_ambiguous_range(mock_voice_dir):
    owner_emb = np.array([1.0, 0.0, 0.0])
    np.save(mock_voice_dir / 'owner.npy', owner_emb)
    
    with patch('mitchell.voice.diarize.preprocess_wav', create=True, return_value=np.array([0.1])), \
         patch('mitchell.voice.diarize.VoiceEncoder', create=True) as MockEncoder:
        
        mock_encoder_instance = MockEncoder.return_value
        # Score approx 0.6
        mock_encoder_instance.embed_utterance.return_value = np.array([0.6, 0.8, 0.0])
        
        is_owner_res, similarity, dec_id = diarize.is_owner(np.array([0.1]), 16000)
        
        assert similarity >= 0.55 and similarity < 0.75
        assert is_owner_res is False
        assert diarize.is_ambiguous(similarity) is True

def test_missing_owner(mock_voice_dir):
    with pytest.raises(FileNotFoundError):
        diarize.is_owner(np.array([0.1]), 16000)

def test_get_recent_decision(mock_voice_dir):
    owner_emb = np.array([1.0, 0.0, 0.0])
    np.save(mock_voice_dir / 'owner.npy', owner_emb)
    
    with patch('mitchell.voice.diarize.preprocess_wav', create=True, return_value=np.array([0.1])), \
         patch('mitchell.voice.diarize.VoiceEncoder', create=True) as MockEncoder:
        
        mock_encoder_instance = MockEncoder.return_value
        mock_encoder_instance.embed_utterance.return_value = np.array([1.0, 0.0, 0.0])
        
        _, _, dec_id = diarize.is_owner(np.array([0.1]), 16000)
        
        decision = diarize.get_recent_decision(dec_id)
        assert decision is not None
        assert decision['decision_id'] == dec_id
        assert decision['decision'] is True

def test_load_thresholds(mock_voice_dir, monkeypatch):
    # Default env vars
    monkeypatch.setenv('DIARIZE_MATCH_THRESHOLD', '0.80')
    
    thresholds = diarize._load_thresholds()
    assert thresholds['match_threshold'] == 0.80
    assert thresholds['ambiguous_floor'] == 0.55
    
    # Custom config
    config = {'match_threshold': 0.90, 'ambiguous_floor': 0.60}
    with open(mock_voice_dir / 'thresholds.json', 'w') as f:
        json.dump(config, f)
        
    thresholds = diarize._load_thresholds()
    assert thresholds['match_threshold'] == 0.90
    assert thresholds['ambiguous_floor'] == 0.60
