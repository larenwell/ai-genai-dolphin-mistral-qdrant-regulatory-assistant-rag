"""
Hybrid Search Engine - FASE C

Orchestrates the complete hybrid retrieval pipeline.
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from config.retrieval_config import get_retrieval_config, get_question_type_settings
from .query_parser import QueryParser
from .filter_builder import FilterBuilder
from .sparse_encoder import SparseEncoder
from .metadata_reranker import MetadataReranker
from .context_composer import ContextComposer


class HybridSearchEngine:
    """
    Complete hybrid search engine.
    
    Pipeline:
    1. Parse query → extract entities
    2. Build filters → intelligent pre-filtering
    3. Dense search → semantic similarity (Qdrant)
    4. Sparse search → keyword matching (BM25)
    5. Metadata re-ranking → legal_weight, level, etc.
    6. Context composition → formatted for LLM
    """
    
    def __init__(self, embedding_controller):
        """
        Initialize hybrid search engine.
        
        Args:
            embedding_controller: EmbeddingControllerQdrant instance
        """
        self.embedding_controller = embedding_controller
        self.config = get_retrieval_config()
        
        # Initialize components
        self.query_parser = QueryParser(self.config["query_parser"])
        self.filter_builder = FilterBuilder(self.config["filter_builder"])
        self.sparse_encoder = SparseEncoder(self.config["hybrid_search"])
        self.metadata_reranker = MetadataReranker(
            self.config["hybrid_search"],
            self.config["reranking"]
        )
        self.context_composer = ContextComposer(self.config["context_composer"])
        
        print("🔍 HybridSearchEngine initialized")
    
    def search(
        self,
        query: str,
        question_type: str = "interpretative",
        top_k: Optional[int] = None
    ) -> Dict:
        """
        Execute complete hybrid search pipeline.
        
        Args:
            query: User query (in English, already translated)
            question_type: Type of question
            top_k: Number of final chunks to return (optional)
        
        Returns:
            Dict with:
            - parsed_query: Parsed entities
            - chunks: Final ranked chunks
            - context: Formatted context string
            - stats: Pipeline statistics
        """
        print(f"\n{'='*70}")
        print(f"🔍 HYBRID SEARCH PIPELINE START")
        print(f"{'='*70}")
        
        stats = {
            "question_type": question_type,
            "dense_retrieved": 0,
            "sparse_scored": 0,
            "after_reranking": 0,
            "final_chunks": 0
        }
        
        # Get question-specific settings
        qt_settings = get_question_type_settings(question_type)
        final_top_k = top_k or qt_settings.get("top_k", 5)
        
        # =====================================================================
        # STEP 1: Parse query
        # =====================================================================
        print(f"\n1️⃣ Parsing query...")
        parsed_query = self.query_parser.parse(query)
        
        print(f"   📝 Detected entities:")
        print(f"      Norms: {parsed_query['norms']}")
        print(f"      Articles: {parsed_query['articles']}")
        print(f"      Keywords: {parsed_query['keywords'][:5]}...")
        
        # =====================================================================
        # STEP 2: Build filters
        # =====================================================================
        print(f"\n2️⃣ Building filters...")
        filters = self.filter_builder.build_filters(parsed_query)
        
        if filters:
            print(f"   ✅ Filters created (intelligent pre-filtering)")
            # Debug: show filter structure
            if hasattr(filters, 'model_dump'):
                filter_dict = filters.model_dump()
                print(f"   🔍 Filter structure: {filter_dict}")
        else:
            print(f"   ℹ️  No filters needed (open search)")
        
        # =====================================================================
        # STEP 3: Dense search (semantic)
        # =====================================================================
        print(f"\n3️⃣ Dense search (semantic)...")
        
        # Generate embedding
        query_embedding = self.embedding_controller.generate_embeddings(query)
        print(f"   ✅ Embedding generated (dim: {len(query_embedding)})")
        
        # Search with filters (retrieve more initially for re-ranking)
        initial_top_k = self.config["hybrid_search"]["dense"]["initial_top_k"]
        print(f"   🔍 Searching with top_k={initial_top_k}, filters={'Yes' if filters else 'No'}")
        
        dense_chunks = self.embedding_controller.load_and_query_qdrant(
            query_embedding=query_embedding,
            top_k=initial_top_k,
            query_filter=filters
        )
        
        stats["dense_retrieved"] = len(dense_chunks)
        print(f"   📊 Retrieved {stats['dense_retrieved']} chunks")
        
        # If no chunks found with filters, try without filters as fallback
        if not dense_chunks and filters:
            print(f"   ⚠️  No chunks found with filters, trying without filters...")
            dense_chunks = self.embedding_controller.load_and_query_qdrant(
                query_embedding=query_embedding,
                top_k=initial_top_k,
                query_filter=None  # Try without filters
            )
            stats["dense_retrieved"] = len(dense_chunks)
            print(f"   📊 Retrieved {stats['dense_retrieved']} chunks (without filters)")
        
        # If still no chunks, return empty
        if not dense_chunks:
            print(f"   ⚠️  No chunks found even without filters!")
            return {
                "parsed_query": parsed_query,
                "chunks": [],
                "context": "",
                "stats": stats
            }
        
        # =====================================================================
        # STEP 4: Sparse search (BM25)
        # =====================================================================
        print(f"\n4️⃣ Sparse search (BM25)...")
        
        sparse_chunks = self.sparse_encoder.score_chunks(
            query_keywords=parsed_query["keywords"],
            chunks=dense_chunks
        )
        
        stats["sparse_scored"] = len(sparse_chunks)
        print(f"   📊 Scored {stats['sparse_scored']} chunks with BM25")
        
        # =====================================================================
        # STEP 5: Metadata re-ranking
        # =====================================================================
        print(f"\n5️⃣ Metadata re-ranking...")
        
        reranked_chunks = self.metadata_reranker.rerank(
            chunks=sparse_chunks,
            parsed_query=parsed_query,
            question_type=question_type
        )
        
        stats["after_reranking"] = len(reranked_chunks)
        print(f"   📊 {stats['after_reranking']} chunks after re-ranking")
        
        # Show top 3 scores
        if reranked_chunks:
            print(f"   🎯 Top 3 scores:")
            for i, chunk in enumerate(reranked_chunks[:3], 1):
                score = chunk.get('final_score', 0.0)
                metadata = chunk.get('payload', chunk)
                code = metadata.get('code', 'Unknown')
                print(f"      {i}. {code}: {score:.3f}")
        
        # =====================================================================
        # STEP 6: Limit to top_k
        # =====================================================================
        final_chunks = reranked_chunks[:final_top_k]
        stats["final_chunks"] = len(final_chunks)
        
        print(f"\n6️⃣ Limiting to top-{final_top_k} chunks")
        print(f"   📊 Final: {stats['final_chunks']} chunks")
        
        # =====================================================================
        # STEP 7: Compose context
        # =====================================================================
        print(f"\n7️⃣ Composing context...")
        
        formatted_context = self.context_composer.compose(final_chunks)
        
        print(f"   ✅ Context composed ({len(formatted_context)} chars)")
        
        # =====================================================================
        # IMPORTANT: Ensure we return chunks used for context composition
        # =====================================================================
        # Si final_chunks está vacío pero el contexto se compuso correctamente,
        # significa que el contexto_composer puede haber usado chunks internamente.
        # En este caso, retornar al menos los top chunks de reranked_chunks
        # para que las fuentes se puedan mostrar.
        chunks_for_display = final_chunks
        
        print(f"\n🔍 DEBUG CHUNKS FOR DISPLAY:")
        print(f"   final_chunks length: {len(final_chunks) if final_chunks else 0}")
        print(f"   reranked_chunks length: {len(reranked_chunks) if reranked_chunks else 0}")
        print(f"   formatted_context length: {len(formatted_context) if formatted_context else 0}")
        
        if not final_chunks and formatted_context and len(formatted_context) > 0:
            # Si no hay final_chunks pero hay contexto, usar los top chunks de reranked_chunks
            print(f"⚠️ Final chunks vacío pero hay contexto, usando top {final_top_k} de reranked_chunks para display")
            if reranked_chunks:
                chunks_for_display = reranked_chunks[:final_top_k]
                stats["final_chunks"] = len(chunks_for_display)
                print(f"   ✅ Usando {len(chunks_for_display)} chunks de reranked_chunks")
            else:
                print(f"   ⚠️ reranked_chunks también está vacío - no hay chunks para mostrar")
        else:
            print(f"   ✅ Usando {len(chunks_for_display) if chunks_for_display else 0} final_chunks")
        
        # =====================================================================
        # DONE
        # =====================================================================
        print(f"\n{'='*70}")
        print(f"✅ HYBRID SEARCH PIPELINE COMPLETE")
        print(f"{'='*70}")
        
        return {
            "parsed_query": parsed_query,
            "chunks": chunks_for_display,  # Usar chunks_for_display en lugar de final_chunks
            "context": formatted_context,
            "stats": stats
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_hybrid_search_engine(embedding_controller) -> HybridSearchEngine:
    """
    Create a hybrid search engine instance.
    
    Args:
        embedding_controller: EmbeddingControllerQdrant instance
    
    Returns:
        HybridSearchEngine instance
    """
    return HybridSearchEngine(embedding_controller)