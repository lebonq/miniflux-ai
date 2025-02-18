from flask import Flask
app = Flask(__name__)

from miniflux_ai import ai_news, ai_summary, my_swaggerui_blueprint