# -*- coding: utf-8 -*-
"""
  This file is part of lisogo

  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from flask import Flask

"""
This file sets up the minimal configuration and environment objects used in
lisogo.
"""

# Flask app - running as standalone or a module?
if __name__ == '__main__':
    app = Flask(__name__)
else:
    from . import app

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

# Fire an http server if we want to run lisogo as a standalone application
if __name__ == '__main__':
    app.run()
