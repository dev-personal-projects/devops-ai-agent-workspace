from fastapi import APIRouter, HTTPException, Depends
import logging
from gateway.app.services.cloudassistance.models.chat_models import ChatRequest, ChatResponse
from gateway.app.services.cloudassistance.services.devops_agent_service import DevOpsAgentService

logger = logging.getLogger(__name__)
# Router for chat-related endpoints
router = APIRouter(prefix="/api/v1/chat", tags=[" Devops chat"])

# Dependency injection - creates service instance
def get_devops_service() -> DevOpsAgentService:
    """
    Dependency injection for DevOpsAgentService.
    Returns:
        DevOpsAgentService instance
    """
    return DevOpsAgentService()


@router.post("/", response_model=ChatResponse)
async def chat_with_agent(
        request: ChatRequest,
        devops_service: DevOpsAgentService = Depends(get_devops_service)
):
    """
    Chat with the DevOps AI Agent.

    Send a message and get an AI-powered response about DevOps and cloud engineering topics.
    The agent maintains conversation context using the conversation_id.
    """
    try:
        logger.info(f"Processing chat request: {request.message[:50]}...")
        response = await devops_service.process_chat(request)
        logger.info("Chat request processed successfully")
        return response

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your request. Please try again."
        )


@router.get("/health")
async def chat_health_check():
    """Health check for chat service"""
    return {"status": "healthy", "service": "devops-chat"}