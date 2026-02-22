# Documentación de `catalogo-metadata.xlsx`

## 📋 Descripción General

`catalogo-metadata.xlsx` es el **catálogo maestro** que define la estructura completa de metadata para todos los documentos del sistema. Este archivo Excel es procesado por `src/utils/excel_parser_catalogo_metadata.py` y sirve como **template y referencia** para la construcción de metadata final.

**Ubicación:** `data/metadata/catalogo-metadata.xlsx`

---

## 🎯 Propósito

Este archivo Excel centraliza:
- **Estructura de metadata**: Define qué campos son obligatorios u opcionales
- **Jerarquía normativa**: Mapea niveles jerárquicos a valores de `legal_weight` e `is_primary_source`
- **Template de metadata**: Sirve como referencia para la estructura final de metadata
- **Estado de obtención**: Indica qué campos ya están obtenidos y cuáles están pendientes

---

## 📊 Estructura del Excel

### Pestañas Principales

El Excel contiene múltiples pestañas, pero las más importantes son:

| Pestaña | Descripción | Uso |
|---------|-------------|-----|
| **1- Estructura Metadata** | Define la estructura completa de metadata con condiciones | ✅ **PRINCIPAL** |
| **3- Jerarquía Normativa** | Define la jerarquía normativa y valores asociados | ✅ **PRINCIPAL** |
| Otras pestañas | Información adicional y referencias | ⚠️ Opcional |

---

## 📑 Pestaña "1- Estructura Metadata"

### Descripción

Esta pestaña define la **estructura completa** de metadata que debe tener cada documento y chunk. Es la **fuente de verdad** para determinar qué campos son obligatorios u opcionales.

### Columnas Principales

| Columna | Descripción | Valores Posibles |
|---------|-------------|------------------|
| **Campo/Field/Key** | Nombre del campo de metadata | `document_id`, `source_file`, `code`, etc. |
| **Condición** | Si el campo es obligatorio u opcional | `obligatorio` \| `opcional` |
| **Obtenido** | Estado de obtención del campo | `informativo` \| `key` \| `ok` \| `pendiente` |
| **Jerarquía Normativa** | Referencia a nivel de jerarquía (si aplica) | Número (1, 2, 3, etc.) |

### Valores de "Condición"

- **`obligatorio`**: El campo **debe** estar presente en la metadata final. Si no se puede obtener, debe generarse o marcarse como error.
- **`opcional`**: El campo puede estar presente o no. Si no se puede obtener, no es un error.

### Valores de "Obtenido"

- **`informativo`**: Campo solo informativo, no se usa para construcción de metadata
- **`key`**: Campo clave que será usado para construir el archivo final JSON
- **`ok`**: Campo ya completado por el cliente (Sincro) en `base-conocimiento.xlsx`
- **`pendiente`**: Campo que necesita ser construido mediante métodos en Python

### Ejemplo de Estructura

```
Campo                    | Condición   | Obtenido   | Jerarquía Normativa
-------------------------|-------------|------------|-------------------
document_id              | obligatorio | key        | -
source_file              | obligatorio | ok         | -
book_title               | obligatorio | ok         | -
code                     | obligatorio | ok         | -
legal_weight             | obligatorio | pendiente | 2
is_primary_source        | obligatorio | pendiente | 2
translated_en            | obligatorio | pendiente | -
chunking_method          | obligatorio | pendiente | -
chunk_index              | obligatorio | pendiente | -
level                    | obligatorio | pendiente | -
article                  | opcional    | pendiente | -
chapter                  | opcional    | pendiente | -
```

### Campos Importantes

#### Campos Obligatorios Principales

**Documento:**
- `document_id`: ID único del documento
- `source_file`: Nombre del archivo original
- `book_title`: Título del documento
- `code`: Código normativo (ej: "Ley 29783")
- `full_name`: Nombre completo del documento
- `edition`: Edición/año
- `provider`: Proveedor del documento
- `country`: País (ej: "PE")
- `scope`: Alcance (ej: "national")
- `status`: Estado (ej: "vigente")

**Jerarquía Normativa:**
- `jerarquia_normativa`: Nivel de jerarquía (1-9)
- `legal_weight`: Peso legal (obtenido de pestaña "3- Jerarquía Normativa")
- `is_primary_source`: Si es fuente primaria (obtenido de pestaña "3- Jerarquía Normativa")

**Chunking:**
- `chunking_method`: Método de chunking (ej: "recursive_character")
- `chunk_index`: Índice del chunk
- `total_chunks`: Total de chunks del documento
- `chunk_size`: Tamaño del chunk en caracteres
- `chunk_words`: Número de palabras en el chunk
- `target_chunk_size`: Tamaño objetivo configurado
- `chunk_overlap`: Solapamiento entre chunks

**Estructura Jerárquica:**
- `level`: Nivel jerárquico (1=artículo, 5=general)
- `article`: Número de artículo (si existe)
- `chapter`: Número de capítulo (si existe)
- `section`: Número de sección (si existe)
- `full_reference`: Referencia completa construida automáticamente

#### Campos Opcionales Principales

- `chapter_title`: Título del capítulo
- `section_title`: Título de la sección
- `article_title`: Título del artículo
- `code_variations`: Variaciones del código normativo
- `is_header_chunk`: Si el chunk contiene solo headers
- `is_table_chunk`: Si el chunk contiene una tabla
- `is_list_chunk`: Si el chunk contiene listas
- `has_citations`: Si el chunk contiene referencias a otras normas
- `keywords_auto`: Keywords extraídos automáticamente
- `display_title`: Título corto para mostrar en UI

---

## 📑 Pestaña "3- Jerarquía Normativa"

### Descripción

Esta pestaña define la **jerarquía normativa** y mapea cada nivel a valores de `legal_weight` e `is_primary_source`. Es usada para completar estos campos en la metadata final.

### Columnas Principales

| Columna | Descripción | Tipo |
|---------|-------------|------|
| **Nivel** | Nivel de jerarquía normativa | Integer (1-9) |
| **Legal Weight** | Peso legal del nivel | Integer (100-1000) |
| **Is Primary Source** | Si es fuente primaria | Boolean (true/false) |

### Mapeo de Niveles

| Nivel | Descripción | Legal Weight | Is Primary Source |
|-------|-------------|--------------|-------------------|
| **1** | Constitución | 1000 | true |
| **2** | Ley Orgánica | 900 | true |
| **3** | Ley Ordinaria | 800 | true |
| **4** | Decreto Supremo | 700 | true |
| **5** | Resolución Ministerial | 600 | true |
| **6** | Resolución Directoral | 500 | true |
| **7** | Norma Técnica Internacional | 400 | false |
| **8** | Norma Técnica Nacional | 400 | false |
| **9** | Ficha Técnica | 300 | false |

### Uso en el Pipeline

Cuando se procesa un documento:
1. Se lee `jerarquia_normativa` de `base-conocimiento.xlsx` (o se infiere)
2. Se consulta esta pestaña para obtener `legal_weight` e `is_primary_source`
3. Estos valores se agregan a la metadata final

**Ejemplo:**
```
jerarquia_normativa: 2 (Ley Orgánica)
  → legal_weight: 900
  → is_primary_source: true
```

---

## 🔧 Procesamiento del Excel

### Parser

**Archivo:** `src/utils/excel_parser_catalogo_metadata.py`  
**Clase:** `MetadataCatalogParser`

### Funcionalidades

1. **Carga de Datos**:
   - Lee la pestaña "1- Estructura Metadata"
   - Lee la pestaña "3- Jerarquía Normativa"
   - Procesa y normaliza los datos

2. **Métodos Disponibles**:
   ```python
   # Obtener estructura completa
   parser.get_metadata_structure() -> Dict[str, Dict]
   
   # Obtener campos obligatorios
   parser.get_obligatory_fields() -> List[str]
   
   # Obtener campos opcionales
   parser.get_optional_fields() -> List[str]
   
   # Obtener campos por estado de obtención
   parser.get_fields_by_obtained_status("pendiente") -> List[str]
   
   # Obtener información de jerarquía
   parser.get_hierarchy_info(level: int) -> Dict
   parser.get_legal_weight(level: int) -> Optional[int]
   parser.get_is_primary_source(level: int) -> Optional[bool]
   ```

### Uso en el Pipeline

El parser se usa en:
- **`src/metadata/metadata_builder.py`**: Para determinar qué campos son obligatorios y obtener valores de jerarquía normativa
- **Validación**: Para verificar que todos los campos obligatorios estén presentes

**Ejemplo de Uso:**
```python
from src.utils.excel_parser_catalogo_metadata import load_metadata_catalog

# Cargar catálogo
catalog = load_metadata_catalog()

# Obtener campos obligatorios
obligatory_fields = catalog.get_obligatory_fields()
# Resultado: ['document_id', 'source_file', 'code', 'legal_weight', ...]

# Obtener legal_weight para nivel 2
legal_weight = catalog.get_legal_weight(2)
# Resultado: 900

# Obtener is_primary_source para nivel 2
is_primary = catalog.get_is_primary_source(2)
# Resultado: True
```

---

## 📋 Integración con el Pipeline

### Flujo de Construcción de Metadata

```
1. base-conocimiento.xlsx
   └─> Genera metadata source (Paso 1)
   └─> Contiene: document_id, source_file, code, jerarquia_normativa, etc.

2. catalogo-metadata.xlsx
   └─> Define estructura requerida (Pestaña "1- Estructura Metadata")
   └─> Define jerarquía normativa (Pestaña "3- Jerarquía Normativa")

3. metadata_builder.py
   └─> Lee catalogo-metadata.xlsx
   └─> Determina campos obligatorios
   └─> Obtiene legal_weight e is_primary_source según jerarquia_normativa
   └─> Construye metadata final siguiendo el template

4. metadata_template.json
   └─> Template de referencia para estructura final
   └─> Alineado con catalogo-metadata.xlsx
```

### Validación

El catálogo se usa para validar que:
- Todos los campos obligatorios estén presentes
- Los campos opcionales se incluyan si están disponibles
- Los valores de jerarquía normativa sean correctos

---

## 📝 Template de Metadata Final

El archivo `data/metadata/metadata_template.json` es el **template de referencia** que muestra la estructura completa de metadata final. Este template está alineado con `catalogo-metadata.xlsx`.

### Estructura del Template

```json
{
  "document_id": "...",
  "metadata_version": "3.0",
  "generated_at": "...",
  "sources": {...},
  "document_metadata": {
    "general": {...},
    "extraction_information": {...},
    "normative_info": {...},
    "normative_hierarchy": {
      "jerarquia_normativa": 2,
      "legal_weight": 900,        // ← Obtenido de pestaña "3- Jerarquía Normativa"
      "is_primary_source": true,   // ← Obtenido de pestaña "3- Jerarquía Normativa"
      ...
    },
    "document_classification": {...},
    "temporal_context": {...},
    "relationships_document": {...}
  },
  "chunking_statistics": {...},
  "chunking_configuration": {...},
  "chunks": [
    {
      "content": "...",
      "metadata": {
        // Todos los campos definidos en "1- Estructura Metadata"
        ...
      }
    }
  ]
}
```

---

## 🔍 Consultas Útiles

### Obtener Todos los Campos Obligatorios

```python
from src.utils.excel_parser_catalogo_metadata import load_metadata_catalog

catalog = load_metadata_catalog()
obligatory = catalog.get_obligatory_fields()
print(f"Campos obligatorios: {len(obligatory)}")
for field in obligatory:
    print(f"  - {field}")
```

### Obtener Campos Pendientes

```python
catalog = load_metadata_catalog()
pending = catalog.get_fields_by_obtained_status("pendiente")
print(f"Campos pendientes: {len(pending)}")
for field in pending:
    info = catalog.get_metadata_structure()[field]
    print(f"  - {field} ({info['condition']})")
```

### Consultar Jerarquía Normativa

```python
catalog = load_metadata_catalog()

# Obtener información completa de un nivel
level_info = catalog.get_hierarchy_info(2)
print(f"Nivel 2: legal_weight={level_info['legal_weight']}, is_primary={level_info['is_primary_source']}")

# Obtener todos los niveles
all_levels = catalog.get_all_hierarchy_levels()
for level in all_levels:
    info = catalog.get_hierarchy_info(level)
    print(f"Nivel {level}: legal_weight={info['legal_weight']}")
```

### Exportar Estructura a JSON

```python
from pathlib import Path

catalog = load_metadata_catalog()
output_path = Path("output/metadata/final/metadata_catalog_structure.json")
catalog.export_structure_to_json(output_path)
print(f"✅ Estructura exportada a: {output_path}")
```

---

## 📊 Estadísticas y Análisis

### Campos por Categoría

El parser permite analizar:
- **Total de campos**: Obligatorios + opcionales
- **Campos por condición**: Cuántos son obligatorios vs opcionales
- **Campos por estado**: Cuántos están "ok", "pendiente", "key", "informativo"
- **Niveles de jerarquía**: Todos los niveles disponibles y sus valores

### Validación de Completitud

Puedes verificar si un documento tiene todos los campos obligatorios:

```python
catalog = load_metadata_catalog()
obligatory_fields = catalog.get_obligatory_fields()

# Verificar metadata de un documento
document_metadata = {...}  # Metadata del documento
missing_fields = [field for field in obligatory_fields if field not in document_metadata]

if missing_fields:
    print(f"⚠️ Campos obligatorios faltantes: {missing_fields}")
else:
    print("✅ Todos los campos obligatorios están presentes")
```

---

## 🔄 Actualización del Catálogo

### Cuándo Actualizar

El catálogo debe actualizarse cuando:
- Se agregan nuevos campos a la metadata
- Se cambia la condición de un campo (obligatorio ↔ opcional)
- Se modifica la jerarquía normativa
- Se agregan nuevos niveles de jerarquía

### Proceso de Actualización

1. **Editar Excel**: Modificar `data/metadata/catalogo-metadata.xlsx`
2. **Validar**: Ejecutar el parser para verificar que se carga correctamente
3. **Actualizar código**: Si se agregan nuevos campos, actualizar `metadata_builder.py`
4. **Actualizar template**: Si es necesario, actualizar `metadata_template.json`
5. **Probar**: Ejecutar el pipeline de ingesta para verificar que todo funciona

### Validación del Excel

```python
from src.utils.excel_parser_catalogo_metadata import load_metadata_catalog

try:
    catalog = load_metadata_catalog()
    print("✅ Catálogo cargado correctamente")
    print(f"   - Campos: {len(catalog.get_metadata_structure())}")
    print(f"   - Obligatorios: {len(catalog.get_obligatory_fields())}")
    print(f"   - Opcionales: {len(catalog.get_optional_fields())}")
    print(f"   - Niveles de jerarquía: {len(catalog.get_all_hierarchy_levels())}")
except Exception as e:
    print(f"❌ Error cargando catálogo: {e}")
```

---

## 📚 Referencias

- **Parser**: `src/utils/excel_parser_catalogo_metadata.py`
- **Metadata Builder**: `src/metadata/metadata_builder.py`
- **Template**: `data/metadata/metadata_template.json`
- **Pipeline de Metadata**: `docs/PIPELINE_METADATA.md`
- **Base de Conocimiento**: `docs/BASE_CONOCIMIENTO_XLSX.md`

---

## ⚠️ Notas Importantes

1. **El catálogo es la fuente de verdad**: Todos los campos obligatorios deben estar definidos aquí
2. **La jerarquía normativa es crítica**: Se usa para calcular `legal_weight` e `is_primary_source`
3. **El template JSON está alineado**: `metadata_template.json` debe reflejar la estructura del catálogo
4. **Validación automática**: El parser valida que las pestañas requeridas existan
5. **Campos pendientes**: Los campos marcados como "pendiente" deben ser implementados en Python

---

## 🔗 Relación con Otros Componentes

### base-conocimiento.xlsx

- **`base-conocimiento.xlsx`**: Contiene los **datos** de los documentos
- **`catalogo-metadata.xlsx`**: Define la **estructura** de metadata

Ambos trabajan juntos:
- `base-conocimiento.xlsx` proporciona los valores iniciales
- `catalogo-metadata.xlsx` define qué campos son necesarios y cómo completarlos

### metadata_template.json

- **`metadata_template.json`**: Template de referencia en formato JSON
- **`catalogo-metadata.xlsx`**: Catálogo maestro en formato Excel

El template JSON es una representación del catálogo Excel, útil para:
- Referencia rápida de la estructura
- Validación de metadata generada
- Documentación de la estructura final

---

**Última Actualización:** 2025-01-05

