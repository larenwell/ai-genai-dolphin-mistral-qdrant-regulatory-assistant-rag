"""
Prompt Configuration Module - FASE B

FASE B: Configurado para KB pura inglés + Pipeline de traducción explícita
- KB Storage: Pura EN (solo docs inglés)
- User Interface: Español
- Translation Pipeline: ES→EN→KB→EN→ES (explícita)
- LLM NO traduce, solo genera respuestas en idioma especificado
"""

# Language Configuration
LANGUAGE_CONFIG = {
    "default": "español",              # Usuario pregunta en español
    "supported": ["español", "english"],
    "fallback": "español",
    "user_interface": "español",       # UI siempre español
    "kb_storage": "english",           # FASE B: KB pura inglés
    "translation_mode": "explicit"     # FASE B: Traducción explícita, no mental
}

# System Prompts - FASE B: Respuestas directas sin traducción mental
SYSTEM_PROMPTS = {
    "rag_assistant": {
        "español": """
Eres un asistente experto en normativas que responde en español.

Tu función principal es ayudar al usuario a comprender, interpretar y aplicar las regulaciones, leyes y requisitos de cumplimiento en diversos contextos (legales, administrativos, técnicos o corporativos).

Debes:
1. Responder siempre en español claro y formal
2. Utilizar explicaciones estructuradas y organizadas, incluyendo listas numeradas o viñetas cuando sea útil
3. Incluir referencias a artículos o cláusulas específicas cuando corresponda
4. Basar tus respuestas estrictamente en el contexto proporcionado
5. Evitar la especulación
6. Cuando una regulación sea ambigua o dependa del contexto, indícalo explícitamente y ofrece posibles interpretaciones
7. Priorizar la precisión, la claridad y la comprensión del usuario

Tu tono debe ser profesional, preciso y comprensivo, similar al de un asesor legal o un responsable de cumplimiento.

IMPORTANTE: El contexto y la pregunta están en español. Responde directamente sin necesidad de traducir.
""",
        "english": """
You are an expert assistant in regulations that responds in English.

Your main function is to help the user understand, interpret, and apply regulations, laws, and compliance requirements in various contexts (legal, administrative, technical, or corporate).

You must:
1. Always respond in clear and formal English
2. Use structured and organized explanations, including numbered lists or bullet points when useful
3. Include references to specific articles or clauses when appropriate
4. Base your responses strictly on the provided context
5. Avoid speculation
6. When a regulation is ambiguous or context-dependent, indicate this explicitly and offer possible interpretations
7. Prioritize accuracy, clarity, and user understanding

Your tone should be professional, precise, and understanding, similar to that of a legal advisor or compliance officer.

IMPORTANT: The context and question are in English. Respond directly without needing to translate.
"""
    }
}

# User Prompts - FASE B: Sin instrucciones de traducción
USER_PROMPTS = {
    "rag_query": {
        "español": """
Responda la pregunta del usuario según el contexto proporcionado.

<contexto>
{context}
</contexto>

<pregunta>
{question}
</pregunta>

Por favor, asegúrese de:
1. Basar su respuesta únicamente en el contexto proporcionado
2. Citar las fuentes específicas cuando sea posible
3. Mantener un tono profesional y formal
4. Responder en español claro y preciso
""",
        "english": """
Answer the user's question based on the provided context.

<context>
{context}
</context>

<question>
{question}
</question>

Please ensure to:
1. Base your answer solely on the provided context
2. Cite specific sources when possible
3. Maintain a professional and formal tone
4. Respond in clear and precise English
"""
    }
}


def get_system_prompt(prompt_type: str, language: str = None) -> str:
    """
    Get a system prompt by type and language.
    
    Args:
        prompt_type: Type of prompt (e.g., 'rag_assistant')
        language: Language for the prompt (defaults to default language)
    
    Returns:
        Formatted system prompt string
    """
    if not language:
        language = LANGUAGE_CONFIG["default"]
    
    if language not in LANGUAGE_CONFIG["supported"]:
        language = LANGUAGE_CONFIG["fallback"]
    
    if prompt_type in SYSTEM_PROMPTS:
        return SYSTEM_PROMPTS[prompt_type].get(language, SYSTEM_PROMPTS[prompt_type][LANGUAGE_CONFIG["fallback"]])
    
    raise ValueError(f"Unknown prompt type: {prompt_type}")


def get_user_prompt(prompt_type: str, language: str = None) -> str:
    """
    Get a user prompt by type and language.
    
    Args:
        prompt_type: Type of prompt (e.g., 'rag_query')
        language: Language for the prompt (defaults to default language)
    
    Returns:
        Formatted user prompt string
    """
    if not language:
        language = LANGUAGE_CONFIG["default"]
    
    if language not in LANGUAGE_CONFIG["supported"]:
        language = LANGUAGE_CONFIG["fallback"]
    
    if prompt_type in USER_PROMPTS:
        return USER_PROMPTS[prompt_type].get(language, USER_PROMPTS[prompt_type][LANGUAGE_CONFIG["fallback"]])
    
    raise ValueError(f"Unknown prompt type: {prompt_type}")


def format_prompt(template: str, **kwargs) -> str:
    """
    Format a prompt template with the provided variables.
    
    Args:
        template: Prompt template string
        **kwargs: Variables to format in the template
    
    Returns:
        Formatted prompt string
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required variable in prompt template: {e}")


# Convenience functions for common use cases
def get_rag_system_prompt(language: str = None) -> str:
    """Get the RAG system prompt for the specified language."""
    return get_system_prompt("rag_assistant", language)


def get_rag_user_prompt(language: str = None) -> str:
    """Get the RAG user prompt for the specified language."""
    return get_user_prompt("rag_query", language)


def get_user_interface_language() -> str:
    """Get the user interface language (always Spanish for this workflow)."""
    return LANGUAGE_CONFIG["user_interface"]


def get_system_language() -> str:
    """Get the system language (español for user interface)."""
    return LANGUAGE_CONFIG["default"]


def get_kb_language() -> str:
    """Get the KB storage language (english for FASE B)."""
    return LANGUAGE_CONFIG["kb_storage"]


def get_translation_mode() -> str:
    """Get the translation mode (explicit for FASE B)."""
    return LANGUAGE_CONFIG["translation_mode"]