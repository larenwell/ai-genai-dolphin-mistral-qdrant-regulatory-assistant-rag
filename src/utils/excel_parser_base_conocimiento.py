#!/usr/bin/env python3
"""
Excel Parser - Procesamiento de base-conocimiento.xlsx

Lee el archivo Excel base-conocimiento.xlsx y genera archivos JSON
individuales para cada documento en output/metadata/source/

Estructura del Excel:
- Fila 1: Categorías (temp, obligatorio, opcional) - Header de pandas
- Fila 2: Nombres reales de columnas (document_id, source_file, etc.)
- Fila 3+: Datos de documentos

Pestañas procesadas:
- NFPA, FMDS, RNE, Gestion, ISO, SST, Medio Ambiente, ASIS

Pestañas ignoradas:
- catalogo, resultados de ingesta
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core import get_logger
from src.core.exceptions import ValidationError

logger = get_logger(__name__)

# Pestañas a procesar (contienen documentos)
DOCUMENT_SHEETS = ['NFPA', 'FMDS', 'RNE', 'Gestion', 'ISO', 'SST', 'Medio Ambiente', 'ASIS']

# Pestañas a ignorar
IGNORED_SHEETS = ['catalogo', 'resultados de ingesta']


class ExcelParser:
    """
    Parser para el archivo base-conocimiento.xlsx
    
    Lee cada pestaña, normaliza columnas y genera JSONs individuales.
    """
    
    def __init__(self, excel_path: Path):
        """
        Inicializa el parser.
        
        Args:
            excel_path: Ruta al archivo Excel
        """
        self.excel_path = Path(excel_path)
        self._excel_file: Optional[pd.ExcelFile] = None
        self._column_mapping: Dict[str, str] = {}
        self._all_documents: List[Dict] = []
        self._documents_by_sheet: Dict[str, List[Dict]] = {}
        self._documents_by_source_file: Dict[str, Dict] = {}
        self._documents_by_id: Dict[str, Dict] = {}
        
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel no encontrado: {excel_path}")
        
        logger.info(f"ExcelParser inicializado: {excel_path}")
    
    def _get_column_mapping(self, df: pd.DataFrame) -> Dict[str, Dict[str, str]]:
        """
        Extrae el mapeo de columnas.
        
        Estructura del Excel:
        - Fila 0 (índice 0): Categorías (temp, obligatorio, opcional)
        - Fila 1 (índice 1): Nombres reales de columnas (Nro., nombre archivo, document_id, etc.)
        - Fila 2+ (índice 2+): Datos
        
        Agrupa por categoría: temp, obligatorio, opcional.
        
        Args:
            df: DataFrame con datos (sin header, lee desde fila 0)
        
        Returns:
            Dict con estructura:
            {
                "temp": {"0": "Nro.", "1": "nombre archivo", ...},
                "obligatorio": {"9": "document_id", "10": "source_file", ...},
                "opcional": {"22": "is_base_regulation", ...}
            }
        """
        if len(df) < 2:
            return {"temp": {}, "obligatorio": {}, "opcional": {}}
        
        # Fila 0: Categorías (temp, obligatorio, opcional)
        category_row = df.iloc[0]
        # Fila 1: Nombres reales de columnas
        name_row = df.iloc[1]
        
        mapping = {
            "temp": {},
            "obligatorio": {},
            "opcional": {}
        }
        
        # Iterar sobre las columnas del DataFrame
        for col_idx in df.columns:
            category = str(category_row[col_idx]).strip().lower()
            real_name = str(name_row[col_idx]).strip()
            
            # Ignorar si el nombre real está vacío o es 'nan'
            if not real_name or real_name.lower() == 'nan':
                continue
            
            # Determinar categoría y agregar al mapeo
            if category == 'temp':
                mapping["temp"][str(col_idx)] = real_name
            elif category == 'obligatorio':
                mapping["obligatorio"][str(col_idx)] = real_name
            elif category == 'opcional':
                mapping["opcional"][str(col_idx)] = real_name
        
        return mapping
    
    def _normalize_value(self, value: Any) -> Any:
        """
        Normaliza un valor para JSON.
        
        Args:
            value: Valor a normalizar
        
        Returns:
            Valor normalizado
        """
        if pd.isna(value):
            return None
        
        if isinstance(value, (int, float)):
            # Convertir float a int si es entero
            if isinstance(value, float) and value.is_integer():
                return int(value)
            return value
        
        # Convertir a string y limpiar
        str_value = str(value).strip()
        
        # Manejar fechas
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        
        return str_value if str_value else None
    
    def _row_to_document(self, row: pd.Series, column_mapping: Dict[str, Dict[str, str]], sheet_name: str) -> Optional[Dict]:
        """
        Convierte una fila del DataFrame a un diccionario de documento.
        
        Estructura del documento:
        {
            "document_id": "...",
            "temp": { ... campos temporales ... },
            "sincro": { ... campos obligatorio + opcional ... },
            "_sheet": "...",
            "_processed_at": "..."
        }
        
        Args:
            row: Fila del DataFrame
            column_mapping: Mapeo de columnas agrupado por categoría
            sheet_name: Nombre de la pestaña
        
        Returns:
            Dict con datos del documento o None si no es válido
        """
        document = {
            "document_id": None,
            "temp": {},
            "sincro": {}
        }
        
        # Procesar campos temp
        for col_idx_str, real_name in column_mapping.get("temp", {}).items():
            col_idx = int(col_idx_str)
            if col_idx in row.index:
                value = self._normalize_value(row[col_idx])
                document["temp"][real_name] = value
        
        # Procesar campos obligatorio (van a sincro)
        for col_idx_str, real_name in column_mapping.get("obligatorio", {}).items():
            col_idx = int(col_idx_str)
            if col_idx in row.index:
                value = self._normalize_value(row[col_idx])
                document["sincro"][real_name] = value
                
                # Guardar document_id a nivel raíz también
                if real_name == "document_id":
                    document["document_id"] = value
        
        # Procesar campos opcional (van a sincro)
        for col_idx_str, real_name in column_mapping.get("opcional", {}).items():
            col_idx = int(col_idx_str)
            if col_idx in row.index:
                value = self._normalize_value(row[col_idx])
                document["sincro"][real_name] = value
        
        # Agregar metadata adicional
        document['_sheet'] = sheet_name
        document['_processed_at'] = datetime.now().isoformat()
        
        # Validar que tiene document_id
        if not document.get('document_id'):
            return None
        
        return document
    
    def parse_sheet(self, sheet_name: str, global_seen_document_ids: Dict[str, Dict] = None) -> List[Dict]:
        """
        Procesa una pestaña del Excel.
        
        Args:
            sheet_name: Nombre de la pestaña
            global_seen_document_ids: Dict global para detectar duplicados entre pestañas.
                                     Si es None, solo detecta duplicados dentro de la pestaña.
                                     Estructura: {document_id: {"sheet": "NOMBRE", "row": fila}}
        
        Returns:
            Lista de documentos procesados
        """
        try:
            logger.info(f"Procesando pestaña: {sheet_name}")
            
            # Leer pestaña (sin header, lee desde fila 0)
            df = pd.read_excel(self.excel_path, sheet_name=sheet_name, header=None)
            
            if len(df) < 3:
                logger.warning(f"Pestaña '{sheet_name}' tiene menos de 3 filas, omitiendo")
                return []
            
            # Obtener mapeo de columnas
            # Fila 0: categorías, Fila 1: nombres reales
            column_mapping = self._get_column_mapping(df)
            
            if not column_mapping:
                logger.warning(f"No se pudo obtener mapeo de columnas para '{sheet_name}'")
                return []
            
            # Inicializar registro global si no se proporciona
            if global_seen_document_ids is None:
                global_seen_document_ids = {}
            
            # Procesar filas desde la fila 2 (índice 2) en adelante (datos)
            documents = []
            seen_document_ids = {}  # Para detectar duplicados dentro de la pestaña: {document_id: fila_primera_ocurrencia}
            for idx in range(2, len(df)):
                row = df.iloc[idx]
                doc = self._row_to_document(row, column_mapping, sheet_name)
                
                if doc:
                    document_id = doc.get('document_id')
                    if document_id:
                        # Verificar duplicado dentro de la pestaña
                        if document_id in seen_document_ids:
                            primera_fila = seen_document_ids[document_id]
                            logger.warning(f"⚠️ Duplicado detectado en fila {idx+1}: {document_id} (pestaña: {sheet_name})")
                            logger.warning(f"   Se usará la primera ocurrencia definida en la fila {primera_fila}, la fila {idx+1} será ignorada.")
                            continue
                        
                        # Verificar duplicado entre pestañas
                        if document_id in global_seen_document_ids:
                            primera_ocurrencia = global_seen_document_ids[document_id]
                            primera_sheet = primera_ocurrencia["sheet"]
                            primera_fila = primera_ocurrencia["row"]
                            logger.warning(f"⚠️ Duplicado entre pestañas detectado en fila {idx+1}: {document_id}")
                            logger.warning(f"   Ya fue procesado en pestaña '{primera_sheet}' (fila {primera_fila}).")
                            logger.warning(f"   Se usará la primera ocurrencia de '{primera_sheet}', esta ocurrencia en '{sheet_name}' (fila {idx+1}) será ignorada.")
                            continue
                        
                        # Primera ocurrencia: registrar en ambos diccionarios
                        seen_document_ids[document_id] = idx + 1  # Guardar número de fila (1-indexed)
                        global_seen_document_ids[document_id] = {
                            "sheet": sheet_name,
                            "row": idx + 1
                        }
                    documents.append(doc)
            
            logger.info(f"✅ Pestaña '{sheet_name}': {len(documents)} documentos procesados")
            return documents
            
        except Exception as e:
            logger.error(f"Error procesando pestaña '{sheet_name}': {e}")
            return []
    
    def parse_all(self) -> Dict[str, List[Dict]]:
        """
        Procesa todas las pestañas del Excel.
        
        Valida duplicados entre pestañas:
        - Si un document_id aparece en múltiples pestañas, se usa la primera ocurrencia
          de la primera pestaña (según orden de DOCUMENT_SHEETS)
        - Se muestran advertencias para duplicados entre pestañas
        
        Returns:
            Dict con nombre de pestaña -> lista de documentos
        """
        logger.info("="*80)
        logger.info("📊 PROCESANDO ARCHIVO EXCEL")
        logger.info("="*80)
        logger.info(f"Archivo: {self.excel_path}")
        
        # Leer pestañas disponibles
        xl = pd.ExcelFile(self.excel_path)
        available_sheets = xl.sheet_names
        
        logger.info(f"Pestañas encontradas: {available_sheets}")
        logger.info(f"Pestañas a procesar: {DOCUMENT_SHEETS}")
        logger.info("="*80)
        
        self._documents_by_sheet = {}
        self._all_documents = []
        self._documents_by_source_file = {}
        self._documents_by_id = {}
        
        # Registro global de document_ids procesados entre todas las pestañas
        # Estructura: {document_id: {"sheet": "NOMBRE", "row": fila}}
        global_seen_document_ids = {}
        
        for sheet_name in DOCUMENT_SHEETS:
            if sheet_name in available_sheets:
                # Pasar el registro global para validar duplicados entre pestañas
                documents = self.parse_sheet(sheet_name, global_seen_document_ids)
                self._documents_by_sheet[sheet_name] = documents
                
                # Agregar a índices
                for doc in documents:
                    self._all_documents.append(doc)
                    
                    # Indexar por source_file (ahora está en sincro)
                    source_file = doc.get('sincro', {}).get('source_file')
                    if source_file:
                        self._documents_by_source_file[source_file] = doc
                    
                    # Indexar por document_id (está en raíz y en sincro)
                    doc_id = doc.get('document_id')
                    if doc_id:
                        self._documents_by_id[doc_id] = doc
            else:
                logger.warning(f"Pestaña '{sheet_name}' no encontrada en el Excel")
        
        logger.info("="*80)
        logger.info(f"📊 RESUMEN: {len(self._all_documents)} documentos procesados en total")
        logger.info("="*80)
        
        return self._documents_by_sheet
    
    def get_document_by_source_file(self, source_file: str) -> Optional[Dict]:
        """
        Busca un documento por source_file.
        
        Args:
            source_file: Nombre del archivo fuente
        
        Returns:
            Dict con datos del documento o None
        """
        return self._documents_by_source_file.get(source_file)
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict]:
        """
        Busca un documento por document_id.
        
        Args:
            document_id: ID del documento
        
        Returns:
            Dict con datos del documento o None
        """
        return self._documents_by_id.get(document_id)
    
    def get_all_documents(self) -> List[Dict]:
        """Retorna todos los documentos procesados."""
        return self._all_documents
    
    def get_documents_by_sheet(self, sheet_name: str) -> List[Dict]:
        """Retorna documentos de una pestaña específica."""
        return self._documents_by_sheet.get(sheet_name, [])
    
    def export_to_json(self, output_dir: Path, clean_dir: bool = True) -> Dict[str, List[str]]:
        """
        Exporta cada documento a un archivo JSON individual.
        
        Estructura de salida:
        output_dir/
        ├── NFPA/
        │   ├── NFPA_11_2024_ED_2024_source.json
        │   └── ...
        ├── FMDS/
        │   ├── FMDS_0104_2024_ED_2024_source.json
        │   └── ...
        └── ...
        
        Args:
            output_dir: Directorio de salida (output/metadata/source/)
            clean_dir: Si True, limpia el directorio antes de exportar
        
        Returns:
            Dict con listas de archivos creados y errores
        """
        output_dir = Path(output_dir)
        
        results = {
            "created": [],
            "errors": [],
            "by_sheet": {}
        }
        
        # Limpiar directorio si se solicita
        if clean_dir and output_dir.exists():
            logger.info(f"🧹 Limpiando directorio: {output_dir}")
            import shutil
            for item in output_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        
        # Crear directorio si no existe
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Exportando JSONs a: {output_dir}")
        
        for sheet_name, documents in self._documents_by_sheet.items():
            results["by_sheet"][sheet_name] = []
            
            # Crear subcarpeta para cada pestaña
            sheet_dir = output_dir / sheet_name
            sheet_dir.mkdir(parents=True, exist_ok=True)
            
            for doc in documents:
                try:
                    document_id = doc.get('document_id')
                    if not document_id:
                        results["errors"].append(f"Documento sin document_id en {sheet_name}")
                        continue
                    
                    # Nombre del archivo: {document_id}_source.json
                    filename = f"{document_id}_source.json"
                    filepath = sheet_dir / filename
                    
                    # Escribir JSON
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(doc, f, indent=2, ensure_ascii=False)
                    
                    # Guardar ruta relativa para el reporte
                    relative_path = f"{sheet_name}/{filename}"
                    results["created"].append(relative_path)
                    results["by_sheet"][sheet_name].append(filename)
                    
                except Exception as e:
                    error_msg = f"Error exportando {doc.get('document_id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
        
        logger.info(f"✅ Exportados {len(results['created'])} archivos JSON en {len(self._documents_by_sheet)} carpetas")
        
        if results["errors"]:
            logger.warning(f"⚠️ {len(results['errors'])} errores durante exportación")
        
        return results


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

_parser_instance: Optional[ExcelParser] = None


def load_excel_metadata(excel_path: Path = None, force_reload: bool = False) -> ExcelParser:
    """
    Carga el Excel y retorna instancia del parser.
    
    Args:
        excel_path: Ruta al Excel (default: data/base-conocimiento.xlsx)
        force_reload: Si True, recarga el Excel aunque ya esté cargado
    
    Returns:
        ExcelParser con datos cargados
    """
    global _parser_instance
    
    if excel_path is None:
        project_root = Path(__file__).parent.parent.parent
        excel_path = project_root / "data" / "base-conocimiento.xlsx"
    
    if _parser_instance is None or force_reload:
        _parser_instance = ExcelParser(excel_path)
        _parser_instance.parse_all()
    
    return _parser_instance


def get_document_by_source_file(source_file: str) -> Optional[Dict]:
    """
    Busca un documento por source_file.
    
    Args:
        source_file: Nombre del archivo fuente
    
    Returns:
        Dict con datos del documento o None
    """
    parser = load_excel_metadata()
    return parser.get_document_by_source_file(source_file)


def get_document_by_id(document_id: str) -> Optional[Dict]:
    """
    Busca un documento por document_id.
    
    Args:
        document_id: ID del documento
    
    Returns:
        Dict con datos del documento o None
    """
    parser = load_excel_metadata()
    return parser.get_document_by_id(document_id)


def export_metadata_to_json(output_dir: Path = None, clean_dir: bool = True) -> Dict[str, List[str]]:
    """
    Exporta toda la metadata a archivos JSON individuales.
    
    Args:
        output_dir: Directorio de salida (default: output/metadata/source/)
        clean_dir: Si True, limpia el directorio antes de exportar
    
    Returns:
        Dict con resultados de exportación
    """
    if output_dir is None:
        project_root = Path(__file__).parent.parent.parent
        output_dir = project_root / "output" / "metadata" / "source"
    
    parser = load_excel_metadata()
    return parser.export_to_json(output_dir, clean_dir)


# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

def main():
    """Función principal para ejecutar desde línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Procesa base-conocimiento.xlsx y genera JSONs")
    parser.add_argument(
        "--excel",
        type=str,
        default="data/base-conocimiento.xlsx",
        help="Ruta al archivo Excel"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/metadata/source",
        help="Directorio de salida para JSONs"
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="No limpiar directorio de salida antes de exportar"
    )
    
    args = parser.parse_args()
    
    # Setup paths
    project_root = Path(__file__).parent.parent.parent
    excel_path = project_root / args.excel
    output_dir = project_root / args.output
    
    print("="*80)
    print("📊 EXCEL PARSER - Procesamiento de base-conocimiento.xlsx")
    print("="*80)
    print(f"Excel: {excel_path}")
    print(f"Salida: {output_dir}")
    print("="*80 + "\n")
    
    # Procesar Excel
    excel_parser = ExcelParser(excel_path)
    documents_by_sheet = excel_parser.parse_all()
    
    # Mostrar resumen por pestaña
    print("\n" + "="*80)
    print("📋 DOCUMENTOS POR PESTAÑA:")
    print("="*80)
    for sheet_name, docs in documents_by_sheet.items():
        print(f"  {sheet_name}: {len(docs)} documentos")
    
    # Exportar a JSON
    print("\n" + "="*80)
    print("📁 EXPORTANDO A JSON...")
    print("="*80)
    
    results = excel_parser.export_to_json(output_dir, clean_dir=not args.no_clean)
    
    print(f"\n✅ Archivos creados: {len(results['created'])}")
    
    if results['errors']:
        print(f"❌ Errores: {len(results['errors'])}")
        for error in results['errors']:
            print(f"   - {error}")
    
    print(f"\n📁 Archivos guardados en: {output_dir}")
    
    # Mostrar algunos ejemplos
    print("\n" + "="*80)
    print("📝 EJEMPLOS DE DOCUMENTOS:")
    print("="*80)
    
    all_docs = excel_parser.get_all_documents()
    for doc in all_docs[:3]:
        sincro = doc.get('sincro', {})
        temp = doc.get('temp', {})
        print(f"\n📄 {doc.get('document_id')}")
        print(f"   temp.condición: {temp.get('condición')}")
        print(f"   temp.codigo: {temp.get('codigo')}")
        print(f"   sincro.source_file: {sincro.get('source_file')}")
        print(f"   sincro.book_title: {sincro.get('book_title')}")
        print(f"   sincro.language: {sincro.get('language')}")
        print(f"   _sheet: {doc.get('_sheet')}")
    
    print("\n" + "="*80)
    print("✅ PROCESO COMPLETADO")
    print("="*80)


if __name__ == "__main__":
    main()

