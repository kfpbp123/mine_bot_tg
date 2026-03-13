import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import config
import database

genai.configure(api_key=config.GEMINI_KEY)
MODEL_ID = "gemini-2.0-flash"
model = genai.GenerativeModel(MODEL_ID)

def analyze_comments():
    try:
        comments = database.get_all_comments()
        if not comments:
            return "📭 Пока нет новых комментариев для анализа."
        
        # Берем последние 30 комментариев для анализа
        comments_text = "\n".join([f"- {c[0]}: {c[1]}" for c in comments[-30:]])
        
        prompt = f"""
        Ты — аналитик Minecraft-сообщества. Проанализируй последние сообщения пользователей:
        {comments_text}
        
        Твоя задача:
        1. О чем чаще всего спрашивают? (Версии, моды, проблемы).
        2. Какие идеи для новых постов можно извлечь?
        3. Общий настрой аудитории.
        
        Ответь кратко и по делу.
        """

        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        return f"⚠️ Ошибка при анализе: {e}"
