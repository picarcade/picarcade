from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import generation, uploads, references, auth
from app.core.config import settings
from app.core.database import db_manager
from app.services.session_manager import session_manager
import os

# Debug print for environment variable and settings
print("REPLICATE_API_TOKEN in backend env:", os.environ.get("REPLICATE_API_TOKEN"))
print("settings.replicate_api_token:", settings.replicate_api_token)

app = FastAPI(
    title="Pictures API",
    description="AI-powered image and video generation with intelligent routing",
    version="1.0.0-phase1",
    openapi_url=f"{settings.api_v1_str}/openapi.json"
)

# Add CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "https://your-domain.vercel.app"  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and session tables on startup
@app.on_event("startup")
async def startup_event():
    await db_manager.create_tables()
    await session_manager.create_session_tables()

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