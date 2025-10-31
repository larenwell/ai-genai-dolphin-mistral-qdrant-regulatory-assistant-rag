#!/usr/bin/env python3
"""
Script de Prueba de Chunking Optimizado
=======================================

Este script implementa las optimizaciones identificadas en el análisis
para mejorar la calidad del chunking y las métricas RAGAS.

Optimizaciones implementadas:
1. Chunks más pequeños (400-600 caracteres)
2. Contextualización mínima
3. Preservación de contenido original
4. Mejor granularidad técnica
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Any
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

class OptimizedMistralExtractionController(MistralExtractionController):
    """Controlador optimizado para mejor chunking"""
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        
        # Configuración optimizada de chunking
        from langchain.text_splitter import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
        
        self.markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"), 
                ("###", "Header 3"),
                ("####", "Header 4"),
            ]
        )
        
        # Chunking optimizado: chunks más pequeños
        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,        # Reducido de 1000
            chunk_overlap=100,     # Reducido de 200
            separators=["\n\n", "\n", ". ", " "]
        )
    
    def contextualize_chunk_optimized(self, chunk: Dict[str, Any], document_summary: str, 
                                    book_title: str, page_num: int = None) -> Dict[str, Any]:
        """Contextualización optimizada que preserva el contenido original"""
        chunk_content = chunk["content"]
        
        # Use page_num from chunk metadata if not provided
        if page_num is None:
            page_num = chunk.get("metadata", {}).get("page_number", 1)
        
        visual_info = self.extract_visual_elements(chunk_content)
        
        # Extract relevant images for this chunk
        chunk_images = self.extract_images_from_chunk(chunk_content, page_num)
        
        # Crear prompt contextual optimizado (más breve)
        context_prompt = f"""
DOCUMENT: {book_title}
PAGE: {page_num}

FRAGMENT CONTENT:
{chunk_content}

INSTRUCTIONS:
Create a brief contextual summary (max 100 words) that:
1. Preserves the original technical language and specific terminology
2. Maintains exact numbers, codes, and references
3. Adds minimal context for understanding
4. Keeps the original structure and formatting intact

IMPORTANT: Do not paraphrase technical terms or change specific values.
"""
        
        try:
            context_response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in creating minimal contextual summaries for RAG systems. 
                        Your goal is to preserve the original technical content while adding only essential context.
                        Keep technical terms, numbers, and structure exactly as they appear in the original."""
                    },
                    {
                        "role": "user",
                        "content": context_prompt
                    }
                ]
            )
            
            contextualized_content = context_response.choices[0].message.content
            
        except Exception as e:
            print(f"Error contextualizing chunk {chunk.get('metadata', {}).get('chunk_id', 'unknown')}: {str(e)}")
            # Fallback: usar contenido original con contexto mínimo
            contextualized_content = f"[{book_title}, Page {page_num}] {chunk_content}"
        
        # Enhanced metadata with images
        enhanced_metadata = {
            **chunk.get("metadata", {}),
            "book_title": book_title,
            "page_number": page_num,
            "has_associated_images": len(chunk_images) > 0,
            **visual_info
        }
        
        return {
            "content": contextualized_content,
            "metadata": enhanced_metadata
        }
    
    def intelligent_chunking_optimized(self, markdown_content: str) -> List[Dict[str, Any]]:
        """Chunking optimizado con mejor granularidad"""
        chunks = []
        
        try:
            # First split by page boundaries
            page_sections = re.split(r'(--- Page \d+ ---)', markdown_content)
            
            # Process pages and their content
            current_page_num = 1
            current_headers = {}
            
            # The first item is content before the first page marker
            if page_sections and not page_sections[0].strip():
                page_sections = page_sections[1:]
            
            i = 0
            while i < len(page_sections):
                section = page_sections[i].strip()
                
                # If this is a page marker, update current page number
                page_match = re.match(r'--- Page (\d+) ---', section)
                if page_match:
                    current_page_num = int(page_match.group(1))
                    i += 1
                    if i >= len(page_sections):
                        break
                    section = page_sections[i].strip()
                
                if not section:
                    i += 1
                    continue
                
                # Process this page's content
                try:
                    # Update headers from this page
                    header_lines = re.findall(r'^(#+)\s+(.*?)$', section, re.MULTILINE)
                    for level, title in header_lines:
                        level_key = f"Header {len(level)}"
                        current_headers[level_key] = title.strip()
                    
                    # Split by headers first
                    header_chunks = self.markdown_splitter.split_text(section)
                    
                    if header_chunks:
                        for chunk in header_chunks:
                            if hasattr(chunk, 'page_content'):
                                content = chunk.page_content
                                metadata = getattr(chunk, 'metadata', {})
                            else:
                                content = str(chunk)
                                metadata = {}
                            
                            # Update metadata with current headers and page number
                            metadata.update({
                                **current_headers,
                                "page_number": current_page_num,
                                "chunk_id": f"{len(chunks)}_0",
                                "chunk_type": "structured_section"
                            })
                            
                            # If chunk is too large, split it further with smaller size
                            if len(content) > 600:  # Reducido de 1200
                                sub_chunks = self.char_splitter.split_text(content)
                                for j, sub_chunk in enumerate(sub_chunks):
                                    sub_metadata = metadata.copy()
                                    sub_metadata.update({
                                        "chunk_id": f"{len(chunks)}_{j}",
                                        "chunk_type": "text_subdivision",
                                        "parent_chunk": len(chunks)
                                    })
                                    chunks.append({
                                        "content": sub_chunk,
                                        "metadata": sub_metadata
                                    })
                            else:
                                chunks.append({
                                    "content": content,
                                    "metadata": metadata
                                })
                    
                except Exception as e:
                    print(f"Error processing page {current_page_num}: {str(e)}")
                    # Fallback to character-based splitting if header splitting fails
                    sub_chunks = self.char_splitter.split_text(section)
                    for j, sub_chunk in enumerate(sub_chunks):
                        chunks.append({
                            "content": sub_chunk,
                            "metadata": {
                                **current_headers,
                                "page_number": current_page_num,
                                "chunk_id": f"{len(chunks)}_{j}",
                                "chunk_type": "text_subdivision"
                            }
                        })
                
                i += 1
                
        except Exception as e:
            print(f"Error in intelligent_chunking_optimized: {str(e)}")
            # Fallback to simple character splitting
            sub_chunks = self.char_splitter.split_text(markdown_content)
            chunks = [{
                "content": chunk,
                "metadata": {
                    "chunk_id": str(i),
                    "chunk_type": "full_text",
                    "page_number": 1
                }
            } for i, chunk in enumerate(sub_chunks)]
        
        return chunks

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

def analyze_chunking_quality_optimized(chunks):
    """Analiza la calidad del chunking optimizado"""
    print_sub_stage("ANÁLISIS DE CALIDAD DEL CHUNKING OPTIMIZADO")
    
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
    medium_chunks = sum(1 for size in chunk_sizes if 200 <= size <= 600)
    large_chunks = sum(1 for size in chunk_sizes if size > 600)
    
    print(f"\n📏 DISTRIBUCIÓN DE TAMAÑOS:")
    print(f"   Chunks pequeños (<200 chars): {small_chunks} ({small_chunks/total_chunks*100:.1f}%)")
    print(f"   Chunks medianos (200-600 chars): {medium_chunks} ({medium_chunks/total_chunks*100:.1f}%)")
    print(f"   Chunks grandes (>600 chars): {large_chunks} ({large_chunks/total_chunks*100:.1f}%)")
    
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

def process_pdf_optimized(pdf_path):
    """Procesa un PDF con chunking optimizado"""
    if not os.path.exists(pdf_path):
        print(f"❌ Error: El archivo {pdf_path} no existe")
        return None

    if not MISTRAL_API_KEY:
        print("❌ Error: MISTRAL_API_KEY no está configurado")
        return None

    pdf_name = os.path.basename(pdf_path)
    print(f"📄 Procesando: {pdf_name}")

    # Inicializar controlador optimizado
    mistral_controller = OptimizedMistralExtractionController(api_key=MISTRAL_API_KEY)

    try:
        print_stage_title("EXTRACCIÓN DE CONTENIDO", 1)
        
        # Extraer contenido con Mistral OCR
        extraction_result = mistral_controller.extract_content_mistral_ocr(pdf_path)
        if not extraction_result:
            print("❌ Error: No se pudo extraer contenido del PDF")
            return None
        
        markdown_content = extraction_result["markdown_content"]
        print(f"✅ Contenido extraído: {len(markdown_content)} caracteres")

        print_stage_title("GENERACIÓN DE RESUMEN", 2)
        
        # Generar resumen del documento
        document_summary = mistral_controller.generate_document_summary(markdown_content)
        print(f"✅ Resumen generado: {len(document_summary)} caracteres")

        print_stage_title("CHUNKING OPTIMIZADO", 3)
        
        # Generar chunks optimizados
        chunks = mistral_controller.intelligent_chunking_optimized(markdown_content)
        print(f"✅ Chunks generados: {len(chunks)}")
        
        if not chunks:
            print("❌ Error: No se generaron chunks")
            return None

        print_stage_title("CONTEXTUALIZACIÓN OPTIMIZADA", 4)
        
        # Contextualizar chunks con método optimizado
        enhanced_chunks = []
        for i, chunk in enumerate(chunks):
            print(f"🔄 Contextualizando chunk {i+1}/{len(chunks)}")
            enhanced_chunk = mistral_controller.contextualize_chunk_optimized(
                chunk, document_summary, pdf_name
            )
            enhanced_chunks.append(enhanced_chunk)
            
            # Mostrar progreso cada 10 chunks
            if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
                print(f"   ✅ Completados: {i+1}/{len(chunks)} chunks")

        print_stage_title("ANÁLISIS DE CALIDAD OPTIMIZADA", 5)
        
        # Analizar calidad del chunking optimizado
        analysis_stats = analyze_chunking_quality_optimized(enhanced_chunks)
        
        # Guardar análisis
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        json_file = OUTPUT_DIR / f"optimized_chunks_{pdf_name}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "pdf_name": pdf_name,
                "timestamp": timestamp,
                "optimization": "chunking_optimized",
                "analysis_stats": analysis_stats,
                "chunks": enhanced_chunks
            }, f, indent=2, ensure_ascii=False)
        
        # Generar reporte comparativo
        md_file = OUTPUT_DIR / f"optimized_analysis_{pdf_name}_{timestamp}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# Análisis de Chunking Optimizado - {pdf_name}\n\n")
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
            f.write(f"- **Chunks medianos (200-600 chars):** {dist['medium']} ({dist['medium']/total*100:.1f}%)\n")
            f.write(f"- **Chunks grandes (>600 chars):** {dist['large']} ({dist['large']/total*100:.1f}%)\n\n")
            
            # Comparación con chunking original
            f.write("## 🔄 Comparación con Chunking Original\n\n")
            f.write("| Métrica | Original | Optimizado | Mejora |\n")
            f.write("|---------|----------|------------|--------|\n")
            f.write(f"| Total chunks | 44 | {analysis_stats['total_chunks']} | {analysis_stats['total_chunks']-44:+d} |\n")
            f.write(f"| Tamaño promedio | 2205.9 | {analysis_stats['avg_size']:.1f} | {2205.9-analysis_stats['avg_size']:.1f} |\n")
            f.write(f"| Chunks medianos | 0% | {dist['medium']/total*100:.1f}% | +{dist['medium']/total*100:.1f}% |\n")
            f.write(f"| Chunks grandes | 100% | {dist['large']/total*100:.1f}% | {dist['large']/total*100-100:.1f}% |\n\n")
            
            # Ejemplos de chunks optimizados
            f.write("## 📄 Ejemplos de Chunks Optimizados\n\n")
            for i, chunk in enumerate(enhanced_chunks[:3]):  # Primeros 3 chunks
                f.write(f"### Chunk {i+1}\n\n")
                f.write(f"**Tipo:** {chunk['metadata'].get('chunk_type', 'unknown')}\n")
                f.write(f"**Página:** {chunk['metadata'].get('page_number', 'N/A')}\n")
                f.write(f"**Tamaño:** {len(chunk['content'])} caracteres\n\n")
                f.write("**Contenido:**\n```\n")
                f.write(chunk['content'][:300] + ("..." if len(chunk['content']) > 300 else ""))
                f.write("\n```\n\n")
        
        print(f"📁 Archivos guardados:")
        print(f"   📊 Análisis JSON: {json_file}")
        print(f"   📝 Reporte Markdown: {md_file}")
        
        print_stage_title("RESUMEN FINAL")
        print(f"✅ Procesamiento optimizado completado")
        print(f"📊 Total de chunks: {len(enhanced_chunks)}")
        print(f"📏 Tamaño promedio: {analysis_stats['avg_size']:.1f} caracteres")
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
    print_stage_title("PRUEBA DE CHUNKING OPTIMIZADO")
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
        
        result = process_pdf_optimized(pdf_path)
        if result:
            print(f"✅ {pdf_file} procesado exitosamente")
        else:
            print(f"❌ Error procesando {pdf_file}")
        
        # Pausa entre archivos
        if len(pdf_files) > 1:
            print(f"\n⏳ Esperando 2 segundos antes del siguiente archivo...")
            time.sleep(2)
    
    print_stage_title("PRUEBA COMPLETADA")
    print(f"📁 Revisa los archivos generados en: {OUTPUT_DIR}")
    print(f"💡 Compara los resultados con el chunking original")

if __name__ == "__main__":
    main()
