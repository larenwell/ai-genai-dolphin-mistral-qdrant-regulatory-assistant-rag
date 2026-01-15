"""
Centralized Configuration Module

Provides centralized configuration management with:
- Pydantic-based validation
- Environment variable loading
- Type safety
- Default values
- Configuration validation
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Centralized application settings with validation.
    
    All settings can be overridden via environment variables.
    """
    
    # ============================================================================
    # Application Settings
    # ============================================================================
    app_name: str = Field(default="RAG Asistente Normativa", env="APP_NAME")
    app_version: str = Field(default="0.2.1", env="APP_VERSION")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    
    # ============================================================================
    # Mistral AI Configuration
    # ============================================================================
    mistral_api_key: str = Field(..., env="MISTRAL_API_KEY")
    mistral_model: str = Field(default="mistral-small-latest", env="MISTRAL_MODEL")
    mistral_temperature: float = Field(default=0.3, env="MISTRAL_TEMPERATURE")
    mistral_max_retries: int = Field(default=3, env="MISTRAL_MAX_RETRIES")
    mistral_timeout: int = Field(default=30, env="MISTRAL_TIMEOUT")
    
    # ============================================================================
    # Qdrant Configuration
    # ============================================================================
    qdrant_url: str = Field(default="http://localhost:6333", env="QDRANT_URL")
    qdrant_collection_name: str = Field(
        default="asistente-normativa-sincro-kb",
        env="QDRANT_COLLECTION_NAME"
    )
    qdrant_timeout: int = Field(default=10, env="QDRANT_TIMEOUT")
    qdrant_vector_size: int = Field(default=768, env="QDRANT_VECTOR_SIZE")
    
    # ============================================================================
    # Ollama Configuration
    # ============================================================================
    ollama_url: str = Field(default="http://localhost:11434", env="OLLAMA_URL")
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        env="OLLAMA_EMBEDDING_MODEL"
    )
    ollama_timeout: int = Field(default=30, env="OLLAMA_TIMEOUT")
    ollama_max_retries: int = Field(default=3, env="OLLAMA_MAX_RETRIES")
    
    # ============================================================================
    # Embedding Configuration
    # ============================================================================
    embedding_dimensions: int = Field(default=768, env="EMBEDDING_DIMENSIONS")
    embedding_batch_size: int = Field(default=50, env="EMBEDDING_BATCH_SIZE")
    embedding_cache_enabled: bool = Field(default=False, env="EMBEDDING_CACHE_ENABLED")
    
    # ============================================================================
    # RAG Configuration
    # ============================================================================
    rag_top_k_default: int = Field(default=5, env="RAG_TOP_K_DEFAULT")
    rag_top_k_factual: int = Field(default=3, env="RAG_TOP_K_FACTUAL")
    rag_top_k_interpretative: int = Field(default=5, env="RAG_TOP_K_INTERPRETATIVE")
    rag_top_k_comparative: int = Field(default=6, env="RAG_TOP_K_COMPARATIVE")
    rag_top_k_procedural: int = Field(default=5, env="RAG_TOP_K_PROCEDURAL")
    rag_min_relevance_score: float = Field(default=0.65, env="RAG_MIN_RELEVANCE_SCORE")
    
    # ============================================================================
    # Translation Configuration
    # ============================================================================
    translation_cache_enabled: bool = Field(
        default=False,
        env="TRANSLATION_CACHE_ENABLED"
    )
    translation_fallback_enabled: bool = Field(
        default=True,
        env="TRANSLATION_FALLBACK_ENABLED"
    )
    
    # ============================================================================
    # Logging Configuration
    # ============================================================================
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_json: bool = Field(default=False, env="LOG_JSON")
    log_dir: Optional[str] = Field(default=None, env="LOG_DIR")
    log_to_file: bool = Field(default=True, env="LOG_TO_FILE")
    log_to_console: bool = Field(default=True, env="LOG_TO_CONSOLE")
    
    # ============================================================================
    # Database Configuration
    # ============================================================================
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # ============================================================================
    # AWS/LocalStack Configuration
    # ============================================================================
    aws_access_key: Optional[str] = Field(default=None, env="APP_AWS_ACCESS_KEY")
    aws_secret_key: Optional[str] = Field(default=None, env="APP_AWS_SECRET_KEY")
    aws_region: Optional[str] = Field(default=None, env="APP_AWS_REGION")
    aws_endpoint: Optional[str] = Field(default=None, env="DEV_AWS_ENDPOINT")
    bucket_name: Optional[str] = Field(default=None, env="BUCKET_NAME")
    
    # ============================================================================
    # Paths Configuration
    # ============================================================================
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "data",
        env="DATA_DIR"
    )
    output_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "output",
        env="OUTPUT_DIR"
    )
    pdf_folder_path: Optional[Path] = Field(default=None, env="PDF_FOLDER_PATH")
    
    # ============================================================================
    # Chainlit Configuration
    # ============================================================================
    chainlit_host: str = Field(default="0.0.0.0", env="CHAINLIT_HOST")
    chainlit_port: int = Field(default=8000, env="CHAINLIT_PORT")
    chainlit_disable_data_layer: bool = Field(
        default=True,
        env="CHAINLIT_DISABLE_DATA_LAYER"
    )
    
    # ============================================================================
    # Validators
    # ============================================================================
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("rag_min_relevance_score")
    @classmethod
    def validate_relevance_score(cls, v):
        """Validate relevance score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Relevance score must be between 0 and 1")
        return v
    
    @field_validator("mistral_temperature")
    @classmethod
    def validate_temperature(cls, v):
        """Validate temperature is between 0 and 2."""
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v
    
    @field_validator("data_dir", "output_dir", mode="before")
    @classmethod
    def validate_paths(cls, v):
        """Convert string paths to Path objects."""
        if isinstance(v, str):
            return Path(v)
        return v
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get or create global settings instance.
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def validate_settings() -> tuple[bool, list[str]]:
    """
    Validate all settings and return validation status.
    
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    try:
        settings = get_settings()
        
        # Validate required paths exist or can be created
        if not settings.data_dir.exists():
            try:
                settings.data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create data directory: {e}")
        
        if not settings.output_dir.exists():
            try:
                settings.output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create output directory: {e}")
        
        # Validate API keys are set
        if not settings.mistral_api_key:
            errors.append("MISTRAL_API_KEY is required but not set")
        
        return len(errors) == 0, errors
        
    except Exception as e:
        errors.append(f"Settings validation failed: {str(e)}")
        return False, errors


def reload_settings() -> Settings:
    """
    Reload settings from environment variables.
    
    Returns:
        New Settings instance
    """
    global _settings
    _settings = None
    return get_settings()

