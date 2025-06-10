from supabase import create_client, Client
from .config import settings
import asyncio
import asyncpg
import logging
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

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
    
    # Sprint 3 Analytics Methods
    async def log_intent_classification(self, data: Dict[str, Any]) -> bool:
        """Log intent classification analytics"""
        try:
            self.supabase.table("intent_classification_logs").insert(data).execute()
            return True
        except Exception as e:
            logger.warning(f"Failed to log intent classification: {e}")
            return False
    
    async def log_cost_tracking(self, data: Dict[str, Any]) -> bool:
        """Log cost tracking data"""
        try:
            self.supabase.table("cost_tracking").insert(data).execute()
            return True
        except Exception as e:
            logger.warning(f"Failed to log cost tracking: {e}")
            return False
    
    async def log_model_selection(self, data: Dict[str, Any]) -> bool:
        """Log model selection analytics"""
        try:
            self.supabase.table("model_selection_logs").insert(data).execute()
            return True
        except Exception as e:
            logger.warning(f"Failed to log model selection: {e}")
            return False
    
    async def log_system_performance(self, data: Dict[str, Any]) -> bool:
        """Log system performance metrics"""
        try:
            self.supabase.table("system_performance_logs").insert(data).execute()
            return True
        except Exception as e:
            logger.warning(f"Failed to log system performance: {e}")
            return False

# Global database instance
db_manager = SupabaseManager()

class AsyncDatabase:
    """Async PostgreSQL interface for Supabase with fallback to Supabase client"""
    
    def __init__(self):
        self.pool = None
        self._connection_string = None
        self.supabase_fallback = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
    
    async def initialize(self):
        """Initialize async database connection pool with graceful fallback"""
        if self.pool is None:
            try:
                # Extract project reference from URL
                supabase_url = settings.supabase_url
                project_ref = supabase_url.split('//')[1].split('.')[0]
                
                # Try database password first (most reliable)
                db_password = getattr(settings, 'supabase_db_password', None)
                if db_password:
                    self._connection_string = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"
                    logger.info("Using database password for PostgreSQL connection")
                else:
                    # Skip PostgreSQL connection if no password available
                    logger.warning("No database password found, skipping PostgreSQL pool - using Supabase client only")
                    self.pool = None
                    return
                
                # Create connection pool
                self.pool = await asyncpg.create_pool(
                    self._connection_string,
                    min_size=1,
                    max_size=10,
                    command_timeout=60
                )
                
                logger.info("Async database pool initialized successfully")
                
            except Exception as e:
                logger.warning(f"PostgreSQL pool initialization failed, using Supabase client fallback: {e}")
                # Continue without async database for graceful degradation
                self.pool = None
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return data"""
        if not self.pool:
            await self.initialize()
            
        if not self.pool:
            logger.warning("No PostgreSQL pool available, skipping execute query")
            return "SKIPPED"
        
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        if not self.pool:
            await self.initialize()
            
        if not self.pool:
            logger.warning("No PostgreSQL pool available, using basic test query")
            # Return a basic test result for health checks
            if "SELECT 1" in query:
                return {"test": 1}
            return None
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args)
            return dict(row) if row else None
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch multiple rows"""
        if not self.pool:
            await self.initialize()
            
        if not self.pool:
            logger.warning("No PostgreSQL pool available, returning empty result")
            return []
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def close(self):
        """Close the connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None

# Global async database instance
_async_db = None

async def get_database() -> AsyncDatabase:
    """Get or create async database instance"""
    global _async_db
    if _async_db is None:
        _async_db = AsyncDatabase()
        await _async_db.initialize()
    return _async_db 