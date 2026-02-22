"""
Centralized Exception Handling Module

Provides custom exceptions and error handling utilities for the RAG system.
"""

from typing import Optional, Dict, Any
from .logger import get_logger

logger = get_logger(__name__)


class RAGSystemError(Exception):
    """Base exception for RAG system errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize RAG system error.
        
        Args:
            message: Error message
            error_code: Optional error code for categorization
            details: Optional additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        logger.error(f"RAGSystemError [{error_code}]: {message}", extra={"details": details})


class EmbeddingError(RAGSystemError):
    """Exception raised for embedding-related errors."""
    pass


class QdrantError(RAGSystemError):
    """Exception raised for Qdrant-related errors."""
    pass


class LLMError(RAGSystemError):
    """Exception raised for LLM-related errors."""
    pass


class TranslationError(RAGSystemError):
    """Exception raised for translation-related errors."""
    pass


class ExtractionError(RAGSystemError):
    """Exception raised for document extraction errors."""
    pass


class ConfigurationError(RAGSystemError):
    """Exception raised for configuration errors."""
    pass


class ValidationError(RAGSystemError):
    """Exception raised for validation errors."""
    pass


