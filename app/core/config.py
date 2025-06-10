from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App settings
    app_name: str = "Pictures"
    debug: bool = False
    api_v1_str: str = "/api/v1"
    
    # Supabase
    supabase_url: str
    supabase_key: str
    supabase_service_role_key: str
    supabase_db_password: Optional[str] = None  # Database password for direct PostgreSQL connection
    
    # API Keys
    openai_api_key: Optional[str] = None
    runway_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    
    # Generation settings
    default_image_size: str = "1024x1024"
    default_video_duration: int = 5
    max_generation_time: int = 300  # 5 minutes
    
    # Sprint 3: Infrastructure settings
    redis_url: Optional[str] = None
    rate_limit_requests_per_minute: int = 100
    rate_limit_requests_per_hour: int = 1000
    cost_limit_per_hour: float = 50.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    intent_cache_ttl: int = 3600
    max_concurrent_classifications: int = 10
    classification_timeout: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings() 