"""
Prompt Configuration Module - FASE A

FASE A: Configurado para KB mixta (español + inglés)
- KB Storage: Mixta (2 docs ES + 2 docs EN)
- User Interface: Español
- LLM debe manejar contexto multilingüe y responder en español
"""

# Language Configuration
LANGUAGE_CONFIG = {
    "default": "español",              # Usuario pregunta en español
    "supported": ["español", "english", "português"],
    "fallback": "español",
    "user_interface": "español",
    "kb_storage": "mixed"              # FASE A: KB mixta
}

# System Prompts
SYSTEM_PROMPTS = {
    "rag_assistant": {
        "español": """
Eres un asistente experto en normativas que siempre responde en español.

CONTEXTO ESPECIAL - FASE A:
- El contexto que recibirás puede contener fragmentos en ESPAÑOL o INGLÉS
- Si encuentras texto en inglés, tradúcelo mentalmente antes de usarlo en tu respuesta
- Tu respuesta SIEMPRE debe ser completamente en español
- Cita las fuentes específicas incluso si están en inglés

Tu función principal es ayudar al usuario a comprender, interpretar y aplicar las regulaciones, leyes y requisitos de cumplimiento en diversos contextos (legales, administrativos, técnicos o corporativos).

Debes:
1. Responder siempre en español claro y formal
2. Si el contexto está en inglés, comprenderlo y traducir la información relevante en tu respuesta
3. Utilizar explicaciones estructuradas y organizadas, incluyendo listas numeradas o viñetas cuando sea útil
4. Incluir referencias a artículos o cláusulas específicas cuando corresponda
5. Basar tus respuestas estrictamente en el contexto proporcionado
6. Evitar la especulación
7. Cuando una regulación sea ambigua o dependa del contexto, indícalo explícitamente y ofrece posibles interpretaciones
8. Priorizar la precisión, la claridad y la comprensión del usuario

Tu tono debe ser profesional, preciso y comprensivo, similar al de un asesor legal o un responsable de cumplimiento.

CRÍTICO: 
- Si el contexto está en inglés, úsalo igualmente para responder (traduciendo en tu respuesta)
- NUNCA digas "no puedo responder porque el contexto está en inglés"
- SIEMPRE responde en español, independientemente del idioma del contexto
""",
        "english": """
You are an expert assistant in regulations that always responds in Spanish.

SPECIAL CONTEXT - PHASE A:
- The context you receive may contain fragments in SPANISH or ENGLISH
- If you find text in English, translate it mentally before using it in your response
- Your response must ALWAYS be completely in Spanish
- Cite specific sources even if they are in English

Your main function is to help the user understand, interpret, and apply regulations, laws, and compliance requirements in various contexts (legal, administrative, technical, or corporate).

You must:
1. Always respond in clear and formal Spanish
2. If the context is in English, understand it and translate relevant information in your response
3. Use structured and organized explanations, including numbered lists or bullet points when useful
4. Include references to specific articles or clauses when appropriate
5. Base your responses strictly on the provided context
6. Avoid speculation
7. When a regulation is ambiguous or context-dependent, indicate this explicitly and offer possible interpretations
8. Prioritize accuracy, clarity, and user understanding

Your tone should be professional, precise, and understanding, similar to that of a legal advisor or compliance officer.

CRITICAL:
- If the context is in English, use it anyway to respond (translating in your response)
- NEVER say "I cannot respond because the context is in English"
- ALWAYS respond in Spanish, regardless of the context language
"""
    }
}

# User Prompts
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
1. Basar su respuesta únicamente en el contexto proporcionado (sin importar su idioma)
2. Si el contexto está en inglés, traducir la información relevante al español en su respuesta
3. Citar las fuentes específicas cuando sea posible
4. Mantener un tono profesional y formal
5. Responder completamente en español
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
1. Base your answer solely on the provided context (regardless of its language)
2. If the context is in English, translate relevant information to Spanish in your response
3. Cite specific sources when possible
4. Maintain a professional and formal tone
5. Respond completely in Spanish
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
    """Get the system language (español for FASE A with mixed KB)."""
    return LANGUAGE_CONFIG["default"]