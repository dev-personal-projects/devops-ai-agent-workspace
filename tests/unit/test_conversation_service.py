import sys
import os
import types

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Provide minimal stub for chat_models to avoid pydantic dependency
chat_models = types.ModuleType('gateway.app.services.cloudassistance.models.chat_models')
class ChatMessage:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
chat_models.ChatMessage = ChatMessage
sys.modules['gateway.app.services.cloudassistance.models.chat_models'] = chat_models

from gateway.app.services.cloudassistance.services.conversation_service import ConversationService


def test_conversation_add_and_get():
    service = ConversationService()
    conv_id = service.create_conversation_id()
    msg1 = ChatMessage(role="user", content="hello")
    msg2 = ChatMessage(role="assistant", content="hi there")

    service.add_message(conv_id, msg1)
    service.add_message(conv_id, msg2)

    history = service.get_conversation_history(conv_id)
    assert history == [msg1, msg2]

    formatted = service.format_messages_for_api(history)
    assert formatted == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
