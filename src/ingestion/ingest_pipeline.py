#!/usr/bin/env python3
"""
Pipeline de Ingesta Completo - Chunking y Embeddings con Metadata Normalizada

Este script refactoriza test_recursive_character_chunking.py para:
1. Leer archivos markdown desde processed_en/{pestaña}/
2. Construir metadata completa usando MetadataBuilder
3. Generar chunks con metadata normalizada
4. Generar embeddings e ingestar en Qdrant
5. Guardar metadata intermedia (chunking) y final

Flujo:
1. Lee markdown desde processed_en/{pestaña}/
2. Construye metadata completa (source + extraction + translation)
3. Genera chunks con RecursiveCharacterTextSplitter
4. Construye metadata completa para cada chunk
5. Genera embeddings
6. Guarda metadata intermedia (chunking) y final
7. Ingesta en Qdrant con metadata normalizada
"""

import os
import json
import sys
import statistics
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.embeddings.embedding_qdrant import EmbeddingControllerQdrant
from src.metadata.metadata_builder import MetadataBuilder
from src.core import get_logger
import ollama

# Setup logging
logger = get_logger(__name__)

# Load environment
load_dotenv()

# Configuración
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "nomic-embed-text"

# Configuración de Recursive Character Chunking
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

EMBEDDING_BATCH_SIZE = 10

# Obtener nombre de colección desde .env
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "normativa-asistente-qdrant-kbs")


def check_ollama_connection() -> bool:
    """Verifica que Ollama esté disponible y respondiendo"""
    logger.info(f"   - URL: {OLLAMA_BASE_URL}")
    logger.info(f"   - Modelo: {OLLAMA_MODEL}")
    logger.info("   - Probando conexión (generando embedding de prueba)...")
    print("   ⏳ Generando embedding de prueba (esto puede tardar 5-10 segundos)...", flush=True)
    sys.stdout.flush()  # Forzar salida inmediata
    
    try:
        # Hacer la llamada directamente - ollama tiene timeout por defecto
        print("   🔄 Llamando a Ollama...", flush=True)
        response = ollama.embed(model=OLLAMA_MODEL, input="test")
        print("   ✅ Respuesta recibida de Ollama", flush=True)
        
        if response and "embeddings" in response:
            logger.info(f"   ✅ Ollama conectado correctamente")
            logger.info(f"   📊 Dimensión de embeddings: {len(response['embeddings'][0])}")
            sys.stdout.flush()
            return True
        logger.warning("   ⚠️ Respuesta de Ollama inesperada")
        sys.stdout.flush()
        return False
    except Exception as e:
        logger.error(f"   ❌ No se puede conectar a Ollama: {str(e)}")
        logger.info(f"   💡 Asegúrate de que Ollama esté corriendo:")
        logger.info(f"      - Verifica: curl http://localhost:11434/api/tags")
        logger.info(f"      - O ejecuta: ./rag_system.sh start ollama")
        logger.info(f"      - Verifica que el modelo esté instalado: ollama pull {OLLAMA_MODEL}")
        sys.stdout.flush()
        return False


def extract_document_id_from_filename(filename: str) -> str:
    """Extrae document_id del nombre del archivo markdown."""
    return Path(filename).stem


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
    logger.info(f"   📊 Estadísticas de chunks:")
    logger.info(f"      Total: {stats['total_chunks']} chunks")
    logger.info(f"      📏 Caracteres:")
    logger.info(f"         - Promedio: {stats['char_stats']['mean']:.0f}")
    logger.info(f"         - Mediana:  {stats['char_stats']['median']:.0f}")
    logger.info(f"         - Rango: {stats['char_stats']['min']} - {stats['char_stats']['max']}")
    logger.info(f"      📝 Palabras:")
    logger.info(f"         - Promedio: {stats['word_stats']['mean']:.0f}")
    logger.info(f"         - Rango: {stats['word_stats']['min']} - {stats['word_stats']['max']}")


def process_recursive_character_chunking(
    markdown_file: Path,
    metadata_builder: MetadataBuilder,
    document_id: str,
    sheet: str
) -> Optional[Tuple[List[Dict], Dict, Dict]]:
    """
    Procesa chunking usando RecursiveCharacterTextSplitter con metadata completa.
    
    Args:
        markdown_file: Path al archivo markdown
        metadata_builder: Instancia de MetadataBuilder
        document_id: ID del documento
        sheet: Nombre de la pestaña
    
    Returns:
        Tuple con (chunks_con_metadata, estadísticas, document_metadata) o None si falla
    """
    
    logger.info(f"   📖 Leyendo archivo markdown...")
    try:
        with open(markdown_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except Exception as e:
        logger.error(f"   ❌ Error leyendo archivo: {str(e)}")
        return None
    
    if not markdown_content.strip():
        logger.warning(f"   ⚠️ El archivo está vacío")
        return None
    
    logger.info(f"   📊 Tamaño del contenido: {len(markdown_content):,} caracteres")
    
    # Construir metadata completa del documento
    logger.info(f"   🏗️ Construyendo metadata completa del documento...")
    document_metadata = metadata_builder.build_document_metadata(document_id, sheet)
    if not document_metadata:
        logger.error(f"   ❌ No se pudo construir metadata completa")
        return None
    
    logger.info(f"   ⚙️ Configurando text splitter...")
    logger.info(f"      - Chunk size: {CHUNK_SIZE}")
    logger.info(f"      - Overlap: {CHUNK_OVERLAP}")
    
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=SEPARATORS,
            is_separator_regex=False
        )
    except Exception as e:
        logger.error(f"   ❌ Error configurando splitter: {str(e)}")
        return None
    
    logger.info(f"   🔄 Dividiendo contenido en chunks...")
    
    try:
        chunks = text_splitter.split_text(markdown_content)
    except Exception as e:
        logger.error(f"   ❌ Error durante chunking: {str(e)}")
        return None
    
    if not chunks:
        logger.warning(f"   ⚠️ No se generaron chunks")
        return None
    
    print(f"   ✅ Chunking completado: {len(chunks)} chunks generados", flush=True)
    logger.info(f"   ✅ Chunking completado: {len(chunks)} chunks generados")
    
    # Analizar estadísticas
    stats = analyze_chunk_statistics(chunks)
    print_chunk_statistics(stats)
    
    print(f"   🏷️ Preparando metadatos de chunks...", flush=True)
    logger.info(f"   🏷️ Preparando metadatos de chunks...")
    
    # Configuración de chunking
    chunking_config = {
        "method": "recursive_character",
        "target_chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "separators": SEPARATORS
    }
    
    # Crear estructura de chunks con metadata completa
    chunked_documents = []
    previous_structure = None
    for i, chunk in enumerate(chunks):
        # Construir metadata completa del chunk (pasando estructura previa para mantener contexto)
        chunk_metadata = metadata_builder.build_chunk_metadata(
            document_metadata=document_metadata,
            chunk_index=i,
            chunk_content=chunk,
            total_chunks=len(chunks),
            chunking_config=chunking_config,
            previous_structure=previous_structure
        )
        
        # Guardar estructura actual para el siguiente chunk
        previous_structure = {
            "level": chunk_metadata.get("level"),
            "level_name": chunk_metadata.get("level_name"),
            "chapter": chunk_metadata.get("chapter"),
            "chapter_title": chunk_metadata.get("chapter_title"),
            "section": chunk_metadata.get("section"),
            "section_title": chunk_metadata.get("section_title"),
            "subsection": chunk_metadata.get("subsection"),
            "subsection_title": chunk_metadata.get("subsection_title"),
            "article": chunk_metadata.get("article"),
            "article_title": chunk_metadata.get("article_title")
        }
        
        chunked_documents.append({
            "content": chunk,
            "metadata": chunk_metadata
        })
    
    print(f"   ✅ Metadatos preparados: {len(chunked_documents)} documentos", flush=True)
    print(f"   ✅ Metadatos preparados: {len(chunked_documents)} documentos", flush=True)
    logger.info(f"   ✅ Metadatos preparados: {len(chunked_documents)} documentos")
    return chunked_documents, stats, document_metadata


def generate_embeddings_batch(
    embedding_controller: EmbeddingControllerQdrant,
    documents: List[str]
) -> List:
    """Genera embeddings en lotes para mejor performance"""
    embeddings = []
    total_batches = (len(documents) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE
    total_docs = len(documents)
    
    print(f"   🔄 Generando embeddings en {total_batches} lotes de {EMBEDDING_BATCH_SIZE}...", flush=True)
    logger.info(f"   🔄 Generando embeddings en {total_batches} lotes de {EMBEDDING_BATCH_SIZE}...")
    
    processed_count = 0
    
    for batch_idx in range(0, len(documents), EMBEDDING_BATCH_SIZE):
        batch = documents[batch_idx:batch_idx + EMBEDDING_BATCH_SIZE]
        batch_num = batch_idx // EMBEDDING_BATCH_SIZE + 1
        
        print(f"      📦 Lote {batch_num}/{total_batches} ({len(batch)} documentos)...", flush=True)
        logger.info(f"      📦 Lote {batch_num}/{total_batches} ({len(batch)} documentos)...")
        
        batch_embeddings = []
        for i, doc in enumerate(batch):
            current_doc_num = batch_idx + i + 1
            try:
                print(f"         🔄 Generando embedding {current_doc_num}/{total_docs}...", end='\r', flush=True)
                embedding = embedding_controller.generate_embeddings(doc)
                
                if embedding is None or len(embedding) == 0:
                    print(f"         ⚠️ Embedding vacío para documento {current_doc_num}/{total_docs}", flush=True)
                    logger.warning(f"         ⚠️ Embedding vacío para documento {current_doc_num}")
                    continue
                
                batch_embeddings.append(embedding)
                processed_count += 1
                print(f"         ✅ Embedding {current_doc_num}/{total_docs} generado ({processed_count}/{total_docs} total)", flush=True)
                
            except Exception as e:
                print(f"         ❌ Error generando embedding {current_doc_num}/{total_docs}: {str(e)}", flush=True)
                logger.error(f"         ❌ Error generando embedding {current_doc_num}: {str(e)}")
                continue
        
        embeddings.extend(batch_embeddings)
        print(f"         ✅ Lote {batch_num} completado ({len(batch_embeddings)}/{len(batch)} exitosos)", flush=True)
        logger.info(f"         ✅ Lote {batch_num} completado ({len(batch_embeddings)}/{len(batch)} exitosos)")
    
    print(f"   ✅ Total embeddings generados: {len(embeddings)}/{len(documents)}", flush=True)
    logger.info(f"   ✅ Total embeddings generados: {len(embeddings)}/{len(documents)}")
    return embeddings


def save_chunks_and_embeddings(
    chunks: List[Dict],
    document_metadata: Dict,
    stats: Dict,
    chunking_config: Dict,
    metadata_builder: MetadataBuilder,
    document_id: str,
    sheet: str,
    check_duplicates: bool = False
) -> bool:
    """
    Guarda chunks, genera embeddings e ingesta en Qdrant con metadata normalizada.
    También guarda metadata intermedia (chunking) y final.
    """
    
    project_root = Path(__file__).parent.parent.parent
    
    logger.info(f"   📁 Creando directorios de salida...")
    logger.info(f"      - Chunking: output/chunking/{sheet}/")
    logger.info(f"      - Preview: output/embeddings_preview/{sheet}/")
    
    chunking_dir = project_root / "output" / "chunking" / sheet
    preview_dir = project_root / "output" / "embeddings_preview" / sheet
    
    chunking_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"   ✅ Directorios creados")
    logger.info(f"   💾 Guardando chunks en archivo JSON...")
    logger.info(f"      - Ubicación: {chunking_dir.name}/")
    # Estructura mejorada: document_id, sheet, chunking_statistics, chunking_configuration y chunks
    chunks_data = {
        "document_id": document_id,
        "sheet": sheet,
        "chunking_statistics": stats,
        "chunking_configuration": chunking_config,
        "chunks": chunks
    }
    
    chunks_file = chunking_dir / f"{document_id}_recursive_character_chunks.json"
    try:
        with open(chunks_file, 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        print(f"   ✅ Chunks guardados exitosamente en: output/chunking/{sheet}/{chunks_file.name}", flush=True)
        logger.info(f"   ✅ Chunks guardados exitosamente")
        logger.info(f"      - Archivo: {chunks_file.name}")
        logger.info(f"      - Ruta completa: {chunks_file}")
        logger.info(f"      - Total chunks: {len(chunks)}")
        logger.info(f"      - Tamaño: {chunks_file.stat().st_size / 1024 / 1024:.2f} MB")
    except Exception as e:
        logger.error(f"   ❌ Error guardando chunks: {str(e)}")
        return False
    
    # Guardar metadata intermedia (chunking)
    print(f"   💾 Guardando metadata intermedia (chunking)...", flush=True)
    logger.info(f"   💾 Guardando metadata intermedia (chunking)...")
    chunking_metadata_path = metadata_builder.save_chunking_metadata(
        document_id=document_id,
        sheet=sheet,
        document_metadata=document_metadata,
        chunking_stats=stats,
        chunking_config=chunking_config
    )
    if chunking_metadata_path:
        print(f"      ✅ Metadata guardada en: output/metadata/chunking/{sheet}/{chunking_metadata_path.name}", flush=True)
        logger.info(f"      - Ubicación: output/metadata/chunking/{sheet}/")
        logger.info(f"      - Archivo: {chunking_metadata_path.name}")
    
    logger.info(f"   🗄️ Inicializando controlador de embeddings...")
    logger.info(f"      - Colección: {COLLECTION_NAME}")
    logger.info(f"      - Modelo: {OLLAMA_MODEL}")
    logger.info(f"      - Reutilizando conexión a Qdrant...")
    try:
        # Reutilizar conexión (ya verificada antes)
        embedding_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
        logger.info(f"   ✅ Controlador inicializado correctamente")
        
        if check_duplicates:
            print(f"   🔍 Verificando si el documento '{document_id}' ya existe en la colección...", flush=True)
            logger.info(f"   🔍 Verificando si el documento '{document_id}' ya existe en la colección...")
            logger.info(f"      (Búsqueda por document_id único en campo 'document_id' de los metadatos)")
            print(f"      🔎 Buscando por document_id: '{document_id}' en campo 'document_id' de los metadatos...", flush=True)
            
            try:
                exists = embedding_controller.check_document_exists(document_id)
                if exists:
                    print(f"      ⚠️ Documento encontrado en la colección", flush=True)
                else:
                    print(f"      ✅ Documento no encontrado (procediendo con ingesta)", flush=True)
                
                if exists:
                    logger.warning(f"   ⚠️ El documento '{document_id}' ya existe en la colección")
                    logger.info(f"   💡 Opciones:")
                    logger.info(f"      - Eliminar el documento existente y reemplazarlo con el nuevo")
                    logger.info(f"      - Saltar este documento y mantener el existente")
                    
                    max_attempts = 3
                    user_input = None
                    for attempt in range(max_attempts):
                        try:
                            user_input = input(f"      ¿Eliminar y reemplazar el documento existente? (s/N): ").strip().lower()
                            if user_input in ['s', 'si', 'sí', 'y', 'yes', 'n', 'no', '']:
                                break
                            else:
                                logger.warning(f"      ⚠️ Respuesta inválida. Debe ser 's' o 'n' (o Enter para 'n')")
                        except (EOFError, KeyboardInterrupt):
                            user_input = "n"
                            logger.info(f"      ⏭️ Saltando documento (interrupción o sin entrada disponible)")
                            break
                    
                    if user_input in ['s', 'si', 'sí', 'y', 'yes']:
                        logger.info(f"      🗑️ Eliminando documento anterior '{document_id}'...")
                        delete_success = embedding_controller.delete_document(document_id)
                        if delete_success:
                            logger.info(f"      ✅ Documento anterior eliminado exitosamente")
                            logger.info(f"      ✅ Procediendo con el nuevo documento...")
                        else:
                            logger.error(f"      ❌ Error al eliminar documento anterior")
                            logger.info(f"      ⏭️ Saltando documento para evitar duplicados")
                            return True
                    else:
                        logger.info(f"      ⏭️ Saltando documento '{document_id}' (se mantiene el existente)")
                        return True
                else:
                    logger.info(f"   ✅ El documento '{document_id}' no existe en la colección")
                    logger.info(f"   ✅ Procediendo con la ingesta...")
                    
            except Exception as e:
                logger.error(f"   ❌ Error verificando duplicados para '{document_id}': {str(e)}")
                logger.warning(f"   ⚠️ Continuando sin verificación (puede haber duplicados)")
                # Continuar sin verificación en caso de error
            
    except Exception as e:
        logger.error(f"   ❌ Error inicializando controlador: {str(e)}")
        return False
    
    logger.info(f"   📋 Preparando documentos para embedding...")
    logger.info(f"      - Total documentos: {len(chunks)}")
    documents_for_embedding = [chunk["content"] for chunk in chunks]
    metadata_list = [chunk["metadata"] for chunk in chunks]
    
    logger.info(f"   🔄 Generando embeddings...")
    embeddings = generate_embeddings_batch(embedding_controller, documents_for_embedding)
    
    if len(embeddings) == 0:
        logger.error(f"   ❌ No se generó ningún embedding válido")
        return False
    
    if len(embeddings) < len(documents_for_embedding):
        logger.warning(f"   ⚠️ Solo se generaron {len(embeddings)}/{len(documents_for_embedding)} embeddings")
        metadata_list = metadata_list[:len(embeddings)]
        documents_for_embedding = documents_for_embedding[:len(embeddings)]
    
    print(f"\n🗃️ Almacenando embeddings en Qdrant...", flush=True)
    logger.info(f"   🗃️ Almacenando embeddings en Qdrant...")
    logger.info(f"      - Colección: {COLLECTION_NAME}")
    logger.info(f"      - Total embeddings: {len(embeddings)}")
    logger.info(f"      - Dimensión: {len(embeddings[0]) if embeddings else 0}")
    print(f"      - Colección: {COLLECTION_NAME}", flush=True)
    print(f"      - Total embeddings: {len(embeddings)}", flush=True)
    print(f"      - Dimensión: {len(embeddings[0]) if embeddings else 0}", flush=True)
    
    try:
        print(f"      - Iniciando guardado en Qdrant (los datos aparecerán en el dashboard cuando termine)...", flush=True)
        success = embedding_controller.store_embeddings(
            embeddings,
            documents_for_embedding,
            metadata_list
        )
        
        if success:
            print(f"\n   ✅ {len(embeddings)} embeddings guardados exitosamente en Qdrant", flush=True)
            print(f"      - Documento: {document_id}", flush=True)
            print(f"      - Chunks ingeridos: {len(embeddings)}", flush=True)
            print(f"      💡 Los datos ya están disponibles en el dashboard de Qdrant", flush=True)
            logger.info(f"   ✅ {len(embeddings)} embeddings guardados exitosamente en Qdrant")
            logger.info(f"      - Documento: {document_id}")
            logger.info(f"      - Chunks ingeridos: {len(embeddings)}")
        else:
            print(f"\n   ⚠️ Algunos embeddings no se guardaron correctamente", flush=True)
            logger.warning(f"   ⚠️ Algunos embeddings no se guardaron correctamente")
            
    except Exception as e:
        logger.error(f"   ❌ Error almacenando en Qdrant: {str(e)}")
        return False
    
    # Guardar metadata final
    print(f"   💾 Guardando metadata final...", flush=True)
    logger.info(f"   💾 Guardando metadata final...")
    final_metadata_path = metadata_builder.save_final_metadata(
        document_id=document_id,
        sheet=sheet,
        document_metadata=document_metadata,
        chunking_stats=stats,
        chunking_config=chunking_config,
        chunks=chunks
    )
    if final_metadata_path:
        print(f"      ✅ Metadata final guardada en: output/metadata/final/{sheet}/{final_metadata_path.name}", flush=True)
        logger.info(f"      - Ubicación: output/metadata/final/{sheet}/")
        logger.info(f"      - Archivo: {final_metadata_path.name}")
    
    print(f"   📊 Generando preview de embeddings...", flush=True)
    logger.info(f"   📊 Generando preview de embeddings...")
    
    # Preparar sample_embeddings: mostrar valores numéricos reales del vector
    # Tomar solo 3 embeddings y mostrar los valores numéricos del vector
    sample_embeddings_info = []
    if embeddings:
        sample_count = min(3, len(embeddings))
        for i in range(sample_count):
            embedding_vector = embeddings[i] if embeddings[i] else []
            sample_embeddings_info.append({
                "index": i,
                "dimension": len(embedding_vector),
                "preview": embedding_vector  # Valores numéricos reales del vector
            })
    
    # Preparar sample_chunks: información de los primeros 3 chunks
    sample_chunks_info = [
        {
            "index": i,
            "size": len(chunks[i]["content"]),
            "preview": chunks[i]["content"][:200] + "..." if len(chunks[i]["content"]) > 200 else chunks[i]["content"]
        }
        for i in range(min(3, len(chunks)))
    ]
    
    # Metadata relacionada con el proceso de embeddings
    embeddings_preview = {
        "document_id": document_id,
        "total_chunks": len(chunks),
        "total_embeddings": len(embeddings),
        "collection_name": COLLECTION_NAME,
        "embedding_model": OLLAMA_MODEL,
        "embedding_dimension": len(embeddings[0]) if embeddings else 0,
        "embedding_generated_at": datetime.now().isoformat(),
        "sample_embeddings": sample_embeddings_info,
        "sample_chunks": sample_chunks_info
    }
    
    preview_file = preview_dir / f"{document_id}_recursive_character_embeddings_preview.json"
    try:
        with open(preview_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings_preview, f, indent=2, ensure_ascii=False)
        print(f"      ✅ Preview guardado en: output/embeddings_preview/{sheet}/{preview_file.name}", flush=True)
        logger.info(f"   ✅ Preview de embeddings guardado")
        logger.info(f"      - Archivo: {preview_file.name}")
        logger.info(f"      - Ruta completa: {preview_file}")
        logger.info(f"      - Ubicación: output/embeddings_preview/{sheet}/")
    except Exception as e:
        print(f"      ⚠️ Error guardando preview: {str(e)}", flush=True)
        logger.warning(f"   ⚠️ Error guardando preview: {str(e)}")
    
    return success


def process_sheet(sheet_name: str, metadata_builder: MetadataBuilder, 
                check_duplicates: bool = False, 
                current_document_offset: int = 0,
                total_documents: int = 0) -> Dict:
    """
    Procesa todos los documentos de una pestaña.
    
    Args:
        sheet_name: Nombre de la pestaña
        metadata_builder: Instancia de MetadataBuilder
        check_duplicates: Si True, verifica duplicados antes de agregar
        current_document_offset: Offset para mostrar progreso global
        total_documents: Total de documentos para mostrar progreso global
    
    Returns:
        Dict con estadísticas de procesamiento
    """
    project_root = Path(__file__).parent.parent.parent
    processed_en_dir = project_root / "output" / "markdown" / "processed_en"
    sheet_dir = processed_en_dir / sheet_name
    
    if not sheet_dir.exists():
        logger.warning(f"⚠️ Directorio no existe: {sheet_dir}")
        return {
            "sheet": sheet_name,
            "processed": 0,
            "failed": 0,
            "total_chunks": 0,
            "total_embeddings": 0
        }
    
    # Buscar archivos markdown
    markdown_files = list(sheet_dir.glob("*.md"))
    
    if not markdown_files:
        logger.info(f"📁 No se encontraron archivos markdown en {sheet_name}")
        return {
            "sheet": sheet_name,
            "processed": 0,
            "failed": 0,
            "total_chunks": 0,
            "total_embeddings": 0
        }
    
    logger.info(f"📁 Encontrados {len(markdown_files)} archivos en {sheet_name}")
    print(f"\n📁 Encontrados {len(markdown_files)} archivos en {sheet_name}", flush=True)
    
    stats = {
        "sheet": sheet_name,
        "processed": 0,
        "failed": 0,
        "total_chunks": 0,
        "total_embeddings": 0
    }
    
    for i, markdown_file in enumerate(markdown_files, 1):
        document_id = extract_document_id_from_filename(markdown_file.name)
        
        # Calcular progreso global si se proporciona
        if total_documents > 0:
            global_doc_num = current_document_offset + i
            progress_text = f"{global_doc_num}/{total_documents}"
        else:
            progress_text = f"{i}/{len(markdown_files)}"
        
        # Mostrar progreso de forma clara y visible
        print(f"\n{'='*80}", flush=True)
        print(f"🔄 PROCESANDO DOCUMENTO {progress_text} [{i}/{len(markdown_files)} en {sheet_name}]: {document_id}", flush=True)
        print(f"{'='*80}", flush=True)
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 PROCESANDO DOCUMENTO {progress_text} [{i}/{len(markdown_files)} en {sheet_name}]: {document_id}")
        logger.info(f"{'='*80}")
        
        # Verificación temprana de duplicados (antes de procesar)
        if check_duplicates:
            logger.info(f"🔍 Verificación temprana de duplicados...")
            logger.info(f"   - Document ID: {document_id}")
            logger.info(f"   - Colección: {COLLECTION_NAME}")
            logger.info(f"   - Conectando a Qdrant...")
            try:
                # Inicializar controlador (solo mostrar mensaje una vez)
                embedding_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
                logger.info(f"   ✅ Conexión a Qdrant establecida")
                logger.info(f"   🔍 Buscando documento en la colección...")
                exists = embedding_controller.check_document_exists(document_id)
                
                if exists:
                    logger.warning(f"⚠️ El documento '{document_id}' ya existe en la colección")
                    logger.info(f"💡 Opciones:")
                    logger.info(f"   - Eliminar el documento existente y reemplazarlo")
                    logger.info(f"   - Saltar este documento y mantener el existente")
                    
                    max_attempts = 3
                    user_input = None
                    for attempt in range(max_attempts):
                        try:
                            user_input = input(f"   ¿Eliminar y reemplazar '{document_id}'? (s/N): ").strip().lower()
                            if user_input in ['s', 'si', 'sí', 'y', 'yes', 'n', 'no', '']:
                                break
                            else:
                                logger.warning(f"   ⚠️ Respuesta inválida. Debe ser 's' o 'n' (o Enter para 'n')")
                        except (EOFError, KeyboardInterrupt):
                            user_input = "n"
                            logger.info(f"   ⏭️ Saltando documento (interrupción o sin entrada disponible)")
                            break
                    
                    if user_input in ['s', 'si', 'sí', 'y', 'yes']:
                        logger.info(f"   🗑️ Eliminando documento anterior '{document_id}'...")
                        delete_success = embedding_controller.delete_document(document_id)
                        if delete_success:
                            logger.info(f"   ✅ Documento anterior eliminado exitosamente")
                        else:
                            logger.error(f"   ❌ Error al eliminar documento anterior")
                            logger.info(f"   ⏭️ Saltando documento para evitar duplicados")
                            stats["failed"] += 1
                            continue
                    else:
                        logger.info(f"   ⏭️ Saltando documento '{document_id}' (se mantiene el existente)")
                        stats["failed"] += 1
                        continue
                else:
                    logger.info(f"✅ El documento '{document_id}' no existe. Procediendo...")
            except Exception as e:
                logger.error(f"❌ Error en verificación temprana de duplicados: {str(e)}")
                logger.warning(f"⚠️ Continuando sin verificación (puede haber duplicados)")
        
        try:
            # FASE 1: Chunking con metadata completa
            print(f"📝 FASE 1: Recursive Character Chunking", flush=True)
            logger.info(f"📝 FASE 1: Recursive Character Chunking")
            logger.info(f"   - Archivo: {markdown_file.name}")
            logger.info(f"   - Document ID: {document_id}")
            logger.info(f"   - Pestaña: {sheet_name}")
            print(f"   - Archivo: {markdown_file.name}", flush=True)
            print(f"   - Document ID: {document_id}", flush=True)
            
            result = process_recursive_character_chunking(
                markdown_file,
                metadata_builder,
                document_id,
                sheet_name
            )
            
            if result is None:
                print(f"❌ Error en chunking de {document_id}", flush=True)
                logger.error(f"❌ Error en chunking de {document_id}")
                stats["failed"] += 1
                continue
            
            chunks, chunking_stats, document_metadata = result
            stats["total_chunks"] += len(chunks)
            print(f"✅ Chunking completado: {len(chunks)} chunks generados", flush=True)
            logger.info(f"✅ Chunking completado exitosamente")
            logger.info(f"   - Total chunks generados: {len(chunks)}")
            logger.info(f"   - Tamaño promedio: {chunking_stats['char_stats']['mean']:.0f} caracteres")
            logger.info("")
            
            # FASE 2: Guardado, embeddings e ingesta
            print(f"\n💾 FASE 2: Guardado, Embeddings e Ingesta", flush=True)
            logger.info(f"💾 FASE 2: Guardado, Embeddings e Ingesta")
            chunking_config = {
                "method": "recursive_character",
                "target_chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "separators": SEPARATORS
            }
            
            # No verificar duplicados aquí porque ya se hizo antes
            should_check = False
            
            success = save_chunks_and_embeddings(
                chunks,
                document_metadata,
                chunking_stats,
                chunking_config,
                metadata_builder,
                document_id,
                sheet_name,
                should_check
            )
            
            if success:
                logger.info(f"🎉 {document_id} procesado exitosamente")
                stats["processed"] += 1
                stats["total_embeddings"] += len(chunks)
            else:
                logger.warning(f"⚠️ {document_id} procesado con advertencias")
                stats["processed"] += 1
                
        except Exception as e:
            logger.error(f"❌ Error inesperado procesando {document_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            stats["failed"] += 1
        
        logger.info("")
    
    return stats


def archive_processed_markdowns(project_root: Path, sheets: List[str]) -> Dict:
    """
    Archiva los archivos markdown de processed_es y processed_en a carpetas archivadas
    con sufijos _ES y _EN respectivamente, dejando las carpetas originales vacías.
    
    Estructura resultante:
    - output/markdown/archived/{pestaña}_ES/{document_id}.md
    - output/markdown/archived/{pestaña}_EN/{document_id}.md
    
    Args:
        project_root: Raíz del proyecto
        sheets: Lista de pestañas procesadas
    
    Returns:
        Dict con estadísticas de archivo
    """
    logger.info("")
    logger.info("="*80)
    logger.info("📦 ARCHIVANDO MARKDOWNS PROCESADOS")
    logger.info("="*80)
    
    processed_es_dir = project_root / "output" / "markdown" / "processed_es"
    processed_en_dir = project_root / "output" / "markdown" / "processed_en"
    archived_dir = project_root / "output" / "markdown" / "archived"
    
    archived_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {
        "archived_es": 0,
        "archived_en": 0,
        "failed_es": 0,
        "failed_en": 0,
        "sheets_processed": 0
    }
    
    for sheet in sheets:
        logger.info(f"\n📁 Procesando pestaña: {sheet}")
        
        # Procesar archivos en español
        es_sheet_dir = processed_es_dir / sheet
        es_archived_dir = archived_dir / f"{sheet}_ES"
        
        if es_sheet_dir.exists():
            es_archived_dir.mkdir(parents=True, exist_ok=True)
            es_files = list(es_sheet_dir.glob("*.md"))
            
            if es_files:
                logger.info(f"   📄 Archivos en español: {len(es_files)}")
                for md_file in es_files:
                    try:
                        dest_file = es_archived_dir / md_file.name
                        md_file.rename(dest_file)
                        stats["archived_es"] += 1
                        logger.debug(f"      ✅ Movido: {md_file.name}")
                    except Exception as e:
                        logger.error(f"      ❌ Error moviendo {md_file.name}: {e}")
                        stats["failed_es"] += 1
                
                # Eliminar carpeta vacía si quedó sin archivos
                try:
                    if not list(es_sheet_dir.glob("*")):
                        es_sheet_dir.rmdir()
                        logger.debug(f"      🗑️  Carpeta vacía eliminada: {es_sheet_dir.name}")
                except Exception as e:
                    logger.debug(f"      ⚠️  No se pudo eliminar carpeta vacía: {e}")
        
        # Procesar archivos en inglés
        en_sheet_dir = processed_en_dir / sheet
        en_archived_dir = archived_dir / f"{sheet}_EN"
        
        if en_sheet_dir.exists():
            en_archived_dir.mkdir(parents=True, exist_ok=True)
            en_files = list(en_sheet_dir.glob("*.md"))
            
            if en_files:
                logger.info(f"   📄 Archivos en inglés: {len(en_files)}")
                for md_file in en_files:
                    try:
                        dest_file = en_archived_dir / md_file.name
                        md_file.rename(dest_file)
                        stats["archived_en"] += 1
                        logger.debug(f"      ✅ Movido: {md_file.name}")
                    except Exception as e:
                        logger.error(f"      ❌ Error moviendo {md_file.name}: {e}")
                        stats["failed_en"] += 1
                
                # Eliminar carpeta vacía si quedó sin archivos
                try:
                    if not list(en_sheet_dir.glob("*")):
                        en_sheet_dir.rmdir()
                        logger.debug(f"      🗑️  Carpeta vacía eliminada: {en_sheet_dir.name}")
                except Exception as e:
                    logger.debug(f"      ⚠️  No se pudo eliminar carpeta vacía: {e}")
        
        if (es_sheet_dir.exists() and list(es_sheet_dir.glob("*.md"))) or \
           (en_sheet_dir.exists() and list(en_sheet_dir.glob("*.md"))):
            stats["sheets_processed"] += 1
    
    logger.info("")
    logger.info("📊 RESUMEN DE ARCHIVADO:")
    logger.info(f"   ✅ Archivos en español archivados: {stats['archived_es']}")
    logger.info(f"   ✅ Archivos en inglés archivados: {stats['archived_en']}")
    if stats["failed_es"] > 0 or stats["failed_en"] > 0:
        logger.warning(f"   ❌ Archivos con errores: {stats['failed_es']} ES, {stats['failed_en']} EN")
    logger.info(f"   📁 Ubicación: {archived_dir.relative_to(project_root)}")
    
    return stats


def main():
    """Función principal"""
    logger.info("="*80)
    logger.info("🚀 PIPELINE DE INGESTA COMPLETO")
    logger.info("="*80)
    logger.info(f"📋 Lee archivos markdown desde processed_en/")
    logger.info(f"   - Chunk size: {CHUNK_SIZE} caracteres")
    logger.info(f"   - Chunk overlap: {CHUNK_OVERLAP} caracteres")
    logger.info(f"   - Método: recursive_character")
    logger.info(f"   - Colección Qdrant: {COLLECTION_NAME}")
    logger.info(f"   - Modelo embeddings: {OLLAMA_MODEL}")
    logger.info("="*80)
    logger.info("")
    
    # NO verificar Ollama aquí - se hará después de seleccionar la opción
    logger.info("🔍 Verificando conexión con Qdrant...")
    logger.info(f"   - URL: http://localhost:6333")
    logger.info(f"   - Colección: {COLLECTION_NAME}")
    
    # Verificar conexión con Qdrant antes de continuar (solo una vez)
    try:
        test_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
        logger.info(f"   ✅ Conexión a Qdrant establecida correctamente")
        logger.info(f"   ✅ Colección '{COLLECTION_NAME}' verificada")
        del test_controller  # Liberar conexión
    except Exception as e:
        logger.error(f"   ❌ Error conectando a Qdrant: {str(e)}")
        logger.error("   💡 Asegúrate de que Qdrant esté ejecutándose:")
        logger.error("      - Verifica: curl http://localhost:6333/collections")
        logger.error("      - O ejecuta: ./rag_system.sh start qdrant")
        return
    
    logger.info("")
    logger.info("📂 Buscando archivos markdown...")
    
    project_root = Path(__file__).parent.parent.parent
    processed_en_dir = project_root / "output" / "markdown" / "processed_en"
    
    if not processed_en_dir.exists():
        logger.error(f"❌ No se encontró el directorio: {processed_en_dir}")
        logger.error("   Ejecuta primero el pipeline de traducción")
        return
    
    # Buscar pestañas (subdirectorios)
    sheets = [d.name for d in processed_en_dir.iterdir() if d.is_dir()]
    
    if not sheets:
        logger.error(f"❌ No se encontraron pestañas en {processed_en_dir}")
        return
    
    logger.info(f"✅ Pestañas encontradas: {len(sheets)}")
    for sheet in sheets:
        logger.info(f"   📄 {sheet}")
    logger.info("")
    
    # Parsear argumentos de línea de comandos (opcionales)
    parser = argparse.ArgumentParser(
        description='Pipeline de Ingesta - Chunking y Embeddings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python src/ingestion/ingest_pipeline.py              # Modo interactivo
  python src/ingestion/ingest_pipeline.py --option 2   # Opción 2 directamente (recomendado)
  python src/ingestion/ingest_pipeline.py -o 1        # Opción 1 directamente
        """
    )
    parser.add_argument(
        '--option', '-o',
        type=str,
        choices=['1', '2'],
        default=None,
        help='Opción de procesamiento: 1=Agregar sin verificar, 2=Verificar duplicados (recomendado). Si no se especifica, se pedirá interactivamente.'
    )
    args = parser.parse_args()
    
    logger.info("🗄️ CONFIGURACIÓN DE COLECCIÓN QDRANT")
    logger.info("-"*60)
    logger.info(f"Colección: {COLLECTION_NAME}")
    logger.info("")
    logger.info("Opciones:")
    logger.info("  1. Agregar a colección existente (sin verificar duplicados)")
    logger.info("  2. Verificar duplicados antes de agregar (recomendado)")
    logger.info("     - Busca por document_id único")
    logger.info("     - Pregunta antes de reemplazar documentos existentes")
    logger.info("")
    
    # Determinar opción
    option = None
    
    # Si se proporcionó --option, usarlo directamente
    if args.option:
        option = args.option
        logger.info(f"   ✅ Opción seleccionada desde argumento: {option}")
    # Si no, pedir input interactivo
    else:
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                option = input("Selecciona una opción (1/2) [default=1]: ").strip()
                if not option:
                    option = "1"
                if option in ['1', '2']:
                    break
                else:
                    logger.warning(f"   ⚠️ Opción inválida: '{option}'. Debe ser 1 o 2.")
                    if attempt < max_attempts - 1:
                        logger.info("   💡 Intenta nuevamente...")
            except (EOFError, KeyboardInterrupt):
                option = "1"
                logger.info("   ℹ️ Usando opción por defecto: 1 (Agregar a colección existente)")
                break
        
        if option not in ['1', '2']:
            option = "1"
            logger.warning("   ⚠️ Opción inválida después de múltiples intentos. Usando opción por defecto: 1")
    
    if option == '2':
        check_duplicates = True
        logger.info("   ✅ Se verificarán duplicados por document_id antes de agregar")
        logger.info("   ✅ Se preguntará antes de reemplazar documentos existentes")
    else:
        check_duplicates = False
        logger.info("   ℹ️ Se agregará a la colección existente sin verificar duplicados")
    
    logger.info("")
    logger.info("="*80)
    logger.info("🔍 INICIANDO VERIFICACIONES PREVIAS")
    logger.info("="*80)
    logger.info("")
    
    # Verificar Ollama primero
    logger.info("📡 PASO 1: Verificando conexión con Ollama...")
    sys.stdout.flush()  # Forzar salida inmediata
    if not check_ollama_connection():
        logger.error("\n❌ No se puede continuar sin conexión a Ollama")
        return
    
    logger.info("")
    logger.info("🔍 Verificando conexión con Qdrant...")
    logger.info(f"   - URL: http://localhost:6333")
    logger.info(f"   - Colección: {COLLECTION_NAME}")
    
    # Verificar conexión con Qdrant antes de continuar (solo una vez)
    try:
        test_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
        logger.info(f"   ✅ Conexión a Qdrant establecida correctamente")
        logger.info(f"   ✅ Colección '{COLLECTION_NAME}' verificada")
        del test_controller  # Liberar conexión
    except Exception as e:
        logger.error(f"   ❌ Error conectando a Qdrant: {str(e)}")
        logger.error("   💡 Asegúrate de que Qdrant esté ejecutándose:")
        logger.error("      - Verifica: curl http://localhost:6333/collections")
        logger.error("      - O ejecuta: ./rag_system.sh start qdrant")
        return
    
    logger.info("")
    logger.info("📂 Buscando archivos markdown...")
    
    project_root = Path(__file__).parent.parent.parent
    processed_en_dir = project_root / "output" / "markdown" / "processed_en"
    
    if not processed_en_dir.exists():
        logger.error(f"❌ No se encontró el directorio: {processed_en_dir}")
        logger.error("   Ejecuta primero el pipeline de traducción")
        return
    
    # Buscar pestañas (subdirectorios)
    sheets = [d.name for d in processed_en_dir.iterdir() if d.is_dir()]
    
    if not sheets:
        logger.error(f"❌ No se encontraron pestañas en {processed_en_dir}")
        return
    
    logger.info(f"✅ Pestañas encontradas: {len(sheets)}")
    for sheet in sheets:
        logger.info(f"   📄 {sheet}")
    logger.info("")
    
    # Inicializar MetadataBuilder
    logger.info("")
    logger.info("🏗️ PASO 4: Inicializando MetadataBuilder...")
    logger.info("   - Cargando catálogo de metadata...")
    try:
        metadata_builder = MetadataBuilder(project_root)
        logger.info("   ✅ MetadataBuilder inicializado correctamente")
    except Exception as e:
        logger.error(f"   ❌ Error inicializando MetadataBuilder: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Procesar cada pestaña
    logger.info("")
    logger.info("="*80)
    logger.info("🚀 PASO 5: INICIANDO PROCESAMIENTO DE DOCUMENTOS")
    logger.info("="*80)
    logger.info("")
    
    all_stats = []
    for idx, sheet in enumerate(sheets, 1):
        logger.info("")
        logger.info(f"📊 PROCESANDO PESTAÑA {idx}/{len(sheets)}: {sheet}")
        logger.info("="*80)
        
        stats = process_sheet(sheet, metadata_builder, check_duplicates)
        all_stats.append(stats)
        
        logger.info("")
        logger.info(f"✅ Pestaña '{sheet}' procesada")
        logger.info(f"   - Documentos procesados: {stats['processed']}")
        logger.info(f"   - Documentos fallidos: {stats['failed']}")
        logger.info(f"   - Total chunks: {stats['total_chunks']}")
        logger.info(f"   - Total embeddings: {stats['total_embeddings']}")
    
    # Resumen final
    logger.info("")
    logger.info("📊 RESUMEN FINAL")
    logger.info("="*60)
    
    total_processed = sum(s["processed"] for s in all_stats)
    total_failed = sum(s["failed"] for s in all_stats)
    total_chunks = sum(s["total_chunks"] for s in all_stats)
    total_embeddings = sum(s["total_embeddings"] for s in all_stats)
    
    logger.info(f"✅ Documentos procesados exitosamente: {total_processed}")
    logger.info(f"❌ Documentos con errores: {total_failed}")
    logger.info(f"📦 Total de chunks generados: {total_chunks}")
    logger.info(f"🔢 Total de embeddings creados: {total_embeddings}")
    
    for stats in all_stats:
        logger.info(f"   📄 {stats['sheet']}: {stats['processed']} procesados, {stats['failed']} fallidos")
    
    if total_processed > 0:
        try:
            logger.info(f"\n📊 ESTADÍSTICAS DE LA COLECCIÓN QDRANT")
            logger.info("-"*60)
            embedding_controller = EmbeddingControllerQdrant(qdrant_collection=COLLECTION_NAME)
            collection_stats = embedding_controller.get_collection_stats()
            logger.info(f"Total de chunks en colección: {collection_stats['total_chunks']}")
            logger.info(f"Documentos únicos: {collection_stats['unique_documents']}")
            logger.info(f"Documentos:")
            for doc_name in sorted(collection_stats['document_names']):
                logger.info(f"   - {doc_name}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron obtener estadísticas: {e}")
    
    if total_processed > 0:
        logger.info(f"\n🎉 Pipeline de ingesta completado!")
        logger.info(f"📁 Revisa los resultados en:")
        logger.info(f"   - output/chunking/<pestaña>/")
        logger.info(f"   - output/embeddings_preview/<pestaña>/")
        logger.info(f"   - output/metadata/chunking/")
        logger.info(f"   - output/metadata/final/")
        logger.info(f"   - Base de conocimiento Qdrant: {COLLECTION_NAME}")
        
        # Archivar markdowns procesados
        logger.info("")
        archive_stats = archive_processed_markdowns(project_root, sheets)
        
        if archive_stats["archived_es"] > 0 or archive_stats["archived_en"] > 0:
            logger.info("")
            logger.info("✅ Markdowns archivados exitosamente")
            logger.info(f"   📁 Ubicación: output/markdown/archived/")
            logger.info(f"   📂 Estructura: archived/<pestaña>_ES/ y archived/<pestaña>_EN/")
            logger.info(f"   🗑️  Carpetas processed_es/ y processed_en/ quedaron vacías para futuros procesamientos")
    
    if total_failed > 0:
        logger.warning(f"\n⚠️ Algunos documentos tuvieron problemas. Revisa los errores arriba.")


if __name__ == "__main__":
    main()

