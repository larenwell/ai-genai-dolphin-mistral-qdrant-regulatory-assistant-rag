#!/usr/bin/env python3
"""
Script de prueba para validar consultas antes de usarlas en la interfaz.

Uso:
    python test_query.py "tu pregunta aquí"
    
Ejemplo:
    python test_query.py "Dame un resumen de lo que menciona el NFPA 37"
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.retrieval.query_parser import QueryParser
from src.retrieval.filter_builder import FilterBuilder
from src.retrieval.sparse_encoder import SparseEncoder
from src.retrieval.metadata_reranker import MetadataReranker
from src.retrieval.context_composer import ContextComposer
from src.retrieval.hybrid_search import HybridSearchEngine
from src.embeddings.embedding_qdrant import EmbeddingControllerQdrant
from config.retrieval_config import get_retrieval_config

def test_query_parser(query: str):
    """Test query parser."""
    print("\n" + "="*70)
    print("1️⃣ TESTING QUERY PARSER")
    print("="*70)
    try:
        parser = QueryParser()
        parsed = parser.parse(query)
        print(f"✅ Query parser OK")
        print(f"   Norms: {parsed.get('norms', [])}")
        print(f"   Articles: {parsed.get('articles', [])}")
        print(f"   Keywords: {parsed.get('keywords', [])[:10]}")
        return parsed
    except Exception as e:
        print(f"❌ Error en query parser: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_filter_builder(parsed_query):
    """Test filter builder."""
    print("\n" + "="*70)
    print("2️⃣ TESTING FILTER BUILDER")
    print("="*70)
    try:
        builder = FilterBuilder()
        filters = builder.build_filters(parsed_query)
        if filters:
            print(f"✅ Filter builder OK")
            print(f"   Filters created")
        else:
            print(f"✅ Filter builder OK (no filters needed)")
        return filters
    except Exception as e:
        print(f"❌ Error en filter builder: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_sparse_encoder(query: str):
    """Test sparse encoder."""
    print("\n" + "="*70)
    print("3️⃣ TESTING SPARSE ENCODER")
    print("="*70)
    try:
        encoder = SparseEncoder()
        
        # Test tokenization
        tokens = encoder._tokenize(query)
        print(f"✅ Tokenization OK: {len(tokens)} tokens")
        
        # Test BM25 score with dummy data
        keywords = query.lower().split()[:5]
        score = encoder.compute_bm25_score(
            query_keywords=keywords,
            chunk_keywords_manual=keywords,
            chunk_text=query
        )
        print(f"✅ BM25 score OK: {score:.4f}")
        return True
    except Exception as e:
        print(f"❌ Error en sparse encoder: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_full_pipeline(query: str):
    """Test full hybrid search pipeline."""
    print("\n" + "="*70)
    print("4️⃣ TESTING FULL HYBRID SEARCH PIPELINE")
    print("="*70)
    try:
        # Initialize embedding controller
        print("   Inicializando EmbeddingController...")
        embedding_controller = EmbeddingControllerQdrant()
        print("   ✅ EmbeddingController OK")
        
        # Initialize hybrid search engine
        print("   Inicializando HybridSearchEngine...")
        hybrid_engine = HybridSearchEngine(embedding_controller)
        print("   ✅ HybridSearchEngine OK")
        
        # Test search (with small top_k for testing)
        print(f"   Ejecutando búsqueda para: '{query[:50]}...'")
        result = hybrid_engine.search(
            query=query,
            question_type="interpretative",
            top_k=3
        )
        
        print(f"   ✅ Búsqueda completada")
        print(f"   Chunks encontrados: {len(result.get('chunks', []))}")
        print(f"   Context length: {len(result.get('context', ''))} chars")
        
        return result
    except Exception as e:
        print(f"❌ Error en pipeline completo: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Uso: python test_query.py 'tu pregunta aquí' [--full]")
        print("\nEjemplo:")
        print("  python test_query.py 'Dame un resumen de lo que menciona el NFPA 37'")
        print("  python test_query.py 'Dame un resumen de lo que menciona el NFPA 37' --full")
        sys.exit(1)
    
    # Extraer query (filtrar --full)
    query = sys.argv[1] if sys.argv[1] != "--full" else sys.argv[2] if len(sys.argv) > 2 else None
    if not query or query == "--full":
        print("❌ Error: Debes proporcionar una pregunta")
        sys.exit(1)
    
    print("="*70)
    print("🧪 TEST DE CONSULTA")
    print("="*70)
    print(f"Query: {query}")
    
    # Test 1: Query Parser
    parsed_query = test_query_parser(query)
    if not parsed_query:
        print("\n❌ FALLO EN QUERY PARSER - No se puede continuar")
        sys.exit(1)
    
    # Test 2: Filter Builder
    filters = test_filter_builder(parsed_query)
    if filters is None:
        print("\n❌ FALLO EN FILTER BUILDER - No se puede continuar")
        sys.exit(1)
    
    # Test 3: Sparse Encoder
    sparse_ok = test_sparse_encoder(query)
    if not sparse_ok:
        print("\n❌ FALLO EN SPARSE ENCODER - No se puede continuar")
        sys.exit(1)
    
    # Test 4: Full Pipeline (opcional, requiere Qdrant)
    print("\n" + "="*70)
    print("4️⃣ TESTING FULL PIPELINE (opcional)")
    print("="*70)
    print("   Para probar el pipeline completo, ejecuta:")
    print("   python test_query.py --full 'tu pregunta'")
    print("\n" + "="*70)
    print("✅ TESTS BÁSICOS COMPLETADOS")
    print("="*70)
    print("\n💡 Los componentes básicos funcionan correctamente")
    print("💡 La consulta está lista para usar en la interfaz")
    
    # Si se pasa --full, probar pipeline completo
    if "--full" in sys.argv:
        result = test_full_pipeline(query)
        if result:
            print("\n" + "="*70)
            print("✅ TODOS LOS TESTS PASARON (incluyendo pipeline completo)")
            print("="*70)
        else:
            print("\n⚠️  El pipeline completo falló, pero los componentes básicos funcionan")

if __name__ == "__main__":
    main()

