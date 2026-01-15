#!/usr/bin/env python3
"""
Script de Validación: Compara chunks en Qdrant vs embeddings_preview

Este script valida la integridad de los datos comparando:
- Chunks almacenados en Qdrant (colección normativa-asistente-kb)
- Chunks guardados en output/embeddings_preview/

Para cada document_id, verifica:
1. Que el número de chunks coincida
2. Que todos los chunk_index estén presentes
3. Que no haya chunks faltantes o duplicados

Uso:
    python src/validation/validate_qdrant_chunks.py
    python src/validation/validate_qdrant_chunks.py --document-id NFPA_03_2024_ED_2024
    python src/validation/validate_qdrant_chunks.py --collection normativa-asistente-kb
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.embeddings.embedding_qdrant import EmbeddingControllerQdrant
from qdrant_client.models import Filter, FieldCondition, MatchValue

load_dotenv()

# Configuración
DEFAULT_COLLECTION = os.getenv("QDRANT_COLLECTION_NAME", "normativa-asistente-kb")
EMBEDDINGS_PREVIEW_DIR = project_root / "output" / "embeddings_preview"


def load_embeddings_preview(document_id: str) -> Dict:
    """
    Carga el archivo de embeddings_preview para un document_id.
    
    Args:
        document_id: ID del documento
        
    Returns:
        Dict con los datos del preview o None si no existe
    """
    # Buscar en todos los subdirectorios
    for sheet_dir in EMBEDDINGS_PREVIEW_DIR.iterdir():
        if not sheet_dir.is_dir():
            continue
            
        preview_file = sheet_dir / f"{document_id}_recursive_character_embeddings_preview.json"
        if preview_file.exists():
            try:
                with open(preview_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"   ⚠️ Error leyendo {preview_file}: {e}")
                return None
    
    return None


def get_qdrant_chunks(embedding_controller: EmbeddingControllerQdrant, document_id: str) -> List[Dict]:
    """
    Obtiene todos los chunks de un documento desde Qdrant.
    
    Args:
        embedding_controller: Controlador de embeddings
        document_id: ID del documento
        
    Returns:
        Lista de chunks con sus metadatos
    """
    chunks = []
    offset = None
    
    while True:
        try:
            scroll_result = embedding_controller.qdrant_client.scroll(
                collection_name=embedding_controller.qdrant_collection,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=100,
                offset=offset,
                with_payload=True
            )
            
            points, next_offset = scroll_result
            
            if not points:
                break
                
            for point in points:
                payload = point.payload
                chunks.append({
                    'id': str(point.id),
                    'chunk_index': payload.get('chunk_index'),
                    'document_id': payload.get('document_id'),
                    'text': payload.get('text', '')[:100] + '...' if payload.get('text') else '',
                })
            
            if next_offset is None:
                break
                
            offset = next_offset
            
        except Exception as e:
            print(f"   ❌ Error obteniendo chunks de Qdrant: {e}")
            break
    
    return chunks


def find_all_document_ids() -> List[str]:
    """
    Encuentra todos los document_ids en embeddings_preview.
    
    Returns:
        Lista de document_ids encontrados
    """
    document_ids = set()
    
    if not EMBEDDINGS_PREVIEW_DIR.exists():
        return []
    
    for sheet_dir in EMBEDDINGS_PREVIEW_DIR.iterdir():
        if not sheet_dir.is_dir():
            continue
            
        for preview_file in sheet_dir.glob("*_recursive_character_embeddings_preview.json"):
            document_id = preview_file.stem.replace("_recursive_character_embeddings_preview", "")
            document_ids.add(document_id)
    
    return sorted(list(document_ids))


def validate_document(
    embedding_controller: EmbeddingControllerQdrant,
    document_id: str,
    verbose: bool = False
) -> Tuple[bool, Dict]:
    """
    Valida un documento específico.
    
    Args:
        embedding_controller: Controlador de embeddings
        document_id: ID del documento a validar
        verbose: Si True, muestra información detallada
        
    Returns:
        Tuple (is_valid, stats)
    """
    print(f"\n{'='*70}")
    print(f"📄 Validando: {document_id}")
    print(f"{'='*70}")
    
    # Cargar datos de embeddings_preview
    preview_data = load_embeddings_preview(document_id)
    if not preview_data:
        print(f"   ❌ No se encontró archivo de embeddings_preview para {document_id}")
        return False, {"error": "preview_not_found"}
    
    expected_chunks = preview_data.get('total_chunks', 0)
    print(f"   📊 Chunks esperados (preview): {expected_chunks}")
    
    # Obtener chunks de Qdrant
    qdrant_chunks = get_qdrant_chunks(embedding_controller, document_id)
    actual_chunks = len(qdrant_chunks)
    print(f"   📊 Chunks en Qdrant: {actual_chunks}")
    
    # Comparar
    is_valid = True
    issues = []
    
    if expected_chunks != actual_chunks:
        is_valid = False
        diff = expected_chunks - actual_chunks
        if diff > 0:
            issues.append(f"Faltan {diff} chunks en Qdrant")
        else:
            issues.append(f"Hay {abs(diff)} chunks extra en Qdrant")
    
    # Verificar chunk_index
    if qdrant_chunks:
        qdrant_indices = {chunk['chunk_index'] for chunk in qdrant_chunks if chunk['chunk_index'] is not None}
        expected_indices = set(range(expected_chunks))
        
        missing_indices = expected_indices - qdrant_indices
        extra_indices = qdrant_indices - expected_indices
        
        if missing_indices:
            is_valid = False
            issues.append(f"Faltan chunk_index: {sorted(list(missing_indices))[:10]}{'...' if len(missing_indices) > 10 else ''}")
        
        if extra_indices:
            is_valid = False
            issues.append(f"Chunk_index extra: {sorted(list(extra_indices))[:10]}{'...' if len(extra_indices) > 10 else ''}")
        
        if verbose and qdrant_indices:
            print(f"   📋 Chunk indices en Qdrant: {sorted(list(qdrant_indices))[:20]}{'...' if len(qdrant_indices) > 20 else ''}")
    
    # Resultado
    if is_valid:
        print(f"   ✅ Documento válido: {actual_chunks} chunks coinciden")
    else:
        print(f"   ❌ Documento con problemas:")
        for issue in issues:
            print(f"      - {issue}")
    
    stats = {
        "document_id": document_id,
        "expected_chunks": expected_chunks,
        "actual_chunks": actual_chunks,
        "is_valid": is_valid,
        "issues": issues
    }
    
    return is_valid, stats


def main():
    parser = argparse.ArgumentParser(
        description="Valida integridad de chunks entre Qdrant y embeddings_preview"
    )
    parser.add_argument(
        "--document-id",
        type=str,
        help="ID del documento específico a validar (opcional)"
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=DEFAULT_COLLECTION,
        help=f"Nombre de la colección Qdrant (default: {DEFAULT_COLLECTION})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostrar información detallada"
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("🔍 VALIDACIÓN DE CHUNKS: QDRANT vs EMBEDDINGS_PREVIEW")
    print("="*70)
    print(f"📦 Colección: {args.collection}")
    print(f"📁 Preview dir: {EMBEDDINGS_PREVIEW_DIR}")
    print("="*70)
    
    # Inicializar controlador
    try:
        embedding_controller = EmbeddingControllerQdrant(qdrant_collection=args.collection)
        print(f"✅ Conectado a Qdrant")
    except Exception as e:
        print(f"❌ Error conectando a Qdrant: {e}")
        return 1
    
    # Validar documento específico o todos
    if args.document_id:
        document_ids = [args.document_id]
    else:
        document_ids = find_all_document_ids()
        print(f"\n📋 Documentos encontrados: {len(document_ids)}")
    
    if not document_ids:
        print("❌ No se encontraron documentos para validar")
        return 1
    
    # Validar cada documento
    results = []
    for document_id in document_ids:
        is_valid, stats = validate_document(
            embedding_controller,
            document_id,
            verbose=args.verbose
        )
        results.append(stats)
    
    # Resumen
    print(f"\n{'='*70}")
    print("📊 RESUMEN DE VALIDACIÓN")
    print(f"{'='*70}")
    
    valid_count = sum(1 for r in results if r.get('is_valid', False))
    invalid_count = len(results) - valid_count
    
    print(f"✅ Documentos válidos: {valid_count}/{len(results)}")
    print(f"❌ Documentos con problemas: {invalid_count}/{len(results)}")
    
    if invalid_count > 0:
        print(f"\n⚠️ Documentos con problemas:")
        for result in results:
            if not result.get('is_valid', False):
                print(f"   - {result['document_id']}: {', '.join(result.get('issues', []))}")
    
    # Estadísticas totales
    total_expected = sum(r.get('expected_chunks', 0) for r in results)
    total_actual = sum(r.get('actual_chunks', 0) for r in results)
    
    print(f"\n📊 Estadísticas Totales:")
    print(f"   Chunks esperados (preview): {total_expected:,}")
    print(f"   Chunks en Qdrant: {total_actual:,}")
    print(f"   Diferencia: {total_expected - total_actual:,}")
    
    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

