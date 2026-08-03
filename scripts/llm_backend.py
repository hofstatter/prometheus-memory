#!/usr/bin/env python3
"""LLM backend unificado para o pipeline L2/L3 (local-first).

LLM_BACKEND:
  ollama   → Ollama local (default, zero cloud) via OLLAMA_BASE_URL/OLLAMA_MODEL
  deepseek → DeepSeek API (cloud) via DEEPSEEK_API_KEY
  degraded → concatenação sem LLM (fallback offline)
"""
import os

import requests as http

BACKEND = os.getenv("LLM_BACKEND", "ollama")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def call_llm(prompt: str, max_tokens: int = 400, temperature: float = 0.3, timeout: int = 45) -> str:
    """Chama o backend configurado. Retorna texto ou "" em erro (caller decide fallback)."""
    if BACKEND == "deepseek":
        return _deepseek(prompt, max_tokens, temperature, timeout)
    if BACKEND == "ollama":
        return _ollama(prompt, max_tokens, temperature, timeout)
    return ""


def _ollama(prompt: str, max_tokens: int, temperature: float, timeout: int) -> str:
    try:
        r = http.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
                  "options": {"temperature": temperature, "num_predict": max_tokens}},
            timeout=timeout,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        print(f"  [llm_backend] ollama falhou: {str(e)[:120]}")
        return ""


def _deepseek(prompt: str, max_tokens: int, temperature: float, timeout: int) -> str:
    if not DEEPSEEK_KEY:
        return ""
    try:
        r = http.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
            json={"model": DEEPSEEK_MODEL,
                  "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": max_tokens, "temperature": temperature},
            timeout=timeout,
        )
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"  [llm_backend] deepseek falhou: {str(e)[:120]}")
        return ""


def available() -> bool:
    if BACKEND == "deepseek":
        return bool(DEEPSEEK_KEY)
    if BACKEND == "ollama":
        try:
            r = http.get(f"{OLLAMA_URL}/api/tags", timeout=4)
            return r.status_code == 200
        except Exception:
            return False
    return False


def describe() -> str:
    if BACKEND == "ollama":
        return f"ollama:{OLLAMA_MODEL}@{OLLAMA_URL}"
    if BACKEND == "deepseek":
        return "deepseek-chat@cloud"
    return "degraded (sem LLM)"
