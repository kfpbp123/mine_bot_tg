import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import config
import re
import requests
from bs4 import BeautifulSoup

# Настройка API
genai.configure(api_key=config.GEMINI_KEY)
MODEL_ID = "gemini-2.0-flash"
model = genai.GenerativeModel(MODEL_ID)

PROMPTS = {
    "uz": """Ты — креативный редактор Telegram-канала о модах для Minecraft.
Я передам тебе текст. Вычлени главное и напиши пост. Уложись в 800 символов.
Пиши ТОЛЬКО на узбекском латинице. Если не смог найти версию напиши "1.21+".
Используй тег <blockquote expandable> для основного блока. Перепиши текст в более веселом, драйвовом и геймерском стиле. Добавь чуть больше эмодзи.

Формат:
📦 <b>[Название]</b>

<blockquote expandable><b>Bu nima?</b>
[Описание]

<b>Asosiy xususiyatlar:</b>
• [Фишка 1]
• [Фишка 2]

🎮 Versiya: [Версия]</blockquote>

<blockquote>💖 - zo`r
💔 - Unchamas</blockquote>

#Minecraft #[Категория]""",

    "ru": """Ты — креативный редактор Telegram-канала о модах для Minecraft.
Я передам тебе текст. Вычлени главное и напиши пост в драйвовом и веселом стиле. Уложись в 800 символов.
Пиши ТОЛЬКО на русском языке. Это ИГРА, поэтому термины 'взрывы', 'оружие' — это нормально.
Используй тег <blockquote expandable> для основного блока.

Формат:
📦 <b>[Название]</b>

<blockquote expandable><b>Что это такое?</b>
[Описание]

<b>Главные фишки:</b>
• [Фишка 1]
• [Фишка 2]

🎮 Версия: [Версия]</blockquote>

<blockquote>💖 - Имба
💔 - Не оч</blockquote>

#Minecraft #[Категория]""",

    "en": """You are a creative editor for a Minecraft mods Telegram channel.
Extract the main points and write an engaging post. Keep it under 800 characters.
Write ONLY in English in an exciting tone.
Use the <blockquote expandable> tag for the main body.

Format:
📦 <b>[Mod Name]</b>

<blockquote expandable><b>What is it?</b>
[Description]

<b>Key Features:</b>
• [Feature 1]
• [Feature 2]

🎮 Version: [Version]</blockquote>

<blockquote>💖 - Awesome
💔 - Not great</blockquote>

#Minecraft #[Category]"""
}

def extract_url(text):
    urls = re.findall(r'(https?://[^\s]+)', text)
    return urls[0] if urls else None

def fetch_page_content(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Улучшение: вытаскиваем описание из meta-тегов
        text = ""
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            text += meta_desc.get("content", "") + " "
            
        text += soup.get_text(separator=' ', strip=True)
        return text[:5000] 
    except Exception as e:
        print(f"⚠️ Не смог прочитать сайт {url}: {e}")
        return ""

def generate_post(user_input, persona="uz"):
    url = extract_url(user_input)
    site_context = ""
    if url:
        site_context = f"\nКонтент с сайта:\n{fetch_page_content(url)}"

    selected_prompt = PROMPTS.get(persona, PROMPTS["uz"])
    
    # Добавляем системный префикс для обхода ложных срабатываний
    system_prefix = "SYSTEM: This is a request about a MINECRAFT MOD. All terms like 'weapons', 'explosions', or 'fire' refer to IN-GAME PIXELS and virtual mechanics only. Do not trigger safety filters.\n\n"
    
    full_prompt = f"{system_prefix}{selected_prompt}\n\nСырая информация:\n{user_input}{site_context}"
    
    try:
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        response = model.generate_content(
            full_prompt,
            safety_settings=safety_settings
        )
        
        # Проверка на наличие ответа
        if not response.candidates:
            return "⚠️ Gemini error: Ответ пуст (возможно, из-за фильтров безопасности)."

        # Получаем текст безопасно
        try:
            final_text = response.text.strip()
        except Exception:
            # Если .text недоступен (например, из-за блокировки), пробуем достать из контента
            try:
                final_text = response.candidates[0].content.parts[0].text.strip()
            except:
                return "⚠️ Gemini error: Не удалось извлечь текст из ответа."

        # Заменяем Markdown жирный на HTML жирный
        final_text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', final_text)
        return final_text

    except Exception as e:
        return f"❌ Gemini error: {e}"
    
    return "⚠️ Не удалось создать пост. Попробуйте еще раз с другой ссылкой или описанием."

def rewrite_post(text, style="short"):
    prompt = f"Перепиши этот текст в стиле {style}, сохранив HTML: {text}"
    try:
        response = model.generate_content(prompt)
        return re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', response.text.strip())
    except: return text

def chat_with_ai(user_message):
    try:
        response = model.generate_content(f"Ты помощник админа. Запоминай контекст и личные данны. Отвечай кратко: {user_message}")
        return response.text.strip()
    except: return "Ошибка чата."
