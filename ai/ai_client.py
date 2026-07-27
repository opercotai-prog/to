import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LOCAL_MODELS = [
    "llama3.2:1b",
]

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)


def get_completion(prompt, model=None):
    models_to_try = [model] if model else LOCAL_MODELS
    for current_model in models_to_try:
        try:
            print(f"--- Пробую модель: {current_model} ---")
            response = client.chat.completions.create(
                model=current_model,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Ошибка с моделью {current_model}: {e}")
            if current_model == models_to_try[-1]:
                return "Ошибка анализа (все модели недоступны)"
            time.sleep(1)
