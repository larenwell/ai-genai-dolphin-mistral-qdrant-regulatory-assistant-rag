"""
RAG Evaluation Package

This package contains tools and utilities for evaluating RAG (Retrieval-Augmented Generation)
systems using various metrics and evaluation frameworks.
"""

from .evaluation_ragas import RAGEvaluator

__version__ = "1.0.0"
__author__ = "RAG System Team"

__all__ = [
    "RAGEvaluator",
] 