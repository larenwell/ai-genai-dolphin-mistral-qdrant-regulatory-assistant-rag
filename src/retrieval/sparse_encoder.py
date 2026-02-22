"""
Sparse Encoder - FASE C

BM25-style sparse encoding over keywords_manual field.
"""

import sys
from pathlib import Path
from typing import List, Dict
import math
from collections import Counter

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.retrieval_config import HYBRID_SEARCH_CONFIG


class SparseEncoder:
    """
    BM25-style sparse encoder for keyword matching.
    
    Computes relevance scores based on:
    - Term frequency in chunk keywords
    - Inverse document frequency (approximated)
    - Exact match boosting
    """
    
    def __init__(self, config: dict = None):
        """
        Initialize sparse encoder.
        
        Args:
            config: Sparse search configuration
        """
        sparse_config = config or HYBRID_SEARCH_CONFIG.get("sparse", {})
        
        self.k1 = sparse_config.get("k1", 1.5)
        self.b = sparse_config.get("b", 0.75)
        self.boost_exact_match = sparse_config.get("boost_exact_match", 2.0)
        self.use_keywords_manual = sparse_config.get("use_keywords_manual", True)
        self.use_text = sparse_config.get("use_text", True)
    
    def compute_bm25_score(
        self, 
        query_keywords: List[str],
        chunk_keywords_manual: List[str],
        chunk_text: str = None
    ) -> float:
        """
        Compute BM25-style score for a chunk.
        
        Args:
            query_keywords: Keywords from query
            chunk_keywords_manual: keywords_manual field from chunk
            chunk_text: Optional text field from chunk
        
        Returns:
            BM25 score (0.0 - 1.0 normalized)
        """
        if not query_keywords:
            return 0.0
        
        # Prepare chunk terms
        chunk_terms = []
        
        if self.use_keywords_manual and chunk_keywords_manual:
            # Normalize keywords_manual (lowercase, split)
            for kw in chunk_keywords_manual:
                if isinstance(kw, str):
                    chunk_terms.extend(kw.lower().split())
        
        if self.use_text and chunk_text:
            # Extract terms from text (simple tokenization)
            text_terms = self._tokenize(chunk_text)
            chunk_terms.extend(text_terms)
        
        if not chunk_terms:
            return 0.0
        
        # Count term frequencies
        chunk_term_freq = Counter(chunk_terms)
        
        # Normalize query keywords
        query_terms = [kw.lower() for kw in query_keywords]
        
        # Calculate BM25 components
        score = 0.0
        matches = 0
        exact_matches = 0
        
        avg_chunk_length = 50  # Approximate average keywords per chunk
        chunk_length = len(chunk_terms)
        
        for term in query_terms:
            if term in chunk_term_freq:
                matches += 1
                
                # Term frequency
                tf = chunk_term_freq[term]
                
                # IDF (simplified - assume medium rarity)
                idf = 2.0  # Simplified IDF (not corpus-dependent)
                
                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (chunk_length / avg_chunk_length)
                )
                
                term_score = idf * (numerator / denominator)
                score += term_score
                
                # Check for exact match (term appears as-is in keywords_manual)
                if self.use_keywords_manual and chunk_keywords_manual:
                    for kw in chunk_keywords_manual:
                        if isinstance(kw, str) and term in kw.lower():
                            exact_matches += 1
                            break
        
        # Normalize score
        max_possible_score = len(query_terms) * 2.0 * (self.k1 + 1)
        normalized_score = min(score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
        
        # Boost for exact matches
        if exact_matches > 0:
            boost_factor = 1.0 + (exact_matches / len(query_terms)) * (self.boost_exact_match - 1.0)
            normalized_score = min(normalized_score * boost_factor, 1.0)
        
        return normalized_score
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text preserving important patterns.
        
        Args:
            text: Text to tokenize
        
        Returns:
            List of tokens
        """
        import re
        
        # Lowercase
        text = text.lower()
        
        # Preserve norm codes (A.130, DS 005-2012-TR, etc.)
        # Replace special patterns with placeholders first
        preserved_patterns = []
        
        # Pattern 1: RNE codes (A.130, E.060)
        rne_pattern = r'\b[a-z]{1,3}\.\d+\b'
        for match in re.finditer(rne_pattern, text):
            placeholder = f"__RNE_{len(preserved_patterns)}__"
            preserved_patterns.append(match.group(0))
            text = text.replace(match.group(0), placeholder)
        
        # Pattern 2: DS codes (005-2012-TR)
        ds_pattern = r'\b\d+-\d+-[a-z]+\b'
        for match in re.finditer(ds_pattern, text):
            placeholder = f"__DS_{len(preserved_patterns)}__"
            preserved_patterns.append(match.group(0))
            text = text.replace(match.group(0), placeholder)
        
        # Pattern 3: Article numbers (artículo 39)
        article_pattern = r'art[íi]culo\s+(\d+)'
        for match in re.finditer(article_pattern, text):
            preserved_patterns.append(f"articulo_{match.group(1)}")
            text = text.replace(match.group(0), f"__ART_{len(preserved_patterns)-1}__")
        
        # Now tokenize normally
        text = re.sub(r'[^a-z0-9\s_]', ' ', text)
        tokens = text.split()
        
        # Restore preserved patterns
        final_tokens = []
        for token in tokens:
            if token.startswith("__") and token.endswith("__"):
                # This is a placeholder, restore original
                match = re.search(r'\d+', token)
                if match:  # ✅ FIX: Verificar que match no sea None
                    idx = int(match.group())
                    if idx < len(preserved_patterns):  # ✅ FIX: Verificar índice válido
                        final_tokens.append(preserved_patterns[idx])
                    else:
                        # Si el índice no es válido, usar el token original
                        final_tokens.append(token)
                else:
                    # Si no hay match, usar el token original
                    final_tokens.append(token)
            elif len(token) > 1:  # Allow single digits and letters
                final_tokens.append(token)
        
        return final_tokens
    
    def score_chunks(
        self,
        query_keywords: List[str],
        chunks: List[Dict]
    ) -> List[Dict]:
        """
        Score multiple chunks with BM25.
        
        Args:
            query_keywords: Keywords from query
            chunks: List of chunks (each with metadata)
        
        Returns:
            List of chunks with added 'sparse_score' field
        """
        scored_chunks = []
        
        for chunk in chunks:
            # Extract metadata
            if hasattr(chunk, 'payload'):
                # Qdrant search result
                metadata = chunk.payload
            else:
                # Already a dict
                metadata = chunk
            
            # Get fields for BM25
            keywords_manual = metadata.get('keywords_manual', [])
            text = metadata.get('text', '')
            
            # Compute score
            sparse_score = self.compute_bm25_score(
                query_keywords=query_keywords,
                chunk_keywords_manual=keywords_manual,
                chunk_text=text
            )
            
            # Add score to chunk
            chunk_copy = chunk if isinstance(chunk, dict) else {
                'payload': chunk.payload,
                'score': chunk.score,
                'id': chunk.id
            }
            chunk_copy['sparse_score'] = sparse_score
            
            scored_chunks.append(chunk_copy)
        
        return scored_chunks


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_encoder_instance = None

def get_sparse_encoder() -> SparseEncoder:
    """Get or create global sparse encoder instance."""
    global _encoder_instance
    if _encoder_instance is None:
        _encoder_instance = SparseEncoder()
    return _encoder_instance


def compute_sparse_scores(
    query_keywords: List[str],
    chunks: List[Dict]
) -> List[Dict]:
    """
    Convenience function to compute sparse scores.
    
    Args:
        query_keywords: Keywords from query
        chunks: List of chunks
    
    Returns:
        Chunks with sparse_score added
    """
    encoder = get_sparse_encoder()
    return encoder.score_chunks(query_keywords, chunks)


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    encoder = SparseEncoder()
    
    # Test case
    query_keywords = ["capacitacion", "empleador", "seguridad"]
    
    chunk_keywords_manual = ["capacitacion_sst", "empleador", "trabajador"]
    chunk_text = "El empleador debe garantizar capacitación en seguridad..."
    
    score = encoder.compute_bm25_score(
        query_keywords=query_keywords,
        chunk_keywords_manual=chunk_keywords_manual,
        chunk_text=chunk_text
    )
    
    print("="*70)
    print("SPARSE ENCODER - TEST")
    print("="*70)
    print(f"\nQuery keywords: {query_keywords}")
    print(f"Chunk keywords: {chunk_keywords_manual}")
    print(f"BM25 score: {score:.3f}")