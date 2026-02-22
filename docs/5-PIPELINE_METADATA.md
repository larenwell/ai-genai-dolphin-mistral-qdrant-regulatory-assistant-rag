# Pipeline de Metadata - Paso a Paso

## 📋 Descripción General

Este documento explica el **pipeline completo de construcción de metadata** desde el archivo Excel hasta la metadata final que se ingesta en Qdrant. Cada paso agrega información específica y construye sobre la metadata del paso anterior.

**Objetivo**: Construir metadata completa, normalizada y estructurada para cada documento y chunk que se ingesta en la base de conocimiento.

---

## 🔄 Visión General del Pipeline

```
base-conocimiento.xlsx
    ↓
[Paso 1] source metadata
    ↓
[Paso 2] extraction metadata
    ↓
[Paso 3] translation metadata (opcional)
    ↓
[Paso 4] chunking metadata (intermedia)
    ↓
[Paso 5] final metadata (completa)
    ↓
Qdrant (ingesta)
```

---

## 📍 Paso 1: Metadata de Source

### Script
```bash
python src/utils/excel_parser_base_conocimiento.py
```

### Entrada
- **Archivo**: `data/base-conocimiento.xlsx`
- **Pestañas**: NFPA, FMDS, RNE, Gestion, ISO, SST, Medio Ambiente, ASIS

### Salida
- **Ubicación**: `output/metadata/source/{pestaña}/{document_id}_source.json`
- **Formato**: JSON con estructura `{temp, sincro}`

### Estructura del JSON

```json
{
  "document_id": "NFPA_22_2023_ED_2023",
  "sheet": "NFPA",
  "temp": {
    "Nro.": "1",
    "nombre archivo": "NFPA 22.pdf",
    "Nro. páginas": "222",
    "peso (MB)": "14.4"
  },
  "sincro": {
    "document_id": "NFPA_22_2023_ED_2023",
    "source_file": "NFPA_22_2023_source.pdf",
    "book_title": "Standard for Water Tanks...",
    "code": "NFPA 22",
    "full_name": "NFPA 22: Standard for...",
    "edition": "2023",
    "provider": "NFPA",
    "provider_full_name": "National Fire Protection Association",
    "country": "US",
    "scope": "international",
    "status": "vigente",
    "jerarquia_normativa": 2,
    "language": "en",
    // ... campos opcionales
  }
}
```

### Campos Explicados

#### Sección `temp` (Temporales)
- **`Nro.`**: Número de registro en el Excel
- **`nombre archivo`**: Nombre original del archivo
- **`Nro. páginas`**: Número de páginas del documento
- **`peso (MB)`**: Tamaño del archivo en MB

#### Sección `sincro` (Obligatorios y Opcionales)
- **`document_id`**: ID único del documento (obligatorio)
- **`source_file`**: Nombre del archivo fuente (obligatorio)
- **`book_title`**: Título del documento (obligatorio)
- **`code`**: Código normativo (obligatorio)
- **`full_name`**: Nombre completo (obligatorio)
- **`edition`**: Edición/año (obligatorio)
- **`provider`**: Proveedor/emisor (obligatorio)
- **`provider_full_name`**: Nombre completo del proveedor (obligatorio)
- **`country`**: País (código ISO) (obligatorio)
- **`scope`**: Alcance (obligatorio)
- **`status`**: Estado (obligatorio)
- **`jerarquia_normativa`**: Nivel jerárquico (obligatorio)
- **`language`**: Idioma (obligatorio)
- **Campos opcionales**: `is_base_regulation`, `regulates`, `regulated_by`, `thematic_area`, `tipo_principal`, `tipo_secundario`, `sector`, `disciplina`, `aplicabilidad`, `publication_date`, `effective_date`, `expiration_date`, `supersedes`, `superseded_by`, `related_standards`, `complementary_norms`, `conflicts_with`, `derived_from`

### Procesamiento
1. Lee cada pestaña del Excel
2. Extrae mapeo de columnas (categorías y nombres)
3. Procesa datos desde fila 2 en adelante
4. Normaliza campos según categorías
5. Detecta y maneja duplicados
6. Genera JSON individual por documento

---

## 📍 Paso 2: Metadata de Extracción

### Script
```bash
python src/extraction/generate_markdown.py
```

### Entrada
- **PDFs**: `output/datasources/{pestaña}/{document_id}_source.pdf`
- **Metadata source**: `output/metadata/source/{pestaña}/{document_id}_source.json`

### Salida
- **Ubicación**: `output/metadata/extraction/{pestaña}/{document_id}_extraction.json`
- **Formato**: JSON con información de extracción

### Estructura del JSON

```json
{
  "document_id": "NFPA_22_2023_ED_2023",
  "sheet": "NFPA",
  "source_file": "NFPA_22_2023_source.pdf",
  "extraction_method": "mistral_ocr",
  "mistral_ocr": true,
  "language": "en",
  "total_pages": 222,
  "file_size_mb": 14.4,
  "markdown_length": 505425,
  "docx_conversion": false,
  "extraction_date": "2025-01-20T10:30:00Z",
  "chunks_processed": 1,
  "chunks_failed": 0,
  "extraction_complete": true
}
```

### Campos Explicados

- **`document_id`**: ID del documento (heredado de source)
- **`sheet`**: Pestaña del documento (heredado de source)
- **`source_file`**: Nombre del archivo fuente (heredado de source)
- **`extraction_method`**: Método de extracción usado (`mistral_ocr`)
- **`mistral_ocr`**: Indica si se usó Mistral OCR
- **`language`**: Idioma detectado (`es`, `en`)
- **`total_pages`**: Número total de páginas extraídas
- **`file_size_mb`**: Tamaño del archivo en MB
- **`markdown_length`**: Longitud del markdown generado en caracteres
- **`docx_conversion`**: Si el archivo fue convertido de DOCX a PDF
- **`extraction_date`**: Fecha y hora de extracción (ISO 8601)
- **`chunks_processed`**: Número de chunks procesados (para PDFs grandes)
- **`chunks_failed`**: Número de chunks que fallaron (para PDFs grandes)
- **`extraction_complete`**: Si la extracción se completó exitosamente

### Procesamiento
1. Lee el PDF desde `output/datasources/`
2. Usa Mistral OCR para extraer texto
3. Detecta idioma automáticamente
4. Genera markdown normalizado
5. Guarda metadata de extracción
6. Elimina PDF procesado exitosamente

---

## 📍 Paso 3: Metadata de Traducción (Opcional)

### Script
```bash
python src/translation/translate_pipeline.py
```

### Entrada
- **Markdowns ES**: `output/markdown/processed_es/{pestaña}/{document_id}.md`
- **Metadata source**: `output/metadata/source/{pestaña}/{document_id}_source.json`
- **Metadata extraction**: `output/metadata/extraction/{pestaña}/{document_id}_extraction.json`

### Salida
- **Ubicación**: `output/metadata/translation/{pestaña}/{document_id}_translated.json`
- **Formato**: JSON con información de traducción

### Estructura del JSON

```json
{
  "document_id": "NFPA_22_2023_ED_2023",
  "sheet": "NFPA",
  "source_language": "es",
  "target_language": "en",
  "translated_en": true,
  "translation_method": "mistral_api",
  "translation_date": "2025-01-20T11:00:00Z",
  "markdown_length_original": 505425,
  "markdown_length_translated": 512340,
  "translation_complete": true
}
```

### Campos Explicados

- **`document_id`**: ID del documento (heredado de source)
- **`sheet`**: Pestaña del documento (heredado de source)
- **`source_language`**: Idioma original (`es`)
- **`target_language`**: Idioma destino (`en`)
- **`translated_en`**: Si el documento fue traducido a inglés
- **`translation_method`**: Método usado (`mistral_api`)
- **`translation_date`**: Fecha y hora de traducción (ISO 8601)
- **`markdown_length_original`**: Longitud del markdown original
- **`markdown_length_translated`**: Longitud del markdown traducido
- **`translation_complete`**: Si la traducción se completó exitosamente

### Procesamiento
1. Lee markdown en español desde `processed_es/`
2. Traduce a inglés usando Mistral API
3. Guarda markdown traducido en `processed_en/`
4. Genera metadata de traducción
5. **NO elimina** el archivo original (se necesita para archivo)

---

## 📍 Paso 4: Metadata de Chunking (Intermedia)

### Script
```bash
python src/ingestion/ingest_pipeline.py
```

### Entrada
- **Markdowns EN**: `output/markdown/processed_en/{pestaña}/{document_id}.md`
- **Metadata source**: `output/metadata/source/{pestaña}/{document_id}_source.json`
- **Metadata extraction**: `output/metadata/extraction/{pestaña}/{document_id}_extraction.json`
- **Metadata translation**: `output/metadata/translation/{pestaña}/{document_id}_translated.json` (si existe)

### Salida
- **Ubicación**: `output/metadata/chunking/{pestaña}/{document_id}_chunking.json`
- **Formato**: JSON con metadata intermedia de chunking

### Estructura del JSON

```json
{
  "document_id": "NFPA_22_2023_ED_2023",
  "sheet": "NFPA",
  "chunking_statistics": {
    "total_chunks": 128,
    "char_stats": {
      "mean": 742.1,
      "median": 795.5,
      "min": 41,
      "max": 998,
      "stdev": 232.68
    },
    "word_stats": {
      "mean": 118.3,
      "median": 120.0,
      "min": 5,
      "max": 258
    }
  },
  "chunking_configuration": {
    "chunking_method": "recursive_character",
    "target_chunk_size": 1000,
    "chunk_overlap": 200,
    "model": "nomic-embed-text",
    "embedding_dimension": 768,
    "separators": ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]
  },
  "generated_at": "2025-01-20T12:00:00Z"
}
```

### Campos Explicados

#### `chunking_statistics`
- **`total_chunks`**: Número total de chunks generados
- **`char_stats`**: Estadísticas de caracteres (mean, median, min, max, stdev)
- **`word_stats`**: Estadísticas de palabras (mean, median, min, max)

#### `chunking_configuration`
- **`chunking_method`**: Método usado (`recursive_character`)
- **`target_chunk_size`**: Tamaño objetivo de chunks (1000 caracteres)
- **`chunk_overlap`**: Solapamiento entre chunks (200 caracteres)
- **`model`**: Modelo de embeddings (`nomic-embed-text`)
- **`embedding_dimension`**: Dimensiones del embedding (768)
- **`separators`**: Separadores usados para chunking

#### Campos Generales
- **`document_id`**: ID del documento
- **`sheet`**: Pestaña del documento
- **`generated_at`**: Fecha y hora de generación (ISO 8601)

### Procesamiento
1. Lee markdown en inglés desde `processed_en/`
2. Divide en chunks usando RecursiveCharacterTextSplitter
3. Calcula estadísticas de chunking
4. Guarda configuración usada
5. Genera metadata intermedia

---

## 📍 Paso 5: Metadata Final

### Script
```bash
python src/ingestion/ingest_pipeline.py
```

### Entrada
- **Metadata source**: `output/metadata/source/{pestaña}/{document_id}_source.json`
- **Metadata extraction**: `output/metadata/extraction/{pestaña}/{document_id}_extraction.json`
- **Metadata translation**: `output/metadata/translation/{pestaña}/{document_id}_translated.json` (si existe)
- **Metadata chunking**: `output/metadata/chunking/{pestaña}/{document_id}_chunking.json`
- **Catálogo de metadata**: `data/metadata/catalogo-metadata.xlsx`

### Salida
- **Ubicación**: `output/metadata/final/{pestaña}/{document_id}_final.json`
- **Formato**: JSON completo siguiendo `metadata_template.json`

### Estructura del JSON

```json
{
  "document_id": "NFPA_22_2023_ED_2023",
  "metadata_version": "3.0",
  "generated_at": "2025-01-20T15:30:00Z",
  "sources": {
    "client_metadata": true,
    "elastika_metadata": true,
    "merged_at": "2025-01-20T15:30:00Z"
  },
  "document_metadata": {
    "general": { /* ... */ },
    "extraction_information": { /* ... */ },
    "normative_info": { /* ... */ },
    "normative_hierarchy": { /* ... */ },
    "document_classification": { /* ... */ },
    "temporal_context": { /* ... */ },
    "relationships_document": { /* ... */ }
  },
  "chunking_statistics": { /* ... */ },
  "chunking_configuration": { /* ... */ },
  "chunks": [ /* ... */ ]
}
```

### Secciones Explicadas

#### `document_metadata.general`
Campos generales del documento:
- **`document_id`**: ID único del documento
- **`source_file`**: Nombre del archivo fuente
- **`book_title`**: Título del documento
- **`source_file_hash`**: Hash del archivo (opcional)
- **`language`**: Idioma del documento
- **`total_pages`**: Número total de páginas
- **`file_size_mb`**: Tamaño del archivo en MB

**Origen**: `source` (temp, sincro) + `extraction`

#### `document_metadata.extraction_information`
Información sobre la extracción:
- **`markdown_length`**: Longitud del markdown generado
- **`docx_conversion`**: Si fue convertido de DOCX
- **`translated_en`**: Si fue traducido a inglés
- **`text_extraction_method`**: Método usado (`mistral_ocr`)
- **`mistral_ocr`**: Si se usó Mistral OCR

**Origen**: `extraction` + `translation`

#### `document_metadata.normative_info`
Información normativa básica:
- **`code`**: Código normativo
- **`full_name`**: Nombre completo
- **`edition`**: Edición/año
- **`provider`**: Proveedor/emisor
- **`provider_full_name`**: Nombre completo del proveedor
- **`country`**: País (código ISO)
- **`scope`**: Alcance
- **`status`**: Estado

**Origen**: `source` (sincro)

#### `document_metadata.normative_hierarchy`
Jerarquía normativa:
- **`jerarquia_normativa`**: Nivel jerárquico (1-5)
- **`legal_weight`**: Peso legal (obtenido del catálogo)
- **`is_primary_source`**: Si es fuente primaria (obtenido del catálogo)
- **`is_base_regulation`**: Si es regulación base
- **`code_variations`**: Variaciones del código (generadas automáticamente)
- **`regulates`**: Normas que regula
- **`regulated_by`**: Norma que lo regula
- **`thematic_area`**: Área temática

**Origen**: `source` (sincro) + `catalogo-metadata.xlsx` (jerarquía normativa)

#### `document_metadata.document_classification`
Clasificación del documento:
- **`tipo_principal`**: Tipo principal
- **`tipo_secundario`**: Tipo secundario
- **`sector`**: Sector
- **`disciplina`**: Disciplina (lista)
- **`aplicabilidad`**: Aplicabilidad (lista)

**Origen**: `source` (sincro)

#### `document_metadata.temporal_context`
Contexto temporal:
- **`publication_date`**: Fecha de publicación
- **`effective_date`**: Fecha de vigencia
- **`expiration_date`**: Fecha de expiración
- **`supersedes`**: Reemplaza a
- **`superseded_by`**: Reemplazado por
- **`ingestion_date`**: Fecha de ingesta (generada automáticamente)
- **`last_updated`**: Última actualización (generada automáticamente)
- **`version_hash`**: Hash de versión (generado automáticamente)

**Origen**: `source` (sincro) + generado automáticamente

#### `document_metadata.relationships_document`
Relaciones con otras normas:
- **`related_standards`**: Estándares relacionados
- **`complementary_norms`**: Normas complementarias
- **`conflicts_with`**: Conflictos con
- **`derived_from`**: Derivado de
- **`parent_document_id`**: ID del documento padre

**Origen**: `source` (sincro)

#### `chunking_statistics` y `chunking_configuration`
Heredados de `chunking` metadata.

#### `chunks`
Array de chunks con contenido y metadata completa (ver siguiente sección).

### Procesamiento
1. Carga metadata de source, extraction, translation, chunking
2. Construye `document_metadata` combinando todas las fuentes
3. Obtiene `legal_weight` e `is_primary_source` desde catálogo
4. Genera `code_variations` automáticamente
5. Construye metadata de chunks
6. Guarda metadata final completa

---

## 🔧 Metadata de Chunks

Cada chunk en la metadata final tiene la siguiente estructura:

```json
{
  "content": "Artículo 49.- El empleador debe garantizar...",
  "metadata": {
    // Campos heredados del documento
    "document_id": "LEY_29783_2011",
    "source_file": "Ley 29783.pdf",
    "book_title": "Ley de Seguridad y Salud en el Trabajo",
    "language": "es",
    "code": "Ley 29783",
    "full_name": "Ley de Seguridad y Salud en el Trabajo",
    "edition": "2011",
    "provider": "CONGRESO",
    "provider_full_name": "Congreso de la República del Perú",
    "country": "PE",
    "scope": "national",
    "status": "vigente",
    "jerarquia_normativa": 2,
    "legal_weight": 900,
    "is_primary_source": true,
    "is_base_regulation": true,
    "thematic_area": "seguridad_salud_trabajo",
    "tipo_principal": "ley_organica",
    "tipo_secundario": "ley_organica_sst",
    "sector": "seguridad_industrial",
    "disciplina": ["seguridad_ocupacional"],
    "aplicabilidad": ["construccion", "mineria", "industria"],
    
    // Estructura jerárquica (extraída del texto)
    "hierarchy": {
      "level": 1,
      "level_name": "articulo",
      "chapter": "5",
      "chapter_title": "Obligaciones del Empleador",
      "section": null,
      "section_title": null,
      "subsection": null,
      "subsection_title": null,
      "article": "49",
      "article_title": "Obligaciones del Empleador",
      "full_reference": "Ley 29783:2011, Art. 49"
    },
    
    // Propiedades del chunk
    "chunk_index": 45,
    "total_chunks": 128,
    "chunk_size": 625,
    "chunk_words": 96,
    "chunking_method": "recursive_character",
    "target_chunk_size": 1000,
    "chunk_overlap": 200,
    "is_header_chunk": false,
    "is_table_chunk": false,
    "is_list_chunk": true,
    "has_citations": false,
    
    // Clasificación temática
    "topic_category": "gestion_sst",
    "subtopics": ["comites_sst", "auditorias_inspecciones"],
    "keywords_manual": ["comite_seguridad", "supervisor_sst"],
    "keywords_auto": ["capacitacion", "empleador", "seguridad"],
    
    // Contexto temporal
    "publication_date": "2011-08-20",
    "effective_date": "2011-08-21",
    "expiration_date": null,
    "supersedes": "Ley 28806",
    "ingestion_date": "2025-01-15T14:23:00Z",
    "last_updated": "2025-01-15T14:23:00Z",
    "version_hash": "v1_a3f2b9c1",
    
    // Relaciones
    "related_standards": ["DS 005-2012-TR", "RM 249-2017-TR"],
    "complementary_norms": ["ISO 45001"],
    "parent_document_id": "LEY_29783_2011",
    "sibling_chunks": [44, 46],
    
    // Referencias y citas
    "citation_format": "Ley 29783:2011, Artículo 49",
    "short_citation": "Ley 29783 (2011) Art. 49",
    "display_title": "Obligaciones del Empleador",
    "priority_level": "high"
  }
}
```

### Campos de Chunk Explicados

#### Campos Heredados del Documento
Todos los campos de `document_metadata` se heredan a cada chunk.

#### `hierarchy` (Estructura Jerárquica)
Extraída automáticamente del texto usando `TextStructureExtractor`:
- **`level`**: Nivel jerárquico (1=artículo, 2=capítulo, 3=sección, 4=subsección, 5=general)
- **`level_name`**: Nombre descriptivo del nivel
- **`chapter`**: Número de capítulo (extraído con regex)
- **`chapter_title`**: Título del capítulo
- **`section`**: Número de sección
- **`section_title`**: Título de la sección
- **`subsection`**: Número de subsección
- **`subsection_title`**: Título de la subsección
- **`article`**: Número de artículo
- **`article_title`**: Título del artículo
- **`full_reference`**: Referencia completa (ej: "Ley 29783:2011, Art. 49")

#### Propiedades del Chunk
- **`chunk_index`**: Índice del chunk (0-based)
- **`total_chunks`**: Total de chunks del documento
- **`chunk_size`**: Tamaño real del chunk en caracteres
- **`chunk_words`**: Cantidad de palabras en el chunk
- **`chunking_method`**: Método de chunking usado
- **`target_chunk_size`**: Tamaño objetivo configurado
- **`chunk_overlap`**: Solapamiento configurado
- **`is_header_chunk`**: Si contiene solo headers
- **`is_table_chunk`**: Si contiene una tabla
- **`is_list_chunk`**: Si contiene listas
- **`has_citations`**: Si contiene referencias a otras normas

#### Clasificación Temática
- **`topic_category`**: Categoría temática principal
- **`subtopics`**: Subcategorías temáticas
- **`keywords_manual`**: Keywords manuales
- **`keywords_auto`**: Keywords extraídos automáticamente

#### Referencias y Citas
Generadas automáticamente:
- **`citation_format`**: Formato completo de cita
- **`short_citation`**: Cita abreviada
- **`display_title`**: Título corto para mostrar
- **`priority_level`**: Nivel de prioridad (`high`, `medium`, `low`)

#### Relaciones
- **`parent_document_id`**: ID del documento padre
- **`sibling_chunks`**: Índices de chunks contiguos (anterior y siguiente)

---

## 🔗 Integración con Catálogo de Metadata

El archivo `data/metadata/catalogo-metadata.xlsx` proporciona:

### Hoja "1- Estructura Metadata"
- Define qué campos son **obligatorios** u **opcionales**
- Indica de dónde se obtiene cada campo
- Define la estructura final de metadata

### Hoja "3- Jerarquía Normativa"
- Mapea `jerarquia_normativa` → `legal_weight`
- Mapea `jerarquia_normativa` → `is_primary_source`
- Define niveles jerárquicos y sus valores asociados

**Ejemplo:**
```
jerarquia_normativa: 2
  → legal_weight: 900
  → is_primary_source: true
```

---

## 📊 Flujo de Construcción de Metadata

```
1. source metadata
   └─> Lee base-conocimiento.xlsx
   └─> Genera JSON con temp + sincro

2. extraction metadata
   └─> Usa source metadata
   └─> Agrega información de extracción
   └─> Detecta idioma

3. translation metadata (opcional)
   └─> Usa source + extraction metadata
   └─> Agrega información de traducción

4. chunking metadata (intermedia)
   └─> Usa source + extraction + translation metadata
   └─> Agrega estadísticas de chunking
   └─> Guarda configuración

5. final metadata
   └─> Combina source + extraction + translation + chunking
   └─> Consulta catálogo para legal_weight e is_primary_source
   └─> Genera code_variations automáticamente
   └─> Extrae estructura jerárquica de cada chunk
   └─> Construye metadata completa de chunks
   └─> Sigue estructura de metadata_template.json
```

---

## 🔧 Módulos Involucrados

### `src/utils/excel_parser_base_conocimiento.py`
- Procesa `base-conocimiento.xlsx`
- Genera metadata de source

### `src/extraction/generate_markdown.py`
- Extrae contenido de PDFs
- Genera metadata de extraction

### `src/translation/translate_pipeline.py`
- Traduce documentos
- Genera metadata de translation

### `src/metadata/metadata_builder.py`
- Construye metadata final
- Combina todas las fuentes
- Genera metadata de chunks

### `src/metadata/text_structure_extractor.py`
- Extrae estructura jerárquica del texto
- Genera code_variations
- Detecta tipo de chunk
- Genera referencias y citas

### `src/utils/excel_parser_catalogo_metadata.py`
- Procesa `catalogo-metadata.xlsx`
- Proporciona información de jerarquía normativa

---

## 📝 Notas Importantes

1. **La metadata se construye incrementalmente**: Cada paso agrega información sobre el anterior.

2. **Los campos obligatorios deben estar completos**: El catálogo define qué campos son obligatorios.

3. **La jerarquía normativa se obtiene del catálogo**: `legal_weight` e `is_primary_source` se obtienen desde `catalogo-metadata.xlsx`.

4. **Los code_variations se generan automáticamente**: Si no existen en source, se generan usando `generate_code_variations()`.

5. **La estructura jerárquica se extrae del texto**: Cada chunk analiza su contenido para extraer nivel, capítulo, sección, artículo, etc.

6. **La metadata final sigue el template**: La estructura final debe seguir `data/metadata/metadata_template.json`.

---

## 📚 Referencias

- **Template de metadata**: `data/metadata/metadata_template.json`
- **Catálogo de metadata**: `data/metadata/catalogo-metadata.xlsx`
- **Base de conocimiento**: `data/base-conocimiento.xlsx`
- **Documentación del Pipeline**: `docs/PIPELINE_INGESTA.md`
- **Documentación de base-conocimiento.xlsx**: `docs/BASE_CONOCIMIENTO_XLSX.md`

---

**Última Actualización:** 2025-01-05

