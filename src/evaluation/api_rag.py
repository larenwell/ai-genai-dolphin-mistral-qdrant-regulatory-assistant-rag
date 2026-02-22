import os, sys
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from llm.mistral_llm import MistralLLM
from embeddings.embedding_qdrant import EmbeddingControllerQdrant

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

load_dotenv(project_root / '.env')

app = FastAPI()

# Initialize LLM with Spanish language for user interface
llm = MistralLLM(api_key=os.getenv("MISTRAL_API_KEY"))

# Get collection name from environment variable or use default
collection_name = os.getenv("QDRANT_COLLECTION_NAME", "asistente-normativa-sincro-kb")
print(f"🔧 Usando colección: {collection_name}")
embedding_admin = EmbeddingControllerQdrant(qdrant_collection=collection_name)

@app.get("/health")
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "collection": collection_name,
        "phase": "FASE A - Evaluación KB Mixta"
    }

@app.post("/rag")
def rag(data: dict):
    """
    RAG endpoint - FASE A: Evaluación con KB Mixta
    
    CAMBIO PRINCIPAL: NO traduce pregunta español→inglés
    Busca directamente en idioma original de la pregunta
    
    Workflow FASE A:
    1. Recibe pregunta en español (usuario)
    2. Busca directamente en español (sin traducir)
    3. Recupera contexto mixto (español + inglés según relevancia)
    4. LLM procesa contexto mixto y responde en español
    
    ADVERTENCIA: Retrieval subóptimo esperado por:
    - KB mixta (2 docs ES + 2 docs EN)
    - Embeddings monolingües (nomic-embed-text)
    - Preguntas en español sobre docs inglés = baja similitud
    """
    question = data.get("question")
    if not question:
        return {"error": "Question is required"}
    
    try:
        # FASE A: NO traducir - buscar en idioma original
        search_query = question
        print(f"🔍 FASE A: Búsqueda directa sin traducción")
        print(f"   Pregunta: '{question[:80]}...'")
        
        # Buscar en KB mixta usando pregunta original
        embed_question = embedding_admin.generate_embeddings(search_query)
        context_response = embedding_admin.load_and_query_qdrant(embed_question, top_k=5)
        
        # Extraer textos de contexto
        context_texts = [match.payload['text'] for match in context_response]
        context = "\n".join(context_texts)
        
        # Extraer metadatos de fuentes (CRÍTICO para detectar idioma)
        context_sources = []
        for match in context_response:
            payload = match.payload
            
            # Campos comunes a todas las KBs
            source_info = {
                "text": payload.get('text', ''),
                "score": float(match.score)
            }
            
            # Detectar tipo de KB por campos disponibles
            if 'document_name' in payload:
                # KBs nuevas (recursive, semantic, structural, hybrid)
                source_info.update({
                    "document_name": payload.get('document_name', 'Unknown'),
                    "chunk_index": payload.get('chunk_index', 'Unknown'),
                    "chunking_method": payload.get('chunking_method', 'Unknown'),
                    "chunk_size": payload.get('chunk_size', 0),
                    "chunk_words": payload.get('chunk_words', 0)
                })
            elif 'book_title' in payload:
                # KB contextual (estructura antigua)
                source_info.update({
                    "document_name": payload.get('book_title', 'Unknown'),  # Usar book_title como document_name
                    "book_title": payload.get('book_title', 'Unknown'),
                    "page_number": payload.get('page_number', 'Unknown'),
                    "chunk_id": payload.get('chunk_id', 'Unknown'),
                    "chunk_type": payload.get('chunk_type', 'Unknown')
                })
            else:
                # Fallback si no reconocemos la estructura
                source_info["document_name"] = "Unknown"
            
            context_sources.append(source_info)
            
        # Debug: Imprimir document_names encontrados
        doc_names = [s.get('document_name', 'Unknown') for s in context_sources]
        print(f"   📄 Documentos recuperados: {doc_names}")
        
        print(f"📚 Contexto recuperado: {len(context_texts)} chunks")
        
        # Detectar idiomas en contexto recuperado
        doc_langs = []
        for source in context_sources:
            doc_name = source.get("document_name", "")
            if any(x in doc_name for x in ["DS NRO 034-2023-EM", "Ley NRO 30947"]):
                doc_langs.append("ES")
            elif any(x in doc_name for x in ["FMDS0104", "FMDS0520"]):
                doc_langs.append("EN")
        
        print(f"🌐 Idiomas en contexto: {doc_langs}")
        
        # LLM procesa contexto mixto y responde en español
        llm.language = "español"
        answer = llm.mistral_chat(context=context, question=question)
        
        print(f"✅ Respuesta generada en español")
        print(f"⚠️  ADVERTENCIA FASE A: Scores esperados bajos por KB mixta + embeddings monolingües")
        
        return {
            "answer": answer,
            "context": context_texts,
            "relevant_docs": context_texts,
            "context_sources": context_sources,
            "workflow_info": {
                "phase": "FASE A",
                "search_strategy": "direct_no_translation",
                "kb_type": "mixed_es_en",
                "embedding_model": "nomic-embed-text (monolingüe)",
                "expected_performance": "suboptimal",
                "context_languages": doc_langs,
                "response_language": "español"
            }
        }
        
    except Exception as e:
        print(f"❌ Error en RAG pipeline: {str(e)}")
        return {
            "error": f"RAG processing failed: {str(e)}",
            "workflow_info": {
                "status": "failed",
                "error_details": str(e)
            }
        }

if __name__ == "__main__":
    print("="*60)
    print("🚀 API RAG - FASE A: Evaluación KB Mixta")
    print("="*60)
    print(f"📦 Colección: {collection_name}")
    print(f"⚠️  SIN traducción forzada (busca en idioma original)")
    print(f"🎯 Objetivo: Comparar 7 métodos de chunking")
    print(f"📊 Scores esperados: 0.30-0.50 (limitación arquitectural)")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8001)