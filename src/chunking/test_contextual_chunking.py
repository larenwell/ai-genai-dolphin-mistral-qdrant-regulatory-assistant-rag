#!/usr/bin/env python3
"""
Script para evaluar Contextual Chunking
Usa el método actual: intelligent_chunking + contextualize_chunk
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from ingestion.ingest_mistral import MistralExtractionController
from embeddings.embedding_qdrant import EmbeddingControllerQdrant

def process_contextual_chunking(markdown_file, document_name, api_key):
    """Procesa chunking usando el método contextual actual"""
    
    # Leer contenido markdown
    with open(markdown_file, 'r', encoding='utf-8') as f:
        markdown_content = f.read()
    
    # Inicializar controlador Mistral
    mistral_controller = MistralExtractionController(api_key)
    
    # Generar resumen del documento
    document_summary = mistral_controller.generate_document_summary(markdown_content)
    
    # Chunking inteligente
    chunks = mistral_controller.intelligent_chunking(markdown_content)
    
    # Contextualizar chunks
    contextualized_chunks = []
    for chunk in chunks:
        enhanced_chunk = mistral_controller.contextualize_chunk(
            chunk, 
            document_summary, 
            document_name
        )
        contextualized_chunks.append(enhanced_chunk)
    
    return contextualized_chunks, document_summary

def save_chunks_and_embeddings(chunks, document_name, document_summary):
    """Guarda chunks y genera embeddings"""
    
    # Crear directorios
    os.makedirs("output/chunking/contextual", exist_ok=True)
    os.makedirs("output/embeddings_preview/contextual", exist_ok=True)
    
    # Guardar chunks
    chunks_file = f"output/chunking/contextual/{document_name}_contextual_chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Chunks guardados: {chunks_file}")
    
    # Generar embeddings y guardar en Qdrant
    collection_name = "rag_contextual_construction"
    embedding_controller = EmbeddingControllerQdrant(qdrant_collection=collection_name)
    
    # Preparar documentos para embedding
    documents_for_embedding = [chunk["content"] for chunk in chunks]
    metadata_list = [chunk["metadata"] for chunk in chunks]
    
    # Generar embeddings
    embeddings = []
    for doc in documents_for_embedding:
        embedding = embedding_controller.generate_embeddings(doc)
        embeddings.append(embedding)
    
    # Guardar en Qdrant
    embedding_controller.store_embeddings(
        embeddings, 
        documents_for_embedding,
        metadata_list
    )
    
    print(f"✅ Embeddings guardados en Qdrant collection: {collection_name}")
    
    # Guardar preview de embeddings
    embeddings_preview = {
        "document_name": document_name,
        "chunking_method": "contextual",
        "total_chunks": len(chunks),
        "collection_name": collection_name,
        "document_summary": document_summary,
        "sample_embeddings": embeddings[:3],  # Primeros 3 embeddings
        "chunk_sizes": [len(chunk["content"]) for chunk in chunks[:10]]  # Tamaños de primeros 10 chunks
    }
    
    preview_file = f"output/embeddings_preview/contextual/{document_name}_contextual_embeddings_preview.json"
    with open(preview_file, 'w', encoding='utf-8') as f:
        json.dump(embeddings_preview, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Preview de embeddings guardado: {preview_file}")
    
    return True

def main():
    """Función principal"""
    load_dotenv()
    
    # Verificar API key
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ Error: MISTRAL_API_KEY no encontrada en las variables de entorno")
        return
    
    # Directorio de markdown
    markdown_dir = "output/markdown"
    markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('_markdown.md')]
    
    if not markdown_files:
        print("❌ No se encontraron archivos markdown en output/markdown")
        print("   Ejecuta primero: python scripts/generate_markdown.py")
        return
    
    print(f"📁 Procesando {len(markdown_files)} archivos markdown...")
    
    for markdown_file in markdown_files:
        # Extraer nombre del documento (remover _markdown.md)
        document_name = markdown_file.replace('_markdown.md', '')
        markdown_path = os.path.join(markdown_dir, markdown_file)
        
        print(f"\n🔄 Procesando: {document_name}")
        
        try:
            # Procesar chunking
            chunks, document_summary = process_contextual_chunking(markdown_path, document_name, api_key)
            print(f"✅ Generados {len(chunks)} chunks")
            
            # Guardar chunks y embeddings
            success = save_chunks_and_embeddings(chunks, document_name, document_summary)
            
            if success:
                print(f"✅ {document_name} procesado exitosamente")
            else:
                print(f"❌ Error procesando {document_name}")
                
        except Exception as e:
            print(f"❌ Error procesando {document_name}: {str(e)}")
    
    print(f"\n🎉 Procesamiento completado para Contextual Chunking")

if __name__ == "__main__":
    main()
