# -*- coding: utf-8 -*-
"""
  This file is part of lisogo

  :copyright: © Martin Richard - martiusweb.net
  :license: Released under GNU/GPLv2 license
"""

from lisogo import app
from flask import render_template

@app.route('/')
def index():
    return render_template('index.html')
