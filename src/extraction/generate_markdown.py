#!/usr/bin/env python3
"""
Script de generación de archivos Markdown desde PDFs y DOCX
Procesa documentos técnicos y genera markdown + metadata normalizada

NO hace ingesta a base de datos - solo genera archivos markdown
La ingesta se hace posteriormente con src/ingestion/test_semantic_chunking.py o src/ingestion/test_recursive_character_chunking.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
import docx2txt  # pip install docx2txt
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from extraction.markdown_extraction import MistralExtractionController


def extract_docx_content(docx_path: str) -> str:
    """Extrae texto de archivo DOCX"""
    try:
        text = docx2txt.process(docx_path)
        return text
    except Exception as e:
        print(f"❌ Error extrayendo DOCX: {e}")
        return None


def make_safe_output_names(src_file: Path, max_stem_len: int = 160) -> tuple[str, str]:
    """Generate safe markdown and metadata filenames with truncated stem if needed."""
    stem = src_file.stem
    safe_stem = stem[:max_stem_len] if len(stem) > max_stem_len else stem
    markdown_filename = f"{safe_stem}_markdown.md"
    metadata_filename = f"{safe_stem}_metadata.json"
    return markdown_filename, metadata_filename


def main():
    """
    Procesa todos los PDFs y DOCX en data/temp/
    Genera archivos Markdown con metadata normalizada
    """
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Mistral controller
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ Error: MISTRAL_API_KEY no encontrada en las variables de entorno")
        return
    
    mistral_controller = MistralExtractionController(api_key)
    
    # Define paths
    data_dir = Path("data/temp")
    output_dir = Path("output/markdown/EXTRA_DS_LEY")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF and DOCX files
    files = (
        list(data_dir.glob("*.pdf"))
        + list(data_dir.glob("*.PDF"))
        + list(data_dir.glob("*.docx"))
        + list(data_dir.glob("*.DOCX"))
    )
    
    if not files:
        print("❌ No se encontraron archivos PDF o DOCX en data/temp/")
        return
    
    print("="*80)
    print("🚀 GENERACIÓN DE ARCHIVOS MARKDOWN")
    print("="*80)
    print(f"📂 Directorio entrada: {data_dir}")
    print(f"📂 Directorio salida: {output_dir}")
    print(f"🔍 Encontrados {len(files)} archivos:")
    for file in files:
        print(f"  - {file.name} ({file.suffix})")
    print("="*80 + "\n")
    
    # Process each file
    processed_files = []
    failed_files = []
    total_files = len(files)
    
    for idx, file in enumerate(files, 1):
        try:
            print(f"\n{'='*80}")
            print(f"📄 Procesando archivo {idx}/{total_files}: {file.name}")
            print(f"{'='*80}")
            
            extraction_result = None
            
            # Extract content based on file type (normalized)
            suffix_lower = file.suffix.lower()
            if suffix_lower == '.pdf':
                print("📋 Tipo: PDF")
                extraction_result = mistral_controller.extract_content_mistral_ocr(str(file))
                
                if not extraction_result or not extraction_result.get('markdown_content'):
                    print(f"❌ Error: No se pudo extraer contenido de {file.name}")
                    failed_files.append(file.name)
                    continue
                
                markdown_content = extraction_result['markdown_content']
                document_summary = extraction_result.get('document_summary', '')
                doc_metadata = extraction_result['metadata']
            
            elif suffix_lower == '.docx':
                print("📋 Tipo: DOCX")
                # Extract text from DOCX
                text_content = extract_docx_content(str(file))
                
                if not text_content:
                    print(f"❌ Error: No se pudo extraer contenido de {file.name}")
                    failed_files.append(file.name)
                    continue
                
                # Convert text to markdown using Mistral
                extraction_result = mistral_controller.convert_text_to_markdown(
                    text_content, 
                    source_file=file.name
                )
                
                if not extraction_result or not extraction_result.get('markdown_content'):
                    print(f"❌ Error: No se pudo convertir a markdown {file.name}")
                    failed_files.append(file.name)
                    continue
                
                markdown_content = extraction_result['markdown_content']
                document_summary = extraction_result.get('document_summary', '')
                doc_metadata = extraction_result['metadata']
            
            else:
                print(f"⚠️ Tipo de archivo no soportado: {file.suffix}")
                failed_files.append(file.name)
                continue
            
            # Display extracted metadata
            print(f"\n📋 METADATA EXTRAÍDA:")
            print(f"   - Document ID: {doc_metadata['document_id']}")
            print(f"   - Source File: {doc_metadata['source_file']}")
            print(f"   - Book Title: {doc_metadata['book_title']}")
            print(f"   - Language: {doc_metadata['language']}")
            print(f"   - Extraction Method: {doc_metadata['extraction_method']}")
            if doc_metadata.get('total_pages'):
                print(f"   - Total Pages: {doc_metadata['total_pages']}")
            if doc_metadata.get('num_mini_summaries', 0) > 0:
                print(f"   - Mini-summaries: {doc_metadata['num_mini_summaries']}")
            else:
                print(f"   - Summary: Omitido temporalmente (se implementará después)")
            
            # Generate output filename
            output_filename, metadata_filename = make_safe_output_names(file)
            output_path = output_dir / output_filename
            
            # Save markdown content
            print(f"\n💾 Guardando markdown...")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"✅ Archivo guardado: {output_filename}")
            print(f"   - Longitud: {len(markdown_content):,} caracteres")
            
            # Save comprehensive metadata with normalized structure
            metadata = {
                # Identificación del documento (NORMALIZADA)
                "document_id": doc_metadata['document_id'],
                "source_file": doc_metadata['source_file'],
                "book_title": doc_metadata['book_title'],
                "language": doc_metadata['language'],
                
                # Archivos generados
                "output_file": output_filename,
                "output_path": str(output_path),
                
                # Estadísticas del contenido
                "markdown_length": len(markdown_content),
                "summary_length": len(document_summary),
                "document_summary": document_summary,
                
                # Metadata de extracción
                "extraction_method": doc_metadata['extraction_method'],
                "total_pages": doc_metadata.get('total_pages'),
                "file_size_mb": doc_metadata.get('file_size_mb'),
                "processed_in_chunks": doc_metadata.get('processed_in_chunks', False),
                "num_mini_summaries": doc_metadata.get('num_mini_summaries', 0),
                
                # Timestamp
                "processed_at": datetime.now().isoformat(),
                
                # Metadata original completa
                "original_metadata": doc_metadata
            }
            
            metadata_path = output_dir / metadata_filename
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Metadata guardada: {metadata_filename}")
            
            # Add to processed files list
            processed_files.append({
                "document_id": doc_metadata['document_id'],
                "source_file": file.name,
                "file_type": file.suffix,
                "book_title": doc_metadata['book_title'],
                "language": doc_metadata['language'],
                "markdown_file": output_filename,
                "metadata_file": metadata_filename,
                "markdown_length": len(markdown_content),
                "total_pages": doc_metadata.get('total_pages'),
                "processed_at": metadata['processed_at']
            })
            
            print(f"\n✅ Completado exitosamente: {file.name}")
            
        except Exception as e:
            print(f"\n❌ Error procesando {file.name}: {str(e)}")
            import traceback
            traceback.print_exc()
            failed_files.append(file.name)
    
    # Generate comprehensive summary report
    print("\n" + "="*80)
    print("📊 GENERANDO REPORTE FINAL")
    print("="*80)
    
    summary = {
        "execution_info": {
            "total_files": len(files),
            "processed_successfully": len(processed_files),
            "failed": len(failed_files),
            "success_rate": f"{(len(processed_files)/len(files)*100):.1f}%" if files else "0%",
            "timestamp": datetime.now().isoformat()
        },
        "processed_files": processed_files,
        "failed_files": failed_files,
        "directories": {
            "input": str(data_dir),
            "output": str(output_dir)
        }
    }
    
    summary_path = output_dir / "processing_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print final summary to console
    print(f"\n{'='*80}")
    print("📊 RESUMEN FINAL DE PROCESAMIENTO")
    print(f"{'='*80}")
    print(f"\n✅ Archivos procesados exitosamente: {len(processed_files)}/{len(files)}")
    print(f"❌ Archivos fallidos: {len(failed_files)}/{len(files)}")
    print(f"📈 Tasa de éxito: {summary['execution_info']['success_rate']}")
    
    if processed_files:
        print(f"\n📚 DOCUMENTOS PROCESADOS:")
        for pf in processed_files:
            print(f"\n   📄 {pf['source_file']}")
            print(f"      - Document ID: {pf['document_id']}")
            print(f"      - Title: {pf['book_title']}")
            print(f"      - Language: {pf['language']}")
            print(f"      - Type: {pf['file_type']}")
            print(f"      - Length: {pf['markdown_length']:,} chars")
            if pf['total_pages']:
                print(f"      - Pages: {pf['total_pages']}")
    
    if failed_files:
        print(f"\n❌ ARCHIVOS FALLIDOS:")
        for failed_file in failed_files:
            print(f"   - {failed_file}")
    
    print(f"\n📁 Archivos guardados en: {output_dir}")
    print(f"📋 Resumen guardado en: {summary_path}")
    print(f"\n{'='*80}")
    print("✅ PROCESAMIENTO COMPLETADO")
    print(f"{'='*80}")
    print(f"\n💡 PRÓXIMO PASO:")
    print(f"   Ejecuta src/ingestion/test_semantic_chunking.py o src/ingestion/test_recursive_character_chunking.py")
    print(f"   para generar embeddings e ingestar en Qdrant")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()