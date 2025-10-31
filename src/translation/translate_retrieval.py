"""
Translation Module - FASE B Optimized

Provides high-quality translation using Mistral API for technical/legal content.
Fallback to free library if Mistral fails.

FASE B: Explicit translation pipeline (ES↔EN)
"""

import os
from mistralai import Mistral
from translate import Translator


class TranslationService:
    """
    Translation service with Mistral API primary, free library fallback.
    Optimized for technical/legal content translation.
    """
    
    def __init__(self, mistral_api_key: str = None):
        """
        Initialize translation service.
        
        Args:
            mistral_api_key: Mistral API key (optional, uses env var if not provided)
        """
        self.mistral_api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        self.mistral_client = Mistral(api_key=self.mistral_api_key) if self.mistral_api_key else None
        self.use_mistral = bool(self.mistral_client)
        
        print(f"🌐 Translation service initialized: {'Mistral API' if self.use_mistral else 'Free library (fallback)'}")
    
    def translate_with_mistral(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate using Mistral API - high quality for technical/legal content.
        
        Args:
            text: Text to translate
            source_lang: Source language code (es/en)
            target_lang: Target language code (es/en)
        
        Returns:
            Translated text
        """
        # Language mapping
        lang_names = {
            "es": "Spanish",
            "en": "English"
        }
        
        source_name = lang_names.get(source_lang, source_lang)
        target_name = lang_names.get(target_lang, target_lang)
        
        # Specialized prompt for technical/legal translation
        prompt = f"""Translate the following {source_name} text to {target_name}.

CRITICAL INSTRUCTIONS:
- Preserve ALL technical terms, legal references, and proper nouns
- Maintain the original structure and formatting
- Keep numbers, dates, and citations EXACTLY as they appear
- For technical terms without direct translation, use the original term in parentheses
- If translating legal documents, preserve legal terminology precision
- DO NOT add explanations or interpretations, ONLY translate

Text to translate:
{text}

Translation:"""

        try:
            response = self.mistral_client.chat.complete(
                model="mistral-small-latest",
                temperature=0.1,  # Low temperature for consistent translations
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            translated = str(response.choices[0].message.content).strip()
            return translated
            
        except Exception as e:
            print(f"❌ Mistral translation failed: {e}")
            raise
    
    def translate_with_free_library(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate using free library (fallback).
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
        
        Returns:
            Translated text
        """
        try:
            translator = Translator(from_lang=source_lang, to_lang=target_lang)
            translation = translator.translate(text)
            return translation
        except Exception as e:
            print(f"❌ Free library translation failed: {e}")
            raise
    
    def translate(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Translate text using best available method.
        
        Args:
            text: Text to translate
            source_lang: Source language code (es/en)
            target_lang: Target language code (es/en)
        
        Returns:
            Translated text
        
        Raises:
            Exception: If all translation methods fail
        """
        # Skip translation if same language
        if source_lang == target_lang:
            return text
        
        # Validate input
        if not text or not text.strip():
            return text
        
        # Try Mistral first (high quality)
        if self.use_mistral:
            try:
                print(f"🔄 Translating with Mistral: {source_lang}→{target_lang} ({len(text)} chars)")
                translated = self.translate_with_mistral(text, source_lang, target_lang)
                print(f"✅ Mistral translation successful")
                return translated
            except Exception as e:
                print(f"⚠️ Mistral failed, trying fallback: {e}")
        
        # Fallback to free library
        try:
            print(f"🔄 Translating with free library: {source_lang}→{target_lang}")
            translated = self.translate_with_free_library(text, source_lang, target_lang)
            print(f"✅ Free library translation successful")
            return translated
        except Exception as e:
            print(f"❌ All translation methods failed: {e}")
            # Return original text if all fails (graceful degradation)
            print(f"⚠️ Returning original text (no translation)")
            return text


# Global instance (singleton pattern)
_translation_service = None


def get_translation_service() -> TranslationService:
    """Get or create global translation service instance."""
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service


def translate_text(text: str, source_lang: str = "es", target_lang: str = "en") -> str:
    """
    Convenience function for translation (backwards compatible).
    
    Args:
        text: Text to translate
        source_lang: Source language code (es/en)
        target_lang: Target language code (es/en)
    
    Returns:
        Translated text
    """
    service = get_translation_service()
    return service.translate(text, source_lang, target_lang)