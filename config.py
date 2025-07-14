"""Configuration settings for the D&D Comic Book Generator."""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Database
    database_url: str = Field("sqlite:///./comic_generator.db", env="DATABASE_URL")
    neo4j_uri: str = Field("bolt://localhost:7687", env="NEO4J_URI")
    neo4j_user: str = Field("neo4j", env="NEO4J_USER")
    neo4j_password: str = Field("password", env="NEO4J_PASSWORD")
    
    # Redis for task queue
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    
    # Image generation settings
    default_image_size: str = "1024x1024"
    max_image_retries: int = 3
    image_quality: str = "standard"  # standard or hd for DALL-E
    
    # Comic generation settings
    panels_per_page: int = 6
    max_pages_per_mission: int = 30
    comic_width: int = 1200
    comic_height: int = 1600
    
    # Processing settings
    max_workers: int = 4
    request_timeout: int = 60
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "comic_generator.log"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()