"""
Lightweight LLM client — OpenAI-compatible API for chat + embeddings.

Configuration via environment variables:
  MEMORY_LLM_BASE_URL     (default: http://localhost:1234/v1)
  MEMORY_LLM_API_KEY      (default: "no-key")
  MEMORY_LLM_MODEL        (default: "local-model")
  MEMORY_EMBEDDING_MODEL  (default: "" → falls back to TF-IDF)
  MEMORY_LLM_TIMEOUT      (default: 30)
"""

import os
from typing import List, Dict, Any, Optional

import requests


class LLMClient:
    """Minimal OpenAI-compatible LLM + embedding client."""

    def __init__(self):
        self.base_url = os.getenv("MEMORY_LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/")
        self.api_key = os.getenv("MEMORY_LLM_API_KEY", "no-key")
        self.model = os.getenv("MEMORY_LLM_MODEL", "local-model")
        self.embedding_model = os.getenv("MEMORY_EMBEDDING_MODEL", "")
        self.timeout = int(os.getenv("MEMORY_LLM_TIMEOUT", "30"))

    def chat(self, messages: List[Dict[str, str]], timeout: int = 0) -> str:
        """Call /chat/completions and return the assistant's text."""
        t = timeout or self.timeout
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {"model": self.model, "messages": messages, "stream": False}
        resp = requests.post(url, headers=headers, json=payload, timeout=t)
        resp.raise_for_status()
        data = resp.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    def embed(self, texts: List[str], timeout: int = 15) -> List[List[float]]:
        """Call /embeddings. Returns empty list on failure (caller falls back to TF-IDF)."""
        if not self.embedding_model:
            return []
        url = f"{self.base_url}/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {"model": self.embedding_model, "input": texts}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("data", [])
            items.sort(key=lambda x: x.get("index", 0))
            return [it.get("embedding", []) for it in items]
        except Exception:
            return []
