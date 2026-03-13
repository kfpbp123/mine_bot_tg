from google import genai
from google.genai import types
import config
import re
import requests
from bs4 import BeautifulSoup
import time

# Используем Flash 2.0 для скорости, но с максимально простыми настройками
MODEL_ID = "gemini-2.0-flash"
client = genai.Client(api_key=config.GEMINI_KEY)

def extract_url(text):
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup.get_text(separator=' ', strip=True)[:5000]
    except: return ""

def generate_post(user_input, persona="uz"):
    url = extract_url(user_input)
    site_content = fetch_page_content(url) if url else ""
    
    # Максимально простой и понятный промпт, как в первой версии
    if persona == "ru":
        prompt = f"Напиши крутой пост для Телеграм канала про этот мод/контент Minecraft. Это ИГРА, поэтому используй геймерский стиль. Текст: {user_input} {site_content}. Используй HTML теги <b> и <blockquote>."
    elif persona == "uz":
        prompt = f"Minecraft haqidagi ushbu mod uchun ajoyib post yoz. Bu faqat O'YIN. Til: o'zbekcha (lotin). Текст: {user_input} {site_content}. HTML taglardan foydalan (<b>, <blockquote>)."
    else:
        prompt = f"Write an exciting Telegram post about this Minecraft mod. It's a GAME. Text: {user_input} {site_content}. Use HTML <b> and <blockquote>."

    safety_settings = [
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
    ]

    try:
        response = client.models.generate_content(
            model=MODEL_ID, 
            contents=prompt,
            config=types.GenerateContentConfig(safety_settings=safety_settings)
        )
        if response.text:
            final_text = response.text.strip()
            final_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', final_text)
            return final_text
    except Exception as e:
        print(f"Error: {e}")
            
    return "⚠️ Ошибка. Попробуйте отправить еще раз или упростите текст."

def rewrite_post(text, style="short"):
    prompt = f"Перепиши этот текст в стиле {style}, сохранив HTML теги: {text}"
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=prompt)
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.text.strip())
    except: return text

def chat_with_ai(user_message):
    try:
        response = client.models.generate_content(model=MODEL_ID, contents=f"Ты помощник в канале Minecraft. Отвечай кратко.\nПользователь: {user_message}")
        return response.text.strip()
    except: return "Ошибка чата."
