# -*- coding: utf-8 -*-
"""
  This file is part of lisogo

  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from flask import Flask

app = Flask(__name__)

from lisogo import views
from lisogo.application import mongodb_connect, mongodb_select_db
