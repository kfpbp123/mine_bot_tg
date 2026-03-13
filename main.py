import telebot
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
import time
import threading
import os
import html
import config
import database
import ai_generator
import watermarker
import comments_analyzer
import utils
import markups
import core
import pytz
from datetime import datetime, timedelta
from bot_instance import bot

database.init_db()
album_cache = {}
user_states = {}

# --- SCHEDULER ---
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = BackgroundScheduler(jobstores=jobstores)
if not scheduler.get_job('queue_process'):
    scheduler.add_job(core.process_queue, 'interval', minutes=1, id='queue_process', replace_existing=True)
scheduler.start()

def show_queue_page(chat_id, page, message_id=None):
    posts = database.get_all_pending()
    if not posts:
        text = "📭 Очередь пуста."
        if message_id: bot.edit_message_text(text, chat_id, message_id)
        else: bot.send_message(chat_id, text)
        return
    if page >= len(posts): page = len(posts) - 1
    if page < 0: page = 0
    post = posts[page]
    msg_text = f"⏳ <b>В очереди: {len(posts)} постов</b>\n\n"
    msg_text += utils.format_queue_post(post, page + 1, len(posts))
    markup = markups.get_queue_manage_markup(post[0], page)
    if message_id:
        try: bot.edit_message_text(msg_text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
        except: pass
    else: bot.send_message(chat_id, msg_text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private': return
    user_states[message.chat.id] = None
    greeting = utils.get_time_greeting()
    bot.send_message(message.chat.id, f"{greeting}! Я бот-администратор.", reply_markup=markups.get_main_menu())

@bot.message_handler(content_types=['text', 'photo'])
def handle_text_photo(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.chat.type in ['group', 'supergroup']:
        if message.text and not message.text.startswith('/'):
            database.save_comment(message.from_user.first_name, message.text, int(time.time()))
        return

    if chat_id in user_states and user_states[chat_id] == 'ai_chat':
        if message.text == "❌ Отмена":
            user_states[chat_id] = None
            bot.send_message(chat_id, "Выход из чата.", reply_markup=markups.get_main_menu())
            return
        bot.send_chat_action(chat_id, 'typing')
        response = ai_generator.chat_with_ai(message.text)
        bot.send_message(chat_id, response, reply_markup=markups.get_cancel_markup())
        return

    if message.content_type == 'text':
        text = message.text
        if text == "📝 Создать пост":
            bot.send_message(chat_id, "Пришли ссылку или текст.")
        elif text == "🤖 Чат с ИИ":
            user_states[chat_id] = 'ai_chat'
            bot.send_message(chat_id, "Задавай вопросы по Minecraft!", reply_markup=markups.get_cancel_markup())
        elif text == "🌍 Выбор языка":
            bot.send_message(chat_id, "Выбери язык:", reply_markup=markups.get_language_menu())
        elif text == "📋 Очередь постов":
            show_queue_page(chat_id, 0)
        elif text == "📊 Статистика":
            core.show_stats(chat_id, len(utils.get_channels()))
        elif text == "🧐 Анализ комментариев":
            msg = bot.send_message(chat_id, "⏳ Анализ...")
            report = comments_analyzer.analyze_comments()
            bot.delete_message(chat_id, msg.message_id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🗑 Очистить", callback_data="clear_comments_db"))
            bot.send_message(chat_id, report, parse_mode="HTML", reply_markup=markup)
        elif text == "📥 Экспорт (CSV)":
            filename, _ = utils.generate_csv_export()
            if filename:
                with open(filename, 'rb') as f: bot.send_document(chat_id, f)
                os.remove(filename)
            else: bot.send_message(chat_id, "Данных для экспорта пока нет.")
        elif text == "💾 Бекап базы":
            if os.path.exists('bot_data.db'):
                with open('bot_data.db', 'rb') as f: bot.send_document(chat_id, f)
            else: bot.send_message(chat_id, "Файл базы данных не найден.")
        elif text == "📢 Реклама":
            msg = bot.send_message(chat_id, "Пришли новый текст рекламы:", reply_markup=markups.get_cancel_markup())
            bot.register_next_step_handler(msg, process_ad_step)
        elif text == "➕ Добавить канал":
            msg = bot.send_message(chat_id, "Введи @username:", reply_markup=markups.get_cancel_markup())
            bot.register_next_step_handler(msg, process_add_channel_step)
        elif text == "📢 Выбор канала":
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            active_ch = utils.get_active_channel(user_id)
            for ch in utils.get_channels():
                status = "✅ " if active_ch == ch else ""
                markup.add(telebot.types.InlineKeyboardButton(f"{status}{ch}", callback_data=f"set_channel_{ch}")) 
            bot.send_message(chat_id, "Выбери канал:", reply_markup=markup)
        elif text == "❌ Отмена":
            user_states[chat_id] = None
            bot.send_message(chat_id, "Отменено.", reply_markup=markups.get_main_menu())
        else:
            if not message.media_group_id: process_single_message(message)
            elif message.media_group_id not in album_cache:
                album_cache[message.media_group_id] = []
                threading.Timer(2.0, process_album, args=[message.media_group_id, chat_id, user_id]).start()
            if message.media_group_id: album_cache[message.media_group_id].append(message)
    elif message.photo:
        if not message.media_group_id: process_single_message(message)
        elif message.media_group_id not in album_cache:
            album_cache[message.media_group_id] = []
            threading.Timer(2.0, process_album, args=[message.media_group_id, chat_id, user_id]).start()
        if message.media_group_id: album_cache[message.media_group_id].append(message)

def process_single_message(message):
    temp_in, temp_out = f"in_{message.message_id}.jpg", f"out_{message.message_id}.jpg"
    try:
        user_input = message.caption if message.photo else message.text
        if not user_input: return
        persona = utils.get_active_persona(message.from_user.id)
        generated_text = ai_generator.generate_post(user_input, persona)
        photo_id = None
        if message.photo:
            file_info = bot.get_file(message.photo[-1].file_id)
            with open(temp_in, 'wb') as f: f.write(bot.download_file(file_info.file_path))
            watermarker.add_watermark(temp_in, temp_out)
            with open(temp_out if os.path.exists(temp_out) else temp_in, 'rb') as f:
                sent = bot.send_photo(message.chat.id, f)
                photo_id = sent.photo[-1].file_id
                bot.delete_message(message.chat.id, sent.message_id)
        draft = {'photo': photo_id, 'text': generated_text, 'document': None, 'ad_added': False, 'channel': utils.get_active_channel(message.from_user.id)}
        database.save_draft(message.from_user.id, photo_id, generated_text, None, draft['channel'])
        send_draft_preview(message.chat.id, draft)
    finally:
        for f in [temp_in, temp_out]: 
            if os.path.exists(f): os.remove(f)

def process_album(media_group_id, chat_id, user_id):
    messages = album_cache.pop(media_group_id, None)
    if not messages: return
    messages.sort(key=lambda x: x.message_id)
    caption = next((m.caption for m in messages if m.caption), "Скриншоты")
    persona = utils.get_active_persona(user_id)
    generated_text = ai_generator.generate_post(caption, persona)
    temp_files, opened_files = [], []
    try:
        for i, m in enumerate(messages):
            file_info = bot.get_file(m.photo[-1].file_id)
            tin, tout = f"in_{media_group_id}_{i}.jpg", f"out_{media_group_id}_{i}.jpg"
            with open(tin, 'wb') as f: f.write(bot.download_file(file_info.file_path))
            watermarker.add_watermark(tin, tout)
            temp_files.append((tin, tout if os.path.exists(tout) else tin))
        media = []
        for _, t in temp_files:
            f = open(t, 'rb')
            opened_files.append(f)
            media.append(telebot.types.InputMediaPhoto(f))
        sent_msgs = bot.send_media_group(chat_id, media)
        photo_id_str = ",".join([m.photo[-1].file_id for m in sent_msgs])
        for m in sent_msgs: bot.delete_message(chat_id, m.message_id)
        draft = {'photo': photo_id_str, 'text': generated_text, 'document': None, 'ad_added': False, 'channel': utils.get_active_channel(user_id)}
        database.save_draft(user_id, photo_id_str, generated_text, None, draft['channel'])
        send_draft_preview(chat_id, draft)
    finally:
        for f in opened_files: f.close()
        for tin, tout in temp_files:
            if os.path.exists(tin): os.remove(tin)
            if os.path.exists(tout) and tout != tin: os.remove(tout)

def send_draft_preview(chat_id, draft):
    if draft['photo'] and ',' in draft['photo']:
        bot.send_media_group(chat_id, [telebot.types.InputMediaPhoto(m) for m in draft['photo'].split(',')])
        sent = bot.send_message(chat_id, draft['text'], parse_mode='HTML')
    elif draft['photo']:
        if len(draft['text']) <= 1024: sent = bot.send_photo(chat_id, draft['photo'], caption=draft['text'], parse_mode='HTML')
        else:
            bot.send_photo(chat_id, draft['photo'])
            sent = bot.send_message(chat_id, draft['text'], parse_mode='HTML')
    else: sent = bot.send_message(chat_id, draft['text'], parse_mode='HTML')
    bot.edit_message_reply_markup(chat_id, sent.message_id, reply_markup=markups.get_draft_markup(sent.message_id))

def process_ad_step(message):
    if message.text == "❌ Отмена": 
        bot.send_message(message.chat.id, "Отменено.", reply_markup=markups.get_main_menu())
        return
    utils.save_ad_text(message.text)
    bot.send_message(message.chat.id, "Реклама сохранена!", reply_markup=markups.get_main_menu())

def process_add_channel_step(message):
    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "Отменено.", reply_markup=markups.get_main_menu())
        return
    new_ch = message.text.strip()
    if not new_ch.startswith('@'): new_ch = '@' + new_ch
    with open("channels.txt", "a", encoding="utf-8") as f: f.write(new_ch + "\n")
    bot.send_message(message.chat.id, f"Канал {new_ch} добавлен!", reply_markup=markups.get_main_menu())

def save_edited_text(message, target_id, chat_id, is_queue=False, post_id=None):
    if message.text == "❌ Отмена": 
        bot.send_message(chat_id, "Отменено.", reply_markup=markups.get_main_menu())
        return
    if is_queue:
        database.update_post_text(post_id, message.text)
        show_queue_page(chat_id, 0)
    else:
        draft = database.get_draft(message.from_user.id)
        if draft:
            draft['text'] = message.text
            database.save_draft(message.from_user.id, draft['photo'], draft['text'], draft['document'], draft['channel'])
            send_draft_preview(chat_id, draft)

def process_exact_time(message, draft_id, chat_id, is_queue=False, post_id=None):
    if message.text == "❌ Отмена":
        bot.send_message(chat_id, "Отменено.", reply_markup=markups.get_main_menu())
        return
    try:
        tashkent_tz = pytz.timezone('Asia/Tashkent')
        ts = int(tashkent_tz.localize(datetime.strptime(message.text, "%d.%m.%Y %H:%M")).timestamp())
        if is_queue:
            database.update_post_time(post_id, ts)
            show_queue_page(chat_id, 0)
        else:
            draft = database.get_draft(message.from_user.id)
            if draft:
                database.add_to_queue(draft['photo'], draft['text'], draft['document'], draft['channel'], ts)
                database.clear_draft(message.from_user.id)
                bot.send_message(chat_id, "Запланировано!", reply_markup=markups.get_main_menu())
    except: bot.send_message(chat_id, "Ошибка формата. Используй ДД.ММ.ГГГГ ЧЧ:ММ")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id, user_id = call.message.chat.id, call.from_user.id
    if call.data.startswith('set_lang_'):
        database.set_user_setting(user_id, lang=call.data.replace('set_lang_', ''))
        bot.delete_message(chat_id, call.message.message_id)
    elif call.data.startswith('set_channel_'):
        database.set_user_setting(user_id, channel=call.data.replace('set_channel_', ''))
        bot.delete_message(chat_id, call.message.message_id)
    elif call.data.startswith('q_'):
        parts = call.data.split('_')
        action, val = parts[1], int(parts[2])
        if action == 'page': show_queue_page(chat_id, val, call.message.message_id)
        elif action == 'del': database.delete_from_queue(val); show_queue_page(chat_id, 0, call.message.message_id)
        elif action == 'edit':
            msg = bot.send_message(chat_id, "Новый текст:", reply_markup=markups.get_cancel_markup())
            bot.register_next_step_handler(msg, save_edited_text, None, chat_id, True, val)
        elif action == 'pub':
            post = next((p for p in database.get_all_pending() if p[0] == val), None)
            if post and core.publish_post_data(post[0], post[1], post[2], post[3], post[4] or config.DEFAULT_CHANNEL):
                show_queue_page(chat_id, 0, call.message.message_id)
        elif action == 'time':
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_publish_queue_menu(val, "qtime_"))
    elif call.data.startswith('qtime_'):
        parts = call.data.split('_')
        action, val, post_id = parts[1], int(parts[2]), int(parts[3])
        if action == 'interval':
            database.update_post_time(post_id, int(time.time()) + val * 3600)
            show_queue_page(chat_id, 0, call.message.message_id)
        elif action == 'exact':
            msg = bot.send_message(chat_id, "Введи время (ДД.ММ.ГГГГ ЧЧ:ММ):", reply_markup=markups.get_cancel_markup())
            bot.register_next_step_handler(msg, process_exact_time, None, chat_id, True, post_id)
    elif call.data == "rewrite_menu": bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_rewrite_menu())
    elif call.data.startswith("rw_"):
        draft = database.get_draft(user_id)
        if draft:
            draft['text'] = ai_generator.rewrite_post(draft['text'], call.data.split("_")[1])
            database.save_draft(user_id, draft['photo'], draft['text'], draft['document'], draft['channel'])
            update_draft_inline(chat_id, call.message.message_id, draft)
    elif call.data == "pub_now":
        draft = database.get_draft(user_id)
        if draft and core.publish_post_data(-1, draft['photo'], draft['text'], draft['document'], draft['channel']):
            database.record_published_post(draft['photo'], draft['text'], draft['document'], draft['channel'])
            database.clear_draft(user_id)
            bot.delete_message(chat_id, call.message.message_id)
    elif call.data == "pub_queue_menu": bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_publish_queue_menu(call.message.message_id))
    elif call.data == "back_to_draft": bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_draft_markup(call.message.message_id))
    elif call.data == "clear_comments_db": database.clear_comments(); bot.answer_callback_query(call.id, "Очищено!")

bot.polling(none_stop=True)
