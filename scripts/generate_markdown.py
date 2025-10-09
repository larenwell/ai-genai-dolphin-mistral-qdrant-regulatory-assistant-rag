#!/usr/bin/env python3
"""
Script para generar archivos Markdown una sola vez por cada PDF en data/ingested_p2/
Este script procesa todos los PDFs y genera los archivos .md que serán usados
por los diferentes métodos de chunking.
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from ingestion.ingest_mistral import MistralExtractionController

def main():
    """Procesa todos los PDFs en data/ingested_p2/ y genera archivos Markdown"""
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Mistral controller
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        print("❌ Error: MISTRAL_API_KEY no encontrada en las variables de entorno")
        return
    
    mistral_controller = MistralExtractionController(api_key)
    
    # Define paths
    data_dir = Path("data/ingested_p2")
    output_dir = Path("src/output/markdown")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all PDF files
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ No se encontraron archivos PDF en data/ingested_p2/")
        return
    
    print(f"🔍 Encontrados {len(pdf_files)} archivos PDF:")
    for pdf_file in pdf_files:
        print(f"  - {pdf_file.name}")
    
    print("\n🚀 Iniciando procesamiento...")
    
    # Process each PDF
    processed_files = []
    failed_files = []
    
    for pdf_file in pdf_files:
        try:
            print(f"\n📄 Procesando: {pdf_file.name}")
            
            # Extract content using Mistral OCR
            extraction_result = mistral_controller.extract_content_mistral_ocr(str(pdf_file))
            
            if not extraction_result or not extraction_result.get('markdown_content'):
                print(f"❌ Error: No se pudo extraer contenido de {pdf_file.name}")
                failed_files.append(pdf_file.name)
                continue
            
            # Get markdown content
            markdown_content = extraction_result['markdown_content']
            
            # Generate output filename
            output_filename = pdf_file.stem + "_markdown.md"
            output_path = output_dir / output_filename
            
            # Save markdown content
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Generate document summary
            document_summary = mistral_controller.generate_document_summary(markdown_content)
            
            # Save metadata
            metadata = {
                "source_file": pdf_file.name,
                "output_file": output_filename,
                "markdown_length": len(markdown_content),
                "summary_length": len(document_summary),
                "document_summary": document_summary,
                "extraction_metadata": extraction_result.get('metadata', {})
            }
            
            metadata_filename = pdf_file.stem + "_metadata.json"
            metadata_path = output_dir / metadata_filename
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Completado: {output_filename}")
            print(f"   - Longitud: {len(markdown_content)} caracteres")
            print(f"   - Resumen: {len(document_summary)} caracteres")
            
            processed_files.append({
                "pdf_file": pdf_file.name,
                "markdown_file": output_filename,
                "metadata_file": metadata_filename,
                "markdown_length": len(markdown_content)
            })
            
        except Exception as e:
            print(f"❌ Error procesando {pdf_file.name}: {str(e)}")
            failed_files.append(pdf_file.name)
    
    # Generate summary report
    summary = {
        "total_files": len(pdf_files),
        "processed_successfully": len(processed_files),
        "failed": len(failed_files),
        "processed_files": processed_files,
        "failed_files": failed_files
    }
    
    summary_path = output_dir / "processing_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print final summary
    print(f"\n📊 RESUMEN FINAL:")
    print(f"✅ Archivos procesados exitosamente: {len(processed_files)}")
    print(f"❌ Archivos fallidos: {len(failed_files)}")
    print(f"📁 Archivos Markdown guardados en: {output_dir}")
    
    if failed_files:
        print(f"\n❌ Archivos fallidos:")
        for failed_file in failed_files:
            print(f"  - {failed_file}")
    
    print(f"\n📋 Resumen guardado en: {summary_path}")

if __name__ == "__main__":
    main()
