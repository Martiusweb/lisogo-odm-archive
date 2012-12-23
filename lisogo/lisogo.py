# -*- coding: utf-8 -*-
"""
  This file is part of lisogo

  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from flask import Flask, g
from pymongo import MongoClient
import config
from model import DocumentTransformer

"""
This file sets up the minimal configuration and environment objects used in
lisogo.
"""

# Flask app - running as standalone or a module?
if __name__ == '__main__':
    app = Flask(__name__)
else:
    from . import app

# Configuration
app.config.from_object('lisogo.config')

# Initalizes logging handler
if not app.debug:
    import logging
    from logging.handlers import RotatingFileHandler

    # Use rotating logs
    logging_handler = RotatingFileHandler(config.LOG_FILE)
    logging_handler.setLevel(getattr(logging, config.LOG_LEVEL))

    # Set format of each logged message
    logging_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %s(message)s [in %(pathname)s:%(lineno)d]'
    ))

    # assign the handler to the interresting modules
    loggers = [app.logger]
    for logger in loggers:
        logger.addHandler(logging_handler)

    from flask import got_request_exception

    # log uncaught exceptions
    @got_request_exception.connect_via(app)
    def log_exception(sender, exception, **extra):
        sender.logger.debug('Uncaught exception %s', exception)

# Set up the connection to mongodb
def mongodb_connect(host = config.MONGODB_HOST, port = config.MONGODB_PORT):
    return MongoClient(host, port)

def mongodb_select_db(client, db_name = config.MONGODB_DB_NAME, module = 'lisogo.model'):
    db = client[db_name]
    db.add_son_manipulator(DocumentTransformer(module))
    return db

# Initialize the connection before handling a request
@app.before_request
def mongo_auto_connect():
    g.mongo = mongodb_connect()
    g.db = mongodb_select_db(g.mongo)

# Ensure the connection to mongodb is closed after a request is handled
@app.teardown_request
def mongo_auto_disconnect(exception):
    g.db = None
    g.mongo.disconnect()

# Fire an http server if we want to run lisogo as a standalone application
# Actually, I don't really fire lisogo app from this file, I use
# ../run_lisogo.py instead
if __name__ == '__main__':
    app.run()
