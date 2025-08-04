from typing import Dict, Optional, Any
import time
from datetime import datetime, timedelta, timezone
import os
import jwt
from app.core.database import db_manager
from supabase import Client

class SupabaseSessionManager:
    """
    Supabase-based session manager that provides persistent sessions
    with JWT authentication support
    """
    
    def __init__(self):
        self.supabase: Client = db_manager.supabase
        self.session_timeout = 3600  # 1 hour timeout
        
        # Enable more verbose logging for session debugging
        self.verbose_logging = os.getenv("SESSION_DEBUG", "false").lower() == "true"
        
        self.cache = None  # Redis cache for session data
    
    async def _get_cache(self):
        """Get Redis cache instance (lazy initialization)"""
        if not self.cache:
            try:
                from app.core.cache import get_cache
                self.cache = await get_cache()
            except Exception as e:
                print(f"[WARNING] Cache not available for sessions: {e}")
                self.cache = None
        return self.cache
    
    async def create_session_tables(self):
        """Create sessions table if it doesn't exist"""
        # This should be run via Supabase migration
        session_table_sql = """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id SERIAL PRIMARY KEY,
            session_id TEXT UNIQUE NOT NULL,
            user_id TEXT,
            current_working_image TEXT,
            metadata JSONB DEFAULT '{}',
            expires_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
        """
        
        print("Please run the following SQL in your Supabase SQL editor:")
        print(session_table_sql)
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with Supabase Auth"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if response.user and response.session:
                return {
                    "user": response.user,
                    "session": response.session,
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                }
            return None
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] Authentication error: {e}")
            return None
    
    async def register_user(self, email: str, password: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Register new user with Supabase Auth"""
        try:
            signup_data = {"email": email, "password": password}
            if metadata:
                signup_data["data"] = metadata
                
            response = self.supabase.auth.sign_up(signup_data)
            
            if response.user:
                return {
                    "user": response.user,
                    "session": response.session,
                    "message": "Registration successful. Check your email for confirmation."
                }
            return None
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] Registration error: {e}")
            return None
    
    async def get_user_from_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from JWT access token - Updated for new Supabase API keys"""
        try:
            print(f"[DEBUG AUTH] Starting token validation for token: {access_token[:50]}...")
            print(f"[DEBUG AUTH] Token type check:")
            print(f"[DEBUG AUTH]   Length: {len(access_token)}")
            print(f"[DEBUG AUTH]   Starts with 'ey': {access_token.startswith('ey')}")
            print(f"[DEBUG AUTH]   Contains dots: {access_token.count('.')}")
            
            # Method 1: Use get_user() directly with JWT token (FIXED)
            try:
                print(f"[DEBUG AUTH] Attempting Method 1: Direct get_user with JWT")
                from supabase import create_client
                from app.core.config import settings
                
                print(f"[DEBUG AUTH] Creating client with URL: {settings.supabase_url[:50]}...")
                print(f"[DEBUG AUTH] Using key: {settings.supabase_key[:20]}...")
                
                from supabase.client import ClientOptions
                
                user_supabase = create_client(
                    settings.supabase_url,
                    settings.supabase_key,  # Use anon key for user operations
                    options=ClientOptions(
                        auto_refresh_token=False,
                        persist_session=False
                    )
                )
                
                print(f"[DEBUG AUTH] Getting user directly with JWT token...")
                # Use get_user() directly with the JWT token instead of set_session()
                user_response = user_supabase.auth.get_user(jwt=access_token)
                
                print(f"[DEBUG AUTH] User response type: {type(user_response)}")
                print(f"[DEBUG AUTH] Has user: {hasattr(user_response, 'user') and user_response.user is not None}")
                
                if hasattr(user_response, 'user') and user_response.user:
                    print(f"[DEBUG AUTH] User object type: {type(user_response.user)}")
                    print(f"[DEBUG AUTH] User ID: {getattr(user_response.user, 'id', 'NO_ID')}")
                    print(f"[DEBUG AUTH] User email: {getattr(user_response.user, 'email', 'NO_EMAIL')}")
                
                if user_response and user_response.user:
                    print(f"[DEBUG AUTH] ✅ User validated via Method 1: {user_response.user.id}")
                    return user_response.user.__dict__
                else:
                    print(f"[DEBUG AUTH] ❌ No user found in response")
                    
            except Exception as e:
                print(f"[DEBUG AUTH] ❌ Method 1 failed: {type(e).__name__}: {e}")
                import traceback
                print(f"[DEBUG AUTH] Full traceback: {traceback.format_exc()}")
                
                # Continue to Method 2 if Method 1 fails
                pass
            
            # Method 2: Try direct JWT decoding and validation (fallback)
            try:
                print(f"[DEBUG AUTH] Attempting Method 2: Direct JWT validation")
                user_id = self._extract_user_id_from_jwt(access_token)
                print(f"[DEBUG AUTH] Extracted user ID: {user_id}")
                
                if user_id:
                    print(f"[DEBUG AUTH] Getting user by ID via admin client...")
                    user_response = self.supabase.auth.admin.get_user_by_id(user_id)
                    print(f"[DEBUG AUTH] Admin user response: {user_response}")
                    
                    if user_response and user_response.user:
                        # Additional verification: ensure the token is valid
                        if self._verify_jwt_token(access_token):
                            print(f"[DEBUG AUTH] ✅ User validated via admin method: {user_id}")
                            return user_response.user.__dict__
                        else:
                            print(f"[DEBUG AUTH] ❌ JWT token verification failed")
                    else:
                        print(f"[DEBUG AUTH] ❌ No user found via admin client")
                else:
                    print(f"[DEBUG AUTH] ❌ Could not extract user ID from JWT")
            except Exception as e:
                print(f"[DEBUG AUTH] ❌ Admin method failed: {type(e).__name__}: {e}")
            
            print(f"[DEBUG AUTH] ❌ All validation methods failed")
            return None
            
        except Exception as e:
            print(f"[DEBUG AUTH] ❌ Critical error in token validation: {type(e).__name__}: {e}")
            return None
    
    def _extract_user_id_from_jwt(self, access_token: str) -> str:
        """Extract user ID from JWT token"""
        try:
            import base64
            import json
            
            # JWT tokens have 3 parts separated by dots
            parts = access_token.split('.')
            if len(parts) != 3:
                return None
            
            # Decode the payload (second part)
            payload = parts[1]
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded_payload = base64.b64decode(payload)
            payload_data = json.loads(decoded_payload)
            
            return payload_data.get('sub')  # 'sub' contains the user ID
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] Error extracting user ID from JWT: {e}")
            return None
    
    def _verify_jwt_token(self, access_token: str) -> bool:
        """Verify JWT token signature and expiration"""
        try:
            import jwt
            from app.core.config import settings
            
            # Get JWT secret from Supabase settings
            jwt_secret = settings.supabase_jwt_secret
            if not jwt_secret:
                # Fallback: try to validate without signature verification
                decoded = jwt.decode(access_token, options={"verify_signature": False})
                # Check if token is expired
                import time
                current_time = time.time()
                if decoded.get('exp', 0) < current_time:
                    return False
                return True
            
            # Verify with signature if secret is available
            decoded = jwt.decode(
                access_token,
                jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
            return True
            
        except jwt.ExpiredSignatureError:
            if self.verbose_logging:
                print("[DEBUG] JWT token has expired")
            return False
        except jwt.InvalidTokenError as e:
            if self.verbose_logging:
                print(f"[DEBUG] Invalid JWT token: {e}")
            return False
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] JWT verification error: {e}")
            return False
    
    async def refresh_session(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh user session using refresh token"""
        try:
            response = self.supabase.auth.refresh_session(refresh_token)
            
            if response.session:
                return {
                    "session": response.session,
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token
                }
            return None
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] Session refresh error: {e}")
            return None
    
    async def create_session(self, session_id: str, user_id: str = None, metadata: Dict[str, Any] = None) -> bool:
        """Create a new session record"""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
            
            session_data = {
                "session_id": session_id,
                "user_id": user_id,
                "metadata": metadata or {},
                "expires_at": expires_at.isoformat()
            }
            
            result = self.supabase.table("user_sessions").insert(session_data).execute()
            return len(result.data) > 0
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] Session creation error: {e}")
            return False
    
    async def get_current_working_image(self, session_id: str) -> Optional[str]:
        """Get current working image for session (with caching)"""
        if not session_id:
            return None
        
        # Check cache first
        cache = await self._get_cache()
        cache_key = f"session_image:{session_id}"
        
        if cache:
            try:
                cached_image = await cache.get(cache_key)
                if cached_image:
                    print(f"[DEBUG] Cache HIT for session image: {session_id}")
                    return cached_image
            except Exception as e:
                print(f"[WARNING] Cache get failed for session: {e}")
        
        # Query database if not cached
        print(f"[DEBUG] SessionManager: Querying for session_id: {session_id}")
        
        try:
            response = self.supabase.table("user_sessions")\
                .select("current_working_image, expires_at")\
                .eq("session_id", session_id)\
                .execute()
            
            # Handle case where session doesn't exist (0 rows)
            if not response.data:
                print(f"[DEBUG] SessionManager: Session {session_id} not found in database")
                # Try to create a new session for this session_id
                print(f"[DEBUG] SessionManager: Auto-creating session {session_id}")
                success = await self.create_session(session_id)
                if success:
                    print(f"[DEBUG] SessionManager: Successfully created new session {session_id}")
                    return None  # No working image yet for new session
                else:
                    print(f"[ERROR] SessionManager: Failed to create session {session_id}")
                    return None
            
            # Handle case where multiple sessions exist (should not happen with unique constraint)
            if len(response.data) > 1:
                print(f"[WARNING] SessionManager: Multiple sessions found for {session_id}, using first")
            
            session_data = response.data[0]
            if session_data:
                print(f"[DEBUG] SessionManager: Query result: {session_data}")
                
                expires_at_str = session_data.get("expires_at")
                current_working_image = session_data.get("current_working_image")
                
                if expires_at_str:
                    from datetime import datetime
                    print(f"[DEBUG] SessionManager: Raw expires_at: {expires_at_str}")
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    current_time = datetime.now(expires_at.tzinfo)
                    
                    print(f"[DEBUG] SessionManager: expires_at: {expires_at}, current_time: {current_time}")
                    
                    if current_time > expires_at:
                        print(f"[DEBUG] SessionManager: Session {session_id} expired")
                        return None
                
                if current_working_image:
                    # Cache the result for 10 minutes
                    if cache:
                        try:
                            await cache.set(cache_key, current_working_image, ttl=600)
                            print(f"[DEBUG] Cached session image for: {session_id}")
                        except Exception as e:
                            print(f"[WARNING] Cache set failed for session: {e}")
                    
                    print(f"[DEBUG] SessionManager: Retrieved working image for {session_id}: {current_working_image}")
                    return current_working_image
                else:
                    print(f"[DEBUG] SessionManager: No working image for session {session_id}")
                    return None
            else:
                print(f"[DEBUG] SessionManager: Session {session_id} not found")
                return None
                
        except Exception as e:
            print(f"[ERROR] SessionManager: Error retrieving session {session_id}: {e}")
            return None
    
    async def set_current_working_image(self, session_id: str, image_url: str, user_id: str) -> bool:
        """Set current working image for session (and update cache)"""
        if not session_id or not image_url:
            return False
        
        try:
            from datetime import datetime, timedelta
            
            # Set expiry to 1 hour from now
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # First try to update existing session
            # Clear working video when setting working image (mutual exclusion)
            update_response = self.supabase.table("user_sessions")\
                .update({
                    "current_working_image": image_url,
                    "current_working_video": None,  # Clear video when setting image
                    "expires_at": expires_at.isoformat() + "Z",
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                })\
                .eq("session_id", session_id)\
                .execute()
            
            # If no rows were updated, insert a new session
            if not update_response.data:
                insert_response = self.supabase.table("user_sessions")\
                    .insert({
                        "session_id": session_id,
                        "user_id": user_id,
                        "current_working_image": image_url,
                        "current_working_video": None,  # Ensure video is null when setting image
                        "expires_at": expires_at.isoformat() + "Z",
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    })\
                    .execute()
                response = insert_response
            else:
                response = update_response
            
            if response.data:
                print(f"[DEBUG] SessionManager: Session {session_id} updated successfully")
                
                # Update cache (set image, clear video)
                cache = await self._get_cache()
                if cache:
                    try:
                        # Set image cache
                        image_cache_key = f"session_image:{session_id}"
                        await cache.set(image_cache_key, image_url, ttl=600)  # 10 minutes
                        
                        # Clear video cache (mutual exclusion)
                        video_cache_key = f"session_video:{session_id}"
                        await cache.delete(video_cache_key)
                        
                        print(f"[DEBUG] Updated image cache and cleared video cache for session: {session_id}")
                    except Exception as e:
                        print(f"[WARNING] Cache update failed for session: {e}")
                
                return True
            else:
                print(f"[ERROR] SessionManager: Failed to update session {session_id}")
                return False
                
        except Exception as e:
            print(f"[ERROR] SessionManager: Error setting working image: {e}")
            return False
    
    async def clear_session(self, session_id: str):
        """Clear a session"""
        try:
            self.supabase.table("user_sessions")\
                .delete()\
                .eq("session_id", session_id)\
                .execute()
            print(f"[DEBUG] SessionManager: Session {session_id} cleared")
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] SessionManager: Error clearing session: {e}")
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (call periodically)"""
        try:
            current_time = datetime.utcnow().isoformat()
            result = self.supabase.table("user_sessions")\
                .delete()\
                .lt("expires_at", current_time)\
                .execute()
            
            if self.verbose_logging and result.data:
                print(f"[DEBUG] SessionManager: Cleaned up {len(result.data)} expired sessions")
                
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] SessionManager: Error cleaning up sessions: {e}")
    
    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get full session information"""
        if not session_id:
            return None
        
        try:
            result = self.supabase.table("user_sessions")\
                .select("*")\
                .eq("session_id", session_id)\
                .single()\
                .execute()
            
            if result.data:
                # Check if session has expired
                expires_at = datetime.fromisoformat(result.data["expires_at"].replace('Z', '+00:00'))
                if expires_at < datetime.utcnow().replace(tzinfo=expires_at.tzinfo):
                    await self.clear_session(session_id)
                    return None
                
                return {
                    "session_id": result.data["session_id"],
                    "user_id": result.data["user_id"],
                    "current_working_image": result.data["current_working_image"],
                    "current_working_video": result.data.get("current_working_video"),
                    "metadata": result.data["metadata"],
                    "created_at": result.data["created_at"],
                    "updated_at": result.data["updated_at"],
                    "expires_at": result.data["expires_at"]
                }
            return None
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] SessionManager: Error getting session info: {e}")
            return None
    
    async def sign_out(self, access_token: str = None):
        """Sign out user from Supabase Auth"""
        try:
            if access_token:
                self.supabase.auth.session = {"access_token": access_token}
            
            self.supabase.auth.sign_out()
            print(f"[DEBUG] SessionManager: User signed out successfully")
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] SessionManager: Error signing out: {e}")
    
    async def get_current_working_video(self, session_id: str) -> Optional[str]:
        """Get current working video for session (with caching)"""
        
        if not session_id:
            return None
        
        # Check cache first
        cache = await self._get_cache()
        cache_key = f"session_video:{session_id}"
        
        if cache:
            try:
                cached_video = await cache.get(cache_key)
                if cached_video:
                    print(f"[DEBUG] Cache HIT for session video: {session_id}")
                    return cached_video
            except Exception as e:
                print(f"[WARNING] Cache error for session video: {e}")
        
        # Query database if not cached
        print(f"[DEBUG] SessionManager: Querying for session video: {session_id}")
        
        try:
            response = self.supabase.table("user_sessions")\
                .select("current_working_video, expires_at")\
                .eq("session_id", session_id)\
                .execute()
            
            # Handle case where session doesn't exist (0 rows)
            if not response.data:
                print(f"[DEBUG] SessionManager: Session {session_id} not found in database")
                return None
            
            session_data = response.data[0]
            if session_data:
                expires_at_str = session_data.get("expires_at")
                current_working_video = session_data.get("current_working_video")
                
                if expires_at_str:
                    from datetime import datetime
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    current_time = datetime.now(expires_at.tzinfo)
                    
                    if current_time > expires_at:
                        print(f"[DEBUG] SessionManager: Session {session_id} expired")
                        return None
                
                if current_working_video:
                    # Cache the result for 10 minutes
                    if cache:
                        try:
                            await cache.set(cache_key, current_working_video, ttl=600)
                            print(f"[DEBUG] Cached session video for: {session_id}")
                        except Exception as e:
                            print(f"[WARNING] Cache set failed for session: {e}")
                    
                    print(f"[DEBUG] SessionManager: Retrieved working video for {session_id}: {current_working_video}")
                    return current_working_video
                else:
                    print(f"[DEBUG] SessionManager: No working video for session {session_id}")
                    return None
                
        except Exception as e:
            print(f"[ERROR] SessionManager: Error retrieving session video {session_id}: {e}")
            return None
    
    async def set_current_working_video(self, session_id: str, video_url: str, user_id: str) -> bool:
        """Set current working video for session (and update cache)"""
        if not session_id or not video_url:
            return False
        
        try:
            from datetime import datetime, timedelta
            
            # Set expiry to 1 hour from now
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # First try to update existing session
            # Clear working image when setting working video (mutual exclusion)
            update_response = self.supabase.table("user_sessions")\
                .update({
                    "current_working_video": video_url,
                    "current_working_image": None,  # Clear image when setting video
                    "expires_at": expires_at.isoformat() + "Z",
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                })\
                .eq("session_id", session_id)\
                .execute()
            
            # If no rows were updated, insert a new session
            if not update_response.data:
                insert_response = self.supabase.table("user_sessions")\
                    .insert({
                        "session_id": session_id,
                        "user_id": user_id,
                        "current_working_video": video_url,
                        "current_working_image": None,  # Ensure image is null when setting video
                        "expires_at": expires_at.isoformat() + "Z",
                        "updated_at": datetime.utcnow().isoformat() + "Z"
                    })\
                    .execute()
                response = insert_response
            else:
                response = update_response
            
            if response.data:
                print(f"[DEBUG] SessionManager: Set working video for session {session_id}: {video_url}")
                
                # Update cache (set video, clear image)
                cache = await self._get_cache()
                if cache:
                    try:
                        # Set video cache
                        video_cache_key = f"session_video:{session_id}"
                        await cache.set(video_cache_key, video_url, ttl=600)
                        
                        # Clear image cache (mutual exclusion)
                        image_cache_key = f"session_image:{session_id}"
                        await cache.delete(image_cache_key)
                        
                        print(f"[DEBUG] Updated video cache and cleared image cache for session: {session_id}")
                    except Exception as e:
                        print(f"[WARNING] Cache update failed for session: {e}")
                
                return True
            else:
                print(f"[ERROR] SessionManager: Failed to set working video for session {session_id}")
                return False
                
        except Exception as e:
            print(f"[ERROR] SessionManager: Error setting session video {session_id}: {e}")
            return False

# Global session manager instance
session_manager = SupabaseSessionManager() 