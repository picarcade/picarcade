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
    
    # API Keys
    openai_api_key: Optional[str] = None
    runway_api_key: Optional[str] = None
    replicate_api_token: Optional[str] = None
    
    # Generation settings
    default_image_size: str = "1024x1024"
    default_video_duration: int = 5
    max_generation_time: int = 300  # 5 minutes
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings() 