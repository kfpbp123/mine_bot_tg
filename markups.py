from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("📝 Создать пост"), KeyboardButton("🤖 Чат с ИИ"))
    markup.add(KeyboardButton("🌍 Выбор языка"), KeyboardButton("📢 Выбор канала"))
    markup.add(KeyboardButton("➕ Добавить канал"), KeyboardButton("📋 Очередь постов"))
    markup.add(KeyboardButton("📊 Статистика"), KeyboardButton("📥 Экспорт (CSV)"))
    markup.add(KeyboardButton("📢 Реклама"), KeyboardButton("💾 Бекап базы"))    
    markup.add(KeyboardButton("🧐 Анализ комментариев"))
    return markup

def get_language_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="set_lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru"),
        InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en")
    )
    return markup

def get_cancel_markup():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton("❌ Отмена"))
    return markup

def get_draft_markup(draft_id):
    markup = InlineKeyboardMarkup(row_width=2)
    interval = getattr(config, 'SMART_QUEUE_INTERVAL_HOURS', 2)
    markup.add(
        InlineKeyboardButton(f"⏳ Умная очередь (+{interval} ч)", callback_data="add_to_smart_q")
    )
    markup.add(
        InlineKeyboardButton("🚀 Опубликовать", callback_data="pub_now"),
        InlineKeyboardButton("📅 В очередь", callback_data="pub_queue_menu")
    )
    markup.add(
        InlineKeyboardButton("📝 Текст", callback_data="edit_text"),
        InlineKeyboardButton("🔄 Рерайт", callback_data="rewrite_menu")
    )
    markup.add(
        InlineKeyboardButton("📢 +Реклама", callback_data="add_ad"),
        InlineKeyboardButton("🗑 Удалить", callback_data="cancel_action")
    )
    return markup

def get_rewrite_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🧱 Коротко", callback_data="rw_short"),
        InlineKeyboardButton("🎮 Геймер", callback_data="rw_fun")
    )
    markup.add(
        InlineKeyboardButton("👨‍🔬 Учёный", callback_data="rw_scientist"),
        InlineKeyboardButton("😴 Нудный", callback_data="rw_boring")
    )
    markup.add(
        InlineKeyboardButton("👔 Профи", callback_data="rw_pro"),
        InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft")
    )
    return markup

def get_publish_queue_menu(target_id, prefix="sched_"):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("2 часа", callback_data=f"{prefix}interval_2_{target_id}"),       
        InlineKeyboardButton("4 часа", callback_data=f"{prefix}interval_4_{target_id}"),       
        InlineKeyboardButton("6 часов", callback_data=f"{prefix}interval_6_{target_id}"),     
        InlineKeyboardButton("12 часов", callback_data=f"{prefix}interval_12_{target_id}"),   
        InlineKeyboardButton("24 часа", callback_data=f"{prefix}interval_24_{target_id}")      
    )
    markup.add(InlineKeyboardButton("📅 Точное время", callback_data=f"{prefix}exact_{target_id}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft" if prefix == "sched_" else f"q_page_0"))
    return markup

def get_queue_manage_markup(post_id, page):
    markup = InlineKeyboardMarkup(row_width=2)
    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"q_page_{page-1}"))
    nav_row.append(InlineKeyboardButton("➡️", callback_data=f"q_page_{page+1}"))
    markup.add(*nav_row)
    
    markup.add(
        InlineKeyboardButton("📝 Текст", callback_data=f"q_edit_{post_id}"),
        InlineKeyboardButton("📅 Время", callback_data=f"q_time_{post_id}")
    )
    markup.add(
        InlineKeyboardButton("🚀 Сейчас", callback_data=f"q_pub_{post_id}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"q_del_{post_id}")
    )
    return markup
