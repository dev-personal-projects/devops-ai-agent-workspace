from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from gateway.config import settings
from gateway.app.auth.controller import auth_controller

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_controller.router)

@app.get("/")
def read_root():
    return {"message": "DevOps Assistant Agent is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": settings.VERSION}