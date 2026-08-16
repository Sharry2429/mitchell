"""Tests for the durable provider-config registry and its server endpoints."""
import os
import pytest

from mitchell.core.providers import (
    load_providers,
    save_providers,
    get_provider,
    provider_env,
    provider_enabled,
    _store_path,
)


@pytest.fixture
def clean_store(tmp_path, monkeypatch):
    monkeypatch.setattr("mitchell.core.providers._store_path", lambda: tmp_path / "providers.json")
    return tmp_path


def test_empty_store_returns_empty_list(clean_store):
    assert load_providers() == []


def test_save_and_load_roundtrip(clean_store):
    providers = [
        {"name": "aicredits", "baseUrl": "https://api.aicredits.in/v1", "apiKey": "k1", "defaultModel": "m1", "enabled": True},
        {"name": "groq", "baseUrl": "https://api.groq.com/openai/v1", "apiKey": "k2", "defaultModel": "m2", "enabled": False},
    ]
    save_providers(providers)
    assert load_providers() == providers
    assert get_provider("aicredits")["apiKey"] == "k1"
    assert get_provider("AICREDITS")["name"] == "aicredits"


def test_provider_env_falls_back_to_env_vars(clean_store, monkeypatch):
    monkeypatch.setenv("AICREDITS_API_KEY", "env-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    # no stored config -> falls back to env + default url
    url, key = provider_env("aicredits")
    assert key == "env-key"
    assert url == "https://api.aicredits.in/v1"
    # groq: no key anywhere
    url2, key2 = provider_env("groq")
    assert key2 is None
    assert url2 == "https://api.groq.com/openai/v1"


def test_provider_env_prefers_stored_config(clean_store):
    save_providers([{"name": "groq", "baseUrl": "https://custom.example.com/v1", "apiKey": "stored", "defaultModel": "x", "enabled": True}])
    url, key = provider_env("groq")
    assert url == "https://custom.example.com/v1"
    assert key == "stored"


def test_provider_enabled_defaults_true_and_respects_flag(clean_store):
    assert provider_enabled("does-not-exist") is True
    save_providers([
        {"name": "groq", "baseUrl": "u", "apiKey": "k", "defaultModel": "m", "enabled": False},
    ])
    assert provider_enabled("groq") is False
