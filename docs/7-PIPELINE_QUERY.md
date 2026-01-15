# Pipeline de Retrieval e Ingesta - Flujo Completo

## 📋 Descripción General

Este documento describe el **flujo completo** desde que el usuario realiza una consulta hasta que recibe una respuesta y puede proporcionar feedback. Este proceso ocurre **después** de que los datos ya han sido ingestados en Qdrant (ver `PIPELINE_INGESTA.md` para el proceso de ingesta).

**Pipeline**: Retrieval → Generación → Respuesta → Feedback  
**Aplicación Principal**: `src/ui/app.py` (Chainlit)  
**Puerto**: 8000  
**Base de Datos**: Qdrant (vectorial) + PostgreSQL (feedback)

---

## 🎯 Visión General del Flujo

```
Usuario (Consulta en Español)
    ↓
Chainlit UI (Puerto 8000)
    ↓
Clasificación de Tipo de Pregunta
    ↓
Detección de Idioma
    ↓
Traducción ES→EN (si necesario)
    ↓
Hybrid Search Engine
    ├─ Query Parser (extrae entidades)
    ├─ Filter Builder (filtros inteligentes)
    ├─ Dense Search (Qdrant - semántica)
    ├─ Sparse Search (BM25 - keywords)
    ├─ Metadata Re-ranking (bonos legales)
    └─ Context Composer (formato para LLM)
    ↓
LLM (Mistral) - Genera Respuesta
    ↓
Traducción EN→ES
    ↓
Chainlit UI - Muestra Respuesta
    ↓
Usuario - Feedback (Thumbs Up/Down + Comentario)
    ↓
PostgreSQL - Almacenamiento Automático
```

---

## 📝 Paso 1: Recepción de Consulta del Usuario

### 1.1 Interfaz Chainlit

**Archivo**: `src/ui/app.py`  
**Función**: `@cl.on_message` → `main(message: cl.Message)`

**Proceso**:
1. Usuario escribe consulta en la interfaz web (http://161.132.45.154:8000/)
2. Chainlit captura el mensaje automáticamente
3. Se ejecuta el handler `main(message)`

**Código**:
```python
@cl.on_message
async def main(message: cl.Message):
    # 1. Actualizar historial
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})
    
    # 2. Mostrar indicador de procesamiento
    await cl.Message(content="**Procesando tu consulta...**", author="Sistema").send()
    
    # 3. Ejecutar pipeline FASE C
    result = process_query_fase_c(message.content)
```

---

## 🔍 Paso 2: Procesamiento de la Consulta (FASE C)

### 2.1 Función Principal

**Archivo**: `src/ui/app.py`  
**Función**: `process_query_fase_c(user_question: str)`

**Pipeline Completo**:
1. Clasificación del tipo de pregunta
2. Detección de idioma
3. Traducción ES→EN (si necesario)
4. Hybrid Search (búsqueda híbrida)
5. Generación de respuesta (LLM)
6. Traducción EN→ES

### 2.2 Clasificación de Tipo de Pregunta

**Archivo**: `src/ui/app.py`  
**Función**: `classify_question_type(question: str)`

**Tipos de Preguntas**:
- **`factual`**: Preguntas de hecho directo (ej: "¿Cuál es el artículo 49?")
- **`interpretative`**: Preguntas de interpretación (ej: "¿Qué significa...?")
- **`comparative`**: Preguntas comparativas (ej: "¿Cuál es la diferencia entre...?")
- **`procedural`**: Preguntas sobre procedimientos (ej: "¿Cómo se debe...?")

**Impacto**:
- Determina `top_k` adaptativo (factual: 3, interpretative: 5, etc.)
- Ajusta el estilo de respuesta del LLM
- Afecta los filtros de relevancia

**Código**:
```python
question_type = classify_question_type(user_question)
# Resultado: "factual" | "interpretative" | "comparative" | "procedural"
```

### 2.3 Detección de Idioma

**Archivo**: `src/ui/app.py`  
**Función**: `detect_language(text: str)`

**Proceso**:
- Detecta si la consulta está en español o inglés
- Usa `langdetect` para detección automática
- Por defecto: español

**Código**:
```python
detected_language = detect_language(user_question)
# Resultado: "español" | "english"
```

### 2.4 Traducción ES→EN

**Archivo**: `src/translation/translate_retrieval.py`  
**Función**: `translate_text(text, source_lang, target_lang)`

**Proceso**:
- Si la consulta está en español, se traduce a inglés
- La búsqueda en Qdrant se realiza en inglés (KB está en inglés)
- Usa Mistral API para traducción

**Código**:
```python
if detected_language == "español":
    search_query_en = translate_text(user_question, source_lang="es", target_lang="en")
else:
    search_query_en = user_question
```

---

## 🔎 Paso 3: Hybrid Search Engine

### 3.1 Inicialización

**Archivo**: `src/retrieval/hybrid_search.py`  
**Clase**: `HybridSearchEngine`

**Componentes Inicializados**:
- `QueryParser`: Extrae entidades de la consulta
- `FilterBuilder`: Construye filtros para Qdrant
- `SparseEncoder`: Codificación BM25 para keywords
- `MetadataReranker`: Re-ranking con bonos de metadata
- `ContextComposer`: Formatea contexto para LLM

**Código**:
```python
hybrid_engine = get_hybrid_search_engine()
search_result = hybrid_engine.search(
    query=search_query_en,
    question_type=question_type
)
```

### 3.2 Paso 3.1: Query Parser

**Archivo**: `src/retrieval/query_parser.py`  
**Clase**: `QueryParser`

**Funcionalidad**:
Extrae entidades de la consulta usando expresiones regulares:

- **Normas**: Ley 29783, DS 001-2024, RM 123-2024, NFPA 37, ISO 9001, RNE A.130, etc.
- **Artículos**: Artículo 49, Art. 49
- **Capítulos**: Capítulo 5, Chapter 5
- **Secciones**: Sección 5.2, Section 5.2
- **Keywords**: Palabras clave relevantes (sin stopwords)

**Patrones Soportados**:
- Leyes peruanas: `Ley N° 29783`, `L. 29783`
- Decretos: `DS 001-2024-MINSA`, `DL 1499`
- Resoluciones: `RM 123-2024-MINSA`, `RD 456-2024`
- Normas técnicas: `NFPA 37`, `ISO 9001`, `FMDS 100`
- RNE: `A.130`, `E.060`, `IS.010`
- ASIS: `PROT-SEC-PHY-001`

**Salida**:
```python
{
    "norms": [{"type": "ley", "code": "29783", "full": "Ley 29783"}],
    "articles": ["49"],
    "chapters": [],
    "sections": [],
    "keywords": ["capacitacion", "empleador", "obligaciones"],
    "has_norm_reference": True,
    "has_article_reference": True
}
```

### 3.3 Paso 3.2: Filter Builder

**Archivo**: `src/retrieval/filter_builder.py`  
**Clase**: `FilterBuilder`

**Funcionalidad**:
Construye filtros inteligentes para Qdrant basados en las entidades extraídas.

**Características**:
- **Generación de variaciones de código**: 
  - `Ley 29783` → `["Ley 29783", "L. 29783", "Ley N° 29783", "LEY 29783"]`
- **Filtros OR (should)**: Más flexible, permite múltiples códigos
- **Mapeo de área temática**: `"seguridad"` → `"seguridad_salud_trabajo"`

**Filtros Construidos**:
- Por código de norma (con variaciones)
- Por artículo
- Por capítulo
- Por área temática (si se detecta en keywords)

**Ejemplo**:
```python
# Consulta: "¿Qué dice el artículo 49 de la Ley 29783?"
# Filtros generados:
Filter(
    should=[
        FieldCondition(key="code", match=MatchAny(any=["Ley 29783", "L. 29783", ...])),
        FieldCondition(key="article", match=MatchValue(value="49"))
    ]
)
```

### 3.4 Paso 3.3: Dense Search (Búsqueda Semántica)

**Archivo**: `src/embeddings/embedding_qdrant.py`  
**Clase**: `EmbeddingControllerQdrant`

**Proceso**:
1. **Generación de embedding**: La consulta en inglés se convierte en un vector de 768 dimensiones usando Ollama (`nomic-embed-text`)
2. **Búsqueda en Qdrant**: Se busca en la colección `normativa-asistente-kb` usando:
   - Embedding de la consulta
   - Filtros construidos (si existen)
   - `top_k` inicial: 20 chunks (configurable)

**Configuración**:
- **Modelo**: `nomic-embed-text` (768 dimensiones)
- **Distancia**: Cosine similarity
- **Top-K inicial**: 20 chunks (para re-ranking posterior)

**Código**:
```python
# Generar embedding
query_embedding = embedding_controller.generate_embeddings(search_query_en)

# Buscar en Qdrant
dense_chunks = embedding_controller.load_and_query_qdrant(
    query_embedding=query_embedding,
    top_k=20,  # initial_top_k
    query_filter=filters  # Filtros del FilterBuilder
)
```

**Resultado**:
Lista de chunks con:
- `score`: Score de similitud semántica (0.0 - 1.0)
- `payload`: Metadata completa del chunk
- `id`: ID del punto en Qdrant

### 3.5 Paso 3.4: Sparse Search (BM25)

**Archivo**: `src/retrieval/sparse_encoder.py`  
**Clase**: `SparseEncoder`

**Funcionalidad**:
Calcula scores BM25 para matching de keywords. Complementa la búsqueda semántica con matching exacto de términos.

**Proceso**:
1. Tokeniza la consulta (keywords extraídos)
2. Calcula frecuencia de términos (TF) en cada chunk
3. Calcula frecuencia inversa de documentos (IDF)
4. Aplica fórmula BM25: `score = TF * IDF`

**Parámetros BM25**:
- `k1`: 1.5 (saturación de frecuencia de términos)
- `b`: 0.75 (normalización de longitud)

**Boost para Matches Exactos**:
- Si un keyword aparece exactamente en el chunk: `score * 2.0`

**Código**:
```python
sparse_chunks = sparse_encoder.score_chunks(
    query_keywords=parsed_query["keywords"],
    chunks=dense_chunks
)
```

**Resultado**:
Cada chunk ahora tiene:
- `score`: Score semántico (dense)
- `sparse_score`: Score BM25 (sparse)

### 3.6 Paso 3.5: Metadata Re-ranking

**Archivo**: `src/retrieval/metadata_reranker.py`  
**Clase**: `MetadataReranker`

**Funcionalidad**:
Re-ordena los chunks aplicando bonos basados en metadata legal y jerárquica.

**Bonos Aplicados**:

1. **Legal Weight Bonus** (0.10):
   - Basado en `legal_weight` (jerarquía normativa)
   - Valores: 1000 (Constitución), 900 (Ley Orgánica), 800 (Ley Ordinaria), etc.
   - Normalizado: `bonus = (legal_weight / 1000) * 0.10`

2. **Primary Source Bonus** (0.10):
   - Si `is_primary_source == true`: `+0.10`

3. **Level Bonus** (0.05):
   - `level == 1` (Artículo): `+0.05`
   - `level == 2` (Capítulo): `+0.04`
   - `level == 3` (Sección): `+0.03`
   - `level == 4` (Subsección): `+0.02`
   - `level == 5` (General): `+0.01`

4. **Code Match Bonus** (0.05):
   - Si el código de la norma mencionada en la consulta coincide con el código del chunk: `+0.05`
   - Verifica variaciones de código también

**Fusión Híbrida**:
```python
final_score = (
    0.40 * dense_score +      # 40% búsqueda semántica
    0.30 * sparse_score +     # 30% matching de keywords
    0.30 * metadata_bonuses    # 30% bonos de metadata
)
```

**Boost Factors Adicionales**:
- **Jerarquía legal**: Multiplicador según nivel (Constitución: 1.50x, Ley: 1.40x, etc.)
- **Nivel de documento**: Artículo principal: 1.3x, Capítulo: 1.2x, etc.
- **Fuente primaria**: `is_primary_source == true`: 1.2x
- **Match exacto de código**: 1.5x

**Filtrado**:
- Chunks con `final_score < 0.40` se eliminan (configurable)

**Código**:
```python
reranked_chunks = metadata_reranker.rerank(
    chunks=sparse_chunks,
    parsed_query=parsed_query,
    question_type=question_type
)
```

**Resultado**:
Lista de chunks ordenados por `final_score` descendente, con:
- `final_score`: Score combinado (dense + sparse + metadata)
- `dense_score`: Score semántico original
- `sparse_score`: Score BM25
- `payload`: Metadata completa

### 3.7 Paso 3.6: Limitación a Top-K

**Proceso**:
Se limita el número de chunks según el tipo de pregunta:

- **Factual**: `top_k = 3`
- **Interpretative**: `top_k = 5`
- **Comparative**: `top_k = 6`
- **Procedural**: `top_k = 5`

**Código**:
```python
final_chunks = reranked_chunks[:final_top_k]
```

### 3.7 Paso 3.7: Context Composer

**Archivo**: `src/retrieval/context_composer.py`  
**Clase**: `ContextComposer`

**Funcionalidad**:
Formatea los chunks finales en un contexto estructurado para el LLM.

**Características**:
- **Agrupación por documento**: Chunks del mismo documento se agrupan
- **Citas estructuradas**: Incluye metadata (código, artículo, capítulo, etc.)
- **Deduplicación**: Elimina chunks con contenido muy similar (similarity > 0.95)
- **Control de longitud**: Máximo 8000 caracteres

**Formato de Cita**:
```
[Documento: Ley 29783:2011]
[Artículo: 49]
[Capítulo: 5]
[Sección: 5.2]
[Relevancia: 0.85]

[Contenido del chunk...]
```

**Código**:
```python
formatted_context = context_composer.compose(final_chunks)
```

**Resultado**:
String formateado con todos los chunks relevantes, listo para enviar al LLM.

---

## 🤖 Paso 4: Generación de Respuesta (LLM)

### 4.1 Mistral LLM

**Archivo**: `src/llm/mistral_llm.py`  
**Clase**: `MistralLLM`

**Proceso**:
1. **Preparación de prompts**:
   - **System Prompt**: Instrucciones del sistema según tipo de pregunta
   - **User Prompt**: Template con contexto y pregunta

2. **Llamada a API**:
   - Modelo: `mistral-small-latest`
   - Temperature: 0.3 (balance entre creatividad y precisión)
   - Idioma: Inglés (para consistencia con KB)

3. **Generación**:
   - El LLM genera respuesta en inglés basada en el contexto
   - Respuesta adaptada al tipo de pregunta (factual: concisa, interpretative: explicativa, etc.)

**Código**:
```python
llm.set_language("english")
response_en = llm.mistral_chat(
    context=context_en,
    question=search_query_en,
    response_language="english",
    question_type=question_type
)
```

**Prompts**:
- **System Prompt**: Define el rol del asistente y estilo de respuesta
- **User Prompt**: `"Context: {context}\n\nQuestion: {question}\n\nAnswer:"`

### 4.2 Traducción EN→ES

**Archivo**: `src/translation/translate_retrieval.py`  
**Función**: `translate_text(text, source_lang, target_lang)`

**Proceso**:
- La respuesta en inglés se traduce a español
- Usa Mistral API para traducción
- Optimizado para texto técnico/legal

**Código**:
```python
response_es = translate_text(response_en, source_lang="en", target_lang="es")
```

---

## 📺 Paso 5: Visualización de Respuesta

### 5.1 Formateo de Respuesta

**Archivo**: `src/ui/app.py`  
**Función**: `format_main_response(response, question_type)`

**Proceso**:
1. Formatea la respuesta con estilo adaptativo según tipo de pregunta
2. Agrega footer informativo (opcional)
3. Aplica formato Markdown

**Código**:
```python
formatted_response = format_main_response(
    result["response_es"],
    question_type=result["question_type"]
)
```

### 5.2 Envío de Mensaje Principal

**Código**:
```python
main_message = create_enhanced_message(
    content=formatted_response,
    author="Asistente"
)
await main_message.send()
```

### 5.3 Visualización de Fuentes

**Archivo**: `src/ui/app.py`  
**Función**: `format_sources_for_display(context_results)`

**Proceso**:
1. Extrae metadata de cada chunk usado
2. Formatea fuentes con:
   - Código de norma
   - Artículo/Capítulo/Sección (si aplica)
   - Score de relevancia
   - Título del documento

**Formato**:
```
**Fuentes:**

1. **Ley 29783:2011, Art. 49** (Relevancia: 0.85)
   - Capítulo 5, Sección 5.2
   - Título: Ley de Seguridad y Salud en el Trabajo

2. **NFPA 37:2024** (Relevancia: 0.78)
   - Sección 4.2
   - Título: Standard for the Installation and Use of Stationary Combustion Engines
```

**Código**:
```python
sources_content = format_sources_for_display(result["context_results"])
sources_message = create_enhanced_message(
    content=sources_content,
    author="Fuentes"
)
await sources_message.send()
```

### 5.4 Actualización de Historial

**Código**:
```python
history.append({"role": "assistant", "content": result["response_es"]})
cl.user_session.set("history", history)
```

### 5.5 Sugerencias de Seguimiento

**Archivo**: `src/ui/app.py`  
**Función**: `get_random_suggestion(question_type)`

**Proceso**:
- Genera sugerencias adaptativas según tipo de pregunta
- Ejemplos:
  - Factual: "¿Quieres saber más sobre este artículo?"
  - Interpretative: "¿Necesitas más contexto sobre este tema?"

**Código**:
```python
suggestion = get_random_suggestion(question_type=result["question_type"])
await cl.Message(
    content=f"**Sugerencia:** {suggestion}",
    author="Sistema"
).send()
```

### 5.6 Advertencia de Baja Relevancia

**Proceso**:
- Calcula relevancia promedio de los chunks
- Si la relevancia es baja (< 0.60) y hay pocos chunks, muestra advertencia

**Código**:
```python
avg_relevance = sum(scores) / len(scores) if scores else 0.0
if should_show_warning(chunks_after, avg_relevance):
    await cl.Message(
        content="⚠️ La relevancia de las fuentes es baja. Considera reformular tu consulta.",
        author="Sistema"
    ).send()
```

---

## 👍 Paso 6: Sistema de Feedback

### 6.1 Interfaz de Usuario

**Proceso**:
1. Usuario ve la respuesta del asistente
2. Usuario puede hacer clic en:
   - 👍 **Thumbs Up**: Respuesta útil
   - 👎 **Thumbs Down**: Respuesta no útil
3. Opcionalmente, usuario puede agregar un comentario explicativo

### 6.2 Almacenamiento Automático

**Proceso Automático de Chainlit**:
- Chainlit detecta automáticamente la variable `DATABASE_URL`
- Cuando el usuario da feedback, Chainlit guarda automáticamente en PostgreSQL

**Estructura de Feedback**:
```sql
Feedback {
    id: UUID (generado automáticamente)
    createdAt: DateTime (timestamp)
    updatedAt: DateTime (timestamp)
    stepId: String? (ID del paso asociado)
    name: "user_feedback"
    value: Float
        - 1.0 = Thumbs Up (👍)
        - 0.0 = Thumbs Down (👎)
    comment: String? (comentario opcional del usuario)
}
```

**Relación con Step**:
- Cada feedback está asociado a un `Step` (paso en la conversación)
- Un `Step` puede tener múltiples `Feedback`

### 6.3 Base de Datos

**Base de Datos**: PostgreSQL  
**Puerto**: 5432  
**Contenedor**: `chainlit-datalayer-postgres`  
**Schema**: Prisma (ver `/root/chainlit-datalayer/prisma/schema.prisma`)

**Tablas Relacionadas**:
- `Feedback`: Almacena el feedback del usuario
- `Step`: Representa cada paso en una conversación
- `Thread`: Representa una conversación completa
- `User`: Representa un usuario

### 6.4 Visualización (Prisma Studio)

**Interfaz**: Prisma Studio  
**Puerto**: 5555  
**URL**: http://161.132.45.154:5555/

**Funcionalidad**:
- Visualizar todos los feedback recibidos
- Filtrar por fecha, valor (thumbs up/down), comentarios
- Analizar tendencias de calidad
- Exportar datos para análisis

**Acceso**:
```bash
# Iniciar Prisma Studio
./rag_system.sh start datalayer

# O acceder directamente
# http://161.132.45.154:5555/
```

---

## 📊 Estadísticas y Métricas

### 7.1 Estadísticas del Pipeline

**Información Capturada**:
```python
{
    "question_type": "factual",
    "dense_retrieved": 20,      # Chunks recuperados de Qdrant
    "sparse_scored": 20,         # Chunks con score BM25
    "after_reranking": 15,       # Chunks después de re-ranking
    "final_chunks": 3,           # Chunks finales usados
    "chunks_before_filter": 20,  # Antes de filtrado
    "chunks_after_filter": 3,    # Después de filtrado
    "top_k_used": 3              # Top-K usado
}
```

### 7.2 Métricas de Calidad

**Relevancia Promedio**:
- Calculada sobre los chunks finales
- Rango: 0.0 - 1.0
- Advertencia si < 0.60

**Tiempo de Respuesta**:
- Tiempo total desde consulta hasta respuesta
- Incluye: traducción, búsqueda, generación, traducción

---

## 🔧 Configuración

### 8.1 Archivos de Configuración

**Retrieval Config**: `config/retrieval_config.py`
- Configuración de hybrid search
- Parámetros de query parser
- Configuración de re-ranking
- Configuración de context composer

**Display Config**: `config/display_config.py`
- Configuración de visualización
- Mensajes de error
- Formato de fuentes

**Prompt Config**: `config/prompt_config.py`
- Prompts del sistema
- Prompts del usuario
- Estilos de respuesta por tipo de pregunta

### 8.2 Variables de Entorno

```bash
# Mistral API
MISTRAL_API_KEY=your_key

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=normativa-asistente-kb

# PostgreSQL (Feedback)
DATABASE_URL=postgresql://root:root@localhost:5432/postgres

# Ollama
OLLAMA_URL=http://localhost:11434
```

---

## 🚀 Inicio del Sistema

### 9.1 Inicio Completo

```bash
# Iniciar todos los servicios
./rag_system.sh start

# Esto inicia:
# - Qdrant (puerto 6333)
# - Ollama (puerto 11434)
# - PostgreSQL (puerto 5432)
# - LocalStack (puerto 4566)
# - RAG Service (puerto 8000)
# - Datalayer Service (puerto 5555)
```

### 9.2 Verificación

```bash
# Verificar estado de todos los servicios
./rag_system.sh check

# Ver logs del RAG Service
./rag_system.sh logs rag

# Ver logs del Datalayer
./rag_system.sh logs datalayer
```

---

## 📝 Ejemplo Completo de Flujo

### Consulta del Usuario

```
Usuario: "¿Qué dice el artículo 49 de la Ley 29783 sobre las obligaciones del empleador?"
```

### Procesamiento

1. **Clasificación**: `question_type = "factual"`
2. **Detección**: `detected_language = "español"`
3. **Traducción**: `"What does article 49 of Law 29783 say about employer obligations?"`
4. **Query Parser**:
   ```python
   {
       "norms": [{"type": "ley", "code": "29783", "full": "Ley 29783"}],
       "articles": ["49"],
       "keywords": ["obligaciones", "empleador"]
   }
   ```
5. **Filter Builder**: Filtros por código "Ley 29783" y artículo "49"
6. **Dense Search**: 20 chunks recuperados de Qdrant
7. **Sparse Search**: Scores BM25 calculados
8. **Re-ranking**: Chunks ordenados por relevancia + bonos legales
9. **Top-K**: 3 chunks finales (factual)
10. **Context**: Contexto formateado con citas
11. **LLM**: Respuesta generada en inglés
12. **Traducción**: Respuesta traducida a español

### Respuesta Mostrada

```
**Respuesta del Asistente:**

Según el artículo 49 de la Ley 29783, el empleador tiene las siguientes obligaciones:

1. Proporcionar equipos de protección personal adecuados
2. Capacitar a los trabajadores en seguridad
3. Implementar medidas de prevención de riesgos
...

**Fuentes:**

1. **Ley 29783:2011, Art. 49** (Relevancia: 0.92)
   - Capítulo 5, Sección 5.2
   - Título: Ley de Seguridad y Salud en el Trabajo

2. **Ley 29783:2011, Art. 50** (Relevancia: 0.78)
   - Capítulo 5, Sección 5.2
   - Título: Ley de Seguridad y Salud en el Trabajo
```

### Feedback del Usuario

```
Usuario hace clic en: 👍 (Thumbs Up)
Comentario: "Muy útil, encontré exactamente lo que necesitaba"
```

### Almacenamiento

```sql
INSERT INTO "Feedback" (
    id, createdAt, updatedAt, stepId, name, value, comment
) VALUES (
    'uuid-generado',
    '2025-01-05 10:30:00',
    '2025-01-05 10:30:00',
    'step-id-asociado',
    'user_feedback',
    1.0,  -- Thumbs Up
    'Muy útil, encontré exactamente lo que necesitaba'
);
```

---

## ⚠️ Manejo de Errores

### 10.1 Errores Comunes

**Error: "No se encontraron chunks relevantes"**
- **Causa**: La consulta no coincide con ningún documento en Qdrant
- **Solución**: Reformular la consulta o verificar que los documentos estén ingestados

**Error: "Error al generar embedding"**
- **Causa**: Ollama no está corriendo o el modelo no está disponible
- **Solución**: `./rag_system.sh start ollama`

**Error: "Error al conectar con Qdrant"**
- **Causa**: Qdrant no está corriendo
- **Solución**: `./rag_system.sh start qdrant`

**Error: "Error al generar respuesta"**
- **Causa**: Mistral API no responde o API key inválida
- **Solución**: Verificar `MISTRAL_API_KEY` en `.env`

### 10.2 Mensajes de Error al Usuario

Todos los errores se muestran de forma amigable al usuario con sugerencias de seguimiento.

---

## 📚 Referencias

- **Pipeline de Ingesta**: `docs/PIPELINE_INGESTA.md`
- **Sistema de Feedback**: `docs/SISTEMA_FEEDBACK.md`
- **Puertos y Servicios**: `docs/PUERTOS_SERVICIOS.md`
- **RAG System Script**: `docs/RAG_SYSTEM_SH.md`
- **Configuración de Retrieval**: `config/retrieval_config.py`
- **Aplicación Principal**: `src/ui/app.py`

---

## 🔄 Flujo Visual Completo

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO (Consulta ES)                     │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              CHAINLIT UI (Puerto 8000)                      │
│  • Captura mensaje                                          │
│  • Actualiza historial                                      │
│  • Muestra "Procesando..."                                  │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│          PROCESAMIENTO (process_query_fase_c)               │
│  1. Clasificar tipo de pregunta                             │
│  2. Detectar idioma                                         │
│  3. Traducir ES→EN                                          │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│           HYBRID SEARCH ENGINE                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Query Parser: Extrae normas, artículos, keywords    │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Filter Builder: Construye filtros para Qdrant       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Dense Search: Búsqueda semántica (Qdrant)           │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Sparse Search: BM25 (keywords)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Metadata Re-ranking: Bonos legales                  │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Context Composer: Formatea contexto para LLM         │   │
│  └─────────────────────────────────────────────────────┘   │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM (Mistral)                                   │
│  • Genera respuesta en inglés                                │
│  • Basada en contexto + pregunta                            │
│  • Estilo adaptado al tipo de pregunta                      │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              TRADUCCIÓN EN→ES                                │
│  • Traduce respuesta a español                               │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              CHAINLIT UI (Visualización)                     │
│  • Muestra respuesta formateada                              │
│  • Muestra fuentes con relevancia                           │
│  • Muestra sugerencias de seguimiento                      │
│  • Advertencia si relevancia baja                           │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              USUARIO (Feedback)                             │
│  • Thumbs Up/Down                                            │
│  • Comentario opcional                                      │
└────────────────────────────┬──────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              POSTGRESQL (Almacenamiento)                    │
│  • Guarda feedback automáticamente                            │
│  • Asociado a Step (paso en conversación)                   │
│  • Disponible en Prisma Studio (puerto 5555)                 │
└─────────────────────────────────────────────────────────────┘
```

---

**Última Actualización:** 2025-01-05

