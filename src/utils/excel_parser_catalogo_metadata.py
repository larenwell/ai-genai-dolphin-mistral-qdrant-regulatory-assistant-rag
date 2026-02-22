#!/usr/bin/env python3
"""
Excel Parser para catalogo-metadata.xlsx

Lee y procesa el archivo catalogo-metadata.xlsx que contiene:
- Hoja "1- Estructura Metadata": Define la estructura de metadata con condiciones (obligatorio/opcional)
- Hoja "3- Jerarquía Normativa": Define la jerarquía normativa y sus valores asociados

Este parser permite:
1. Leer la estructura de metadata requerida
2. Obtener información de jerarquía normativa
3. Mapear campos según su condición (obligatorio/opcional)
4. Determinar valores de legal_weight e is_primary_source según jerarquía
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core import get_logger

logger = get_logger(__name__)


class MetadataCatalogParser:
    """
    Parser para el archivo catalogo-metadata.xlsx
    
    Lee las hojas:
    - "1- Estructura Metadata": Estructura de campos con condiciones
    - "3- Jerarquía Normativa": Jerarquía normativa y valores asociados
    """
    
    def __init__(self, excel_path: Path):
        """
        Inicializa el parser.
        
        Args:
            excel_path: Ruta al archivo catalogo-metadata.xlsx
        """
        self.excel_path = Path(excel_path)
        self._metadata_structure: Optional[pd.DataFrame] = None
        self._hierarchy_data: Optional[pd.DataFrame] = None
        self._metadata_fields: Dict[str, Dict] = {}
        self._hierarchy_mapping: Dict[int, Dict] = {}
        
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel no encontrado: {excel_path}")
        
        logger.info(f"MetadataCatalogParser inicializado: {excel_path}")
        self._load_data()
    
    def _load_data(self):
        """Carga las hojas del Excel en memoria"""
        try:
            excel_file = pd.ExcelFile(self.excel_path)
            
            # Cargar hoja "1- Estructura Metadata"
            if "1- Estructura Metadata" in excel_file.sheet_names:
                self._metadata_structure = pd.read_excel(
                    self.excel_path,
                    sheet_name="1- Estructura Metadata"
                )
                logger.info(f"✅ Hoja '1- Estructura Metadata' cargada: {len(self._metadata_structure)} filas")
            else:
                logger.warning("⚠️ Hoja '1- Estructura Metadata' no encontrada")
            
            # Cargar hoja "3- Jerarquía Normativa"
            if "3- Jerarquía Normativa" in excel_file.sheet_names:
                self._hierarchy_data = pd.read_excel(
                    self.excel_path,
                    sheet_name="3- Jerarquía Normativa"
                )
                logger.info(f"✅ Hoja '3- Jerarquía Normativa' cargada: {len(self._hierarchy_data)} filas")
            else:
                logger.warning("⚠️ Hoja '3- Jerarquía Normativa' no encontrada")
            
            # Procesar datos
            self._process_metadata_structure()
            self._process_hierarchy_data()
            
        except Exception as e:
            logger.error(f"Error cargando Excel: {e}")
            raise
    
    def _process_metadata_structure(self):
        """Procesa la hoja de estructura de metadata"""
        if self._metadata_structure is None or len(self._metadata_structure) == 0:
            return
        
        # Normalizar nombres de columnas (eliminar espacios, convertir a minúsculas)
        df = self._metadata_structure.copy()
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        # Buscar columnas relevantes
        # Asumimos que hay columnas como: campo, condición, obtenido, jerarquia_normativa, etc.
        for idx, row in df.iterrows():
            # Intentar identificar el campo/key
            field_name = None
            condition = None
            obtained = None
            hierarchy_ref = None
            
            # Buscar en diferentes posibles nombres de columnas
            for col in df.columns:
                col_lower = str(col).lower()
                if 'campo' in col_lower or 'field' in col_lower or 'key' in col_lower:
                    field_name = str(row[col]).strip() if pd.notna(row[col]) else None
                elif 'condición' in col_lower or 'condicion' in col_lower:
                    condition = str(row[col]).strip().lower() if pd.notna(row[col]) else None
                elif 'obtenido' in col_lower:
                    obtained = str(row[col]).strip().lower() if pd.notna(row[col]) else None
                elif 'jerarquía' in col_lower or 'jerarquia' in col_lower:
                    hierarchy_ref = str(row[col]).strip() if pd.notna(row[col]) else None
            
            if field_name and field_name != 'nan' and field_name:
                self._metadata_fields[field_name] = {
                    "field_name": field_name,
                    "condition": condition or "opcional",
                    "obtained": obtained or "pendiente",
                    "hierarchy_reference": hierarchy_ref,
                    "row_index": idx
                }
        
        logger.info(f"📋 Procesados {len(self._metadata_fields)} campos de metadata")
    
    def _process_hierarchy_data(self):
        """Procesa la hoja de jerarquía normativa"""
        if self._hierarchy_data is None or len(self._hierarchy_data) == 0:
            return
        
        # Normalizar nombres de columnas
        df = self._hierarchy_data.copy()
        df.columns = [str(col).strip().lower() for col in df.columns]
        
        # Buscar columnas directamente por nombre normalizado
        nivel_col = None
        legal_weight_col = None
        is_primary_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if col_lower == 'nivel':
                nivel_col = col
            elif col_lower == 'legal_weight':
                legal_weight_col = col
            elif col_lower == 'is_primary_source':
                is_primary_col = col
        
        # Procesar cada fila
        for idx, row in df.iterrows():
            level = None
            legal_weight = None
            is_primary_source = None
            
            # Leer nivel
            if nivel_col and nivel_col in df.columns:
                try:
                    level_val = row[nivel_col]
                    if pd.notna(level_val):
                        level = int(level_val)
                except (ValueError, TypeError):
                    level = None
            
            # Leer legal_weight
            if legal_weight_col and legal_weight_col in df.columns:
                try:
                    weight_val = row[legal_weight_col]
                    if pd.notna(weight_val):
                        legal_weight = int(weight_val)
                except (ValueError, TypeError):
                    legal_weight = None
            
            # Leer is_primary_source
            if is_primary_col and is_primary_col in df.columns:
                val = row[is_primary_col]
                if pd.notna(val):
                    # Puede ser boolean, string, o número
                    if isinstance(val, bool):
                        is_primary_source = val
                    elif isinstance(val, (int, float)):
                        is_primary_source = bool(val)
                    else:
                        val_str = str(val).strip().lower()
                        if val_str in ['true', '1', 'yes', 'sí', 'si', 'verdadero']:
                            is_primary_source = True
                        elif val_str in ['false', '0', 'no', 'falso']:
                            is_primary_source = False
                        else:
                            is_primary_source = None
            
            if level is not None:
                self._hierarchy_mapping[level] = {
                    "level": level,
                    "legal_weight": legal_weight,
                    "is_primary_source": is_primary_source,
                    "row_index": idx
                }
        
        logger.info(f"📊 Procesados {len(self._hierarchy_mapping)} niveles de jerarquía")
    
    def get_metadata_structure(self) -> Dict[str, Dict]:
        """
        Obtiene la estructura completa de metadata.
        
        Returns:
            Dict con campos y sus propiedades
        """
        return self._metadata_fields.copy()
    
    def get_obligatory_fields(self) -> List[str]:
        """
        Obtiene lista de campos obligatorios.
        
        Returns:
            Lista de nombres de campos obligatorios
        """
        return [
            field_name
            for field_name, field_info in self._metadata_fields.items()
            if field_info.get("condition", "").lower() == "obligatorio"
        ]
    
    def get_optional_fields(self) -> List[str]:
        """
        Obtiene lista de campos opcionales.
        
        Returns:
            Lista de nombres de campos opcionales
        """
        return [
            field_name
            for field_name, field_info in self._metadata_fields.items()
            if field_info.get("condition", "").lower() == "opcional"
        ]
    
    def get_fields_by_obtained_status(self, status: str) -> List[str]:
        """
        Obtiene campos según su estado de obtención.
        
        Args:
            status: "informativo", "key", "ok", "pendiente"
        
        Returns:
            Lista de nombres de campos
        """
        return [
            field_name
            for field_name, field_info in self._metadata_fields.items()
            if field_info.get("obtained", "").lower() == status.lower()
        ]
    
    def get_hierarchy_info(self, hierarchy_level: int) -> Optional[Dict]:
        """
        Obtiene información de jerarquía normativa para un nivel dado.
        
        Args:
            hierarchy_level: Nivel de jerarquía (ej: 1, 2, 3)
        
        Returns:
            Dict con legal_weight e is_primary_source, o None si no existe
        """
        return self._hierarchy_mapping.get(hierarchy_level)
    
    def get_legal_weight(self, hierarchy_level: int) -> Optional[int]:
        """
        Obtiene el legal_weight para un nivel de jerarquía.
        
        Args:
            hierarchy_level: Nivel de jerarquía
        
        Returns:
            legal_weight o None
        """
        hierarchy_info = self.get_hierarchy_info(hierarchy_level)
        return hierarchy_info.get("legal_weight") if hierarchy_info else None
    
    def get_is_primary_source(self, hierarchy_level: int) -> Optional[bool]:
        """
        Obtiene is_primary_source para un nivel de jerarquía.
        
        Args:
            hierarchy_level: Nivel de jerarquía
        
        Returns:
            is_primary_source o None
        """
        hierarchy_info = self.get_hierarchy_info(hierarchy_level)
        return hierarchy_info.get("is_primary_source") if hierarchy_info else None
    
    def get_all_hierarchy_levels(self) -> List[int]:
        """
        Obtiene todos los niveles de jerarquía disponibles.
        
        Returns:
            Lista de niveles
        """
        return sorted(self._hierarchy_mapping.keys())
    
    def export_structure_to_json(self, output_path: Path):
        """
        Exporta la estructura de metadata a JSON para referencia.
        
        Args:
            output_path: Ruta donde guardar el JSON
        """
        output_data = {
            "metadata_fields": self._metadata_fields,
            "hierarchy_mapping": self._hierarchy_mapping,
            "obligatory_fields": self.get_obligatory_fields(),
            "optional_fields": self.get_optional_fields(),
            "exported_at": datetime.now().isoformat()
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Estructura exportada a: {output_path}")


def load_metadata_catalog(excel_path: Path = None) -> MetadataCatalogParser:
    """
    Carga el catálogo de metadata desde el Excel.
    
    Args:
        excel_path: Ruta al archivo catalogo-metadata.xlsx. Si es None, usa la ruta por defecto.
    
    Returns:
        Instancia de MetadataCatalogParser
    """
    if excel_path is None:
        project_root = Path(__file__).parent.parent.parent
        excel_path = project_root / "data" / "metadata" / "catalogo-metadata.xlsx"
    
    return MetadataCatalogParser(excel_path)


if __name__ == "__main__":
    """Script de prueba"""
    project_root = Path(__file__).parent.parent.parent
    excel_path = project_root / "data" / "metadata" / "catalogo-metadata.xlsx"
    
    print("🔍 Cargando catálogo de metadata...")
    parser = load_metadata_catalog(excel_path)
    
    print("\n📋 Campos obligatorios:")
    for field in parser.get_obligatory_fields():
        print(f"  - {field}")
    
    print("\n📋 Campos opcionales:")
    for field in parser.get_optional_fields():
        print(f"  - {field}")
    
    print("\n📊 Niveles de jerarquía:")
    for level in parser.get_all_hierarchy_levels():
        info = parser.get_hierarchy_info(level)
        print(f"  Nivel {level}: legal_weight={info.get('legal_weight')}, is_primary_source={info.get('is_primary_source')}")
    
    print("\n💾 Exportando estructura a JSON...")
    output_path = project_root / "output" / "metadata" / "final" / "metadata_catalog_structure.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    parser.export_structure_to_json(output_path)
    print(f"✅ Exportado a: {output_path}")

