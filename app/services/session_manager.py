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
        """Get user information from JWT access token"""
        try:
            # Set the session with the access token
            self.supabase.auth.session = {"access_token": access_token}
            user_response = self.supabase.auth.get_user()
            
            if user_response and user_response.user:
                return user_response.user.__dict__
            return None
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] Token verification error: {e}")
            return None
    
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
        """Get the current working image for a session"""
        if not session_id:
            print(f"[DEBUG] SessionManager: No session_id provided")
            return None
        
        try:
            print(f"[DEBUG] SessionManager: Querying for session_id: {session_id}")
            result = self.supabase.table("user_sessions")\
                .select("current_working_image, expires_at")\
                .eq("session_id", session_id)\
                .single()\
                .execute()
            
            print(f"[DEBUG] SessionManager: Query result: {result.data}")
            
            if result.data:
                # Check if session has expired  
                expires_at_str = result.data["expires_at"]
                print(f"[DEBUG] SessionManager: Raw expires_at: {expires_at_str}")
                
                # Handle timezone parsing more robustly
                try:
                    if expires_at_str.endswith('Z'):
                        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    elif '+00:00' in expires_at_str:
                        expires_at = datetime.fromisoformat(expires_at_str)
                    else:
                        # Assume UTC if no timezone info
                        expires_at = datetime.fromisoformat(expires_at_str).replace(tzinfo=timezone.utc)
                    
                    current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
                    print(f"[DEBUG] SessionManager: expires_at: {expires_at}, current_time: {current_time}")
                    
                    if expires_at < current_time:
                        print(f"[DEBUG] SessionManager: Session {session_id} expired, clearing")
                        await self.clear_session(session_id)
                        return None
                        
                except Exception as tz_error:
                    print(f"[DEBUG] SessionManager: Timezone parsing error: {tz_error}, assuming session valid")
                
                working_image = result.data.get("current_working_image")
                print(f"[DEBUG] SessionManager: Retrieved working image for {session_id}: {working_image}")
                return working_image
            else:
                print(f"[DEBUG] SessionManager: Session {session_id} not found")
                return None
                
        except Exception as e:
            print(f"[DEBUG] SessionManager: Error retrieving working image: {e}")
            import traceback
            print(f"[DEBUG] SessionManager: Full traceback: {traceback.format_exc()}")
            return None
    
    async def set_current_working_image(self, session_id: str, image_url: str, user_id: str = None):
        """Set the current working image for a session"""
        if not session_id:
            print(f"[DEBUG] SessionManager: No session_id provided for setting working image")
            return
        
        print(f"[DEBUG] SessionManager: Setting working image for {session_id}: {image_url}")
        
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=self.session_timeout)
            
            # Try to update existing session first
            update_result = self.supabase.table("user_sessions")\
                .update({
                    "current_working_image": image_url,
                    "user_id": user_id,
                    "expires_at": expires_at.isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                })\
                .eq("session_id", session_id)\
                .execute()
            
            # If no rows updated, create new session
            if not update_result.data:
                await self.create_session(session_id, user_id, {"current_working_image": image_url})
            
            print(f"[DEBUG] SessionManager: Session {session_id} updated successfully")
            
        except Exception as e:
            if self.verbose_logging:
                print(f"[DEBUG] SessionManager: Error setting working image: {e}")
    
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

# Global session manager instance
session_manager = SupabaseSessionManager() 