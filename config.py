"""Configuration settings for the D&D Comic Book Generator."""

import os
from typing import Optional


class Settings:
    """Application settings."""
    
    def __init__(self):
        # API Keys
        self.openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
        
        # Database
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./comic_generator.db")
        self.neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
        
        # Redis for task queue
        self.redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Image generation settings
        self.default_image_size: str = "1024x1024"
        self.max_image_retries: int = 3
        self.image_quality: str = "standard"  # standard or hd for DALL-E
        
        # Comic generation settings
        self.panels_per_page: int = 6
        self.max_pages_per_mission: int = 30
        self.comic_width: int = 1200
        self.comic_height: int = 1600
        
        # Processing settings
        self.max_workers: int = 4
        self.request_timeout: int = 60
        
        # Logging
        self.log_level: str = "INFO"
        self.log_file: str = "comic_generator.log"


# Global settings instance
settings = Settings()