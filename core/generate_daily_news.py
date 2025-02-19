import json
import time
from datetime import datetime, timedelta
from openai import OpenAI

from common import logger
from common.config import Config
from core.get_ai_result import get_ai_result

config = Config()
llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)

def generate_daily_news(miniflux_client):
    logger.info('Generating daily news')
    
    logger.info('Connection to database')
    conn = sqlite3.connect('miniflux-ai.db')     
    conn.row_factory = sqlite3.Row 
    logger.info('Connected to database')
    cursor = conn.cursor()
    
    
    # Calculate the time 12 hours ago
    time_12_hours_ago = datetime.now() - timedelta(hours=12)

    # Format the time as a string in the same format as the datetime column
    time_12_hours_ago_str = time_12_hours_ago.strftime('%Y-%m-%d %H:%M:%S')

    # Select articles with a summary and dated in the past 12 hours
    cursor.execute('''
        SELECT * FROM entries
        WHERE summary IS NOT NULL AND datetime >= ?
    ''', (time_12_hours_ago_str,))

    # Fetch all matching rows
    rows = cursor.fetchall()
    entries = cursor.fetchall()
    
    logger.info(entries[0])
    
    exit(0)

    contents = '\n'.join([miniflux_client.get_entry(i['id'])['content'] for i in entries])
    # greeting
    greeting = get_ai_result(config.ai_news_prompts['greeting'], time.strftime('%B %d, %Y at %I:%M %p'))
    # summary_block
    summary_block = get_ai_result(config.ai_news_prompts['summary_block'], contents)
    # summary
    summary = get_ai_result(config.ai_news_prompts['summary'], summary_block)

    response_content = greeting + '\n\n### 🌐Summary\n' + summary + '\n\n### 📝News\n' + summary_block

    logger.info('Generated daily news: ' + response_content)

    with open('ai_news.json', 'w') as f:
        json.dump(response_content, f, indent=4, ensure_ascii=False)

    # trigger miniflux feed refresh
    feeds = miniflux_client.get_feeds()
    ai_news_feed_id = next((item['id'] for item in feeds if 'Newsᴬᴵ for you' in item['title']), None)

    if ai_news_feed_id:
        miniflux_client.refresh_feed(ai_news_feed_id)
        logger.debug('Successfully refreshed the ai_news feed in Miniflux!')