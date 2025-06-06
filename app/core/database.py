from supabase import create_client, Client
from .config import settings
import asyncio
from typing import Dict, Any, List, Optional

class SupabaseManager:
    """Supabase database manager for Pictures"""
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key  # Use service role for server-side operations
        )
    
    async def create_tables(self):
        """Create necessary tables if they don't exist"""
        
        # Generation history table
        generation_history_sql = """
        CREATE TABLE IF NOT EXISTS generation_history (
            id SERIAL PRIMARY KEY,
            generation_id TEXT UNIQUE NOT NULL,
            user_id TEXT NOT NULL,
            prompt TEXT NOT NULL,
            intent TEXT,
            model_used TEXT,
            output_url TEXT,
            success TEXT NOT NULL,
            execution_time INTEGER,
            metadata JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_generation_history_user_id ON generation_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_generation_history_created_at ON generation_history(created_at);
        """
        
        try:
            # Note: Supabase Python client doesn't directly support DDL
            # You'll need to run this SQL in your Supabase SQL editor
            print("Please run the following SQL in your Supabase SQL editor:")
            print(generation_history_sql)
            
        except Exception as e:
            print(f"Error creating tables: {e}")
    
    async def insert_generation_history(self, data: Dict[str, Any]) -> bool:
        """Insert generation history record"""
        try:
            result = self.supabase.table("generation_history").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error inserting generation history: {e}")
            return False
    
    async def get_user_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's generation history"""
        try:
            result = self.supabase.table("generation_history")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data
        except Exception as e:
            print(f"Error fetching user history: {e}")
            return []
    
    async def get_generation_by_id(self, generation_id: str) -> Optional[Dict[str, Any]]:
        """Get specific generation by ID"""
        try:
            result = self.supabase.table("generation_history")\
                .select("*")\
                .eq("generation_id", generation_id)\
                .single()\
                .execute()
            
            return result.data
        except Exception as e:
            print(f"Error fetching generation: {e}")
            return None

# Global database instance
db_manager = SupabaseManager() 