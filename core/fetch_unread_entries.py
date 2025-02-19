import concurrent.futures
import time
import traceback
import sqlite3

from common.logger import logger
from core.process_entries import process_entry


def fetch_unread_entries(config, miniflux_client):
    logger.info('Getting unread entries')
    entries = miniflux_client.get_entries(status=['unread'], limit=10000)
        
    logger.info('Connection to database')
    conn = sqlite3.connect('miniflux-ai.db')     
    conn.row_factory = sqlite3.Row 
    logger.info('Connected to database')
    cursor = conn.cursor()
    
    for entry in entries['entries']:
        id_entry = entry['id']
        datetime = entry['published_at']
        title = entry['title']
        site_url = entry['feed']['site_url']
        category_id = entry['feed']['category']['id']
        content = entry['content']
        
        cursor.execute('SELECT 1 FROM entries WHERE id = ?', (id_entry,))
        exist = cursor.fetchone()
        
        if(not exist):
            cursor.execute('''
                INSERT INTO entries (id, category_id, date, title, site_url, content, summary) VALUES (?, ?, ?, ?, ?, ?, NULL)
            ''', (id_entry, category_id, datetime, title, site_url, content))
            conn.commit()
            logger.info('Inserted entry with id: ' + str(id_entry))
        else:
            logger.info('Entry with id: ' + str(id_entry) + ' already exists')


    cursor.execute('SELECT * FROM entries WHERE summary IS NULL')
    entries_not_summarised = cursor.fetchall()
            
    conn.commit()
    conn.close()
        
    start_time = time.time()
    logger.info('Get unsummarized unread entries: ' + str(len(entries_not_summarised))) if len(entries_not_summarised) > 0 else logger.info('No new entries')

    with concurrent.futures.ThreadPoolExecutor(max_workers=config.llm_max_workers) as executor:
        futures = [executor.submit(process_entry, miniflux_client, entry) for entry in entries_not_summarised]
        for future in concurrent.futures.as_completed(futures):
            try:
                data = future.result()
            except Exception as e:
                logger.error(traceback.format_exc())
                logger.error('generated an exception: %s' % e)

    # if len(entries['entries']) > 0 and time.time() - start_time >= 3:
    #     logger.info('Done')
