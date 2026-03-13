from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import config

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(KeyboardButton("➕ Создать пост"), KeyboardButton("🤖 Чат с ИИ"))
    markup.add(KeyboardButton("📋 Очередь"), KeyboardButton("🌍 Язык"))
    markup.add(KeyboardButton("📢 Каналы"), KeyboardButton("📊 Статистика"))
    markup.add(KeyboardButton("⚙️ Настройки"), KeyboardButton("🧐 Анализ"))
    return markup

def get_settings_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📢 Рекламный текст", callback_data="set_ad_text"),
        InlineKeyboardButton("➕ Добавить канал", callback_data="add_new_channel")
    )
    markup.add(InlineKeyboardButton("💾 Бекап базы", callback_data="db_backup"))
    markup.add(InlineKeyboardButton("📥 Экспорт CSV", callback_data="csv_export"))
    return markup

def get_template_menu():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("📦 Стандартный (Описание + фишки)", callback_data="tmpl_standard"),
        InlineKeyboardButton("🔥 Список (ТОП-4 фишки)", callback_data="tmpl_list"),
        InlineKeyboardButton("🧐 Обзор (Плюсы и Минусы)", callback_data="tmpl_review")
    )
    markup.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_action"))
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
    markup.add(InlineKeyboardButton("⏳ Умная очередь", callback_data="add_to_smart_q"))
    markup.add(
        InlineKeyboardButton("🚀 Сейчас", callback_data="pub_now"),
        InlineKeyboardButton("📅 Время", callback_data="pub_queue_menu")
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
    markup.add(InlineKeyboardButton("👔 Профи", callback_data="rw_pro"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft"))
    return markup

def get_publish_queue_menu(target_id, prefix="sched_"):
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("+2ч", callback_data=f"{prefix}interval_2_{target_id}"),       
        InlineKeyboardButton("+4ч", callback_data=f"{prefix}interval_4_{target_id}"),       
        InlineKeyboardButton("+6ч", callback_data=f"{prefix}interval_6_{target_id}")
    )
    markup.add(
        InlineKeyboardButton("+12ч", callback_data=f"{prefix}interval_12_{target_id}"),   
        InlineKeyboardButton("+24ч", callback_data=f"{prefix}interval_24_{target_id}"),
        InlineKeyboardButton("🕒 Своё", callback_data=f"{prefix}exact_{target_id}")
    )
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back_to_draft" if prefix == "sched_" else "q_page_0"))
    return markup

def get_queue_manage_markup(post_id, page):
    markup = InlineKeyboardMarkup(row_width=2)
    nav_row = []
    if page > 0: nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"q_page_{page-1}"))
    nav_row.append(InlineKeyboardButton("➡️", callback_data=f"q_page_{page+1}"))
    markup.add(*nav_row)
    markup.add(
        InlineKeyboardButton("📝 Текст", callback_data=f"q_edit_{post_id}"),
        InlineKeyboardButton("🕒 Время", callback_data=f"q_time_{post_id}")
    )
    markup.add(
        InlineKeyboardButton("🚀 Опубликовать", callback_data=f"q_pub_{post_id}"),
        InlineKeyboardButton("🗑 Удалить", callback_data=f"q_del_{post_id}")
    )
    return markup
