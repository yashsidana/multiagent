import os
import json
import logging
from typing import Dict, Any, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified client for invoking chat models across agents.
    Supports OpenAI, OpenAI-compatible APIs (Ollama, vLLM, LMStudio),
    and safe rule-based heuristic fallbacks when running without API keys.
    """

    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL
        self._client = None

    def _get_client(self):
        if self._client is None and self.api_key:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                logger.warning("Could not initialize OpenAI client: %s", str(e))
                self._client = None
        return self._client

    def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        json_mode: bool = False
    ) -> str:
        """Invokes chat completion or uses structured heuristic fallback."""
        client = self._get_client()
        if client:
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if json_mode:
                    kwargs["response_format"] = {"type": "json_object"}

                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception as e:
                logger.error("LLM API call failed: %s. Using heuristic fallback.", str(e))

        # Heuristic fallback if no API key is provided
        return self._heuristic_fallback(messages, json_mode)

    def _heuristic_fallback(self, messages: List[Dict[str, str]], json_mode: bool) -> str:
        """
        Provides sensible default behavior for local unit testing and offline demonstrations
        when OPENAI_API_KEY is not configured.
        """
        last_msg = messages[-1]["content"].lower() if messages else ""

        if json_mode:
            # Router heuristic
            is_sql = any(k in last_msg for k in ["revenue", "sales", "how many", "total", "customer", "order", "rep", "quota", "price"])
            is_rag = any(k in last_msg for k in ["policy", "refund", "review", "why", "discount", "strategy", "roadmap", "hardware"])
            
            if is_sql and is_rag:
                route = "hybrid"
            elif is_sql:
                route = "sql"
            else:
                route = "rag"

            return json.dumps({
                "route": route,
                "reason": f"Heuristic classification based on keyword matching: '{route}'"
            })

        # Plain text fallback
        return (
            "This is a demonstration response. Please configure your OPENAI_API_KEY in .env "
            "for live model reasoning."
        )


llm_client = LLMClient()

