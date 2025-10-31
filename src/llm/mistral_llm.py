"""
Mistral LLM Module - FASE B Optimized

Supports explicit language control for RAG responses.
Can generate responses in Spanish or English as needed for translation pipeline.
Supports dynamic prompts based on question type.
"""

import os
from mistralai import Mistral
from config.prompt_config import get_rag_system_prompt, get_rag_user_prompt, format_prompt


class MistralLLM:
    """
    Mistral LLM wrapper with explicit language control.
    
    FASE B: Supports generating responses in English (for translation pipeline)
    or Spanish (direct response).
    
    NEW: Dynamic prompts based on question type for optimal response length/style.
    """
    
    def __init__(self, api_key: str) -> None:
        """
        Initialize Mistral LLM client.
        
        Args:
            api_key: Mistral API key
        """
        self.mistral_client = Mistral(api_key=api_key)
        self.language = "español"  # Default language
    
    def mistral_chat(
        self, 
        context: str, 
        question: str, 
        response_language: str = None,
        question_type: str = None
    ) -> str:
        """
        Generate RAG response using Mistral.
        
        Args:
            context: Retrieved context from KB
            question: User question
            response_language: Language for response (overrides self.language if provided)
            question_type: Type of question (factual/interpretative/comparative/procedural)
                          Used to adjust response style and length
        
        Returns:
            Generated response in specified language
        """
        # Determine response language
        target_language = response_language or self.language
        
        # Get prompts in target language WITH question type style
        system_prompt = get_rag_system_prompt(
            language=target_language,
            question_type=question_type  # NEW: Adds specialized instructions
        )
        user_prompt_template = get_rag_user_prompt(target_language)
        
        # Format the user prompt with context and question
        user_prompt = format_prompt(
            user_prompt_template, 
            context=context, 
            question=question
        )
        
        # Log for debugging
        print(f"🤖 LLM generating response in: {target_language}")
        if question_type:
            print(f"📝 Question type: {question_type}")
        
        # Call Mistral API
        response = self.mistral_client.chat.complete(
            model="mistral-small-latest",
            temperature=0.3,  # Slightly higher for more natural responses
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )
        
        response_text = str(response.choices[0].message.content)
        
        print(f"✅ LLM response generated ({len(response_text)} chars)")
        
        return response_text
    
    def set_language(self, language: str) -> None:
        """
        Set default response language.
        
        Args:
            language: Target language (español/english)
        """
        self.language = language
        print(f"🌐 LLM default language set to: {language}")