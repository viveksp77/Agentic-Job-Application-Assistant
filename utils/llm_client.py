import os
import traceback
import ollama
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Model config — update this if you switch models
# ---------------------------------------------------------------------------
OLLAMA_MODEL = 'llama3.2'       # must match exactly what `ollama list` shows
OPENAI_MODEL = 'gpt-4o-mini'    # only used if OPENAI_API_KEY is set in .env


class LLMClient:
    def __init__(self):
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None

        if self.openai_client:
            print("[LLMClient] OpenAI client initialised — will use OpenAI first.")
        else:
            print("[LLMClient] No OpenAI key found — using Ollama only.")

    def chat(self, messages: list, max_retries: int = 2) -> str:
        """
        Unified chat interface: OpenAI → Ollama → dummy fallback.

        Args:
            messages:    List of {'role': 'system'|'user'|'assistant', 'content': str}
            max_retries: How many times to retry on transient OpenAI errors.

        Returns:
            Response text string from the LLM.
        """
        # --- 1. Try OpenAI if key is available ---
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
                        print(f"[LLMClient] OpenAI quota/billing issue — falling back to Ollama: {e}")
                        break
                    if attempt < max_retries - 1:
                        print(f"[LLMClient] OpenAI attempt {attempt + 1} failed, retrying: {e}")
                        continue
                    print(f"[LLMClient] OpenAI failed after {max_retries} attempts: {e}")

        # --- 2. Try Ollama ---
        try:
            print(f"[LLMClient] Calling Ollama model: {OLLAMA_MODEL}")
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=messages,
            )
            content = response['message']['content']
            print(f"[LLMClient] Ollama response received ({len(content)} chars)")
            return content
        except Exception as e:
            print(f"[LLMClient] Ollama error: {e}")
            traceback.print_exc()

        # --- 3. Dummy fallback (last resort — tells you something is broken) ---
        print("[LLMClient] WARNING: Both OpenAI and Ollama failed. Returning dummy response.")
        return self._dummy_fallback(messages)

    def _dummy_fallback(self, messages: list) -> str:
        """
        Last-resort static responses.
        These are intentionally obvious so you notice when real LLM calls fail.
        Check your terminal for the Ollama error printed above.
        """
        prompt = messages[-1]['content'].lower() if messages else ''

        if 'cover letter' in prompt:
            return (
                "[DUMMY] Dear Hiring Manager,\n\n"
                "Ollama is not responding — check your terminal for errors.\n\n"
                "Sincerely, Candidate"
            )
        elif 'interview' in prompt:
            return (
                "1. [DUMMY] Ollama is not responding — check terminal.\n"
                "2. Verify `ollama serve` is running.\n"
                "3. Verify model name with `ollama list`."
            )
        elif 'optimize' in prompt or 'bullet' in prompt:
            return "• [DUMMY] Ollama not responding — check terminal for errors."
        elif 'job description' in prompt or 'analyze' in prompt:
            return '{"job_title": "Unknown", "required_skills": [], "experience_level": "Mid", "key_responsibilities": []}'
        elif 'roadmap' in prompt or 'suggestion' in prompt:
            return "1. [DUMMY] Ollama not responding — check terminal."
        else:
            return "[DUMMY] LLM unavailable — check terminal for Ollama errors."


# Global singleton used by all tools
llm_client = LLMClient()