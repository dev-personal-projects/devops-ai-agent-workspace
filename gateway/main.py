from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from gateway.config import settings
from gateway.app.auth.controller import auth_controller
from gateway.app.auth.middleware.auth_middleware import  auth_required
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

# Add CORS middleware (must be added before other middlewares)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes that don't require authentication
UNPROTECTED_PATHS = [
    "/",
    "/health",
    "/auth/signup",
    "/auth/login",
    "/docs",
    "/redoc",
    "/openapi.json",
]


def is_protected_path(path: str) -> bool:
    """Check if a path requires authentication"""
    return not any(path.startswith(unprotected) for unprotected in UNPROTECTED_PATHS)


@app.middleware("http")
async def authentication_middleware(request: Request, call_next):
    """Global authentication middleware"""

    # Skip authentication for unprotected paths
    if not is_protected_path(request.url.path):
        response = await call_next(request)
        return response

    try:
        # Authenticate the request - sets request.state.current_user
        await auth_middleware.authenticate_request(request)

        logger.info(f"User {request.state.current_user['id']} accessed {request.url.path}")
        response = await call_next(request)
        return response

    except HTTPException as auth_error:
        logger.warning(f"Authentication failed for {request.url.path}: {auth_error.detail}")
        return JSONResponse(
            status_code=auth_error.status_code,
            content={
                "error": "Authentication failed",
                "detail": auth_error.detail,
                "path": request.url.path
            }
        )
    except Exception as e:
        logger.error(f"Unexpected authentication error for {request.url.path}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal authentication error",
                "detail": "An unexpected error occurred during authentication"
            }
        )


# Include routers
app.include_router(auth_controller.router)


@app.get("/")
def read_root():
    """Root endpoint - publicly accessible"""
    return {
        "message": "DevOps Assistant Agent is running!",
        "version": settings.VERSION,
        "status": "active"
    }


@app.get("/health")
def health_check():
    """Health check endpoint - publicly accessible"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "service": settings.PROJECT_NAME
    }


@app.get("/protected-example")
async def protected_example(request: Request):
    """Example protected endpoint - requires authentication"""
    current_user = request.state.current_user
    return {
        "message": f"Hello authenticated user!",
        "user_id": current_user["id"],
        "email": current_user.get("email"),
        "timestamp": "2025-07-20T12:00:00Z"
    }


# Add startup event handler
@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 {settings.PROJECT_NAME} v{settings.VERSION} starting up...")
    logger.info(f"📝 Documentation available at /docs")
    logger.info(f"🔒 Authentication middleware enabled for protected routes")


# Add shutdown event handler
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"🛑 {settings.PROJECT_NAME} shutting down...")


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "detail": f"The path {request.url.path} was not found",
            "path": request.url.path
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred"
        }
    )