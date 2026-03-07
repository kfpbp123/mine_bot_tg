# main.py
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.background import BackgroundScheduler
import time
from datetime import datetime
import os
import config
import database
import ai_generator
import watermarker

# Инициализация
database.init_db()
bot = telebot.TeleBot(config.TELEGRAM_TOKEN)
user_drafts = {}
active_channels = {} 

# --- СИСТЕМА ПРОВЕРКИ ОЧЕРЕДИ (АВТОПОСТИНГ) ---

def check_queue():
    """Функция, которая вызывается планировщиком каждую минуту"""
    ready_posts = database.get_ready_posts()
    for post in ready_posts:
        post_id, photo_id, text, doc_id, channel_id = post
        try:
            # Отправка фото с текстом
            if photo_id:
                bot.send_photo(channel_id, photo_id, caption=text, parse_mode="HTML")
            elif text:
                bot.send_message(channel_id, text, parse_mode="HTML")
            
            # Отправка документа (если есть)
            if doc_id:
                bot.send_document(channel_id, doc_id)
                
            # Помечаем как отправленное
            database.mark_as_posted(post_id)
            print(f"✅ Пост {post_id} успешно опубликован в {channel_id}")
            
        except Exception as e:
            print(f"❌ Ошибка публикации поста {post_id}: {e}")

# Запуск планировщика
scheduler = BackgroundScheduler(timezone="Asia/Tashkent") # Укажите ваш часовой пояс
scheduler.add_job(check_queue, 'interval', minutes=1)
scheduler.start()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def is_admin(user_id):
    if hasattr(config, 'ADMIN_IDS'):
        return user_id in config.ADMIN_IDS
    return True 

def get_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_action"))
    return markup

# --- ОБРАБОТЧИКИ КОМАНД ---

@bot.message_handler(commands=['start'])
def start(message):
    if not is_admin(message.from_user.id): return
    bot.send_message(message.chat.id, "🤖 Бот готов. Отправь описание мода или ссылку, чтобы создать пост.")

@bot.message_handler(commands=['queue'])
def show_queue(message):
    if not is_admin(message.from_user.id): return
    pending = database.get_all_pending()
    if not pending:
        bot.send_message(message.chat.id, "📭 Очередь пуста.")
        return
    
    res = "📅 <b>Очередь публикаций:</b>\n\n"
    for p in pending:
        dt = datetime.fromtimestamp(p[5]).strftime('%d.%m %H:%M') if p[5] else "Сразу"
        res += f"• {dt} -> {p[4]}\n"
    bot.send_message(message.chat.id, res, parse_mode="HTML")

# --- ЛОГИКА СОЗДАНИЯ ПОСТА ---

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    if not is_admin(message.from_user.id): return
    
    msg = bot.send_message(message.chat.id, "⏳ Генерирую пост...")
    
    # Генерация текста через Gemini
    try:
        generated_text = ai_generator.generate_post(message.text)
        
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ В очередь", callback_data="add_to_q"),
                   InlineKeyboardButton("📅 Время", callback_data="sched_exact"))
        markup.add(InlineKeyboardButton("🗑 Удалить", callback_data="cancel_action"))
        
        sent_msg = bot.send_message(message.chat.id, generated_text, parse_mode="HTML", reply_markup=markup)
        
        # Сохраняем черновик
        user_drafts[sent_msg.message_id] = {
            'text': generated_text,
            'photo': None,
            'document': None,
            'channel': config.DEFAULT_CHANNEL
        }
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка нейросети: {e}", message.chat.id, msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "cancel_action":
        bot.delete_message(call.message.chat.id, call.message.message_id)
        return

    draft = user_drafts.get(call.message.message_id)
    
    if call.data == "add_to_q":
        if draft:
            database.add_to_queue(draft['photo'], draft['text'], draft['document'], draft['channel'], int(time.time()))
            bot.answer_callback_query(call.id, "✅ Добавлено в очередь")
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    if call.data == "sched_exact":
        msg = bot.send_message(call.message.chat.id, "🕒 Введи дату и время в формате:\n`07.03.2026 21:00`", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_time, call.message.message_id)

def process_time(message, draft_msg_id):
    try:
        dt = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        timestamp = int(dt.timestamp())
        
        draft = user_drafts.get(draft_msg_id)
        if draft:
            database.add_to_queue(draft['photo'], draft['text'], draft['document'], draft['channel'], timestamp)
            bot.send_message(message.chat.id, f"📅 Запланировано на {message.text}")
            bot.edit_message_reply_markup(message.chat.id, draft_msg_id, reply_markup=None)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат. Попробуй еще раз через кнопку 'Время'.")

# Запуск бота
print("🚀 Бот запущен...")
bot.infinity_polling()