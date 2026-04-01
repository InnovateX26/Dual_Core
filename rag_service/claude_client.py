"""
LLM Client — Handles AI response generation using Google Gemini API.
Includes fallback template-based responses when API key is not available.
"""

import os
import time
from typing import Optional

from prompt_templates import build_system_prompt, build_context_prompt, build_user_message
from language_detector import get_response_language_instruction


# Auto-load from .env file if keys not in environment
def _load_env_file():
    """Load API keys from the project's .env file."""
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and value and key not in os.environ:
                        os.environ[key] = value

_load_env_file()

# Check for API keys — prefer Gemini (user already has it)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

USE_GEMINI = bool(GOOGLE_API_KEY and GOOGLE_API_KEY != "your_key_here")
USE_CLAUDE = bool(ANTHROPIC_API_KEY and ANTHROPIC_API_KEY != "your_key_here") and not USE_GEMINI

_gemini_model = None
_claude_client = None

if USE_GEMINI:
    try:
        import google.generativeai as genai
        genai.configure(api_key=GOOGLE_API_KEY)
        _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
        print("[LLM] ✅ Gemini API initialized (gemini-2.0-flash)")
    except Exception as e:
        print(f"[LLM] ❌ Gemini init failed: {e}")
        USE_GEMINI = False

elif USE_CLAUDE:
    try:
        import anthropic
        _claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        print("[LLM] ✅ Claude API initialized")
    except Exception as e:
        print(f"[LLM] ❌ Claude init failed: {e}")
        USE_CLAUDE = False

else:
    print("[LLM] ⚠️ No API key found — using built-in fallback responses")


def generate_response(
    query: str,
    context_chunks: list[dict],
    language_code: str,
    model: str = "auto",
    max_tokens: int = 1500,
    temperature: float = 0.7,
) -> dict:
    """
    Generate a response using Gemini, Claude, or fallback.
    """
    start_time = time.time()

    # Build prompts
    language_instruction = get_response_language_instruction(language_code)
    system_prompt = build_system_prompt(language_instruction)
    context_prompt = build_context_prompt(context_chunks)
    user_message = build_user_message(query, context_prompt)

    # Try Gemini first
    if USE_GEMINI and _gemini_model:
        try:
            # Combine system + user into a single prompt for Gemini
            full_prompt = f"{system_prompt}\n\n{user_message}"
            
            response = _gemini_model.generate_content(
                full_prompt,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
            )

            response_text = response.text
            elapsed_ms = int((time.time() - start_time) * 1000)

            return {
                "response": response_text,
                "model_used": "gemini-2.0-flash",
                "response_time_ms": elapsed_ms,
                "tokens_used": 0,
            }

        except Exception as e:
            print(f"[LLM] Gemini error: {e}")
            return _fallback_response(query, context_chunks, language_code, start_time, f"Gemini error: {e}")

    # Try Claude
    elif USE_CLAUDE and _claude_client:
        try:
            message = _claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )

            response_text = message.content[0].text
            elapsed_ms = int((time.time() - start_time) * 1000)

            return {
                "response": response_text,
                "model_used": "claude-sonnet-4-20250514",
                "response_time_ms": elapsed_ms,
                "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
            }

        except Exception as e:
            print(f"[LLM] Claude error: {e}")
            return _fallback_response(query, context_chunks, language_code, start_time, str(e))

    # Fallback
    else:
        return _fallback_response(query, context_chunks, language_code, start_time)


def _fallback_response(
    query: str,
    context_chunks: list[dict],
    language_code: str,
    start_time: float,
    error: Optional[str] = None,
) -> dict:
    """Template-based response when no LLM API is available."""
    elapsed_ms = int((time.time() - start_time) * 1000)

    if not context_chunks:
        response = _get_no_context_response(language_code, query)
    else:
        response = _build_context_response(context_chunks, language_code, query)

    return {
        "response": response,
        "model_used": "built-in-fallback",
        "response_time_ms": elapsed_ms,
        "tokens_used": 0,
        "fallback_reason": error or "No API key configured",
    }


def _get_no_context_response(lang: str, query: str) -> str:
    """Response when no relevant context is found."""
    responses = {
        "hi": (
            f"🙏 नमस्ते किसान भाई!\n\n"
            f"आपने पूछा: \"{query}\"\n\n"
            f"इस विषय पर मेरे पास अभी विस्तृत जानकारी उपलब्ध नहीं है। "
            f"मैं आपको सुझाव दूंगा कि अपने नज़दीकी **कृषि विज्ञान केंद्र (KVK)** से संपर्क करें "
            f"या **किसान कॉल सेंटर (1800-180-1551)** पर कॉल करें।\n\n"
            f"🌾 कोई और सवाल हो तो ज़रूर पूछें!"
        ),
        "en": (
            f"🙏 Namaste farmer friend!\n\n"
            f"You asked: \"{query}\"\n\n"
            f"I don't have detailed information on this specific topic right now. "
            f"I suggest contacting your nearest **Krishi Vigyan Kendra (KVK)** "
            f"or calling the **Kisan Call Centre (1800-180-1551)** for expert help.\n\n"
            f"🌾 Feel free to ask any other farming question!"
        ),
        "hi-en": (
            f"🙏 Namaste kisan bhai!\n\n"
            f"Aapne pucha: \"{query}\"\n\n"
            f"Is topic par mere paas abhi detailed information nahi hai. "
            f"Aap apne nearest **KVK (Krishi Vigyan Kendra)** se contact karein "
            f"ya **Kisan Call Centre (1800-180-1551)** par call karein.\n\n"
            f"🌾 Koi aur sawaal ho toh zaroor puchiye!"
        ),
    }
    return responses.get(lang, responses["en"])


def _build_context_response(chunks: list[dict], lang: str, query: str) -> str:
    """Build a response from retrieved context chunks."""
    best_chunk = chunks[0]
    title = best_chunk.get("title", "")
    content = best_chunk.get("content", "")

    if lang == "hi":
        header = f"🙏 नमस्ते किसान भाई!\n\n**{title}** के बारे में जानकारी:\n\n"
        footer = "\n\n🌾 और जानकारी चाहिए तो पूछें! किसान कॉल सेंटर: 1800-180-1551"
    elif lang == "hi-en":
        header = f"🙏 Namaste kisan bhai!\n\n**{title}** ke baare mein jaankari:\n\n"
        footer = "\n\n🌾 Aur kuch jaanna hai toh puchiye! Kisan Call Centre: 1800-180-1551"
    else:
        header = f"🙏 Namaste farmer friend!\n\nHere's information about **{title}**:\n\n"
        footer = "\n\n🌾 Feel free to ask more questions! Kisan Call Centre: 1800-180-1551"

    # Format content
    sentences = content.split(". ")
    formatted_content = ""
    for sentence in sentences:
        s = sentence.strip()
        if s:
            if ":" in s and len(s.split(":")[0]) < 50:
                formatted_content += f"**{s.split(':')[0]}:** {':'.join(s.split(':')[1:])}\n"
            else:
                formatted_content += f"• {s}.\n"

    if len(chunks) > 1:
        additional = "\n**Related Information:**\n"
        for chunk in chunks[1:3]:
            additional += f"• {chunk.get('title', '')}\n"
        formatted_content += additional

    return header + formatted_content + footer
