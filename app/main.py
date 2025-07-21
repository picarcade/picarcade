from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.database import db_manager
from app.services.session_manager import session_manager
import os
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Environment validation (production-safe)
import logging
logger = logging.getLogger(__name__)
logger.info("API keys loaded: %s", 
    {
        "replicate": bool(settings.replicate_api_token),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }
)

# Import API routes after environment is loaded
from app.api.v1 import generation, uploads, references, auth
from app.api import health
from app.api.simplified_endpoints import router as simplified_router

# Initialize database and session tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db_manager.create_tables()
    await session_manager.create_session_tables()
    yield
    # Shutdown (if needed)

app = FastAPI(
    title="Pictures API",
    description="AI-powered image and video generation with intelligent routing",
    version="1.0.0-phase1",
    openapi_url=f"{settings.api_v1_str}/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://localhost:3001",  # Next.js dev server (backup port)
        "http://localhost:3002",  # Next.js dev server (backup port)
        "http://localhost:3003",  # Next.js dev server (backup port)
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://127.0.0.1:3003",
        "https://picarcade.ai",  # Production domain
        "https://www.picarcade.ai",  # Production domain with www
        "https://picarcade-frontend.vercel.app",  # Your specific frontend
        "https://picarcade-frontend-68ol897kk-jamesskelton-nexefys-projects.vercel.app",  # Latest deployment with auth fix
        "*"  # Allow all origins for testing (remove in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add validation error handler for better 422 debugging
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error("Validation error on %s: %s", request.url, exc.errors())
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "body": str(exc.body) if hasattr(exc, 'body') else None
        }
    )

# Include API routes
app.include_router(
    auth.router,
    prefix=f"{settings.api_v1_str}/auth",
    tags=["authentication"]
)

app.include_router(
    generation.router,
    prefix=f"{settings.api_v1_str}/generation",
    tags=["generation"]
)

app.include_router(
    uploads.router,
    prefix=f"{settings.api_v1_str}/uploads",
    tags=["uploads"]
)

app.include_router(
    references.router,
    prefix=f"{settings.api_v1_str}/references",
    tags=["references"]
)

app.include_router(
    health.router,
    tags=["health"]
)

app.include_router(
    simplified_router,
    tags=["simplified-flow"]
)

@app.get("/")
async def root():
    return {
        "message": "Pictures API - AI-powered content generation",
        "version": "1.0.0-phase1",
        "status": "active",
        "database": "supabase",
        "authentication": "enabled"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "phase": "1",
        "database": "connected" if db_manager.supabase else "disconnected",
        "authentication": "supabase"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 