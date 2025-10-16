"""
API Configuration System
Manages API keys and settings for external services
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class APIConfig:
    """
    Centralized API configuration.
    Reads from environment variables with fallbacks.
    """
    
    # ==================================================================
    # SEARCH APIs
    # ==================================================================
    
    # SerpAPI (Google Shopping/Products search)
    # Free tier: 100 searches/month
    # Sign up: https://serpapi.com/
    SERPAPI_KEY: Optional[str] = os.getenv("SERPAPI_KEY")
    SERPAPI_ENABLED: bool = SERPAPI_KEY is not None
    
    # ==================================================================
    # SCIENTIFIC LITERATURE APIs
    # ==================================================================
    
    # PubMed/NCBI E-utilities (completely free!)
    # Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/
    PUBMED_EMAIL: str = os.getenv("PUBMED_EMAIL", "your-email@example.com")
    PUBMED_API_KEY: Optional[str] = os.getenv("PUBMED_API_KEY")  # Optional but recommended
    PUBMED_ENABLED: bool = True  # Always available
    
    # Europe PMC (free alternative to PubMed)
    # Documentation: https://europepmc.org/RestfulWebService
    EUROPEPMC_ENABLED: bool = True
    
    # ==================================================================
    # PRODUCT DATABASE APIs
    # ==================================================================
    
    # Sigma-Aldrich Product Search (if available)
    SIGMA_API_KEY: Optional[str] = os.getenv("SIGMA_API_KEY")
    SIGMA_ENABLED: bool = SIGMA_API_KEY is not None
    
    # ==================================================================
    # CURRENCY & MARKET DATA
    # ==================================================================
    
    # ExchangeRate-API (free tier: 1500 requests/month)
    # Sign up: https://www.exchangerate-api.com/
    EXCHANGE_RATE_API_KEY: Optional[str] = os.getenv("EXCHANGE_RATE_API_KEY")
    EXCHANGE_RATE_ENABLED: bool = EXCHANGE_RATE_API_KEY is not None
    
    # ==================================================================
    # LLM APIs (for enhanced explainability)
    # ==================================================================
    
    # OpenAI (for generating rationales)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_ENABLED: bool = OPENAI_API_KEY is not None
    
    # Anthropic Claude (alternative)
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_ENABLED: bool = ANTHROPIC_API_KEY is not None
    
    # Groq API (FREE alternative)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    GROQ_ENABLED: bool = GROQ_API_KEY is not None
    # ==================================================================
    # RATE LIMITING & CACHING
    # ==================================================================
    
    # Enable request caching to reduce API calls
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_DIR: Path = Path("./cache")
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))
    
    # Rate limiting
    MAX_REQUESTS_PER_MINUTE: int = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "10"))
    
    # ==================================================================
    # TIMEOUTS & RETRIES
    # ==================================================================
    
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY_SECONDS: float = float(os.getenv("RETRY_DELAY_SECONDS", "1.0"))
    
    # ==================================================================
    # FEATURE FLAGS
    # ==================================================================
    
    # Enable/disable specific features
    USE_WEB_SEARCH: bool = os.getenv("USE_WEB_SEARCH", "true").lower() == "true"
    USE_LITERATURE_API: bool = os.getenv("USE_LITERATURE_API", "true").lower() == "true"
    USE_LLM_EXPLANATIONS: bool = os.getenv("USE_LLM_EXPLANATIONS", "false").lower() == "true"
    
    @classmethod
    def summary(cls) -> dict:
        """Return configuration summary"""
        return {
            "search": {
                "serpapi": cls.SERPAPI_ENABLED,
                "web_search_enabled": cls.USE_WEB_SEARCH
            },
            "literature": {
                "pubmed": cls.PUBMED_ENABLED,
                "europepmc": cls.EUROPEPMC_ENABLED,
                "literature_api_enabled": cls.USE_LITERATURE_API
            },
            "llm": {
                "openai": cls.OPENAI_ENABLED,
                "anthropic": cls.ANTHROPIC_ENABLED,
                "llm_explanations_enabled": cls.USE_LLM_EXPLANATIONS
            },
            "cache": {
                "enabled": cls.ENABLE_CACHE,
                "ttl_hours": cls.CACHE_TTL_HOURS
            },
            "rate_limiting": {
                "max_requests_per_minute": cls.MAX_REQUESTS_PER_MINUTE
            }
        }
    
    @classmethod
    def validate(cls) -> list[str]:
        """Validate configuration and return warnings"""
        warnings = []
        
        if not cls.SERPAPI_ENABLED and cls.USE_WEB_SEARCH:
            warnings.append("⚠️  Web search enabled but SerpAPI key not configured - will use mock data")
        
        if cls.PUBMED_EMAIL == "your-email@example.com":
            warnings.append("⚠️  PubMed email not configured - please set PUBMED_EMAIL in .env")
        
        if cls.USE_LLM_EXPLANATIONS and not (cls.OPENAI_ENABLED or cls.ANTHROPIC_ENABLED):
            warnings.append("⚠️  LLM explanations enabled but no LLM API key configured")
        
        return warnings


# Print configuration on import (for debugging)
if __name__ != "__main__":
    config_summary = APIConfig.summary()
    warnings = APIConfig.validate()
    
    # Only print in development mode
    if os.getenv("DEBUG", "false").lower() == "true":
        print("="*60)
        print("🔧 API Configuration Loaded")
        print("="*60)
        print(f"Search APIs: {config_summary['search']}")
        print(f"Literature APIs: {config_summary['literature']}")
        print(f"LLM APIs: {config_summary['llm']}")
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"  {w}")
        print("="*60)