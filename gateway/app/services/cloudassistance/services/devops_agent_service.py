from typing import List
import logging

from gateway.app.services.cloudassistance.services.azure_client import  AzureAIFoundryClient
from gateway.app.services.cloudassistance.models.chat_models import ChatMessage, ChatRequest, ChatResponse
from gateway.app.services.cloudassistance.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

class DevOpsAgentService:
    """
       Main service orchestrating the DevOps AI Agent.
       Implements Dependency Inversion Principle - depends on abstractions.
       """

    # System prompt for DevOps expertise
    SYSTEM_PROMPT = """You are an expert DevOps and Cloud Engineering AI Assistant. You help engineers with:

    - Cloud platforms (AWS, Azure, GCP)
    - Infrastructure as Code (Terraform, ARM templates, CloudFormation)
    - Container orchestration (Docker, Kubernetes)
    - CI/CD pipelines (Jenkins, GitHub Actions, Azure DevOps)
    - Monitoring and observability
    - Security best practices
    - Configuration management
    - Site reliability engineering (SRE)

    Provide practical, actionable advice with code examples when helpful. Be concise but thorough."""

    def __init__(self):
        self.azure_client = AzureAIFoundryClient()
        self.conversation_service = ConversationService()

    async def process_chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat request and return response.

        Args:
            request: Chat request with message and optional conversation ID

        Returns:
            Chat response with AI answer and conversation ID
        """
        try:
            # Get or create conversation ID
            conversation_id = request.conversation_id or self.conversation_service.create_conversation_id()

            # Get conversation history for context
            history = self.conversation_service.get_conversation_history(conversation_id)

            # Build messages for API call
            messages = self._build_messages(history, request.message)

            # Get AI response
            ai_response = await self.azure_client.send_chat_completion(messages)

            # Store user message and AI response
            user_message = ChatMessage(role="user", content=request.message)
            assistant_message = ChatMessage(role="assistant", content=ai_response)

            self.conversation_service.add_message(conversation_id, user_message)
            self.conversation_service.add_message(conversation_id, assistant_message)

            return ChatResponse(
                response=ai_response,
                conversation_id=conversation_id,
                sources=[]  # Azure AI Foundry will handle RAG internally
            )

        except Exception as e:
            logger.error(f"Error processing chat: {e}")
            raise

    def _build_messages(self, history: List[ChatMessage], current_message: str) -> List[dict]:
            """
            Build message list for API call including system prompt and conversation history.

            Args:
                history: Previous conversation messages
                current_message: Current user message

            Returns:
                Formatted messages for Azure API
            """
            messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

            # Add conversation history
            for msg in history:
                messages.append({"role": msg.role, "content": msg.content})

            # Add current user message
            messages.append({"role": "user", "content": current_message})

            return messages

