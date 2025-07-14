from fastapi import APIRouter, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from app.services.session_manager import session_manager

router = APIRouter()
security = HTTPBearer()

# Pydantic models for request/response
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    metadata: Optional[Dict[str, Any]] = None

class RefreshRequest(BaseModel):
    refresh_token: str

class AuthResponse(BaseModel):
    user: Dict[str, Any]
    session: Optional[Dict[str, Any]] = None
    access_token: str
    refresh_token: str
    message: Optional[str] = None

class UserResponse(BaseModel):
    user: Dict[str, Any]

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user from JWT token"""
    try:
        access_token = credentials.credentials
        user = await session_manager.get_user_from_token(access_token)
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password
    Returns access token and refresh token for session management
    """
    try:
        auth_result = await session_manager.authenticate_user(
            email=request.email,
            password=request.password
        )
        
        if not auth_result:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Create a session record in user_sessions table
        session_id = auth_result["session"].access_token if auth_result["session"] else auth_result["access_token"]
        user_id = auth_result["user"].id if hasattr(auth_result["user"], 'id') else str(auth_result["user"])
        
        # Create session record for tracking
        await session_manager.create_session(
            session_id=session_id,
            user_id=user_id,
            metadata={"login_time": "now", "source": "login_endpoint"}
        )
        
        return AuthResponse(
            user=auth_result["user"].__dict__,
            session=auth_result["session"].__dict__ if auth_result["session"] else None,
            access_token=auth_result["access_token"],
            refresh_token=auth_result["refresh_token"],
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed: {str(e)}"
        )

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """
    Register a new user with email and password
    Returns user info and session tokens
    """
    try:
        auth_result = await session_manager.register_user(
            email=request.email,
            password=request.password,
            metadata=request.metadata
        )
        
        if not auth_result:
            raise HTTPException(
                status_code=400,
                detail="Registration failed. Email may already be in use."
            )
        
        # Create a session record in user_sessions table if session exists
        if auth_result.get("session"):
            session_id = auth_result["session"].access_token
            user_id = auth_result["user"].id if hasattr(auth_result["user"], 'id') else str(auth_result["user"])
            
            await session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                metadata={"registration_time": "now", "source": "register_endpoint"}
            )
        
        return AuthResponse(
            user=auth_result["user"].__dict__,
            session=auth_result["session"].__dict__ if auth_result["session"] else None,
            access_token=auth_result["session"].access_token if auth_result["session"] else "",
            refresh_token=auth_result["session"].refresh_token if auth_result["session"] else "",
            message=auth_result.get("message", "Registration successful")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using refresh token
    """
    try:
        auth_result = await session_manager.refresh_session(request.refresh_token)
        
        if not auth_result:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired refresh token"
            )
        
        # Get user info from the new access token
        user = await session_manager.get_user_from_token(auth_result["access_token"])
        
        return AuthResponse(
            user=user.__dict__ if user else {},
            session=auth_result["session"].__dict__,
            access_token=auth_result["access_token"],
            refresh_token=auth_result["refresh_token"],
            message="Token refreshed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Token refresh failed: {str(e)}"
        )

@router.post("/logout")
async def logout(current_user: Dict = Depends(get_current_user)):
    """
    Logout current user and invalidate session
    """
    try:
        await session_manager.sign_out()
        return {"message": "Logout successful"}
        
    except Exception as e:
        # Don't fail logout even if there's an error
        return {"message": "Logout completed"}

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: Dict = Depends(get_current_user)):
    """
    Get current authenticated user information
    """
    return UserResponse(user=current_user)

@router.get("/validate")
async def validate_token(current_user: Dict = Depends(get_current_user)):
    """
    Validate if the current token is still valid
    Returns user info if valid, 401 if invalid
    """
    return {
        "valid": True,
        "user": current_user,
        "message": "Token is valid"
    } 