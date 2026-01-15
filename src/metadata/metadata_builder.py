#!/usr/bin/env python3
"""
Metadata Builder - Construcción de metadata completa para chunks

Este módulo construye metadata completa paso a paso:
1. Lee metadata de source, extraction, translation
2. Completa campos obligatorios según catalogo-metadata.xlsx
3. Obtiene legal_weight e is_primary_source desde jerarquía normativa
4. Genera metadata intermedia y final para ingesta en Qdrant

Estructura de metadata:
- source: output/metadata/source/{pestaña}/{document_id}_source.json
- extraction: output/metadata/extraction/{pestaña}/{document_id}_extraction.json
- translation: output/metadata/translation/{pestaña}/{document_id}_translated.json
- chunking (intermedia): output/metadata/chunking/{pestaña}/{document_id}_chunking.json
- final: output/metadata/final/{pestaña}/{document_id}_final.json
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core import get_logger
from src.utils.excel_parser_catalogo_metadata import load_metadata_catalog
from src.metadata.text_structure_extractor import (
    TextStructureExtractor,
    generate_code_variations,
    parse_list_field,
    generate_citation_format,
    generate_short_citation,
    generate_display_title,
    determine_priority_level
)

logger = get_logger(__name__)

# Load environment
load_dotenv()


class MetadataBuilder:
    """
    Constructor de metadata completa para documentos y chunks.
    
    Construye metadata paso a paso desde source hasta final,
    completando campos obligatorios según el catálogo de metadata.
    """
    
    def __init__(self, project_root: Path = None):
        """
        Inicializa el builder.
        
        Args:
            project_root: Raíz del proyecto. Si es None, se detecta automáticamente.
        """
        if project_root is None:
            project_root = Path(__file__).parent.parent.parent
        
        self.project_root = Path(project_root)
        self.metadata_source_dir = self.project_root / "output" / "metadata" / "source"
        self.metadata_extraction_dir = self.project_root / "output" / "metadata" / "extraction"
        self.metadata_translation_dir = self.project_root / "output" / "metadata" / "translation"
        self.metadata_chunking_dir = self.project_root / "output" / "metadata" / "chunking"
        self.metadata_final_dir = self.project_root / "output" / "metadata" / "final"
        
        # Cargar catálogo de metadata
        catalog_path = self.project_root / "data" / "metadata" / "catalogo-metadata.xlsx"
        try:
            self.catalog = load_metadata_catalog(catalog_path)
            logger.info("✅ Catálogo de metadata cargado")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo cargar catálogo de metadata: {e}")
            self.catalog = None
        
        # Inicializar extractor de estructura
        self.structure_extractor = TextStructureExtractor()
        
        # Crear directorios si no existen
        self.metadata_chunking_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_final_dir.mkdir(parents=True, exist_ok=True)
    
    def load_source_metadata(self, document_id: str, sheet: str = None) -> Optional[Dict]:
        """
        Carga metadata desde source.
        
        Args:
            document_id: ID del documento
            sheet: Nombre de la pestaña (opcional, busca en todas si no se especifica)
        
        Returns:
            Dict con metadata source o None
        """
        if sheet:
            source_file = self.metadata_source_dir / sheet / f"{document_id}_source.json"
            if source_file.exists():
                try:
                    with open(source_file, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                        metadata['_sheet'] = sheet
                        return metadata
                except Exception as e:
                    logger.warning(f"Error leyendo {source_file}: {e}")
        else:
            # Buscar en todas las pestañas
            for sheet_dir in self.metadata_source_dir.iterdir():
                if not sheet_dir.is_dir():
                    continue
                source_file = sheet_dir / f"{document_id}_source.json"
                if source_file.exists():
                    try:
                        with open(source_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            metadata['_sheet'] = sheet_dir.name
                            return metadata
                    except Exception as e:
                        logger.warning(f"Error leyendo {source_file}: {e}")
        
        return None
    
    def load_extraction_metadata(self, document_id: str, sheet: str) -> Optional[Dict]:
        """Carga metadata desde extraction."""
        extraction_file = self.metadata_extraction_dir / sheet / f"{document_id}_extraction.json"
        if extraction_file.exists():
            try:
                with open(extraction_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error leyendo {extraction_file}: {e}")
        return None
    
    def load_translation_metadata(self, document_id: str, sheet: str) -> Optional[Dict]:
        """Carga metadata desde translation."""
        translation_file = self.metadata_translation_dir / sheet / f"{document_id}_translated.json"
        if translation_file.exists():
            try:
                with open(translation_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error leyendo {translation_file}: {e}")
        return None
    
    def build_document_metadata(self, document_id: str, sheet: str) -> Optional[Dict]:
        """
        Construye metadata completa del documento combinando todas las fuentes.
        
        Args:
            document_id: ID del documento
            sheet: Nombre de la pestaña
        
        Returns:
            Dict con metadata completa o None
        """
        # Cargar metadata de todas las fuentes
        source_meta = self.load_source_metadata(document_id, sheet)
        if not source_meta:
            logger.error(f"No se encontró metadata source para {document_id}")
            return None
        
        extraction_meta = self.load_extraction_metadata(document_id, sheet)
        translation_meta = self.load_translation_metadata(document_id, sheet)
        
        # Construir metadata base desde source
        metadata = {
            "document_id": document_id,
            "sheet": sheet,
            "metadata_version": "3.0",
            "generated_at": datetime.now().isoformat(),
            "sources": {
                "client_metadata": True,
                "elastika_metadata": True,
                "merged_at": datetime.now().isoformat()
            }
        }
        
        # Construir sección general
        general = self._build_general_metadata(source_meta, extraction_meta, translation_meta)
        metadata["document_metadata"] = {
            "general": general
        }
        
        # Construir sección extraction_information
        extraction_info = self._build_extraction_information(extraction_meta, source_meta)
        if extraction_info:
            metadata["document_metadata"]["extraction_information"] = extraction_info
        
        # Construir sección normative_info
        normative_info = self._build_normative_info(source_meta)
        if normative_info:
            metadata["document_metadata"]["normative_info"] = normative_info
        
        # Construir sección normative_hierarchy
        normative_hierarchy = self._build_normative_hierarchy(source_meta)
        if normative_hierarchy:
            metadata["document_metadata"]["normative_hierarchy"] = normative_hierarchy
        
        # Construir sección document_classification
        document_classification = self._build_document_classification(source_meta)
        if document_classification:
            metadata["document_metadata"]["document_classification"] = document_classification
        
        # Construir sección temporal_context
        temporal_context = self._build_temporal_context(source_meta)
        if temporal_context:
            metadata["document_metadata"]["temporal_context"] = temporal_context
        
        # Construir sección relationships_document
        relationships = self._build_relationships(source_meta)
        if relationships:
            metadata["document_metadata"]["relationships_document"] = relationships
        
        return metadata
    
    def _build_general_metadata(self, source: Dict, extraction: Optional[Dict], translation: Optional[Dict]) -> Dict:
        """Construye metadata general."""
        sincro = source.get("sincro", {})
        temp = source.get("temp", {})
        
        general = {
            "document_id": source.get("sincro", {}).get("document_id") or source.get("document_id"),
            "source_file": sincro.get("source_file") or temp.get("nombre archivo", ""),
            "book_title": sincro.get("book_title", ""),
            "language": extraction.get("language") if extraction else sincro.get("language", "en"),
            "total_pages": temp.get("Nro. páginas") or extraction.get("total_pages") if extraction else None,
            "file_size_mb": temp.get("peso (MB)") or extraction.get("file_size_mb") if extraction else None
        }
        
        # source_file_hash (opcional, pendiente por ahora)
        # general["source_file_hash"] = None
        
        return general
    
    def _build_extraction_information(self, extraction: Optional[Dict], source: Dict) -> Dict:
        """Construye metadata de información de extracción."""
        if not extraction:
            return {
                "markdown_length": None,
                "docx_conversion": False,
                "translated_en": False,
                "text_extraction_method": "mistral_ocr",
                "mistral_ocr": True
            }
        
        return {
            "markdown_length": extraction.get("markdown_length"),
            "docx_conversion": extraction.get("docx_conversion", False),
            "translated_en": extraction.get("translated_en", False),
            "text_extraction_method": extraction.get("text_extraction_method", "mistral_ocr"),
            "mistral_ocr": extraction.get("mistral_ocr", True)
        }
    
    def _build_normative_info(self, source: Dict) -> Dict:
        """Construye metadata de información normativa."""
        sincro = source.get("sincro", {})
        
        return {
            "code": sincro.get("code", ""),
            "full_name": sincro.get("full_name", ""),
            "edition": sincro.get("edition", ""),
            "provider": sincro.get("provider", ""),
            "provider_full_name": sincro.get("provider_full_name", ""),
            "country": sincro.get("country", ""),
            "scope": sincro.get("scope", ""),
            "status": sincro.get("status", "vigente")
        }
    
    def _build_normative_hierarchy(self, source: Dict) -> Dict:
        """Construye metadata de jerarquía normativa."""
        sincro = source.get("sincro", {})
        jerarquia_normativa = sincro.get("jerarquia_normativa")
        
        if jerarquia_normativa is None:
            logger.warning("jerarquia_normativa no encontrada en source metadata")
            return {
                "jerarquia_normativa": None,
                "legal_weight": None,
                "is_primary_source": None
            }
        
        # Obtener legal_weight e is_primary_source desde catálogo
        legal_weight = None
        is_primary_source = None
        
        if self.catalog:
            hierarchy_info = self.catalog.get_hierarchy_info(jerarquia_normativa)
            if hierarchy_info:
                legal_weight = hierarchy_info.get("legal_weight")
                is_primary_source = hierarchy_info.get("is_primary_source")
        
        # Generar code_variations si no existen (usando la misma función que en chunks)
        code = sincro.get("code", "")
        code_variations = sincro.get("code_variations") or []
        if not code_variations and code:
            code_variations = generate_code_variations(code)
        
        return {
            "jerarquia_normativa": jerarquia_normativa,
            "legal_weight": legal_weight,
            "is_primary_source": is_primary_source,
            "is_base_regulation": sincro.get("is_base_regulation"),
            "code_variations": code_variations,
            "regulates": sincro.get("regulates") or [],
            "regulated_by": sincro.get("regulated_by"),
            "thematic_area": sincro.get("thematic_area", "")
        }
    
    def _build_document_classification(self, source: Dict) -> Dict:
        """Construye metadata de clasificación del documento."""
        sincro = source.get("sincro", {})
        
        # Parsear disciplina y aplicabilidad (pueden ser strings separados por comas)
        disciplina = sincro.get("disciplina", "")
        aplicabilidad = sincro.get("aplicabilidad")
        
        return {
            "tipo_principal": sincro.get("tipo_principal", ""),
            "tipo_secundario": sincro.get("tipo_secundario", ""),
            "sector": sincro.get("sector", ""),
            "disciplina": parse_list_field(disciplina),
            "aplicabilidad": parse_list_field(aplicabilidad)
        }
    
    def _build_temporal_context(self, source: Dict) -> Dict:
        """Construye metadata de contexto temporal."""
        sincro = source.get("sincro", {})
        
        return {
            "publication_date": sincro.get("publication_date"),
            "effective_date": sincro.get("effective_date"),
            "expiration_date": sincro.get("expiration_date"),
            "supersedes": sincro.get("supersedes"),
            "superseded_by": sincro.get("superseded_by"),
            "ingestion_date": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "version_hash": self._generate_version_hash(source)
        }
    
    def _build_relationships(self, source: Dict) -> Dict:
        """Construye metadata de relaciones con otras normas."""
        sincro = source.get("sincro", {})
        
        return {
            "related_standards": sincro.get("related_standards") or [],
            "complementary_norms": sincro.get("complementary_norms") or [],
            "conflicts_with": sincro.get("conflicts_with") or [],
            "derived_from": sincro.get("derived_from"),
            "parent_document_id": sincro.get("document_id")
            # Nota: sibling_chunks NO se incluye aquí porque es información a nivel de chunks, no de documento
        }
    
    def _generate_version_hash(self, source: Dict) -> str:
        """Genera hash de versión del documento."""
        # Usar document_id y timestamp para generar hash
        content = f"{source.get('sincro', {}).get('document_id', '')}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def build_chunk_metadata(self, document_metadata: Dict, chunk_index: int, chunk_content: str, 
                            total_chunks: int, chunking_config: Dict, previous_structure: Optional[Dict] = None) -> Dict:
        """
        Construye metadata completa para un chunk individual.
        
        Args:
            document_metadata: Metadata completa del documento
            chunk_index: Índice del chunk (0-based)
            chunk_content: Contenido del chunk
            total_chunks: Total de chunks del documento
            chunking_config: Configuración de chunking (method, size, overlap)
            previous_structure: Estructura del chunk anterior (para mantener contexto)
        
        Returns:
            Dict con metadata completa del chunk
        """
        doc_meta = document_metadata.get("document_metadata", {})
        general = doc_meta.get("general", {})
        normative_info = doc_meta.get("normative_info", {})
        normative_hierarchy = doc_meta.get("normative_hierarchy", {})
        document_classification = doc_meta.get("document_classification", {})
        temporal_context = doc_meta.get("temporal_context", {})
        relationships = doc_meta.get("relationships_document", {})
        
        # Extraer estructura del texto (pasar code y edition para full_reference)
        code = normative_info.get("code", "")
        edition = str(normative_info.get("edition", ""))
        structure = self.structure_extractor.extract_structure(chunk_content, previous_structure, code, edition)
        
        # Detectar tipo de chunk
        chunk_type = self.structure_extractor.detect_chunk_type(chunk_content)
        
        # Obtener información de source para campos adicionales
        source_meta = self.load_source_metadata(general.get("document_id"), document_metadata.get("sheet"))
        sincro = source_meta.get("sincro", {}) if source_meta else {}
        
        # Generar sibling_chunks (chunks contiguos)
        sibling_chunks = []
        if chunk_index > 0:
            sibling_chunks.append(chunk_index - 1)
        if chunk_index < total_chunks - 1:
            sibling_chunks.append(chunk_index + 1)
        
        # Generar code_variations si no existen
        code = normative_info.get("code", "")
        code_variations = normative_hierarchy.get("code_variations", [])
        if not code_variations and code:
            code_variations = generate_code_variations(code)
        
        # Generar citaciones
        edition = str(normative_info.get("edition", ""))
        citation_format = generate_citation_format(
            code, edition, structure.get("article"), structure.get("chapter"), structure.get("section")
        )
        short_citation = generate_short_citation(code, edition, structure.get("article"))
        
        # Generar display_title
        display_title = generate_display_title(
            structure.get("article_title"),
            structure.get("section_title"),
            structure.get("chapter_title"),
            general.get("book_title")
        )
        
        # Determinar priority_level
        priority_level = determine_priority_level(
            structure.get("level", 5),
            normative_hierarchy.get("is_primary_source"),
            normative_hierarchy.get("legal_weight")
        )
        
        # Parsear campos de lista desde source
        disciplina = parse_list_field(document_classification.get("disciplina", []))
        aplicabilidad = parse_list_field(document_classification.get("aplicabilidad", []))
        topic_category = sincro.get("topic_category")
        subtopics = parse_list_field(sincro.get("subtopics"))
        keywords_manual = parse_list_field(sincro.get("keywords_manual"))
        
        # Construir metadata del chunk
        chunk_metadata = {
            # Identificación del documento
            "document_id": general.get("document_id"),
            "source_file": general.get("source_file"),
            "book_title": general.get("book_title"),
            "language": general.get("language"),
            
            # Información normativa
            "code": normative_info.get("code"),
            "full_name": normative_info.get("full_name"),
            "edition": normative_info.get("edition"),
            "provider": normative_info.get("provider"),
            "provider_full_name": normative_info.get("provider_full_name"),
            "country": normative_info.get("country"),
            "scope": normative_info.get("scope"),
            "status": normative_info.get("status"),
            
            # Jerarquía normativa
            "jerarquia_normativa": normative_hierarchy.get("jerarquia_normativa"),
            "legal_weight": normative_hierarchy.get("legal_weight"),
            "is_primary_source": normative_hierarchy.get("is_primary_source"),
            "is_base_regulation": normative_hierarchy.get("is_base_regulation"),
            "code_variations": code_variations,
            "regulates": normative_hierarchy.get("regulates", []),
            "regulated_by": normative_hierarchy.get("regulated_by"),
            "thematic_area": normative_hierarchy.get("thematic_area", ""),
            
            # Clasificación
            "tipo_principal": document_classification.get("tipo_principal"),
            "tipo_secundario": document_classification.get("tipo_secundario"),
            "sector": document_classification.get("sector"),
            "disciplina": disciplina,
            "aplicabilidad": aplicabilidad,
            
            # Estructura jerárquica del chunk
            "level": structure.get("level", 5),
            "level_name": structure.get("level_name", ""),
            "chapter": structure.get("chapter"),
            "chapter_title": structure.get("chapter_title", ""),
            "section": structure.get("section"),
            "section_title": structure.get("section_title", ""),
            "subsection": structure.get("subsection"),
            "subsection_title": structure.get("subsection_title", ""),
            "article": structure.get("article"),
            "article_title": structure.get("article_title", ""),
            "full_reference": structure.get("full_reference"),
            
            # Información del chunk
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "chunk_size": len(chunk_content),
            "chunk_words": len(chunk_content.split()),
            "chunking_method": chunking_config.get("method", "recursive_character"),
            "target_chunk_size": chunking_config.get("target_chunk_size", 1000),
            "chunk_overlap": chunking_config.get("chunk_overlap", 200),
            "is_header_chunk": chunk_type.get("is_header_chunk", False),
            "is_table_chunk": chunk_type.get("is_table_chunk", False),
            "is_list_chunk": chunk_type.get("is_list_chunk", False),
            "has_citations": chunk_type.get("has_citations", False),
            
            # Categorización y keywords
            "topic_category": topic_category,
            "subtopics": subtopics,
            "keywords_manual": keywords_manual,
            "keywords_auto": [],  # Se puede completar con TF-IDF/NER si se requiere
            
            # Contexto temporal
            "publication_date": temporal_context.get("publication_date"),
            "effective_date": temporal_context.get("effective_date"),
            "expiration_date": temporal_context.get("expiration_date"),
            "supersedes": temporal_context.get("supersedes"),
            "superseded_by": temporal_context.get("superseded_by"),
            "ingestion_date": temporal_context.get("ingestion_date"),
            "last_updated": temporal_context.get("last_updated"),
            "version_hash": temporal_context.get("version_hash"),
            
            # Relaciones
            "related_standards": relationships.get("related_standards", []),
            "complementary_norms": relationships.get("complementary_norms", []),
            "conflicts_with": relationships.get("conflicts_with", []),
            "derived_from": relationships.get("derived_from"),
            "parent_document_id": general.get("document_id"),
            "sibling_chunks": sibling_chunks,
            
            # Metadatos de presentación
            "citation_format": citation_format,
            "short_citation": short_citation,
            "display_title": display_title,
            "priority_level": priority_level
        }
        
        return chunk_metadata
    
    def save_chunking_metadata(self, document_id: str, sheet: str, document_metadata: Dict, 
                               chunking_stats: Dict, chunking_config: Dict) -> Path:
        """
        Guarda metadata intermedia de chunking.
        
        Args:
            document_id: ID del documento
            sheet: Nombre de la pestaña
            document_metadata: Metadata completa del documento
            chunking_stats: Estadísticas de chunking
            chunking_config: Configuración de chunking
        
        Returns:
            Path al archivo guardado
        """
        sheet_dir = self.metadata_chunking_dir / sheet
        sheet_dir.mkdir(parents=True, exist_ok=True)
        
        # Metadata solo relacionada con chunking (sin document_metadata)
        chunking_metadata = {
            "document_id": document_id,
            "sheet": sheet,
            "chunking_statistics": chunking_stats,
            "chunking_configuration": chunking_config,
            "generated_at": datetime.now().isoformat()
        }
        
        output_file = sheet_dir / f"{document_id}_chunking.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(chunking_metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Metadata de chunking guardada: {output_file}")
        return output_file
    
    def save_final_metadata(self, document_id: str, sheet: str, document_metadata: Dict,
                           chunking_stats: Dict, chunking_config: Dict, chunks: List[Dict]) -> Path:
        """
        Guarda metadata final para ingesta en Qdrant siguiendo el template.
        
        Args:
            document_id: ID del documento
            sheet: Nombre de la pestaña
            document_metadata: Metadata completa del documento
            chunking_stats: Estadísticas de chunking
            chunking_config: Configuración de chunking
            chunks: Lista de chunks con su metadata
        
        Returns:
            Path al archivo guardado
        """
        sheet_dir = self.metadata_final_dir / sheet
        sheet_dir.mkdir(parents=True, exist_ok=True)
        
        # Construir metadata final según template
        final_metadata = {
            "document_id": document_id,
            "metadata_version": "3.0",
            "generated_at": datetime.now().isoformat() + "Z",
            "sources": {
                "client_metadata": True,
                "elastika_metadata": True,
                "merged_at": datetime.now().isoformat() + "Z"
            },
            "document_metadata": document_metadata.get("document_metadata", {}),
            "chunking_statistics": chunking_stats,
            "chunking_configuration": {
                "chunking_method": chunking_config.get("method", "recursive_character"),
                "chunk_size": chunking_config.get("target_chunk_size", 1000),
                "chunk_overlap": chunking_config.get("chunk_overlap", 200),
                "model": "nomic-embed-text",
                "embedding_dimension": 768,
                "separators": chunking_config.get("separators", [])
            },
            "chunks": chunks
        }
        
        output_file = sheet_dir / f"{document_id}_final.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Metadata final guardada: {output_file}")
        return output_file


if __name__ == "__main__":
    """Script de prueba"""
    builder = MetadataBuilder()
    
    # Probar con un documento
    document_id = "NFPA_11_2024_ED_2024"
    sheet = "NFPA"
    
    print(f"🔍 Construyendo metadata para {document_id}...")
    metadata = builder.build_document_metadata(document_id, sheet)
    
    if metadata:
        print("✅ Metadata construida exitosamente")
        print(f"📊 Campos generales: {len(metadata.get('document_metadata', {}).get('general', {}))}")
        print(f"📊 Jerarquía normativa: {metadata.get('document_metadata', {}).get('normative_hierarchy', {})}")
    else:
        print("❌ No se pudo construir metadata")

