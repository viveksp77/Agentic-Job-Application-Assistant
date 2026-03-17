import os
import traceback
from typing import Generator
import ollama
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = 'llama3.2'
OPENAI_MODEL = 'gpt-4o-mini'


class LLMClient:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None

        if self.openai_client:
            print("[LLMClient] OpenAI client initialised — will use OpenAI first.")
        else:
            print("[LLMClient] No OpenAI key found — using Ollama only.")

    def chat(self, messages: list, max_retries: int = 2) -> str:
        """Blocking chat — returns full response string."""
        # --- 1. Try OpenAI ---
        if self.openai_client:
            for attempt in range(max_retries):
                try:
                    response = self.openai_client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=messages,
                    )
                    content = response.choices[0].message.content
                    print(f"[LLMClient] OpenAI response received ({len(content)} chars)")
                    return content
                except Exception as e:
                    err = str(e).lower()
                    if 'quota' in err or '429' in err or 'billing' in err:
                        print(f"[LLMClient] OpenAI quota issue — falling back to Ollama: {e}")
                        break
                    if attempt < max_retries - 1:
                        continue
                    print(f"[LLMClient] OpenAI failed after {max_retries} attempts: {e}")

        # --- 2. Try Ollama ---
        try:
            print(f"[LLMClient] Calling Ollama model: {OLLAMA_MODEL}")
            response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
            content = response['message']['content']
            print(f"[LLMClient] Ollama response received ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"[LLMClient] Ollama error: {e}")
            traceback.print_exc()

        # --- 3. Dummy fallback ---
        print("[LLMClient] WARNING: Both OpenAI and Ollama failed. Returning dummy response.")
        return self._dummy_fallback(messages)

    def stream(self, messages: list) -> Generator[str, None, None]:
        """
        Streaming chat — yields text chunks as they arrive.
        Falls back to chunking the full response if streaming is unavailable.
        """
        # --- Try Ollama streaming ---
        try:
            print(f"[LLMClient] Streaming from Ollama: {OLLAMA_MODEL}")
            stream = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                token = chunk.get('message', {}).get('content', '')
                if token:
                    yield token
            return
        except Exception as e:
            print(f"[LLMClient] Ollama streaming error: {e}")

        # --- Fallback: get full response and yield in small chunks ---
        try:
            full = self.chat(messages)
            words = full.split(' ')
            for i, word in enumerate(words):
                yield word + (' ' if i < len(words) - 1 else '')
        except Exception as e:
            yield f"[Error generating response: {e}]"

    def _dummy_fallback(self, messages: list) -> str:
        prompt = messages[-1]['content'].lower() if messages else ''
        if 'cover letter' in prompt:
            return "[DUMMY] Ollama not responding — check terminal for errors."
        elif 'interview' in prompt:
            return "1. [DUMMY] Ollama not responding.\n2. Verify ollama serve is running.\n3. Check model name with ollama list."
        elif 'optimize' in prompt or 'bullet' in prompt:
            return "• [DUMMY] Ollama not responding — check terminal."
        elif 'job description' in prompt:
            return '{"job_title": "Unknown", "required_skills": [], "experience_level": "Mid", "key_responsibilities": []}'
        else:
            return "[DUMMY] LLM unavailable — check terminal for Ollama errors."


llm_client = LLMClient()