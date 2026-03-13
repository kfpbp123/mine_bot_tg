import pytz
from datetime import datetime, timedelta
import os
import re
import csv
import config
import database

def get_time_greeting():
    tashkent_tz = pytz.timezone('Asia/Tashkent')
    hour = datetime.now(tashkent_tz).hour
    if hour < 6: return "╤А╤Я╨КтДв ╨атАЭ╨а╤Х╨а┬▒╨б╨В╨а╤Х╨атДЦ ╨а╨Е╨а╤Х╨бтАб╨а╤С"
    elif hour < 12: return "╤А╤Я╨КтАж ╨атАЭ╨а╤Х╨а┬▒╨б╨В╨а╤Х╨а┬╡ ╨б╤У╨бтАЪ╨б╨В╨а╤Х"
    elif hour < 18: return "╨▓╨В╨┐╤С╨П ╨атАЭ╨а╤Х╨а┬▒╨б╨В╨бтА╣╨атДЦ ╨а╥С╨а┬╡╨а╨Е╨б╨К"
    else: return "╤А╤Я╨КтАа ╨атАЭ╨а╤Х╨а┬▒╨б╨В╨бтА╣╨атДЦ ╨а╨Ж╨а┬╡╨бтАб╨а┬╡╨б╨В"

def format_queue_post(post, index, total):
    post_id, photo_id, text, doc_id, channel, time_sched = post
    type_icon = "╤А╤ЯтАУ╤Ш╨┐╤С╨П" if photo_id else "╤А╤ЯтАЬ╤Ь" if not doc_id else "╤А╤ЯтАЬ╨Г"
    if photo_id and ',' in photo_id: type_icon = "╤А╤ЯтАЬ╤Щ"

    tashkent_tz = pytz.timezone('Asia/Tashkent')
    if time_sched:
        dt = datetime.fromtimestamp(time_sched, tashkent_tz)
        now = datetime.now(tashkent_tz)
        if dt.date() == now.date(): time_str = f"╨а╨О╨а┬╡╨а╤Ц╨а╤Х╨а╥С╨а╨Е╨б╨П ╨а╨Ж {dt.strftime('%H:%M')}"
        elif dt.date() == (now + timedelta(days=1)).date(): time_str = f"╨атАФ╨а┬░╨а╨Ж╨бтАЪ╨б╨В╨а┬░ ╨а╨Ж {dt.strftime('%H:%M')}"
        else: time_str = dt.strftime('%d.%m.%Y %H:%M')
    else:
        time_str = "╨▓╨П┬░ ╨а╤Ь╨а┬╡ ╨а┬╖╨а┬░╨а╤Ч╨а┬╗╨а┬░╨а╨Е╨а╤С╨б╨В╨а╤Х╨а╨Ж╨а┬░╨а╨Е╨а╤Х"

    preview = re.sub(r'<[^>]+>', '', text)[:100]
    return f"""╨▓тАвтАЭ╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╤А╤ЯтАЬтА╣ ╨а╤Я╨а╤Ы╨а╨О╨а╤Ю {index}/{total} ╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАвтАФ
{type_icon} <b>╨а╤Ю╨а╤С╨а╤Ч:</b> {'╨а╤Т╨а┬╗╨б╨К╨а┬▒╨а╤Х╨а╤Ш' if photo_id and ',' in photo_id else '╨а┬д╨а╤Х╨бтАЪ╨а╤Х' if photo_id else '╨а╤Ю╨а┬╡╨а╤Ф╨б╨Г╨бтАЪ'}
╤А╤ЯтАЬ╤Ю <b>╨а╤Щ╨а┬░╨а╨Е╨а┬░╨а┬╗:</b> {channel or config.DEFAULT_CHANNEL}
╨▓╨П┬░ <b>╨атАЩ╨б╨В╨а┬╡╨а╤Ш╨б╨П:</b> {time_str}

╤А╤ЯтАЬ╤Ь <b>╨а╤Я╨б╨В╨а┬╡╨а╨Ж╨б╨К╨б╨Л:</b>
<i>{preview}{'...' if len(text) > 100 else ''}</i>
╨▓тАв╤Щ╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Т╨▓тАв╤Ь"""

def get_channels():
    channels = config.AVAILABLE_CHANNELS.copy()
    if os.path.exists("channels.txt"):
        with open("channels.txt", "r", encoding="utf-8") as f:
            extra_channels = [line.strip() for line in f.readlines() if line.strip()]
            for ch in extra_channels:
                if ch not in channels: channels.append(ch)
    return channels

def get_active_channel(user_id, active_channels):
    ch = active_channels.get(user_id)
    if ch: return ch
    channels = get_channels()
    return channels[0] if channels else config.DEFAULT_CHANNEL

def get_active_persona(user_id, user_personas):
    return user_personas.get(user_id, "uz")

def save_ad_text(text):
    with open("ad.txt", "w", encoding="utf-8") as f: f.write(text)

def get_ad_text():
    if os.path.exists("ad.txt"):
        with open("ad.txt", "r", encoding="utf-8") as f: return f.read()
    return ""

def generate_csv_export():
    posts = database.get_all_posts()
    if not posts: return None, None

    tashkent_tz = pytz.timezone('Asia/Tashkent')
    filename = f"posts_export_{datetime.now(tashkent_tz).strftime('%Y%m%d_%H%M%S')}.csv"

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['ID', '╨а╤Щ╨а┬░╨а╨Е╨а┬░╨а┬╗', '╨а╤Ю╨а┬╡╨а╤Ф╨б╨Г╨бтАЪ ╨а╤Ч╨а╤Х╨б╨Г╨бтАЪ╨а┬░', '╨а╨О╨бтАЪ╨а┬░╨бтАЪ╨б╤У╨б╨Г', '╨атАЩ╨б╨В╨а┬╡╨а╤Ш╨б╨П ╨а╤Ч╨б╤У╨а┬▒╨а┬╗╨а╤С╨а╤Ф╨а┬░╨бтАа╨а╤С╨а╤С', '╨а╤Ь╨а┬░╨а┬╗╨а╤С╨бтАб╨а╤С╨а┬╡ ╨бтАЮ╨а╤Х╨бтАЪ╨а╤Х/╨бтАЮ╨а┬░╨атДЦ╨а┬╗╨а┬░'])

        for p in posts:
            time_str = datetime.fromtimestamp(p[6], tashkent_tz).strftime('%d.%m.%Y %H:%M') if len(p) > 6 and p[6] else "╨а╤Ь╨а┬╡╨бтАЪ"
            has_media = "╨атАЭ╨а┬░" if p[1] or p[3] else "╨а╤Ь╨а┬╡╨бтАЪ"
            clean_text = re.sub(r'<[^>]+>', '', p[2])
            writer.writerow([p[0], p[5] if len(p) > 5 else "Default", clean_text, p[4], time_str, has_media])
    
    return filename, posts
