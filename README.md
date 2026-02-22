# Asistente de Normativa - Sistema RAG Completo

## 📋 Descripción General

Sistema de Asistente Virtual Inteligente para consultas sobre normativa técnica en español, implementado con **RAG (Retrieval-Augmented Generation)** y optimizado para el flujo de trabajo de base de conocimiento en inglés y respuestas en español.

**Versión:** v0.2.1  
**Última Actualización:** 2025-01-05

---

## 🎯 Características Principales

### Procesamiento de Documentos
- ✅ **Extracción Inteligente**: Procesamiento de PDFs y DOCX usando Mistral OCR
- ✅ **Soporte para Documentos Grandes**: División automática de PDFs > 1000 páginas o > 100MB
- ✅ **Preservación de Estructura**: Mantiene formato, tablas, imágenes y estructura jerárquica
- ✅ **Conversión a Markdown**: Normalización a formato Markdown estructurado
- ✅ **Detección de Idioma**: Automática (español/inglés)

### Pipeline de Ingestión Completo
- ✅ **Pipeline Modular**: 5 pasos bien definidos (metadata → conversión → extracción → traducción → ingesta)
- ✅ **Metadata Completa**: Sistema robusto de metadata con jerarquía normativa
- ✅ **Múltiples Métodos de Chunking**: Recursive, semantic, structural, hybrid
- ✅ **Gestión de Duplicados**: Detección y manejo automático de documentos duplicados
- ✅ **Archivado Automático**: Movimiento automático de markdowns procesados

### Sistema de Búsqueda Híbrida (FASE C)
- ✅ **Búsqueda Densa (Dense)**: Búsqueda semántica vectorial con embeddings
- ✅ **Búsqueda Sparse (BM25)**: Búsqueda por palabras clave
- ✅ **Re-ranking con Metadata**: Priorización por legal_weight, is_primary_source, nivel jerárquico
- ✅ **Filtros Inteligentes**: Pre-filtrado basado en código normativo, variaciones, jerarquía
- ✅ **Parser de Consultas**: Extracción automática de normas, artículos, capítulos, secciones
- ✅ **Composición de Contexto**: Formateo estructurado para LLM

### Modelos y Tecnologías
- ✅ **Embeddings Locales**: Ollama con modelo `nomic-embed-text` (768 dimensiones)
- ✅ **LLM**: Mistral AI (`mistral-small-latest`) para generación de respuestas
- ✅ **Base de Datos Vectorial**: Qdrant con distancia Cosine
- ✅ **OCR Avanzado**: Mistral OCR para extracción de texto de PDFs

### Interfaz y Experiencia de Usuario
- ✅ **Interfaz Web Moderna**: Chainlit con diseño responsive
- ✅ **Clasificación de Preguntas**: 4 tipos (factual, interpretative, comparative, procedural)
- ✅ **Respuestas Adaptativas**: Estilo de respuesta según tipo de pregunta
- ✅ **Sistema de Fuentes**: Visualización de fuentes con relevancia y metadata
- ✅ **Manejo de Errores**: Mensajes claros y sugerencias de seguimiento

### Traducción Automática
- ✅ **Traducción en Tiempo Real**: Para consultas Q&A (español ↔ inglés)
- ✅ **Traducción por Lotes**: Pipeline completo de traducción de documentos
- ✅ **Optimización Técnica**: Especializado en documentos técnicos/legales
- ✅ **Modo Reanudación**: Continuación automática de traducciones interrumpidas

### Infraestructura y DevOps
- ✅ **Script Unificado**: `rag_system.sh` para gestión completa del sistema
- ✅ **Firewall Persistente**: Reglas de firewall automáticas y persistentes
- ✅ **Gestión de Servicios**: Inicio, parada, monitoreo de todos los servicios
- ✅ **Health Checks**: Verificación automática de servicios dependientes
- ✅ **Docker Compose**: Orquestación de contenedores (Qdrant, PostgreSQL, Ollama, LocalStack)

### Evaluación y Validación
- ✅ **Evaluación RAGAS**: Métricas de calidad (context recall, answer relevancy, faithfulness)
- ✅ **Validación de Ingestión**: Scripts de verificación de completitud
- ✅ **Análisis de Documentos**: Detección de duplicados y análisis de calidad
- ✅ **Reportes Automáticos**: Generación de reportes Excel y JSON

---

## 🏗️ Arquitectura del Sistema

### Arquitectura Bilingüe Única
```
Usuario (Español) 
    ↓
Traducción ES→EN (query)
    ↓
Búsqueda Híbrida (Base de Conocimiento en Inglés)
    ↓
Traducción EN→ES (contexto)
    ↓
Generación de Respuesta (Español)
    ↓
Usuario (Español)
```

### Componentes Principales

#### 1. **Extracción de Documentos** (`src/extraction/`)
- **`generate_markdown.py`**: Script principal de extracción
- **`markdown_extraction.py`**: Controlador de extracción con Mistral OCR
- **Características**:
  - Extracción con Mistral OCR (modelo `mistral-ocr-latest`)
  - Procesamiento inteligente de PDFs y DOCX
  - Preservación de estructura (headers, tablas, listas)
  - Conversión a Markdown normalizado
  - Generación de metadata estructurada
  - Soporte para documentos grandes (>1000 páginas)
  - Validación de completitud de contenido

#### 2. **Pipeline de Ingestión** (`src/ingestion/`)
- **`ingest_pipeline.py`**: Pipeline completo de ingesta (recomendado)
- **`test_recursive_character_chunking.py`**: Script legacy
- **Características**:
  - Chunking con RecursiveCharacterTextSplitter
  - Generación de embeddings con Ollama
  - Almacenamiento vectorial en Qdrant
  - Metadata normalizada completa
  - Archivado automático de markdowns procesados
  - Verificación de duplicados opcional

#### 3. **Metadata Management** (`src/metadata/`)
- **`metadata_builder.py`**: Construcción de metadata completa
- **`text_structure_extractor.py`**: Extracción de estructura jerárquica
- **Características**:
  - Metadata heredada del documento
  - Estructura jerárquica (nivel, capítulo, sección, artículo)
  - Propiedades de chunks (índice, tamaño, palabras)
  - Relaciones (chunks hermanos, documento padre)
  - Referencias y citas (full_reference, citation_format)
  - Metadata normativa (legal_weight, is_primary_source)

#### 4. **Embeddings y Vectorización** (`src/embeddings/`)
- **`embedding_qdrant.py`**: Controlador de embeddings con Qdrant
- **Características**:
  - Generación de embeddings con Ollama `nomic-embed-text`
  - Almacenamiento vectorial en Qdrant
  - Búsqueda de similitud semántica (Cosine)
  - Configuración: 768 dimensiones
  - Creación automática de colecciones
  - Manejo robusto de errores con retry

#### 5. **Sistema de Retrieval Híbrido** (`src/retrieval/`) - **FASE C**
- **`hybrid_search.py`**: Motor de búsqueda híbrida principal
- **`query_parser.py`**: Parser de consultas (normas, artículos, keywords)
- **`filter_builder.py`**: Construcción de filtros Qdrant inteligentes
- **`sparse_encoder.py`**: Codificación BM25 para búsqueda sparse
- **`metadata_reranker.py`**: Re-ranking con metadata (legal_weight, level, etc.)
- **`context_composer.py`**: Composición de contexto estructurado
- **Características**:
  - Pipeline completo: Parse → Filter → Dense → Sparse → Re-rank → Compose
  - Extracción de entidades (normas, artículos, capítulos, secciones)
  - Filtros inteligentes con variaciones de código
  - Búsqueda híbrida (dense + sparse)
  - Re-ranking con bonificaciones de metadata
  - Composición de contexto optimizada para LLM

#### 6. **Modelos de Lenguaje** (`src/llm/`)
- **`mistral_llm.py`**: Integración con Mistral AI
- **Características**:
  - Integración con Mistral AI (`mistral-small-latest`)
  - Prompts centralizados y configurables
  - Respuestas siempre en español
  - Sistema de prompts por tipo de pregunta
  - Optimización para contexto RAG

#### 7. **Interfaz de Usuario** (`src/ui/`)
- **`app.py`**: Aplicación Chainlit principal
- **Características**:
  - Frontend web con Chainlit
  - Clasificación automática de tipos de pregunta
  - Sistema de traducción integrado
  - Formateo adaptativo de respuestas
  - Visualización de fuentes con relevancia
  - Manejo de errores y sugerencias

#### 8. **Traducción** (`src/translation/`)
- **`translate_retrieval.py`**: Traducción en tiempo real para Q&A
- **`translate_pipeline.py`**: Pipeline de traducción por lotes
- **`translate_document.py`**: Clase principal de traducción
- **`translate_documents_batch.py`**: Script de traducción masiva
- **Características**:
  - Traducción ES↔EN en tiempo real
  - Traducción por lotes optimizada
  - Modo reanudación automática
  - Optimización para documentos técnicos/legales

#### 9. **Utilidades** (`src/utils/`)
- **`excel_parser_base_conocimiento.py`**: Parser de Excel de base de conocimiento
- **`excel_parser_catalogo_metadata.py`**: Parser de catálogo de metadata
- **Características**:
  - Generación de metadata desde Excel
  - Detección y manejo de duplicados
  - Validación de estructura de datos
  - Exportación a JSON normalizado

#### 10. **Conversión** (`src/conversion/`)
- **`docx_to_pdf.py`**: Conversión de DOC/DOCX a PDF
- **Características**:
  - Conversión automática con LibreOffice
  - Backup de archivos originales
  - Preparación para pipeline de extracción

#### 11. **Evaluación** (`src/evaluation/`)
- **`evaluate_ragas.py`**: Evaluación con métricas RAGAS
- **`run_evaluation.py`**: Script de ejecución de evaluación
- **`api_rag.py`**: API para evaluación
- **Características**:
  - Métricas RAGAS (context recall, answer relevancy, faithfulness)
  - Reportes comparativos
  - Datasets de evaluación
  - Análisis de calidad

#### 12. **Core** (`src/core/`)
- **`logger.py`**: Sistema de logging centralizado
- **`exceptions.py`**: Excepciones personalizadas
- **`retry.py`**: Lógica de retry con exponential backoff
- **Características**:
  - Logging estructurado con niveles
  - Excepciones categorizadas
  - Retry logic con circuit breakers
  - Configuración centralizada

#### 13. **Configuración** (`config/`)
- **`settings.py`**: Configuración centralizada con Pydantic
- **`retrieval_config.py`**: Configuración del sistema de retrieval
- **`prompt_config.py`**: Prompts del sistema por idioma
- **`display_config.py`**: Configuración de visualización UI
- **Características**:
  - Validación automática de configuración
  - Type safety con Pydantic
  - Valores por defecto documentados
  - Configuración modular por componente

---

## 📦 Requisitos del Sistema

### Dependencias del Sistema
- **Python 3.12+** - Lenguaje principal
- **uv** - Gestor de paquetes Python moderno
- **Node.js** - Runtime para herramientas de desarrollo
- **npm/npx** - Gestor de paquetes Node.js
- **Docker** - Contenedores para servicios
- **Docker Compose** - Orquestación de contenedores
- **LibreOffice** - Para conversión DOC/DOCX → PDF
- **Memoria RAM**: 8GB+ recomendado

### Versiones de Dependencias
- **Chainlit**: <2.6.0 (versión estable)
- **Python**: 3.12+
- **Qdrant**: latest
- **Ollama**: latest
- **Mistral AI**: API v1

### Variables de Entorno Requeridas
```bash
# Mistral AI (REQUERIDO)
MISTRAL_API_KEY=your_mistral_api_key

# Qdrant (OPCIONAL - tiene defaults)
QDRANT_COLLECTION_NAME=normativa-asistente-kb
QDRANT_URL=http://localhost:6333

# Configuración de PDFs (OPCIONAL)
PDF_FOLDER_PATH=../data/test

# Base de Datos (OPCIONAL - para Chainlit data layer)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# AWS LocalStack (OPCIONAL - para Chainlit data layer)
BUCKET_NAME=my-bucket
APP_AWS_ACCESS_KEY=random-key
APP_AWS_SECRET_KEY=random-key
APP_AWS_REGION=eu-central-1
DEV_AWS_ENDPOINT=http://localhost:4566

# Logging (OPCIONAL)
LOG_LEVEL=INFO
LOG_JSON=false
LOG_DIR=logs/
```

---

## 🚀 Instalación y Configuración

### 1. Clonar el Repositorio
```bash
git clone <repository-url>
cd ai-genai-rag-asistente-normativa-sincro
```

### 2. Instalar Dependencias
```bash
# Instalar dependencias Python con uv
uv sync

# Activar entorno virtual
source .venv/bin/activate
```

### 3. Configurar Variables de Entorno
```bash
# Copiar template de .env (si existe)
cp .env.example .env

# Editar .env con tus valores
nano .env
```

### 4. Instalar Modelo de Embeddings
```bash
# Asegurar que Ollama esté corriendo
./rag_system.sh start ollama

# Verificar que el modelo esté disponible
curl http://localhost:11434/api/tags | grep nomic-embed-text
```

### 5. Iniciar Servicios
```bash
# Iniciar todos los servicios
./rag_system.sh start

# O iniciar servicios individuales
./rag_system.sh start qdrant
./rag_system.sh start ollama
./rag_system.sh start postgresql
./rag_system.sh start localstack
```

---

## 📖 Uso del Sistema

### Gestión de Servicios

El sistema incluye un script unificado `rag_system.sh` para gestionar todos los servicios:

```bash
# Comandos principales
./rag_system.sh start          # Iniciar TODO el sistema
./rag_system.sh stop           # Detener TODO el sistema
./rag_system.sh restart        # Reiniciar TODO el sistema
./rag_system.sh status         # Ver estado de TODO el sistema
./rag_system.sh check          # Verificación completa del sistema
./rag_system.sh monitor        # Monitoreo continuo (30 segundos)
./rag_system.sh emergency      # Reinicio de emergencia

# Servicios individuales
./rag_system.sh start qdrant     # Solo Qdrant
./rag_system.sh start ollama     # Solo Ollama
./rag_system.sh start rag        # Solo RAG Service
./rag_system.sh start datalayer  # Solo Datalayer Service

# Ver logs
./rag_system.sh logs rag       # Logs del RAG
./rag_system.sh logs datalayer # Logs del Datalayer
```

### Pipeline de Ingestión de Documentos

El pipeline completo consta de 5 pasos:

#### Paso 1: Preparar Metadata
```bash
python src/utils/excel_parser_base_conocimiento.py
```
- **Entrada**: `data/base-conocimiento.xlsx`
- **Salida**: `output/metadata/source/{pestaña}/{document_id}_source.json`
- **Características**: Detección y manejo de duplicados

#### Paso 2: Convertir/Preparar PDFs
```bash
python src/conversion/docx_to_pdf.py
```
- **Entrada**: `data/input/*.{pdf,doc,docx}`
- **Salida**: `output/datasources/{pestaña}/{document_id}_source.pdf`
- **Backup**: `data/processed/{timestamp}/` (formato original)

#### Paso 3: Generar Markdown
```bash
python src/extraction/generate_markdown.py
```
- **Entrada**: PDFs de `output/datasources/` y metadata de `output/metadata/source/`
- **Salida**: 
  - `output/markdown/processed_es/{pestaña}/{document_id}.md` (español)
  - `output/markdown/processed_en/{pestaña}/{document_id}.md` (inglés)
  - `output/metadata/extraction/{pestaña}/{document_id}_extraction.json`
- **Características**: 
  - Soporte para PDFs grandes (>1000 páginas)
  - Detección automática de idioma
  - Eliminación automática de PDFs procesados exitosamente

#### Paso 4: Traducir (si aplica)
```bash
python src/translation/translate_pipeline.py
```
- **Entrada**: `output/markdown/processed_es/{pestaña}/`
- **Salida**: 
  - `output/markdown/processed_en/{pestaña}/{document_id}.md`
  - `output/metadata/translation/{pestaña}/{document_id}_translated.json`
- **Características**: Modo reanudación automática

#### Paso 5: Ingestar a Qdrant
```bash
# Modo interactivo
python src/ingestion/ingest_pipeline.py

# Opción 1: Agregar sin verificar duplicados
python src/ingestion/ingest_pipeline.py --option 1

# Opción 2: Verificar duplicados (recomendado)
python src/ingestion/ingest_pipeline.py --option 2
```
- **Entrada**: Markdowns de `output/markdown/processed_en/` y metadata completa
- **Salida**:
  - Qdrant collection: `normativa-asistente-kb` (definida en `.env`)
  - `output/chunking/{pestaña}/{document_id}_recursive_character_chunks.json`
  - `output/metadata/chunking/{pestaña}/{document_id}_chunking.json`
  - `output/metadata/final/{pestaña}/{document_id}_final.json`
  - `output/embeddings_preview/{pestaña}/{document_id}_recursive_character_embeddings_preview.json`
  - `output/markdown/archived/{pestaña}_ES/` y `{pestaña}_EN/` (archivados automáticamente)

**Documentación Completa**: Ver `docs/PIPELINE_INGESTA.md`

### Interfaz Web

```bash
# Iniciar interfaz web Chainlit
chainlit run src/ui/app.py --host 0.0.0.0 --port 8000
```

Acceder a: `http://localhost:8000/` (o `http://161.132.45.154:8000/` en producción)

### Evaluación RAG

```bash
cd src/evaluation/
python evaluate_ragas.py
```

---

## 🔧 Configuración Avanzada

### Sistema de Retrieval Híbrido

El sistema de retrieval está completamente configurado en `config/retrieval_config.py`:

- **Búsqueda Densa**: Pesos configurables (dense_weight, sparse_weight)
- **Filtros**: Pre-filtrado inteligente por código normativo
- **Re-ranking**: Bonificaciones por legal_weight, is_primary_source, nivel jerárquico
- **Thresholds**: Configurables para filtrado de relevancia
- **Top-K Dinámico**: Basado en tipo de pregunta

### Configuración de Chunking

- **Método**: RecursiveCharacterTextSplitter (por defecto)
- **Chunk Size**: 1000 caracteres (configurable)
- **Chunk Overlap**: 200 caracteres (configurable)
- **Separadores**: `["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]`

### Configuración de Embeddings

- **Modelo**: `nomic-embed-text` (Ollama local)
- **Dimensiones**: 768
- **Distancia**: Cosine similarity
- **Batch Size**: 10 documentos por lote

### Configuración de Qdrant

- **Vector Size**: 768 dimensiones
- **Distance**: Cosine
- **Storage**: On-disk payload
- **Auto-creation**: Colecciones creadas automáticamente

---

## 📁 Estructura del Proyecto

```
ai-genai-rag-asistente-normativa-sincro/
├── src/                              # Código fuente
│   ├── core/                         # Módulos core compartidos
│   │   ├── logger.py                # Sistema de logging
│   │   ├── exceptions.py            # Excepciones personalizadas
│   │   └── retry.py                 # Retry logic
│   ├── extraction/                   # Extracción de documentos
│   │   ├── generate_markdown.py     # Script principal
│   │   └── markdown_extraction.py  # Controlador Mistral OCR
│   ├── ingestion/                     # Ingesta a Qdrant
│   │   ├── ingest_pipeline.py       # Pipeline completo (recomendado)
│   │   └── test_recursive_character_chunking.py  # Legacy
│   ├── embeddings/                   # Vectorización
│   │   └── embedding_qdrant.py     # Controlador Qdrant
│   ├── retrieval/                    # Sistema de búsqueda híbrida (FASE C)
│   │   ├── hybrid_search.py         # Motor principal
│   │   ├── query_parser.py          # Parser de consultas
│   │   ├── filter_builder.py        # Construcción de filtros
│   │   ├── sparse_encoder.py        # Codificación BM25
│   │   ├── metadata_reranker.py     # Re-ranking con metadata
│   │   └── context_composer.py       # Composición de contexto
│   ├── llm/                          # Modelos de lenguaje
│   │   └── mistral_llm.py           # Integración Mistral AI
│   ├── translation/                  # Traducción automática
│   │   ├── translate_retrieval.py  # Traducción Q&A tiempo real
│   │   ├── translate_pipeline.py   # Pipeline de traducción
│   │   ├── translate_document.py   # Clase principal
│   │   └── translate_documents_batch.py  # Traducción masiva
│   ├── ui/                           # Interfaz de usuario
│   │   └── app.py                   # Aplicación Chainlit
│   ├── metadata/                     # Gestión de metadata
│   │   ├── metadata_builder.py      # Construcción de metadata
│   │   └── text_structure_extractor.py  # Extracción de estructura
│   ├── utils/                        # Utilidades
│   │   ├── excel_parser_base_conocimiento.py  # Parser Excel base conocimiento
│   │   └── excel_parser_catalogo_metadata.py  # Parser catálogo metadata
│   ├── conversion/                   # Conversión de documentos
│   │   └── docx_to_pdf.py           # DOC/DOCX → PDF
│   └── evaluation/                   # Evaluación RAG
│       ├── evaluate_ragas.py         # Métricas RAGAS
│       ├── run_evaluation.py        # Script de evaluación
│       └── api_rag.py               # API para evaluación
├── config/                           # Configuración
│   ├── settings.py                  # Configuración centralizada (Pydantic)
│   ├── retrieval_config.py         # Configuración retrieval híbrido
│   ├── prompt_config.py            # Prompts del sistema
│   └── display_config.py           # Configuración UI
├── docs/                            # Documentación
│   ├── PIPELINE_INGESTA.md         # Documentación pipeline completo
│   ├── MEJORAS_IMPLEMENTADAS.md    # Mejoras implementadas
│   ├── ESTADO_MEJORAS.md           # Estado de aplicación de mejoras
│   ├── ANALISIS_MEJORAS.md         # Análisis de mejoras pendientes
│   └── FIREWALL_PERSISTENTE.md     # Documentación firewall
├── output/                          # Datos generados
│   ├── metadata/                     # Metadata por etapa
│   │   ├── source/                 # Metadata de source
│   │   ├── extraction/             # Metadata de extracción
│   │   ├── translation/            # Metadata de traducción
│   │   ├── chunking/               # Metadata intermedia
│   │   └── final/                  # Metadata final
│   ├── chunking/                    # Chunks generados
│   ├── embeddings_preview/          # Preview de embeddings
│   ├── markdown/                    # Markdowns procesados
│   │   ├── processed_es/           # Español (temporal)
│   │   ├── processed_en/            # Inglés (temporal)
│   │   └── archived/               # Archivados (permanente)
│   └── datasources/                 # PDFs temporales
├── data/                            # Datos de entrada
│   ├── input/                      # Archivos originales
│   ├── processed/                  # Backups con timestamp
│   ├── base-conocimiento.xlsx     # Fuente de verdad
│   └── metadata/                   # Catálogos de metadata
├── scripts/                         # Scripts utilitarios
├── rag_system.sh                   # Script maestro de gestión
├── .env                            # Variables de entorno
├── pyproject.toml                  # Configuración del proyecto
└── README.md                       # Este archivo
```

---

## 🔐 Seguridad y Firewall

El sistema incluye un firewall persistente configurado automáticamente:

- **IPs Permitidas**: Configuradas en `rag_system.sh`
- **Puerto 8000**: Solo accesible desde IPs autorizadas
- **Persistencia**: Reglas se restauran automáticamente al reiniciar
- **Integración**: Se configura automáticamente al iniciar servicios

**Documentación Completa**: Ver `docs/FIREWALL_PERSISTENTE.md`

---

## 📊 Puertos y Servicios

| Servicio | URL | Puerto | Descripción |
|----------|-----|--------|-------------|
| **Chainlit RAG** | http://localhost:8000/ | 8000 | Interfaz principal del asistente |
| **Qdrant Dashboard** | http://localhost:6333/dashboard | 6333 | Base de datos vectorial |
| **Prisma Studio** | http://localhost:5555/ | 5555 | Gestión de base de datos PostgreSQL |
| **PostgreSQL** | localhost:5432 | 5432 | Base de datos principal |
| **Ollama** | http://localhost:11434/ | 11434 | Servicio de embeddings locales |
| **LocalStack** | http://localhost:4566/ | 4566 | Emulación de servicios AWS |

---

## 🧪 Testing y Validación

### Script de Prueba de Consultas
```bash
# Probar consulta sin conectar a Qdrant
python test_query.py "tu pregunta aquí"

# Probar consulta completa (con Qdrant)
python test_query.py --full "tu pregunta aquí"
```

### Validación de Ingestión
```bash
# Verificar estado de ingestión
python scripts/validate_ingestion_status.py
```

### Evaluación RAGAS
```bash
cd src/evaluation/
python evaluate_ragas.py
```

---

## 🐛 Solución de Problemas

### Errores Comunes

1. **Error de conexión a Qdrant**
   ```bash
   # Verificar que Qdrant esté corriendo
   ./rag_system.sh start qdrant
   curl http://localhost:6333/collections
   ```

2. **Error de API Mistral**
   - Verificar `MISTRAL_API_KEY` en `.env`
   - Verificar que la clave sea válida

3. **Error de Ollama**
   ```bash
   # Verificar que Ollama esté corriendo
   ./rag_system.sh start ollama
   curl http://localhost:11434/api/tags
   ```

4. **Error de memoria**
   - Aumentar RAM disponible
   - Reducir batch_size en configuración

5. **Error de puertos ocupados**
   ```bash
   # Verificar puertos
   lsof -ti:8000 | xargs kill -9
   lsof -ti:6333 | xargs kill -9
   ```

### Logs y Debugging

- **Logs del sistema**: Ver con `./rag_system.sh logs rag`
- **Logs de servicios**: Verificar con `docker logs <container_name>`
- **Debug mode**: Configurar `DEBUG_MODE=true` en `.env`

---

## 📚 Documentación Adicional

- **Pipeline de Ingestión**: `docs/PIPELINE_INGESTA.md`
- **Mejoras Implementadas**: `docs/MEJORAS_IMPLEMENTADAS.md`
- **Estado de Mejoras**: `docs/ESTADO_MEJORAS.md`
- **Análisis de Mejoras**: `docs/ANALISIS_MEJORAS.md`
- **Firewall**: `docs/FIREWALL_PERSISTENTE.md`
- **Guía de Desarrollo**: `CLAUDE.md`
- **Gestión de Servicios**: `SERVICIOS.md`

---

## 🎯 Roadmap y Próximas Mejoras

### Implementado ✅
- ✅ Sistema de logging centralizado
- ✅ Configuración centralizada con Pydantic
- ✅ Manejo de errores con excepciones personalizadas
- ✅ Retry logic con exponential backoff
- ✅ Sistema de búsqueda híbrida completo
- ✅ Pipeline de ingesta modular
- ✅ Firewall persistente
- ✅ Gestión unificada de servicios

### Pendiente 🔄
- ⏳ Integración completa de mejoras en módulos principales
- ⏳ Cache de embeddings
- ⏳ Tests unitarios y de integración
- ⏳ Métricas y analytics
- ⏳ Async/await para operaciones I/O
- ⏳ Validación de entrada de usuario
- ⏳ Rate limiting

Ver `docs/ANALISIS_MEJORAS.md` y `docs/ESTADO_MEJORAS.md` para detalles completos.

---

## 👥 Contribución

1. Fork el proyecto
2. Crear una rama feature (`git checkout -b feature/AmazingFeature`)
3. Commit los cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

---

## 📧 Contacto

- **Desarrollador**: Laren Osorio Toribio
- **Email**: losorio@rcp.pe
- **Organización**: RCP

---

## 📝 Changelog

### v0.2.1 (2025-01-05)
- ✅ Sistema de búsqueda híbrida completo (FASE C)
- ✅ Pipeline de ingesta modular y robusto
- ✅ Sistema de metadata completo con jerarquía normativa
- ✅ Firewall persistente y gestión unificada de servicios
- ✅ Corrección de bugs en retrieval (threshold, code matching)
- ✅ Documentación completa del pipeline
- ✅ Script de prueba de consultas

### v0.2.0
- ✅ Nueva colección Qdrant: `normativa-asistente-kb`
- ✅ Sistema de validación de ingestión
- ✅ Organización de salidas en `output/`
- ✅ Mejoras en ingestión con Mistral OCR
- ✅ Configuración centralizada
- ✅ Análisis de documentos

### v0.1.0
- ✅ Migración completa de Pinecone a Qdrant
- ✅ Migración de Groq a Mistral AI
- ✅ Implementación de flujo inglés KB + español Q&A
- ✅ Interfaz web con Chainlit
- ✅ Sistema de evaluación RAG
- ✅ Procesamiento OCR con Mistral
- ✅ Chunking contextualizado inteligente

---

**Última Actualización**: 2025-01-05
