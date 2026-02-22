#!/usr/bin/env python3
"""
Script de generación de archivos Markdown desde PDFs (Fase 3 del Pipeline)

Procesa documentos desde output/datasources/{pestaña}/ y genera markdown organizado por idioma.

Flujo:
1. Lee PDFs desde output/datasources/{pestaña}/
2. Obtiene document_id desde output/metadata/source/{pestaña}/
3. Extrae contenido con Mistral OCR
4. Detecta idioma del contenido
5. Guarda en processed_es/{pestaña}/ o processed_en/{pestaña}/
6. Guarda metadata en output/metadata/extraction/{pestaña}/ con sufijo _extraction.json

NOTA: La traducción de documentos en español a inglés se hace en un paso separado
usando src/translation/translate_documents_batch.py (Paso 4 del pipeline).

NO hace ingesta a base de datos - solo genera archivos markdown
La ingesta se hace posteriormente con src/ingestion/test_recursive_character_chunking.py
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List, Optional

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core import get_logger
from src.extraction.markdown_extraction import MistralExtractionController

# Setup logging
logger = get_logger(__name__)

# Import PyPDF2 después de configurar logger
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logger.warning("PyPDF2 no está instalado. No se podrá obtener metadata del PDF directamente.")

# Load environment
load_dotenv()


def load_metadata_tmp(metadata_dir: Path, document_id: str) -> Optional[Dict]:
    """
    Carga metadata original desde output/metadata/source/{pestaña}/{document_id}_source.json
    
    Args:
        metadata_dir: Directorio base de metadata (output/metadata/source/)
        document_id: ID del documento a buscar
    
    Returns:
        Dict con metadata o None si no se encuentra
    """
    # Buscar en todas las subcarpetas (pestañas)
    for sheet_dir in metadata_dir.iterdir():
        if not sheet_dir.is_dir():
            continue
        
        json_file = sheet_dir / f"{document_id}_source.json"
        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    metadata['_sheet'] = sheet_dir.name
                    return metadata
            except Exception as e:
                logger.warning(f"Error leyendo {json_file}: {e}")
    
    return None


def extract_document_id_from_filename(filename: str) -> str:
    """
    Extrae document_id del nombre del archivo PDF.
    
    Formato esperado: {document_id}_source.pdf
    """
    # Remover sufijo _source y extensión
    if filename.endswith('_source.pdf'):
        return filename.replace('_source.pdf', '')
    elif filename.endswith('.pdf'):
        return filename.replace('.pdf', '')
    return Path(filename).stem


def get_pdf_total_pages(pdf_path: Path) -> Optional[int]:
    """
    Obtiene el número total de páginas de un archivo PDF.
    
    Args:
        pdf_path: Ruta al archivo PDF
    
    Returns:
        Número de páginas o None si hay error
    """
    if not PyPDF2:
        logger.warning("PyPDF2 no está disponible. No se puede obtener total_pages del PDF.")
        return None
    
    try:
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            logger.debug(f"Total de páginas obtenido del PDF: {total_pages}")
            return total_pages
    except Exception as e:
        logger.warning(f"Error obteniendo total_pages del PDF {pdf_path.name}: {e}")
        return None


def get_pdf_file_size_mb(pdf_path: Path) -> Optional[float]:
    """
    Obtiene el tamaño del archivo PDF en MB.
    
    Args:
        pdf_path: Ruta al archivo PDF
    
    Returns:
        Tamaño en MB o None si hay error
    """
    try:
        if not pdf_path.exists():
            logger.warning(f"El archivo PDF no existe: {pdf_path}")
            return None
        
        file_size_bytes = pdf_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.debug(f"Tamaño del archivo obtenido: {file_size_mb:.2f} MB")
        return round(file_size_mb, 2)
    except Exception as e:
        logger.warning(f"Error obteniendo file_size_mb del PDF {pdf_path.name}: {e}")
        return None


def detect_language_from_content(text: str, extraction_controller: MistralExtractionController) -> str:
    """
    Detecta el idioma del contenido del documento.
    
    Args:
        text: Contenido del documento (markdown)
        extraction_controller: Controlador de extracción con método detect_language
    
    Returns:
        "es" o "en"
    """
    detected = extraction_controller.detect_language(text)
    
    # Normalizar a "es" o "en"
    if detected == "es":
        return "es"
    elif detected == "en":
        return "en"
    else:
        # Si no se detecta claramente, usar heurística adicional
        sample = text[:2000].lower()
        spanish_indicators = ['artículo', 'decreto', 'ley', 'considerando', 'dispone', 'establece']
        english_indicators = ['section', 'standard', 'requirements', 'shall', 'must', 'shall be']
        
        es_count = sum(1 for word in spanish_indicators if word in sample)
        en_count = sum(1 for word in english_indicators if word in sample)
        
        if es_count > en_count:
            return "es"
        elif en_count > es_count:
            return "en"
        else:
            # Por defecto, asumir español si hay caracteres especiales
            if any(c in sample for c in ['á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡']):
                return "es"
            return "en"  # Por defecto inglés para documentos técnicos


def process_datasources_directory(
    datasources_dir: Path,
    metadata_source_dir: Path,
    output_md_dir: Path,
    metadata_extraction_dir: Path,
    extraction_controller: MistralExtractionController
) -> Dict:
    """
    Procesa todos los PDFs en output/datasources/{pestaña}/
    
    Returns:
        Dict con estadísticas de procesamiento
    """
    results = {
        "processed": [],
        "failed": [],
        "by_language": {"es": 0, "en": 0},
        "by_sheet": {}
    }
    
    if not datasources_dir.exists():
        logger.error(f"Directorio datasources no existe: {datasources_dir}")
        return results
    
    # Recorrer cada subcarpeta (pestaña)
    for sheet_dir in datasources_dir.iterdir():
        if not sheet_dir.is_dir():
            continue
        
        sheet_name = sheet_dir.name
        logger.info(f"\n{'='*80}")
        logger.info(f"📁 Procesando pestaña: {sheet_name}")
        logger.info(f"{'='*80}")
        
        results["by_sheet"][sheet_name] = {"processed": 0, "failed": 0}
        
        # Obtener todos los PDFs en esta pestaña
        pdf_files = list(sheet_dir.glob("*_source.pdf"))
        
        if not pdf_files:
            logger.warning(f"No se encontraron PDFs en {sheet_dir}")
            continue
        
        logger.info(f"📄 Encontrados {len(pdf_files)} archivos PDF")
        
        # Procesar cada PDF
        for idx, pdf_file in enumerate(pdf_files, 1):
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Archivo {idx}/{len(pdf_files)}: {pdf_file.name}")
                logger.info(f"{'='*60}")
                
                # Extraer document_id del nombre del archivo
                document_id = extract_document_id_from_filename(pdf_file.name)
                logger.info(f"🔍 Document ID: {document_id}")
                
                # Cargar metadata original
                metadata_tmp = load_metadata_tmp(metadata_source_dir, document_id)
                if not metadata_tmp:
                    logger.warning(f"⚠️ No se encontró metadata temporal para {document_id}")
                    # Continuar con metadata mínima
                    metadata_tmp = {
                        "document_id": document_id,
                        "sincro": {"source_file": pdf_file.name},
                        "_sheet": sheet_name
                    }
                
                # Extraer contenido con Mistral OCR (sin generar resumen para optimizar tiempo)
                logger.info("🔄 Extrayendo contenido con Mistral OCR...")
                extraction_result = extraction_controller.extract_content_mistral_ocr(
                    str(pdf_file),
                    generate_summary=False  # No generar resumen para optimizar tiempo de procesamiento
                )
                
                if not extraction_result or not extraction_result.get('markdown_content'):
                    logger.error(f"❌ No se pudo extraer contenido de {pdf_file.name}")
                    results["failed"].append({
                        "file": pdf_file.name,
                        "sheet": sheet_name,
                        "error": "Extraction failed"
                    })
                    results["by_sheet"][sheet_name]["failed"] += 1
                    continue
                
                markdown_content = extraction_result['markdown_content']
                # NOTA: document_summary ya no se genera (generate_summary=False) para optimizar tiempo
                document_summary = extraction_result.get('document_summary', '')
                doc_metadata = extraction_result['metadata']
                
                # Detectar idioma del contenido
                logger.info("🌐 Detectando idioma del documento...")
                detected_language = detect_language_from_content(markdown_content, extraction_controller)
                logger.info(f"✅ Idioma detectado: {detected_language.upper()}")
                
                # Determinar carpeta de salida según idioma
                lang_output_dir = output_md_dir / f"processed_{detected_language}" / sheet_name
                lang_output_dir.mkdir(parents=True, exist_ok=True)
                
                # Nombre del archivo: {document_id}.md
                output_filename = f"{document_id}.md"
                output_path = lang_output_dir / output_filename
                
                # Guardar markdown
                logger.info(f"💾 Guardando markdown en: {output_path.relative_to(output_md_dir)}")
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                logger.info(f"✅ Markdown guardado: {len(markdown_content):,} caracteres")
                
                # Preparar metadata completa
                # Priorizar datos de _source.json cuando estén disponibles
                temp_data = metadata_tmp.get('temp', {})
                sincro_data = metadata_tmp.get('sincro', {})
                
                # Obtener total_pages: preferir de _source.json, sino de doc_metadata, sino del PDF
                total_pages = temp_data.get('Nro. páginas') or doc_metadata.get('total_pages')
                if not total_pages:
                    logger.info("📄 Obteniendo total_pages del PDF...")
                    total_pages = get_pdf_total_pages(pdf_file)
                
                # Obtener file_size_mb: preferir de _source.json, sino de doc_metadata, sino del PDF
                file_size_mb = temp_data.get('peso (MB)') or doc_metadata.get('file_size_mb')
                if not file_size_mb:
                    logger.info("📊 Obteniendo file_size_mb del PDF...")
                    file_size_mb = get_pdf_file_size_mb(pdf_file)
                
                # Obtener source_file: preferir de _source.json sincro, sino del nombre del PDF
                source_file = sincro_data.get('source_file') or pdf_file.name
                
                # Obtener sheet: preferir de _source.json, sino usar sheet_name actual
                sheet = metadata_tmp.get('_sheet') if metadata_tmp else sheet_name
                
                # Determinar docx_conversion: verificar si el archivo original era DOC/DOCX
                # La lógica se basa en la extensión del source_file:
                # - Si source_file termina en .doc o .docx → fue convertido (docx_conversion = True)
                # - Si source_file termina en .pdf → ya era PDF (docx_conversion = False)
                docx_conversion = False
                if source_file:
                    source_file_lower = source_file.lower()
                    if source_file_lower.endswith(('.doc', '.docx')):
                        docx_conversion = True
                
                # text_extraction_method siempre es "mistral_ocr" (string)
                text_extraction_method = 'mistral_ocr'
                
                # Construir metadata en el orden especificado
                metadata_md = {
                    # Identificación del documento
                    "document_id": document_id,
                    "source_file": source_file,
                    "language": detected_language,
                    "sheet": sheet,
                    
                    # Estadísticas del contenido
                    "markdown_length": len(markdown_content),
                    "total_pages": total_pages,
                    "file_size_mb": file_size_mb,
                    
                    # Metadata de conversión y extracción
                    "docx_conversion": docx_conversion,  # Boolean: true si fue convertido de DOC/DOCX
                    "text_extraction_method": text_extraction_method,  # String: "mistral_ocr"
                    "mistral_ocr": True,  # Boolean: siempre true
                    
                    # Timestamp
                    "processed_at": datetime.now().isoformat()
                }
                
                # Guardar metadata en output/metadata/extraction/{pestaña}/
                metadata_sheet_dir = metadata_extraction_dir / sheet_name
                metadata_sheet_dir.mkdir(parents=True, exist_ok=True)
                metadata_filename = f"{document_id}_extraction.json"
                metadata_path = metadata_sheet_dir / metadata_filename
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata_md, f, indent=2, ensure_ascii=False)
                
                logger.info(f"✅ Metadata guardada: {metadata_path.relative_to(metadata_extraction_dir.parent)}")
                
                # Agregar a resultados
                results["processed"].append({
                    "document_id": document_id,
                    "source_file": pdf_file.name,
                    "sheet": sheet_name,
                    "language": detected_language,
                    "output_file": output_filename,
                    "markdown_length": len(markdown_content),
                    "total_pages": doc_metadata.get('total_pages'),
                    "file_size_mb": doc_metadata.get('file_size_mb')
                })
                
                results["by_language"][detected_language] += 1
                results["by_sheet"][sheet_name]["processed"] += 1
                
                logger.info(f"✅ Completado exitosamente: {document_id}")
                
                # Eliminar archivo PDF de datasources solo si se procesó exitosamente
                try:
                    pdf_file.unlink()
                    logger.info(f"🗑️ Archivo eliminado de datasources: {pdf_file.name}")
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo eliminar {pdf_file.name}: {e}")
                
            except Exception as e:
                logger.error(f"❌ Error procesando {pdf_file.name}: {str(e)}")
                import traceback
                traceback.print_exc()
                results["failed"].append({
                    "file": pdf_file.name,
                    "sheet": sheet_name,
                    "error": str(e)
                })
                results["by_sheet"][sheet_name]["failed"] += 1
                # NO eliminar archivos con errores - deben permanecer para revisión
    
    return results


def translate_spanish_documents(
    processed_es_dir: Path,
    processed_en_dir: Path,
    timeout: int = 60
) -> Dict:
    """
    [DEPRECATED - NO SE USA EN ESTE SCRIPT]
    Traduce todos los documentos en español a inglés usando translate_documents_batch.py
    
    NOTA: Esta función ya no se usa en este script. La traducción se hace en un paso
    separado usando src/translation/translate_documents_batch.py (Paso 4 del pipeline).
    
    Args:
        processed_es_dir: Directorio con markdowns en español (processed_es)
        processed_en_dir: Directorio donde guardar traducciones (processed_en)
        timeout: Timeout para traducción
    
    Returns:
        Dict con estadísticas de traducción
    """
    from src.translation.translate_document import DocumentTranslator
    
    results = {
        "translated": [],
        "failed": [],
        "total": 0
    }
    
    if not processed_es_dir.exists():
        logger.warning(f"Directorio de español no existe: {processed_es_dir}")
        return results
    
    # Recorrer cada subcarpeta (pestaña)
    translator = DocumentTranslator(timeout_seconds=timeout)
    
    for sheet_dir in processed_es_dir.iterdir():
        if not sheet_dir.is_dir():
            continue
        
        sheet_name = sheet_dir.name
        logger.info(f"\n{'='*80}")
        logger.info(f"🌐 Traduciendo pestaña: {sheet_name}")
        logger.info(f"{'='*80}")
        
        # Crear directorio de salida para esta pestaña
        output_sheet_dir = processed_en_dir / sheet_name
        output_sheet_dir.mkdir(parents=True, exist_ok=True)
        
        # Obtener todos los markdowns
        md_files = list(sheet_dir.glob("*.md"))
        
        if not md_files:
            logger.info(f"No hay archivos para traducir en {sheet_dir}")
            continue
        
        logger.info(f"📄 Encontrados {len(md_files)} archivos para traducir")
        
        for idx, md_file in enumerate(md_files, 1):
            try:
                logger.info(f"\n📄 Traduciendo {idx}/{len(md_files)}: {md_file.name}")
                
                output_file = output_sheet_dir / md_file.name
                
                # Verificar si ya existe traducción
                if output_file.exists():
                    logger.info(f"⏭️ Traducción ya existe, omitiendo: {md_file.name}")
                    results["translated"].append({
                        "file": md_file.name,
                        "sheet": sheet_name,
                        "status": "already_exists"
                    })
                    continue
                
                # Traducir
                success = translator.translate_file(
                    str(md_file),
                    str(output_file),
                    source_lang="es",
                    target_lang="en"
                )
                
                if success:
                    logger.info(f"✅ Traducido: {md_file.name}")
                    results["translated"].append({
                        "file": md_file.name,
                        "sheet": sheet_name,
                        "status": "translated"
                    })
                    results["total"] += 1
                else:
                    logger.error(f"❌ Error traduciendo: {md_file.name}")
                    results["failed"].append({
                        "file": md_file.name,
                        "sheet": sheet_name
                    })
                    
            except Exception as e:
                logger.error(f"❌ Error traduciendo {md_file.name}: {str(e)}")
                results["failed"].append({
                    "file": md_file.name,
                    "sheet": sheet_name,
                    "error": str(e)
                })
    
    return results


def main():
    """Función principal."""
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    datasources_dir = project_root / "output" / "datasources"
    metadata_source_dir = project_root / "output" / "metadata" / "source"
    output_md_dir = project_root / "output" / "markdown"
    metadata_extraction_dir = project_root / "output" / "metadata" / "extraction"
    
    # Validar paths
    if not datasources_dir.exists():
        logger.error(f"Directorio datasources no existe: {datasources_dir}")
        logger.error("Ejecuta primero: python src/conversion/docx_to_pdf.py")
        return
    
    if not metadata_source_dir.exists():
        logger.error(f"Directorio de metadata original no existe: {metadata_source_dir}")
        logger.error("Ejecuta primero: python src/utils/excel_parser_base_conocimiento.py")
        return
    
    # Inicializar Mistral controller
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        logger.error("❌ Error: MISTRAL_API_KEY no encontrada en las variables de entorno")
        return
    
    extraction_controller = MistralExtractionController(api_key)
    
    logger.info("="*80)
    logger.info("🚀 GENERACIÓN DE ARCHIVOS MARKDOWN (Fase 3 del Pipeline)")
    logger.info("="*80)
    logger.info(f"📂 Datasources: {datasources_dir}")
    logger.info(f"📂 Metadata source: {metadata_source_dir}")
    logger.info(f"📂 Salida markdown: {output_md_dir}")
    logger.info(f"📂 Salida metadata: {metadata_extraction_dir}")
    logger.info("="*80 + "\n")
    
    # Paso 1: Procesar todos los PDFs en datasources/
    logger.info("📊 Paso 1: Procesando PDFs desde datasources/...")
    results = process_datasources_directory(
        datasources_dir,
        metadata_source_dir,
        output_md_dir,
        metadata_extraction_dir,
        extraction_controller
    )
    
    # Mostrar resumen de procesamiento
    logger.info("\n" + "="*80)
    logger.info("📊 RESUMEN DE PROCESAMIENTO")
    logger.info("="*80)
    logger.info(f"✅ Archivos procesados: {len(results['processed'])}")
    logger.info(f"❌ Archivos fallidos: {len(results['failed'])}")
    logger.info(f"📊 Por idioma:")
    logger.info(f"   - Español (ES): {results['by_language']['es']}")
    logger.info(f"   - Inglés (EN): {results['by_language']['en']}")
    
    if results['by_sheet']:
        logger.info(f"\n📊 Por pestaña:")
        for sheet, stats in results['by_sheet'].items():
            logger.info(f"   - {sheet}: {stats['processed']} procesados, {stats['failed']} fallidos")
    
    if results['failed']:
        logger.warning(f"\n❌ Archivos fallidos:")
        for failed in results['failed']:
            logger.warning(f"   - {failed['file']} ({failed['sheet']}): {failed.get('error', 'Unknown error')}")
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("✅ PROCESO COMPLETADO")
    logger.info("="*80)
    logger.info(f"\n📁 Markdowns guardados en:")
    logger.info(f"   - Español: {output_md_dir / 'processed_es'}")
    logger.info(f"   - Inglés: {output_md_dir / 'processed_en'}")
    logger.info(f"\n📋 Metadata guardada en: {metadata_extraction_dir}")
    
    # Información sobre archivos eliminados
    if results['processed']:
        logger.info(f"\n🗑️ Archivos eliminados de datasources: {len(results['processed'])}")
        logger.info(f"   (Solo archivos procesados exitosamente fueron eliminados)")
    
    if results['failed']:
        logger.warning(f"\n⚠️ Archivos con errores NO fueron eliminados: {len(results['failed'])}")
        logger.warning(f"   Revisa los errores y vuelve a ejecutar el script después de corregirlos")
    
    # Información sobre próximos pasos
    if results['by_language']['es'] > 0:
        logger.info(f"\n💡 Próximos pasos:")
        logger.info(f"   1. Traducir documentos en español a inglés:")
        logger.info(f"      python src/translation/translate_documents_batch.py --input-dir {output_md_dir / 'processed_es'} --output-dir {output_md_dir / 'processed_en'}")
        logger.info(f"   2. Ingestar a Qdrant:")
        logger.info(f"      python src/ingestion/test_recursive_character_chunking.py")
    else:
        logger.info(f"\n💡 Próximo paso: Ingestar a Qdrant")
        logger.info(f"   python src/ingestion/test_recursive_character_chunking.py")
    
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    main()
