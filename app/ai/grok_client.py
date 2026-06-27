import httpx
from typing import Optional, List, Dict, Any
import yaml
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

XAI_API_KEY = config["xai"]["api_key"]
XAI_MODEL = config["xai"].get("model", "grok-2")
XAI_API_URL = "https://api.x.ai/v1/chat/completions"


class GrokClient:
    def __init__(self, api_key: str = XAI_API_KEY, model: str = XAI_MODEL):
        self.api_key = api_key
        self.model = model
        self.api_url = XAI_API_URL

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Send chat request to xAI Grok API"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)
        
        payload = {
            "model": self.model,
            "messages": full_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Short timeout - if API is unreachable, fail fast and use fallback
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    self.api_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result["choices"][0]["message"]["content"]
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.TimeoutException) as e:
                # API unreachable, fail fast so fallback can be used
                raise ConnectionError(f"xAI API unreachable: {e}") from e

    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> str:
        """Synchronous version of chat"""
        import asyncio
        return asyncio.run(self.chat(messages, system_prompt, temperature, max_tokens))


# Singleton
_grok_client: Optional[GrokClient] = None

def get_grok_client() -> GrokClient:
    global _grok_client
    if _grok_client is None:
        _grok_client = GrokClient()
    return _grok_client
