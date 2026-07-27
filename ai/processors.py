import json
import re
from ai.ai_client import get_completion

def extract_json(text):
    """Находит JSON-структуру в тексте, даже если ИИ добавил лишние слова."""
    try:
        # Ищем всё, что находится между первой { и последней }
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return match.group(0)
        return text
    except Exception:
        return text

def classify_law(law_text):
    prompt = f"""
    Проанализируй текст закона и верни ТОЛЬКО JSON объект.
    Текст: {law_text}
    
    Формат ответа:
    {{
        "domain": "один из: AML/ПОД/ФТ, Страховое право, Ценные бумаги, Общее",
        "product": "короткое название продукта",
        "actor": "через запятую: Bank, Insurance, Individual, Qualified_Investor, Regulator"
    }}
    Убедись, что в ответе НЕТ ничего, кроме JSON.
    """
    raw_response = get_completion(prompt)
    clean_response = extract_json(raw_response)
    
    try:
        return json.loads(clean_response)
    except Exception:
        # Если ИИ совсем не справился, возвращаем базовые теги
        return {"domain": "Общее", "product": "Не определен", "actor": "Individual"}

def summarize_law(law_text):
    prompt = f"""
    Ты аналитик в банке. Объясни суть этого изменения простыми словами для директора (2 предложения).
    Текст: {law_text}
    """
    response = get_completion(prompt)
    # Просто очищаем от возможных кавычек
    return response.strip().replace('"', '')
