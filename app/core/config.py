from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # App settings
    app_name: str = "Pictures"
    debug: bool = False
    api_v1_str: str = "/api/v1"
    
    # Frontend URL for magic link redirects
    frontend_url: str = "http://localhost:3000"  # Override in production
    
    # Supabase - Updated for new API key system (July 2025)
    supabase_url: str
    supabase_key: str  # Can be legacy anon key or new publishable key (sb_publishable_...)
    supabase_service_role_key: str  # Can be legacy service_role or new secret key (sb_secret_...)
    supabase_jwt_secret: Optional[str] = None  # JWT secret for validating user tokens
    supabase_db_password: Optional[str] = None  # Database password for direct PostgreSQL connection
    
    # New Supabase API keys (optional, for migration)
    supabase_publishable_key: Optional[str] = None  # New publishable key (replaces anon)
    supabase_secret_key: Optional[str] = None  # New secret key (replaces service_role)
    
    # API Keys
    openai_api_key: Optional[str] = None
    runway_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Stripe Payment Processing
    stripe_publishable_key: Optional[str] = None
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    
    # Google Cloud/Vertex AI settings
    google_cloud_project: Optional[str] = None
    google_cloud_location: str = "us-central1"
    google_application_credentials: Optional[str] = None  # Path to service account JSON file
    veo3_skip_bucket_check: bool = False  # Skip GCS bucket existence checks for VEO-3
    
    # Generation settings
    default_image_size: str = "1024x1024"
    default_video_duration: int = 5
    max_generation_time: int = 300  # 5 minutes
    
    # Session settings
    session_expiry_minutes: int = 30
    
    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60
    
    # Configuration for cache
    cache_enabled: bool = True
    cache_ttl: int = 3600  # 1 hour
    
    # Circuit breaker
    circuit_breaker_enabled: bool = True
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 60
    
    # Redis connection
    redis_url: Optional[str] = None
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    
    # Health check
    health_check_enabled: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

# Global settings instance
settings = Settings() 