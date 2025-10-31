# src/ui/app.py - FASE B: Explicit Translation Pipeline with Optimizations
import os, sys
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import chainlit as cl
from llm.mistral_llm import MistralLLM
from translation.translate import translate_text, get_translation_service
from embeddings.embedding_qdrant import EmbeddingControllerQdrant
from dotenv import load_dotenv


from config.display_config import (
    get_display_config, 
    get_emoji, 
    get_relevance_icon, 
    get_random_suggestion, 
    format_error_message,
    get_adaptive_footer,        # ✅ NUEVO
    should_show_warning,        # ✅ NUEVO
    get_question_type_badge     # ✅ NUEVO (opcional)
)

from config.prompt_config import LANGUAGE_CONFIG, get_kb_language

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

load_dotenv(project_root / '.env')

# Load display configuration
DISPLAY_CONFIG = get_display_config()

# Initialize translation service at startup
translation_service = get_translation_service()
print(f"🌐 Translation service ready")


# ============================================================================
# QUESTION TYPE CLASSIFICATION - NEW
# ============================================================================

def classify_question_type(question: str) -> str:
    """
    Clasifica el tipo de pregunta para ajustar nivel de detalle y top_k.
    
    Args:
        question: Pregunta del usuario
    
    Returns:
        question_type: "factual" | "interpretative" | "comparative" | "procedural"
    """
    question_lower = question.lower()
    
    # Indicadores de preguntas FACTUALES (respuesta corta, datos específicos)
    factual_indicators = [
        # Interrogativos específicos
        "cuál es", "cuánto", "cuántos", "cuándo", "dónde", "qué",
        # Medidas y especificaciones
        "medida", "medidas", "dimensión", "dimensiones", "tamaño",
        "especificación", "especificaciones", "valor", "valores",
        # Unidades
        "milímetros", "mm", "metros", "cm", "pulgadas", "inches",
        "días", "meses", "años", "horas",
        # Datos concretos
        "plazo", "fecha", "número", "cantidad", "porcentaje",
        "temperatura", "presión", "velocidad",
        # Referencias normativas
        "artículo número", "sección", "párrafo", "inciso",
        "numeral", "literal",
        # Definiciones cortas
        "nombre de", "título de", "definición de", "qué significa",
        "a qué se refiere"
    ]
    
    # Indicadores de preguntas INTERPRETATIVAS (respuesta extensa, análisis)
    interpretative_indicators = [
        # Análisis
        "cómo se aplica", "cómo se interpreta", "cómo funciona",
        "por qué", "explica", "describe", "detalla",
        # Propósito y objetivos
        "cuál es el propósito", "cuál es el objetivo",
        "cuál es la finalidad", "para qué sirve",
        # Razonamiento
        "interpreta", "analiza", "evalúa", "considera",
        "qué significa", "qué implica", "qué consecuencias",
        "qué efectos", "qué impacto",
        # Contexto
        "en qué contexto", "bajo qué circunstancias",
        "en qué casos", "cuándo aplica"
    ]
    
    # Indicadores COMPARATIVOS
    comparative_indicators = [
        "diferencia entre", "diferencias entre",
        "comparar", "comparación", "compara",
        "versus", "vs", "vs.",
        "en contraste con", "a diferencia de",
        "similar a", "parecido a",
        "mejor que", "peor que",
        "ventajas y desventajas"
    ]
    
    # Indicadores PROCEDURALES (pasos, procesos)
    procedural_indicators = [
        "cómo hacer", "cómo realizar", "cómo ejecutar",
        "pasos para", "proceso de", "proceso para",
        "procedimiento", "procedimiento para",
        "requisitos para", "cómo cumplir",
        "qué debo hacer", "qué pasos",
        "secuencia", "orden",
        "primero", "luego", "después", "finalmente"
    ]
    
    # Scoring por categoría
    factual_score = sum(1 for ind in factual_indicators if ind in question_lower)
    interpretative_score = sum(1 for ind in interpretative_indicators if ind in question_lower)
    comparative_score = sum(1 for ind in comparative_indicators if ind in question_lower)
    procedural_score = sum(1 for ind in procedural_indicators if ind in question_lower)
    
    # Decisión con prioridad
    if factual_score > 0:
        return "factual"
    elif comparative_score > 0:
        return "comparative"
    elif procedural_score > 0:
        return "procedural"
    elif interpretative_score > 0:
        return "interpretative"
    else:
        # Default: interpretativa (pregunta abierta o ambigua)
        return "interpretative"


def get_optimal_top_k(question_type: str) -> int:
    """
    Determina el número óptimo de chunks según tipo de pregunta.
    
    Args:
        question_type: Tipo de pregunta
    
    Returns:
        top_k: Número de chunks a recuperar
    """
    TOP_K_CONFIG = {
        "factual": 3,           # Datos específicos → Menos chunks, más precisión
        "comparative": 6,        # Comparaciones → Más chunks para cubrir ambos lados
        "procedural": 5,         # Procedimientos → Balance intermedio
        "interpretative": 5      # Explicaciones → Balance estándar
    }
    
    return TOP_K_CONFIG.get(question_type, 5)  # Default: 5


def filter_low_relevance_chunks(context_results, min_score: float = 0.65):
    """
    Filtra chunks con baja relevancia para evitar ruido en el contexto.
    
    Args:
        context_results: Lista de resultados de búsqueda
        min_score: Score mínimo de relevancia (0.0-1.0)
    
    Returns:
        Lista filtrada de chunks relevantes
    """
    if not context_results:
        return context_results
    
    filtered = [chunk for chunk in context_results if chunk.score >= min_score]
    
    print(f"📊 Relevance filtering: {len(context_results)} → {len(filtered)} chunks (threshold={min_score})")
    
    # Si no hay chunks que pasen el threshold, devolver al menos el top 1
    if not filtered and context_results:
        print(f"⚠️ No chunks above threshold, keeping top 1 (score: {context_results[0].score:.3f})")
        return context_results[:1]
    
    return filtered


def format_context_with_metadata(context_results) -> str:
    """
    Formatea contexto con metadata estructurada para ayudar al LLM a citar fuentes.
    
    AJUSTADO para metadata real de Qdrant:
    - document_id: ID único del documento
    - source_file: Nombre del archivo original
    - text: Contenido del chunk
    - NO incluye página (pendiente para FASE C)
    
    Args:
        context_results: Lista de resultados de búsqueda
    
    Returns:
        Contexto formateado con metadata
    """
    if not context_results:
        return ""
    
    formatted_chunks = []
    
    for i, match in enumerate(context_results, 1):
        metadata = match.payload
        
        # Extract metadata with available fields
        doc_id = metadata.get('document_id', 'Unknown')
        source_file = metadata.get('source_file', 'Unknown Document')
        text = metadata.get('text', '[No text available]')
        score = match.score
        
        # Crear nombre legible del documento
        # Prioridad: source_file limpio > document_id
        if source_file and source_file != 'Unknown Document':
            # Limpiar nombre del archivo (remover extensión y caracteres especiales)
            doc_name = source_file.replace('.pdf', '').replace('.docx', '')
            doc_name = doc_name.replace('_', ' ').strip()
        else:
            doc_name = doc_id.replace('_', ' ')
        
        # Intentar extraer header del texto (si tiene formato markdown)
        header = extract_header_from_text(text)
        header_info = f" - {header}" if header else ""
        
        # Formato estructurado que ayuda al LLM a citar
        formatted_chunk = f"""[Source {i}: {doc_name}{header_info}, Relevance: {score:.2f}]
{text}
"""
        formatted_chunks.append(formatted_chunk)
    
    return "\n\n---\n\n".join(formatted_chunks)


def extract_header_from_text(text: str) -> str:
    """
    Extrae el primer header encontrado en el texto (si tiene formato markdown).
    
    Args:
        text: Texto del chunk
    
    Returns:
        Header extraído o string vacío
    """
    import re
    
    # Buscar headers markdown en orden de prioridad (### > ## > #)
    patterns = [
        (r'^### (.+?)$', 3),  # H3
        (r'^## (.+?)$', 2),   # H2
        (r'^# (.+?)$', 1)     # H1
    ]
    
    for pattern, level in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            header_text = match.group(1).strip()
            # Limitar longitud del header
            if len(header_text) > 50:
                header_text = header_text[:47] + "..."
            return header_text
    
    return ""


def format_sources_for_display(context_results):
    """
    Format sources for display with metadata.
    
    AJUSTADO para metadata real de Qdrant:
    - Usa source_file como nombre del documento
    - Extrae headers del texto si existen
    - NO incluye página (pendiente para FASE C)
    
    Args:
        context_results: Lista de resultados de búsqueda
    
    Returns:
        Texto formateado con fuentes
    """
    if not context_results:
        return DISPLAY_CONFIG["error_messages"]["no_sources"]
    
    try:
        max_sources = DISPLAY_CONFIG["source_display"].get("max_sources_displayed", 5)
        matches = context_results[:max_sources]
        
        sources_text = DISPLAY_CONFIG["source_formatting"].get("header", "### 📚 **Fuentes consultadas**\n")
        
        for i, match in enumerate(matches, 1):
            metadata = match.payload
            
            # Extract metadata with available fields
            source_file = metadata.get('source_file', 'Sin título')
            text = metadata.get('text', '')
            
            # Limpiar nombre del archivo
            title = source_file.replace('.pdf', '').replace('.docx', '').replace('_', ' ').strip()
            
            # Intentar extraer header del texto
            header = extract_header_from_text(text)
            header_info = f" - {header}" if header else ""
            
            # Score de relevancia
            score = float(match.score)
            score_percentage = int(score * 100)
            relevance_icon = get_relevance_icon(score_percentage)
            
            # Formato sin página (pendiente FASE C)
            source_line = f"{i}. {relevance_icon} **`{title}`**{header_info} _(relevancia: {score_percentage}%)_\n"
            sources_text += source_line
        
        return sources_text
        
    except Exception as e:
        print(f"Error formatting sources: {e}")
        import traceback
        traceback.print_exc()
        return "### **Fuentes consultadas**\n\n*Error al formatear las fuentes.*"


def format_main_response(response_text, question_type: str = None):
    """Format the main response with proper structure and adaptive footer."""
    if not response_text:
        return DISPLAY_CONFIG["error_messages"].get("no_response", "**No se pudo generar una respuesta.**")
    
    try:
        formatted_response = ""
        
        if DISPLAY_CONFIG["response_formatting"].get("add_header", True):
            formatted_response += f"### **Respuesta**\n"
        
        formatted_response += response_text
        
        if DISPLAY_CONFIG["response_formatting"].get("add_footer", True):
            # NEW: Use adaptive footer based on question type
            footer_text = get_adaptive_footer(question_type)
            formatted_response += f"\n\n{footer_text}"
        
        return formatted_response
        
    except Exception as e:
        print(f"Error formatting response: {e}")
        return f"### **Respuesta**\n{response_text}"


def create_enhanced_message(content, author="Asistente", elements=None):
    """Create an enhanced message with visual elements."""
    message = cl.Message(content=content, author=author)
    
    if elements:
        for element in elements:
            message.elements.append(element)
    
    return message


# Initialize LLM and embedding controller
llm = MistralLLM(api_key=os.getenv("MISTRAL_API_KEY"))
embedding_admin = EmbeddingControllerQdrant()


def detect_language(text: str) -> str:
    """
    Detect language of input text (Spanish vs English).
    
    Args:
        text: Input text
    
    Returns:
        Detected language ("español" or "english")
    """
    spanish_indicators = ['á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡', 'qué', 'cómo', 'cuál', 'dónde']
    english_indicators = ['what', 'how', 'which', 'where', 'when', 'why', 'the', 'is', 'are']
    
    text_lower = text.lower()
    spanish_count = sum(1 for indicator in spanish_indicators if indicator in text_lower)
    english_count = sum(1 for indicator in english_indicators if indicator in text_lower)
    
    if spanish_count > english_count:
        return "español"
    elif english_count > spanish_count:
        return "english"
    else:
        return LANGUAGE_CONFIG["default"]

# ============================================================================
# FASE B PIPELINE - OPTIMIZED
# ============================================================================

def process_query_fase_b(user_question: str) -> dict:
    """
    FASE B: Explicit translation pipeline for English KB + Spanish Q&A.
    
    OPTIMIZATIONS:
    - Question type classification for adaptive top_k
    - Dynamic prompts based on question type
    - Relevance filtering to reduce noise
    - Metadata-aware context formatting
    
    Pipeline:
    1. Classify question type → Determine optimal top_k
    2. User question (ES) → Translate to EN
    3. Generate embedding (EN)
    4. Search KB (EN) with adaptive top_k
    5. Filter low-relevance chunks
    6. Format context with metadata
    7. LLM generate response (EN context + EN question → EN response) with type-specific prompt
    8. Translate response to ES
    9. Return to user (ES)
    
    Args:
        user_question: User's question in any language
    
    Returns:
        dict with:
            - original_question: Original user question
            - detected_language: Detected language of question
            - question_type: Classified question type
            - top_k_used: Number of chunks retrieved
            - search_query_en: English translation for KB search
            - context_en: Retrieved English context
            - chunks_before_filter: Number of chunks before filtering
            - chunks_after_filter: Number of chunks after filtering
            - response_en: LLM response in English
            - response_es: Final translated response in Spanish
            - context_results: Raw context results for source display
    """
    
    # Step 1: Classify question type
    question_type = classify_question_type(user_question)
    print(f"📝 Question type classified: {question_type}")
    
    # Step 2: Determine optimal top_k based on question type
    optimal_top_k = get_optimal_top_k(question_type)
    print(f"🎯 Optimal top_k for {question_type}: {optimal_top_k}")
    
    # Step 3: Detect language
    detected_language = detect_language(user_question)
    print(f"🌐 Detected language: {detected_language}")
    
    # Step 4: Translate question to English (for KB search)
    kb_language = get_kb_language()  # Should be "english" for FASE B
    
    if detected_language == "español":
        print(f"🔄 Step 1/8: Translating question ES→EN for KB search")
        search_query_en = translate_text(user_question, source_lang="es", target_lang="en")
        print(f"✅ Question translated: '{search_query_en[:100]}...'")
    else:
        print(f"ℹ️ Question already in English, using directly")
        search_query_en = user_question
    
    # Step 5: Generate embedding and search KB (in English) with adaptive top_k
    print(f"🔍 Step 2/8: Generating embedding and searching KB (top_k={optimal_top_k})")
    embed_question = embedding_admin.generate_embeddings(search_query_en)
    context_results_raw = embedding_admin.load_and_query_qdrant(embed_question, top_k=optimal_top_k)
    
    chunks_before_filter = len(context_results_raw)
    print(f"📄 Step 3/8: Retrieved {chunks_before_filter} chunks from KB")
    
    # Step 6: Filter low-relevance chunks
    print(f"🔍 Step 4/8: Filtering low-relevance chunks")
    context_results = filter_low_relevance_chunks(context_results_raw, min_score=0.65)
    
    chunks_after_filter = len(context_results)
    print(f"✅ Filtered to {chunks_after_filter} high-relevance chunks")
    
    # Step 7: Format context with metadata
    print(f"📝 Step 5/8: Formatting context with metadata")
    context_en = format_context_with_metadata(context_results)
    
    print(f"✅ Context formatted ({len(context_en)} chars)")
    
    # Step 8: LLM generates response in English with question-type-specific prompt
    print(f"🤖 Step 6/8: LLM generating {question_type} response in English")
    llm.set_language("english")  # Force English response
    response_en = llm.mistral_chat(
        context=context_en,
        question=search_query_en,
        response_language="english",
        question_type=question_type  # NEW: Adaptive prompt
    )
    
    print(f"✅ English response generated ({len(response_en)} chars)")
    
    # Step 9: Translate response to Spanish
    print(f"🔄 Step 7/8: Translating response EN→ES for user")
    response_es = translate_text(response_en, source_lang="en", target_lang="es")
    
    print(f"✅ Spanish response ready ({len(response_es)} chars)")
    print(f"✅ Step 8/8: Pipeline complete!")
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"📊 PIPELINE SUMMARY:")
    print(f"  Question type: {question_type}")
    print(f"  Top-K used: {optimal_top_k}")
    print(f"  Chunks retrieved: {chunks_before_filter}")
    print(f"  Chunks after filter: {chunks_after_filter}")
    print(f"  Context size: {len(context_en)} chars")
    print(f"  Response size: {len(response_es)} chars")
    print(f"{'='*60}\n")
    
    return {
        "original_question": user_question,
        "detected_language": detected_language,
        "question_type": question_type,
        "top_k_used": optimal_top_k,
        "search_query_en": search_query_en,
        "context_en": context_en,
        "chunks_before_filter": chunks_before_filter,
        "chunks_after_filter": chunks_after_filter,
        "response_en": response_en,
        "response_es": response_es,
        "context_results": context_results
    }

# ============================================================================
# CHAINLIT EVENT HANDLERS
# ============================================================================

# ============================================================================
# CHAINLIT EVENT HANDLERS - COMPLETE
# ============================================================================

@cl.on_chat_start
async def start():
    """Initialize the chat session with a welcome message."""
    cl.user_session.set("history", [])
    
    if DISPLAY_CONFIG["visual_elements"].get("welcome_message", True):
        welcome_msg = DISPLAY_CONFIG.get(
            "welcome_message", 
            "## 🚀 **¡Bienvenido al Asistente de Normativa!**\n\n¿En qué puedo ayudarte hoy?"
        )
        await cl.Message(content=welcome_msg, author="Asistente").send()


@cl.on_message
async def main(message: cl.Message):
    """
    Main message handler with FASE B explicit translation pipeline + optimizations.
    
    Flow:
    1. Update history
    2. Show processing indicator
    3. Execute FASE B pipeline (with question classification, adaptive top-k, filtering)
    4. Display response with adaptive formatting
    5. Display sources
    6. Show adaptive follow-up suggestions
    7. Show warnings if low relevance detected
    8. Handle errors gracefully
    """
    # =========================================================================
    # STEP 1: Update conversation history
    # =========================================================================
    history = cl.user_session.get("history")
    history.append({"role": "user", "content": message.content})
    
    # =========================================================================
    # STEP 2: Show processing indicator
    # =========================================================================
    if DISPLAY_CONFIG["visual_elements"].get("processing_indicator", True):
        processing_msg = DISPLAY_CONFIG["error_messages"].get(
            "processing", 
            "🔄 **Procesando tu consulta...**"
        )
        await cl.Message(content=processing_msg, author="Sistema").send()
    
    try:
        # =====================================================================
        # STEP 3: Execute FASE B optimized pipeline
        # =====================================================================
        print(f"\n{'='*60}")
        print(f"🚀 FASE B OPTIMIZED PIPELINE START")
        print(f"{'='*60}")
        
        result = process_query_fase_b(message.content)
        
        print(f"{'='*60}")
        print(f"✅ FASE B PIPELINE COMPLETE")
        print(f"{'='*60}\n")
        
        # =====================================================================
        # STEP 4: Display main response with adaptive formatting
        # =====================================================================
        
        # Format response with adaptive footer based on question type
        formatted_response = format_main_response(
            result["response_es"],
            question_type=result["question_type"]  # Pass question type for adaptive footer
        )
        
        # Add debug info if DEBUG_MODE is enabled
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            question_type_badge = get_question_type_badge(result["question_type"])
            debug_info = f"\n\n---\n{question_type_badge} | Chunks: {result['chunks_after_filter']}/{result['chunks_before_filter']} | Top-K: {result['top_k_used']}"
            formatted_response += debug_info
        
        # Send main response
        main_message = create_enhanced_message(
            content=formatted_response,
            author="Asistente"
        )
        await main_message.send()
        
        # =====================================================================
        # STEP 5: Display sources if configured
        # =====================================================================
        if DISPLAY_CONFIG["visual_elements"].get("source_attribution", True):
            sources_content = format_sources_for_display(result["context_results"])
            sources_message = create_enhanced_message(
                content=sources_content,
                author="Fuentes"
            )
            await sources_message.send()
        
        # =====================================================================
        # STEP 6: Update conversation history
        # =====================================================================
        history.append({"role": "assistant", "content": result["response_es"]})
        cl.user_session.set("history", history)
        
        # =====================================================================
        # STEP 7: Add adaptive follow-up suggestions
        # =====================================================================
        if DISPLAY_CONFIG["visual_elements"].get("follow_up_suggestions", True):
            try:
                # Get suggestion based on question type (adaptive)
                suggestion = get_random_suggestion(question_type=result["question_type"])
                await cl.Message(
                    content=f"💡 **Sugerencia:** {suggestion}",
                    author="Sistema"
                ).send()
            except Exception as e:
                print(f"⚠️ Error getting suggestion: {e}")
                # Continue without suggestion if there's an error
        
        # =====================================================================
        # STEP 8: Show low relevance warning if needed
        # =====================================================================
        if result["chunks_after_filter"] > 0:  # Only if we have chunks
            try:
                # Calculate average relevance
                avg_relevance = sum(c.score for c in result["context_results"]) / len(result["context_results"])
                
                # Check if warning should be shown
                if should_show_warning(result["chunks_after_filter"], avg_relevance):
                    warning_msg = DISPLAY_CONFIG["error_messages"].get("low_relevance", "⚠️ Relevancia baja detectada")
                    await cl.Message(
                        content=warning_msg,
                        author="Sistema"
                    ).send()
            except Exception as e:
                print(f"⚠️ Error checking relevance warning: {e}")
                # Continue without warning if there's an error
        
    except Exception as e:
        # =====================================================================
        # ERROR HANDLING
        # =====================================================================
        
        # Show user-friendly error message if configured
        if DISPLAY_CONFIG["visual_elements"].get("error_handling", True):
            error_message = format_error_message("processing_error", error=str(e))
            
            await cl.Message(
                content=error_message,
                author="Sistema"
            ).send()
        
        # Log detailed error for debugging
        print(f"❌ ERROR in main handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Optional: Send notification to admin/monitoring system
        # notify_admin_of_error(user_message=message.content, error=str(e))