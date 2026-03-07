import sqlite3
import time

def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  photo_id TEXT,
                  text TEXT,
                  document_id TEXT,
                  status TEXT DEFAULT 'pending')''')
    
    # Безопасно добавляем новые колонки, если их нет
    try:
        c.execute("ALTER TABLE queue ADD COLUMN channel_id TEXT")
    except sqlite3.OperationalError:
        pass # Колонка уже существует
    
    try:
        c.execute("ALTER TABLE queue ADD COLUMN scheduled_time INTEGER")
    except sqlite3.OperationalError:
        pass # Колонка уже существует
        
    conn.commit()
    conn.close()

def add_to_queue(photo_id, text, document_id=None, channel_id=None, scheduled_time=None):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("INSERT INTO queue (photo_id, text, document_id, channel_id, scheduled_time) VALUES (?, ?, ?, ?, ?)", 
              (photo_id, text, document_id, channel_id, scheduled_time))
    conn.commit()
    conn.close()

def get_ready_posts():
    """Получает посты, время публикации которых уже наступило"""
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    current_time = int(time.time())
    # Выбираем посты, где время <= текущему, или время не задано (сразу в очередь)
    c.execute('''SELECT id, photo_id, text, document_id, channel_id 
                 FROM queue 
                 WHERE status='pending' AND (scheduled_time IS NULL OR scheduled_time <= ?) 
                 ORDER BY scheduled_time ASC''', (current_time,))
    rows = c.fetchall()
    conn.close()
    return rows

def mark_as_posted(post_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("UPDATE queue SET status='posted' WHERE id=?", (post_id,))
    conn.commit()
    conn.close()

def get_queue_count():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM queue WHERE status='pending'")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_pending():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("SELECT id, photo_id, text, document_id, channel_id, scheduled_time FROM queue WHERE status='pending' ORDER BY scheduled_time ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_from_queue(post_id):
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM queue WHERE id=?", (post_id,))
    conn.commit()
    conn.close()