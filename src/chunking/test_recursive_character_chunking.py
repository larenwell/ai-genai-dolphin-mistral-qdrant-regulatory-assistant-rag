#!/usr/bin/env python3
"""
Script optimizado para Recursive Character Text Chunking
Lee archivos markdown generados por generate_markdown.py y su metadata
Genera embeddings e ingesta en Qdrant con metadata normalizada
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

from langchain_text_splitters import RecursiveCharacterTextSplitter
from embeddings.embedding_qdrant import EmbeddingControllerQdrant
import ollama

# Configuración
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"

# Configuración de Recursive Character Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

EMBEDDING_BATCH_SIZE = 10
COLLECTION_NAME = "asistente_normativa_sincro_kb_english_rcc"

def check_ollama_connection() -> bool:
    """Verifica que Ollama esté disponible y respondiendo"""
    print("🔍 Verificando conexión con Ollama...")
    try:
        response = ollama.embed(model=OLLAMA_MODEL, input="test")
        if response and "embeddings" in response:
            print(f"   ✅ Ollama conectado correctamente")
            print(f"   📊 Dimensión de embeddings: {len(response['embeddings'][0])}")
            return True
        return False
    except Exception as e:
        print(f"   ❌ No se puede conectar a Ollama: {str(e)}")
        print(f"   💡 Asegúrate de que Ollama esté corriendo:")
        print(f"      - Ejecuta: ollama serve")
        print(f"      - Verifica que el modelo esté instalado: ollama pull {OLLAMA_MODEL}")
        return False

def load_document_metadata(markdown_file: Path) -> Optional[Dict]:
    """
    Carga la metadata del documento desde el archivo JSON
    
    Args:
        markdown_file: Path al archivo markdown
        
    Returns:
        Dict con metadata del documento o None si no existe
    """
    # Buscar archivo de metadata correspondiente
    metadata_file = markdown_file.parent / (markdown_file.stem.replace('_markdown', '') + '_metadata.json')
    
    if not metadata_file.exists():
        print(f"   ⚠️  Archivo de metadata no encontrado: {metadata_file.name}")
        return None
    
    try:
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        print(f"   ✅ Metadata cargada:")
        print(f"      - Document ID: {metadata.get('document_id', 'N/A')}")
        print(f"      - Title: {metadata.get('book_title', 'N/A')}")
        print(f"      - Language: {metadata.get('language', 'N/A')}")
        
        return metadata
        
    except Exception as e:
        print(f"   ❌ Error leyendo metadata: {str(e)}")
        return None

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

def process_recursive_character_chunking(markdown_file: Path, doc_metadata: Dict) -> Optional[Tuple[List[Dict], Dict]]:
    """
    Procesa chunking usando RecursiveCharacterTextSplitter
    Usa metadata normalizada del documento
    
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
    
    print(f"   ⚙️ Configurando text splitter...")
    print(f"      - Chunk size: {CHUNK_SIZE}")
    print(f"      - Overlap: {CHUNK_OVERLAP}")
    
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=SEPARATORS,
            is_separator_regex=False
        )
    except Exception as e:
        print(f"   ❌ Error configurando splitter: {str(e)}")
        return None
    
    print(f"   🔄 Dividiendo contenido en chunks...")
    
    try:
        chunks = text_splitter.split_text(markdown_content)
    except Exception as e:
        print(f"   ❌ Error durante chunking: {str(e)}")
        return None
    
    if not chunks:
        print(f"   ⚠️ No se generaron chunks")
        return None
    
    print(f"   ✅ Chunking completado: {len(chunks)} chunks generados")
    
    # Analizar estadísticas
    stats = analyze_chunk_statistics(chunks)
    print_chunk_statistics(stats)
    
    print(f"   🏷️ Preparando metadatos de chunks...")
    
    # Crear estructura de chunks con metadata NORMALIZADA
    chunked_documents = []
    for i, chunk in enumerate(chunks):
        # Metadata completa y normalizada
        chunk_metadata = {
            # Identificación del documento (normalizada)
            "document_id": doc_metadata['document_id'],
            "source_file": doc_metadata['source_file'],
            "book_title": doc_metadata['book_title'],
            "language": doc_metadata['language'],
            
            # Información del chunk
            "chunk_index": i,
            "chunking_method": "recursive_character",
            "chunk_size": len(chunk),
            "chunk_words": len(chunk.split()),
            
            # Configuración del chunking
            "target_chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP
        }
        
        chunked_documents.append({
            "content": chunk,
            "metadata": chunk_metadata
        })
    
    print(f"   ✅ Metadatos preparados: {len(chunked_documents)} documentos")
    return chunked_documents, stats

def generate_embeddings_batch(embedding_controller: EmbeddingControllerQdrant, 
                              documents: List[str]) -> List:
    """Genera embeddings en lotes para mejor performance"""
    embeddings = []
    total_batches = (len(documents) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    
    print(f"   🔄 Generando embeddings en {total_batches} lotes de {EMBEDDING_BATCH_SIZE}...")
    
    for batch_idx in range(0, len(documents), EMBEDDING_BATCH_SIZE):
        batch = documents[batch_idx:batch_idx + EMBEDDING_BATCH_SIZE]
        batch_num = batch_idx // EMBEDDING_BATCH_SIZE + 1
        
        print(f"      📦 Lote {batch_num}/{total_batches} ({len(batch)} documentos)...")
        
        batch_embeddings = []
        for i, doc in enumerate(batch):
            try:
                embedding = embedding_controller.generate_embeddings(doc)
                
                if embedding is None or len(embedding) == 0:
                    print(f"         ⚠️ Embedding vacío para documento {batch_idx + i}")
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
                               doc_metadata: Dict,
                               stats: Dict,
                               recreate_collection: bool = False,
                               check_duplicates: bool = False) -> bool:
    """Guarda chunks y genera embeddings con metadata normalizada"""
    
    project_root = Path(__file__).parent.parent

    print(f"   📁 Creando directorios de salida...")

    chunking_dir = project_root / "src" / "output" / "chunking" / "recursive_character"
    preview_dir = project_root / "src" / "output" / "embeddings_preview" / "recursive_character"
    
    chunking_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"   💾 Guardando chunks en archivo JSON...")
    chunks_data = {
        "document_id": doc_metadata['document_id'],
        "book_title": doc_metadata['book_title'],
        "language": doc_metadata['language'],
        "statistics": stats,
        "configuration": {
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
            "separators": SEPARATORS
        },
        "chunks": chunks
    }
    
    # Usar document_id para el nombre del archivo
    chunks_file = chunking_dir / f"{doc_metadata['document_id']}_recursive_character_chunks.json"
    try:
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Chunks guardados: {chunks_file.name}")
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
            print(f"   🔍 Verificando si '{doc_metadata['document_id']}' ya existe...")
            exists = embedding_controller.check_document_exists(doc_metadata['document_id'])
            if exists:
                user_input = input(f"      ¿Eliminar y reemplazar el documento existente? (s/N): ").lower()
                if user_input == 's':
                    print(f"      🗑️ Eliminando documento anterior...")
                    embedding_controller.delete_document(doc_metadata['document_id'])
                    print(f"      ✅ Documento anterior eliminado")
                else:
                    print(f"      ⏭️ Saltando documento")
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
        "document_id": doc_metadata['document_id'],
        "book_title": doc_metadata['book_title'],
        "language": doc_metadata['language'],
        "chunking_method": "recursive_character",
        "configuration": {
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP,
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
                "preview": chunks[i]["content"][:200] + "..." if len(chunks[i]["content"]) > 200 else chunks[i]["content"]
            }
            for i in range(min(5, len(chunks)))
        ]
    }
    
    preview_file = preview_dir / f"{doc_metadata['document_id']}_recursive_character_embeddings_preview.json"
    try:
        with open(preview_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_preview, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Preview guardado: {preview_file.name}")
    except Exception as e:
        print(f"   ⚠️ Error guardando preview: {str(e)}")
    
    return success

def main():
    """Función principal"""
    print("🚀 RECURSIVE CHARACTER TEXT CHUNKING")
    print("="*60)
    print(f"📋 Lee archivos markdown y metadata generados por generate_markdown.py")
    print(f"   - Chunk size: {CHUNK_SIZE} caracteres")
    print(f"   - Overlap: {CHUNK_OVERLAP} caracteres")
    print()
    
    load_dotenv()
    
    if not check_ollama_connection():
        print("\n❌ No se puede continuar sin conexión a Ollama")
        return
    
    print()
    
    project_root = Path(__file__).parent.parent
    
    # ACTUALIZADO: Leer de markdown_english (no markdown)
    markdown_dir = project_root / "src" / "output" /"markdown"/ "FMDS"
    
    if not markdown_dir.exists():
        print(f"❌ No se encontró el directorio: {markdown_dir}")
        print("   Ejecuta primero: python scripts/generate_markdown.py")
        return
    
    markdown_files = [f for f in os.listdir(markdown_dir) if f.endswith('_markdown.md')]
    
    if not markdown_files:
        print(f"❌ No se encontraron archivos markdown en {markdown_dir}")
        print("   Ejecuta primero: python scripts/generate_markdown.py")
        return
    
    print(f"📁 Archivos markdown encontrados: {len(markdown_files)}")
    for file in markdown_files:
        print(f"   📄 {file}")
    print()
    
    print("🗄️ CONFIGURACIÓN DE COLECCIÓN QDRANT")
    print("-"*60)
    print(f"Colección: {COLLECTION_NAME}")
    print()
    print("Opciones:")
    print("  1. Agregar a colección existente")
    print("  2. Recrear colección (BORRA todo)")
    print("  3. Verificar duplicados antes de agregar (recomendado)")
    print()
    
    option = input("Selecciona una opción (1/2/3) [default=1]: ").strip()
    
    if option == '2':
        recreate = True
        check_duplicates = False
        print("   ⚠️ Se recreará la colección")
    elif option == '3':
        recreate = False
        check_duplicates = True
        print("   ✅ Se verificarán duplicados")
    else:
        recreate = False
        check_duplicates = False
        print("   ℹ️ Se agregará a la colección existente")
    
    total_processed = 0
    total_failed = 0
    total_chunks = 0
    total_embeddings = 0
    
    for i, markdown_file in enumerate(markdown_files, 1):
        markdown_path = markdown_dir / markdown_file
        
        print(f"🔄 PROCESANDO DOCUMENTO {i}/{len(markdown_files)}: {markdown_file}")
        print("-"*60)
        
        try:
            # NUEVO: Cargar metadata del documento
            print(f"📋 FASE 0: Carga de Metadata")
            doc_metadata = load_document_metadata(markdown_path)
            
            if not doc_metadata:
                print(f"❌ No se pudo cargar metadata de {markdown_file}")
                total_failed += 1
                continue
            
            print(f"📝 FASE 1: Recursive Character Chunking")
            result = process_recursive_character_chunking(markdown_path, doc_metadata)
            
            if result is None:
                print(f"❌ Error en chunking de {markdown_file}")
                total_failed += 1
                continue
            
            chunks, stats = result
            total_chunks += len(chunks)
            print(f"✅ Chunking completado: {len(chunks)} chunks generados")
            print()
            
            print(f"💾 FASE 2: Guardado y Embeddings")
            should_recreate = recreate and (i == 1)
            should_check = check_duplicates
            success = save_chunks_and_embeddings(chunks, doc_metadata, stats, should_recreate, should_check)
            
            if success:
                print(f"🎉 {doc_metadata['document_id']} procesado exitosamente")
                total_processed += 1
                total_embeddings += len(chunks)
            else:
                print(f"⚠️ {doc_metadata['document_id']} procesado con advertencias")
                total_processed += 1
                
        except Exception as e:
            print(f"❌ Error inesperado procesando {markdown_file}: {str(e)}")
            import traceback
            traceback.print_exc()
            total_failed += 1
        
        print()
        print("="*60)
        print()
    
    # Resumen final
    print("📊 RESUMEN FINAL")
    print("="*60)
    print(f"✅ Documentos procesados exitosamente: {total_processed}")
    print(f"❌ Documentos con errores: {total_failed}")
    print(f"📁 Total de documentos: {len(markdown_files)}")
    print(f"📦 Total de chunks generados: {total_chunks}")
    print(f"🔢 Total de embeddings creados: {total_embeddings}")
    
    if total_processed > 0:
        try:
            print(f"\n📊 ESTADÍSTICAS DE LA COLECCIÓN QDRANT")
            print("-"*60)
            embedding_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
            stats = embedding_controller.get_collection_stats()
            print(f"Total de chunks en colección: {stats['total_chunks']}")
            print(f"Documentos únicos: {stats['unique_documents']}")
            print(f"Documentos:")
            for doc_name in sorted(stats['document_names']):
                print(f"   - {doc_name}")
        except Exception as e:
            print(f"⚠️ No se pudieron obtener estadísticas: {e}")
    
    if total_processed > 0:    
        print(f"\n🎉 Recursive Character Chunking completado!")
        print(f"📁 Revisa los resultados en:")
        print(f"   - output/chunking/recursive_character/")
        print(f"   - output/embeddings_preview/recursive_character/")
        print(f"   - Base de conocimiento Qdrant: {COLLECTION_NAME}")
    
    if total_failed > 0:
        print(f"\n⚠️ Algunos documentos tuvieron problemas. Revisa los errores arriba.")

if __name__ == "__main__":
    main()