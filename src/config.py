"""
Configuration module for GoHighLevel LangGraph Agent
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # App Config
    app_env: str = Field(default="development", env="APP_ENV")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    port: int = Field(default=8000, env="PORT")
    
    # OpenAI
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    
    # GoHighLevel
    ghl_api_token: str = Field(..., env="GHL_API_TOKEN")
    ghl_location_id: str = Field(..., env="GHL_LOCATION_ID")
    ghl_calendar_id: str = Field(..., env="GHL_CALENDAR_ID")
    ghl_assigned_user_id: str = Field(..., env="GHL_ASSIGNED_USER_ID")
    ghl_api_base_url: str = Field(
        default="https://services.leadconnectorhq.com",
        env="GHL_API_BASE_URL"
    )
    
    # Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_ANON_KEY")
    
    # LangSmith (optional)
    langchain_tracing_v2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(
        default="ghl-langgraph-migration",
        env="LANGCHAIN_PROJECT"
    )
    
    # Custom Field IDs
    lead_score_field_id: str = Field(
        default="wAPjuqxtfgKLCJqahjo1",
        env="LEAD_SCORE_FIELD_ID"
    )
    last_intent_field_id: str = Field(
        default="Q1n5kaciimUU6JN5PBD6",
        env="LAST_INTENT_FIELD_ID"
    )
    business_type_field_id: str = Field(
        default="HtoheVc48qvAfvRUKhfG",
        env="BUSINESS_TYPE_FIELD_ID"
    )
    urgency_level_field_id: str = Field(
        default="dXasgCZFgqd62psjw7nd",
        env="URGENCY_LEVEL_FIELD_ID"
    )
    goal_field_id: str = Field(
        default="r7jFiJBYHiEllsGn7jZC",
        env="GOAL_FIELD_ID"
    )
    budget_field_id: str = Field(
        default="4Qe8P25JRLW0IcZc5iOs",
        env="BUDGET_FIELD_ID"
    )
    verified_name_field_id: str = Field(
        default="TjB0I5iNfVwx3zyxZ9sW",
        env="VERIFIED_NAME_FIELD_ID"
    )
    preferred_day_field_id: str = Field(
        default="D1aD9KUDNm5Lp4Kz8yAD",
        env="PREFERRED_DAY_FIELD_ID"
    )
    preferred_time_field_id: str = Field(
        default="M70lUtadchW4f2pJGDJ5",
        env="PREFERRED_TIME_FIELD_ID"
    )
    
    # Agent Configuration
    cold_lead_threshold: int = Field(default=4, env="COLD_LEAD_THRESHOLD")
    warm_lead_threshold: int = Field(default=7, env="WARM_LEAD_THRESHOLD")
    
    # Business Hours (in EST/EDT)
    business_hours_start: int = Field(default=9, env="BUSINESS_HOURS_START")
    business_hours_end: int = Field(default=18, env="BUSINESS_HOURS_END")
    
    # Retry Configuration
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_delay: int = Field(default=60, env="RETRY_DELAY")  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Agent Names
AGENT_NAMES = {
    "maria": "Maria",
    "carlos": "Carlos",
    "sofia": "Sofia"
}

# Lead Intents
LEAD_INTENTS = {
    "LISTO_COMPRAR": "Ready to buy",
    "BUSCANDO_INFO": "Looking for information",
    "COMPARANDO_OPCIONES": "Comparing options",
    "SOLO_PREGUNTANDO": "Just asking",
    "NO_INTERESADO": "Not interested"
}

# Message Templates
ACKNOWLEDGMENT_MESSAGE = "✓"

# API Headers
def get_ghl_headers() -> dict:
    """Get GoHighLevel API headers"""
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.ghl_api_token}",
        "Content-Type": "application/json",
        "Version": "2021-07-28"
    }