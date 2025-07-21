from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from gateway.config import settings
from gateway.app.auth.controller.auth_controller import router as auth_router
from gateway.app.services.cloudassistance.routers.chat_router import router as chat_router
from gateway.app.auth.middleware.auth_middleware import auth_required

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Unprotected paths (public endpoints)
UNPROTECTED = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/signup",
    "/auth/login",
}

def is_protected(path: str) -> bool:
    """Check if a path requires authentication"""
    return not any(path.startswith(u) for u in UNPROTECTED)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Authentication middleware for protected endpoints"""
    if not is_protected(request.url.path):
        return await call_next(request)

    try:
        # Verify token and set current user
        current_user = await auth_required(request)
        request.state.current_user = current_user
        logger.info(f"User {current_user.id} accessing {request.url.path}")
        return await call_next(request)

    except HTTPException as auth_err:
        logger.warning(f"Auth failed: {auth_err.detail}")
        return JSONResponse(
            status_code=auth_err.status_code,
            content={"error": auth_err.detail, "path": request.url.path},
        )
    except Exception as e:
        logger.error(f"Unexpected auth error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal auth error"},
        )

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)  # Updated router

@app.get("/")
def read_root():
    """Root endpoint"""
    return {"message": "DevOps AI Agent running", "version": settings.VERSION}

@app.get("/health")
def health_check():
    """Global health check endpoint"""
    return {"status": "healthy", "version": settings.VERSION}