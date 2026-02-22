#!/usr/bin/env python3
"""
Script de Conversión y Preparación de Documentos (Fase Datasources)

Convierte DOC/DOCX a PDF y copia PDFs a output/datasources/
Procesa archivos desde data/input/ usando metadata de output/metadata/source/

Flujo:
1. Lee JSONs de metadata desde output/metadata/source/{pestaña}/
2. Filtra documentos con condición "por ingestar" o "Por cargar"
3. Busca archivos en data/input/ por source_file
4. Si es DOC/DOCX → convierte a PDF
5. Si es PDF → copia
6. Guarda en output/datasources/{pestaña}/ como {document_id}_source.pdf
7. Mueve ORIGINALES a data/processed/{timestamp}/ (backup con formato original)

Almacenamiento:
- data/input/: Temporal, archivos originales (se eliminan después de procesar)
- data/processed/{timestamp}/: Backup de originales (DOC, DOCX o PDF original)
- output/datasources/{pestaña}/: Temporal, solo PDFs para generar markdown
- output/datasources/ se limpia después de la ingesta

Sufijo _source: indica archivo fuente listo para procesamiento de markdown
"""

import os
import sys
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core import get_logger
from src.utils.excel_parser_base_conocimiento import load_excel_metadata

# Setup logging
logger = get_logger(__name__)

# Load environment
load_dotenv()

# Condiciones que indican que un archivo debe ser procesado
CONDITIONS_TO_PROCESS = ["por ingestar", "por cargar"]

# Sufijo para archivos en fase datasources
DATASOURCE_SUFFIX = "_source"


def convert_doc_to_pdf(doc_path: Path, pdf_path: Path) -> bool:
    """
    Convierte un archivo DOC o DOCX a PDF.
    
    Métodos de conversión (en orden de preferencia):
    1. LibreOffice (soffice) - mejor calidad, soporta DOC y DOCX
    2. docx2pdf - solo DOCX, requiere LibreOffice/Word
    3. python-docx + reportlab - solo DOCX, básico
    
    Args:
        doc_path: Ruta al archivo DOC o DOCX
        pdf_path: Ruta donde guardar el PDF
    
    Returns:
        True si la conversión fue exitosa, False en caso contrario
    """
    file_ext = doc_path.suffix.lower()
    
    try:
        # Método 1: LibreOffice (funciona con DOC y DOCX)
        try:
            import subprocess
            
            logger.info(f"Convirtiendo {file_ext.upper()} a PDF usando LibreOffice: {doc_path.name}")
            
            # Crear directorio de salida si no existe
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Usar soffice para convertir
            result = subprocess.run([
                'soffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', str(pdf_path.parent),
                str(doc_path)
            ], capture_output=True, text=True, timeout=120)
            
            # LibreOffice genera el PDF con el nombre original
            expected_pdf = pdf_path.parent / f"{doc_path.stem}.pdf"
            
            if expected_pdf.exists():
                # Renombrar al nombre deseado si es diferente
                if expected_pdf != pdf_path:
                    shutil.move(str(expected_pdf), str(pdf_path))
                logger.info(f"✅ PDF generado: {pdf_path.name}")
                return True
            else:
                raise Exception(f"PDF no generado: {result.stderr}")
                
        except FileNotFoundError:
            logger.warning("LibreOffice (soffice) no disponible, intentando alternativa...")
        except subprocess.TimeoutExpired:
            logger.warning("Timeout en LibreOffice, intentando alternativa...")
        except Exception as e:
            logger.warning(f"Error con LibreOffice: {e}, intentando alternativa...")
        
        # Método 2: docx2pdf (solo DOCX)
        if file_ext == '.docx':
            try:
                from docx2pdf import convert
                logger.info(f"Convirtiendo DOCX a PDF usando docx2pdf: {doc_path.name}")
                convert(str(doc_path), str(pdf_path))
                logger.info(f"✅ PDF generado: {pdf_path.name}")
                return True
            except ImportError:
                logger.warning("docx2pdf no disponible, intentando alternativa...")
            except Exception as e:
                logger.warning(f"Error con docx2pdf: {e}, intentando alternativa...")
        
        # Método 3: python-docx + reportlab (solo DOCX, básico)
        if file_ext == '.docx':
            try:
                from docx import Document
                from reportlab.lib.pagesizes import letter
                from reportlab.lib.styles import getSampleStyleSheet
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                
                logger.info(f"Convirtiendo DOCX a PDF usando python-docx + reportlab: {doc_path.name}")
                
                doc = Document(doc_path)
                pdf_doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
                styles = getSampleStyleSheet()
                story = []
                
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        p = Paragraph(paragraph.text, styles['Normal'])
                        story.append(p)
                        story.append(Spacer(1, 12))
                
                pdf_doc.build(story)
                logger.info(f"✅ PDF generado: {pdf_path.name}")
                return True
                
            except ImportError:
                logger.error("Ni LibreOffice, docx2pdf ni reportlab están disponibles.")
                logger.error("Opciones de instalación:")
                logger.error("  - apt install libreoffice (recomendado)")
                logger.error("  - pip install docx2pdf (requiere LibreOffice/Word)")
                logger.error("  - pip install python-docx reportlab")
                return False
            except Exception as e:
                logger.error(f"Error en conversión alternativa: {e}")
                return False
        
        # Si es DOC y no hay LibreOffice, no hay alternativa
        if file_ext == '.doc':
            logger.error("Archivos DOC requieren LibreOffice para conversión.")
            logger.error("Instala: apt install libreoffice")
            return False
            
    except Exception as e:
        logger.error(f"Error convirtiendo {file_ext.upper()} a PDF: {e}")
        return False
    
    return False


def clean_directory(directory: Path) -> bool:
    """
    Limpia todos los archivos de un directorio.
    
    Args:
        directory: Directorio a limpiar
    
    Returns:
        True si fue exitoso, False en caso contrario
    """
    try:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            return True
        
        # Eliminar todos los archivos y subdirectorios
        for file in directory.iterdir():
            if file.is_file():
                file.unlink()
                logger.debug(f"Archivo eliminado: {file.name}")
            elif file.is_dir():
                shutil.rmtree(file)
                logger.debug(f"Carpeta eliminada: {file.name}")
        
        logger.info(f"✅ Directorio limpiado: {directory}")
        return True
        
    except Exception as e:
        logger.error(f"Error limpiando directorio {directory}: {e}")
        return False


def get_documents_to_process(metadata_dir: Path) -> List[Dict]:
    """
    Lee todos los JSONs de metadata y filtra los que deben procesarse.
    
    Args:
        metadata_dir: Directorio con subcarpetas de metadata (output/metadata/source/)
    
    Returns:
        Lista de documentos con condición "por ingestar" o "Por cargar"
    """
    documents = []
    
    if not metadata_dir.exists():
        logger.error(f"Directorio de metadata no existe: {metadata_dir}")
        return documents
    
    # Recorrer cada subcarpeta (pestaña)
    for sheet_dir in metadata_dir.iterdir():
        if not sheet_dir.is_dir():
            continue
        
        sheet_name = sheet_dir.name
        
        # Leer cada JSON en la subcarpeta
        for json_file in sheet_dir.glob("*_source.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    doc = json.load(f)
                
                # Verificar condición
                condicion = doc.get('temp', {}).get('condición', '').lower().strip()
                
                if condicion in CONDITIONS_TO_PROCESS:
                    doc['_json_path'] = str(json_file)
                    documents.append(doc)
                    logger.debug(f"Documento a procesar: {doc.get('document_id')} ({sheet_name})")
                    
            except Exception as e:
                logger.warning(f"Error leyendo {json_file}: {e}")
    
    logger.info(f"📋 Encontrados {len(documents)} documentos para procesar")
    return documents


def process_documents(
    documents: List[Dict],
    input_dir: Path,
    output_dir: Path,
    processed_dir: Path
) -> Dict[str, List[str]]:
    """
    Procesa los documentos: convierte DOCX a PDF o copia PDFs.
    
    Args:
        documents: Lista de documentos a procesar
        input_dir: Directorio con archivos de entrada (data/input/)
        output_dir: Directorio de salida (output/datasources/)
        processed_dir: Directorio para backup de originales (data/processed/)
    
    Returns:
        Dict con listas de archivos procesados, convertidos, copiados y errores
    """
    results = {
        "processed": [],
        "converted": [],
        "copied": [],
        "not_found": [],
        "errors": []
    }
    
    # Limpiar output/datasources/
    logger.info("🧹 Limpiando output/datasources/...")
    clean_directory(output_dir)
    
    # Crear directorio de procesados si no existe
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Procesar cada documento
    for doc in documents:
        try:
            document_id = doc.get('document_id')
            source_file = doc.get('sincro', {}).get('source_file')
            sheet_name = doc.get('_sheet')
            
            if not document_id or not source_file:
                logger.warning(f"Documento sin document_id o source_file: {doc}")
                results["errors"].append(f"Documento sin datos completos")
                continue
            
            logger.info(f"\n{'='*80}")
            logger.info(f"📄 Procesando: {source_file}")
            logger.info(f"   document_id: {document_id}")
            logger.info(f"   pestaña: {sheet_name}")
            logger.info(f"{'='*80}")
            
            # Buscar archivo en data/input/
            input_file = input_dir / source_file
            
            if not input_file.exists():
                # Intentar con diferentes variaciones de nombre
                found = False
                for f in input_dir.iterdir():
                    if f.name.lower() == source_file.lower():
                        input_file = f
                        found = True
                        break
                
                if not found:
                    logger.warning(f"⚠️ Archivo no encontrado en data/input/: {source_file}")
                    results["not_found"].append(source_file)
                    continue
            
            # Crear subcarpeta para la pestaña
            sheet_output_dir = output_dir / sheet_name
            sheet_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Nombre de salida: {document_id}_source.pdf
            output_filename = f"{document_id}{DATASOURCE_SUFFIX}.pdf"
            output_path = sheet_output_dir / output_filename
            
            # Determinar tipo de archivo y procesar
            file_ext = input_file.suffix.lower()
            
            if file_ext in ['.doc', '.docx']:
                logger.info(f"📝 Tipo: {file_ext.upper()} → Convertir a PDF")
                
                if convert_doc_to_pdf(input_file, output_path):
                    results["converted"].append(f"{sheet_name}/{output_filename}")
                    results["processed"].append({
                        "document_id": document_id,
                        "source_file": source_file,
                        "output_file": f"{sheet_name}/{output_filename}",
                        "action": "converted",
                        "original_format": file_ext
                    })
                    logger.info(f"✅ Convertido: {output_filename}")
                else:
                    results["errors"].append(f"{source_file}: Error en conversión")
                    logger.error(f"❌ Error convirtiendo {source_file}")
                    continue
                    
            elif file_ext == '.pdf':
                logger.info("📄 Tipo: PDF → Copiar")
                
                try:
                    shutil.copy2(input_file, output_path)
                    results["copied"].append(f"{sheet_name}/{output_filename}")
                    results["processed"].append({
                        "document_id": document_id,
                        "source_file": source_file,
                        "output_file": f"{sheet_name}/{output_filename}",
                        "action": "copied",
                        "original_format": file_ext
                    })
                    logger.info(f"✅ Copiado: {output_filename}")
                except Exception as e:
                    results["errors"].append(f"{source_file}: Error copiando - {e}")
                    logger.error(f"❌ Error copiando {source_file}: {e}")
                    continue
            else:
                logger.warning(f"⚠️ Tipo de archivo no soportado: {file_ext}")
                results["errors"].append(f"{source_file}: Tipo no soportado ({file_ext})")
                continue
            
            # Mover archivo original a data/processed/{timestamp}/ (backup)
            # El archivo ORIGINAL (DOC, DOCX o PDF) se guarda en su formato original
            try:
                processed_file = processed_dir / source_file
                shutil.move(str(input_file), str(processed_file))
                logger.info(f"📦 Original ({file_ext}) movido a: {processed_file.relative_to(processed_dir.parent.parent)}")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo mover original a processed: {e}")
        
        except Exception as e:
            logger.error(f"❌ Error procesando documento: {e}")
            results["errors"].append(f"{doc.get('document_id', 'unknown')}: {str(e)}")
    
    return results


def main():
    """Función principal."""
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    input_dir = project_root / "data" / "input"
    output_dir = project_root / "output" / "datasources"
    metadata_dir = project_root / "output" / "metadata" / "source"
    
    # Crear timestamp para backup: processed/YYYYMMDD_HHMMSS/
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processed_dir = project_root / "data" / "processed" / timestamp
    
    # Validar paths
    if not input_dir.exists():
        logger.warning(f"Directorio de entrada no existe, creándolo: {input_dir}")
        input_dir.mkdir(parents=True, exist_ok=True)
    
    if not metadata_dir.exists():
        logger.error(f"Directorio de metadata no existe: {metadata_dir}")
        logger.error("Ejecuta primero: python src/utils/excel_parser_base_conocimiento.py")
        return
    
    logger.info("="*80)
    logger.info("🚀 CONVERSIÓN Y PREPARACIÓN DE DOCUMENTOS (Fase Datasources)")
    logger.info("="*80)
    logger.info(f"📂 Entrada: {input_dir}")
    logger.info(f"📂 Metadata: {metadata_dir}")
    logger.info(f"📂 Salida: {output_dir}")
    logger.info(f"📂 Backup: {processed_dir} (timestamp: {timestamp})")
    logger.info(f"🏷️ Sufijo: {DATASOURCE_SUFFIX}")
    logger.info(f"📋 Condiciones: {CONDITIONS_TO_PROCESS}")
    logger.info("")
    logger.info("📋 ALMACENAMIENTO:")
    logger.info("   - data/input/: Temporal, se elimina tras procesar")
    logger.info("   - data/processed/{timestamp}/: Backup de originales")
    logger.info("   - output/datasources/: Temporal, PDFs para markdown")
    logger.info("="*80 + "\n")
    
    # Paso 1: Obtener documentos a procesar desde metadata
    logger.info("📊 Paso 1: Leyendo metadata de documentos...")
    documents = get_documents_to_process(metadata_dir)
    
    if not documents:
        logger.warning("No hay documentos para procesar")
        logger.info("Verifica que existan documentos con condición 'por ingestar' o 'Por cargar'")
        return
    
    # Mostrar documentos encontrados
    logger.info(f"\n📋 Documentos a procesar ({len(documents)}):")
    for doc in documents:
        source_file = doc.get('sincro', {}).get('source_file', 'unknown')
        sheet = doc.get('_sheet', 'unknown')
        logger.info(f"   - {source_file} ({sheet})")
    
    # Paso 2: Procesar archivos
    logger.info("\n📁 Paso 2: Procesando archivos...")
    results = process_documents(documents, input_dir, output_dir, processed_dir)
    
    # Mostrar resumen
    logger.info("\n" + "="*80)
    logger.info("📊 RESUMEN DE PROCESAMIENTO")
    logger.info("="*80)
    logger.info(f"✅ Archivos procesados: {len(results['processed'])}")
    logger.info(f"📝 DOCX convertidos: {len(results['converted'])}")
    logger.info(f"📄 PDFs copiados: {len(results['copied'])}")
    logger.info(f"⚠️ No encontrados: {len(results['not_found'])}")
    logger.info(f"❌ Errores: {len(results['errors'])}")
    
    if results['processed']:
        logger.info(f"\n📋 Archivos en output/datasources/:")
        for item in results['processed']:
            logger.info(f"   ✅ {item['output_file']} ({item['action']})")
    
    if results['not_found']:
        logger.warning(f"\n⚠️ Archivos no encontrados en data/input/:")
        for f in results['not_found']:
            logger.warning(f"   - {f}")
    
    if results['errors']:
        logger.error(f"\n❌ Errores encontrados:")
        for e in results['errors']:
            logger.error(f"   - {e}")
    
    logger.info("\n" + "="*80)
    logger.info("✅ PROCESO COMPLETADO")
    logger.info("="*80)
    logger.info(f"\n📁 PDFs listos en: {output_dir}")
    logger.info(f"📦 Originales (formato original) en: {processed_dir}")
    logger.info("\n💡 Próximo paso: Generar markdown desde los PDFs")
    logger.info("   python src/extraction/generate_markdown.py")
    logger.info("\n⚠️ Recuerda: output/datasources/ es temporal, se limpia tras ingestar")


if __name__ == "__main__":
    main()
