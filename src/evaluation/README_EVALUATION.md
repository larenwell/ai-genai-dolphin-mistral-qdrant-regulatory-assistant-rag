# Evaluación de Bases de Conocimiento con RAGAS

Este directorio contiene scripts para evaluar diferentes bases de conocimiento usando RAGAS (RAG Assessment).

## 🎯 Objetivo

Evaluar y comparar el rendimiento de diferentes métodos de chunking:
- **Contextual RAG** (original): `asistente-normativa-sincro-kb`
- **Semantic RAG p95**: `rag_semantic_construction`
- **Semantic RAG p75**: `rag_semantic_construction_p75`
- **Semantic RAG gradient**: `rag_semantic_construction_gradient`

## 📁 Estructura

```
src/evaluation/
├── api_rag.py                          # API RAG para evaluación
├── evaluate_ragas.py                   # Evaluador principal con RAGAS
├── run_evaluation.py                   # Script maestro (evaluar individual o todas)
├── generate_comparison_report.py       # Generador de reportes comparativos
├── data/
│   └── evaluation_dataset.jsonl        # Dataset de preguntas de evaluación
└── README_EVALUATION.md               # Este archivo
```

## 🚀 Uso

### Evaluar una Base de Conocimiento Específica

```bash
cd /root/ai-genai-rag-asistente-normativa-sincro

# Evaluar contextual RAG
uv run python src/evaluation/run_evaluation.py --collection asistente-normativa-sincro-kb --output-suffix contextual

# Evaluar semantic p95
uv run python src/evaluation/run_evaluation.py --collection rag_semantic_construction --output-suffix semantic_p95

# Evaluar semantic p75
uv run python src/evaluation/run_evaluation.py --collection rag_semantic_construction_p75 --output-suffix semantic_p75

# Evaluar semantic gradient
uv run python src/evaluation/run_evaluation.py --collection rag_semantic_construction_gradient --output-suffix semantic_gradient
```

### Evaluar Todas las Bases de Conocimiento

```bash
cd /root/ai-genai-rag-asistente-normativa-sincro
uv run python src/evaluation/run_evaluation.py --all
```

### Listar Bases de Conocimiento Disponibles

```bash
cd /root/ai-genai-rag-asistente-normativa-sincro
uv run python src/evaluation/run_evaluation.py --list
```

### Generar Reporte Comparativo

```bash
cd /root/ai-genai-rag-asistente-normativa-sincro
uv run python src/evaluation/generate_comparison_report.py
```

> **Nota**: Este script busca automáticamente todos los resultados de evaluación en `src/output/evaluation/` y genera un reporte comparativo consolidado.

**Cuándo usar:**
- Después de evaluar múltiples bases de conocimiento
- Para comparar el rendimiento entre diferentes métodos de chunking
- Para generar un reporte ejecutivo consolidado

## 📊 Métricas Evaluadas

- **Answer Relevancy**: Relevancia de la respuesta a la pregunta
- **Context Precision**: Precisión del contexto recuperado
- **Context Recall**: Recuperación del contexto relevante
- **Answer Correctness**: Correctitud de la respuesta

> **Nota**: La métrica `Faithfulness` está temporalmente deshabilitada debido a problemas de parsing con el formato de respuesta de Mistral.

## 📁 Resultados

Los resultados se guardan en `src/output/evaluation/`:

```
src/output/evaluation/
├── contextual/                          # Resultados contextual RAG
├── semantic_p95/                        # Resultados semantic p95
├── semantic_p75/                        # Resultados semantic p75
├── semantic_gradient/                   # Resultados semantic gradient
└── comparison/                          # Reportes comparativos
    └── comparison_report_YYYYMMDD_HHMMSS.txt
```

Cada carpeta contiene:
- `evaluation_results_YYYYMMDD_HHMMSS.csv`: Resultados detallados en CSV
- `evaluation_results_YYYYMMDD_HHMMSS.json`: Resultados en JSON
- `evaluation_report_YYYYMMDD_HHMMSS.txt`: Reporte detallado

La carpeta `comparison/` contiene:
- `comparison_report_YYYYMMDD_HHMMSS.txt`: Reporte comparativo consolidado

## 🔧 Requisitos

- Python 3.12+
- uv (gestor de paquetes)
- Ollama ejecutándose en puerto 11434
- Qdrant ejecutándose en puerto 6333
- Variables de entorno configuradas (MISTRAL_API_KEY, etc.)

## 📋 Proceso de Evaluación

1. **Configuración**: Se configura la API RAG para usar la colección específica
2. **Inicio API**: Se inicia la API RAG en puerto 8001
3. **Verificación KB**: Se verifica que la base de conocimiento correcta esté en uso
4. **Carga Dataset**: Se carga el dataset de 64 preguntas de evaluación
5. **Evaluación**: Se evalúa cada pregunta usando RAGAS (con manejo robusto de errores)
6. **Cálculo Métricas**: Se calculan métricas por tipo de pregunta
7. **Exportación**: Se guardan resultados en CSV, JSON y TXT
8. **Limpieza**: Se detiene la API y se limpia el entorno

## ✅ Estado Actual del Sistema

### **Mejoras Implementadas**
- ✅ **Manejo robusto de errores**: Los errores de parsing de RAGAS no interrumpen la evaluación
- ✅ **Verificación de KB**: Confirmación visual de qué base de conocimiento se está usando
- ✅ **Código limpio**: Eliminación completa de referencias a métricas deshabilitadas
- ✅ **Cálculos corregidos**: Promedios y puntuaciones compuestas ajustadas correctamente
- ✅ **Timeouts optimizados**: Tiempo de espera aumentado para mayor estabilidad

### **Métricas Activas**
- **Answer Relevancy**: Relevancia de la respuesta a la pregunta
- **Context Precision**: Precisión del contexto recuperado  
- **Context Recall**: Recuperación del contexto relevante
- **Answer Correctness**: Correctitud de la respuesta

### **Métricas Deshabilitadas**
- **Faithfulness**: Temporalmente deshabilitada por problemas de parsing con Mistral

## 🎯 Interpretación de Resultados

### Puntuaciones
- **0.0 - 0.3**: Muy bajo
- **0.3 - 0.5**: Bajo
- **0.5 - 0.7**: Medio
- **0.7 - 0.9**: Alto
- **0.9 - 1.0**: Muy alto

### Recomendaciones
- **Answer Relevancy < 0.7**: Mejorar la relevancia de las respuestas
- **Context Precision < 0.7**: Mejorar la precisión del contexto recuperado
- **Context Recall < 0.7**: Mejorar la recuperación de contexto relevante
- **Answer Correctness < 0.7**: Mejorar la correctitud de las respuestas

## 🚨 Solución de Problemas

### API no disponible
```bash
# Verificar que Ollama esté ejecutándose
curl http://localhost:11434/api/tags

# Verificar que Qdrant esté ejecutándose
curl http://localhost:6333/collections
```

### Errores de parsing RAGAS
```
OutputParserException(Failed to parse StringIO from completion...)
```
**Solución**: Este error es normal y esperado. RAGAS a veces tiene problemas de parsing con las respuestas de Mistral. El sistema maneja estos errores automáticamente asignando scores por defecto (0.0) y continúa con la evaluación.

### Error de memoria
- Reducir el batch_size en los scripts
- Usar evaluaciones individuales en lugar de secuenciales

### Timeout en evaluaciones
- Aumentar el timeout en `wait_for_api()`
- Verificar la conectividad de red

### Error "unsupported operand type(s) for +: 'int' and 'NoneType'"
**Solución**: Este error ha sido resuelto en la versión actual. Si aparece, verificar que se esté usando la versión más reciente de los scripts.

### Errores de conexión durante evaluación
```
Connection failed. If the problem persists, please check your internet connection or VPN
```
**Solución**: 
1. Verificar que la API esté ejecutándose: `curl http://localhost:8001/health`
2. Si no está ejecutándose, reiniciar la evaluación
3. Verificar que no haya conflictos de puerto: `fuser -k 8001/tcp`

### Evaluación se detiene prematuramente
**Solución**: 
- El sistema tiene manejo robusto de errores que permite continuar la evaluación
- Los errores de parsing individuales no afectan el resultado final
- Verificar los logs para identificar problemas específicos

## 📞 Soporte

Para problemas o preguntas:
1. Revisar los logs de evaluación
2. Verificar que todas las dependencias estén instaladas
3. Comprobar que las bases de conocimiento existan en Qdrant
4. Verificar la configuración de variables de entorno

## 🔄 Actualizaciones

- **v1.0**: Evaluación básica con RAGAS
- **v1.1**: Soporte para múltiples bases de conocimiento
- **v1.2**: Reportes comparativos automáticos
- **v1.3**: Scripts de evaluación individual y secuencial
- **v1.4**: Eliminación de métrica Faithfulness por problemas de parsing
- **v1.5**: Mejoras en manejo de errores y estabilidad del sistema