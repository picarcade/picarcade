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
    """Dependency to get current authenticated user from JWT token - Updated for new Supabase API keys"""
    try:
        access_token = credentials.credentials
        print(f"[DEBUG Auth] Attempting to validate token: {access_token[:20]}...")
        
        user = await session_manager.get_user_from_token(access_token)
        
        if not user:
            print(f"[DEBUG Auth] Token validation failed - no user returned")
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token - please sign in again"
            )
        
        print(f"[DEBUG Auth] User validated successfully: {user.get('id', 'unknown')}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG Auth] Authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}"
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
            
            # Gift 200 XP to new user
            from app.services.subscription_service import subscription_service
            await subscription_service.create_initial_xp_balance(user_id, 200)
        
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

class MagicLinkRequest(BaseModel):
    email: EmailStr

class MagicLinkVerifyRequest(BaseModel):
    token_hash: str
    type: str = "email"

@router.post("/send-magic-link")
async def send_magic_link(request: MagicLinkRequest):
    """
    Send magic link to user's email for passwordless authentication
    Creates user account if it doesn't exist
    """
    try:
        # Get frontend URL from environment or default
        from app.core.config import settings
        frontend_url = getattr(settings, 'frontend_url', 'http://localhost:3000')
        
        # Use Supabase's built-in magic link functionality
        response = session_manager.supabase.auth.sign_in_with_otp({
            "email": request.email,
            "options": {
                "should_create_user": True,  # Auto-create users
                "email_redirect_to": f"{frontend_url}/auth/callback"
            }
        })
        
        return {
            "message": "Magic link sent! Check your email to sign in.",
            "email": request.email
        }
        
    except Exception as e:
        print(f"[DEBUG] Magic link send error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to send magic link: {str(e)}"
        )

@router.post("/verify-magic-link")
async def verify_magic_link(request: MagicLinkVerifyRequest):
    """
    Verify magic link token and create session
    """
    try:
        # Verify the magic link token
        response = session_manager.supabase.auth.verify_otp({
            "token_hash": request.token_hash,
            "type": request.type
        })
        
        if not response.user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired magic link"
            )
        
        # Create session in our system
        if response.session:
            session_id = response.session.access_token
            user_id = response.user.id
            
            await session_manager.create_session(
                session_id=session_id,
                user_id=user_id,
                metadata={"magic_link_login": True, "login_time": "now"}
            )
        
        return {
            "user": response.user.__dict__ if hasattr(response.user, '__dict__') else str(response.user),
            "session": response.session.__dict__ if response.session and hasattr(response.session, '__dict__') else None,
            "access_token": response.session.access_token if response.session else "",
            "refresh_token": response.session.refresh_token if response.session else "",
            "message": "Magic link verified successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DEBUG] Magic link verify error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or expired magic link: {str(e)}"
        ) 