from translate import Translator

def translate_text(text: str, source_lang: str = "es", target_lang: str = "en") -> str:
    translator = Translator(from_lang=source_lang, to_lang=target_lang)
    translation = translator.translate(text)
    return translation
    