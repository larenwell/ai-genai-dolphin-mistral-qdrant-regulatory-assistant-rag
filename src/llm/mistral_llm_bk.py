import os
from mistralai import Mistral
from config.prompt_config import get_rag_system_prompt, get_rag_user_prompt, format_prompt

class MistralLLM:
    def __init__(self, api_key: str) -> None:
        self.mistral_client = Mistral(api_key=api_key)
        self.language = "español"

    def mistral_chat(self, context, question: str) -> str:
        # Get prompts from centralized configuration
        system_prompt = get_rag_system_prompt(self.language)
        user_prompt_template = get_rag_user_prompt(self.language)
        
        # Format the user prompt with context and question
        user_prompt = format_prompt(user_prompt_template, context=context, question=question)

        response = self.mistral_client.chat.complete(
            model="mistral-small-latest",
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

        response = str(response.choices[0].message.content)
        return response
    
