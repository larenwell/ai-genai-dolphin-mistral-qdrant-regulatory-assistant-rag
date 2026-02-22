#!/usr/bin/env python3
"""
Pipeline de Traducción de Documentos (Paso 4 del Pipeline)

Procesa documentos desde processed_es/ y los traduce a inglés, guardándolos en processed_en/.
Genera metadata de traducción en output/metadata/translation/{pestaña}/{document_id}_translated.json

Flujo:
1. Lee documentos desde processed_es/{pestaña}/
2. Los documentos en processed_en/ se mantienen (ya están en inglés)
3. Traduce documentos desde processed_es/ a processed_en/{pestaña}/
4. Genera metadata de traducción en output/metadata/translation/{pestaña}/
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core import get_logger
from src.translation.translate_document import DocumentTranslator

# Setup logging
logger = get_logger(__name__)

# Load environment
load_dotenv()

# Directorios base
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROCESSED_ES_DIR = PROJECT_ROOT / "output" / "markdown" / "processed_es"
PROCESSED_EN_DIR = PROJECT_ROOT / "output" / "markdown" / "processed_en"
METADATA_TRANSLATE_DIR = PROJECT_ROOT / "output" / "metadata" / "translation"


def extract_document_id_from_filename(filename: str) -> str:
    """Extrae document_id del nombre del archivo markdown."""
    return Path(filename).stem


def create_translation_metadata(
    document_id: str,
    source_file: str,
    sheet: str,
    translated_en: bool,
    source_language: str = "es",
    target_language: str = "en",
    translation_method: str = "mistral",
    error: Optional[str] = None,
    translation_stats: Optional[Dict] = None
) -> Dict:
    """
    Crea metadata de traducción.
    
    Args:
        document_id: ID del documento
        source_file: Nombre del archivo fuente
        sheet: Pestaña/carpeta del documento
        translated_en: Si fue traducido exitosamente
        source_language: Idioma fuente (default: "es")
        target_language: Idioma destino (default: "en")
        translation_method: Método de traducción usado
        error: Mensaje de error si hubo fallo
        translation_stats: Estadísticas de traducción (chars, API calls, etc.)
    
    Returns:
        Dict con metadata de traducción
    """
    metadata = {
        "document_id": document_id,
        "source_file": source_file,
        "sheet": sheet,
        "translated_en": translated_en,
        "source_language": source_language,
        "target_language": target_language,
        "translation_method": translation_method,
        "processed_at": datetime.now().isoformat()
    }
    
    if error:
        metadata["error"] = error
    
    if translation_stats:
        metadata["translation_stats"] = translation_stats
    
    return metadata


def save_translation_metadata(metadata: Dict, sheet: str) -> Path:
    """
    Guarda metadata de traducción en output/metadata/translation/{sheet}/{document_id}_translated.json
    
    Args:
        metadata: Metadata de traducción
        sheet: Pestaña/carpeta
    
    Returns:
        Path al archivo guardado
    """
    output_dir = METADATA_TRANSLATE_DIR / sheet
    output_dir.mkdir(parents=True, exist_ok=True)
    
    document_id = metadata["document_id"]
    output_file = output_dir / f"{document_id}_translated.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    return output_file


def translate_document_file(
    input_file: Path,
    output_file: Path,
    translator: DocumentTranslator,
    timeout: int = 60
) -> Tuple[bool, Optional[Dict], Optional[str]]:
    """
    Traduce un archivo markdown.
    
    Args:
        input_file: Archivo de entrada (markdown en español)
        output_file: Archivo de salida (markdown en inglés)
        translator: Instancia de DocumentTranslator
        timeout: Timeout para traducción
    
    Returns:
        Tuple (success, stats, error_message)
    """
    try:
        # Verificar si ya existe traducción
        if output_file.exists():
            logger.info(f"⏭️  Traducción ya existe: {output_file.name}")
            return True, None, None
        
        # Traducir archivo
        success = translator.translate_file(
            str(input_file),
            str(output_file),
            source_lang="es",
            target_lang="en"
        )
        
        if success:
            # Obtener estadísticas del traductor
            stats = {
                "total_chars_translated": getattr(translator, 'total_chars_translated', 0),
                "api_calls_made": getattr(translator, 'api_calls_made', 0),
                "failed_chunks": getattr(translator, 'failed_chunks', [])
            }
            return True, stats, None
        else:
            return False, None, "Translation failed"
            
    except Exception as e:
        logger.error(f"Error traduciendo {input_file.name}: {e}")
        return False, None, str(e)


def get_translation_progress(input_dir: Path, output_dir: Path) -> tuple[List[str], List[str]]:
    """
    Obtiene el progreso de traducción comparando archivos de entrada y salida.
    
    Args:
        input_dir: Directorio con archivos fuente (español)
        output_dir: Directorio con archivos traducidos (inglés)
    
    Returns:
        Tuple (completed_files, remaining_files)
    """
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        return [], []
    
    input_files = set(f.name for f in input_dir.glob("*.md"))
    output_files = set(f.name for f in output_dir.glob("*.md"))
    
    completed = list(output_files)
    remaining = list(input_files - output_files)
    
    return completed, remaining


def process_sheet_translation(sheet: str, translator: DocumentTranslator, resume: bool = True) -> Dict:
    """
    Procesa la traducción de todos los documentos de una pestaña con capacidad de reanudación.
    
    Args:
        sheet: Nombre de la pestaña/carpeta
        translator: Instancia de DocumentTranslator
        resume: Si True, reanuda desde donde se quedó (omite archivos ya traducidos)
    
    Returns:
        Dict con estadísticas de procesamiento
    """
    stats = {
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "already_translated": 0
    }
    
    # Directorios
    input_dir = PROCESSED_ES_DIR / sheet
    output_dir = PROCESSED_EN_DIR / sheet
    
    if not input_dir.exists():
        logger.warning(f"Carpeta no encontrada: {input_dir}")
        return stats
    
    # Crear directorio de salida si no existe
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Obtener progreso de traducción
    completed, remaining = get_translation_progress(input_dir, output_dir)
    
    if resume and completed:
        logger.info(f"📊 Modo reanudación: {len(completed)} archivos ya traducidos, {len(remaining)} pendientes")
        md_files = [input_dir / f for f in remaining]
    else:
        md_files = list(input_dir.glob("*.md"))
    
    if not md_files:
        if completed:
            logger.info(f"✅ Todos los archivos ya están traducidos en {sheet}")
        else:
            logger.info(f"No se encontraron archivos .md en {input_dir}")
        return stats
    
    logger.info(f"📁 Procesando {len(md_files)} archivo(s) en {sheet}...")
    
    failed_files = []
    
    for idx, input_file in enumerate(md_files, 1):
        document_id = extract_document_id_from_filename(input_file.name)
        output_file = output_dir / input_file.name
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 Archivo {idx}/{len(md_files)}: {input_file.name}")
        logger.info(f"{'='*60}")
        
        # Verificar si ya existe en processed_en (ya traducido)
        if output_file.exists():
            logger.info(f"✅ Ya existe en processed_en: {output_file.name}")
            metadata = create_translation_metadata(
                document_id=document_id,
                source_file=input_file.name,
                sheet=sheet,
                translated_en=True
            )
            metadata["note"] = "Already exists in processed_en (document was already in English)"
            save_translation_metadata(metadata, sheet)
            stats["already_translated"] += 1
            continue
        
        try:
            # Traducir archivo
            success, translation_stats, error = translate_document_file(
                input_file,
                output_file,
                translator
            )
            
            # Crear y guardar metadata
            metadata = create_translation_metadata(
                document_id=document_id,
                source_file=input_file.name,
                sheet=sheet,
                translated_en=success,
                translation_stats=translation_stats,
                error=error
            )
            metadata_path = save_translation_metadata(metadata, sheet)
            
            if success:
                logger.info(f"✅ Traducido exitosamente: {input_file.name}")
                logger.info(f"📋 Metadata guardada: {metadata_path.relative_to(METADATA_TRANSLATE_DIR.parent)}")
                stats["processed"] += 1
            else:
                logger.error(f"❌ Error traduciendo: {input_file.name}")
                failed_files.append(input_file.name)
                stats["failed"] += 1
                
        except KeyboardInterrupt:
            logger.warning(f"\n⚠️  Interrumpido por el usuario. Progreso guardado.")
            logger.info(f"✅ Completados: {stats['processed']}/{idx-1}")
            logger.info(f"❌ Fallidos: {len(failed_files)}")
            if failed_files:
                logger.warning(f"Archivos fallidos: {', '.join(failed_files)}")
            # Guardar progreso parcial antes de salir
            break
        except Exception as e:
            logger.error(f"❌ Error inesperado traduciendo {input_file.name}: {e}")
            failed_files.append(input_file.name)
            stats["failed"] += 1
            continue
    
    if failed_files:
        logger.warning(f"\n⚠️  Archivos fallidos en {sheet}: {', '.join(failed_files)}")
    
    return stats


def main():
    """Función principal."""
    # Validar directorios
    if not PROCESSED_ES_DIR.exists():
        logger.error(f"Directorio processed_es no existe: {PROCESSED_ES_DIR}")
        logger.error("Ejecuta primero: python src/extraction/generate_markdown.py")
        return
    
    # Inicializar traductor
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        logger.error("❌ Error: MISTRAL_API_KEY no encontrada en las variables de entorno")
        return
    
    translator = DocumentTranslator(timeout_seconds=60)
    
    logger.info("="*80)
    logger.info("🌐 PIPELINE DE TRADUCCIÓN (Paso 4 del Pipeline)")
    logger.info("="*80)
    logger.info(f"📂 Entrada (español): {PROCESSED_ES_DIR}")
    logger.info(f"📂 Salida (inglés): {PROCESSED_EN_DIR}")
    logger.info(f"📂 Metadata: {METADATA_TRANSLATE_DIR}")
    logger.info("="*80 + "\n")
    
    # Obtener pestañas en processed_es
    sheets = [d.name for d in PROCESSED_ES_DIR.iterdir() if d.is_dir()]
    
    if not sheets:
        logger.warning("No se encontraron pestañas en processed_es/")
        return
    
    logger.info(f"📋 Pestañas encontradas: {', '.join(sheets)}\n")
    
    total_stats = {
        "processed": 0,
        "skipped": 0,
        "failed": 0,
        "already_translated": 0
    }
    
    # Procesar cada pestaña
    for sheet in sheets:
        logger.info(f"\n{'='*80}")
        logger.info(f"📁 Procesando pestaña: {sheet}")
        logger.info(f"{'='*80}")
        
        stats = process_sheet_translation(sheet, translator, resume=True)
        
        # Acumular estadísticas
        for key in total_stats:
            total_stats[key] += stats[key]
        
        logger.info(f"\n📊 Resumen {sheet}:")
        logger.info(f"   ✅ Traducidos: {stats['processed']}")
        logger.info(f"   ⏭️  Ya existían: {stats['already_translated']}")
        logger.info(f"   ❌ Fallidos: {stats['failed']}")
    
    # Resumen final
    logger.info("\n" + "="*80)
    logger.info("📊 RESUMEN FINAL")
    logger.info("="*80)
    logger.info(f"   ✅ Total traducidos: {total_stats['processed']}")
    logger.info(f"   ⏭️  Total ya existían: {total_stats['already_translated']}")
    logger.info(f"   ❌ Total fallidos: {total_stats['failed']}")
    logger.info("="*80)
    logger.info(f"\n📁 Archivos traducidos guardados en: {PROCESSED_EN_DIR}")
    logger.info(f"📋 Metadata guardada en: {METADATA_TRANSLATE_DIR}")
    logger.info("="*80 + "\n")


if __name__ == "__main__":
    main()

