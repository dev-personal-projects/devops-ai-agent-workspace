from typing import List, Dict
import httpx
import logging
from gateway.config import settings

logger = logging.getLogger(__name__)


class AzureAIFoundryClient:
    """Simple client for Azure AI Foundry API calls."""

    def __init__(self):
        self.endpoint = settings.AZURE_AI_FOUNDRY_ENDPOINT.rstrip("/")
        self.api_key = settings.AZURE_AI_FOUNDRY_API_KEY
        self.deployment_name = settings.AZURE_AI_FOUNDRY_DEPLOYMENT_NAME
        self.api_version = settings.AZURE_AI_FOUNDRY_API_VERSION

    async def send_chat_completion(
            self,
            messages: List[Dict[str, str]],
            max_tokens: int = 800,
            temperature: float = 0.1,
    ) -> str:
        """Send chat completion request to Azure AI Foundry."""

        # Build URL with API version as query parameter
        url = f"{self.endpoint}/openai/deployments/{self.deployment_name}/chat/completions?api-version={self.api_version}"

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }

        # Use max_completion_tokens as per Azure documentation
        payload = {
            "messages": messages,
            "max_completion_tokens": max_tokens,  # Changed to match Azure API
            "temperature": temperature,
            "model": self.deployment_name,  # Added model parameter
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            logger.info(f"Sending request to: {url}")

            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            return data["choices"][0]["message"]["content"]