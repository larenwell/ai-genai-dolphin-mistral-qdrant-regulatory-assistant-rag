# Pipeline de Ingesta de Documentos

## 📋 Visión General

Este documento describe el pipeline completo para ingestar documentos a la base de conocimiento, optimizado para VPS con espacio limitado.

---

## 🗂️ Estructura de Directorios

```
proyecto/
├── data/
│   ├── input/                      # 🔴 TEMPORAL: Archivos originales
│   │   ├── NFPA 22.pdf             #    Se eliminan después de procesar
│   │   └── Manual.docx             #    (están respaldados en nube)
│   │
│   ├── processed/                  # 📦 BACKUP LOCAL: Formato original
│   │   └── 20241218_120530/        #    Timestamp: YYYYMMDD_HHMMSS
│   │       ├── NFPA 22.pdf         #    PDF original
│   │       └── Manual.docx         #    ⚠️ DOCX original (no PDF)
│   │
│   └── base-conocimiento.xlsx      # ✅ MANTENER: Fuente de verdad
│
├── output/
│   ├── metadata/
│   │   ├── source/                 # ✅ MANTENER: Metadata de source (Paso 1)
│   │   │   ├── NFPA/
│   │   │   ├── FMDS/
│   │   │   └── ...
│   │   ├── extraction/              # ✅ MANTENER: Metadata de extracción (Paso 3)
│   │   │   ├── NFPA/
│   │   │   └── ...
│   │   ├── translation/             # ✅ MANTENER: Metadata de traducción (Paso 4)
│   │   │   ├── NFPA/
│   │   │   └── ...
│   │   ├── chunking/                # ✅ MANTENER: Metadata intermedia (Paso 5)
│   │   │   ├── NFPA/
│   │   │   └── ...
│   │   └── final/                   # ✅ MANTENER: Metadata final normalizada (Paso 5)
│   │       ├── NFPA/
│   │       └── ...
│   │
│   ├── datasources/                 # 🔴 TEMPORAL: SIEMPRE PDFs
│   │   └── NFPA/                    #    Eliminar después de generar markdown
│   │       └── NFPA_22_2023_source.pdf
│   │
│   ├── chunking/                    # ✅ MANTENER: Chunks con metadata (Paso 5)
│   │   └── NFPA/
│   │       └── NFPA_22_2023_recursive_character_chunks.json
│   │
│   ├── embeddings_preview/          # ✅ MANTENER: Preview de embeddings (Paso 5)
│   │   └── NFPA/
│   │       └── NFPA_22_2023_recursive_character_embeddings_preview.json
│   │
│   └── markdown/                    # ✅ MANTENER: Markdowns finales
│       ├── processed_es/            # 🔴 TEMPORAL: Markdowns en español (Paso 3)
│       │   └── NFPA/                #    Se mueven a archived/ en Paso 5
│       │       └── NFPA_22_2023.md
│       ├── processed_en/            # 🔴 TEMPORAL: Markdowns en inglés (Paso 3/4)
│       │   └── NFPA/                #    Se mueven a archived/ en Paso 5
│       │       └── NFPA_22_2023.md
│       └── archived/                # ✅ MANTENER: Markdowns archivados (Paso 5)
│           ├── NFPA_ES/             #    Markdowns en español archivados
│           └── NFPA_EN/             #    Markdowns en inglés archivados
```

### ⚠️ Formatos de Archivos

| Ubicación | Formato | Descripción |
|-----------|---------|-------------|
| `data/input/` | DOC, DOCX, PDF | Archivos originales tal como llegan |
| `data/processed/{timestamp}/` | DOC, DOCX, PDF | **Formato ORIGINAL** (backup) |
| `output/datasources/` | **SOLO PDF** | Convertidos/copiados para markdown |
| `output/markdown/` | MD | Resultado final para ingesta |

---

## 🔄 Pipeline de Procesamiento

### Paso 1: Preparar Metadata
```bash
python src/utils/excel_parser_base_conocimiento.py
```

**Entrada:** `data/base-conocimiento.xlsx`  
**Salida:** `output/metadata/source/{pestaña}/{document_id}_source.json`  
**Estado:** ✅ MANTENER (archivos pequeños, necesarios para referencia)

**Manejo de Duplicados:**

El script detecta y maneja duplicados de dos formas:

1. **Duplicados dentro de la misma pestaña:**
   - ✅ **Usa la primera ocurrencia** encontrada en la pestaña
   - ⚠️ **Muestra advertencia** para cada duplicado detectado:
     ```
     ⚠️ Duplicado detectado en fila XX: DOC_ID (pestaña: NOMBRE)
        Se usará la primera ocurrencia definida en la fila YY, la fila XX será ignorada.
     ```
   - ❌ **Ignora las siguientes ocurrencias** del mismo `document_id` en la misma pestaña

2. **Duplicados entre diferentes pestañas:**
   - ✅ **Usa la primera ocurrencia de la primera pestaña** (según orden de `DOCUMENT_SHEETS`)
   - ⚠️ **Muestra advertencia** cuando se detecta duplicado entre pestañas:
     ```
     ⚠️ Duplicado entre pestañas detectado en fila XX: DOC_ID
        Ya fue procesado en pestaña 'NOMBRE_PESTAÑA_1' (fila YY).
        Se usará la primera ocurrencia de 'NOMBRE_PESTAÑA_1', esta ocurrencia en 'NOMBRE_PESTAÑA_2' (fila XX) será ignorada.
     ```
   - ❌ **Ignora las ocurrencias** en pestañas posteriores

**Ejemplos:**
- **Dentro de pestaña:** Si `DL_1499_2020_ED_2020` aparece en filas 13, 28, 45 de la pestaña SST:
  - Fila 13: Se procesa y se guarda ✅
  - Fila 28: Se muestra advertencia y se ignora ⚠️
  - Fila 45: Se muestra advertencia y se ignora ⚠️

- **Entre pestañas:** Si `DS_017_2009_ED_2009` aparece en pestaña SST (fila 27) y en pestaña Medio Ambiente (fila 18):
  - SST, Fila 27: Se procesa y se guarda ✅ (primera pestaña según orden)
  - Medio Ambiente, Fila 18: Se muestra advertencia de duplicado entre pestañas y se ignora ⚠️

**Recomendación:** Revisar y corregir duplicados en el Excel para evitar inconsistencias y asegurar que cada `document_id` aparezca solo una vez.

### Paso 2: Convertir/Preparar PDFs
```bash
python src/conversion/docx_to_pdf.py
```

**Entrada:** `data/input/*.{pdf,doc,docx}`  (se cortan los archivos)
**Salida:** `output/datasources/{pestaña}/{document_id}_source.pdf` (SIEMPRE PDF)  
**Backup:** `data/processed/{timestamp}/` (formato original: DOC, DOCX o PDF)  
**Estado:** 🔴 TEMPORAL - eliminar los archivos de datasources después del paso 3

**Importante:** 
- DOC/DOCX → se convierte a PDF (requiere LibreOffice)
- PDF → se copia
- En `data/processed/` va el archivo **ORIGINAL** (no el convertido)

### Paso 3: Generar Markdown
```bash
python src/extraction/generate_markdown.py
```

**Entrada:**
- `output/datasources/{pestaña}/{document_id}_source.pdf` - PDFs generados en el Paso 2
- `output/metadata/source/{pestaña}/{document_id}_source.json` - Metadata del Paso 1

**Salida:**
- `output/markdown/processed_es/{pestaña}/{document_id}.md` - Markdowns en español
- `output/markdown/processed_en/{pestaña}/{document_id}.md` - Markdowns en inglés (si ya estaban en inglés)
- `output/metadata/extraction/{pestaña}/{document_id}_extraction.json` - Metadata de extracción

**Estado:** 
- `processed_es/` y `processed_en/`: 🔴 TEMPORAL - Se mueven automáticamente a `archived/` durante el Paso 5 (ingesta)
- `metadata/extraction/`: ✅ MANTENER - Metadata de referencia

**Proceso:**
1. Lee PDFs desde `output/datasources/{pestaña}/` (formato: `{document_id}_source.pdf`)
2. Carga metadata desde `output/metadata/source/{pestaña}/`
3. Extrae contenido con **Mistral OCR** (requiere `MISTRAL_API_KEY`)
   - Soporta documentos grandes: divide automáticamente PDFs > 1000 páginas o > 100MB
   - Valida que todo el contenido se procese correctamente
4. **Detecta idioma automáticamente** (español o inglés)
5. Guarda markdown en carpeta según idioma detectado:
   - Español → `processed_es/{pestaña}/`
   - Inglés → `processed_en/{pestaña}/`
6. Genera metadata de extracción con información del proceso (idioma detectado, páginas procesadas, etc.)
7. **Elimina archivos PDF de datasources** solo si se procesaron exitosamente

**Manejo de archivos:**
- ✅ **Archivos procesados exitosamente:** Se eliminan automáticamente de `datasources/`
- ❌ **Archivos con errores:** Se mantienen en `datasources/` para revisión y corrección
- ⚠️ **Recomendación:** Revisar archivos con errores antes de volver a ejecutar el script

**Nota:** Los documentos en español se traducen a inglés en el Paso 4 (traducción separada).

### Paso 4: Traducir (si aplica)
```bash
python src/translation/translate_pipeline.py
```

**Entrada:**
- `output/markdown/processed_es/{pestaña}/{document_id}.md` - Markdowns en español del Paso 3

**Salida:**
- `output/markdown/processed_en/{pestaña}/{document_id}.md` - Markdowns traducidos a inglés
- `output/metadata/translation/{pestaña}/{document_id}_translated.json` - Metadata de traducción

**Estado:**
- `processed_en/`: 🔴 TEMPORAL - Se mueve automáticamente a `archived/{pestaña}_EN/` durante el Paso 5 (ingesta)
- `metadata/translation/`: ✅ MANTENER - Metadata de referencia

**Proceso:**
1. Lee documentos desde `output/markdown/processed_es/{pestaña}/`
2. Los documentos en `processed_en/` se mantienen (ya están en inglés, no se retraducen)
3. Traduce documentos desde `processed_es/` a `processed_en/{pestaña}/` usando **Mistral API**
4. Genera metadata de traducción con estadísticas (chars traducidos, API calls, etc.)
5. **Modo reanudación:** Omite archivos ya traducidos si se interrumpe el proceso

**Nota:** Solo traduce documentos que están en español. Los documentos que ya están en inglés (detectados en el Paso 3) se mantienen en `processed_en/` sin traducir.

### Paso 5: Ingestar a Qdrant
```bash
python src/ingestion/ingest_pipeline.py
```

**Opciones de ejecución:**
```bash
# Modo interactivo (pregunta opción)
python src/ingestion/ingest_pipeline.py

# Opción 1: Agregar sin verificar duplicados
python src/ingestion/ingest_pipeline.py --option 1

# Opción 2: Verificar duplicados antes de agregar (recomendado)
python src/ingestion/ingest_pipeline.py --option 2
```

**Entrada:**
- `output/markdown/processed_en/{pestaña}/{document_id}.md` - Markdowns en inglés del Paso 4
- `output/metadata/source/{pestaña}/{document_id}_source.json` - Metadata del Paso 1
- `output/metadata/extraction/{pestaña}/{document_id}_extraction.json` - Metadata del Paso 3
- `output/metadata/translation/{pestaña}/{document_id}_translated.json` - Metadata del Paso 4 (si aplica)

**Salida:**
- **Qdrant collection:** `normativa-asistente-kb` (definida en `.env` como `QDRANT_COLLECTION_NAME`)
- `output/chunking/{pestaña}/{document_id}_recursive_character_chunks.json` - Chunks con metadata
- `output/metadata/chunking/{pestaña}/{document_id}_chunking.json` - Metadata intermedia de chunking
- `output/metadata/final/{pestaña}/{document_id}_final.json` - Metadata final normalizada
- `output/embeddings_preview/{pestaña}/{document_id}_recursive_character_embeddings_preview.json` - Preview de embeddings
- `output/markdown/archived/{pestaña}_ES/{document_id}.md` - Markdowns en español archivados (automático)
- `output/markdown/archived/{pestaña}_EN/{document_id}.md` - Markdowns en inglés archivados (automático)

**Estado:** ✅ MANTENER - archivos finales para referencia

**Comportamiento de archivos de salida:**
- ✅ **Conservación de datos:** Los archivos de documentos diferentes se conservan. Cada archivo tiene un nombre único basado en `document_id`.
- ⚠️ **Sobrescritura:** Si se procesa el mismo `document_id` nuevamente, los archivos correspondientes se sobrescriben con la nueva versión.
- 📁 **Organización por pestaña:** Todos los archivos se organizan por pestaña (`{pestaña}/`), permitiendo múltiples ejecuciones sin perder datos de otros documentos.

**Proceso:**
1. Lee archivos markdown desde `output/markdown/processed_en/{pestaña}/`
2. Construye metadata completa combinando:
   - Metadata de source (`_source.json` del Paso 1)
   - Metadata de extraction (`_extraction.json` del Paso 3)
   - Metadata de translation (`_translated.json` del Paso 4, si existe)
3. Genera chunks usando **RecursiveCharacterTextSplitter**:
   - Chunk size: 1000 caracteres (configurable)
   - Chunk overlap: 200 caracteres (configurable)
   - Separadores: `["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]`
4. Construye metadata completa para cada chunk:
   - Metadata heredada del documento (código, título, edición, etc.)
   - Estructura jerárquica (nivel, capítulo, sección, artículo)
   - Propiedades del chunk (índice, tamaño, palabras, método de chunking)
   - Relaciones (chunks hermanos, documento padre)
   - Referencias y citas (full_reference, citation_format)
   - Metadata normativa (legal_weight, is_primary_source, jerarquía)
5. Genera embeddings usando **Ollama** (modelo: `nomic-embed-text`)
   - Batch size: 10 documentos por lote
   - Dimensiones: 768 (modelo nomic-embed-text)
6. Guarda archivos intermedios y finales:
   - `output/chunking/{pestaña}/{document_id}_recursive_character_chunks.json` - Chunks con metadata
   - `output/metadata/chunking/{pestaña}/{document_id}_chunking.json` - Metadata intermedia
   - `output/metadata/final/{pestaña}/{document_id}_final.json` - Metadata final normalizada
   - `output/embeddings_preview/{pestaña}/{document_id}_recursive_character_embeddings_preview.json` - Preview
7. Ingesta en Qdrant con metadata normalizada:
   - Collection: `normativa-asistente-kb` (definida en `.env`)
   - Cada chunk se almacena con su embedding y metadata completa
8. **Archiva automáticamente** los markdowns procesados:
   - Mueve archivos de `processed_es/{pestaña}/` → `archived/{pestaña}_ES/`
   - Mueve archivos de `processed_en/{pestaña}/` → `archived/{pestaña}_EN/`
   - Deja las carpetas `processed_es/` y `processed_en/` vacías para futuros procesamientos

**Configuración:**
- **Modelo embeddings:** `nomic-embed-text` (Ollama)
- **Batch size:** 10 documentos por lote
- **Opciones de ingesta:**
  - Opción 1: Agregar sin verificar duplicados (más rápido)
  - Opción 2: Verificar duplicados por `document_id` antes de agregar (recomendado)

**Requisitos:**
- Ollama ejecutándose en `http://localhost:11434`
- Qdrant ejecutándose en `http://localhost:6333`
- Modelo `nomic-embed-text` instalado en Ollama: `ollama pull nomic-embed-text`
- Variables de entorno configuradas en `.env`:
  - `QDRANT_COLLECTION_NAME` (por defecto: `normativa-asistente-kb`)
  - `MISTRAL_API_KEY` (para traducción si aplica)

### Paso 6: Limpieza (para VPS)
```bash
python src/utils/cleanup.py  # Por implementar
```

**Elimina:**
- `output/datasources/` (PDFs temporales)
- `data/processed/` (backups si hay poco espacio)

---

## 📊 Flujo de Archivos

### Caso 1: Archivo PDF
```
┌─────────────────────────────────────────────────────────────────────┐
│ ARCHIVO ORIGINAL (PDF)                                               │
│ data/input/NFPA 22.pdf                                              │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 1: excel_parser_base_conocimiento.py                            │
│ → output/metadata/source/NFPA/NFPA_22_2023_ED_2023_source.json      │
│   (JSON con metadata de Sincro)                                      │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 2: docx_to_pdf.py                                               │
│ → output/datasources/NFPA/NFPA_22_2023_ED_2023_source.pdf (copiado)    │
│ → data/processed/20241218_120530/NFPA 22.pdf (backup PDF original)  │
└─────────────────┬───────────────────────────────────────────────────┘
```

### Caso 2: Archivo DOC/DOCX
```
┌─────────────────────────────────────────────────────────────────────┐
│ ARCHIVO ORIGINAL (DOCX)                                              │
│ data/input/Manual.docx                                              │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 1: excel_parser_base_conocimiento.py                            │
│ → output/metadata/source/Gestion/GES_MAN_001_source.json            │
│   (JSON con metadata de Sincro)                                      │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 2: docx_to_pdf.py                                               │
│ → output/datasources/Gestion/GES_MAN_001_source.pdf (⚡ CONVERTIDO)    │
│ → data/processed/20241218_120530/Manual.docx (⚠️ DOCX ORIGINAL)     │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 3: generate_markdown.py                                         │
│ → output/markdown/processed_es/NFPA/NFPA_22_2023_ED_2023.md         │
│   (o processed_en/ si ya está en inglés)                            │
│ → output/metadata/extraction/NFPA/NFPA_22_2023_ED_2023_extraction.json │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 4: translate_pipeline.py (si language=es)                     │
│ → output/markdown/processed_en/NFPA/NFPA_22_2023_ED_2023.md          │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 5: ingest_pipeline.py                                           │
│ → Qdrant collection: normativa-asistente-kb (desde .env)            │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PASO 6: cleanup.py                                                   │
│ → Elimina output/datasources/ y data/processed/ (opcional)          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 💾 Gestión de Espacio en VPS

### Recomendaciones:

1. **Siempre mantener:**
   - `data/base-conocimiento.xlsx` (fuente de verdad)
   - `output/metadata/source/` (JSONs pequeños, referencia)
   - `output/metadata/extraction/` (Metadata de extracción)
   - `output/metadata/translation/` (Metadata de traducción, si aplica)
   - `output/metadata/chunking/` (Metadata intermedia de chunking)
   - `output/metadata/final/` (Metadata final normalizada)
   - `output/chunking/` (Chunks con metadata)
   - `output/embeddings_preview/` (Preview de embeddings)
   - `output/markdown/archived/` (Markdowns archivados)

3. **Eliminar después de procesar:**
   - `output/datasources/` (PDFs temporales)
   - `data/input/` (vaciar después de procesar)

4. **Opcional (según espacio):**
   - `data/processed/{timestamp}/` (backups)
   - Recomendación: Subir backups a S3/Google Drive y eliminar local

### Comandos de Limpieza:

```bash
# Eliminar datasources (después de generar markdown)
rm -rf output/datasources/*

# Eliminar backups antiguos (mantener último)
ls -t data/processed/ | tail -n +2 | xargs -I {} rm -rf data/processed/{}

# Eliminar todos los backups
rm -rf data/processed/*
```

---

## 🔧 Comandos del Pipeline

### Pipeline Completo:
```bash
# 1. Generar metadata desde Excel
python src/utils/excel_parser_base_conocimiento.py

# 2. Convertir DOC/DOCX a PDF (o copiar PDFs)
#    - Originales van a data/processed/{timestamp}/
#    - PDFs van a output/datasources/{pestaña}/
python src/conversion/docx_to_pdf.py

# 3. Generar markdown desde PDFs
python src/extraction/generate_markdown.py

# 4. Traducir (si hay documentos en español)
python src/translation/translate_pipeline.py

# 5. Ingestar a Qdrant
python src/ingestion/ingest_pipeline.py

# 6. Limpiar temporales (datasources ya no se necesita)
rm -rf output/datasources/*
```

### Limpiar backups antiguos (opcional, si hay poco espacio):
```bash
# Mantener solo el último backup
ls -t data/processed/ | tail -n +2 | xargs -I {} rm -rf data/processed/{}
```

---

## 📝 Notas Importantes

1. **Backup externo:** Si necesitas conservar archivos originales, súbelos a S3 o Google Drive antes de eliminarlos del VPS.

2. **Re-procesamiento:** Si necesitas re-procesar un documento:
   - Colócalo en `data/input/`
   - Asegúrate que esté en `base-conocimiento.xlsx` con condición "por ingestar"
   - Ejecuta el pipeline

3. **Nombres de archivos:** 
   - `{document_id}_source.json` → Metadata de source (Paso 1)
   - `{document_id}_source.pdf` → PDF fuente (datasources, Paso 2)
   - `{document_id}.md` → Markdown final (Paso 3)
   - `{document_id}_extraction.json` → Metadata de extracción (Paso 3)
   - `{document_id}_translated.json` → Metadata de traducción (Paso 4, si aplica)
   - `{document_id}_chunking.json` → Metadata intermedia de chunking (Paso 5)
   - `{document_id}_final.json` → Metadata final normalizada (Paso 5)
   - `{document_id}_recursive_character_chunks.json` → Chunks con metadata (Paso 5)
   - `{document_id}_recursive_character_embeddings_preview.json` → Preview de embeddings (Paso 5)

4. **Condiciones válidas:** "por ingestar", "por cargar" (case insensitive)

---

## 📅 Historial de Backups

Los backups se guardan con timestamp en formato: `YYYYMMDD_HHMMSS`

Ejemplo:
```
data/processed/
├── 20241218_120530/
│   ├── NFPA 22.pdf          # PDF original
│   └── Manual.docx           # ⚠️ DOCX original (no convertido)
├── 20241219_093015/
│   ├── LEY 29783.pdf
│   └── Procedimiento.doc     # ⚠️ DOC original
```

**Importante:** En `processed/` se guarda el archivo en su **formato original**:
- Si llegó como DOC → se guarda como DOC
- Si llegó como DOCX → se guarda como DOCX
- Si llegó como PDF → se guarda como PDF

El PDF convertido está en `output/datasources/` (temporal).

---

**Última actualización:** 2025-01-05

---

## 🔧 Requisitos del Sistema

Para conversión de DOC/DOCX a PDF:

```bash
# Opción 1: LibreOffice (RECOMENDADO - soporta DOC y DOCX)
apt install libreoffice

# Opción 2: Solo DOCX (alternativas Python)
pip install docx2pdf        # Requiere LibreOffice/Word instalado
pip install python-docx reportlab  # Conversión básica
```

**Nota:** Los archivos DOC (Word 97-2003) **requieren LibreOffice** para conversión.

