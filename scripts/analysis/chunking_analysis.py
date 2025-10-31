#!/usr/bin/env python3
"""
Script de Análisis de Chunking para RAG Contextual
==================================================

Este script procesa un PDF usando Mistral OCR y genera chunks con splitting
para análisis de calidad, sin generar embeddings ni ingestar en la KB.

Propósito: Analizar la calidad del chunking para optimizar el RAG Contextual
"""

import os
import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv

# Agregar el directorio src al path para importaciones
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from ingestion.ingest_mistral import MistralExtractionController

# Configuración del proyecto
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Cargar variables de entorno
load_dotenv(project_root / '.env')

# Configuración
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
PDF_FOLDER_PATH = project_root / "data" / "test"
OUTPUT_DIR = project_root / "output" / "process"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def print_stage_title(title: str, stage_number: int = None):
    """Imprime un título de etapa con separadores visuales"""
    if stage_number:
        print(f"\n{'='*80}")
        print(f"🚀 ETAPA {stage_number}: {title}")
        print(f"{'='*80}")
    else:
        print(f"\n{'='*80}")
        print(f"🎯 {title}")
        print(f"{'='*80}")

def print_sub_stage(title: str):
    """Imprime un sub-título de etapa"""
    print(f"\n📋 {title}")
    print(f"{'-'*60}")

def analyze_chunking_quality(chunks):
    """Analiza la calidad del chunking generado"""
    print_sub_stage("ANÁLISIS DE CALIDAD DEL CHUNKING")
    
    # Estadísticas básicas
    total_chunks = len(chunks)
    chunk_sizes = [len(chunk["content"]) for chunk in chunks]
    avg_size = sum(chunk_sizes) / total_chunks if total_chunks > 0 else 0
    min_size = min(chunk_sizes) if chunk_sizes else 0
    max_size = max(chunk_sizes) if chunk_sizes else 0
    
    print(f"📊 ESTADÍSTICAS DE CHUNKS:")
    print(f"   Total de chunks: {total_chunks}")
    print(f"   Tamaño promedio: {avg_size:.1f} caracteres")
    print(f"   Tamaño mínimo: {min_size} caracteres")
    print(f"   Tamaño máximo: {max_size} caracteres")
    
    # Análisis de distribución de tamaños
    small_chunks = sum(1 for size in chunk_sizes if size < 200)
    medium_chunks = sum(1 for size in chunk_sizes if 200 <= size <= 800)
    large_chunks = sum(1 for size in chunk_sizes if size > 800)
    
    print(f"\n📏 DISTRIBUCIÓN DE TAMAÑOS:")
    print(f"   Chunks pequeños (<200 chars): {small_chunks} ({small_chunks/total_chunks*100:.1f}%)")
    print(f"   Chunks medianos (200-800 chars): {medium_chunks} ({medium_chunks/total_chunks*100:.1f}%)")
    print(f"   Chunks grandes (>800 chars): {large_chunks} ({large_chunks/total_chunks*100:.1f}%)")
    
    # Análisis de tipos de chunks
    chunk_types = {}
    for chunk in chunks:
        chunk_type = chunk["metadata"].get("chunk_type", "unknown")
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
    
    print(f"\n🏷️  TIPOS DE CHUNKS:")
    for chunk_type, count in chunk_types.items():
        print(f"   {chunk_type}: {count} ({count/total_chunks*100:.1f}%)")
    
    # Análisis de elementos visuales
    visual_stats = {
        "has_images": 0,
        "has_tables": 0,
        "has_formulas": 0,
        "has_lists": 0
    }
    
    for chunk in chunks:
        metadata = chunk["metadata"]
        for key in visual_stats:
            if metadata.get(key, False):
                visual_stats[key] += 1
    
    print(f"\n🖼️  ELEMENTOS VISUALES:")
    for element, count in visual_stats.items():
        print(f"   {element}: {count} chunks ({count/total_chunks*100:.1f}%)")
    
    return {
        "total_chunks": total_chunks,
        "avg_size": avg_size,
        "min_size": min_size,
        "max_size": max_size,
        "size_distribution": {
            "small": small_chunks,
            "medium": medium_chunks,
            "large": large_chunks
        },
        "chunk_types": chunk_types,
        "visual_elements": visual_stats
    }

def save_chunking_analysis(chunks, pdf_name, analysis_stats):
    """Guarda el análisis de chunking en formato markdown y JSON"""
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    
    # 1. Guardar chunks completos en JSON
    json_file = OUTPUT_DIR / f"chunks_analysis_{pdf_name}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            "pdf_name": pdf_name,
            "timestamp": timestamp,
            "analysis_stats": analysis_stats,
            "chunks": chunks
        }, f, indent=2, ensure_ascii=False)
    
    # 2. Generar reporte en Markdown
    md_file = OUTPUT_DIR / f"chunking_analysis_{pdf_name}_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# Análisis de Chunking - {pdf_name}\n\n")
        f.write(f"**Fecha de análisis:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Estadísticas generales
        f.write("## 📊 Estadísticas Generales\n\n")
        f.write(f"- **Total de chunks:** {analysis_stats['total_chunks']}\n")
        f.write(f"- **Tamaño promedio:** {analysis_stats['avg_size']:.1f} caracteres\n")
        f.write(f"- **Tamaño mínimo:** {analysis_stats['min_size']} caracteres\n")
        f.write(f"- **Tamaño máximo:** {analysis_stats['max_size']} caracteres\n\n")
        
        # Distribución de tamaños
        f.write("## 📏 Distribución de Tamaños\n\n")
        dist = analysis_stats['size_distribution']
        total = analysis_stats['total_chunks']
        f.write(f"- **Chunks pequeños (<200 chars):** {dist['small']} ({dist['small']/total*100:.1f}%)\n")
        f.write(f"- **Chunks medianos (200-800 chars):** {dist['medium']} ({dist['medium']/total*100:.1f}%)\n")
        f.write(f"- **Chunks grandes (>800 chars):** {dist['large']} ({dist['large']/total*100:.1f}%)\n\n")
        
        # Tipos de chunks
        f.write("## 🏷️ Tipos de Chunks\n\n")
        for chunk_type, count in analysis_stats['chunk_types'].items():
            f.write(f"- **{chunk_type}:** {count} ({count/total*100:.1f}%)\n")
        f.write("\n")
        
        # Elementos visuales
        f.write("## 🖼️ Elementos Visuales\n\n")
        for element, count in analysis_stats['visual_elements'].items():
            f.write(f"- **{element}:** {count} chunks ({count/total*100:.1f}%)\n")
        f.write("\n")
        
        # Ejemplos de chunks
        f.write("## 📄 Ejemplos de Chunks\n\n")
        for i, chunk in enumerate(chunks[:5]):  # Primeros 5 chunks
            f.write(f"### Chunk {i+1}\n\n")
            f.write(f"**Tipo:** {chunk['metadata'].get('chunk_type', 'unknown')}\n")
            f.write(f"**Página:** {chunk['metadata'].get('page_number', 'N/A')}\n")
            f.write(f"**Tamaño:** {len(chunk['content'])} caracteres\n")
            f.write(f"**Elementos visuales:** {', '.join([k for k, v in chunk['metadata'].items() if k.startswith('has_') and v])}\n\n")
            f.write("**Contenido:**\n```\n")
            f.write(chunk['content'][:500] + ("..." if len(chunk['content']) > 500 else ""))
            f.write("\n```\n\n")
        
        if len(chunks) > 5:
            f.write(f"... y {len(chunks) - 5} chunks más\n\n")
    
    # 3. Guardar solo el contenido markdown original (sin contextualización)
    original_md_file = OUTPUT_DIR / f"original_markdown_{pdf_name}_{timestamp}.md"
    with open(original_md_file, 'w', encoding='utf-8') as f:
        f.write(f"# Contenido Markdown Original - {pdf_name}\n\n")
        f.write(f"**Fecha de extracción:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        # Aquí se guardaría el markdown original si lo tuviéramos disponible
    
    print(f"📁 Archivos guardados:")
    print(f"   📊 Análisis JSON: {json_file}")
    print(f"   📝 Reporte Markdown: {md_file}")
    print(f"   📄 Markdown original: {original_md_file}")

def process_pdf_for_analysis(pdf_path):
    """Procesa un PDF para análisis de chunking"""
    if not os.path.exists(pdf_path):
        print(f"❌ Error: El archivo {pdf_path} no existe")
        return None

    if not MISTRAL_API_KEY:
        print("❌ Error: MISTRAL_API_KEY no está configurado")
        return None

    pdf_name = os.path.basename(pdf_path)
    print(f"📄 Procesando: {pdf_name}")
    print(f"🔑 MISTRAL_API_KEY configurado: {'Sí' if MISTRAL_API_KEY else 'No'}")

    # Inicializar controlador Mistral
    mistral_controller = MistralExtractionController(api_key=MISTRAL_API_KEY)

    try:
        print_stage_title("EXTRACCIÓN DE CONTENIDO", 1)
        
        # Extraer contenido con Mistral OCR
        extraction_result = mistral_controller.extract_content_mistral_ocr(pdf_path)
        if not extraction_result:
            print("❌ Error: No se pudo extraer contenido del PDF")
            return None
        
        markdown_content = extraction_result["markdown_content"]
        print(f"✅ Contenido extraído: {len(markdown_content)} caracteres")
        
        # Guardar markdown original
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        original_md_file = OUTPUT_DIR / f"original_markdown_{pdf_name}_{timestamp}.md"
        with open(original_md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Contenido Markdown Original - {pdf_name}\n\n")
            f.write(f"**Fecha de extracción:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(markdown_content)
        
        print(f"📄 Markdown original guardado: {original_md_file}")

        print_stage_title("GENERACIÓN DE RESUMEN", 2)
        
        # Generar resumen del documento
        document_summary = mistral_controller.generate_document_summary(markdown_content)
        print(f"✅ Resumen generado: {len(document_summary)} caracteres")
        print(f"📝 Resumen: {document_summary[:200]}...")

        print_stage_title("CHUNKING INTELIGENTE", 3)
        
        # Generar chunks
        chunks = mistral_controller.intelligent_chunking(markdown_content)
        print(f"✅ Chunks generados: {len(chunks)}")
        
        if not chunks:
            print("❌ Error: No se generaron chunks")
            return None

        print_stage_title("CONTEXTUALIZACIÓN", 4)
        
        # Contextualizar chunks (sin generar embeddings)
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 Contextualizando chunk {i+1}/{len(chunks)}")
            enhanced_chunk = mistral_controller.contextualize_chunk(
                chunk, document_summary, pdf_name
            )
            enhanced_chunks.append(enhanced_chunk)
            
            # Mostrar progreso cada 10 chunks
            if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
                print(f"   ✅ Completados: {i+1}/{len(chunks)} chunks")

        print_stage_title("ANÁLISIS DE CALIDAD", 5)
        
        # Analizar calidad del chunking
        analysis_stats = analyze_chunking_quality(enhanced_chunks)
        
        # Guardar análisis
        save_chunking_analysis(enhanced_chunks, pdf_name, analysis_stats)
        
        print_stage_title("RESUMEN FINAL")
        print(f"✅ Procesamiento completado exitosamente")
        print(f"📊 Total de chunks: {len(enhanced_chunks)}")
        print(f"📁 Archivos generados en: {OUTPUT_DIR}")
        
        return enhanced_chunks

    except Exception as e:
        print(f"❌ Error procesando documento: {str(e)}")
        import traceback
        print(f"📋 Traceback completo:")
        traceback.print_exc()
        return None

def main():
    """Función principal"""
    print_stage_title("ANÁLISIS DE CHUNKING PARA RAG CONTEXTUAL")
    print(f"📁 Directorio de PDFs: {PDF_FOLDER_PATH}")
    print(f"📁 Directorio de salida: {OUTPUT_DIR}")
    
    # Buscar archivos PDF en la carpeta
    pdf_files = [f for f in os.listdir(PDF_FOLDER_PATH) if f.lower().endswith(".pdf")]
    
    if not pdf_files:
        print(f"❌ No se encontraron archivos PDF en {PDF_FOLDER_PATH}")
        return
    
    print(f"📄 Archivos PDF encontrados: {len(pdf_files)}")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file}")
    
    # Procesar cada archivo
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_FOLDER_PATH, pdf_file)
        print(f"\n{'='*80}")
        print(f"📄 PROCESANDO: {pdf_file}")
        print(f"{'='*80}")
        
        result = process_pdf_for_analysis(pdf_path)
        if result:
            print(f"✅ {pdf_file} procesado exitosamente")
        else:
            print(f"❌ Error procesando {pdf_file}")
        
        # Pausa entre archivos
        if len(pdf_files) > 1:
            print(f"\n⏳ Esperando 2 segundos antes del siguiente archivo...")
            time.sleep(2)
    
    print_stage_title("ANÁLISIS COMPLETADO")
    print(f"📁 Revisa los archivos generados en: {OUTPUT_DIR}")
    print(f"💡 Usa los archivos .md para analizar la calidad del chunking")

if __name__ == "__main__":
    main()
