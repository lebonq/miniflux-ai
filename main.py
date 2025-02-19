import concurrent.futures
import time
import traceback
import sqlite3

import miniflux
import schedule

from common import Config, logger
from miniflux_ai import app
from core import fetch_unread_entries, generate_daily_news

config = Config()
miniflux_client = miniflux.Client(config.miniflux_base_url, api_key=config.miniflux_api_key)
while True:
    try:
        alive = miniflux_client.me()
        logger.info('Successfully connected to Miniflux!')
        break
    except Exception as e:
        logger.error('Cannot connect to Miniflux: %s' % e)
        time.sleep(1)

def my_schedule():
    interval = 15 if config.miniflux_webhook_secret else 1
    schedule.every(interval).minutes.do(fetch_unread_entries, config, miniflux_client)
    schedule.run_all()

    if config.ai_news_schedule:
        feeds = miniflux_client.get_feeds()
        if not any('Newsᴬᴵ for you' in item['title'] for item in feeds):
            try:
                miniflux_client.create_feed(category_id=1, feed_url=config.ai_news_url + '/rss/ai-news')
                logger.info('Successfully created the ai_news feed in Miniflux!')
            except Exception as e:
                logger.error('Failed to create the ai_news feed in Miniflux: %s' % e)
        for ai_schedule in config.ai_news_schedule:
            schedule.every().day.at(ai_schedule).do(generate_daily_news, miniflux_client)

    while True:
        schedule.run_pending()
        time.sleep(1)

def my_flask():
    logger.info('Starting API')
    app.run(host='0.0.0.0', port=80)

if __name__ == '__main__':
    
    conn = sqlite3.connect('miniflux-ai.db')
    logger.info('Connected to database')
    
    #If database empty create table for entries : date,title,id,summary
    if conn.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='entries';").fetchone()[0] == 0:
        logger.info('Creating table because it does not exist')
        conn.execute('''CREATE TABLE IF NOT EXISTS entries (
                        id INTEGER PRIMARY KEY,
                        category_id INTEGER NOT NULL,
                        date TEXT NOT NULL,
                        title TEXT NOT NULL,
                        site_url TEXT NOT NULL,
                        summary TEXT
                    );''')
        conn.commit()
    conn.close()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(my_flask)
        executor.submit(my_schedule)
