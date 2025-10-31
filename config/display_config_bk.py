"""
Display Configuration for Chainlit Frontend

This module contains all the configuration parameters for the visual display
and formatting of responses in the Chainlit interface.
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
    "show_language_info": True  # Show detected language and translation info
}

# Emojis and icons
EMOJIS = {
    "welcome": "",
    "assistant": "",
    "sources": "",
    "processing": "",
    "error": "",
    "warning": "",
    "suggestion": "",
    "document": "",
    "page": "",
    "relevance": "",
    "score": ""
}

# Relevance score icons
RELEVANCE_ICONS = {
    "high": "🟢",
    "medium": "🟡", 
    "low": "🔴"
}

# Follow-up suggestions
FOLLOW_UP_SUGGESTIONS = [
    "¿Te gustaría que profundice en algún aspecto específico?",
    "¿Necesitas información adicional sobre este tema?",
    "¿Hay alguna otra normativa relacionada que te interese consultar?",
    "¿Te gustaría que busque información más específica sobre este punto?",
    "¿Hay algún estándar o código particular que te interese revisar?"
]

# Error messages
ERROR_MESSAGES = {
    "processing_error": """
### **Error en el procesamiento**

Lo sentimos, hubo un problema al procesar tu consulta:

**Error:** {error}

**Sugerencias:**
• Verifica que tu pregunta esté clara y específica
• Intenta reformular la consulta
• Si el problema persiste, contacta al administrador

**¿Te gustaría intentar con otra pregunta?**
""",
    
    "no_sources": "**No se encontraron fuentes relevantes.**",
    "no_response": "**No se pudo generar una respuesta.**",
    "processing": "**Procesando tu consulta...**"
}

# Welcome message
WELCOME_MESSAGE = """
## **¡Bienvenido al Asistente de Normativa!**

Soy tu asistente especializado en normativas técnicas y documentos de ingeniería. Puedo ayudarte con:

• **Consultas técnicas** sobre normativas y estándares
• **Análisis de documentos** y especificaciones
• **Recomendaciones** basadas en la documentación disponible
• **Búsqueda inteligente** en la base de conocimiento

**¿En qué puedo ayudarte hoy?**
"""

# Response formatting
RESPONSE_FORMATTING = {
    "add_header": True,
    "add_footer": True,
    "footer_text": "*Esta respuesta se generó basándose en la información técnica disponible en los documentos.*",
    "use_separators": False
}

# Source formatting
SOURCE_FORMATTING = {
    "header": "### **Fuentes consultadas**\n",
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

def get_display_config():
    """Get the complete display configuration."""
    return {
        "message_formatting": MESSAGE_FORMATTING,
        "source_display": SOURCE_DISPLAY,
        "visual_elements": VISUAL_ELEMENTS,
        "emojis": EMOJIS,
        "relevance_icons": RELEVANCE_ICONS,
        "follow_up_suggestions": FOLLOW_UP_SUGGESTIONS,
        "error_messages": ERROR_MESSAGES,
        "welcome_message": WELCOME_MESSAGE,
        "response_formatting": RESPONSE_FORMATTING,
        "source_formatting": SOURCE_FORMATTING
    }

def get_emoji(key):
    """Get an emoji by key."""
    return EMOJIS.get(key, "")

def get_relevance_icon(score):
    """Get relevance icon based on score."""
    if score >= SOURCE_DISPLAY["relevance_thresholds"]["high"]:
        return RELEVANCE_ICONS["high"]
    elif score >= SOURCE_DISPLAY["relevance_thresholds"]["medium"]:
        return RELEVANCE_ICONS["medium"]
    else:
        return RELEVANCE_ICONS["low"]

def get_random_suggestion():
    """Get a random follow-up suggestion."""
    import random
    return random.choice(FOLLOW_UP_SUGGESTIONS)

def format_error_message(error_type, **kwargs):
    """Format an error message."""
    template = ERROR_MESSAGES.get(error_type, "Error desconocido")
    return template.format(**kwargs)