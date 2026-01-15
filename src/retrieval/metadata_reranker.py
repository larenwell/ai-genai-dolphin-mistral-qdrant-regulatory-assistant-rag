"""
Metadata Re-ranker - FASE C

Re-ranks search results using metadata bonuses.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.retrieval_config import HYBRID_SEARCH_CONFIG, RERANKING_CONFIG


class MetadataReranker:
    """
    Re-ranks chunks using metadata-based bonuses.
    
    Bonuses applied:
    - legal_weight (jerarquia_normativa)
    - is_primary_source
    - document level (article vs section)
    - code exact match
    """
    
    def __init__(
        self, 
        hybrid_config: dict = None,
        reranking_config: dict = None
    ):
        """
        Initialize metadata re-ranker.
        
        Args:
            hybrid_config: Hybrid search configuration
            reranking_config: Re-ranking configuration
        """
        self.hybrid_config = hybrid_config or HYBRID_SEARCH_CONFIG
        self.reranking_config = reranking_config or RERANKING_CONFIG
        
        # Extract weights
        self.dense_weight = self.hybrid_config.get("dense", {}).get("weight", 0.40)
        self.sparse_weight = self.hybrid_config.get("sparse", {}).get("weight", 0.30)
        
        # Extract bonus weights
        bonuses = self.hybrid_config.get("metadata_bonuses", {})
        self.legal_weight_bonus = bonuses.get("legal_weight_bonus", 0.10)
        self.primary_source_bonus = bonuses.get("primary_source_bonus", 0.10)
        self.level_bonus = bonuses.get("level_bonus", 0.05)
        self.code_match_bonus = bonuses.get("code_match_bonus", 0.05)
        
        # Boost factors
        self.boost_factors = self.reranking_config.get("boost_factors", {})
    
    def rerank(
        self,
        chunks: List[Dict],
        parsed_query: Optional[Dict] = None,
        question_type: str = "interpretative"
    ) -> List[Dict]:
        """
        Re-rank chunks with hybrid fusion + metadata bonuses.
        
        Args:
            chunks: List of chunks (must have 'score' and 'sparse_score')
            parsed_query: Parsed query (for code matching)
            question_type: Type of question
        
        Returns:
            Re-ranked list of chunks (sorted by final_score descending)
        """
        scored_chunks = []
        
        for chunk in chunks:
            # Extract metadata
            if hasattr(chunk, 'payload'):
                metadata = chunk.payload
                dense_score = chunk.score if hasattr(chunk, 'score') else 0.0
            else:
                metadata = chunk.get('payload', chunk)
                dense_score = chunk.get('score', 0.0)
            
            sparse_score = chunk.get('sparse_score', 0.0)
            
            # Calculate metadata bonuses
            bonuses = self._calculate_bonuses(metadata, parsed_query)
            
            # Hybrid fusion
            final_score = (
                self.dense_weight * dense_score +
                self.sparse_weight * sparse_score +
                bonuses["total"]
            )
            
            # Apply boost factors
            final_score = self._apply_boosts(final_score, metadata, parsed_query)
            
            # Normalize final_score if configured
            # (boost factors can make score > 1.0, but we want to display as percentage)
            if self.reranking_config.get("normalize_scores", True):
                max_score = self.reranking_config.get("max_score", 1.0)
                final_score = min(final_score, max_score)
            
            # Store final score
            chunk_copy = chunk if isinstance(chunk, dict) else {
                'payload': chunk.payload,
                'score': chunk.score,
                'id': chunk.id if hasattr(chunk, 'id') else None
            }
            chunk_copy['final_score'] = final_score
            chunk_copy['bonuses'] = bonuses
            
            scored_chunks.append(chunk_copy)
        
        # Sort by final score (descending)
        scored_chunks.sort(key=lambda x: x['final_score'], reverse=True)
        
        # Filter by minimum threshold
        min_threshold = self.reranking_config.get("min_score_threshold", 0.40)
        
        # IMPORTANT: Si después del filtro no quedan chunks, mantener al menos el top 1
        # para evitar que el contexto quede vacío cuando hay información relevante
        filtered_chunks = [c for c in scored_chunks if c['final_score'] >= min_threshold]
        
        if not filtered_chunks and scored_chunks:
            # Si todos los chunks fueron filtrados pero había chunks, mantener el top 1
            # Esto asegura que siempre haya contexto disponible si hay información
            print(f"⚠️ Todos los chunks fueron filtrados (threshold={min_threshold}), manteniendo top 1 (score: {scored_chunks[0]['final_score']:.3f})")
            filtered_chunks = scored_chunks[:1]
        
        scored_chunks = filtered_chunks
        
        # Deduplicate if enabled
        if self.reranking_config.get("deduplicate", True):
            scored_chunks = self._deduplicate(scored_chunks)
        
        return scored_chunks
    
    def _calculate_bonuses(
        self,
        metadata: Dict,
        parsed_query: Optional[Dict]
    ) -> Dict:
        """Calculate all metadata bonuses."""
        bonuses = {
            "legal_weight": 0.0,
            "primary_source": 0.0,
            "level": 0.0,
            "code_match": 0.0,
            "total": 0.0
        }
        
        # Legal weight bonus (normalized)
        legal_weight = metadata.get('legal_weight', 0)
        if legal_weight > 0:
            # Normalize: 1000 → 1.0, 400 → 0.4
            normalized_weight = legal_weight / 1000.0
            bonuses["legal_weight"] = self.legal_weight_bonus * normalized_weight
        
        # Primary source bonus
        if metadata.get('is_primary_source', False):
            bonuses["primary_source"] = self.primary_source_bonus
        
        # Level bonus (prefer main articles)
        level = metadata.get('level', 5)
        if level == 1:
            bonuses["level"] = self.level_bonus
        elif level == 2:
            bonuses["level"] = self.level_bonus * 0.7
        elif level == 3:
            bonuses["level"] = self.level_bonus * 0.4
        
        # Code match bonus
        if parsed_query and parsed_query.get("has_norm_reference"):
            code = metadata.get('code', '')
            code_variations = metadata.get('code_variations', [])
            
            for norm in parsed_query.get('norms', []):
                query_code = norm['code']
                query_full = norm['full']
                
                # Check main code
                if query_code in code or code in query_full or code == query_code:
                    bonuses["code_match"] = self.code_match_bonus
                    break
                
                # Check code variations
                if code_variations:
                    for variation in code_variations:
                        if query_code in variation or variation in query_full or variation == query_code:
                            bonuses["code_match"] = self.code_match_bonus
                            break
                    if bonuses["code_match"] > 0:
                        break
                    
        # Total bonus
        bonuses["total"] = sum([
            bonuses["legal_weight"],
            bonuses["primary_source"],
            bonuses["level"],
            bonuses["code_match"]
        ])
        
        return bonuses
    
    def _apply_boosts(
        self,
        score: float,
        metadata: Dict,
        parsed_query: Optional[Dict]
    ) -> float:
        """Apply multiplicative boost factors."""
        boosted_score = score
        
        # Legal hierarchy boost
        jerarquia = metadata.get('jerarquia_normativa', 9)
        hierarchy_boosts = self.boost_factors.get("legal_hierarchy", {})
        if jerarquia in hierarchy_boosts:
            boost = hierarchy_boosts[jerarquia]
            boosted_score *= boost
        
        # Document level boost
        level = metadata.get('level', 5)
        level_boosts = self.boost_factors.get("document_level", {})
        if level in level_boosts:
            boost = level_boosts[level]
            boosted_score *= boost
        
        # Primary source boost
        if metadata.get('is_primary_source', False):
            boost = self.boost_factors.get("is_primary_source", 1.2)
            boosted_score *= boost
        
        # Code exact match boost (mejorado para manejar variaciones)
        if parsed_query and parsed_query.get("has_norm_reference"):
            code = metadata.get('code', '')
            code_variations = metadata.get('code_variations', [])
            
            for norm in parsed_query.get('norms', []):
                query_code = norm.get('code', '')
                query_full = norm.get('full', '')
                
                # Check exact match
                if code == query_full or code == query_code:
                    boost = self.boost_factors.get("code_exact_match", 1.5)
                    boosted_score *= boost
                    break
                
                # Check if query code/norm is in code or variations
                if query_code in code or code in query_full:
                    boost = self.boost_factors.get("code_exact_match", 1.5)
                    boosted_score *= boost
                    break
                
                # Check code variations
                if code_variations:
                    for variation in code_variations:
                        if query_code in variation or variation in query_full or variation == query_full:
                            boost = self.boost_factors.get("code_exact_match", 1.5)
                            boosted_score *= boost
                            break
                    if boosted_score > score:  # Si se aplicó boost, salir
                        break
        
        return boosted_score
    
    def _deduplicate(self, chunks: List[Dict]) -> List[Dict]:
        """Remove duplicate chunks (same document + chunk_index)."""
        seen = set()
        unique_chunks = []
        
        dedup_key = self.reranking_config.get("dedup_key", "chunk_index")
        
        for chunk in chunks:
            metadata = chunk.get('payload', chunk)
            
            document_id = metadata.get('document_id', '')
            chunk_idx = metadata.get(dedup_key, -1)
            
            key = f"{document_id}_{chunk_idx}"
            
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)
        
        return unique_chunks


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

_reranker_instance = None

def get_metadata_reranker() -> MetadataReranker:
    """Get or create global metadata re-ranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = MetadataReranker()
    return _reranker_instance


def rerank_chunks(
    chunks: List[Dict],
    parsed_query: Optional[Dict] = None,
    question_type: str = "interpretative"
) -> List[Dict]:
    """
    Convenience function to re-rank chunks.
    
    Args:
        chunks: List of chunks with scores
        parsed_query: Parsed query (optional)
        question_type: Type of question
    
    Returns:
        Re-ranked chunks
    """
    reranker = get_metadata_reranker()
    return reranker.rerank(chunks, parsed_query, question_type)