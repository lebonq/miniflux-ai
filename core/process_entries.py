import json
import sqlite3
import markdown
from markdownify import markdownify as md
from openai import OpenAI
import threading

from common.config import Config
from common.logger import logger
from core.entry_filter import filter_entry

config = Config()
llm_client = OpenAI(base_url=config.llm_base_url, api_key=config.llm_api_key)
file_lock = threading.Lock()

def process_entry(miniflux_client, entry):
    #Todo change to queue
    llm_result = ''
    start_with_list = [name[1]['title'] for name in config.agents.items()]
    style_block = [name[1]['style_block'] for name in config.agents.items()]
    [start_with_list.append('<pre') for i in style_block if i]
 
    try:
        with open('entries.json', 'r') as file:
            data_before_update = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        data_before_update = []
        
    conn = sqlite3.connect('miniflux-ai.db')      
    cursor = conn.cursor()
    
    content = miniflux_client.get_entry(entry['id'])['content']

    for agent in config.agents.items():
        # filter, if AI is not generating, and in allow_list, or not in deny_list
        if filter_entry(agent, entry):
            if '${content}' in agent[1]['prompt']:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": agent[1]['prompt'].replace('${content}', md(content))}
                ]
            else:
                messages = [
                    {"role": "system", "content": agent[1]['prompt']},
                    {"role": "user", "content": "The following is the input content:\n---\n " + md(content)}
                ]

            completion = llm_client.chat.completions.create(
                model=config.llm_model,
                messages= messages,
                timeout=config.llm_timeout
            )

            response_content = completion.choices[0].message.content
            logger.info(f"agents:{agent[0]} - feed_title:{entry['title']} - id:{entry['id']} - result:{response_content}")

            # save for ai_summary
            if agent[0] == 'summary':
                cursor.execute('''
                    UPDATE entries SET summary = ? WHERE id = ?
                ''', (response_content, entry['id']))
                conn.commit()
                logger.info('Updated entry with id: ' + str(entry['id']))

            if agent[1]['style_block']:
                llm_result = (llm_result + '<pre style="white-space: pre-wrap;"><code>\n'
                              + agent[1]['title']
                              + response_content.replace('\n', '').replace('\r', '')
                              + '\n</code></pre><hr><br />')
            else:
                llm_result = llm_result + f"{agent[1]['title']}{markdown.markdown(response_content)}<hr><br />"
        else:
            logger.info(f"agents:{agent[0]} - feed_title:{entry['title']} - id:{entry['id']}  not summarised : already done")

    #if len(llm_result) > 0:
        #dict_result = miniflux_client.update_entry(entry['id'], content= llm_result + content)
        
    conn.close()
