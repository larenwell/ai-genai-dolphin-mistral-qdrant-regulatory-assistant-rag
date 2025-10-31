#!/usr/bin/env python3
"""
Script optimizado para Hybrid Chunking
Combina Structural (MarkdownHeaderTextSplitter) + Semantic (SemanticChunker)
con mejores prácticas y validaciones
"""

import os
import json
import sys
import statistics
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings
from embeddings.embedding_qdrant import EmbeddingControllerQdrant

# Configuración
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"

# Configuración de Hybrid Chunking
STRUCTURAL_HEADERS = [
    ("#", "Header 1"),
    ("##", "Header 2"), 
    ("###", "Header 3"),
    ("####", "Header 4"),
]

# Semantic chunking solo se aplica a secciones grandes
MIN_SECTION_SIZE_FOR_SEMANTIC = 3000  # Solo dividir secciones > 3000 caracteres
SEMANTIC_METHOD = "percentile"  # percentile | standard_deviation | gradient | interquartile
SEMANTIC_THRESHOLD = 80  # Para secciones grandes, usar 80-85 para balance

EMBEDDING_BATCH_SIZE = 10
COLLECTION_NAME = "rag_hybrid_construction_p80_markdown"

def check_ollama_connection() -> bool:
    """Verifica que Ollama esté disponible y respondiendo"""
    print("🔍 Verificando conexión con Ollama...")
    try:
        embeddings = OllamaEmbeddings(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL
        )
        test_result = embeddings.embed_query("test connection")
        
        if test_result and len(test_result) > 0:
            print(f"   ✅ Ollama conectado correctamente")
            print(f"   📊 Dimensión de embeddings: {len(test_result)}")
            return True
        else:
            print(f"   ❌ Ollama respondió pero el embedding está vacío")
            return False
            
    except Exception as e:
        print(f"   ❌ No se puede conectar a Ollama: {str(e)}")
        print(f"   💡 Asegúrate de que Ollama esté corriendo:")
        print(f"      - Ejecuta: ollama serve")
        print(f"      - Verifica que el modelo esté instalado: ollama pull {OLLAMA_MODEL}")
        return False

def analyze_chunk_statistics(chunks: List[str]) -> Dict:
    """Analiza estadísticas de los chunks generados"""
    chunk_sizes = [len(chunk) for chunk in chunks]
    chunk_words = [len(chunk.split()) for chunk in chunks]
    
    return {
        "total_chunks": len(chunks),
        "char_stats": {
            "mean": statistics.mean(chunk_sizes),
            "median": statistics.median(chunk_sizes),
            "min": min(chunk_sizes),
            "max": max(chunk_sizes),
            "stdev": statistics.stdev(chunk_sizes) if len(chunk_sizes) > 1 else 0
        },
        "word_stats": {
            "mean": statistics.mean(chunk_words),
            "median": statistics.median(chunk_words),
            "min": min(chunk_words),
            "max": max(chunk_words)
        }
    }

def print_chunk_statistics(stats: Dict):
    """Imprime estadísticas de forma legible"""
    print(f"   📊 Estadísticas de chunks:")
    print(f"      Total: {stats['total_chunks']} chunks")
    print(f"      ")
    print(f"      📏 Caracteres:")
    print(f"         - Promedio: {stats['char_stats']['mean']:.0f}")
    print(f"         - Mediana:  {stats['char_stats']['median']:.0f}")
    print(f"         - Rango: {stats['char_stats']['min']} - {stats['char_stats']['max']}")
    print(f"      ")
    print(f"      📝 Palabras:")
    print(f"         - Promedio: {stats['word_stats']['mean']:.0f}")
    print(f"         - Rango: {stats['word_stats']['min']} - {stats['word_stats']['max']}")

def process_hybrid_chunking(markdown_file: Path, document_name: str) -> Optional[Tuple[List[Dict], Dict]]:
    """
    Procesa chunking combinando Structural + Semantic
    
    Estrategia:
    1. Divide por estructura (headers markdown)
    2. Solo aplica semantic chunking a secciones > MIN_SECTION_SIZE_FOR_SEMANTIC
    3. Secciones pequeñas se mantienen como un solo chunk
    
    Returns:
        Tuple con (chunks_con_metadata, estadísticas) o None si falla
    """
    
    print(f"   📖 Leyendo archivo markdown...")
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except Exception as e:
        print(f"   ❌ Error leyendo archivo: {str(e)}")
        return None
    
    if not markdown_content.strip():
        print(f"   ⚠️ El archivo está vacío")
        return None
    
    print(f"   📊 Tamaño del contenido: {len(markdown_content):,} caracteres")
    
    # FASE 1: Structural Chunking (por headers)
    print(f"   🏗️ FASE 1: Chunking Estructural (por headers markdown)...")
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=STRUCTURAL_HEADERS,
        strip_headers=False  # Mantener headers en el contenido
    )
    
    try:
        structural_chunks = markdown_splitter.split_text(markdown_content)
        print(f"   ✅ Secciones estructurales generadas: {len(structural_chunks)}")
    except Exception as e:
        print(f"   ❌ Error en chunking estructural: {str(e)}")
        return None
    
    # FASE 2: Semantic Chunking en secciones grandes
    print(f"   🧠 FASE 2: Semantic Chunking en secciones grandes (>{MIN_SECTION_SIZE_FOR_SEMANTIC} chars)...")
    print(f"      Método: {SEMANTIC_METHOD}, Threshold: {SEMANTIC_THRESHOLD}")
    
    # Configurar embeddings para semantic chunking
    try:
        embeddings = OllamaEmbeddings(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL
        )
    except Exception as e:
        print(f"   ❌ Error configurando embeddings: {str(e)}")
        return None
    
    # Configurar semantic chunker según método
    try:
        if SEMANTIC_METHOD == "gradient":
            semantic_chunker = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="gradient",
                add_start_index=True
            )
        elif SEMANTIC_METHOD == "standard_deviation":
            semantic_chunker = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="standard_deviation",
                breakpoint_threshold_amount=SEMANTIC_THRESHOLD if SEMANTIC_THRESHOLD else 3.0,
                add_start_index=True
            )
        elif SEMANTIC_METHOD == "interquartile":
            semantic_chunker = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="interquartile",
                breakpoint_threshold_amount=SEMANTIC_THRESHOLD if SEMANTIC_THRESHOLD else 1.5,
                add_start_index=True
            )
        else:  # percentile (default)
            semantic_chunker = SemanticChunker(
                embeddings=embeddings,
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=SEMANTIC_THRESHOLD if SEMANTIC_THRESHOLD else 95,
                add_start_index=True
            )
    except Exception as e:
        print(f"   ❌ Error configurando semantic chunker: {str(e)}")
        return None
    
    # Aplicar semantic chunking solo a secciones grandes
    hybrid_chunks = []
    sections_subdivided = 0
    sections_kept_whole = 0
    
    for i, structural_chunk in enumerate(structural_chunks):
        section_content = structural_chunk.page_content
        section_size = len(section_content)
        
        # Decidir si aplicar semantic chunking
        if section_size > MIN_SECTION_SIZE_FOR_SEMANTIC:
            # Sección grande: aplicar semantic chunking
            try:
                print(f"      📄 Sección {i+1}: {section_size} chars → Subdividiendo...")
                semantic_chunks = semantic_chunker.split_text(section_content)
                sections_subdivided += 1
                
                for j, semantic_chunk in enumerate(semantic_chunks):
                    hybrid_chunks.append({
                        "content": semantic_chunk,
                        "metadata": {
                            "structural_chunk_index": i,
                            "semantic_chunk_index": j,
                            "total_semantic_chunks_in_section": len(semantic_chunks),
                            "section_size": section_size,
                            "was_subdivided": True,
                            **structural_chunk.metadata
                        }
                    })
                
                print(f"         ✅ Generados {len(semantic_chunks)} sub-chunks")
                
            except Exception as e:
                print(f"      ⚠️ Error en semantic chunking de sección {i+1}: {e}")
                # Si falla, mantener la sección completa
                hybrid_chunks.append({
                    "content": section_content,
                    "metadata": {
                        "structural_chunk_index": i,
                        "semantic_chunk_index": 0,
                        "total_semantic_chunks_in_section": 1,
                        "section_size": section_size,
                        "was_subdivided": False,
                        **structural_chunk.metadata
                    }
                })
                sections_kept_whole += 1
        else:
            # Sección pequeña: mantener completa
            hybrid_chunks.append({
                "content": section_content,
                "metadata": {
                    "structural_chunk_index": i,
                    "semantic_chunk_index": 0,
                    "total_semantic_chunks_in_section": 1,
                    "section_size": section_size,
                    "was_subdivided": False,
                    **structural_chunk.metadata
                }
            })
            sections_kept_whole += 1
    
    print(f"   ✅ Hybrid Chunking completado:")
    print(f"      - Secciones estructurales: {len(structural_chunks)}")
    print(f"      - Secciones subdivididas: {sections_subdivided}")
    print(f"      - Secciones completas: {sections_kept_whole}")
    print(f"      - Total chunks finales: {len(hybrid_chunks)}")
    
    # Agregar metadatos finales
    for idx, chunk in enumerate(hybrid_chunks):
        chunk["metadata"].update({
            "chunk_index": idx,
            "document_name": document_name,
            "chunking_method": "hybrid_structural_semantic",
            "chunk_size": len(chunk["content"]),
            "chunk_words": len(chunk["content"].split()),
            "semantic_method": SEMANTIC_METHOD,
            "semantic_threshold": SEMANTIC_THRESHOLD,
            "min_section_size": MIN_SECTION_SIZE_FOR_SEMANTIC
        })
    
    # Analizar estadísticas
    chunk_contents = [c["content"] for c in hybrid_chunks]
    stats = analyze_chunk_statistics(chunk_contents)
    print_chunk_statistics(stats)
    
    # Agregar info de estrategia a stats
    stats["strategy"] = {
        "structural_sections": len(structural_chunks),
        "sections_subdivided": sections_subdivided,
        "sections_kept_whole": sections_kept_whole,
        "min_section_size_for_semantic": MIN_SECTION_SIZE_FOR_SEMANTIC
    }
    
    return hybrid_chunks, stats

def generate_embeddings_batch(embedding_controller: EmbeddingControllerQdrant, 
                              documents: List[str]) -> List:
    """Genera embeddings en lotes para mejor performance"""
    embeddings = []
    total_batches = (len(documents) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    
    print(f"   🔄 Generando embeddings en {total_batches} lotes de {EMBEDDING_BATCH_SIZE}...")
    
    for batch_idx in range(0, len(documents), EMBEDDING_BATCH_SIZE):
        batch = documents[batch_idx:batch_idx + EMBEDDING_BATCH_SIZE]
        batch_num = batch_idx // EMBEDDING_BATCH_SIZE + 1
        
        print(f"      📦 Procesando lote {batch_num}/{total_batches} ({len(batch)} documentos)...")
        
        batch_embeddings = []
        for i, doc in enumerate(batch):
            try:
                embedding = embedding_controller.generate_embeddings(doc)
                
                if embedding is None or len(embedding) == 0:
                    print(f"         ⚠️ Warning: Embedding vacío para documento {batch_idx + i}")
                    continue
                
                batch_embeddings.append(embedding)
                
            except Exception as e:
                print(f"         ❌ Error generando embedding {batch_idx + i}: {str(e)}")
                continue
        
        embeddings.extend(batch_embeddings)
        print(f"         ✅ Lote {batch_num} completado ({len(batch_embeddings)}/{len(batch)} exitosos)")
    
    print(f"   ✅ Total embeddings generados: {len(embeddings)}/{len(documents)}")
    return embeddings

def save_chunks_and_embeddings(chunks: List[Dict], 
                               document_name: str, 
                               stats: Dict,
                               recreate_collection: bool = False,
                               check_duplicates: bool = False) -> bool:
    """Guarda chunks y genera embeddings con validaciones"""
    
    project_root = Path(__file__).parent.parent
    
    print(f"   📁 Creando directorios de salida...")
    
    chunking_dir = project_root / "output" / "chunking" / "hybrid_p80_markdown"
    preview_dir = project_root / "output" / "embeddings_preview" / "hybrid_p80_markdown"
    
    chunking_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"   💾 Guardando chunks en archivo JSON...")
    chunks_data = {
        "document_name": document_name,
        "statistics": stats,
        "chunks": chunks
    }
    
    chunks_file = chunking_dir / f"{document_name}_hybrid_chunks.json"
    try:
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Chunks guardados: {chunks_file}")
    except Exception as e:
        print(f"   ❌ Error guardando chunks: {str(e)}")
        return False
    
    print(f"   🗄️ Inicializando controlador de embeddings...")
    try:
        embedding_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
        
        if recreate_collection:
            print(f"   🗑️ Recreando colección {COLLECTION_NAME}...")
            success = embedding_controller.recreate_collection()
            if not success:
                print(f"   ❌ Error recreando colección")
                return False
        
        if check_duplicates:
            print(f"   🔍 Verificando si '{document_name}' ya existe en la colección...")
            exists = embedding_controller.check_document_exists(document_name)
            if exists:
                user_input = input(f"      ¿Eliminar y reemplazar el documento existente? (s/N): ").lower()
                if user_input == 's':
                    print(f"      🗑️ Eliminando documento anterior...")
                    embedding_controller.delete_document(document_name)
                    print(f"      ✅ Documento anterior eliminado. Procediendo con el nuevo...")
                else:
                    print(f"      ⏭️ Saltando documento para evitar duplicados.")
                    return True
            else:
                print(f"   ✅ Documento no existe. Procediendo...")
            
    except Exception as e:
        print(f"   ❌ Error inicializando controlador: {str(e)}")
        return False
    
    print(f"   📋 Preparando documentos para embedding...")
    documents_for_embedding = [chunk["content"] for chunk in chunks]
    metadata_list = [chunk["metadata"] for chunk in chunks]
    
    embeddings = generate_embeddings_batch(embedding_controller, documents_for_embedding)
    
    if len(embeddings) == 0:
        print(f"   ❌ No se generó ningún embedding válido")
        return False
    
    if len(embeddings) < len(documents_for_embedding):
        print(f"   ⚠️ Solo se generaron {len(embeddings)}/{len(documents_for_embedding)} embeddings")
        metadata_list = metadata_list[:len(embeddings)]
        documents_for_embedding = documents_for_embedding[:len(embeddings)]
    
    print(f"   🗃️ Almacenando embeddings en Qdrant...")
    print(f"      📊 Colección: {COLLECTION_NAME}")
    
    try:
        success = embedding_controller.store_embeddings(
            embeddings, 
            documents_for_embedding,
            metadata_list
        )
        
        if success:
            print(f"   ✅ {len(embeddings)} embeddings guardados exitosamente en Qdrant")
        else:
            print(f"   ⚠️ Algunos embeddings no se guardaron correctamente")
            
    except Exception as e:
        print(f"   ❌ Error almacenando en Qdrant: {str(e)}")
        return False
    
    print(f"   📊 Generando preview de embeddings...")
    embeddings_preview = {
        "document_name": document_name,
        "chunking_method": "hybrid_structural_semantic",
        "configuration": {
            "structural_headers": STRUCTURAL_HEADERS,
            "min_section_size_for_semantic": MIN_SECTION_SIZE_FOR_SEMANTIC,
            "semantic_method": SEMANTIC_METHOD,
            "semantic_threshold": SEMANTIC_THRESHOLD,
            "model": OLLAMA_MODEL,
            "embedding_dimension": len(embeddings[0]) if embeddings else 0
        },
        "statistics": stats,
        "total_chunks": len(chunks),
        "total_embeddings": len(embeddings),
        "collection_name": COLLECTION_NAME,
        "sample_embeddings": embeddings[:3] if len(embeddings) >= 3 else embeddings,
        "sample_chunks": [
            {
                "index": i,
                "size": len(chunks[i]["content"]),
                "structural_index": chunks[i]["metadata"]["structural_chunk_index"],
                "was_subdivided": chunks[i]["metadata"]["was_subdivided"],
                "preview": chunks[i]["content"][:200] + "..." if len(chunks[i]["content"]) > 200 else chunks[i]["content"]
            }
            for i in range(min(5, len(chunks)))
        ]
    }
    
    preview_file = preview_dir / f"{document_name}_hybrid_embeddings_preview.json"
    try:
        with open(preview_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_preview, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Preview de embeddings guardado: {preview_file}")
    except Exception as e:
        print(f"   ⚠️ Error guardando preview: {str(e)}")
    
    return success

def main():
    """Función principal"""
    print("🚀 INICIANDO HYBRID CHUNKING (VERSIÓN OPTIMIZADA)")
    print("=" * 60)
    print(f"📋 Estrategia: Structural + Semantic Híbrido")
    print(f"   1. Divide por estructura (headers markdown)")
    print(f"   2. Semantic chunking solo en secciones >{MIN_SECTION_SIZE_FOR_SEMANTIC} chars")
    print(f"   3. Secciones pequeñas se mantienen completas")
    print()
    
    load_dotenv()
    
    if not check_ollama_connection():
        print("\n❌ No se puede continuar sin conexión a Ollama")
        return
    
    print()
    
    project_root = Path(__file__).parent.parent
    markdown_dir = project_root / "output" / "markdown"
    
    if not markdown_dir.exists():
        print(f"❌ No se encontró el directorio: {markdown_dir}")
        print("   Ejecuta primero: python scripts/generate_markdown.py")
        return
    
    markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('_markdown.md')]
    
    if not markdown_files:
        print("❌ No se encontraron archivos markdown en output/markdown")
        print("   Ejecuta primero: python scripts/generate_markdown.py")
        return
    
    print(f"📁 Archivos markdown encontrados: {len(markdown_files)}")
    for file in markdown_files:
        print(f"   📄 {file}")
    print()
    
    print("🗄️ CONFIGURACIÓN DE COLECCIÓN QDRANT")
    print("-" * 60)
    print(f"Colección: {COLLECTION_NAME}")
    print()
    print("Opciones:")
    print("  1. Agregar a colección existente (mantiene datos previos)")
    print("  2. Recrear colección (BORRA todo y empieza desde cero)")
    print("  3. Verificar duplicados antes de agregar (recomendado)")
    print()
    
    option = input("Selecciona una opción (1/2/3) [default=1]: ").strip()
    
    if option == '2':
        recreate = True
        check_duplicates = False
        print("   ⚠️ Se recreará la colección (se perderán datos previos)")
    elif option == '3':
        recreate = False
        check_duplicates = True
        print("   ✅ Se verificarán duplicados antes de agregar")
    else:
        recreate = False
        check_duplicates = False
        print("   ℹ️ Se agregará a la colección existente")
    
    total_processed = 0
    total_failed = 0
    total_chunks = 0
    total_embeddings = 0
    
    for i, markdown_file in enumerate(markdown_files, 1):
        document_name = markdown_file.replace('_markdown.md', '')
        markdown_path = markdown_dir / markdown_file
        
        print(f"🔄 PROCESANDO DOCUMENTO {i}/{len(markdown_files)}: {document_name}")
        print("-" * 60)
        
        try:
            print(f"📝 FASE 1: Hybrid Chunking")
            result = process_hybrid_chunking(markdown_path, document_name)
            
            if result is None:
                print(f"❌ Error en chunking de {document_name}")
                total_failed += 1
                continue
            
            chunks, stats = result
            total_chunks += len(chunks)
            print(f"✅ Chunking completado: {len(chunks)} chunks generados")
            print()
            
            print(f"💾 FASE 2: Guardado y Embeddings")
            should_recreate = recreate and (i == 1)
            should_check = check_duplicates
            success = save_chunks_and_embeddings(chunks, document_name, stats, should_recreate, should_check)
            
            if success:
                print(f"🎉 {document_name} procesado exitosamente")
                total_processed += 1
                total_embeddings += len(chunks)
            else:
                print(f"⚠️ {document_name} procesado con advertencias")
                total_processed += 1
                
        except Exception as e:
            print(f"❌ Error inesperado procesando {document_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            total_failed += 1
        
        print()
        print("=" * 60)
        print()
    
    # Resumen final
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    print(f"✅ Documentos procesados exitosamente: {total_processed}")
    print(f"❌ Documentos con errores: {total_failed}")
    print(f"📁 Total de documentos: {len(markdown_files)}")
    print(f"📦 Total de chunks generados: {total_chunks}")
    print(f"🔢 Total de embeddings creados: {total_embeddings}")
    
    # Mostrar estadísticas de la colección
    if total_processed > 0:
        try:
            print(f"\n📊 ESTADÍSTICAS DE LA COLECCIÓN QDRANT")
            print("-" * 60)
            embedding_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
            stats = embedding_controller.get_collection_stats()
            print(f"Total de chunks en colección: {stats['total_chunks']}")
            print(f"Documentos únicos: {stats['unique_documents']}")
            print(f"Nombres de documentos:")
            for doc_name in sorted(stats['document_names']):
                print(f"   - {doc_name}")
        except Exception as e:
            print(f"⚠️ No se pudieron obtener estadísticas: {e}")
    
    if total_processed > 0:
        print(f"\n🎉 Hybrid Chunking completado!")
        print(f"📁 Revisa los resultados en:")
        print(f"   - output/chunking/hybrid_p80_markdown/")
        print(f"   - output/embeddings_preview/hybrid_p80_markdown/")
        print(f"   - Base de conocimiento Qdrant: {COLLECTION_NAME}")
        print(f"\n📊 Configuración utilizada:")
        print(f"   - Modelo: {OLLAMA_MODEL}")
        print(f"   - Min section size: {MIN_SECTION_SIZE_FOR_SEMANTIC} chars")
        print(f"   - Semantic method: {SEMANTIC_METHOD}")
        print(f"   - Semantic threshold: {SEMANTIC_THRESHOLD}")
        print(f"   - Batch size: {EMBEDDING_BATCH_SIZE}")
    
    if total_failed > 0:
        print(f"\n⚠️ Algunos documentos tuvieron problemas. Revisa los errores arriba.")

if __name__ == "__main__":
    main()