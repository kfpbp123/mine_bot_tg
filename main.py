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
from strings import MESSAGES, BUTTONS

database.init_db()
album_cache = {}
user_states = {}

# --- SCHEDULER ---
jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')}
scheduler = BackgroundScheduler(jobstores=jobstores)
if not scheduler.get_job('queue_process'):
    scheduler.add_job(core.process_queue, 'interval', minutes=1, id='queue_process', replace_existing=True)
scheduler.start()

def get_user_lang(user_id):
    lang, _ = database.get_user_settings(user_id)
    return lang or 'uz'

def show_queue_page(chat_id, page, message_id=None):
    user_id = chat_id # В личке совпадает
    lang = get_user_lang(user_id)
    posts = database.get_all_pending()
    if not posts:
        text = MESSAGES[lang]['queue_empty']
        if message_id: bot.edit_message_text(text, chat_id, message_id, parse_mode='HTML')
        else: bot.send_message(chat_id, text, parse_mode='HTML')
        return
    if page >= len(posts): page = len(posts) - 1
    if page < 0: page = 0
    post = posts[page]
    msg_text = utils.format_queue_post(post, page + 1, len(posts))
    markup = markups.get_queue_manage_markup(post[0], page, lang)
    if message_id:
        try: bot.edit_message_text(msg_text, chat_id, message_id, parse_mode='HTML', reply_markup=markup)
        except: pass
    else: bot.send_message(chat_id, msg_text, parse_mode='HTML', reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private': return
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    user_states[message.chat.id] = None
    text = MESSAGES[lang]['welcome']
    bot.send_message(message.chat.id, text, reply_markup=markups.get_main_menu(lang), parse_mode='HTML')

@bot.message_handler(content_types=['text', 'photo', 'document', 'video', 'audio'])
def handle_text_photo_file(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    lang = get_user_lang(user_id)

    if message.chat.type in ['group', 'supergroup']:
        if message.text and not message.text.startswith('/'):
            database.save_comment(message.from_user.first_name, message.text, int(time.time()))
        return

    # --- ОБРАБОТКА REPLY ---
    if message.reply_to_message:
        file_id = None
        if message.document: file_id = message.document.file_id
        elif message.video: file_id = message.video.file_id
        elif message.audio: file_id = message.audio.file_id
        elif message.photo: file_id = message.photo[-1].file_id
        
        if file_id:
            bot.send_chat_action(chat_id, 'upload_document')
            draft = database.get_draft(user_id)
            if draft:
                if message.photo: draft['photo'] = file_id
                else: draft['document'] = file_id
                database.save_draft(user_id, draft['photo'], draft['text'], draft['document'], draft['channel'], 1 if draft.get('ad_added') else 0)
                bot.reply_to(message, MESSAGES[lang]['file_attached'])
                send_draft_preview(chat_id, draft)
                return

    state_data = user_states.get(chat_id)
    if state_data and state_data.get('state') == 'ai_chat':
        if message.text in [BUTTONS['uz']['cancel'], BUTTONS['ru']['cancel'], BUTTONS['en']['cancel']]:
            user_states[chat_id] = None
            bot.send_message(chat_id, MESSAGES[lang]['ai_chat_off'], reply_markup=markups.get_main_menu(lang), parse_mode='HTML')
            return
        bot.send_chat_action(chat_id, 'typing')
        response = ai_generator.chat_with_ai(message.text, lang)
        bot.send_message(chat_id, f"🤖 <b>AI:</b>\n\n{response}", parse_mode='HTML', reply_markup=markups.get_cancel_markup(lang))
        return

    if message.content_type == 'text':
        text = message.text
        # Проверка кнопок на всех языках
        if text in [BUTTONS['uz']['create'], BUTTONS['ru']['create'], BUTTONS['en']['create']]:
            bot.send_message(chat_id, "📬 <b>Link / Info?</b>", parse_mode='HTML')
        elif text in [BUTTONS['uz']['ai_chat'], BUTTONS['ru']['ai_chat'], BUTTONS['en']['ai_chat']]:
            user_states[chat_id] = {'state': 'ai_chat'}
            bot.send_message(chat_id, MESSAGES[lang]['ai_chat_active'], reply_markup=markups.get_cancel_markup(lang), parse_mode='HTML')
        elif text in [BUTTONS['uz']['lang'], BUTTONS['ru']['lang'], BUTTONS['en']['lang']]:
            bot.send_message(chat_id, MESSAGES[lang]['choose_lang'], reply_markup=markups.get_language_menu(), parse_mode='HTML')
        elif text in [BUTTONS['uz']['queue'], BUTTONS['ru']['queue'], BUTTONS['en']['queue']]:
            bot.send_chat_action(chat_id, 'typing')
            show_queue_page(chat_id, 0)
        elif text in [BUTTONS['uz']['stats'], BUTTONS['ru']['stats'], BUTTONS['en']['stats']]:
            core.show_stats(chat_id, len(utils.get_channels()))
        elif text in [BUTTONS['uz']['settings'], BUTTONS['ru']['settings'], BUTTONS['en']['settings']]:
            bot.send_message(chat_id, MESSAGES[lang]['settings'], reply_markup=markups.get_settings_menu(lang), parse_mode='HTML')
        elif text in [BUTTONS['uz']['analyze'], BUTTONS['ru']['analyze'], BUTTONS['en']['analyze']]:
            bot.send_chat_action(chat_id, 'typing')
            msg = bot.send_message(chat_id, MESSAGES[lang]['analyzing'], parse_mode='HTML')
            report = comments_analyzer.analyze_comments()
            bot.delete_message(chat_id, msg.message_id)
            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("🗑 Clear", callback_data="clear_comments_db"))
            bot.send_message(chat_id, report, parse_mode="HTML", reply_markup=markup)
        elif text in [BUTTONS['uz']['cancel'], BUTTONS['ru']['cancel'], BUTTONS['en']['cancel']]:
            user_states[chat_id] = None
            bot.send_message(chat_id, "🏠", reply_markup=markups.get_main_menu(lang), parse_mode='HTML')
        else:
            bot.send_chat_action(chat_id, 'typing')
            if not message.media_group_id:
                start_generation(chat_id, user_id, text, None)
            elif message.media_group_id not in album_cache:
                album_cache[message.media_group_id] = []
                threading.Timer(2.0, process_album_immediate, args=[message.media_group_id, chat_id, user_id]).start()
            if message.media_group_id: album_cache[message.media_group_id].append(message)
    
    elif message.photo:
        bot.send_chat_action(chat_id, 'upload_photo')
        if not message.media_group_id:
            start_generation(chat_id, user_id, message.caption, message.photo[-1].file_id)
        elif message.media_group_id not in album_cache:
            album_cache[message.media_group_id] = []
            threading.Timer(2.0, process_album_immediate, args=[message.media_group_id, chat_id, user_id]).start()
        if message.media_group_id: album_cache[message.media_group_id].append(message)

def process_album_immediate(media_group_id, chat_id, user_id):
    messages = album_cache.pop(media_group_id, None)
    if not messages: return
    caption = next((m.caption for m in messages if m.caption), "")
    photo_ids = ",".join([m.photo[-1].file_id for m in messages])
    start_generation(chat_id, user_id, caption, photo_ids, is_album=True)

def start_generation(chat_id, user_id, user_input, photo_id, is_album=False):
    lang = get_user_lang(user_id)
    msg = bot.send_message(chat_id, MESSAGES[lang]['generation_start'], parse_mode='HTML')
    
    generated_text = ai_generator.generate_post(user_input or "Minecraft", persona=lang)
    bot.delete_message(chat_id, msg.message_id)
    
    final_photo_id = photo_id
    if photo_id and not is_album:
        bot.send_chat_action(chat_id, 'upload_photo')
        temp_in, temp_out = f"in_{chat_id}.jpg", f"out_{chat_id}.jpg"
        file_info = bot.get_file(photo_id)
        with open(temp_in, 'wb') as f: f.write(bot.download_file(file_info.file_path))
        watermarker.add_watermark(temp_in, temp_out)
        with open(temp_out if os.path.exists(temp_out) else temp_in, 'rb') as f:
            sent = bot.send_photo(chat_id, f)
            final_photo_id = sent.photo[-1].file_id
            bot.delete_message(chat_id, sent.message_id)
        if os.path.exists(temp_in): os.remove(temp_in)
        if os.path.exists(temp_out): os.remove(temp_out)

    draft = {'photo': final_photo_id, 'text': generated_text, 'document': None, 'ad_added': False, 'channel': utils.get_active_channel(user_id)}
    database.save_draft(user_id, final_photo_id, generated_text, None, draft['channel'])
    send_draft_preview(chat_id, draft)

def send_draft_preview(chat_id, draft):
    user_id = chat_id
    lang = get_user_lang(user_id)
    bot.send_chat_action(chat_id, 'typing')
    doc_info = f"\n\n📄 <b>File:</b> Yes" if draft.get('document') else ""
    full_text = draft['text'] + doc_info
    
    if draft['photo'] and ',' in draft['photo']:
        bot.send_media_group(chat_id, [telebot.types.InputMediaPhoto(m) for m in draft['photo'].split(',')])
        sent = bot.send_message(chat_id, full_text, parse_mode='HTML')
    elif draft['photo']:
        if len(full_text) <= 1024: 
            sent = bot.send_photo(chat_id, draft['photo'], caption=full_text, parse_mode='HTML')
        else:
            bot.send_photo(chat_id, draft['photo'])
            sent = bot.send_message(chat_id, full_text, parse_mode='HTML')
    else: 
        sent = bot.send_message(chat_id, full_text, parse_mode='HTML')
    
    bot.edit_message_reply_markup(chat_id, sent.message_id, reply_markup=markups.get_draft_markup(lang))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id, user_id = call.message.chat.id, call.from_user.id
    lang = get_user_lang(user_id)
    
    if call.data.startswith('set_lang_'):
        new_lang = call.data.replace('set_lang_', '')
        database.set_user_setting(user_id, lang=new_lang)
        bot.answer_callback_query(call.id, "✅ Done")
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(chat_id, MESSAGES[new_lang]['welcome'], reply_markup=markups.get_main_menu(new_lang), parse_mode='HTML')
    
    elif call.data == "csv_export":
        filename, _ = utils.generate_csv_export()
        if filename:
            with open(filename, 'rb') as f: bot.send_document(chat_id, f)
            os.remove(filename)
    
    elif call.data == "db_backup":
        if os.path.exists('bot_data.db'):
            with open('bot_data.db', 'rb') as f: bot.send_document(chat_id, f)

    elif call.data == "set_ad_text":
        msg = bot.send_message(chat_id, MESSAGES[lang]['enter_ad'], reply_markup=markups.get_cancel_markup(lang))
        bot.register_next_step_handler(msg, process_ad_step)

    elif call.data == "add_new_channel":
        msg = bot.send_message(chat_id, MESSAGES[lang]['enter_channel'], reply_markup=markups.get_cancel_markup(lang))
        bot.register_next_step_handler(msg, process_add_channel_step)

    elif call.data.startswith('set_channel_'):
        database.set_user_setting(user_id, channel=call.data.replace('set_channel_', ''))
        bot.delete_message(chat_id, call.message.message_id)

    elif call.data.startswith('q_'):
        parts = call.data.split('_')
        action, val = parts[1], int(parts[2])
        if action == 'page': show_queue_page(chat_id, val, call.message.message_id)
        elif action == 'del': database.delete_from_queue(val); show_queue_page(chat_id, 0, call.message.message_id)
        elif action == 'edit':
            msg = bot.send_message(chat_id, MESSAGES[lang]['enter_new_text'], reply_markup=markups.get_cancel_markup(lang))
            bot.register_next_step_handler(msg, save_edited_text, None, chat_id, True, val)
        elif action == 'pub':
            post = next((p for p in database.get_all_pending() if p[0] == val), None)
            if post and core.publish_post_data(post[0], post[1], post[2], post[3], post[4] or config.DEFAULT_CHANNEL):
                show_queue_page(chat_id, 0, call.message.message_id)
        elif action == 'time':
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_publish_queue_menu(val, "qtime_", lang))

    elif call.data == "rewrite_menu": 
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_rewrite_menu(lang))
    
    elif call.data.startswith("rw_"):
        draft = database.get_draft(user_id)
        if draft:
            bot.send_chat_action(chat_id, 'typing')
            draft['text'] = ai_generator.rewrite_post(draft['text'], call.data.split("_")[1], lang)
            database.save_draft(user_id, draft['photo'], draft['text'], draft['document'], draft['channel'], 1 if draft.get('ad_added') else 0)
            finalize_draft_update(chat_id, call.message.message_id, draft)

    elif call.data == "edit_text":
        msg = bot.send_message(chat_id, MESSAGES[lang]['enter_new_text'], reply_markup=markups.get_cancel_markup(lang))
        bot.register_next_step_handler(msg, save_edited_text, call.message.message_id, chat_id)

    elif call.data == "add_to_smart_q":
        draft = database.get_draft(user_id)
        if draft:
            last_time = database.get_last_scheduled_time()
            now = int(time.time())
            interval = config.SMART_QUEUE_INTERVAL_HOURS * 3600
            new_time = (last_time + interval) if (last_time and last_time > now) else (now + 3600)
            database.add_to_queue(draft['photo'], draft['text'], draft['document'], draft['channel'], new_time)
            database.clear_draft(user_id)
            bot.answer_callback_query(call.id, MESSAGES[lang]['smart_queue_done'] + datetime.fromtimestamp(new_time).strftime('%d.%m %H:%M'))
            bot.delete_message(chat_id, call.message.message_id)

    elif call.data == "add_ad":
        ad_text = utils.get_ad_text()
        draft = database.get_draft(user_id)
        if draft and not draft.get('ad_added'):
            draft['text'] += f"\n\n{ad_text}"
            database.save_draft(user_id, draft['photo'], draft['text'], draft['document'], draft['channel'], 1)
            finalize_draft_update(chat_id, call.message.message_id, draft)
            bot.answer_callback_query(call.id, MESSAGES[lang]['ad_added'])

    elif call.data == "pub_now":
        draft = database.get_draft(user_id)
        if draft and core.publish_post_data(-1, draft['photo'], draft['text'], draft['document'], draft['channel']):
            database.record_published_post(draft['photo'], draft['text'], draft['document'], draft['channel'])
            database.clear_draft(user_id)
            bot.delete_message(chat_id, call.message.message_id)

    elif call.data == "pub_queue_menu": 
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_publish_queue_menu(call.message.message_id, lang=lang))
    elif call.data == "back_to_draft": 
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=markups.get_draft_markup(lang))
    elif call.data == "cancel_action": 
        bot.delete_message(chat_id, call.message.message_id)

def finalize_draft_update(chat_id, message_id, draft):
    lang = get_user_lang(chat_id)
    doc_info = f"\n\n📄 <b>File:</b> Yes" if draft.get('document') else ""
    full_text = draft['text'] + doc_info
    try: bot.edit_message_text(full_text, chat_id, message_id, parse_mode='HTML', reply_markup=markups.get_draft_markup(lang))
    except:
        try: bot.edit_message_caption(full_text, chat_id, message_id, parse_mode='HTML', reply_markup=markups.get_draft_markup(lang))
        except: pass

def process_ad_step(message):
    lang = get_user_lang(message.from_user.id)
    if message.text in [BUTTONS['uz']['cancel'], BUTTONS['ru']['cancel'], BUTTONS['en']['cancel']]: return
    utils.save_ad_text(message.text)
    bot.send_message(message.chat.id, MESSAGES[lang]['ad_saved'], reply_markup=markups.get_main_menu(lang))

def process_add_channel_step(message):
    lang = get_user_lang(message.from_user.id)
    if message.text in [BUTTONS['uz']['cancel'], BUTTONS['ru']['cancel'], BUTTONS['en']['cancel']]: return
    new_ch = message.text.strip()
    if not new_ch.startswith('@'): new_ch = '@' + new_ch
    with open("channels.txt", "a", encoding="utf-8") as f: f.write(new_ch + "\n")
    bot.send_message(message.chat.id, MESSAGES[lang]['channel_added'], reply_markup=markups.get_main_menu(lang))

def save_edited_text(message, target_id, chat_id, is_queue=False, post_id=None):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    if message.text in [BUTTONS['uz']['cancel'], BUTTONS['ru']['cancel'], BUTTONS['en']['cancel']]: return
    
    if is_queue:
        database.update_post_text(post_id, message.text)
        show_queue_page(chat_id, 0)
    else:
        draft = database.get_draft(user_id)
        if draft:
            # Отправляем новый текст на рерайт "красивое оформление", но с сохранением смысла пользователя
            bot.send_chat_action(chat_id, 'typing')
            draft['text'] = ai_generator.rewrite_post(message.text, "pro", lang)
            database.save_draft(user_id, draft['photo'], draft['text'], draft['document'], draft['channel'], 1 if draft.get('ad_added') else 0)
            send_draft_preview(chat_id, draft)

bot.polling(none_stop=True)
