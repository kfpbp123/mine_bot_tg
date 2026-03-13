import telebot
import config
import database
import os
import time
import pytz
from datetime import datetime

def publish_post_data(bot, post_id, photo_id, text, document_id, channel_id, is_auto=False):
    try:
        if photo_id:
            if ',' in photo_id:
                ids = photo_id.split(',')
                media = [telebot.types.InputMediaPhoto(media=pid, caption=text if i==0 and len(text)<=1024 else None, parse_mode='HTML') for i, pid in enumerate(ids)]
                bot.send_media_group(channel_id, media)
                if len(text) > 1024:
                    bot.send_message(channel_id, text, parse_mode='HTML')
            else:
                if len(text) <= 1024:
                    bot.send_photo(channel_id, photo_id, caption=text, parse_mode='HTML')
                else:
                    bot.send_photo(channel_id, photo_id)
                    bot.send_message(channel_id, text, parse_mode='HTML')
        else:
            bot.send_message(channel_id, text, parse_mode='HTML')

        if document_id: bot.send_document(channel_id, document_id)

        if post_id != -1:
            database.mark_as_posted(post_id)
            if is_auto:
                for admin in getattr(config, 'ADMIN_IDS', []):
                    try: bot.send_message(admin, f"╨▓╤ЪтАж <b>╨а╤Т╨а╨Ж╨бтАЪ╨а╤Х╨а╤Ч╨а╤Х╨б╨Г╨бтАЪ╨а╤С╨а╨Е╨а╤Ц:</b> ╨атАФ╨а┬░╨а╤Ч╨┬╗╨а┬░╨а╨Е╨а╤С╨б╨В╨а╤Х╨а╨Ж╨а┬░╨а╨Е╨а╨Е╨бтА╣╨атДЦ ╨а╤Ч╨а╤Х╨б╨Г╨бтАЪ ╨б╤У╨б╨Г╨а╤Ч╨а┬╡╨бтВм╨а╨Е╨а╤Х ╨а╤Х╨а╤Ч╨б╤У╨а┬▒╨а┬╗╨а╤С╨а╤Ф╨а╤Х╨а╨Ж╨а┬░╨а╨Е ╨а╨Ж {channel_id}!", parse_mode='HTML') 
                    except: pass
        return True
    except Exception as e:
        print(f"╨▓╤Ь╨К ╨а╤Ы╨бтВм╨а╤С╨а┬▒╨а╤Ф╨а┬░ ╨а╤Ч╨б╤У╨а┬▒╨а┬╗╨а╤С╨а╤Ф╨а┬░╨бтАа╨а╤С╨а╤С ╨а╨Ж {channel_id}: {e}")
        return False

def process_queue(bot):
    posts = database.get_ready_posts()
    for post in posts:
        post_id, photo_id, text, document_id, channel_id = post
        target_channel = channel_id if channel_id else config.DEFAULT_CHANNEL
        publish_post_data(bot, post_id, photo_id, text, document_id, target_channel, is_auto=True)

def show_stats(bot, chat_id, channels_count):
    stats = database.get_stats()
    text = f"""╤А╤ЯтАЬ╨Й <b>╨а╨О╨а╤Ю╨а╤Т╨а╤Ю╨а╨а╨О╨а╤Ю╨а╨а╤Щ╨а╤Т ╨атАШ╨а╤Ы╨а╤Ю╨а╤Т</b> ╤А╤ЯтАЬ╨Й

╤А╤ЯтАЬ╤Ь ╨атАЩ╨б╨Г╨а┬╡╨а╤Ц╨а╤Х ╨а╤Ч╨а╤Х╨б╨Г╨бтАЪ╨а╤Х╨а╨Ж ╨б╨Г╨а╤Х╨а┬╖╨а╥С╨а┬░╨а╨Е╨а╤Х: <b>{stats['total']}</b>
╨▓╤ЪтАж ╨а╨И╨б╨Г╨а╤Ч╨а┬╡╨бтВм╨а╨Е╨а╤Х ╨а╤Х╨а╤Ч╨б╤У╨а┬▒╨а┬╗╨а╤С╨а╤Ф╨а╤Х╨а╨Ж╨а┬░╨а╨Е╨а╤Х: <b>{stats['published']}</b>
╨▓╨П╤Ц ╨атАУ╨а╥С╨б╤У╨бтАЪ ╨а╨Ж ╨а╤Х╨бтАб╨а┬╡╨б╨В╨а┬╡╨а╥С╨а╤С: <b>{stats['queue']}</b>
╤А╤ЯтАЬтАж ╨а╤Ы╨а╤Ч╨б╤У╨а┬▒╨а┬╗╨а╤С╨а╤Ф╨а╤Х╨а╨Ж╨а┬░╨а╨Е╨а╤Х ╨б╨Г╨а┬╡╨а╤Ц╨а╤Х╨а╥С╨а╨Е╨б╨П: <b>{stats['today']}</b>
╤А╤ЯтАЬ╤Ю ╨а╤Я╨а╤Х╨а╥С╨а╤Ф╨а┬╗╨б╨Л╨бтАб╨а┬╡╨а╨Е╨а╨Е╨бтА╣╨бтАж ╨а╤Ф╨а┬░╨а╨Е╨а┬░╨а┬╗╨а╤Х╨а╨Ж: <b>{channels_count}</b>"""
    bot.send_message(chat_id, text, parse_mode='HTML')
