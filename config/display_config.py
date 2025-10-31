"""
Display Configuration for Chainlit Frontend - FASE B Optimized

This module contains all the configuration parameters for the visual display
and formatting of responses in the Chainlit interface.

NEW in FASE B:
- Question type indicators
- Pipeline status badges
- Adaptive follow-up suggestions
- Enhanced metadata display
"""

# Message formatting settings
MESSAGE_FORMATTING = {
    "use_emojis": True,
    "use_markdown": True,
    "use_separators": True,
    "max_response_length": 2000,  # characters
    "truncate_long_responses": True
}

# Source display settings
SOURCE_DISPLAY = {
    "show_chunk_type": True,
    "show_page_number": True,
    "show_relevance_score": True,
    "use_relevance_icons": True,
    "max_sources_displayed": 5,
    "relevance_thresholds": {
        "high": 80,      # Green icon
        "medium": 60,    # Yellow icon
        "low": 0         # Red icon
    }
}

# Visual elements
VISUAL_ELEMENTS = {
    "welcome_message": True,
    "processing_indicator": True,
    "follow_up_suggestions": True,
    "error_handling": True,
    "source_attribution": True,
    "show_language_info": False,  # FASE B: Transparente para usuario (todo en ES)
    "show_question_type": False,   # NEW: Mostrar tipo de pregunta (debug mode)
    "show_pipeline_stats": False   # NEW: Mostrar estadísticas del pipeline (debug mode)
}

# Emojis and icons
EMOJIS = {
    "welcome": "🚀",
    "assistant": "🤖",
    "sources": "📚",
    "processing": "🔄",
    "error": "❌",
    "warning": "⚠️",
    "suggestion": "💡",
    "document": "📄",
    "page": "📖",
    "relevance": "🎯",
    "score": "⭐",
    # NEW: Question type emojis
    "factual": "🔢",
    "interpretative": "📖",
    "comparative": "⚖️",
    "procedural": "📋"
}

# Relevance score icons
RELEVANCE_ICONS = {
    "high": "🟢",
    "medium": "🟡", 
    "low": "🔴"
}

# NEW: Question type badges
QUESTION_TYPE_BADGES = {
    "factual": "🔢 **Dato Específico**",
    "interpretative": "📖 **Análisis Detallado**",
    "comparative": "⚖️ **Comparación**",
    "procedural": "📋 **Procedimiento**"
}

# Follow-up suggestions - IMPROVED: Adaptadas por tipo de pregunta
FOLLOW_UP_SUGGESTIONS = {
    "factual": [
        "¿Necesitas conocer otros datos relacionados?",
        "¿Te gustaría saber la fuente normativa de este dato?",
        "¿Hay alguna otra especificación técnica que te interese?",
        "¿Quieres verificar si hay actualizaciones recientes de este valor?"
    ],
    "interpretative": [
        "¿Te gustaría que profundice en algún aspecto específico?",
        "¿Necesitas ejemplos prácticos de aplicación?",
        "¿Hay algún caso particular que quieras analizar?",
        "¿Te gustaría que explique las excepciones a esta norma?"
    ],
    "comparative": [
        "¿Te gustaría una comparación más detallada?",
        "¿Necesitas saber las ventajas/desventajas de cada opción?",
        "¿Hay otros elementos que quieras comparar?",
        "¿Te interesa conocer casos de uso para cada alternativa?"
    ],
    "procedural": [
        "¿Necesitas aclaración sobre algún paso específico?",
        "¿Te gustaría saber los requisitos previos?",
        "¿Hay alguna parte del proceso que quieras profundizar?",
        "¿Necesitas información sobre plazos o responsables?"
    ],
    "general": [
        "¿Te gustaría que profundice en algún aspecto específico?",
        "¿Necesitas información adicional sobre este tema?",
        "¿Hay alguna otra normativa relacionada que te interese consultar?",
        "¿Te gustaría que busque información más específica sobre este punto?",
        "¿Hay algún estándar o código particular que te interese revisar?"
    ]
}

# Error messages
ERROR_MESSAGES = {
    "processing_error": """
### ❌ **Error en el procesamiento**

Lo sentimos, hubo un problema al procesar tu consulta:

**Error:** {error}

**Sugerencias:**
- Verifica que tu pregunta esté clara y específica
- Intenta reformular la consulta
- Si el problema persiste, contacta al administrador

**¿Te gustaría intentar con otra pregunta?**
""",
    
    "no_sources": "📚 **No se encontraron fuentes relevantes para tu consulta.**",
    "no_response": "🤖 **No se pudo generar una respuesta.**",
    "processing": "🔄 **Procesando tu consulta...**",
    
    # NEW: Translation errors
    "translation_error": """
### ⚠️ **Advertencia de Traducción**

Hubo un problema con la traducción automática, pero se generó una respuesta usando el contexto disponible.

La calidad de la respuesta puede verse afectada. Si la información no es clara, intenta reformular tu pregunta.
""",
    
    # NEW: Low relevance warning
    "low_relevance": """
### ⚠️ **Relevancia Baja**

Los documentos encontrados tienen baja relevancia para tu consulta. La respuesta puede no ser completamente precisa.

**Sugerencias:**
- Reformula tu pregunta con términos más específicos
- Verifica la ortografía y sintaxis
- Intenta usar terminología técnica del dominio
"""
}

# Welcome message
WELCOME_MESSAGE = """
## 🚀 **¡Bienvenido al Asistente de Normativa!**

Soy tu asistente especializado en normativas técnicas y documentos de ingeniería. Puedo ayudarte con:

- 🔢 **Datos específicos** - Medidas, plazos, especificaciones técnicas
- 📖 **Análisis detallado** - Interpretación de normativas y regulaciones
- ⚖️ **Comparaciones** - Diferencias entre estándares y procedimientos
- 📋 **Procedimientos** - Pasos y requisitos para cumplimiento normativo

**💡 Consejo:** Formula preguntas claras y específicas para obtener mejores resultados.

**¿En qué puedo ayudarte hoy?**
"""

# Response formatting
RESPONSE_FORMATTING = {
    "add_header": True,
    "add_footer": True,
    "footer_text": "*Esta respuesta se generó basándose en la información técnica disponible en los documentos.*",
    "use_separators": False,
    # NEW: Adaptive footer by question type
    "adaptive_footer": {
        "factual": "*Dato extraído de la documentación oficial.*",
        "interpretative": "*Interpretación basada en el análisis de la normativa vigente.*",
        "comparative": "*Comparación basada en las fuentes disponibles.*",
        "procedural": "*Procedimiento extraído de la documentación técnica.*"
    }
}

# Source formatting
SOURCE_FORMATTING = {
    "header": "### 📚 **Fuentes consultadas**\n",
    "use_separators": False,
    "source_template": {
        "title": "{number}. {relevance_icon} ",
        "document": "**`{title}`**",
        "page": " p.{page}",
        "header": " - {header}",
        "score": " _(relevancia: {score}%)_"
    },
    "separator": "\n"
}

# NEW: Pipeline status messages (for debug mode)
PIPELINE_STATUS = {
    "question_classified": "📝 Tipo de pregunta: {question_type}",
    "translation_start": "🔄 Traduciendo consulta...",
    "translation_complete": "✅ Traducción completada",
    "search_start": "🔍 Buscando en la base de conocimiento...",
    "search_complete": "✅ Encontrados {chunks} documentos relevantes",
    "filtering": "🔍 Filtrando resultados por relevancia...",
    "filtering_complete": "✅ {filtered} documentos de alta relevancia",
    "generating": "🤖 Generando respuesta...",
    "generating_complete": "✅ Respuesta generada"
}


def get_display_config():
    """Get the complete display configuration."""
    return {
        "message_formatting": MESSAGE_FORMATTING,
        "source_display": SOURCE_DISPLAY,
        "visual_elements": VISUAL_ELEMENTS,
        "emojis": EMOJIS,
        "relevance_icons": RELEVANCE_ICONS,
        "question_type_badges": QUESTION_TYPE_BADGES,
        "follow_up_suggestions": FOLLOW_UP_SUGGESTIONS,
        "error_messages": ERROR_MESSAGES,
        "welcome_message": WELCOME_MESSAGE,
        "response_formatting": RESPONSE_FORMATTING,
        "source_formatting": SOURCE_FORMATTING,
        "pipeline_status": PIPELINE_STATUS
    }


def get_emoji(key):
    """Get an emoji by key."""
    return EMOJIS.get(key, "")


def get_relevance_icon(score):
    """
    Get relevance icon based on score.
    
    Args:
        score: Relevance score (0-100)
    
    Returns:
        Icon string (emoji)
    """
    if score >= SOURCE_DISPLAY["relevance_thresholds"]["high"]:
        return RELEVANCE_ICONS["high"]
    elif score >= SOURCE_DISPLAY["relevance_thresholds"]["medium"]:
        return RELEVANCE_ICONS["medium"]
    else:
        return RELEVANCE_ICONS["low"]


def get_question_type_badge(question_type: str) -> str:
    """
    Get badge for question type.
    
    Args:
        question_type: Type of question
    
    Returns:
        Badge string with emoji and label
    """
    return QUESTION_TYPE_BADGES.get(question_type, "❓ **Consulta General**")


def get_random_suggestion(question_type: str = None):
    """
    Get a random follow-up suggestion adapted to question type.
    
    Args:
        question_type: Type of question (factual/interpretative/comparative/procedural)
    
    Returns:
        Random suggestion string
    """
    import random
    
    # Get suggestions for specific type or general
    suggestions = FOLLOW_UP_SUGGESTIONS.get(question_type, FOLLOW_UP_SUGGESTIONS["general"])
    
    return random.choice(suggestions)


def get_adaptive_footer(question_type: str = None) -> str:
    """
    Get adaptive footer based on question type.
    
    Args:
        question_type: Type of question
    
    Returns:
        Footer text string
    """
    if question_type and question_type in RESPONSE_FORMATTING["adaptive_footer"]:
        return RESPONSE_FORMATTING["adaptive_footer"][question_type]
    
    return RESPONSE_FORMATTING["footer_text"]


def format_error_message(error_type, **kwargs):
    """
    Format an error message.
    
    Args:
        error_type: Type of error
        **kwargs: Variables to format in the template
    
    Returns:
        Formatted error message string
    """
    template = ERROR_MESSAGES.get(error_type, "❌ Error desconocido")
    return template.format(**kwargs)


def format_pipeline_status(status_type: str, **kwargs) -> str:
    """
    Format a pipeline status message (for debug mode).
    
    Args:
        status_type: Type of status message
        **kwargs: Variables to format in the template
    
    Returns:
        Formatted status message string
    """
    template = PIPELINE_STATUS.get(status_type, "")
    return template.format(**kwargs) if template else ""


def should_show_warning(chunks_after_filter: int, avg_relevance: float) -> bool:
    """
    Determine if low relevance warning should be shown.
    
    Args:
        chunks_after_filter: Number of chunks after filtering
        avg_relevance: Average relevance score
    
    Returns:
        True if warning should be shown
    """
    # Show warning if very few chunks or low average relevance
    return chunks_after_filter < 2 or avg_relevance < 0.60