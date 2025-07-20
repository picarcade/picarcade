"""
Vercel-compatible entry point for PicArcade FastAPI backend
"""
import sys
import os

# Add the parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

# This is the ASGI application that Vercel will serve
# The variable name 'app' is important for Vercel to detect 