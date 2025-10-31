#!/usr/bin/env python3
"""
Script para validar el estado de la ingesta de documentos.
Compara los chunks esperados (según los archivos JSON) con los chunks 
realmente almacenados en Qdrant para cada document_id.
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Cargar variables de entorno
load_dotenv()

# Configuración
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
DEFAULT_COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_NAME", "")  # Fallback si no está en JSON
EMBEDDINGS_PREVIEW_DIR = Path("output/embeddings_preview/recursive_character")
OUTPUT_DIR = Path("output/analysis")


def load_json_files(preview_dir: Path) -> List[Dict]:
    """
    Carga todos los archivos JSON de embeddings preview
    
    Args:
        preview_dir: Directorio con los archivos JSON
        
    Returns:
        Lista de diccionarios con la información de cada archivo
    """
    json_files = list(preview_dir.glob("*_recursive_character_embeddings_preview.json"))
    documents_info = []
    
    print(f"📁 Encontrados {len(json_files)} archivos JSON")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            document_id = data.get("document_id", "")
            total_chunks_expected = data.get("statistics", {}).get("total_chunks", 0)
            collection_name = data.get("collection_name", "") or DEFAULT_COLLECTION_NAME
            book_title = data.get("book_title", "")
            
            if not document_id:
                print(f"⚠️ Archivo {json_file.name} no tiene document_id, omitiendo")
                continue
            
            if not collection_name:
                print(f"⚠️ Archivo {json_file.name} no tiene collection_name y no hay fallback definido, omitiendo")
                print(f"   💡 Define QDRANT_COLLECTION_NAME en .env o verifica el JSON")
                continue
                
            documents_info.append({
                "document_id": document_id,
                "total_chunks_expected": total_chunks_expected,
                "collection_name": collection_name,
                "book_title": book_title,
                "json_file": json_file.name
            })
            
        except Exception as e:
            print(f"❌ Error leyendo {json_file.name}: {e}")
            continue
    
    return documents_info


def count_chunks_in_qdrant(qdrant_client: QdrantClient, collection_name: str, document_id: str) -> int:
    """
    Cuenta los chunks almacenados en Qdrant para un document_id específico
    
    Args:
        qdrant_client: Cliente de Qdrant
        collection_name: Nombre de la colección
        document_id: ID del documento a contar
        
    Returns:
        Número de chunks encontrados
    """
    try:
        # Usar scroll con filtro para contar todos los chunks del document_id
        total_count = 0
        offset = None
        
        while True:
            scroll_result = qdrant_client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id)
                        )
                    ]
                ),
                limit=1000,
                offset=offset
            )
            
            points, next_offset = scroll_result
            
            if not points:
                break
                
            total_count += len(points)
            
            if next_offset is None:
                break
                
            offset = next_offset
        
        return total_count
        
    except Exception as e:
        print(f"   ⚠️ Error contando chunks para {document_id}: {e}")
        return 0


def validate_ingestion_status(documents_info: List[Dict], qdrant_url: str) -> List[Dict]:
    """
    Valida el estado de ingesta para cada documento
    
    Args:
        documents_info: Lista con información de documentos
        qdrant_url: URL del servidor Qdrant
        
    Returns:
        Lista con resultados de validación
    """
    results = []
    qdrant_client = QdrantClient(url=qdrant_url)
    
    print(f"\n🔍 Validando estado de ingesta para {len(documents_info)} documentos...")
    print("=" * 80)
    
    for i, doc_info in enumerate(documents_info, 1):
        document_id = doc_info["document_id"]
        collection_name = doc_info["collection_name"]
        expected_chunks = doc_info["total_chunks_expected"]
        
        print(f"\n[{i}/{len(documents_info)}] Validando: {document_id}")
        print(f"   📦 Esperados: {expected_chunks} chunks")
        print(f"   🗄️ Colección: {collection_name}")
        
        # Verificar si la colección existe
        try:
            collections = qdrant_client.get_collections().collections
            collection_exists = any(col.name == collection_name for col in collections)
            
            if not collection_exists:
                print(f"   ⚠️ Colección '{collection_name}' no existe en Qdrant")
                actual_chunks = 0
            else:
                actual_chunks = count_chunks_in_qdrant(qdrant_client, collection_name, document_id)
                print(f"   ✅ Encontrados: {actual_chunks} chunks")
        except Exception as e:
            print(f"   ❌ Error accediendo a Qdrant: {e}")
            actual_chunks = 0
        
        diferencia = expected_chunks - actual_chunks
        
        status = "✅ OK" if diferencia == 0 else "⚠️ DIFERENCIA"
        if diferencia > 0:
            status = "❌ FALTANTES"
        elif diferencia < 0:
            status = "⚠️ EXTRA"
        
        result = {
            "document_id": document_id,
            "book_title": doc_info["book_title"],
            "collection_name": collection_name,
            "total_chunks_esperados": expected_chunks,
            "total_chunks_en_qdrant": actual_chunks,
            "diferencia": diferencia,
            "estado": status
        }
        
        results.append(result)
        
        if diferencia != 0:
            print(f"   {status}: {abs(diferencia)} chunks de diferencia")
        else:
            print(f"   {status}")
    
    return results


def generate_excel_report(results: List[Dict], output_dir: Path) -> str:
    """
    Genera un reporte Excel con los resultados de validación
    
    Args:
        results: Lista con resultados de validación
        output_dir: Directorio de salida
        
    Returns:
        Ruta del archivo Excel generado
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = output_dir / f"ingestion_validation_report_{timestamp}.xlsx"
    
    # Crear DataFrame
    df = pd.DataFrame(results)
    
    # Reordenar columnas
    column_order = [
        "document_id",
        "book_title",
        "collection_name",
        "total_chunks_esperados",
        "total_chunks_en_qdrant",
        "diferencia",
        "estado"
    ]
    df = df[column_order]
    
    # Renombrar columnas para mejor legibilidad
    df.columns = [
        "Document ID",
        "Título",
        "Colección",
        "Total Chunks Esperados",
        "Total Chunks en Qdrant",
        "Diferencia",
        "Estado"
    ]
    
    # Ordenar por diferencia (mayores diferencias primero)
    df = df.sort_values("Diferencia", ascending=False, key=abs)
    
    # Crear Excel con múltiples hojas
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Hoja completa
        df.to_excel(writer, sheet_name='Validación Completa', index=False)
        
        # Hoja solo con problemas
        df_problemas = df[df['Diferencia'] != 0]
        if len(df_problemas) > 0:
            df_problemas.to_excel(writer, sheet_name='Documentos con Problemas', index=False)
        
        # Hoja resumen
        resumen_data = {
            'Métrica': [
                'Total Documentos',
                'Documentos OK',
                'Documentos con Diferencia',
                'Documentos con Faltantes',
                'Documentos con Extra',
                'Total Chunks Esperados',
                'Total Chunks en Qdrant',
                'Diferencia Total'
            ],
            'Valor': [
                len(df),
                len(df[df['Diferencia'] == 0]),
                len(df[df['Diferencia'] != 0]),
                len(df[df['Diferencia'] > 0]),
                len(df[df['Diferencia'] < 0]),
                df['Total Chunks Esperados'].sum(),
                df['Total Chunks en Qdrant'].sum(),
                df['Diferencia'].sum()
            ]
        }
        df_resumen = pd.DataFrame(resumen_data)
        df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
    
    print(f"\n✅ Reporte Excel generado: {excel_file}")
    return str(excel_file)


def main():
    """Función principal"""
    print("=" * 80)
    print("📊 VALIDACIÓN DE ESTADO DE INGESTA")
    print("=" * 80)
    
    # Verificar que existe el directorio de previews
    preview_dir = Path(__file__).parent.parent / EMBEDDINGS_PREVIEW_DIR
    if not preview_dir.exists():
        print(f"❌ Error: No se encuentra el directorio {preview_dir}")
        print("   Asegúrate de haber ejecutado la ingesta de documentos")
        sys.exit(1)
    
    # Cargar información de archivos JSON
    print(f"\n📁 Leyendo archivos JSON de: {preview_dir}")
    documents_info = load_json_files(preview_dir)
    
    if not documents_info:
        print("❌ No se encontraron documentos para validar")
        sys.exit(1)
    
    # Validar ingesta
    results = validate_ingestion_status(documents_info, QDRANT_URL)
    
    # Generar reporte Excel
    output_dir = Path(__file__).parent.parent / OUTPUT_DIR
    excel_file = generate_excel_report(results, output_dir)
    
    # Resumen final
    print("\n" + "=" * 80)
    print("📊 RESUMEN FINAL")
    print("=" * 80)
    
    total_docs = len(results)
    docs_ok = len([r for r in results if r["diferencia"] == 0])
    docs_con_problemas = total_docs - docs_ok
    
    print(f"✅ Documentos OK: {docs_ok}/{total_docs}")
    print(f"⚠️ Documentos con problemas: {docs_con_problemas}/{total_docs}")
    
    if docs_con_problemas > 0:
        total_esperados = sum(r["total_chunks_esperados"] for r in results)
        total_qdrant = sum(r["total_chunks_en_qdrant"] for r in results)
        print(f"📦 Total chunks esperados: {total_esperados}")
        print(f"📦 Total chunks en Qdrant: {total_qdrant}")
        print(f"📊 Diferencia total: {total_esperados - total_qdrant}")
    
    print(f"\n📄 Reporte detallado guardado en: {excel_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()

