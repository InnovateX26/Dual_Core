"""
Prompt Templates for the Multilingual Agricultural AI Assistant.
Defines system prompts, context injection, and language-specific instructions.
"""


SYSTEM_PROMPT = """You are **Krishi Mitra** (कृषि मित्र) — a friendly, knowledgeable AI agricultural advisor for Indian farmers.

## CRITICAL LANGUAGE RULE
**You MUST respond ENTIRELY in the language specified below.** This is the MOST IMPORTANT rule. If the farmer writes in Hindi, you reply in Hindi. If Tamil, reply in Tamil. If Hinglish (Hindi words in English letters), reply in Hinglish. Do NOT mix English into non-English responses unless using English technical terms or brand names.

{language_instruction}

## Your Identity
- You are a trusted farm advisor who speaks the farmer's language
- You have deep knowledge of Indian agriculture: crops, diseases, fertilizers, weather, government schemes, and market prices
- You are like a wise elder in the village who gives practical, tested advice

## Core Rules
1. **Keep language simple and farmer-friendly.** Avoid technical jargon. Use words a farmer with basic education would understand.
2. **Be practical and actionable.** Give specific product names, dosages, timings, and steps. Don't give vague advice.
3. **Be honest.** If you don't know, say so instead of making up information.
4. **Use simple formatting:** Short paragraphs, bullet points, and numbered steps.
5. **Be warm and respectful.** Address the farmer as "किसान भाई/बहन" or equivalent in their language.
6. **Focus on Indian context:** Indian crop varieties, Indian pesticide brands, Indian government schemes.
7. **Include safety warnings** when recommending pesticides or chemicals.

## Response Format
- Start with a brief, friendly greeting in the farmer's language
- Give the main advice in clear steps or bullet points
- End with an encouraging note
- Keep total response under 300 words
"""

CONTEXT_TEMPLATE = """## Reference Knowledge (Use this information to answer accurately)

The following verified information is relevant to the farmer's question. Use it to provide accurate, grounded responses:

{context_chunks}

---
**Important:** Base your answer primarily on the above reference knowledge. If the question goes beyond this information, you may use your general knowledge but indicate areas of uncertainty.
"""

NO_CONTEXT_TEMPLATE = """## Note
No specific reference documents were found for this query. Respond using your general agricultural knowledge for the Indian context. Be extra careful to indicate when you are not fully certain about specific details like dosages or product names.
"""


def build_system_prompt(language_instruction: str) -> str:
    """Build the complete system prompt with language instruction."""
    return SYSTEM_PROMPT.format(language_instruction=language_instruction)


def build_context_prompt(context_chunks: list[dict]) -> str:
    """
    Build the context injection portion of the prompt from retrieved chunks.

    Args:
        context_chunks: List of dicts with 'title', 'content', 'category', 'score'
    """
    if not context_chunks:
        return NO_CONTEXT_TEMPLATE

    formatted_chunks = []
    for i, chunk in enumerate(context_chunks, 1):
        category_label = chunk.get("category", "general").replace("_", " ").title()
        formatted_chunks.append(
            f"### [{category_label}] {chunk.get('title', 'Unknown')}\n"
            f"{chunk.get('content', '')}\n"
            f"(Relevance: {chunk.get('score', 0):.0%})"
        )

    chunks_text = "\n\n".join(formatted_chunks)
    return CONTEXT_TEMPLATE.format(context_chunks=chunks_text)


def build_user_message(farmer_query: str, context_prompt: str) -> str:
    """Build the final user message combining context and query."""
    return f"{context_prompt}\n\n## Farmer's Question\n{farmer_query}"


# === Suggestion Templates per Language ===

SUGGESTIONS = {
    "hi": [
        "गेहूं में रतुआ रोग का इलाज क्या है?",
        "PM-KISAN योजना में कैसे रजिस्टर करें?",
        "टमाटर में सबसे अच्छी खाद कौन सी है?",
        "ड्रिप सिंचाई कैसे लगवाएं?",
        "फसल बीमा कैसे करवाएं?",
    ],
    "en": [
        "How to treat wheat rust disease?",
        "What are the best fertilizers for rice?",
        "How to register for PM-KISAN scheme?",
        "Best practices for drip irrigation",
        "How to prevent fungal diseases in crops?",
    ],
    "bn": [
        "ধানের ব্লাস্ট রোগের চিকিৎসা কী?",
        "PM-KISAN যোজনায় কীভাবে নিবন্ধন করবেন?",
        "টমেটোতে সেরা সার কোনটি?",
        "ফসল বীমা কীভাবে করবেন?",
    ],
    "ta": [
        "நெல் ப்ளாஸ்ட் நோயை எப்படி குணப்படுத்துவது?",
        "PM-KISAN திட்டத்தில் எப்படி பதிவு செய்வது?",
        "தக்காளிக்கு சிறந்த உரம் எது?",
    ],
    "te": [
        "వరి బ్లాస్ట్ వ్యాధికి చికిత్స ఏమిటి?",
        "PM-KISAN పథకంలో ఎలా నమోదు చేసుకోవాలి?",
        "టమాటాకు ఉత్తమ ఎరువు ఏది?",
    ],
    "mr": [
        "गव्हातील तांबेरा रोगावर उपचार काय?",
        "PM-KISAN योजनेत नोंदणी कशी करावी?",
        "टोमॅटोसाठी सर्वोत्तम खत कोणते?",
    ],
    "gu": [
        "ઘઉંમાં રસ્ટ રોગની સારવાર શું છે?",
        "PM-KISAN યોજનામાં કેવી રીતે નોંધણી કરાવવી?",
    ],
    "kn": [
        "ಭತ್ತದ ಬ್ಲಾಸ್ಟ್ ರೋಗಕ್ಕೆ ಚಿಕಿತ್ಸೆ ಏನು?",
        "PM-KISAN ಯೋಜನೆಯಲ್ಲಿ ಹೇಗೆ ನೋಂದಾಯಿಸುವುದು?",
    ],
    "ml": [
        "നെല്ലിലെ ബ്ലാസ്റ്റ് രോഗത്തിന് ചികിത്സ എന്താണ്?",
        "PM-KISAN പദ്ധതിയിൽ എങ്ങനെ രജിസ്റ്റർ ചെയ്യാം?",
    ],
    "hi-en": [
        "Tomato mein fungal disease aa gayi hai, kya karu?",
        "PM-KISAN mein registration kaise hoga?",
        "Gehun ki fasal mein kaunsi khad daalni chahiye?",
        "Drip irrigation ka kharcha kitna aata hai?",
        "Fasal bima kaise karwa sakte hain?",
    ],
    "mai": [
        "गेहूं मे रतुआ रोग के इलाज की बात बताउ?",
        "PM-KISAN मे रजिस्ट्रेशन कोना होतै?",
    ],
}


def get_suggestions(lang_code: str) -> list[str]:
    """Get suggestion chips for a given language."""
    return SUGGESTIONS.get(lang_code, SUGGESTIONS["en"])
