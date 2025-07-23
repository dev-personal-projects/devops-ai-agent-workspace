import sys
import os
import types
import asyncio
from unittest.mock import AsyncMock

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Stub httpx module to avoid dependency
httpx = types.ModuleType('httpx')
class AsyncClient:
    def __init__(self, *args, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc, tb):
        pass
    async def post(self, *args, **kwargs):
        class Resp:
            def raise_for_status(self):
                pass
            def json(self):
                return {"choices": [{"message": {"content": "stub"}}]}
        return Resp()
httpx.AsyncClient = AsyncClient
sys.modules['httpx'] = httpx

# Stub config module with minimal settings
config_module = types.ModuleType('gateway.config')
class Settings:
    AZURE_AI_FOUNDRY_ENDPOINT = 'https://example.com'
    AZURE_AI_FOUNDRY_API_KEY = 'dummy'
    AZURE_AI_FOUNDRY_DEPLOYMENT_NAME = 'test-deployment'
    AZURE_AI_FOUNDRY_API_VERSION = '2024-10-01-preview'
settings = Settings()
config_module.settings = settings
sys.modules['gateway.config'] = config_module

# Stub chat_models
chat_models = types.ModuleType('gateway.app.services.cloudassistance.models.chat_models')
class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
class ChatRequest:
    def __init__(self, message: str, conversation_id=None):
        self.message = message
        self.conversation_id = conversation_id
class ChatResponse:
    def __init__(self, response: str, conversation_id: str, sources=None):
        self.response = response
        self.conversation_id = conversation_id
        self.sources = sources or []
chat_models.ChatMessage = ChatMessage
chat_models.ChatRequest = ChatRequest
chat_models.ChatResponse = ChatResponse
sys.modules['gateway.app.services.cloudassistance.models.chat_models'] = chat_models

from gateway.app.services.cloudassistance.services.devops_agent_service import DevOpsAgentService


def test_process_chat_adds_messages_and_returns_response():
    service = DevOpsAgentService()
    service.azure_client.send_chat_completion = AsyncMock(return_value='pong')

    request = ChatRequest(message='ping')
    response = asyncio.run(service.process_chat(request))

    assert response.response == 'pong'
    assert isinstance(response.conversation_id, str)

    history = service.conversation_service.get_conversation_history(response.conversation_id)
    assert len(history) == 2
    assert history[0].role == 'user'
    assert history[0].content == 'ping'
    assert history[1].role == 'assistant'
    assert history[1].content == 'pong'
