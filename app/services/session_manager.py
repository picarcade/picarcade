from typing import Dict, Optional
import time
from datetime import datetime, timedelta

class SessionManager:
    """
    Manages conversation sessions and tracks current working images
    for contextual image editing workflows
    """
    
    def __init__(self):
        # In-memory storage for sessions (could be Redis in production)
        self.sessions: Dict[str, Dict] = {}
        self.session_timeout = 3600  # 1 hour timeout
    
    def get_current_working_image(self, session_id: str) -> Optional[str]:
        """Get the current working image for a session"""
        if not session_id:
            print(f"[DEBUG] SessionManager: No session_id provided")
            return None
            
        session = self.sessions.get(session_id)
        if not session:
            print(f"[DEBUG] SessionManager: Session {session_id} not found")
            return None
            
        # Check if session has expired
        if self._is_session_expired(session):
            print(f"[DEBUG] SessionManager: Session {session_id} expired, clearing")
            self.clear_session(session_id)
            return None
        
        working_image = session.get("current_working_image")
        print(f"[DEBUG] SessionManager: Retrieved working image for {session_id}: {working_image}")
        return working_image
    
    def set_current_working_image(self, session_id: str, image_url: str, user_id: str = None):
        """Set the current working image for a session"""
        if not session_id:
            print(f"[DEBUG] SessionManager: No session_id provided for setting working image")
            return
        
        print(f"[DEBUG] SessionManager: Setting working image for {session_id}: {image_url}")
        
        self.sessions[session_id] = {
            "current_working_image": image_url,
            "user_id": user_id,
            "last_updated": time.time(),
            "created_at": self.sessions.get(session_id, {}).get("created_at", time.time())
        }
        
        print(f"[DEBUG] SessionManager: Session {session_id} updated successfully")
    
    def clear_session(self, session_id: str):
        """Clear a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def _is_session_expired(self, session: Dict) -> bool:
        """Check if a session has expired"""
        last_updated = session.get("last_updated", 0)
        return time.time() - last_updated > self.session_timeout
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (call periodically)"""
        expired_sessions = []
        for session_id, session in self.sessions.items():
            if self._is_session_expired(session):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.clear_session(session_id)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get full session information"""
        if not session_id:
            return None
            
        session = self.sessions.get(session_id)
        if not session or self._is_session_expired(session):
            return None
            
        return {
            "session_id": session_id,
            "current_working_image": session.get("current_working_image"),
            "user_id": session.get("user_id"),
            "last_updated": datetime.fromtimestamp(session.get("last_updated", 0)),
            "created_at": datetime.fromtimestamp(session.get("created_at", 0))
        }

# Global session manager instance
session_manager = SessionManager() 