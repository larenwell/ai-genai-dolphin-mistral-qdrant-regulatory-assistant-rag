#!/usr/bin/env python3
"""
Text Structure Extractor - Extrae información estructural del texto

Extrae información jerárquica del documento:
- Capítulos, secciones, subsecciones
- Artículos
- Niveles jerárquicos
- Referencias completas
"""

import re
from typing import Dict, Optional, List, Tuple
from src.core import get_logger

logger = get_logger(__name__)


class TextStructureExtractor:
    """Extractor de estructura jerárquica del texto."""
    
    def __init__(self):
        """Inicializa el extractor."""
        # Patrones para detectar estructuras
        self.chapter_patterns = [
            r'(?i)^\s*(?:cap[íi]tulo|chapter)\s+([IVXLCDM]+|\d+)\s*[:\-]?\s*(.+)?$',
            r'(?i)^\s*cap[íi]tulo\s+(\d+)\s*[:\-]?\s*(.+)?$',
            r'(?i)^\s*chapter\s+(\d+)\s*[:\-]?\s*(.+)?$',
            r'(?i)^\s*##\s+(?:cap[íi]tulo|chapter)\s+([IVXLCDM]+|\d+)\s*[:\-]?\s*(.+)?$'
        ]
        
        self.section_patterns = [
            r'(?i)^\s*(?:secci[óo]n|section)\s+(\d+\.\d+|\d+)\s*[:\-]?\s*(.+)?$',
            r'(?i)^\s*###\s+(?:secci[óo]n|section)\s+(\d+\.\d+|\d+)\s*[:\-]?\s*(.+)?$',
            r'^\s*(\d+\.\d+)\s+([^\n]+)$',  # Formato: "5.2 Título"
        ]
        
        self.subsection_patterns = [
            r'(?i)^\s*(?:subsecci[óo]n|subsection)\s+(\d+\.\d+\.\d+)\s*[:\-]?\s*(.+)?$',
            r'(?i)^\s*####\s+(?:subsecci[óo]n|subsection)\s+(\d+\.\d+\.\d+)\s*[:\-]?\s*(.+)?$',
            r'^\s*(\d+\.\d+\.\d+)\s+([^\n]+)$',  # Formato: "5.2.3 Título"
        ]
        
        self.article_patterns = [
            r'(?i)^\s*(?:art[íi]culo|art\.?)\s+(\d+)\s*[:\-]?\s*(.+)?$',
            r'(?i)^\s*art[íi]culo\s+(\d+)\s*\.\s*-\s*(.+)$',  # "Artículo 49.- Título"
        ]
    
    def extract_structure(self, chunk_content: str, previous_structure: Optional[Dict] = None, 
                         code: Optional[str] = None, edition: Optional[str] = None) -> Dict:
        """
        Extrae información estructural del chunk.
        
        Args:
            chunk_content: Contenido del chunk
            previous_structure: Estructura del chunk anterior (para mantener contexto)
        
        Returns:
            Dict con información estructural extraída
        """
        lines = chunk_content.split('\n')
        
        structure = {
            "level": 5,  # Por defecto: nivel general
            "level_name": "",
            "chapter": None,
            "chapter_title": "",
            "section": None,
            "section_title": "",
            "subsection": None,
            "subsection_title": "",
            "article": None,
            "article_title": "",
            "full_reference": None
        }
        
        # Si hay estructura previa, heredarla
        if previous_structure:
            structure.update(previous_structure)
        
        # Buscar en las primeras líneas del chunk
        for i, line in enumerate(lines[:10]):  # Revisar primeras 10 líneas
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Buscar artículo (máxima prioridad)
            article_match = self._match_patterns(line_stripped, self.article_patterns)
            if article_match:
                structure["article"] = int(article_match[0])
                structure["article_title"] = article_match[1].strip() if len(article_match) > 1 and article_match[1] else ""
                structure["level"] = 1
                structure["level_name"] = "articulo"
                # Buscar título en línea siguiente si no está en la misma
                if not structure["article_title"] and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not self._is_structure_line(next_line):
                        structure["article_title"] = next_line
                break
            
            # Buscar subsección
            subsection_match = self._match_patterns(line_stripped, self.subsection_patterns)
            if subsection_match:
                structure["subsection"] = subsection_match[0]
                structure["subsection_title"] = subsection_match[1].strip() if len(subsection_match) > 1 and subsection_match[1] else ""
                structure["level"] = 4
                structure["level_name"] = "subseccion"
                if not structure["subsection_title"] and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not self._is_structure_line(next_line):
                        structure["subsection_title"] = next_line
                break
            
            # Buscar sección
            section_match = self._match_patterns(line_stripped, self.section_patterns)
            if section_match:
                structure["section"] = section_match[0]
                structure["section_title"] = section_match[1].strip() if len(section_match) > 1 and section_match[1] else ""
                structure["level"] = 3
                structure["level_name"] = "seccion"
                if not structure["section_title"] and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not self._is_structure_line(next_line):
                        structure["section_title"] = next_line
                break
            
            # Buscar capítulo
            chapter_match = self._match_patterns(line_stripped, self.chapter_patterns)
            if chapter_match:
                chapter_num = chapter_match[0]
                # Convertir números romanos a decimales si es necesario
                if self._is_roman_numeral(chapter_num):
                    chapter_num = str(self._roman_to_int(chapter_num))
                structure["chapter"] = int(chapter_num) if chapter_num.isdigit() else None
                structure["chapter_title"] = chapter_match[1].strip() if len(chapter_match) > 1 and chapter_match[1] else ""
                structure["level"] = 2
                structure["level_name"] = "capitulo"
                if not structure["chapter_title"] and i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not self._is_structure_line(next_line):
                        structure["chapter_title"] = next_line
                break
        
        # Construir full_reference
        structure["full_reference"] = self._build_full_reference(structure, code, edition)
        
        return structure
    
    def _match_patterns(self, text: str, patterns: List[str]) -> Optional[Tuple]:
        """Intenta hacer match con una lista de patrones."""
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.groups()
        return None
    
    def _is_structure_line(self, line: str) -> bool:
        """Verifica si una línea parece ser una línea de estructura."""
        structure_indicators = [
            r'^(?:cap[íi]tulo|chapter|secci[óo]n|section|art[íi]culo|art\.)',
            r'^#{1,4}\s+',
            r'^\d+\.\d+',
        ]
        for indicator in structure_indicators:
            if re.match(indicator, line, re.IGNORECASE):
                return True
        return False
    
    def _is_roman_numeral(self, text: str) -> bool:
        """Verifica si el texto es un número romano."""
        return bool(re.match(r'^[IVXLCDM]+$', text.upper()))
    
    def _roman_to_int(self, roman: str) -> int:
        """Convierte número romano a entero."""
        roman_numerals = {
            'I': 1, 'V': 5, 'X': 10, 'L': 50,
            'C': 100, 'D': 500, 'M': 1000
        }
        result = 0
        prev_value = 0
        for char in reversed(roman.upper()):
            value = roman_numerals.get(char, 0)
            if value < prev_value:
                result -= value
            else:
                result += value
            prev_value = value
        return result
    
    def _build_full_reference(self, structure: Dict, code: Optional[str] = None, edition: Optional[str] = None) -> Optional[str]:
        """
        Construye referencia completa del chunk.
        
        Formato: "Ley 29783:2011, Art. 49"
        """
        parts = []
        
        # Agregar código y edición si están disponibles
        if code:
            if edition:
                parts.append(f"{code}:{edition}")
            else:
                parts.append(code)
        
        # Agregar referencias jerárquicas
        ref_parts = []
        if structure.get("chapter"):
            ref_parts.append(f"Cap. {structure['chapter']}")
        if structure.get("section"):
            ref_parts.append(f"Sec. {structure['section']}")
        if structure.get("subsection"):
            ref_parts.append(f"Subsec. {structure['subsection']}")
        if structure.get("article"):
            ref_parts.append(f"Art. {structure['article']}")
        
        if ref_parts:
            parts.append(", ".join(ref_parts))
        
        if parts:
            return ", ".join(parts)
        return None
    
    def detect_chunk_type(self, chunk_content: str) -> Dict[str, bool]:
        """
        Detecta el tipo de contenido del chunk.
        
        Returns:
            Dict con flags: is_header_chunk, is_table_chunk, is_list_chunk, has_citations
        """
        content_lower = chunk_content.lower()
        lines = chunk_content.split('\n')
        
        # Detectar header chunk (solo headers sin contenido sustancial)
        header_indicators = ['#', '##', '###', '####']
        header_lines = sum(1 for line in lines if any(line.strip().startswith(h) for h in header_indicators))
        is_header_chunk = header_lines > 0 and len(chunk_content.strip()) < 200
        
        # Detectar tabla (líneas con múltiples pipes o tabs)
        table_pattern = r'\|.*\|.*\|'  # Al menos 3 columnas
        is_table_chunk = bool(re.search(table_pattern, chunk_content))
        
        # Detectar lista (bullets o numeradas)
        list_patterns = [
            r'^\s*[-*•]\s+',  # Bullets
            r'^\s*\d+[\.\)]\s+',  # Numeradas
        ]
        list_lines = sum(1 for line in lines if any(re.match(p, line) for p in list_patterns))
        is_list_chunk = list_lines >= 2  # Al menos 2 líneas de lista
        
        # Detectar citas/referencias a normas
        citation_patterns = [
            r'(?i)(?:ley|decreto|resoluci[óo]n|norma|standard|nfpa|iso|ansi)\s+[\d\-]+',
            r'(?i)art[íi]culo\s+\d+',
            r'(?i)secci[óo]n\s+\d+',
            r'[A-Z]{2,}\s+\d+',  # Códigos como "DS 005-2012-TR"
        ]
        has_citations = any(re.search(p, chunk_content) for p in citation_patterns)
        
        return {
            "is_header_chunk": is_header_chunk,
            "is_table_chunk": is_table_chunk,
            "is_list_chunk": is_list_chunk,
            "has_citations": has_citations
        }


def generate_code_variations(code: str) -> List[str]:
    """
    Genera variaciones del código normativo para matching robusto.
    
    Ejemplo: "Ley_29783_2011" -> ["Ley 29783", "Ley N° 29783", "L. 29783"]
    
    Args:
        code: Código normativo original
    
    Returns:
        Lista de variaciones del código
    """
    if not code:
        return []
    
    variations = [code]  # Incluir el original
    
    # Normalizar: quitar guiones bajos y convertir a espacios
    normalized = code.replace('_', ' ').strip()
    variations.append(normalized)
    
    # Extraer números del código
    numbers = re.findall(r'\d+', code)
    if numbers:
        main_number = numbers[0]
        
        # Patrones comunes
        if 'ley' in code.lower():
            variations.extend([
                f"Ley {main_number}",
                f"Ley N° {main_number}",
                f"Ley Nº {main_number}",
                f"L. {main_number}",
                f"Ley N° {main_number}",
            ])
        elif 'decreto' in code.lower() or 'ds' in code.lower():
            variations.extend([
                f"DS {main_number}",
                f"Decreto Supremo {main_number}",
                f"D.S. {main_number}",
            ])
        elif 'resolucion' in code.lower() or 'rm' in code.lower():
            variations.extend([
                f"RM {main_number}",
                f"Resolución Ministerial {main_number}",
                f"R.M. {main_number}",
            ])
        elif 'nfpa' in code.lower():
            variations.extend([
                f"NFPA {main_number}",
                f"NFPA-{main_number}",
            ])
    
    # Eliminar duplicados manteniendo orden
    seen = set()
    unique_variations = []
    for v in variations:
        if v not in seen:
            seen.add(v)
            unique_variations.append(v)
    
    return unique_variations


def parse_list_field(value: Optional[str]) -> List[str]:
    """
    Parsea un campo que puede ser string separado por comas o lista.
    
    Args:
        value: Valor que puede ser string, lista o None
    
    Returns:
        Lista de strings
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if isinstance(value, str):
        if not value.strip():
            return []
        return [v.strip() for v in value.split(',') if v.strip()]
    return []


def generate_citation_format(code: str, edition: str, article: Optional[int] = None,
                            chapter: Optional[int] = None, section: Optional[str] = None) -> str:
    """
    Genera formato de citación completo.
    
    Ejemplo: "Ley 29783:2011, Artículo 49"
    """
    parts = []
    
    if code:
        parts.append(code)
    if edition:
        parts.append(f":{edition}")
    
    citation_parts = []
    if article:
        citation_parts.append(f"Art. {article}")
    if chapter:
        citation_parts.append(f"Cap. {chapter}")
    if section:
        citation_parts.append(f"Sec. {section}")
    
    if citation_parts:
        parts.append(", ".join(citation_parts))
    
    return ", ".join(parts) if parts else ""


def generate_short_citation(code: str, edition: str, article: Optional[int] = None) -> str:
    """
    Genera formato de citación abreviado.
    
    Ejemplo: "Ley 29783 (2011) Art. 49"
    """
    parts = []
    
    if code:
        parts.append(code)
    if edition:
        parts.append(f"({edition})")
    if article:
        parts.append(f"Art. {article}")
    
    return " ".join(parts)


def generate_display_title(article_title: Optional[str] = None, section_title: Optional[str] = None,
                          chapter_title: Optional[str] = None, book_title: Optional[str] = None) -> Optional[str]:
    """
    Genera título corto para mostrar en UI.
    
    Prioridad: article_title > section_title > chapter_title > book_title
    """
    if article_title:
        return article_title
    if section_title:
        return section_title
    if chapter_title:
        return chapter_title
    if book_title:
        return book_title
    return None


def determine_priority_level(level: int, is_primary_source: Optional[bool] = None,
                            legal_weight: Optional[int] = None) -> str:
    """
    Determina el nivel de prioridad para ranking.
    
    Args:
        level: Nivel jerárquico (1=artículo, 5=general)
        is_primary_source: Si es fuente primaria
        legal_weight: Peso legal (mayor = más importante)
    
    Returns:
        "high", "medium", o "low"
    """
    # Artículos siempre son high priority
    if level == 1:
        return "high"
    
    # Si es fuente primaria y tiene alto peso legal
    if is_primary_source and legal_weight and legal_weight >= 800:
        return "high"
    
    # Capítulos y secciones son medium
    if level in [2, 3]:
        return "medium"
    
    # Resto es low
    return "low"

